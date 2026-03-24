"""
superagente.py — Super Agente Claude Code para el bot de Telegram.
Responsabilidad: llamar claude -p con contexto de sesión y gestionar historial.
Usado por: telegram_bot/bot.py
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn

REPO_DIR = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
CLAUDE_BIN = '/home/osserver/.local/bin/claude'
MAX_HISTORIAL = 10   # últimos N pares pregunta/respuesta que se incluyen en el prompt
TIMEOUT_CLAUDE = 300  # segundos (5 min — consultas complejas con múltiples queries tardan 1-2 min)


# ── Sesiones ──────────────────────────────────────────────────────────────────

def obtener_o_crear_sesion(usuario_id: str, empresa: str) -> dict:
    """Retorna la sesión activa del usuario o crea una nueva."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, mensajes FROM sa_sesiones WHERE usuario_id=%s AND empresa=%s',
                (usuario_id, empresa)
            )
            row = cur.fetchone()
            if row:
                msgs = row['mensajes']
                if isinstance(msgs, str):
                    msgs = json.loads(msgs or '[]')
                return {'id': row['id'], 'mensajes': msgs}
            cur.execute(
                "INSERT INTO sa_sesiones (empresa, usuario_id) VALUES (%s, %s)",
                (empresa, usuario_id)
            )
            conn.commit()
            return {'id': cur.lastrowid, 'mensajes': []}
    finally:
        conn.close()


def guardar_intercambio(sesion_id: int, pregunta: str, respuesta: str):
    """Agrega el par pregunta/respuesta al historial y lo rota al máximo."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT mensajes FROM sa_sesiones WHERE id=%s', (sesion_id,))
            row = cur.fetchone()
            msgs = row['mensajes'] if row else []
            if isinstance(msgs, str):
                msgs = json.loads(msgs or '[]')

            msgs.append({'role': 'user',      'content': pregunta})
            msgs.append({'role': 'assistant', 'content': respuesta})

            # Rotar: mantener solo los últimos MAX_HISTORIAL pares
            if len(msgs) > MAX_HISTORIAL * 2:
                msgs = msgs[-(MAX_HISTORIAL * 2):]

            cur.execute(
                'UPDATE sa_sesiones SET mensajes=%s WHERE id=%s',
                (json.dumps(msgs, ensure_ascii=False), sesion_id)
            )
            conn.commit()
    finally:
        conn.close()


def limpiar_sesion(usuario_id: str, empresa: str):
    """Borra el historial de la sesión."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sa_sesiones SET mensajes='[]' WHERE usuario_id=%s AND empresa=%s",
                (usuario_id, empresa)
            )
            conn.commit()
    finally:
        conn.close()


# ── Config ────────────────────────────────────────────────────────────────────

def obtener_prompt_sistema(empresa: str) -> str | None:
    """Lee el prompt_sistema desde sa_config."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT prompt_sistema FROM sa_config WHERE empresa=%s AND activo=1 LIMIT 1',
                (empresa,)
            )
            row = cur.fetchone()
            return row['prompt_sistema'] if row else None
    finally:
        conn.close()


def obtener_telegram_ids_nivel7(empresa: str) -> list[str]:
    """Retorna los telegram_id de usuarios nivel 7 para enviar aprobaciones."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT telegram_id FROM ia_usuarios WHERE nivel>=7 AND telegram_id IS NOT NULL AND activo=1",
            )
            return [str(r['telegram_id']) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Consulta principal ────────────────────────────────────────────────────────

def consultar(pregunta: str, usuario_id: str, nombre_usuario: str,
              nivel: int, empresa: str) -> dict:
    """
    Llama claude -p con el contexto completo.
    Returns:
      {'ok': True,  'tipo': 'texto',     'contenido': str}
      {'ok': True,  'tipo': 'tabla',     'contenido': dict}
      {'ok': True,  'tipo': 'aprobacion','contenido': dict, 'ids_nivel7': list}
      {'ok': False, 'error': str}
    """
    prompt_tpl = obtener_prompt_sistema(empresa)
    if not prompt_tpl or prompt_tpl == 'PROMPT_PENDIENTE':
        return {'ok': False, 'error': 'El Super Agente no está configurado aún. '
                                      'Pedile a Santi que configure el prompt en el admin.'}

    sesion     = obtener_o_crear_sesion(usuario_id, empresa)
    historial  = _formatear_historial(sesion['mensajes'])

    prompt = (prompt_tpl
              .replace('{usuario_nombre}', nombre_usuario)
              .replace('{nivel}',          str(nivel))
              .replace('{empresa}',        empresa)
              .replace('{sesion_id}',      str(sesion['id']))
              .replace('{historial}',      historial)
              .replace('{pregunta}',       pregunta))

    # Llamar claude -p desde el repo
    # Se limpia CLAUDECODE del env para permitir ejecución cuando el bot corre
    # desde dentro de otra sesión de Claude Code (ej: testing)
    env = os.environ.copy()
    env.pop('CLAUDECODE', None)

    try:
        proc = subprocess.run(
            [CLAUDE_BIN, '-p', prompt, '--output-format', 'text'],
            capture_output=True, text=True,
            cwd=REPO_DIR, timeout=TIMEOUT_CLAUDE,
            env=env,
        )
        respuesta_raw = proc.stdout.strip()
        if not respuesta_raw and proc.stderr:
            return {'ok': False, 'error': f'Claude error: {proc.stderr[:200]}'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'El Super Agente tardó demasiado. Intenta de nuevo.'}
    except FileNotFoundError:
        return {'ok': False, 'error': 'claude no está instalado o no está en el PATH.'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    if not respuesta_raw:
        return {'ok': False, 'error': 'El Super Agente no respondió.'}

    # Intentar extraer y parsear JSON especial (tabla o aprobación)
    data = _extraer_json(respuesta_raw)
    if data:
        tipo = data.get('tipo')
        if tipo == 'tabla':
            # Normalizar filas: si son dicts, convertir a listas usando el orden de columnas
            filas = data.get('filas', [])
            columnas = data.get('columnas', [])
            if filas and isinstance(filas[0], dict):
                filas = [[str(f.get(c, '')) for c in columnas] for f in filas]
                data['filas'] = filas
            guardar_intercambio(sesion['id'], pregunta, data.get('texto', '(tabla)'))
            return {'ok': True, 'tipo': 'tabla', 'contenido': data}
        if tipo == 'aprobacion':
            ids7 = obtener_telegram_ids_nivel7(empresa)
            return {'ok': True, 'tipo': 'aprobacion', 'contenido': data, 'ids_nivel7': ids7}

    # Respuesta de texto plano
    guardar_intercambio(sesion['id'], pregunta, respuesta_raw)
    return {'ok': True, 'tipo': 'texto', 'contenido': respuesta_raw}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extraer_json(texto: str) -> dict | None:
    """Extrae un JSON de tipo tabla/aprobacion del texto de Claude.
    Maneja: JSON puro, JSON dentro de bloques markdown, JSON precedido de texto."""
    import re
    # Remover bloques de código markdown
    texto = re.sub(r'```(?:json)?\s*', '', texto).replace('```', '').strip()
    # Buscar primer { hasta el último }
    inicio = texto.find('{')
    fin    = texto.rfind('}')
    if inicio == -1 or fin == -1:
        return None
    try:
        data = json.loads(texto[inicio:fin + 1])
        if isinstance(data, dict) and data.get('tipo') in ('tabla', 'aprobacion'):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _formatear_historial(mensajes: list) -> str:
    if not mensajes:
        return '(sin historial previo en esta sesión)'
    lineas = []
    for m in mensajes:
        prefijo = 'Usuario' if m.get('role') == 'user' else 'Super Agente'
        lineas.append(f"{prefijo}: {m.get('content', '')}")
    return '\n'.join(lineas)
