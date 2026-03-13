"""
Módulo de conexiones a bases de datos externas.
Lee credenciales de ia_conexiones_bd y genera schema automático (SHOW COLUMNS).
Soporta: mariadb, mysql, postgresql.
"""
import json
import time
import pymysql
import pymysql.cursors
from .config import get_local_conn

# Caché por conexion_id: {id: {'schema': str, 'ts': float}}
_cache_schema = {}
_CACHE_TTL = 3600  # 1 hora


def get_conexion(conexion_id: int) -> dict | None:
    """Carga config de una conexión desde ia_conexiones_bd."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ia_conexiones_bd WHERE id = %s AND activo = 1",
                (conexion_id,)
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_conexion_externa(cfg: dict):
    """Abre conexión a la BD externa según tipo."""
    tipo = cfg.get('tipo', 'mariadb')
    if tipo in ('mysql', 'mariadb'):
        return pymysql.connect(
            host=cfg['host'],
            port=int(cfg['puerto']),
            user=cfg['usuario'],
            password=cfg['password'],
            database=cfg['base_datos'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=15,
            read_timeout=30
        )
    elif tipo == 'postgresql':
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(
            host=cfg['host'],
            port=int(cfg['puerto']),
            user=cfg['usuario'],
            password=cfg['password'],
            dbname=cfg['base_datos'],
            connect_timeout=15
        )
    else:
        raise ValueError(f"Tipo de BD no soportado: {tipo}")


def test_conexion(conexion_id: int) -> dict:
    """
    Prueba una conexión. Devuelve {ok, mensaje, tablas_disponibles}.
    """
    cfg = get_conexion(conexion_id)
    if not cfg:
        return {'ok': False, 'mensaje': 'Conexión no encontrada o inactiva.'}
    conn_ext = None
    try:
        conn_ext = get_conexion_externa(cfg)
        tipo = cfg.get('tipo', 'mariadb')
        with conn_ext.cursor() as cur:
            if tipo in ('mysql', 'mariadb'):
                cur.execute("SHOW TABLES")
                filas = cur.fetchall()
                tablas = [list(f.values())[0] for f in filas]
            else:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                )
                tablas = [r['table_name'] for r in cur.fetchall()]
        return {
            'ok': True,
            'mensaje': f'Conexión exitosa. {len(tablas)} tablas disponibles.',
            'tablas_disponibles': tablas
        }
    except Exception as e:
        return {'ok': False, 'mensaje': str(e), 'tablas_disponibles': []}
    finally:
        if conn_ext:
            conn_ext.close()


def generar_schema(conexion_id: int, tablas: list) -> str:
    """
    Lee SHOW COLUMNS de cada tabla y genera schema legible para la IA.
    Formato: tabla: nombre_tabla\n  campo TIPO\n  ...
    """
    cfg = get_conexion(conexion_id)
    if not cfg:
        return '-- Conexión no disponible\n'

    conn_ext = None
    partes = []
    tipo = cfg.get('tipo', 'mariadb')

    try:
        conn_ext = get_conexion_externa(cfg)
        with conn_ext.cursor() as cur:
            for tabla in tablas:
                try:
                    if tipo in ('mysql', 'mariadb'):
                        cur.execute(f"SHOW COLUMNS FROM `{tabla}`")
                        cols = cur.fetchall()
                        lineas = [f"  {c['Field']} {c['Type']}" for c in cols]
                    else:
                        cur.execute(
                            "SELECT column_name, data_type FROM information_schema.columns "
                            "WHERE table_name = %s ORDER BY ordinal_position",
                            (tabla,)
                        )
                        cols = cur.fetchall()
                        lineas = [f"  {c['column_name']} {c['data_type']}" for c in cols]

                    partes.append(f"tabla: {tabla}\n" + "\n".join(lineas))
                except Exception as e:
                    partes.append(f"tabla: {tabla}\n  -- no disponible: {e}")
    except Exception as e:
        return f'-- Error conectando: {e}\n'
    finally:
        if conn_ext:
            conn_ext.close()

    return "\n\n".join(partes)


def sincronizar_schema(tema_id: int, empresa: str) -> dict:
    """
    Lee ia_esquemas para el tema, regenera ddl_auto desde la BD externa
    y lo guarda en ia_esquemas.ddl_auto. Devuelve {ok, mensaje, schema}.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ia_esquemas WHERE tema_id = %s AND empresa = %s AND activo = 1",
                (tema_id, empresa)
            )
            esquema = cur.fetchone()

        if not esquema:
            return {'ok': False, 'mensaje': 'No hay esquema configurado para este tema.'}

        tablas = json.loads(esquema.get('tablas_incluidas') or '[]')
        if not tablas:
            return {'ok': True, 'mensaje': 'Este tema no tiene tablas configuradas (solo RAG).', 'schema': ''}

        ddl = generar_schema(esquema['conexion_id'], tablas)

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_esquemas SET ddl_auto = %s, ultima_sync = NOW() WHERE id = %s",
                (ddl, esquema['id'])
            )

        # Limpiar caché
        _cache_schema.pop(tema_id, None)

        return {'ok': True, 'mensaje': f'Schema sincronizado. {len(tablas)} tablas.', 'schema': ddl}
    except Exception as e:
        return {'ok': False, 'mensaje': str(e)}
    finally:
        conn.close()


def obtener_schema_tema(tema_id: int, empresa: str) -> str:
    """
    Devuelve el schema completo para un tema (ddl_auto + notas_manuales).
    Usa caché de 1 hora. Si no hay ddl_auto, sincroniza automáticamente.
    """
    ahora = time.time()
    cached = _cache_schema.get(tema_id)
    if cached and (ahora - cached['ts']) < _CACHE_TTL:
        return cached['schema']

    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ia_esquemas WHERE tema_id = %s AND empresa = %s AND activo = 1",
                (tema_id, empresa)
            )
            esquema = cur.fetchone()

        if not esquema:
            return ''

        ddl = esquema.get('ddl_auto') or ''
        notas = esquema.get('notas_manuales') or ''

        # Si no tiene ddl_auto todavía, sincronizar ahora
        if not ddl:
            resultado = sincronizar_schema(tema_id, empresa)
            ddl = resultado.get('schema', '')

        partes = []
        if ddl:
            partes.append(ddl)
        if notas:
            partes.append(f"\nNOTAS DE NEGOCIO:\n{notas}")

        schema_completo = "\n".join(partes)
        _cache_schema[tema_id] = {'schema': schema_completo, 'ts': ahora}
        return schema_completo

    finally:
        conn.close()
