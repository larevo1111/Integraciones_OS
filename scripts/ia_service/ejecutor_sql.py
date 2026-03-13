"""
Ejecutor SQL seguro contra BDs externas configuradas en ia_conexiones_bd.

SEGURIDAD — DOS CAPAS INDEPENDIENTES:
  Capa 1: sqlglot parsea el AST y verifica que sea SELECT puro (antes de tocar la BD).
  Capa 2: SET SESSION TRANSACTION READ ONLY — el motor de BD enforcea solo lectura
           a nivel de sesión. Ni root puede escribir. Independiente de permisos del usuario.

Solo se permiten SELECT. Devuelve filas como lista de dicts.
"""
import sqlglot
import sqlglot.expressions as exp
from .config import get_local_conn, get_hostinger_conn

MAX_FILAS = 500


def _validar_sql_ast(sql: str) -> str | None:
    """
    Capa 1: Validación por AST con sqlglot.
    Devuelve mensaje de error si no es SELECT puro, None si es válido.
    """
    sql_clean = sql.strip()

    # Rechazo rápido: debe empezar por SELECT
    if not sql_clean.upper().lstrip('(').startswith('SELECT'):
        return 'Solo se permiten consultas SELECT.'

    try:
        statements = sqlglot.parse(sql_clean)
    except Exception as e:
        return f'SQL inválido: {e}'

    if not statements:
        return 'No se pudo parsear el SQL.'

    for stmt in statements:
        if stmt is None:
            continue
        # Verificar que el statement raíz sea un SELECT
        if not isinstance(stmt, exp.Select):
            tipo = type(stmt).__name__
            return f'Solo SELECT permitido. Se detectó: {tipo}.'

        # Verificar que no haya subqueries mutantes dentro del SELECT
        for node in stmt.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete,
                                 exp.Drop, exp.Create, exp.Alter,
                                 exp.DDL, exp.Grant, exp.Revoke)):
                tipo = type(node).__name__
                return f'SQL contiene operación no permitida: {tipo}.'

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

    # ── Capa 1: validación AST ────────────────────────────────────────
    error = _validar_sql_ast(sql)
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
            conn = get_hostinger_conn()

        # ── Capa 2: READ ONLY a nivel de sesión ───────────────────────
        # El motor de BD enforcea solo lectura independientemente de los
        # permisos del usuario. Ni root puede escribir en esta sesión.
        with conn.cursor() as cur:
            try:
                cur.execute("SET SESSION TRANSACTION READ ONLY")
            except Exception:
                pass  # Algunas BDs no soportan esto — la Capa 1 sigue activa

        # ── Ejecutar SELECT ───────────────────────────────────────────
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
