"""
superagente_oc.py — Super Agente OpenCode para el bot de Telegram.
Envía prompts a OpenCode CLI (opencode run) y devuelve la respuesta.
Maneja sesiones persistentes con --session/--continue y nombres de conversaciones.
No usa API keys — modelos gratuitos de OpenCode.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn

REPO_DIR = '/home/osserver/Proyectos_Antigravity/sa_opencode'
OC_BIN = '/home/osserver/.nvm/versions/node/v22.17.0/bin/opencode'
TIMEOUT_OC = 300  # segundos


# ── Ejecutar OpenCode ────────────────────────────────────────────────────────

def _ejecutar_opencode(prompt: str, session_id: str = None) -> dict:
    """Ejecuta opencode run y retorna {ok, result, session_id}."""
    cmd = [OC_BIN, 'run', prompt]
    if session_id:
        cmd += ['--session', session_id, '--continue']

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=REPO_DIR, timeout=TIMEOUT_OC,
        )
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'El Super Agente OpenCode tardó demasiado. Intenta de nuevo.'}
    except FileNotFoundError:
        return {'ok': False, 'error': 'opencode no está instalado.'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    stdout = proc.stdout.strip()
    stderr = (proc.stderr or '').strip()

    if not stdout:
        return {'ok': False, 'error': stderr[:200] if stderr else 'El Super Agente OpenCode no respondió.'}

    # Limpiar códigos ANSI de la salida
    import re
    clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
    # Quitar línea de header "> build · modelo"
    lines = clean.strip().split('\n')
    content_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('> ') and '·' in stripped:
            continue  # skip header line
        if stripped.startswith('→ Read') or stripped.startswith('→ '):
            continue  # skip tool usage lines
        if stripped.startswith('$ '):
            continue  # skip command execution lines
        content_lines.append(line)

    result_text = '\n'.join(content_lines).strip()
    if not result_text:
        result_text = clean.strip()

    return {
        'ok': True,
        'result': result_text,
        'session_id': '',  # OpenCode no retorna session_id en run mode
    }


# ── Sesiones BD ──────────────────────────────────────────────────────────────

def obtener_sesion_activa(usuario_id: str, empresa: str) -> dict | None:
    """Retorna la sesión activa del usuario o None."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, oc_session_id, nombre FROM saoc_sesiones '
                'WHERE usuario_id=%s AND empresa=%s AND activa=1 '
                'ORDER BY updated_at DESC LIMIT 1',
                (usuario_id, empresa)
            )
            return cur.fetchone()
    finally:
        conn.close()


def crear_sesion(usuario_id: str, empresa: str, oc_session_id: str = '',
                 nombre: str = 'Sin nombre') -> int:
    """Crea una sesión nueva y la marca como activa. Desactiva las demás."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE saoc_sesiones SET activa=0 WHERE usuario_id=%s AND empresa=%s',
                (usuario_id, empresa)
            )
            cur.execute(
                'INSERT INTO saoc_sesiones (empresa, usuario_id, oc_session_id, nombre, activa) '
                'VALUES (%s, %s, %s, %s, 1)',
                (empresa, usuario_id, oc_session_id, nombre)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def listar_conversaciones(usuario_id: str, empresa: str) -> list[dict]:
    """Lista todas las conversaciones del usuario, activa primero."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, nombre, activa, created_at FROM saoc_sesiones '
                'WHERE usuario_id=%s AND empresa=%s '
                'ORDER BY activa DESC, updated_at DESC',
                (usuario_id, empresa)
            )
            return cur.fetchall()
    finally:
        conn.close()


def cambiar_conversacion(usuario_id: str, empresa: str, sesion_id: int) -> bool:
    """Activa una conversación y desactiva las demás."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE saoc_sesiones SET activa=0 WHERE usuario_id=%s AND empresa=%s',
                (usuario_id, empresa)
            )
            cur.execute(
                'UPDATE saoc_sesiones SET activa=1 WHERE id=%s AND usuario_id=%s',
                (sesion_id, usuario_id)
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def renombrar_conversacion(sesion_id: int, nombre: str):
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE saoc_sesiones SET nombre=%s WHERE id=%s', (nombre, sesion_id))
            conn.commit()
    finally:
        conn.close()


def borrar_conversacion(sesion_id: int, usuario_id: str) -> str | None:
    """Borra la sesión de BD. Retorna nombre borrado o None."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT nombre FROM saoc_sesiones WHERE id=%s AND usuario_id=%s',
                (sesion_id, usuario_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute('DELETE FROM saoc_sesiones WHERE id=%s', (sesion_id,))
            conn.commit()
            return row['nombre']
    finally:
        conn.close()


# ── Consulta principal ───────────────────────────────────────────────────────

def consultar(pregunta: str, usuario_id: str, nombre_usuario: str,
              nivel: int, empresa: str) -> dict:
    """
    Consulta al Super Agente OpenCode.
    Cada mensaje es un prompt independiente (opencode run).
    Si hay sesión activa, usa --session + --continue.
    """
    sesion = obtener_sesion_activa(usuario_id, empresa)

    if sesion and sesion.get('oc_session_id'):
        resp = _ejecutar_opencode(pregunta, session_id=sesion['oc_session_id'])
    else:
        resp = _ejecutar_opencode(pregunta)

    if not resp.get('ok'):
        return resp

    return _procesar_respuesta(resp['result'])


def nueva_conversacion(pregunta: str, usuario_id: str, nombre_usuario: str,
                       nivel: int, empresa: str) -> dict:
    """Fuerza creación de una conversación nueva."""
    nombre = _generar_nombre(pregunta)

    resp = _ejecutar_opencode(pregunta)
    if not resp.get('ok'):
        return resp

    crear_sesion(usuario_id, empresa, oc_session_id='', nombre=nombre)

    return _procesar_respuesta(resp['result'])


# ── Procesar respuesta ───────────────────────────────────────────────────────

def _procesar_respuesta(result_text: str) -> dict:
    """Parsea la respuesta de OpenCode y retorna dict tipado."""
    data = _extraer_json(result_text)
    if data:
        tipo = data.get('tipo')
        if tipo == 'tabla':
            filas = data.get('filas', [])
            columnas = data.get('columnas', [])
            if filas and isinstance(filas[0], dict):
                data['filas'] = [[str(f.get(c, '')) for c in columnas] for f in filas]
            return {'ok': True, 'tipo': 'tabla', 'contenido': data}

    return {'ok': True, 'tipo': 'texto', 'contenido': result_text}


def _extraer_json(texto: str) -> dict | None:
    """Extrae JSON de tipo tabla del texto de OpenCode."""
    import re
    texto = re.sub(r'```(?:json)?\s*', '', texto).replace('```', '').strip()
    inicio = texto.find('{')
    fin = texto.rfind('}')
    if inicio == -1 or fin == -1:
        return None
    try:
        data = json.loads(texto[inicio:fin + 1])
        if isinstance(data, dict) and data.get('tipo') == 'tabla':
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _generar_nombre(pregunta: str, max_len: int = 40) -> str:
    """Genera nombre de sesión: 'SAOC - ' + pregunta truncada."""
    texto = pregunta.strip()
    if len(texto) <= max_len:
        return f'SAOC - {texto}'
    truncado = texto[:max_len]
    ultimo_espacio = truncado.rfind(' ')
    if ultimo_espacio > 10:
        truncado = truncado[:ultimo_espacio]
    return f'SAOC - {truncado}'
