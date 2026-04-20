"""
Configuración central del servicio de IA.
Lee credenciales del .env central (integracion_conexionesbd.env).
"""
import os
import sys
import pymysql
from dotenv import load_dotenv

# Cargar scripts/.env (GEMINI_API_KEY, GROQ_API_KEY, etc.)
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE, '.env'))

# Helper central de BD
sys.path.insert(0, _BASE)
from lib import cfg_local, cfg_remota_ssh, cfg_remota_db

_local = cfg_local()
DB_HOST = _local['host']
DB_PORT = _local['port']
DB_USER = _local['user']
DB_PASS = _local['password']
DB_IA   = 'ia_service_os'

# Conexión a "integración" (conexión directa al puerto MySQL público,
# misma IP que el SSH host). Si en el futuro el servidor no expone MySQL
# directamente, cambiar a SSH tunnel via lib.remota('INTEGRACION').
_ssh_i = cfg_remota_ssh('INTEGRACION')
_db_i  = cfg_remota_db('INTEGRACION')
HOSTINGER_HOST = _ssh_i['host']
HOSTINGER_PORT = 3306
HOSTINGER_USER = _db_i['user']
HOSTINGER_PASS = _db_i['password']
HOSTINGER_DB   = _db_i['database']


def get_local_conn():
    """Conexión a ia_service_os en MariaDB local."""
    return pymysql.connect(
        **_local, database=DB_IA,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def get_hostinger_conn():
    """Conexión directa a integración MySQL (sin SSH tunnel)."""
    return pymysql.connect(
        host=HOSTINGER_HOST, port=HOSTINGER_PORT,
        user=HOSTINGER_USER, password=HOSTINGER_PASS,
        database=HOSTINGER_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
        read_timeout=30
    )
