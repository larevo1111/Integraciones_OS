"""
Manejo del contexto de conversación.
Lee y escribe ia_conversaciones: resumen vivo (≤1000 palabras) + agente activo.
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
    """Borra el resumen y reinicia la conversación."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_conversaciones SET resumen = NULL WHERE id = %s",
                (conversacion_id,)
            )
    finally:
        conn.close()
