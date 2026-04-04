"""
superagente.py — Super Agente Claude Code para el bot de Telegram.
Simplemente envía prompts a Claude Code CLI (claude -p) y devuelve la respuesta.
Maneja sesiones persistentes con --resume y nombres de conversaciones.
No usa API keys, no loguea — es hablar con Claude por terminal.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn

REPO_DIR = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
CLAUDE_BIN = '/home/osserver/.local/bin/claude'
CLAUDE_SESSIONS_DIR = os.path.expanduser(
    '~/.claude/projects/-home-osserver-Proyectos-Antigravity-Integraciones-OS'
)
TIMEOUT_CLAUDE = 1200  # segundos (20 minutos)


# ── Ejecutar Claude ──────────────────────────────────────────────────────────

def _ejecutar_claude(prompt: str, session_id: str = None) -> dict:
    """Ejecuta claude -p y retorna {ok, result, session_id} parseado del JSON."""
    env = os.environ.copy()
    env.pop('CLAUDECODE', None)
    env.pop('ANTHROPIC_API_KEY', None)  # Forzar OAuth (plan Pro), no API key

    cmd = [CLAUDE_BIN, '-p', prompt, '--output-format', 'json']
    if session_id:
        cmd += ['--resume', session_id]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=REPO_DIR, timeout=TIMEOUT_CLAUDE, env=env,
        )
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'El Super Agente tardó demasiado. Intenta de nuevo.'}
    except FileNotFoundError:
        return {'ok': False, 'error': 'claude no está instalado.'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    stdout = proc.stdout.strip()
    stderr = (proc.stderr or '').strip()

    if not stdout:
        stderr_lower = stderr.lower()
        if 'credit balance' in stderr_lower:
            return {'ok': False, 'error': 'La cuenta de Claude alcanzó su límite de uso. Intenta más tarde.'}
        if 'prompt is too long' in stderr_lower or 'too long' in stderr_lower:
            return {'ok': False, 'error': 'La conversación es muy larga. Creá una nueva con 📝 Nueva.'}
        return {'ok': False, 'error': stderr[:200] if stderr else 'El Super Agente no respondió.'}

    # claude --output-format json puede emitir múltiples líneas; la última es el resultado
    last_line = stdout.strip().split('\n')[-1]
    try:
        data = json.loads(last_line)
        result_text = data.get('result', '')
        if 'credit balance' in result_text.lower():
            return {'ok': False, 'error': 'La cuenta de Claude alcanzó su límite de uso. Intenta más tarde.'}
        return {
            'ok': True,
            'result': result_text,
            'session_id': data.get('session_id', ''),
        }
    except (json.JSONDecodeError, ValueError):
        if 'credit balance' in last_line.lower():
            return {'ok': False, 'error': 'La cuenta de Claude alcanzó su límite de uso. Intenta más tarde.'}
        return {'ok': False, 'error': f'Respuesta no válida: {last_line[:200]}'}


# ── Sesiones BD ──────────────────────────────────────────────────────────────

def obtener_sesion_activa(usuario_id: str, empresa: str) -> dict | None:
    """Retorna la sesión activa del usuario o None."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, claude_session_id, nombre FROM sa_sesiones '
                'WHERE usuario_id=%s AND empresa=%s AND activa=1 '
                'ORDER BY updated_at DESC LIMIT 1',
                (usuario_id, empresa)
            )
            return cur.fetchone()
    finally:
        conn.close()


def crear_sesion(usuario_id: str, empresa: str, claude_session_id: str,
                 nombre: str = 'Sin nombre') -> int:
    """Crea una sesión nueva y la marca como activa. Desactiva las demás."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE sa_sesiones SET activa=0 WHERE usuario_id=%s AND empresa=%s',
                (usuario_id, empresa)
            )
            cur.execute(
                'INSERT INTO sa_sesiones (empresa, usuario_id, claude_session_id, nombre, activa) '
                'VALUES (%s, %s, %s, %s, 1)',
                (empresa, usuario_id, claude_session_id, nombre)
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
                'SELECT id, claude_session_id, nombre, activa, created_at FROM sa_sesiones '
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
                'UPDATE sa_sesiones SET activa=0 WHERE usuario_id=%s AND empresa=%s',
                (usuario_id, empresa)
            )
            cur.execute(
                'UPDATE sa_sesiones SET activa=1 WHERE id=%s AND usuario_id=%s',
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
            cur.execute('UPDATE sa_sesiones SET nombre=%s WHERE id=%s', (nombre, sesion_id))
            conn.commit()
    finally:
        conn.close()


def borrar_conversacion(sesion_id: int, usuario_id: str) -> str | None:
    """Borra la sesión de BD y el .jsonl del disco. Retorna nombre borrado o None."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT claude_session_id, nombre FROM sa_sesiones WHERE id=%s AND usuario_id=%s',
                (sesion_id, usuario_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            # Borrar archivo de sesión de Claude
            jsonl = os.path.join(CLAUDE_SESSIONS_DIR, f"{row['claude_session_id']}.jsonl")
            if os.path.exists(jsonl):
                os.remove(jsonl)
            cur.execute('DELETE FROM sa_sesiones WHERE id=%s', (sesion_id,))
            conn.commit()
            return row['nombre']
    finally:
        conn.close()


def obtener_historial(claude_session_id: str, max_intercambios: int = 5) -> str:
    """
    Lee el .jsonl de la sesión de Claude y retorna los últimos N intercambios
    user/assistant como texto formateado para mostrar en Telegram.
    """
    jsonl = os.path.join(CLAUDE_SESSIONS_DIR, f'{claude_session_id}.jsonl')
    if not os.path.exists(jsonl):
        return ''

    intercambios = []
    try:
        with open(jsonl, encoding='utf-8') as f:
            lines = [json.loads(l) for l in f if l.strip()]

        ultimo_user = None
        for line in lines:
            tipo = line.get('type')
            msg = line.get('message', {})
            role = msg.get('role', '')
            content = msg.get('content', '')

            # Extraer texto
            if isinstance(content, list):
                texto = ' '.join(
                    c.get('text', '') for c in content
                    if isinstance(c, dict) and c.get('type') == 'text'
                ).strip()
            else:
                texto = str(content).strip()

            if not texto:
                continue

            # Saltar el primer mensaje user (es el system prompt)
            if tipo == 'user' and role == 'user':
                # El primer mensaje contiene el prompt del sistema — saltar
                if '\nSos el Super Agente' in texto or '\nEres el Super Agente' in texto:
                    continue
                ultimo_user = texto[:300]
            elif tipo == 'assistant' and role == 'assistant' and ultimo_user:
                intercambios.append((ultimo_user, texto[:300]))
                ultimo_user = None

    except Exception:
        return ''

    if not intercambios:
        return ''

    ultimos = intercambios[-max_intercambios:]
    lineas = ['📜 *Últimos intercambios:*']
    for i, (usr, ast) in enumerate(ultimos, 1):
        lineas.append(f'\n*{i}. Tú:* {usr}')
        lineas.append(f'*SA:* {ast}')
    return '\n'.join(lineas)


# ── Config ───────────────────────────────────────────────────────────────────

def obtener_prompt_sistema(empresa: str) -> str | None:
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
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT telegram_id FROM ia_usuarios "
                "WHERE nivel>=7 AND telegram_id IS NOT NULL AND activo=1",
            )
            return [str(r['telegram_id']) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Consulta principal ───────────────────────────────────────────────────────

def consultar(pregunta: str, usuario_id: str, nombre_usuario: str,
              nivel: int, empresa: str) -> dict:
    """
    Consulta al Super Agente. Usa --resume si hay sesión activa.
    Si no hay sesión, crea una nueva enviando primero el prompt sistema.
    """
    sesion = obtener_sesion_activa(usuario_id, empresa)

    if sesion:
        resp = _ejecutar_claude(pregunta, session_id=sesion['claude_session_id'])
        if not resp.get('ok'):
            return resp
        return _procesar_respuesta(resp['result'])
    else:
        # Sin sesión → crear nueva con prompt sistema (ya retorna procesado)
        return _iniciar_sesion(pregunta, usuario_id, nombre_usuario, nivel, empresa)


def nueva_conversacion(pregunta: str, usuario_id: str, nombre_usuario: str,
                       nivel: int, empresa: str) -> dict:
    """Fuerza creación de una conversación nueva."""
    return _iniciar_sesion(pregunta, usuario_id, nombre_usuario, nivel, empresa,
                           procesar=True)


def _iniciar_sesion(pregunta: str, usuario_id: str, nombre_usuario: str,
                    nivel: int, empresa: str, procesar: bool = True) -> dict:
    """Crea sesión nueva: envía prompt sistema, luego la pregunta con --resume."""
    prompt_tpl = obtener_prompt_sistema(empresa)
    if not prompt_tpl or prompt_tpl == 'PROMPT_PENDIENTE':
        return {'ok': False, 'error': 'El Super Agente no está configurado. '
                                      'Pedile a Santi que configure el prompt.'}

    # Generar nombre: "SA - " + pregunta truncada al último espacio antes de 40 chars
    nombre = _generar_nombre(pregunta)

    prompt_sistema = (prompt_tpl
                      .replace('{usuario_nombre}', nombre_usuario)
                      .replace('{nivel}', str(nivel))
                      .replace('{empresa}', empresa))

    prompt_con_nombre = f'{nombre}\n\n{prompt_sistema}'
    resp1 = _ejecutar_claude(prompt_con_nombre)
    if not resp1.get('ok'):
        return resp1

    session_id = resp1['session_id']
    if not session_id:
        return {'ok': False, 'error': 'No se obtuvo session_id de Claude.'}

    # Guardar en BD con el mismo nombre
    crear_sesion(usuario_id, empresa, session_id, nombre=nombre)

    resp2 = _ejecutar_claude(pregunta, session_id=session_id)
    if not resp2.get('ok'):
        return resp2

    if procesar:
        return _procesar_respuesta(resp2['result'])
    return resp2


# ── Procesar respuesta ───────────────────────────────────────────────────────

def _procesar_respuesta(result_text: str) -> dict:
    """Parsea la respuesta de Claude y retorna dict tipado."""
    data = _extraer_json(result_text)
    if data:
        tipo = data.get('tipo')
        if tipo == 'tabla':
            filas = data.get('filas', [])
            columnas = data.get('columnas', [])
            if filas and isinstance(filas[0], dict):
                data['filas'] = [[str(f.get(c, '')) for c in columnas] for f in filas]
            return {'ok': True, 'tipo': 'tabla', 'contenido': data}
        if tipo == 'aprobacion':
            ids7 = obtener_telegram_ids_nivel7('ori_sil_2')
            return {'ok': True, 'tipo': 'aprobacion', 'contenido': data, 'ids_nivel7': ids7}

    return {'ok': True, 'tipo': 'texto', 'contenido': result_text}


def _extraer_json(texto: str) -> dict | None:
    """Extrae JSON de tipo tabla/aprobacion del texto de Claude."""
    import re
    texto = re.sub(r'```(?:json)?\s*', '', texto).replace('```', '').strip()
    inicio = texto.find('{')
    fin = texto.rfind('}')
    if inicio == -1 or fin == -1:
        return None
    try:
        data = json.loads(texto[inicio:fin + 1])
        if isinstance(data, dict) and data.get('tipo') in ('tabla', 'aprobacion'):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _generar_nombre(pregunta: str, max_len: int = 40) -> str:
    """Genera nombre de sesión: 'SA - ' + pregunta truncada al último espacio."""
    texto = pregunta.strip()
    if len(texto) <= max_len:
        return f'SA - {texto}'
    truncado = texto[:max_len]
    ultimo_espacio = truncado.rfind(' ')
    if ultimo_espacio > 10:
        truncado = truncado[:ultimo_espacio]
    return f'SA - {truncado}'
