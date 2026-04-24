"""
scripts/lib/db_conn.py — Helper único de conexiones a BD (Python)
Lee credenciales de `integracion_conexionesbd.env` en la raíz del repo.

Uso con context manager (recomendado):
    from lib.db_conn import local, integracion, gestion, comunidad

    with local('effi_data') as conn:
        cur = conn.cursor()
        cur.execute('SELECT 1')

    with integracion(dict_cursor=True) as conn:
        ...

Uso con dicts raw (para scripts legados que quieren armar la conexión manual):
    from lib.db_conn import cfg_local, cfg_remota_ssh, cfg_remota_db

Mismos drivers que ya se usan: pymysql, sshtunnel.
"""
import os
import sys
from pathlib import Path
from contextlib import contextmanager

import pymysql
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

# ─── Cargar .env central (raíz del repo) ─────────────────────────────
_RAIZ_REPO = Path(__file__).resolve().parents[2]
_ENV_PATH  = _RAIZ_REPO / 'integracion_conexionesbd.env'
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    print(f'[db_conn] WARN: {_ENV_PATH} no existe', file=sys.stderr)

TIMEZONE = os.getenv('DB_TIMEZONE', '-05:00')


# ─── Config readers ──────────────────────────────────────────────────
def cfg_local():
    """Dict con host/port/user/password del MariaDB local (sin database)."""
    return dict(
        host=os.getenv('DB_LOCAL_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_LOCAL_PORT', 3306)),
        user=os.getenv('DB_LOCAL_USER'),
        password=os.getenv('DB_LOCAL_PASS'),
    )


def cfg_remota_ssh(prefijo):
    """Config SSH para una BD remota. prefijo ∈ {INTEGRACION, GESTION, INVENTARIO, COMUNIDAD}."""
    P = prefijo.upper()
    return dict(
        host=os.getenv(f'DB_{P}_SSH_HOST'),
        port=int(os.getenv(f'DB_{P}_SSH_PORT', 22)),
        user=os.getenv(f'DB_{P}_SSH_USER'),
        key=os.path.expanduser(os.getenv(f'DB_{P}_SSH_KEY', '')),
        remote_host=os.getenv(f'DB_{P}_REMOTE_HOST', '127.0.0.1'),
        remote_port=int(os.getenv(f'DB_{P}_REMOTE_PORT', 3306)),
    )


def cfg_remota_db(prefijo):
    """Dict user/password/database listo para pymysql/mysql.connector (sin host/port)."""
    P = prefijo.upper()
    return dict(
        user=os.getenv(f'DB_{P}_USER'),
        password=os.getenv(f'DB_{P}_PASS'),
        database=os.getenv(f'DB_{P}_NAME'),
        charset='utf8mb4',
    )


# ─── Tuneles SSH compartidos (por prefijo) ───────────────────────────
_tuneles = {}  # prefijo → SSHTunnelForwarder activo


def _es_local(prefijo):
    """Detecta si la BD remota es realmente local (mismo servidor). Salta SSH tunnel."""
    h = (os.getenv(f'DB_{prefijo.upper()}_SSH_HOST', '') or '').lower()
    return h in ('localhost', '127.0.0.1', '', 'direct')


def abrir_tunel(prefijo):
    """Abre (o reusa) un SSHTunnelForwarder para el prefijo dado. Retorna el tunel.

    Si DB_<prefijo>_SSH_HOST es localhost/127.0.0.1/direct, retorna None: el caller
    debe conectar directo al MariaDB local sin pasar por tunnel."""
    P = prefijo.upper()
    if _es_local(P):
        return None
    if P in _tuneles and _tuneles[P].is_active:
        return _tuneles[P]
    s = cfg_remota_ssh(P)
    t = SSHTunnelForwarder(
        (s['host'], s['port']),
        ssh_username=s['user'],
        ssh_pkey=s['key'],
        remote_bind_address=(s['remote_host'], s['remote_port']),
    )
    t.start()
    _tuneles[P] = t
    return t


def cerrar_tuneles():
    """Cierra todos los tuneles activos. Útil al final de scripts de una sola pasada."""
    for t in _tuneles.values():
        try:
            t.stop()
        except Exception:
            pass
    _tuneles.clear()


# ─── Context managers (API principal) ────────────────────────────────
def _conectar(kwargs, dict_cursor):
    k = dict(kwargs)
    k.setdefault('charset', 'utf8mb4')
    k.setdefault('autocommit', True)
    if dict_cursor:
        k['cursorclass'] = pymysql.cursors.DictCursor
    return pymysql.connect(init_command=f"SET time_zone = '{TIMEZONE}'", **k)


@contextmanager
def local(db_name, dict_cursor=False):
    """Conexión a una BD del MariaDB local. Uso: with local('effi_data') as conn:"""
    conn = _conectar(dict(cfg_local(), database=db_name), dict_cursor)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def remota(prefijo, dict_cursor=False):
    """Conexión a una BD remota. prefijo ∈ {INTEGRACION, GESTION, INVENTARIO, COMUNIDAD}.

    Usa SSH tunnel salvo que DB_<prefijo>_SSH_HOST sea localhost/127.0.0.1/direct,
    en cuyo caso conecta directo al MariaDB del mismo servidor."""
    tunel = abrir_tunel(prefijo)
    db = cfg_remota_db(prefijo)
    ssh = cfg_remota_ssh(prefijo)
    if tunel is None:
        host = ssh['remote_host']
        port = ssh['remote_port']
    else:
        host = '127.0.0.1'
        port = tunel.local_bind_port
    kwargs = dict(
        host=host, port=port,
        user=db['user'], password=db['password'], database=db['database'],
        connect_timeout=15, read_timeout=30,
    )
    conn = _conectar(kwargs, dict_cursor)
    try:
        yield conn
    finally:
        conn.close()


def integracion(dict_cursor=False): return remota('INTEGRACION', dict_cursor)
def gestion(dict_cursor=False):     return remota('GESTION',     dict_cursor)
def inventario(dict_cursor=False):  return remota('INVENTARIO',  dict_cursor)
def comunidad(dict_cursor=False):   return remota('COMUNIDAD',   dict_cursor)


# ─── cfg_inventario(): dict listo para pymysql.connect con tunnel SSH abierto ───
# Útil para scripts heredados que hacen pymysql.connect(**DB_INV) estilo dict.
# Abre el tunnel 1 vez por proceso y reusa.
def cfg_inventario(dict_cursor=True):
    """Retorna dict compatible con pymysql.connect(**).
    Abre tunnel SSH al VPS si no está abierto, conecta al puerto local forwardeado.
    """
    return _cfg_remota_dict('INVENTARIO', dict_cursor)


def cfg_integracion(dict_cursor=True):
    """Retorna dict compatible con pymysql.connect(**) para os_integracion en VPS.
    Abre tunnel SSH al VPS si no está abierto, conecta al puerto local forwardeado.

    USAR PARA: scripts/apps de inventario, producción, gestión, ERP que necesiten
    consultar tablas zeffi_* (OPs, materiales, artículos, recetas, costos) o
    resumen_ventas_*. NUNCA usar cfg_local()+'effi_data' para esto — effi_data
    local es solo intermediaria del pipeline (ver MANIFESTO §8).
    """
    return _cfg_remota_dict('INTEGRACION', dict_cursor)


def _cfg_remota_dict(prefijo, dict_cursor):
    t = abrir_tunel(prefijo)
    db = cfg_remota_db(prefijo)
    cfg = {
        'host': '127.0.0.1',
        'port': t.local_bind_port if t else db['remote_port'],
        'user': db['user'],
        'password': db['password'],
        'database': db['database'],
        'charset': 'utf8mb4',
        'autocommit': True,
        'connect_timeout': 15,
    }
    if dict_cursor:
        cfg['cursorclass'] = pymysql.cursors.DictCursor
    return cfg
