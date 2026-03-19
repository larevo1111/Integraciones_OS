"""
Manejo del contexto de conversación.
Lee y escribe ia_conversaciones: resumen vivo (≤1000 palabras) + agente activo
+ mensajes_recientes (últimos 5 pares pregunta/respuesta verbatim).
"""
from .config import get_local_conn


def obtener_o_crear(usuario_id: str, canal: str, conversacion_id: int = None,
                    nombre_usuario: str = None) -> dict:
    """
    Busca la conversación activa.
    - Si viene conversacion_id: busca por id.
    - Si no: busca por (usuario_id, canal), toma la más reciente.
    - Si no existe: crea una nueva.

    Returns: fila de ia_conversaciones como dict
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            if conversacion_id:
                cur.execute(
                    "SELECT * FROM ia_conversaciones WHERE id = %s",
                    (conversacion_id,)
                )
            else:
                cur.execute(
                    "SELECT * FROM ia_conversaciones WHERE usuario_id = %s AND canal = %s "
                    "ORDER BY updated_at DESC LIMIT 1",
                    (usuario_id, canal)
                )
            row = cur.fetchone()

            if row:
                # Actualizar nombre si cambió
                if nombre_usuario and row.get('nombre_usuario') != nombre_usuario:
                    cur.execute(
                        "UPDATE ia_conversaciones SET nombre_usuario = %s WHERE id = %s",
                        (nombre_usuario, row['id'])
                    )
                    row['nombre_usuario'] = nombre_usuario
                return row

            # Crear nueva conversación
            cur.execute(
                "INSERT INTO ia_conversaciones (usuario_id, canal, nombre_usuario) VALUES (%s, %s, %s)",
                (usuario_id, canal, nombre_usuario)
            )
            cur.execute("SELECT * FROM ia_conversaciones WHERE id = LAST_INSERT_ID()")
            return cur.fetchone()
    finally:
        conn.close()


def guardar_resumen(conversacion_id: int, resumen: str):
    """Actualiza el resumen de contexto de la conversación."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_conversaciones SET resumen = %s WHERE id = %s",
                (resumen[:6000], conversacion_id)  # tope de seguridad ~1000 palabras
            )
    finally:
        conn.close()


def cambiar_agente(conversacion_id: int, agente_slug: str):
    """Cambia el agente activo de la conversación (comando /agente)."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_conversaciones SET agente_activo = %s WHERE id = %s",
                (agente_slug, conversacion_id)
            )
    finally:
        conn.close()


def resetear(conversacion_id: int):
    """Borra el resumen, mensajes recientes y caché SQL — reinicia la conversación."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_conversaciones SET resumen = NULL, mensajes_recientes = '[]', metadata = NULL "
                "WHERE id = %s",
                (conversacion_id,)
            )
    finally:
        conn.close()


def guardar_cache_sql(conversacion_id: int, pregunta: str, columnas: list, datos: list):
    """
    Guarda el último resultado SQL exitoso en metadata.
    El router lo usa para decidir si la siguiente pregunta necesita SQL nuevo.
    """
    import json as _json
    MAX_FILAS = 500  # suficiente para seguimientos; evita metadata gigante
    cache = {
        'ultimo_sql': {
            'pregunta': pregunta[:300],
            'columnas': columnas,
            'datos':    datos[:MAX_FILAS],
            'n_filas':  len(datos),
        }
    }
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_conversaciones SET metadata = %s WHERE id = %s",
                (_json.dumps(cache, ensure_ascii=False, default=str), conversacion_id)
            )
            conn.commit()
    finally:
        conn.close()


def leer_cache_sql(conv: dict) -> dict | None:
    """
    Lee el caché SQL de la conversación.
    Retorna dict con {pregunta, columnas, datos, n_filas} o None si no hay.
    """
    import json as _json
    raw = conv.get('metadata')
    if not raw:
        return None
    try:
        meta = _json.loads(raw) if isinstance(raw, str) else raw
        return meta.get('ultimo_sql')
    except Exception:
        return None


def guardar_mensajes_recientes(conversacion_id: int, pregunta: str, respuesta: str, max_pares: int = 5):
    """
    Agrega el par pregunta/respuesta al historial reciente verbatim.
    Rota automáticamente: mantiene solo los últimos max_pares.
    Se llama DESPUÉS de cada consulta exitosa.
    """
    import json as _json
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mensajes_recientes FROM ia_conversaciones WHERE id = %s",
                (conversacion_id,)
            )
            row = cur.fetchone()
            if not row:
                return

            try:
                mensajes = _json.loads(row['mensajes_recientes'] or '[]')
            except Exception:
                mensajes = []

            mensajes.append({
                'pregunta':  pregunta[:1000],
                'respuesta': respuesta[:2000],
            })

            if len(mensajes) > max_pares:
                mensajes = mensajes[-max_pares:]

            cur.execute(
                "UPDATE ia_conversaciones SET mensajes_recientes = %s WHERE id = %s",
                (_json.dumps(mensajes, ensure_ascii=False), conversacion_id)
            )
            conn.commit()
    finally:
        conn.close()


def obtener_mensajes_recientes_formateados(conversacion: dict) -> str:
    """
    Convierte mensajes_recientes (JSON) en texto para el system prompt.
    Retorna string vacío si no hay historial.
    """
    import json as _json
    raw = conversacion.get('mensajes_recientes')
    if not raw:
        return ''
    try:
        mensajes = _json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return ''
    if not mensajes:
        return ''

    partes = ['## Últimos intercambios de esta conversación (verbatim):\n']
    for i, m in enumerate(mensajes, 1):
        partes.append(f"**Pregunta {i}:** {m.get('pregunta', '')}")
        partes.append(f"**Respuesta {i}:** {m.get('respuesta', '')}\n")
    return '\n'.join(partes)
