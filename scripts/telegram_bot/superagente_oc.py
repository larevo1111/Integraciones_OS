"""
superagente_oc.py — Super Agente OpenCode para el bot de Telegram.
Envía prompts a OpenCode CLI (opencode run) y devuelve la respuesta.
Maneja sesiones persistentes con --session/--continue y nombres de conversaciones.
No usa API keys — modelos gratuitos de OpenCode.
"""
import json
import logging
import os
import subprocess
import sys

log = logging.getLogger('os_ia_bot')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn

REPO_DIR = '/home/osserver/Proyectos_Antigravity/sa_opencode'
OC_BIN = '/home/osserver/.nvm/versions/node/v22.17.0/bin/opencode'
TIMEOUT_OC = 1200  # segundos (20 minutos)
MODEL_DEFAULT = 'opencode/nemotron-3-super-free'
MODEL_VISION  = 'opencode/nemotron-3-super-free'  # qwen3.6-plus-free ya no existe


# ── Ejecutar OpenCode ────────────────────────────────────────────────────────

def _ejecutar_opencode(prompt: str, session_id: str = None, con_imagen: bool = False) -> dict:
    """Ejecuta opencode run --format json y retorna {ok, result, session_id}."""
    cmd = [OC_BIN, 'run', '--format', 'json', '-m', MODEL_VISION if con_imagen else MODEL_DEFAULT]
    cmd.append(prompt)
    if session_id:
        cmd += ['--session', session_id]

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
        log.error(f'SAOC stdout vacío: rc={proc.returncode}, session={session_id}, stderr={stderr[:200]}')
        return {
            'ok': False,
            'error': stderr[:200] if stderr else 'El Super Agente OpenCode no respondió.',
            'sesion_rota': bool(session_id and not stderr),
        }

    # Parsear líneas JSON — extraer textos y session_id
    text_parts = []
    sid = ''
    for line in stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not sid and event.get('sessionID'):
            sid = event['sessionID']
        etype = event.get('type', '')
        part = event.get('part', {})
        if etype == 'text' and part.get('text'):
            text_parts.append(part['text'])

    result_text = ''.join(text_parts).strip()
    if not result_text:
        log.warning(f'SAOC sin texto. stdout={stdout[:500]}')
        return {'ok': False, 'error': 'El Super Agente OpenCode no respondió.'}

    return {
        'ok': True,
        'result': result_text,
        'session_id': sid,
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
                'SELECT id, oc_session_id, nombre, activa, created_at FROM saoc_sesiones '
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


_OC_DB = os.path.expanduser('~/.local/share/opencode/opencode.db')


def obtener_historial(oc_session_id: str, max_intercambios: int = 5) -> str:
    """
    Lee el SQLite de OpenCode y retorna los últimos N intercambios como texto.
    """
    if not os.path.exists(_OC_DB):
        return ''
    try:
        import sqlite3
        conn = sqlite3.connect(_OC_DB)
        # Obtener parts tipo 'text' con su rol (via message) ordenados
        rows = conn.execute(
            '''
            SELECT json_extract(m.data, '$.role') AS role, p.data
            FROM part p
            JOIN message m ON p.message_id = m.id
            WHERE p.session_id = ?
              AND json_extract(p.data, '$.type') = 'text'
            ORDER BY p.time_created
            ''',
            (oc_session_id,)
        ).fetchall()
        conn.close()

        intercambios = []
        ultimo_user = None
        for role, data_str in rows:
            try:
                data = json.loads(data_str)
                texto = data.get('text', '').strip()
            except Exception:
                continue
            if not texto:
                continue

            if role == 'user':
                ultimo_user = texto[:300]
            elif role == 'assistant' and ultimo_user:
                intercambios.append((ultimo_user, texto[:300]))
                ultimo_user = None

        if not intercambios:
            return ''

        ultimos = intercambios[-max_intercambios:]
        lineas = ['📜 *Últimos intercambios:*']
        for i, (usr, ast) in enumerate(ultimos, 1):
            lineas.append(f'\n*{i}. Tú:* {usr}')
            lineas.append(f'*SA:* {ast}')
        return '\n'.join(lineas)

    except Exception:
        return ''


# ── Consulta principal ───────────────────────────────────────────────────────

def consultar(pregunta: str, usuario_id: str, nombre_usuario: str,
              nivel: int, empresa: str, con_imagen: bool = False) -> dict:
    """
    Consulta al Super Agente OpenCode.
    Si hay sesión activa, usa --session para continuar la conversación.
    Si no hay sesión, crea una nueva.
    con_imagen=True usa mimo-v2-omni-free para esa llamada (visión).
    """
    sesion = obtener_sesion_activa(usuario_id, empresa)

    if sesion and sesion.get('oc_session_id'):
        resp = _ejecutar_opencode(pregunta, session_id=sesion['oc_session_id'], con_imagen=con_imagen)
        if not resp.get('ok'):
            # Si la sesión está rota (stdout vacío sin stderr), crear una nueva
            if resp.get('sesion_rota'):
                log.warning(f'SAOC sesión rota {sesion["oc_session_id"]}, creando nueva')
                return nueva_conversacion(pregunta, usuario_id, nombre_usuario, nivel, empresa, con_imagen=con_imagen)
            return resp
        return _procesar_respuesta(resp['result'])
    else:
        return nueva_conversacion(pregunta, usuario_id, nombre_usuario, nivel, empresa, con_imagen=con_imagen)


def nueva_conversacion(pregunta: str, usuario_id: str, nombre_usuario: str,
                       nivel: int, empresa: str, con_imagen: bool = False) -> dict:
    """Fuerza creación de una conversación nueva (sin --session)."""
    nombre = _generar_nombre(pregunta)

    resp = _ejecutar_opencode(pregunta, con_imagen=con_imagen)
    if not resp.get('ok'):
        return resp

    oc_sid = resp.get('session_id', '')
    crear_sesion(usuario_id, empresa, oc_session_id=oc_sid, nombre=nombre)

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
    """Genera nombre de sesión: 'SAOC_' + pregunta truncada."""
    texto = pregunta.strip()
    if len(texto) <= max_len:
        return f'SAOC_{texto}'
    truncado = texto[:max_len]
    ultimo_espacio = truncado.rfind(' ')
    if ultimo_espacio > 10:
        truncado = truncado[:ultimo_espacio]
    return f'SAOC_{truncado}'
