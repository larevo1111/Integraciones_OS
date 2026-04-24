"""
grupo_helper.py — Detecta compatibilidad de productos para programarlos en una sola OP.

Regla de compatibilidad: dos productos son compatibles si comparten la **materia prima
a granel principal**. Para detectarlo:

1. Para cada cod_articulo, identificar cuál es su MP granel principal:
   - Buscar en sus OPs históricas el material que más kg/litros consume (no envases, no etiquetas)
   - Tomar el más frecuente
2. Comparar: si todos los productos del grupo apuntan al mismo cod_material granel → compatibles.

Ejemplos:
- Crema Maní 500g + 230g + 130g → todos usan cod 151 (CREMA DE MANI X KILO) → ✅
- Miel 640g + 1000g + 275g → todos usan cod 373 (MIEL FILTRADA) → ✅
- Crema Maní 500g + Miel 640g → cod 151 vs cod 373 → ❌ NO compatibles

Cache simple en memoria por proceso (60 seg de TTL).
"""
import os
import sys
import time
from typing import Optional
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_integracion

# os_integracion VPS — ver MANIFESTO §8
DB_EFFI = cfg_integracion(dict_cursor=True)

_CACHE = {}  # cod_articulo -> (mp_granel_cod, ts)
_TTL = 60.0


def _q(sql, params=None):
    conn = pymysql.connect(**DB_EFFI)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def mp_granel_principal(cod_articulo: str) -> Optional[dict]:
    """Identifica la MP granel principal de un producto.

    Heurística:
    - Trae las últimas 5 OPs vigentes donde el producto aparece.
    - De los materiales consumidos, descarta envases/etiquetas/tapas (por nombre).
    - Calcula el material que más se consume en kg/L (cantidad acumulada).
    - Devuelve el material con mayor consumo total: {'cod', 'nombre'}.

    Devuelve None si no hay OPs históricas.
    """
    now = time.time()
    cached = _CACHE.get(cod_articulo)
    if cached and now - cached[1] < _TTL:
        return cached[0]

    # Paso 1: últimas 5 OPs vigentes del producto
    ops_rows = _q("""
        SELECT DISTINCT ap.id_orden
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia = 'Orden vigente'
          AND e.vigencia = 'Vigente'
        ORDER BY CAST(ap.id_orden AS UNSIGNED) DESC
        LIMIT 5
    """, (cod_articulo,))
    ops_ids = [r['id_orden'] for r in ops_rows]
    if not ops_ids:
        _CACHE[cod_articulo] = (None, now)
        return None

    # Paso 2: materiales de esas OPs
    placeholders = ','.join(['%s'] * len(ops_ids))
    rows = _q(f"""
        SELECT m.cod_material AS cod, m.descripcion_material AS nombre,
               CAST(REPLACE(m.cantidad, ',', '.') AS DECIMAL(15,4)) AS cantidad
        FROM zeffi_materiales m
        WHERE m.id_orden IN ({placeholders})
          AND m.vigencia = 'Orden vigente'
    """, tuple(ops_ids))

    if not rows:
        _CACHE[cod_articulo] = (None, now)
        return None

    # Filtrar materiales que NO sean envases, etiquetas, tapas, bolsas, cajas, moldes
    PALABRAS_NO_GRANEL = ('ENVASE', 'ETIQUETA', 'TAPA', 'BOLSA', 'CAJA', 'MOLDE',
                          'CARTÓN', 'CARTON', 'CINTA', 'PRECINTO', 'STICKER')

    granel = {}
    for r in rows:
        nombre_up = (r['nombre'] or '').upper()
        if any(p in nombre_up for p in PALABRAS_NO_GRANEL):
            continue
        cod = r['cod']
        granel[cod] = granel.get(cod, {'cod': cod, 'nombre': r['nombre'], 'cantidad': 0})
        granel[cod]['cantidad'] += float(r['cantidad'] or 0)

    if not granel:
        _CACHE[cod_articulo] = (None, now)
        return None

    # El material granel más consumido
    mp = max(granel.values(), key=lambda x: x['cantidad'])
    resultado = {'cod': mp['cod'], 'nombre': mp['nombre'],
                 'cantidad_acumulada': round(mp['cantidad'], 4)}
    _CACHE[cod_articulo] = (resultado, now)
    return resultado


def evaluar_compatibilidad(cods_articulos: list) -> dict:
    """Evalúa si una lista de productos pueden programarse en una sola OP.

    Retorna:
    {
      'compatible': True/False,
      'mp_granel_comun': cod o None,
      'productos': [{'cod', 'mp_granel': {'cod','nombre'}, ...}],
      'razon': str
    }
    """
    if not cods_articulos:
        return {'compatible': False, 'razon': 'Lista vacía'}

    productos = []
    granel_set = set()
    for cod in cods_articulos:
        mp = mp_granel_principal(cod)
        productos.append({'cod': cod, 'mp_granel': mp})
        if mp:
            granel_set.add(mp['cod'])
        else:
            granel_set.add(None)

    # Si hay más de 1 granel distinto → no compatibles
    if len(granel_set) == 1 and None not in granel_set:
        cod_granel = next(iter(granel_set))
        return {
            'compatible': True,
            'mp_granel_comun': cod_granel,
            'productos': productos,
            'razon': f'Todos los productos comparten la misma MP granel: {cod_granel}',
        }
    if None in granel_set:
        return {
            'compatible': False,
            'mp_granel_comun': None,
            'productos': productos,
            'razon': 'Al menos un producto no tiene MP granel identificable (sin OPs históricas)',
        }
    return {
        'compatible': False,
        'mp_granel_comun': None,
        'productos': productos,
        'razon': f'Los productos tienen MP granel distintos: {sorted(granel_set)}',
    }
