#!/usr/bin/env python3
"""Variante de sugerir_receta que ATRIBUYE materiales al producto principal
cuando la OP es multi-producto.

Heurística:
- Si una OP tiene 1 solo producido → todos los materiales son de ese.
- Si una OP tiene N producidos:
  - Por cada material con cantidad C:
    - Si C coincide con cantidad del principal (±5%) → 100% al principal.
    - Si C coincide con cantidad de OTRO producido (±5%) → 0% al principal (es de otro).
    - Si C = suma(cant_producidos) → distribuir por share.
    - Si no coincide con ninguno → distribuir por share.
- Los producidos "hermanos" del principal NO se cuentan como co-productos.
"""
from statistics import median
from typing import Optional

from _common import q_effi, to_float, FECHA_INICIO_UNIVERSO


TOL_MATCH = 0.05  # 5% para considerar que una cantidad "coincide" con otra

# Ingredientes específicos — si están en el nombre de un material, ese material
# "pertenece" al producido que tenga ese token. Orden importa (más específico primero).
INGREDIENTES_ESPECIFICOS = [
    'macadamia', 'almendra', 'propoleo', 'vainilla', 'panela',
    'mani', 'nibs', 'polen', 'miel', 'cacao', 'chocomiel',
    'jabon', 'jengibre', 'menta', 'pasteuri',
]


def tokens_especificos(nombre: str):
    n = (nombre or '').lower()
    return {t for t in INGREDIENTES_ESPECIFICOS if t in n}


def obtener_ops_articulo(cod_articulo: str, n: int = 10):
    return q_effi(
        """
        SELECT DISTINCT ap.id_orden, LEFT(e.fecha_de_creacion, 19) AS fecha
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia='Orden vigente' AND e.vigencia='Vigente'
          AND e.fecha_de_creacion >= %s
        ORDER BY e.fecha_de_creacion DESC
        LIMIT %s
        """,
        (cod_articulo, FECHA_INICIO_UNIVERSO, n),
    )


def obtener_detalle_op(id_orden: str) -> dict:
    producidos = q_effi(
        """SELECT cod_articulo AS cod, descripcion_articulo_producido AS nombre,
                  cantidad, precio_minimo_ud AS precio
             FROM zeffi_articulos_producidos
             WHERE id_orden=%s AND vigencia='Orden vigente'""",
        (id_orden,),
    )
    materiales = q_effi(
        """SELECT cod_material AS cod, descripcion_material AS nombre,
                  cantidad, costo_ud AS costo
             FROM zeffi_materiales
             WHERE id_orden=%s AND vigencia='Orden vigente'""",
        (id_orden,),
    )
    costos = q_effi(
        """SELECT costo_de_produccion AS cp, cantidad, costo_ud
             FROM zeffi_otros_costos
             WHERE id_orden=%s AND vigencia='Orden vigente'""",
        (id_orden,),
    )
    return {'producidos': producidos, 'materiales': materiales, 'costos': costos}


def atribuir(detalle: dict, cod_principal: str, nombre_principal: str = ''):
    """Devuelve (materiales_atribuidos, costos_atribuidos, cant_principal).
    Descarta producidos hermanos (no los cuenta como co-productos).

    Reglas de atribución de cada material:
    1. Afinidad semántica: si el material tiene tokens específicos (mani, macadamia…)
       que NO están en el nombre del principal pero sí en el de otro producido → descartar.
    2. Match por cantidad exacta (±5%) con el principal → 100% al principal.
    3. Match por cantidad con OTRO producido → 0% al principal.
    4. Sin match: distribuir por share (cant_principal / cant_total).
    """
    prods = [{'cod': p['cod'], 'cant': to_float(p['cantidad']),
              'nombre': p.get('nombre', '')} for p in detalle['producidos']]
    cant_principal = sum(p['cant'] for p in prods if p['cod'] == cod_principal)
    cant_total = sum(p['cant'] for p in prods)
    if cant_total <= 0 or cant_principal <= 0:
        return [], [], 0.0

    share = cant_principal / cant_total

    otros = [p for p in prods if p['cod'] != cod_principal and p['cant'] > 0]
    tokens_principal = tokens_especificos(nombre_principal)

    atribuidos_m = []
    for m in detalle['materiales']:
        cant_m = to_float(m['cantidad'])
        tk_m = tokens_especificos(m['nombre'])

        # 1. Afinidad semántica: si el material tiene tokens que NO están en el principal
        #    pero sí están en SOLO algún otro producido → descartar (es de otro).
        if tk_m and not (tk_m & tokens_principal):
            afines_otros = [p for p in otros if tk_m & tokens_especificos(p['nombre'])]
            if afines_otros:
                continue  # el material es de otro producido

        # 2. Match cantidad exacta principal
        if abs(cant_m - cant_principal) / max(cant_principal, 1e-6) < TOL_MATCH:
            atribuidos_m.append({
                'cod': m['cod'], 'nombre': m['nombre'],
                'cantidad': cant_m, 'costo': to_float(m['costo']),
                'atribucion': 'match_cantidad',
            })
            continue

        # 3. Match cantidad de otro producido (y el principal no coincide)
        coincide_otro = any(
            abs(cant_m - o['cant']) / max(o['cant'], 1e-6) < TOL_MATCH for o in otros
        )
        if coincide_otro:
            continue

        # 4. Share
        atribuidos_m.append({
            'cod': m['cod'], 'nombre': m['nombre'],
            'cantidad': cant_m * share, 'costo': to_float(m['costo']),
            'atribucion': f'share_{share:.3f}',
        })

    # Costos (siempre proporcional al share — el M.O. se reparte)
    atribuidos_c = []
    for c in detalle['costos']:
        cant_c = to_float(c['cantidad'])
        atribuidos_c.append({
            'cp': c['cp'],
            'cantidad': cant_c * share,
            'costo_ud': to_float(c['costo_ud']),
            'atribucion': f'share_{share:.3f}',
        })

    return atribuidos_m, atribuidos_c, cant_principal


def coef_variacion(valores):
    if not valores or len(valores) < 2:
        return 0.0
    m = sum(valores) / len(valores)
    if m == 0:
        return 0.0
    var = sum((v - m) ** 2 for v in valores) / len(valores)
    return (var ** 0.5) / abs(m)


def detectar_outliers_mad(valores, threshold=3.0):
    if len(valores) < 3:
        return valores, []
    med = median(valores)
    deviations = [abs(v - med) for v in valores]
    mad = median(deviations)
    if mad == 0:
        return [v for v in valores if v == med], [v for v in valores if v != med]
    limpios = [v for v in valores if abs(v - med) <= threshold * mad]
    outliers = [v for v in valores if abs(v - med) > threshold * mad]
    return limpios, outliers


def sugerir_atribuido(cod_articulo: str, cantidad: float = 1.0, n_ops: int = 10) -> dict:
    """Sugiere receta con atribución multi-producto."""
    ops = obtener_ops_articulo(cod_articulo, n_ops)
    if not ops:
        return {
            'cod_articulo': cod_articulo, 'cantidad_solicitada': cantidad,
            'patron': 'sin_historia', 'confianza': 'baja',
            'materiales': [], 'productos': [], 'costos': [],
            'ops_referencia': [], 'ops_analizadas': 0,
            'observaciones': ['Sin OPs históricas'],
        }

    # Nombre del principal para afinidad semántica
    nombre_ppal_r = q_effi(
        "SELECT nombre FROM zeffi_inventario WHERE id=%s LIMIT 1", (cod_articulo,)
    )
    nombre_ppal = nombre_ppal_r[0]['nombre'] if nombre_ppal_r else ''

    # Recopilar datos atribuidos
    registros = []  # list of {op_id, cant_prod, materiales[], costos[]}
    for op in ops:
        det = obtener_detalle_op(op['id_orden'])
        mats, cs, cant = atribuir(det, cod_articulo, nombre_ppal)
        if cant <= 0:
            continue
        registros.append({
            'op_id': op['id_orden'], 'fecha': op['fecha'],
            'cant_prod': cant, 'materiales': mats, 'costos': cs,
        })

    if not registros:
        return {
            'cod_articulo': cod_articulo, 'cantidad_solicitada': cantidad,
            'patron': 'sin_historia', 'confianza': 'baja',
            'materiales': [], 'productos': [], 'costos': [],
            'ops_referencia': [], 'ops_analizadas': 0,
            'observaciones': ['OPs sin producción válida del artículo'],
        }

    # Detectar patrón
    cantidades_prod = [r['cant_prod'] for r in registros]
    cv_prod = coef_variacion(cantidades_prod)

    # Agrupar materiales por cod
    mats_agg = {}
    for r in registros:
        for m in r['materiales']:
            mats_agg.setdefault(m['cod'], {'nombre': m['nombre'], 'absolutos': [], 'ratios': [], 'costos': [], 'ops': []})
            mats_agg[m['cod']]['absolutos'].append(m['cantidad'])
            mats_agg[m['cod']]['ratios'].append(m['cantidad'] / r['cant_prod'])
            mats_agg[m['cod']]['costos'].append(m['costo'])
            mats_agg[m['cod']]['ops'].append(r['op_id'])

    # CV medio de ratios y absolutos
    cv_abs_list = [coef_variacion(v['absolutos']) for v in mats_agg.values() if len(v['absolutos']) >= 2]
    cv_rat_list = [coef_variacion(v['ratios']) for v in mats_agg.values() if len(v['ratios']) >= 2]
    cv_abs_avg = sum(cv_abs_list) / len(cv_abs_list) if cv_abs_list else 0
    cv_rat_avg = sum(cv_rat_list) / len(cv_rat_list) if cv_rat_list else 0

    es_lote_fijo = (cv_abs_avg < 0.10 and cv_prod < 0.20) or (cv_abs_avg < cv_rat_avg * 0.5 and cv_abs_avg < 0.15)
    patron = 'lote_fijo' if es_lote_fijo else 'escalable'

    # Calcular receta sugerida
    materiales_sugeridos = []
    outliers_set = set()

    if es_lote_fijo:
        cant_lote_std = median(cantidades_prod)
        n_lotes = max(1, round(cantidad / cant_lote_std + 0.4999))
        cant_efectiva = n_lotes * cant_lote_std

        for cod, info in mats_agg.items():
            limpios, outs = detectar_outliers_mad(info['absolutos'])
            for v, op_id in zip(info['absolutos'], info['ops']):
                if v in outs:
                    outliers_set.add(op_id)
            if not limpios or len(limpios) < len(registros) * 0.5:
                continue
            cant_lote = median(limpios)
            materiales_sugeridos.append({
                'cod': cod, 'nombre': info['nombre'],
                'cantidad': round(cant_lote * n_lotes, 4),
                'ratio': round(cant_lote / cant_lote_std, 6),
                'costo': median(info['costos']) if info['costos'] else 0,
                'n_ops': len(limpios),
            })
    else:
        cant_efectiva = cantidad
        n_lotes = None
        cant_lote_std = None

        for cod, info in mats_agg.items():
            limpios_r, outs_r = detectar_outliers_mad(info['ratios'])
            for v, op_id in zip(info['ratios'], info['ops']):
                if v in outs_r:
                    outliers_set.add(op_id)
            if not limpios_r or len(limpios_r) < len(registros) * 0.5:
                continue
            ratio = median(limpios_r)
            materiales_sugeridos.append({
                'cod': cod, 'nombre': info['nombre'],
                'cantidad': round(ratio * cantidad, 4),
                'ratio': round(ratio, 6),
                'costo': median(info['costos']) if info['costos'] else 0,
                'n_ops': len(limpios_r),
            })

    # Costos de producción
    costos_agg = {}
    for r in registros:
        for c in r['costos']:
            k = c['cp']
            costos_agg.setdefault(k, {'cantidades': [], 'ratios': [], 'costos_ud': []})
            costos_agg[k]['cantidades'].append(c['cantidad'])
            costos_agg[k]['ratios'].append(c['cantidad'] / r['cant_prod'])
            costos_agg[k]['costos_ud'].append(c['costo_ud'])

    costos_sugeridos = []
    for cp, info in costos_agg.items():
        if len(info['cantidades']) < len(registros) * 0.5:
            continue
        if es_lote_fijo:
            limpios, _ = detectar_outliers_mad(info['cantidades'])
            cant = median(limpios) * n_lotes if limpios else 0
        else:
            limpios, _ = detectar_outliers_mad(info['ratios'])
            cant = median(limpios) * cantidad if limpios else 0
        costos_sugeridos.append({
            'cp': cp, 'cantidad': round(cant, 4),
            'costo_ud': median(info['costos_ud']) if info['costos_ud'] else 0,
        })

    # Confianza
    n_total = len(registros)
    if n_total >= 4 and cv_rat_avg < 0.15:
        confianza = 'alta'
    elif n_total >= 3 and cv_rat_avg < 0.30:
        confianza = 'media'
    else:
        confianza = 'baja'

    observaciones = []
    n_mixtas = sum(1 for r in registros if len([p for p in obtener_detalle_op(r['op_id'])['producidos']]) > 1)
    if n_mixtas:
        observaciones.append(f'{n_mixtas}/{n_total} OPs fueron multi-producto — materiales atribuidos por cantidad/share')
    if outliers_set:
        observaciones.append(f'{len(outliers_set)} OPs descartadas outlier: {sorted(outliers_set)}')

    materiales_sugeridos.sort(key=lambda x: -x['cantidad'])

    return {
        'cod_articulo': cod_articulo, 'cantidad_solicitada': cantidad,
        'patron': patron, 'cantidad_lote_estandar': cant_lote_std,
        'cantidad_efectiva': cant_efectiva, 'n_lotes': n_lotes,
        'confianza': confianza,
        'materiales': materiales_sugeridos,
        'costos': costos_sugeridos,
        'ops_referencia': [r['op_id'] for r in registros],
        'ops_outlier_descartadas': sorted(outliers_set),
        'ops_analizadas': len(registros),
        'cv_ratios': round(cv_rat_avg, 4),
        'cv_absolutos': round(cv_abs_avg, 4),
        'observaciones': observaciones,
    }


if __name__ == '__main__':
    import json
    import sys
    if len(sys.argv) < 2:
        print('Uso: python3 sugerir_atribuido.py <cod> [cantidad] [n_ops]')
        sys.exit(1)
    cod = sys.argv[1]
    cant = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    print(json.dumps(sugerir_atribuido(cod, cant, n), indent=2, default=str, ensure_ascii=False))
