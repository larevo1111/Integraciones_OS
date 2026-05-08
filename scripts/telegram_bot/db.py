"""
Gestión de sesiones y autenticación de usuarios del bot en ia_service_os.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ia_service.config import get_local_conn


# ── Autenticación ─────────────────────────────────────────────────────────────

def verificar_por_telefono(telefono: str) -> dict | None:
    """
    Busca un usuario en ia_usuarios por teléfono.
    Retorna el registro o None si no está autorizado.
    El teléfono debe incluir prefijo país: +573214550933
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, nombre, nivel, activo FROM ia_usuarios "
                "WHERE telefono = %s AND activo = 1",
                (telefono,)
            )
            return cur.fetchone()
    finally:
        conn.close()


def vincular_telegram_id(telefono: str, telegram_id: int):
    """Guarda el telegram_id en ia_usuarios tras verificación exitosa."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_usuarios SET telegram_id = %s WHERE telefono = %s",
                (telegram_id, telefono)
            )
            conn.commit()
    finally:
        conn.close()


def verificar_por_telegram_id(telegram_id: int) -> dict | None:
    """
    Verificación rápida por telegram_id (ya vinculado).
    Evita pedir el teléfono en cada sesión.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, nombre, nivel, activo FROM ia_usuarios "
                "WHERE telegram_id = %s AND activo = 1",
                (telegram_id,)
            )
            return cur.fetchone()
    finally:
        conn.close()


# ── Sesiones ──────────────────────────────────────────────────────────────────

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
                   empresa: str = 'ori_sil_2', autorizado: int = None,
                   nivel: int = None):
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bot_sesiones
                  (telegram_user_id, username, nombre, conversacion_id,
                   agente_preferido, empresa, autorizado, nivel)
                VALUES (%s, %s, %s, %s, %s, %s,
                        COALESCE(%s, 0), COALESCE(%s, 1))
                ON DUPLICATE KEY UPDATE
                  username         = VALUES(username),
                  nombre           = VALUES(nombre),
                  conversacion_id  = COALESCE(VALUES(conversacion_id), conversacion_id),
                  agente_preferido = COALESCE(VALUES(agente_preferido), agente_preferido),
                  empresa          = VALUES(empresa),
                  autorizado       = COALESCE(VALUES(autorizado), autorizado),
                  nivel            = COALESCE(VALUES(nivel), nivel),
                  updated_at       = NOW()
            """, (telegram_user_id, username, nombre, conversacion_id,
                  agente_preferido, empresa, autorizado, nivel))
            conn.commit()
    finally:
        conn.close()


# ── Tablas temporales ─────────────────────────────────────────────────────────

def guardar_tabla_temp(token: str, pregunta: str, columnas: list,
                       filas: list, empresa: str = 'ori_sil_2'):
    import json
    cols_json = json.dumps(columnas)
    filas_json = json.dumps(filas)
    sql = """
        INSERT INTO bot_tablas_temp (token, empresa, pregunta, columnas, filas)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE filas=VALUES(filas), created_at=NOW()
    """
    params = (token, empresa, pregunta, cols_json, filas_json)

    # 1) Guardar en local (ia_service_os) — fuente de verdad para el bot
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
    finally:
        conn.close()

    # 2) Replicar al VPS (os_integracion) — necesario para el ERP en VPS
    # Si falla, NO romper el flujo del bot — solo loggear.
    try:
        from lib import integracion
        with integracion() as conn_vps:
            with conn_vps.cursor() as cur:
                cur.execute(sql, params)
                conn_vps.commit()
    except Exception as e:
        print(f'[bot_tablas_temp] WARN: no se pudo replicar al VPS: {e}', flush=True)


def limpiar_tablas_viejas():
    """Borrar tablas temporales de más de 24h."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bot_tablas_temp WHERE created_at < NOW() - INTERVAL 24 HOUR")
            conn.commit()
    finally:
        conn.close()
