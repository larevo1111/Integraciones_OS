"""Helpers compartidos del libro de recetas."""
import os
import re
import sys

# scripts/ al path
_SCRIPTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pymysql
from lib import cfg_integracion  # type: ignore
from lib.db_conn import cfg_inventario  # type: ignore


FECHA_INICIO_UNIVERSO = '2025-01-01 00:00:00'


# ─── Familias ────────────────────────────────────────────────────────────
FAMILIAS = [
    ('coberturas',  r'(cobertura|manteca de cacao)'),
    ('tabletas',    r'tableta'),
    ('propoleo',    r'propoleo'),
    ('polen',       r'polen'),
    ('mieles',      r'(miel|chocomiel)'),
    ('cremas_mani', r'(crema de mani|crema mani)'),
    ('chocolates',  r'chocolate'),
    ('cacao_nibs',  r'(nibs|cacao|licor)'),
    ('infusiones',  r'infusion'),
]


def familia_por_nombre(nombre: str) -> str:
    n = (nombre or '').lower()
    for fam, rx in FAMILIAS:
        if re.search(rx, n):
            return fam
    return 'otros'


# ─── Conexión os_integracion VPS (lectura de OPs y catálogos) ─────────────
# effi_data local es solo intermediaria del pipeline. Ver MANIFESTO §8.
def db_effi():
    return pymysql.connect(**cfg_integracion(dict_cursor=True))


def q_effi(sql: str, params=None):
    conn = db_effi()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


# ─── Conexión VPS inventario_produccion_effi (recetas) ───────────────────
class DbRecetas:
    """Context manager para la BD de recetas (VPS via SSH tunnel compartido)."""

    def __init__(self, dict_cursor=True):
        self.dict_cursor = dict_cursor
        self._conn = None

    def __enter__(self):
        self._conn = pymysql.connect(**cfg_inventario(dict_cursor=self.dict_cursor))
        return self._conn

    def __exit__(self, *args):
        if self._conn:
            self._conn.close()


# ─── Utilidades ──────────────────────────────────────────────────────────
def to_float(v) -> float:
    if v is None:
        return 0.0
    return float(str(v).replace(',', '.'))


# Extraer peso/volumen del nombre (640g, 1000gr, 250cc, 150 grs, etc.)
_RX_PESO = re.compile(
    r'(?P<num>\d+(?:[\.,]\d+)?)\s*(?P<unit>grs?|gramos?|gr|g|kg|kilos?|cc|ml|l|litro)',
    re.IGNORECASE,
)


def peso_desde_nombre(nombre: str):
    """Devuelve (valor_en_gramos_o_ml, unit_original) o None si no se puede."""
    if not nombre:
        return None
    m = _RX_PESO.search(nombre)
    if not m:
        return None
    num = float(m.group('num').replace(',', '.'))
    unit = m.group('unit').lower().rstrip('s')
    if unit in ('gr', 'g', 'grs', 'gramo'):
        return (num, 'g')
    if unit in ('kg', 'kilo'):
        return (num * 1000, 'g')
    if unit in ('cc', 'ml'):
        return (num, 'ml')
    if unit in ('l', 'litro'):
        return (num * 1000, 'ml')
    return None
