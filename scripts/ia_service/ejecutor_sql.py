"""
Ejecutor SQL seguro contra BDs externas configuradas en ia_conexiones_bd.
Solo permite SELECT. Devuelve filas como lista de dicts.
"""
import re
from .config import get_local_conn, get_hostinger_conn

MAX_FILAS = 500

_PROHIBIDAS = re.compile(
    r'\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b',
    re.IGNORECASE
)


def _validar_sql(sql: str) -> str | None:
    """Devuelve mensaje de error si el SQL no es seguro, None si es válido."""
    sql_clean = sql.strip()
    if not sql_clean.upper().startswith('SELECT'):
        return 'Solo se permiten consultas SELECT.'
    if _PROHIBIDAS.search(sql_clean):
        return 'SQL contiene palabras no permitidas.'
    return None


def ejecutar(sql: str, conexion_id: int = None) -> dict:
    """
    Ejecuta un SELECT contra la BD configurada.

    Args:
        sql:          Consulta SQL generada por el LLM.
        conexion_id:  ID de ia_conexiones_bd. None = usa Hostinger legacy.

    Returns:
        {ok, filas, columnas, total, truncado, error}
    """
    sql = sql.strip()
    error = _validar_sql(sql)
    if error:
        return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                'truncado': False, 'error': error}

    conn = None
    try:
        if conexion_id:
            from .conector import get_conexion, get_conexion_externa
            cfg = get_conexion(conexion_id)
            if not cfg:
                return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                        'truncado': False, 'error': 'Conexión no encontrada.'}
            conn = get_conexion_externa(cfg)
        else:
            # Fallback legacy: Hostinger directo
            conn = get_hostinger_conn()

        with conn.cursor() as cur:
            cur.execute(sql)
            filas = cur.fetchmany(MAX_FILAS + 1)
            truncado = len(filas) > MAX_FILAS
            filas = filas[:MAX_FILAS]
            columnas = [d[0] for d in cur.description] if cur.description else []

        return {
            'ok':      True,
            'filas':   filas,
            'columnas': columnas,
            'total':   len(filas),
            'truncado': truncado,
            'error':   None,
        }

    except Exception as e:
        return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                'truncado': False, 'error': str(e)}
    finally:
        if conn:
            conn.close()
