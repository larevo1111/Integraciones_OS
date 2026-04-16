#!/usr/bin/env python3
"""Genera informe PDF del inventario físico."""
import os, sys, json, argparse
from datetime import datetime
import pymysql

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_INV = dict(host='localhost', user='osadmin', password='Epist2487.', database='os_inventario',
              cursorclass=pymysql.cursors.DictCursor)

NOMBRES_GRUPO = {
    'MP': 'Materia Prima', 'INS': 'Insumos', 'PP': 'Producto en Proceso',
    'PT': 'Producto Terminado', 'DS': 'Desarrollo', 'DES': 'Desperdicio',
    'NM': 'No Matriculado', 'SIN': 'Sin clasificar'
}

def q(sql, params=None):
    conn = pymysql.connect(**DB_INV)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()

def fmtm(n):
    """Formato moneda: $1.234.567"""
    if n is None: return '$0'
    neg = n < 0
    s = f'{abs(int(round(n))):,}'.replace(',', '.')
    return f'-${s}' if neg else f'${s}'

def fmtq(n):
    """Formato cantidad: 1.234,50"""
    if n is None: return '—'
    n = float(n)
    if n == int(n): return f'{int(n):,}'.replace(',', '.')
    return f'{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def recopilar(fecha):
    """Recopila todos los datos necesarios para el informe."""
    # Resumen general
    resumen = q("""
        SELECT COUNT(*) AS total,
            SUM(CASE WHEN inventario_fisico IS NOT NULL THEN 1 ELSE 0 END) AS contados,
            SUM(CASE WHEN inventario_fisico IS NULL THEN 1 ELSE 0 END) AS sin_contar,
            SUM(CASE WHEN inventario_fisico IS NOT NULL AND ROUND(diferencia,2)=0 THEN 1 ELSE 0 END) AS exactos,
            SUM(CASE WHEN inventario_fisico IS NOT NULL AND diferencia>0 THEN 1 ELSE 0 END) AS sobrantes,
            SUM(CASE WHEN inventario_fisico IS NOT NULL AND diferencia<0 THEN 1 ELSE 0 END) AS faltantes
        FROM inv_conteos WHERE fecha_inventario=%s AND excluido=0
    """, (fecha,))[0]

    # Valorización total
    val = q("""
        SELECT ROUND(SUM(COALESCE(inventario_teorico,0)*COALESCE(costo_manual,0)),0) AS val_teo,
               ROUND(SUM(COALESCE(inventario_fisico,0)*COALESCE(costo_manual,0)),0) AS val_fis,
               ROUND(SUM(COALESCE(diferencia,0)*COALESCE(costo_manual,0)),0) AS impacto
        FROM inv_conteos WHERE fecha_inventario=%s AND excluido=0 AND inventario_fisico IS NOT NULL
    """, (fecha,))[0]

    # Por bodega
    bodegas = q("""
        SELECT bodega, COUNT(*) AS articulos,
            ROUND(SUM(COALESCE(inventario_fisico,0)*COALESCE(costo_manual,0)),0) AS val_fis,
            ROUND(SUM(COALESCE(inventario_teorico,0)*COALESCE(costo_manual,0)),0) AS val_teo,
            ROUND(SUM(COALESCE(diferencia,0)*COALESCE(costo_manual,0)),0) AS impacto
        FROM inv_conteos WHERE fecha_inventario=%s AND excluido=0 AND inventario_fisico IS NOT NULL
        GROUP BY bodega ORDER BY val_fis DESC
    """, (fecha,))

    # Por tipo (grupo)
    tipos = q("""
        SELECT COALESCE(r.grupo,'SIN') AS tipo, COUNT(*) AS articulos,
            SUM(CASE WHEN ROUND(c.diferencia,2)=0 THEN 1 ELSE 0 END) AS exactos,
            SUM(CASE WHEN c.diferencia!=0 THEN 1 ELSE 0 END) AS con_dif,
            ROUND(SUM(COALESCE(c.inventario_teorico,0)*COALESCE(c.costo_manual,0)),0) AS val_teo,
            ROUND(SUM(COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0)),0) AS val_fis,
            ROUND(SUM(COALESCE(c.diferencia,0)*COALESCE(c.costo_manual,0)),0) AS impacto
        FROM inv_conteos c LEFT JOIN inv_rangos r ON r.id_effi=c.id_effi
        WHERE c.fecha_inventario=%s AND c.excluido=0 AND c.inventario_fisico IS NOT NULL
        GROUP BY COALESCE(r.grupo,'SIN')
        ORDER BY SUM(COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0)) DESC
    """, (fecha,))

    # Por categoría
    categorias = q("""
        SELECT c.categoria, COUNT(*) AS articulos,
            ROUND(SUM(COALESCE(c.inventario_teorico,0)*COALESCE(c.costo_manual,0)),0) AS val_teo,
            ROUND(SUM(COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0)),0) AS val_fis,
            ROUND(SUM(COALESCE(c.diferencia,0)*COALESCE(c.costo_manual,0)),0) AS impacto
        FROM inv_conteos c WHERE c.fecha_inventario=%s AND c.excluido=0 AND c.inventario_fisico IS NOT NULL
        GROUP BY c.categoria ORDER BY val_fis DESC
    """, (fecha,))

    # Top 20 inconsistencias
    top20 = q("""
        SELECT c.id_effi, c.nombre, COALESCE(r.grupo,'') AS tipo, c.bodega,
            c.inventario_teorico AS teorico, c.inventario_fisico AS fisico,
            c.diferencia AS dif, c.costo_manual, ROUND(c.diferencia*c.costo_manual,0) AS impacto
        FROM inv_conteos c LEFT JOIN inv_rangos r ON r.id_effi=c.id_effi
        WHERE c.fecha_inventario=%s AND c.excluido=0 AND c.inventario_fisico IS NOT NULL AND c.diferencia!=0
        ORDER BY ABS(c.diferencia*c.costo_manual) DESC LIMIT 20
    """, (fecha,))

    # Productos No Conformes
    pnc = q("""
        SELECT c.id_effi, c.nombre, c.inventario_fisico AS fisico,
            c.inventario_teorico AS teorico, c.costo_manual,
            ROUND(COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0),0) AS valor_fisico
        FROM inv_conteos c
        WHERE c.fecha_inventario=%s AND c.bodega='Productos No Conformes' AND c.excluido=0
        ORDER BY COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0) DESC
    """, (fecha,))

    # Sin costo
    sin_costo = q("""
        SELECT COUNT(*) AS n FROM inv_conteos
        WHERE fecha_inventario=%s AND excluido=0 AND (costo_manual=0 OR costo_manual IS NULL)
    """, (fecha,))[0]['n']

    # Listado completo (para la última sección)
    listado = q("""
        SELECT c.id_effi, c.nombre, c.categoria, COALESCE(r.grupo,'') AS tipo,
            c.bodega, c.inventario_teorico AS teorico, c.inventario_fisico AS fisico,
            c.diferencia AS dif, c.costo_manual,
            ROUND(COALESCE(c.inventario_fisico,0)*COALESCE(c.costo_manual,0),0) AS valor_fisico,
            ROUND(COALESCE(c.diferencia,0)*COALESCE(c.costo_manual,0),0) AS impacto
        FROM inv_conteos c LEFT JOIN inv_rangos r ON r.id_effi=c.id_effi
        WHERE c.fecha_inventario=%s AND c.excluido=0 AND c.inventario_fisico IS NOT NULL
        ORDER BY c.categoria, c.nombre
    """, (fecha,))

    return {
        'fecha': fecha, 'resumen': resumen, 'val': val,
        'bodegas': bodegas, 'tipos': tipos, 'categorias': categorias,
        'top20': top20, 'pnc': pnc, 'sin_costo': sin_costo, 'listado': listado
    }


def generar_html(d):
    """Genera HTML del informe."""
    fecha_fmt = datetime.strptime(d['fecha'], '%Y-%m-%d').strftime('%d de %B de %Y').replace(
        'January','enero').replace('February','febrero').replace('March','marzo').replace(
        'April','abril').replace('May','mayo').replace('June','junio').replace(
        'July','julio').replace('August','agosto').replace('September','septiembre').replace(
        'October','octubre').replace('November','noviembre').replace('December','diciembre')
    r = d['resumen']
    v = d['val']
    pct_exactitud = round(int(r['exactos']) / int(r['contados']) * 100, 1) if int(r['contados']) > 0 else 0

    # Filas por tipo
    filas_tipo = ''
    for t in d['tipos']:
        nombre = NOMBRES_GRUPO.get(t['tipo'], t['tipo'])
        pct = round(int(t['exactos']) / int(t['articulos']) * 100, 1) if int(t['articulos']) > 0 else 0
        filas_tipo += f"""<tr>
            <td>{nombre}</td><td class="r">{t['articulos']}</td>
            <td class="r">{t['exactos']}</td><td class="r">{pct}%</td>
            <td class="r">{fmtm(t['val_teo'])}</td><td class="r">{fmtm(t['val_fis'])}</td>
            <td class="r {'neg' if int(t['impacto'] or 0)<0 else 'pos'}">{fmtm(t['impacto'])}</td>
        </tr>"""

    # Filas por categoría
    filas_cat = ''
    for c in d['categorias']:
        if int(c['val_fis'] or 0) == 0 and int(c['val_teo'] or 0) == 0:
            continue
        filas_cat += f"""<tr>
            <td>{c['categoria']}</td><td class="r">{c['articulos']}</td>
            <td class="r">{fmtm(c['val_teo'])}</td><td class="r">{fmtm(c['val_fis'])}</td>
            <td class="r {'neg' if int(c['impacto'] or 0)<0 else 'pos'}">{fmtm(c['impacto'])}</td>
        </tr>"""

    # Filas top 20
    filas_top = ''
    for i, t in enumerate(d['top20'], 1):
        filas_top += f"""<tr>
            <td class="r">{i}</td><td>{t['id_effi']}</td><td>{t['nombre']}</td>
            <td>{t['tipo']}</td><td>{t['bodega']}</td>
            <td class="r">{fmtq(t['teorico'])}</td><td class="r">{fmtq(t['fisico'])}</td>
            <td class="r {'neg' if float(t['dif'] or 0)<0 else 'pos'}">{fmtq(t['dif'])}</td>
            <td class="r">{fmtm(t['costo_manual'])}</td>
            <td class="r {'neg' if int(t['impacto'] or 0)<0 else 'pos'}">{fmtm(t['impacto'])}</td>
        </tr>"""

    # Filas PNC
    filas_pnc = ''
    pnc_total = 0
    for p in d['pnc']:
        fisico = float(p['fisico'] or 0)
        if fisico == 0:
            continue
        val = int(p['valor_fisico'] or 0)
        pnc_total += val
        filas_pnc += f"""<tr>
            <td>{p['id_effi']}</td><td>{p['nombre']}</td>
            <td class="r">{fmtq(p['fisico'])}</td>
            <td class="r">{fmtm(p['costo_manual'])}</td>
            <td class="r">{fmtm(val)}</td>
        </tr>"""

    # Listado completo
    filas_listado = ''
    for l in d['listado']:
        cls_dif = 'neg' if float(l['dif'] or 0) < 0 else ('pos' if float(l['dif'] or 0) > 0 else '')
        filas_listado += f"""<tr>
            <td>{l['id_effi']}</td><td class="nombre">{l['nombre']}</td>
            <td>{l['tipo']}</td><td>{l['bodega'][:4] if l['bodega'] != 'Principal' else 'Ppal'}</td>
            <td class="r">{fmtq(l['teorico'])}</td><td class="r">{fmtq(l['fisico'])}</td>
            <td class="r {cls_dif}">{fmtq(l['dif'])}</td>
            <td class="r">{fmtm(l['costo_manual'])}</td>
            <td class="r">{fmtm(l['valor_fisico'])}</td>
            <td class="r {cls_dif}">{fmtm(l['impacto'])}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@page {{ size: letter; margin: 15mm 12mm; }}
@page listado {{ size: letter landscape; margin: 10mm 8mm; }}
body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 9pt; color: #1a1a1a; line-height: 1.4; }}
h1 {{ font-size: 18pt; margin: 0 0 2px; color: #111; }}
h2 {{ font-size: 12pt; margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 2px solid #00C853; color: #111; }}
h3 {{ font-size: 10pt; margin: 14px 0 4px; color: #333; }}
.subtitle {{ font-size: 10pt; color: #666; margin: 0 0 12px; }}
.header-row {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
.logo {{ font-size: 24pt; font-weight: 700; color: #00C853; }}

/* KPIs */
.kpis {{ display: flex; gap: 10px; margin: 10px 0; }}
.kpi {{ flex: 1; background: #f7f7f7; border-radius: 6px; padding: 10px 12px; text-align: center; }}
.kpi-label {{ font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
.kpi-value {{ font-size: 14pt; font-weight: 700; color: #111; }}
.kpi-value.neg {{ color: #dc2626; }}
.kpi-value.pos {{ color: #16a34a; }}

/* Tablas */
table {{ width: 100%; border-collapse: collapse; font-size: 8pt; margin: 6px 0 12px; }}
th {{ background: #f0f0f0; padding: 5px 6px; text-align: left; font-weight: 600; font-size: 7.5pt;
     text-transform: uppercase; letter-spacing: 0.3px; color: #555; border-bottom: 2px solid #ddd; }}
td {{ padding: 4px 6px; border-bottom: 1px solid #eee; }}
tr:nth-child(even) {{ background: #fafafa; }}
.r {{ text-align: right; }}
.neg {{ color: #dc2626; font-weight: 600; }}
.pos {{ color: #16a34a; font-weight: 600; }}
.nombre {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.total-row {{ font-weight: 700; background: #f0f0f0 !important; border-top: 2px solid #ccc; }}

/* Secciones */
.hallazgos {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px 14px; margin: 10px 0; font-size: 8.5pt; }}
.hallazgos li {{ margin: 3px 0; }}
.recomendaciones {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 10px 14px; margin: 10px 0; font-size: 8.5pt; }}

/* Page breaks */
.page-break {{ page-break-before: always; }}
.listado-section {{ page: listado; page-break-before: always; }}
.no-break {{ page-break-inside: avoid; }}

/* Firmas */
.firmas {{ display: flex; justify-content: space-around; margin-top: 40px; }}
.firma {{ text-align: center; width: 200px; }}
.firma-linea {{ border-top: 1px solid #333; margin-top: 50px; padding-top: 4px; font-size: 8pt; }}
</style>
</head><body>

<!-- ═══ PÁGINA 1: RESUMEN EJECUTIVO ═══ -->
<div class="header-row">
    <div>
        <h1>Informe de Inventario Físico</h1>
        <p class="subtitle">Origen Silvestre — {fecha_fmt}</p>
    </div>
    <div class="logo">OS</div>
</div>

<h2>1. Resumen Ejecutivo</h2>
<p>Inventario físico realizado el <strong>{fecha_fmt}</strong> en las bodegas Principal y Productos No Conformes.
Se contaron <strong>{r['contados']}</strong> de {r['total']} artículos registrados ({r['sin_contar']} excluido/sin contar).</p>

<div class="kpis">
    <div class="kpi">
        <div class="kpi-label">Valor Teórico</div>
        <div class="kpi-value">{fmtm(v['val_teo'])}</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Valor Físico</div>
        <div class="kpi-value">{fmtm(v['val_fis'])}</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Diferencia Neta</div>
        <div class="kpi-value {'neg' if int(v['impacto'] or 0)<0 else 'pos'}">{fmtm(v['impacto'])}</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Exactitud</div>
        <div class="kpi-value">{pct_exactitud}%</div>
    </div>
</div>

<table>
    <tr><th>Indicador</th><th class="r">Cantidad</th></tr>
    <tr><td>Artículos contados</td><td class="r">{r['contados']}</td></tr>
    <tr><td>Coincidencias exactas</td><td class="r">{r['exactos']}</td></tr>
    <tr><td>Sobrantes (físico > teórico)</td><td class="r pos">{r['sobrantes']}</td></tr>
    <tr><td>Faltantes (físico < teórico)</td><td class="r neg">{r['faltantes']}</td></tr>
    <tr><td>Sin contar / excluidos</td><td class="r">{r['sin_contar']}</td></tr>
    <tr><td>Artículos sin costo manual asignado</td><td class="r">{d['sin_costo']}</td></tr>
</table>

<h3>Valorización por Bodega</h3>
<table>
    <tr><th>Bodega</th><th class="r">Artículos</th><th class="r">Valor Teórico</th><th class="r">Valor Físico</th><th class="r">Impacto</th></tr>
    {''.join(f"<tr><td>{b['bodega']}</td><td class='r'>{b['articulos']}</td><td class='r'>{fmtm(b['val_teo'])}</td><td class='r'>{fmtm(b['val_fis'])}</td><td class='r {'neg' if int(b['impacto'] or 0)<0 else 'pos'}'>{fmtm(b['impacto'])}</td></tr>" for b in d['bodegas'])}
    <tr class="total-row"><td>TOTAL</td><td class="r">{sum(int(b['articulos']) for b in d['bodegas'])}</td><td class="r">{fmtm(v['val_teo'])}</td><td class="r">{fmtm(v['val_fis'])}</td><td class="r {'neg' if int(v['impacto'] or 0)<0 else 'pos'}">{fmtm(v['impacto'])}</td></tr>
</table>

<!-- ═══ PÁGINA 2: COSTEO POR TIPO Y CATEGORÍA ═══ -->
<div class="page-break"></div>
<h2>2. Costeo del Inventario por Tipo de Artículo</h2>
<table>
    <tr><th>Tipo</th><th class="r">Art.</th><th class="r">Exactos</th><th class="r">%Exact.</th><th class="r">Val. Teórico</th><th class="r">Val. Físico</th><th class="r">Impacto</th></tr>
    {filas_tipo}
    <tr class="total-row"><td>TOTAL</td><td class="r">{r['contados']}</td><td class="r">{r['exactos']}</td><td class="r">{pct_exactitud}%</td><td class="r">{fmtm(v['val_teo'])}</td><td class="r">{fmtm(v['val_fis'])}</td><td class="r {'neg' if int(v['impacto'] or 0)<0 else 'pos'}">{fmtm(v['impacto'])}</td></tr>
</table>

<h3>Por Categoría Effi</h3>
<table>
    <tr><th>Categoría</th><th class="r">Art.</th><th class="r">Val. Teórico</th><th class="r">Val. Físico</th><th class="r">Impacto</th></tr>
    {filas_cat}
    <tr class="total-row"><td>TOTAL</td><td class="r">{r['contados']}</td><td class="r">{fmtm(v['val_teo'])}</td><td class="r">{fmtm(v['val_fis'])}</td><td class="r {'neg' if int(v['impacto'] or 0)<0 else 'pos'}">{fmtm(v['impacto'])}</td></tr>
</table>

<h3>Productos No Conformes</h3>
<p>Se encontraron {sum(1 for p in d['pnc'] if float(p['fisico'] or 0)>0)} artículos con existencia física en la bodega de productos no conformes.</p>
<table>
    <tr><th>Cód</th><th>Artículo</th><th class="r">Físico</th><th class="r">Costo Un.</th><th class="r">Valor</th></tr>
    {filas_pnc}
    <tr class="total-row"><td colspan="4">TOTAL PRODUCTOS NO CONFORMES</td><td class="r">{fmtm(pnc_total)}</td></tr>
</table>

<!-- ═══ PÁGINA 3: TOP 20 INCONSISTENCIAS ═══ -->
<div class="page-break"></div>
<h2>3. Top 20 Inconsistencias por Impacto Económico</h2>
<table>
    <tr><th>#</th><th>Cód</th><th>Artículo</th><th>Tipo</th><th>Bodega</th><th class="r">Teórico</th><th class="r">Físico</th><th class="r">Dif.</th><th class="r">Costo Un.</th><th class="r">Impacto</th></tr>
    {filas_top}
</table>

<!-- ═══ PÁGINA 4: HALLAZGOS Y RECOMENDACIONES ═══ -->
<div class="page-break"></div>
<h2>4. Hallazgos y Análisis</h2>
<div class="hallazgos">
    <strong>Principales hallazgos:</strong>
    <ul>
        <li><strong>Materias Primas</strong> concentran el mayor faltante: almendra de cacao, polen, vainilla y maní representan el grueso de la diferencia.</li>
        <li><strong>Cajas de chocolate</strong> (cód 412, 580) muestran sobrante significativo — posiblemente stock recibido no registrado en Effi.</li>
        <li><strong>Productos en Proceso</strong> (nibs, coberturas) presentan faltantes importantes — posible consumo en producción no registrado.</li>
        <li><strong>Etiquetas</strong> (cód 90) con -852 unidades de diferencia — probable consumo acumulado sin registro.</li>
        <li><strong>Bodega Desarrollo</strong>: stock en 0. No requiere traslado.</li>
        <li><strong>{d['sin_costo']}</strong> artículos no tienen costo manual asignado en Effi — su valorización es $0.</li>
        <li><strong>Productos No Conformes</strong>: se encontraron {sum(1 for p in d['pnc'] if float(p['fisico'] or 0)>0)} artículos por valor de {fmtm(pnc_total)}.</li>
    </ul>
</div>

<h2>5. Ajustes Recomendados y Próximos Pasos</h2>
<div class="recomendaciones">
    <strong>Recomendaciones:</strong>
    <ul>
        <li>Generar ajuste de inventario en Effi para alinear stock del sistema con el conteo físico.</li>
        <li>Investigar las 20 inconsistencias críticas antes de ajustar — algunas pueden ser errores de registro corregibles.</li>
        <li>Asignar costo manual a los {d['sin_costo']} artículos que no lo tienen para completar la valorización.</li>
        <li>Definir destino de los productos no conformes (disposición, reproceso o baja).</li>
        <li>Implementar inventarios parciales periódicos (semanal por categoría o quincenal por valor ABC).</li>
        <li>Este informe se aprueba como <strong>nueva línea base</strong> del inventario.</li>
    </ul>
</div>

<div class="firmas">
    <div class="firma"><div class="firma-linea">Director — Origen Silvestre</div></div>
    <div class="firma"><div class="firma-linea">Responsable de Inventario</div></div>
</div>

<!-- ═══ ANEXO: LISTADO COMPLETO ═══ -->
<div class="listado-section"></div>
<h2>Anexo: Listado Completo de Inventario</h2>
<p style="font-size:8pt;color:#666">Detalle de todos los artículos contados con cantidades físicas, teóricas, costos y diferencias. Ordenado por categoría.</p>
<table style="font-size:7pt">
    <tr><th>Cód</th><th>Artículo</th><th>Tipo</th><th>Bod.</th><th class="r">Teórico</th><th class="r">Físico</th><th class="r">Dif.</th><th class="r">Costo Un.</th><th class="r">Val. Físico</th><th class="r">Impacto</th></tr>
    {filas_listado}
    <tr class="total-row"><td colspan="8">TOTAL INVENTARIO FÍSICO</td><td class="r">{fmtm(v['val_fis'])}</td><td class="r {'neg' if int(v['impacto'] or 0)<0 else 'pos'}">{fmtm(v['impacto'])}</td></tr>
</table>

</body></html>"""
    return html


def generar_pdf(fecha, output_path=None):
    """Genera el PDF del informe."""
    import weasyprint
    datos = recopilar(fecha)
    html = generar_html(datos)

    if not output_path:
        output_dir = os.path.join(BASE_DIR, 'inventario', 'informes')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'informe_inventario_{fecha}.pdf')

    weasyprint.HTML(string=html).write_pdf(output_path)
    print(f'PDF generado: {output_path}')
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fecha', required=True)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    generar_pdf(args.fecha, args.output)
