"""
analisis_inconsistencias.py — Motor de análisis de inconsistencias de inventario.

Capa 1: Reglas deterministas (Python puro, sin IA)
Capa 2: Análisis IA (OpenCode qwen3.6 o Ollama qwen2.5:7b)

Uso desde api.py:
    from inventario.analisis_inconsistencias import analizar_articulo, analizar_todos
"""

import re
import json
import subprocess
import sys
import os
import pymysql
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local, cfg_inventario
DB_EFFI = dict(**cfg_local(), database='effi_data')
DB_INV  = cfg_inventario(dict_cursor=False)

CAUSAS = {
    'FALTA_FACTURAR': 'Faltó remisionar o facturar',
    'OP_NO_EJECUTADA': 'OP no ejecutada',
    'ERROR_UNIDAD_OP': 'Error unidades en OP',
    'ERROR_UNIDAD_COMPRA': 'Error unidades en compra',
    'FALTA_COMPRA': 'Faltó registrar compra',
    'VALORES_OP': 'Valores incorrectos en OP',
    'VALORES_DESPACHO': 'Valores incorrectos en despacho',
    'VALORES_COMPRA': 'Valores incorrectos en compra',
    'PRODUCTO_DANADO': 'Producto dañado',
    'OBSOLETO': 'Obsoleto',
    'REDUNDANTE': 'Artículo redundante',
}

OC_BIN = '/home/osserver/.nvm/versions/node/v22.17.0/bin/opencode'
OC_REPO = '/home/osserver/Proyectos_Antigravity/sa_opencode'


def _db_query(db_config, sql, params=None):
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
    conn.close()
    return list(rows)


def _parse_cantidad(val):
    """Convierte texto con coma decimal a float."""
    if val is None:
        return 0.0
    return float(str(val).replace(',', '.'))


# ═══════════════════════════════════════════════════════════════════════════════
# CAPA 1: ANÁLISIS DETERMINISTA
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_trazabilidad(id_effi, limit=30):
    """Últimos movimientos de trazabilidad del artículo."""
    return _db_query(DB_EFFI, """
        SELECT transaccion, tipo_de_movimiento, cantidad, bodega, fecha
        FROM zeffi_trazabilidad
        WHERE id_articulo = %s
        ORDER BY fecha DESC
        LIMIT %s
    """, (id_effi, limit))


def _obtener_ops_como_material(id_effi):
    """OPs donde este artículo es materia prima (consumido)."""
    return _db_query(DB_EFFI, """
        SELECT m.id_orden, m.descripcion_material, m.cantidad,
               e.estado, e.vigencia, e.fecha_de_creacion
        FROM zeffi_materiales m
        JOIN zeffi_produccion_encabezados e ON m.id_orden = e.id_orden
        WHERE m.cod_material = %s AND m.vigencia = 'Orden vigente'
    """, (id_effi,))


def _obtener_ops_como_producto(id_effi):
    """OPs donde este artículo es producto terminado (producido)."""
    return _db_query(DB_EFFI, """
        SELECT p.id_orden, p.descripcion_articulo_producido, p.cantidad,
               e.estado, e.vigencia, e.fecha_de_creacion
        FROM zeffi_articulos_producidos p
        JOIN zeffi_produccion_encabezados e ON p.id_orden = e.id_orden
        WHERE p.cod_articulo = %s AND p.vigencia = 'Orden vigente'
    """, (id_effi,))


def _obtener_articulos_misma_op(id_effi, fecha_inventario):
    """Otros artículos de las mismas OPs que también tienen diferencia."""
    # Buscar OPs donde participa este artículo (como material o producto)
    ops_material = _db_query(DB_EFFI, """
        SELECT DISTINCT id_orden FROM zeffi_materiales
        WHERE cod_material = %s AND vigencia = 'Orden vigente'
    """, (id_effi,))
    ops_producto = _db_query(DB_EFFI, """
        SELECT DISTINCT id_orden FROM zeffi_articulos_producidos
        WHERE cod_articulo = %s AND vigencia = 'Orden vigente'
    """, (id_effi,))

    op_ids = set()
    for r in ops_material + ops_producto:
        op_ids.add(str(r['id_orden']))

    if not op_ids:
        return []

    # Buscar todos los artículos de esas OPs
    placeholders = ','.join(['%s'] * len(op_ids))
    otros_materiales = _db_query(DB_EFFI, f"""
        SELECT DISTINCT cod_material AS id_effi, descripcion_material AS nombre
        FROM zeffi_materiales WHERE id_orden IN ({placeholders}) AND vigencia = 'Orden vigente'
    """, list(op_ids))
    otros_productos = _db_query(DB_EFFI, f"""
        SELECT DISTINCT cod_articulo AS id_effi, descripcion_articulo_producido AS nombre
        FROM zeffi_articulos_producidos WHERE id_orden IN ({placeholders}) AND vigencia = 'Orden vigente'
    """, list(op_ids))

    otros_ids = set()
    for r in otros_materiales + otros_productos:
        if str(r['id_effi']) != str(id_effi):
            otros_ids.add(str(r['id_effi']))

    if not otros_ids:
        return []

    # Buscar sus diferencias en inv_gestion
    placeholders2 = ','.join(['%s'] * len(otros_ids))
    return _db_query(DB_INV, f"""
        SELECT id_effi, nombre, grupo, total_diferencia, impacto_economico
        FROM inv_gestion
        WHERE fecha_inventario = %s AND id_effi IN ({placeholders2}) AND total_diferencia != 0
    """, [fecha_inventario] + list(otros_ids))


def _buscar_nombres_similares(nombre, id_effi):
    """Busca artículos con nombre similar (posible duplicado)."""
    # Tomar las primeras 3 palabras significativas del nombre
    palabras = [p for p in nombre.upper().split() if len(p) > 2 and p not in ('DE', 'EN', 'POR', 'CON', 'SIN', 'X')]
    if len(palabras) < 2:
        return []

    patron = f"%{palabras[0]}%{palabras[1]}%"
    return _db_query(DB_EFFI, """
        SELECT id_effi, nombre FROM inv_catalogo_articulos
        WHERE nombre LIKE %s AND id_effi != %s
        LIMIT 5
    """, (patron, id_effi))


def analisis_determinista(gestion_row, fecha_inventario):
    """
    Ejecuta reglas deterministas para un artículo.
    Retorna: { causa, confianza, explicacion, evidencia[] }
    """
    id_effi = gestion_row['id_effi']
    nombre = gestion_row['nombre'] or ''
    diferencia = float(gestion_row['total_diferencia'] or 0)
    grupo = gestion_row['grupo'] or ''
    unidad = gestion_row['unidad'] or ''

    resultados = []
    evidencias = []

    # ── Regla 1: OP no ejecutada ──────────────────────────────────
    ops_mat = _obtener_ops_como_material(id_effi)
    ops_prod = _obtener_ops_como_producto(id_effi)

    ops_generadas_mat = [o for o in ops_mat if o['estado'] == 'Generada' and o['vigencia'] == 'Vigente']
    ops_generadas_prod = [o for o in ops_prod if o['estado'] == 'Generada' and o['vigencia'] == 'Vigente']

    if ops_generadas_mat and diferencia < 0:
        # Falta materia prima Y hay OPs generadas que la consumen
        consumo_ops = sum(_parse_cantidad(o['cantidad']) for o in ops_generadas_mat)
        if consumo_ops > 0:
            ratio = min(abs(diferencia) / consumo_ops, 1.0)
            confianza = int(60 + ratio * 35)  # 60-95%
            ops_ids = [str(o['id_orden']) for o in ops_generadas_mat]
            evidencias.append({
                'tipo': 'ops_generadas',
                'detalle': f"OPs generadas vigentes: {', '.join(ops_ids)} consumen {consumo_ops} {unidad}"
            })
            resultados.append({
                'causa': CAUSAS['OP_NO_EJECUTADA'],
                'confianza': confianza,
                'explicacion': f"Faltan {abs(diferencia)} {unidad}. Las OPs generadas ({', '.join(ops_ids)}) consumen {consumo_ops} {unidad} como materia prima. {'La diferencia coincide.' if ratio > 0.8 else f'Explica {ratio*100:.0f}% del faltante.'}",
            })

    if ops_generadas_prod and diferencia > 0:
        # Sobra producto terminado Y hay OPs generadas que lo producen
        produccion_ops = sum(_parse_cantidad(o['cantidad']) for o in ops_generadas_prod)
        if produccion_ops > 0:
            ratio = min(diferencia / produccion_ops, 1.0)
            confianza = int(60 + ratio * 35)
            ops_ids = [str(o['id_orden']) for o in ops_generadas_prod]
            evidencias.append({
                'tipo': 'ops_generadas_producto',
                'detalle': f"OPs generadas vigentes: {', '.join(ops_ids)} producen {produccion_ops} {unidad}"
            })
            resultados.append({
                'causa': CAUSAS['OP_NO_EJECUTADA'],
                'confianza': confianza,
                'explicacion': f"Sobran {diferencia} {unidad}. Las OPs generadas ({', '.join(ops_ids)}) producen {produccion_ops} {unidad}. Effi ya registró la producción pero no se ha ejecutado físicamente.",
            })

    # ── Regla 2: Error de unidades (×1000) ────────────────────────
    if diferencia != 0 and abs(diferencia) > 1:
        if unidad in ('KG', 'LT'):
            # ¿La diferencia × 1000 coincide con el teórico o físico?
            teorico = float(gestion_row['total_teorico'] or 0)
            fisico = float(gestion_row['total_fisico'] or 0)
            if fisico > 0 and abs(fisico * 1000 - teorico) < teorico * 0.05:
                resultados.append({
                    'causa': CAUSAS['ERROR_UNIDAD_OP'],
                    'confianza': 90,
                    'explicacion': f"El conteo físico ({fisico}) × 1000 = {fisico*1000}, que coincide con el teórico ({teorico}). Probable error: se contó en gramos en vez de kilos.",
                })
            elif teorico > 0 and abs(teorico * 1000 - fisico) < fisico * 0.05:
                resultados.append({
                    'causa': CAUSAS['ERROR_UNIDAD_OP'],
                    'confianza': 90,
                    'explicacion': f"El teórico ({teorico}) × 1000 = {teorico*1000}, que coincide con el físico ({fisico}). Probable error de unidad en Effi.",
                })

    # ── Regla 3: Artículos relacionados (cruce MP↔PT en misma OP) ──
    relacionados = _obtener_articulos_misma_op(id_effi, fecha_inventario)
    if relacionados:
        # Si faltan materias primas Y sobran productos de la misma OP (o viceversa)
        faltantes_rel = [r for r in relacionados if float(r['total_diferencia']) < 0]
        sobrantes_rel = [r for r in relacionados if float(r['total_diferencia']) > 0]

        if diferencia < 0 and sobrantes_rel:
            nombres_sob = ', '.join([f"{r['nombre'][:30]} (+{float(r['total_diferencia'])})" for r in sobrantes_rel[:3]])
            evidencias.append({
                'tipo': 'articulos_relacionados',
                'detalle': f"Artículos de las mismas OPs con sobrante: {nombres_sob}"
            })
            if not any(r['causa'] == CAUSAS['OP_NO_EJECUTADA'] for r in resultados):
                resultados.append({
                    'causa': CAUSAS['VALORES_OP'],
                    'confianza': 65,
                    'explicacion': f"Falta {abs(diferencia)} {unidad} de {nombre[:30]}. Artículos de las mismas OPs tienen sobrante: {nombres_sob}. Posible error en valores de la OP.",
                })

        if diferencia > 0 and faltantes_rel:
            nombres_fal = ', '.join([f"{r['nombre'][:30]} ({float(r['total_diferencia'])})" for r in faltantes_rel[:3]])
            evidencias.append({
                'tipo': 'articulos_relacionados',
                'detalle': f"Artículos de las mismas OPs con faltante: {nombres_fal}"
            })

    # ── Regla 4: Trazabilidad sospechosa ──────────────────────────
    trazabilidad = _obtener_trazabilidad(id_effi, 20)
    if trazabilidad:
        # Buscar egresos recientes que podrían ser despachos sin facturar
        egresos_recientes = [t for t in trazabilidad
                            if _parse_cantidad(t['cantidad']) < 0
                            and t['tipo_de_movimiento'] == 'Creación de transacción'
                            and 'REMISION' not in (t['transaccion'] or '').upper()
                            and 'FACTURA' not in (t['transaccion'] or '').upper()]

        if diferencia < 0 and egresos_recientes:
            total_egresos = sum(abs(_parse_cantidad(e['cantidad'])) for e in egresos_recientes[:5])
            evidencias.append({
                'tipo': 'trazabilidad',
                'detalle': f"Egresos recientes sin factura/remisión: {len(egresos_recientes)} movimientos, total {total_egresos} {unidad}"
            })

        # Si no hay movimientos recientes y la diferencia es grande
        if not trazabilidad and abs(diferencia) > 5:
            resultados.append({
                'causa': CAUSAS['FALTA_COMPRA'],
                'confianza': 45,
                'explicacion': f"Sin movimientos en trazabilidad y diferencia de {diferencia} {unidad}. Posible compra o ingreso no registrado.",
            })

    # ── Regla 5: Artículo duplicado ───────────────────────────────
    similares = _buscar_nombres_similares(nombre, id_effi)
    if similares:
        nombres_sim = ', '.join([f"{s['id_effi']}-{s['nombre'][:30]}" for s in similares[:3]])
        evidencias.append({
            'tipo': 'duplicado',
            'detalle': f"Artículos con nombre similar: {nombres_sim}"
        })
        if not resultados:
            resultados.append({
                'causa': CAUSAS['REDUNDANTE'],
                'confianza': 40,
                'explicacion': f"Existen artículos con nombre similar: {nombres_sim}. Verificar si hay duplicación.",
            })

    # ── Resultado final ──────────────────────────────────────────
    if resultados:
        # Tomar la causa con mayor confianza
        mejor = max(resultados, key=lambda r: r['confianza'])
        return {
            'causa': mejor['causa'],
            'confianza': mejor['confianza'],
            'explicacion': mejor['explicacion'],
            'evidencia': evidencias,
            'todas_las_causas': resultados,
        }

    return {
        'causa': None,
        'confianza': 0,
        'explicacion': 'No se encontró causa determinista. Se requiere análisis manual o IA.',
        'evidencia': evidencias,
        'todas_las_causas': [],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CAPA 2: ANÁLISIS IA
# ═══════════════════════════════════════════════════════════════════════════════

def _llamar_ia(prompt, timeout=60):
    """Llama a OpenCode CLI para análisis IA."""
    try:
        result = subprocess.run(
            [OC_BIN, 'run', '--format', 'json', '--model', 'opencode/qwen3.6-plus-free', '-p', prompt],
            capture_output=True, text=True, timeout=timeout,
            cwd=OC_REPO
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        respuesta = data.get('result', '') if isinstance(data, dict) else str(data)
        return respuesta
    except Exception:
        return None


def analisis_ia(gestion_row, evidencias_deterministas, fecha_inventario):
    """Análisis con IA para casos que las reglas deterministas no resolvieron."""
    id_effi = gestion_row['id_effi']
    nombre = gestion_row['nombre']
    diferencia = float(gestion_row['total_diferencia'] or 0)
    teorico = float(gestion_row['total_teorico'] or 0)
    fisico = float(gestion_row['total_fisico'] or 0)
    impacto = float(gestion_row['impacto_economico'] or 0)
    grupo = gestion_row['grupo']
    unidad = gestion_row['unidad']

    # Recopilar datos para el prompt
    trazabilidad = _obtener_trazabilidad(id_effi, 15)
    traza_texto = ''
    for t in trazabilidad[:10]:
        cant = _parse_cantidad(t['cantidad'])
        traza_texto += f"  {t['fecha']} | {t['transaccion'][:50]} | {'+' if cant > 0 else ''}{cant} | {t['bodega']}\n"

    evidencias_texto = ''
    for e in evidencias_deterministas:
        evidencias_texto += f"  - {e['tipo']}: {e['detalle']}\n"

    prompt = f"""Eres un auditor de inventario de una empresa de alimentos (Origen Silvestre).
Analiza esta inconsistencia y determina la causa más probable.

ARTÍCULO: {nombre} (Grupo: {grupo}, Unidad: {unidad})
DIFERENCIA: {diferencia} {unidad} (teórico: {teorico}, físico: {fisico})
IMPACTO ECONÓMICO: ${abs(impacto):,.0f}

TRAZABILIDAD RECIENTE:
{traza_texto or '  Sin movimientos registrados'}

EVIDENCIAS ENCONTRADAS:
{evidencias_texto or '  Ninguna'}

CAUSAS POSIBLES:
1. Faltó remisionar o facturar
2. OP no ejecutada
3. Error unidades en OP
4. Error unidades en compra
5. Faltó registrar compra
6. Valores incorrectos en OP
7. Valores incorrectos en despacho
8. Valores incorrectos en compra

Responde SOLO con un JSON válido (sin markdown, sin explicación adicional):
{{"causa": "nombre de la causa", "confianza": 0-100, "explicacion": "explicación breve en español"}}"""

    respuesta = _llamar_ia(prompt)
    if not respuesta:
        return None

    # Intentar parsear JSON de la respuesta
    try:
        # Buscar JSON en la respuesta
        match = re.search(r'\{[^{}]+\}', respuesta)
        if match:
            data = json.loads(match.group())
            return {
                'causa': data.get('causa', 'Indeterminada'),
                'confianza': min(int(data.get('confianza', 30)), 80),  # Cap IA a 80%
                'explicacion': data.get('explicacion', respuesta[:200]),
            }
    except (json.JSONDecodeError, ValueError):
        pass

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def analizar_articulo(gestion_row, fecha_inventario, usar_ia=True):
    """
    Analiza un artículo: Capa 1 (determinista) → Capa 2 (IA si necesario).
    Retorna dict con causa, confianza, explicacion, evidencia.
    """
    # Capa 1
    resultado = analisis_determinista(gestion_row, fecha_inventario)

    # Capa 2: si la confianza es baja, pedir ayuda a la IA
    if usar_ia and resultado['confianza'] < 60:
        resultado_ia = analisis_ia(gestion_row, resultado.get('evidencia', []), fecha_inventario)
        if resultado_ia and resultado_ia['confianza'] > resultado['confianza']:
            resultado['causa'] = resultado_ia['causa']
            resultado['confianza'] = resultado_ia['confianza']
            resultado['explicacion'] = resultado_ia['explicacion']
            resultado['fuente'] = 'ia'
        else:
            resultado['fuente'] = 'determinista'
    else:
        resultado['fuente'] = 'determinista'

    return resultado


def analizar_todos(fecha_inventario, usar_ia=True, callback=None):
    """
    Analiza todos los artículos con diferencia para una fecha.
    callback(progreso, total, articulo) se llama por cada artículo procesado.
    Retorna: { analizados, con_causa, sin_causa }
    """
    rows = _db_query(DB_INV, """
        SELECT * FROM inv_gestion
        WHERE fecha_inventario = %s AND total_diferencia != 0
        ORDER BY ABS(impacto_economico) DESC
    """, (fecha_inventario,))

    conn = pymysql.connect(**DB_INV)
    analizados = 0
    con_causa = 0

    for i, row in enumerate(rows):
        resultado = analizar_articulo(row, fecha_inventario, usar_ia=usar_ia)

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE inv_gestion
                SET causa_ia = %s, confianza_ia = %s, explicacion_ia = %s,
                    evidencia_ia = %s, analizado_en = NOW(),
                    estado = CASE WHEN estado = 'pendiente' THEN 'analizado' ELSE estado END
                WHERE id = %s
            """, (
                resultado.get('causa'),
                resultado.get('confianza', 0),
                resultado.get('explicacion'),
                json.dumps(resultado.get('evidencia', []), ensure_ascii=False),
                row['id']
            ))
            conn.commit()

        analizados += 1
        if resultado.get('causa'):
            con_causa += 1

        if callback:
            callback(i + 1, len(rows), row['nombre'])

    conn.close()
    return {'analizados': analizados, 'con_causa': con_causa, 'sin_causa': analizados - con_causa}
