"""
Ejecutor SQL seguro contra Hostinger (tablas analíticas).
Solo permite SELECT. Devuelve filas como lista de dicts.
"""
import re
from .config import get_hostinger_conn

# Máximo de filas a devolver (evita respuestas masivas)
MAX_FILAS = 500

# Palabras clave peligrosas que nunca deben aparecer en un SQL generado por IA
_PROHIBIDAS = re.compile(
    r'\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b',
    re.IGNORECASE
)


def ejecutar(sql: str) -> dict:
    """
    Ejecuta un SELECT contra Hostinger.

    Returns:
        {
            "ok": bool,
            "filas": list[dict],
            "columnas": list[str],
            "total": int,
            "truncado": bool,  # True si había más de MAX_FILAS
            "error": str|None
        }
    """
    sql = sql.strip()

    # Seguridad: solo SELECT
    if not sql.upper().startswith('SELECT'):
        return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                'truncado': False, 'error': 'Solo se permiten consultas SELECT.'}

    if _PROHIBIDAS.search(sql):
        return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                'truncado': False, 'error': 'SQL contiene palabras no permitidas.'}

    conn = None
    try:
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            cur.execute(sql)
            filas = cur.fetchmany(MAX_FILAS + 1)
            truncado = len(filas) > MAX_FILAS
            filas = filas[:MAX_FILAS]
            columnas = [d[0] for d in cur.description] if cur.description else []

        return {
            'ok':       True,
            'filas':    filas,
            'columnas': columnas,
            'total':    len(filas),
            'truncado': truncado,
            'error':    None,
        }

    except Exception as e:
        return {'ok': False, 'filas': [], 'columnas': [], 'total': 0,
                'truncado': False, 'error': str(e)}
    finally:
        if conn:
            conn.close()
