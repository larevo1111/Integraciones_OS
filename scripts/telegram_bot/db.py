"""
Gestión de sesiones de usuarios del bot en ia_service_os.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn


def obtener_sesion(telegram_user_id: int) -> dict:
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bot_sesiones WHERE telegram_user_id = %s",
                (telegram_user_id,)
            )
            return cur.fetchone() or {}
    finally:
        conn.close()


def guardar_sesion(telegram_user_id: int, username: str, nombre: str,
                   conversacion_id: int = None, agente_preferido: str = None,
                   empresa: str = 'ori_sil_2'):
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bot_sesiones
                  (telegram_user_id, username, nombre, conversacion_id, agente_preferido, empresa)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  username         = VALUES(username),
                  nombre           = VALUES(nombre),
                  conversacion_id  = COALESCE(VALUES(conversacion_id), conversacion_id),
                  agente_preferido = COALESCE(VALUES(agente_preferido), agente_preferido),
                  empresa          = VALUES(empresa),
                  updated_at       = NOW()
            """, (telegram_user_id, username, nombre, conversacion_id, agente_preferido, empresa))
            conn.commit()
    finally:
        conn.close()


def guardar_tabla_temp(token: str, pregunta: str, columnas: list,
                       filas: list, empresa: str = 'ori_sil_2'):
    import json
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bot_tablas_temp (token, empresa, pregunta, columnas, filas)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE filas=VALUES(filas), created_at=NOW()
            """, (token, empresa, pregunta, json.dumps(columnas), json.dumps(filas)))
            conn.commit()
    finally:
        conn.close()


def limpiar_tablas_viejas():
    """Borrar tablas temporales de más de 24h."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bot_tablas_temp WHERE created_at < NOW() - INTERVAL 24 HOUR")
            conn.commit()
    finally:
        conn.close()
