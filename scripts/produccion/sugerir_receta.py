#!/usr/bin/env python3
"""
Sugiere la receta de una OP basándose en OPs históricas del mismo artículo.

Algoritmo:
1. Buscar últimas N OPs vigentes donde el artículo aparece como producido.
2. Para cada OP, normalizar materiales/costos por unidad producida (ratio).
3. Detectar el patrón: escalable (ratios consistentes) o lote fijo (materiales absolutos consistentes).
4. Detectar y descartar OPs outlier usando MAD (Median Absolute Deviation).
5. Calcular receta sugerida usando la mediana de las OPs limpias.
6. Reportar nivel de confianza.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local
import pymysql
from statistics import median
from typing import Optional


DB_EFFI = dict(**cfg_local(), database='effi_data', cursorclass=pymysql.cursors.DictCursor)


def to_float(v) -> float:
    if v is None: return 0.0
    return float(str(v).replace(',', '.'))


def q(sql, params=None):
    conn = pymysql.connect(**DB_EFFI)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def obtener_ops_articulo(cod_articulo: str, n: int = 10) -> list:
    """Trae últimas N OPs vigentes donde el artículo aparece como producido."""
    return q("""
        SELECT DISTINCT ap.id_orden, LEFT(e.fecha_de_creacion, 19) AS fecha,
               e.id_encargado AS encargado_cc, e.nombre_encargado
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia = 'Orden vigente'
          AND e.vigencia = 'Vigente'
        ORDER BY CAST(ap.id_orden AS UNSIGNED) DESC
        LIMIT %s
    """, (cod_articulo, n))


def obtener_detalle_op(id_orden: str) -> dict:
    """Trae producidos, materiales y costos de una OP."""
    producidos = q("""
        SELECT cod_articulo AS cod, descripcion_articulo_producido AS nombre, cantidad
        FROM zeffi_articulos_producidos
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
    """, (id_orden,))
    materiales = q("""
        SELECT cod_material AS cod, descripcion_material AS nombre, cantidad
        FROM zeffi_materiales
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
    """, (id_orden,))
    costos = q("""
        SELECT costo_de_produccion AS cp, cantidad, costo_ud
        FROM zeffi_otros_costos
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
    """, (id_orden,))
    return {'producidos': producidos, 'materiales': materiales, 'costos': costos}


def detectar_outliers_mad(valores: list, threshold: float = 3.0) -> tuple:
    """Devuelve (limpios, outliers) usando Median Absolute Deviation."""
    if len(valores) < 3:
        return valores, []
    med = median(valores)
    deviations = [abs(v - med) for v in valores]
    mad = median(deviations)
    if mad == 0:
        # Todos iguales o casi: cualquier desviación es outlier
        return [v for v in valores if v == med], [v for v in valores if v != med]
    limpios = [v for v in valores if abs(v - med) <= threshold * mad]
    outliers = [v for v in valores if abs(v - med) > threshold * mad]
    return limpios, outliers


def coef_variacion(valores: list) -> float:
    """CV = stddev / media. Si es bajo, los valores son consistentes."""
    if not valores or len(valores) < 2:
        return 0.0
    m = sum(valores) / len(valores)
    if m == 0:
        return 0.0
    var = sum((v - m) ** 2 for v in valores) / len(valores)
    return (var ** 0.5) / abs(m)


def sugerir_receta(cod_articulo: str, cantidad: float, n_ops: int = 10) -> dict:
    """
    Sugiere receta para producir `cantidad` del artículo `cod_articulo`.

    Devuelve:
    {
      'cod_articulo': str,
      'cantidad_solicitada': float,
      'patron': 'escalable' | 'lote_fijo' | 'lote_fijo_multiple' | 'sin_historia',
      'cantidad_lote_estandar': float | None,  # solo si es lote fijo
      'n_lotes': int | None,                    # solo si es lote fijo
      'cantidad_efectiva': float,               # cantidad real que producirá la receta
      'ops_analizadas': int,
      'ops_outlier_descartadas': [id_op...],
      'confianza': 'alta' | 'media' | 'baja',
      'co_productos': [...],
      'materiales': [{cod, desc, cantidad, costo_unit, ratio_unit, n_ops_aparece}],
      'costos': [{cp, cantidad, costo_ud}],
      'observaciones': [str],  # info adicional
      'ops_referencia': [id_op...]
    }
    """
    ops = obtener_ops_articulo(cod_articulo, n_ops)
    if not ops:
        return {
            'cod_articulo': cod_articulo,
            'cantidad_solicitada': cantidad,
            'patron': 'sin_historia',
            'confianza': 'baja',
            'observaciones': ['Sin OPs históricas vigentes para este artículo'],
            'materiales': [], 'costos': [], 'co_productos': [],
            'ops_analizadas': 0, 'ops_outlier_descartadas': [], 'ops_referencia': [],
        }

    # 1. Recopilar detalle de cada OP
    recetas = []
    for op in ops:
        detalle = obtener_detalle_op(op['id_orden'])
        # Cantidad producida del NUESTRO artículo
        nuestra = sum(to_float(p['cantidad']) for p in detalle['producidos'] if p['cod'] == cod_articulo)
        if nuestra <= 0:
            continue
        # Otros productos (excepto desperdicios, que se identifican por nombre)
        otros_prod = [p for p in detalle['producidos']
                      if p['cod'] != cod_articulo
                      and not (p['nombre'] or '').upper().startswith('DESPER')]
        es_mixta = len(otros_prod) > 0
        recetas.append({
            'op_id': op['id_orden'], 'fecha': op['fecha'],
            'cant_producida': nuestra,
            'producidos': detalle['producidos'],
            'materiales': detalle['materiales'],
            'costos': detalle['costos'],
            'es_mixta': es_mixta,
            'otros_prod': otros_prod,
        })

    if not recetas:
        return {
            'cod_articulo': cod_articulo, 'cantidad_solicitada': cantidad,
            'patron': 'sin_historia', 'confianza': 'baja',
            'observaciones': ['OPs encontradas pero sin cantidad producida válida'],
            'materiales': [], 'costos': [], 'co_productos': [],
            'ops_analizadas': 0, 'ops_outlier_descartadas': [], 'ops_referencia': [],
        }

    # 2. PRIORIZAR OPs no mixtas. Threshold bajado a 1 (antes 3) — siempre que haya
    # al menos 1 pura, esa es más confiable que las mixtas.
    no_mixtas = [r for r in recetas if not r['es_mixta']]
    if len(no_mixtas) >= 1:
        recetas_uso = no_mixtas
        nota_mixtas = f'Usando {len(no_mixtas)} OPs puras (excluidas {len(recetas) - len(no_mixtas)} mixtas con co-productos)'
    else:
        recetas_uso = recetas
        nota_mixtas = 'Sin OPs puras — usando OPs mixtas (precisión limitada por materiales compartidos)'

    # 2.b Detectar OPs "incompletas": faltan materiales que aparecen en la mayoría
    # Ejemplo: OP de prueba sin cobertura cuando todas las demás la tienen
    if len(recetas_uso) >= 3:
        # Materiales que aparecen en >=70% de las OPs candidatas
        mat_count = {}
        for r in recetas_uso:
            for m in r['materiales']:
                mat_count[m['cod']] = mat_count.get(m['cod'], 0) + 1
        threshold = len(recetas_uso) * 0.7
        materiales_comunes = {cod for cod, n in mat_count.items() if n >= threshold}
        # Filtrar OPs que tengan al menos 80% de los materiales comunes
        recetas_completas = []
        descartadas_incompletas = []
        for r in recetas_uso:
            mats_op = {m['cod'] for m in r['materiales']}
            comunes_presentes = materiales_comunes & mats_op
            if len(comunes_presentes) >= len(materiales_comunes) * 0.8:
                recetas_completas.append(r)
            else:
                descartadas_incompletas.append(r['op_id'])
        if len(recetas_completas) >= 2 and descartadas_incompletas:
            recetas_uso = recetas_completas

    # 3. DETECCIÓN DE PATRÓN: lote fijo vs escalable
    # Para cada material, ver si:
    # - cantidades absolutas son ~iguales (CV bajo) → posible lote fijo
    # - ratios material/producido son ~iguales (CV bajo) → escalable
    todos_materiales = {}
    for r in recetas_uso:
        for m in r['materiales']:
            cod = m['cod']
            if cod not in todos_materiales:
                todos_materiales[cod] = {'desc': m['nombre'], 'absolutos': [], 'ratios': [], 'ops': []}
            cant = to_float(m['cantidad'])
            todos_materiales[cod]['absolutos'].append(cant)
            todos_materiales[cod]['ratios'].append(cant / r['cant_producida'])
            todos_materiales[cod]['ops'].append(r['op_id'])

    # Cantidad producida también
    cantidades_producidas = [r['cant_producida'] for r in recetas_uso]
    cv_producido = coef_variacion(cantidades_producidas)

    # Por cada material, calcular CVs
    cv_absolutos_por_mat = []
    cv_ratios_por_mat = []
    for cod, info in todos_materiales.items():
        if len(info['absolutos']) >= 2:
            cv_absolutos_por_mat.append(coef_variacion(info['absolutos']))
            cv_ratios_por_mat.append(coef_variacion(info['ratios']))

    # Determinar patrón
    cv_abs_avg = sum(cv_absolutos_por_mat) / len(cv_absolutos_por_mat) if cv_absolutos_por_mat else 0
    cv_rat_avg = sum(cv_ratios_por_mat) / len(cv_ratios_por_mat) if cv_ratios_por_mat else 0

    es_lote_fijo = (cv_abs_avg < 0.10 and cv_producido < 0.20) or (cv_abs_avg < cv_rat_avg * 0.5 and cv_abs_avg < 0.15)
    patron = 'lote_fijo' if es_lote_fijo else 'escalable'

    # 4. CALCULAR RECETA SUGERIDA
    materiales_sugeridos = []
    ops_outlier_set = set()
    observaciones = []

    if es_lote_fijo:
        # Cantidad estándar de lote = mediana de cant_producida
        cant_lote_std = median(cantidades_producidas)
        # Cuántos lotes necesitamos
        n_lotes = max(1, round(cantidad / cant_lote_std + 0.4999))  # redondeo al alza
        cant_efectiva = n_lotes * cant_lote_std

        for cod, info in todos_materiales.items():
            absolutos = info['absolutos']
            limpios, outliers = detectar_outliers_mad(absolutos)
            for v, op_id in zip(absolutos, info['ops']):
                if v in outliers and op_id:
                    ops_outlier_set.add(op_id)
            if not limpios:
                continue
            # Solo incluir si aparece en >=50% de las OPs
            if len(limpios) < len(recetas_uso) * 0.5:
                observaciones.append(f'Material {cod} aparece solo en {len(limpios)}/{len(recetas_uso)} OPs — descartado')
                continue
            cant_por_lote = median(limpios)
            materiales_sugeridos.append({
                'cod': cod, 'desc': info['desc'],
                'cantidad': round(cant_por_lote * n_lotes, 4),
                'ratio_unit': round(cant_por_lote / cant_lote_std, 6),
                'n_ops_aparece': len(limpios),
            })
    else:
        # Escalable: usar mediana de ratios × cantidad solicitada
        cant_efectiva = cantidad
        n_lotes = None
        cant_lote_std = None

        for cod, info in todos_materiales.items():
            ratios = info['ratios']
            limpios, outliers = detectar_outliers_mad(ratios)
            for v, op_id in zip(ratios, info['ops']):
                if v in outliers and op_id:
                    ops_outlier_set.add(op_id)
            if not limpios:
                continue
            if len(limpios) < len(recetas_uso) * 0.5:
                observaciones.append(f'Material {cod} aparece solo en {len(limpios)}/{len(recetas_uso)} OPs — descartado')
                continue
            ratio_final = median(limpios)
            materiales_sugeridos.append({
                'cod': cod, 'desc': info['desc'],
                'cantidad': round(ratio_final * cantidad, 4),
                'ratio_unit': round(ratio_final, 6),
                'n_ops_aparece': len(limpios),
            })

    # 5. COSTOS DE PRODUCCIÓN (M.O. etc)
    todos_costos = {}
    for r in recetas_uso:
        for c in r['costos']:
            key = c['cp']
            if key not in todos_costos:
                todos_costos[key] = {'cp': c['cp'], 'cantidades': [], 'ratios': [], 'costo_ud': []}
            cant_costo = to_float(c['cantidad'])
            todos_costos[key]['cantidades'].append(cant_costo)
            todos_costos[key]['ratios'].append(cant_costo / r['cant_producida'])
            todos_costos[key]['costo_ud'].append(to_float(c['costo_ud']))

    costos_sugeridos = []
    for cp, info in todos_costos.items():
        if len(info['cantidades']) < len(recetas_uso) * 0.5:
            continue
        if es_lote_fijo:
            limpios, _ = detectar_outliers_mad(info['cantidades'])
            cant = median(limpios) * n_lotes if limpios else 0
        else:
            limpios, _ = detectar_outliers_mad(info['ratios'])
            cant = median(limpios) * cantidad if limpios else 0
        costos_sugeridos.append({
            'cp': cp,
            'cantidad': round(cant, 4),
            'costo_ud': median(info['costo_ud']) if info['costo_ud'] else 0,
        })

    # 6. CO-PRODUCTOS (productos secundarios consistentes)
    co_productos_count = {}
    for r in recetas_uso:
        for op in r['otros_prod']:
            cod = op['cod']
            cant = to_float(op['cantidad'])
            if cod not in co_productos_count:
                co_productos_count[cod] = {'desc': op['nombre'], 'cantidades': [], 'ratios': []}
            co_productos_count[cod]['cantidades'].append(cant)
            co_productos_count[cod]['ratios'].append(cant / r['cant_producida'])

    co_productos = []
    for cod, info in co_productos_count.items():
        if len(info['cantidades']) >= len(recetas_uso) * 0.6:  # umbral mayor para co-prods
            if es_lote_fijo:
                cant = median(info['cantidades']) * n_lotes
            else:
                cant = median(info['ratios']) * cantidad
            co_productos.append({
                'cod': cod, 'desc': info['desc'],
                'cantidad': round(cant, 4),
                'n_ops_aparece': len(info['cantidades']),
            })

    # 7. CONFIANZA
    n_total = len(recetas_uso)
    n_outliers = len(ops_outlier_set)
    if n_total >= 4 and cv_rat_avg < 0.15:
        confianza = 'alta'
    elif n_total >= 3 and cv_rat_avg < 0.30:
        confianza = 'media'
    else:
        confianza = 'baja'

    # Ajustes a observaciones
    if nota_mixtas:
        observaciones.append(nota_mixtas)
    if n_outliers > 0:
        observaciones.append(f'{n_outliers} OPs descartadas como outliers: {sorted(ops_outlier_set)}')
    if es_lote_fijo:
        observaciones.append(f'Patrón lote fijo: cada lote produce ~{cant_lote_std} unid. Sugiero {n_lotes} lote(s) → {cant_efectiva} unid totales')

    return {
        'cod_articulo': cod_articulo,
        'cantidad_solicitada': cantidad,
        'patron': patron,
        'cantidad_lote_estandar': cant_lote_std,
        'n_lotes': n_lotes,
        'cantidad_efectiva': cant_efectiva,
        'ops_analizadas': len(recetas),
        'ops_efectivas': len(recetas_uso),
        'ops_outlier_descartadas': sorted(ops_outlier_set),
        'cv_absolutos': round(cv_abs_avg, 4),
        'cv_ratios': round(cv_rat_avg, 4),
        'confianza': confianza,
        'co_productos': sorted(co_productos, key=lambda x: -x['cantidad']),
        'materiales': sorted(materiales_sugeridos, key=lambda x: -x['cantidad']),
        'costos': costos_sugeridos,
        'observaciones': observaciones,
        'ops_referencia': [r['op_id'] for r in recetas_uso],
    }


if __name__ == '__main__':
    import json
    if len(sys.argv) < 3:
        print('Uso: python3 sugerir_receta.py <cod_articulo> <cantidad> [n_ops]')
        sys.exit(1)
    cod = sys.argv[1]
    cant = float(sys.argv[2])
    n_ops = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    resultado = sugerir_receta(cod, cant, n_ops)
    print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))
