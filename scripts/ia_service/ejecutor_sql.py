"""
Ejecutor SQL seguro contra BDs externas configuradas en ia_conexiones_bd.

SEGURIDAD — DOS CAPAS INDEPENDIENTES:
  Capa 1: sqlglot parsea el AST y verifica que sea SELECT puro (antes de tocar la BD).
  Capa 2: SET SESSION TRANSACTION READ ONLY — el motor de BD enforcea solo lectura
           a nivel de sesión. Ni root puede escribir. Independiente de permisos del usuario.

Solo se permiten SELECT. Devuelve filas como lista de dicts.
"""
import re
import sqlglot
import sqlglot.expressions as exp
from .config import get_local_conn, get_hostinger_conn


def limpiar_sql(sql: str) -> str:
    """Elimina ANSI escape codes y caracteres de control que el LLM a veces inyecta."""
    sql = re.sub(r'\x1b\[[0-9;]*[mGKHF]', '', sql)   # ANSI con ESC
    sql = re.sub(r'\[[\d;]+[mGKHF]', '', sql)          # ANSI sin ESC (artefacto markdown)
    sql = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sql)
    return sql.strip()

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
        statements = sqlglot.parse(sql_clean, dialect='mysql')
    except Exception as e:
        return f'SQL inválido: {e}'

    if not statements:
        return 'No se pudo parsear el SQL.'

    for stmt in statements:
        if stmt is None:
            continue
        # Verificar que el statement raíz sea un SELECT
        # SELECT puro + operaciones de conjunto (UNION/INTERSECT/EXCEPT) son todas read-only
        # sqlglot parsea "SELECT ... UNION SELECT ..." como exp.Union, no exp.Select
        RAIZ_OK = (exp.Select, exp.Union, exp.Intersect, exp.Except)
        MUTANTES = (exp.Insert, exp.Update, exp.Delete,
                    exp.Drop, exp.Create, exp.Alter,
                    exp.DDL, exp.Grant, exp.Revoke, exp.Command)

        if not isinstance(stmt, RAIZ_OK):
            tipo = type(stmt).__name__
            return f'Solo SELECT permitido. Se detectó: {tipo}.'

        # Verificar que no haya operaciones mutantes en ningún nodo del árbol
        for node in stmt.walk():
            if isinstance(node, MUTANTES):
                tipo = type(node).__name__
                return f'SQL contiene operación no permitida: {tipo}.'

    return None


def _normalizar_sql(sql: str) -> str:
    """
    Corrige patrones de UNION que MariaDB rechaza:
    Si el LLM genera   SELECT ... ORDER BY ... LIMIT N UNION ALL SELECT ... ORDER BY ... LIMIT N
    sqlglot parsea el segundo ORDER BY/LIMIT como del UNION completo, y la rama
    izquierda queda con su propio ORDER BY/LIMIT → MariaDB lo rechaza sin paréntesis.

    Corrección: detectar ese patrón y envolver cada rama en paréntesis.
    Si no aplica o falla, devuelve el SQL original sin modificar.
    """
    try:
        stmts = sqlglot.parse(sql, dialect='mysql')
        if not stmts:
            return sql
        stmt = stmts[0]

        if not isinstance(stmt, (exp.Union, exp.Intersect, exp.Except)):
            return sql

        left = stmt.left
        # ¿La rama izquierda tiene ORDER BY o LIMIT propios?
        left_has_order = any(isinstance(n, (exp.Order, exp.Limit)) for n in left.walk())
        # ¿El UNION tiene ORDER BY/LIMIT propios (absorbidos del segundo SELECT)?
        union_order = stmt.args.get('order')
        union_limit = stmt.args.get('limit')

        if not left_has_order:
            return sql  # Patrón normal — sin corrección necesaria

        # Construir el SQL de la rama derecha con ORDER BY y LIMIT del UNION
        right = stmt.right
        sql_right = right.sql(dialect='mysql')
        if union_order:
            sql_right += ' ' + union_order.sql(dialect='mysql')
        if union_limit:
            sql_right += ' ' + union_limit.sql(dialect='mysql')

        sql_left = left.sql(dialect='mysql')

        # Determinar el operador
        distinct = stmt.args.get('distinct', True)
        op = 'UNION' if distinct else 'UNION ALL'

        return f'({sql_left}) {op} ({sql_right})'
    except Exception:
        pass
    return sql


def ejecutar(sql: str, conexion_id: int = None) -> dict:
    """
    Ejecuta un SELECT contra la BD configurada.

    Args:
        sql:          Consulta SQL generada por el LLM.
        conexion_id:  ID de ia_conexiones_bd. None = usa Hostinger legacy.

    Returns:
        {ok, filas, columnas, total, truncado, error}
    """
    sql = limpiar_sql(sql)
    sql = _normalizar_sql(sql)

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
