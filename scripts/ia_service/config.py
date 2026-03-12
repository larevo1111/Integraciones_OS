"""
Configuración central del servicio de IA.
Lee .env y credenciales de BD.
"""
import os
import pymysql
from dotenv import load_dotenv

# Cargar .env desde scripts/
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE, '.env'))

# ── BD local ia_service_os ────────────────────────────────────────────
DB_HOST     = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT     = int(os.getenv('DB_PORT', 3306))
DB_USER     = os.getenv('DB_USER', 'osadmin')
DB_PASS     = os.getenv('DB_PASS', 'Epist2487.')
DB_IA       = 'ia_service_os'

# ── BD Hostinger (para ejecutar SQL analítico) ────────────────────────
HOSTINGER_HOST = os.getenv('HOSTINGER_HOST', '109.106.250.195')
HOSTINGER_PORT = int(os.getenv('HOSTINGER_PORT', 3306))
HOSTINGER_USER = os.getenv('HOSTINGER_USER', 'u768061575_osserver')
HOSTINGER_PASS = os.getenv('HOSTINGER_PASS', 'Epist2487.')
HOSTINGER_DB   = os.getenv('HOSTINGER_DB',   'u768061575_os_integracion')


def get_local_conn():
    """Conexión a ia_service_os en MariaDB local."""
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_IA,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def get_hostinger_conn():
    """Conexión directa a Hostinger MySQL (sin SSH tunnel, acceso externo)."""
    return pymysql.connect(
        host=HOSTINGER_HOST, port=HOSTINGER_PORT,
        user=HOSTINGER_USER, password=HOSTINGER_PASS,
        database=HOSTINGER_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
        read_timeout=30
    )
