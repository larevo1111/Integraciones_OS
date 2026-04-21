#!/usr/bin/env python3
"""Genera análisis ejecutivo del inventario usando IA."""
import os, sys, json, argparse, requests
import pymysql
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local
DB_INV  = dict(**cfg_local(), database='os_inventario',
              cursorclass=pymysql.cursors.DictCursor)
DB_EFFI = dict(**cfg_local(), database='effi_data',
               cursorclass=pymysql.cursors.DictCursor)
IA_URL = 'http://localhost:5100/ia/simple'


def q(db, sql, params=None):
    conn = pymysql.connect(**db)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def recopilar_datos(fecha):
    """Recopila todos los datos del inventario para el prompt."""
    # Conteos con diferencia
    arts = q(DB_INV, """
        SELECT c.id_effi, c.nombre, c.bodega, c.inventario_teorico AS teorico,
               c.inventario_fisico AS fisico, c.diferencia, c.costo_manual,
               ROUND(c.diferencia * c.costo_manual, 0) AS impacto,
               COALESCE(r.grupo,'') AS tipo
        FROM inv_conteos c
        LEFT JOIN inv_rangos r ON r.id_effi = c.id_effi
        WHERE c.fecha_inventario = %s AND c.excluido = 0
        ORDER BY ABS(c.diferencia * COALESCE(c.costo_manual,0)) DESC
    """, (fecha,))

    # Trazabilidad reciente para los artículos con diferencia
    traz_detalle = {}
    for a in arts:
        if float(a['diferencia'] or 0) == 0:
            continue
        movs = q(DB_EFFI, """
            SELECT LEFT(transaccion,50) AS transaccion, cantidad, LEFT(fecha,16) AS fecha,
                   tipo_de_movimiento, vigencia_de_transaccion
            FROM zeffi_trazabilidad
            WHERE id_articulo = %s AND bodega = 'Principal'
              AND fecha >= DATE_SUB(%s, INTERVAL 30 DAY)
              AND vigencia_de_transaccion = 'Transacción vigente'
            ORDER BY fecha DESC LIMIT 15
        """, (a['id_effi'], fecha))
        traz_detalle[a['id_effi']] = movs

    # Observaciones registradas
    obs = q(DB_INV, """
        SELECT tipo, descripcion, detalle FROM inv_observaciones
        WHERE fecha_inventario = %s ORDER BY created_at
    """, (fecha,))

    # Inventario anterior para comparar
    fecha_anterior = q(DB_INV, """
        SELECT MAX(fecha_inventario) AS f FROM inv_conteos
        WHERE fecha_inventario < %s
    """, (fecha,))[0]['f']

    comparacion = []
    if fecha_anterior:
        for a in arts:
            prev = q(DB_INV, """
                SELECT inventario_fisico, inventario_teorico, diferencia
                FROM inv_conteos WHERE fecha_inventario = %s AND id_effi = %s AND bodega = 'Principal' AND excluido = 0
            """, (fecha_anterior, a['id_effi']))
            if prev:
                comparacion.append({
                    'id_effi': a['id_effi'], 'nombre': a['nombre'],
                    'fis_anterior': float(prev[0]['inventario_fisico'] or 0),
                    'fis_actual': float(a['fisico'] or 0),
                    'dif_anterior': float(prev[0]['diferencia'] or 0),
                    'dif_actual': float(a['diferencia'] or 0)
                })

    return {
        'fecha': fecha, 'fecha_anterior': str(fecha_anterior) if fecha_anterior else None,
        'articulos': arts, 'trazabilidad': traz_detalle,
        'observaciones': obs, 'comparacion': comparacion
    }


def construir_prompt(datos):
    """Construye el prompt para el análisis IA."""
    fecha = datos['fecha']
    arts = datos['articulos']
    total = len(arts)
    con_dif = [a for a in arts if float(a['diferencia'] or 0) != 0]
    exactos = total - len(con_dif)
    sobrantes = [a for a in con_dif if float(a['diferencia'] or 0) > 0]
    faltantes = [a for a in con_dif if float(a['diferencia'] or 0) < 0]

    # Tabla de artículos
    tabla = "| Cód | Artículo | Tipo | Teórico | Físico | Dif | Impacto $ |\n|---|---|---|---|---|---|---|\n"
    for a in arts:
        dif = float(a['diferencia'] or 0)
        if dif == 0:
            continue
        tabla += f"| {a['id_effi']} | {a['nombre'][:40]} | {a['tipo']} | {float(a['teorico'] or 0):.2f} | {float(a['fisico'] or 0):.2f} | {dif:+.2f} | ${int(a['impacto'] or 0):,} |\n"

    # Trazabilidad
    traz_txt = ""
    for eid, movs in datos['trazabilidad'].items():
        art = next((a for a in arts if a['id_effi'] == eid), None)
        if not art:
            continue
        traz_txt += f"\n### {eid} — {art['nombre'][:40]}\n"
        for m in movs[:8]:
            traz_txt += f"  {m['fecha']} | {m['cantidad']} | {m['transaccion']}\n"

    # Observaciones
    obs_txt = "\n".join(f"- [{o['tipo']}] {o['descripcion']}" for o in datos['observaciones']) if datos['observaciones'] else "Ninguna"

    # Comparación con anterior
    comp_txt = ""
    if datos['comparacion']:
        comp_txt = f"\n### Comparación con inventario anterior ({datos['fecha_anterior']})\n"
        for c in datos['comparacion']:
            if c['dif_anterior'] == 0 and c['dif_actual'] == 0:
                continue
            comp_txt += f"- {c['id_effi']} {c['nombre'][:35]}: antes dif={c['dif_anterior']:+.1f}, ahora dif={c['dif_actual']:+.1f}\n"

    prompt = f"""Eres un analista de inventario de Origen Silvestre, una empresa colombiana de productos agroecológicos (miel, chocolate, cremas, propóleo).

Genera un ANÁLISIS EJECUTIVO del inventario parcial del {fecha}. Habla como analista profesional dirigiéndote al director de la empresa. En español, claro, sin tecnicismos innecesarios.

## Datos del inventario
- {total} artículos contados, {exactos} coinciden exacto, {len(sobrantes)} sobrantes, {len(faltantes)} faltantes
- Valor teórico: ${sum(float(a['teorico'] or 0) * float(a['costo_manual'] or 0) for a in arts):,.0f}
- Valor físico: ${sum(float(a['fisico'] or 0) * float(a['costo_manual'] or 0) for a in arts):,.0f}

## Artículos con diferencia
{tabla}

## Trazabilidad reciente (últimos 30 días)
{traz_txt}

## Observaciones registradas
{obs_txt}
{comp_txt}

## Instrucciones para tu análisis
1. RESUMEN EJECUTIVO (3-4 líneas máximo): qué pasó en este inventario
2. PROBLEMAS SISTÉMICOS: identifica patrones (no lista artículo por artículo, agrupa por causa)
3. CAUSAS RAÍZ: por qué están pasando estos descuadres
4. ERRORES ARRASTRADOS: qué viene de antes y qué es nuevo
5. ACCIONES CONCRETAS: qué debe hacer la empresa para mejorar (máximo 5 acciones)
6. PRIORIDAD: qué corregir primero

Sé directo, no repitas los datos que ya están en la tabla. Analiza, interpreta y recomienda. Entre 600 y 1000 palabras. IMPORTANTE: completa TODAS las 6 secciones, no te cortes."""

    return prompt


def generar_analisis(fecha):
    """Genera el análisis IA y lo guarda como PDF."""
    import weasyprint

    datos = recopilar_datos(fecha)
    prompt = construir_prompt(datos)

    # Llamar directo a Gemini API
    try:
        env_path = os.path.join(BASE_DIR, 'scripts', '.env')
        api_key = ''
        with open(env_path) as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break

        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
        resp = requests.post(gemini_url, json={
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': 8000, 'temperature': 0.3}
        }, timeout=90)
        data = resp.json()
        analisis = data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        analisis = f'Error al consultar IA: {e}'

    # Convertir markdown a HTML
    import markdown
    html_body = markdown.markdown(analisis, extensions=['tables', 'nl2br'])

    fecha_fmt = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d de %B de %Y').replace(
        'March','marzo').replace('April','abril').replace('May','mayo').replace(
        'January','enero').replace('February','febrero').replace('June','junio').replace(
        'July','julio').replace('August','agosto').replace('September','septiembre').replace(
        'October','octubre').replace('November','noviembre').replace('December','diciembre')

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@page {{ size: letter; margin: 18mm 15mm; }}
body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.6; }}
h1 {{ font-size: 18pt; margin: 0 0 4px; color: #111; }}
h2 {{ font-size: 13pt; margin: 20px 0 8px; padding-bottom: 3px; border-bottom: 2px solid #00C853; color: #111; }}
h3 {{ font-size: 11pt; margin: 14px 0 4px; color: #333; }}
.subtitle {{ font-size: 10pt; color: #666; margin: 0 0 16px; }}
.header-row {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
.logo {{ font-size: 24pt; font-weight: 700; color: #00C853; }}
.badge {{ display: inline-block; background: #f0fdf4; border: 1px solid #bbf7d0; color: #16a34a; font-size: 8pt; font-weight: 600; padding: 2px 8px; border-radius: 4px; margin-bottom: 12px; }}
p {{ margin: 6px 0; }}
li {{ margin: 3px 0; }}
strong {{ color: #111; }}
</style>
</head><body>
<div class="header-row">
    <div>
        <h1>Análisis IA — Inventario Físico</h1>
        <p class="subtitle">Origen Silvestre — {fecha_fmt}</p>
    </div>
    <div class="logo">OS</div>
</div>
<div class="badge">Generado por IA · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
<p>{html_body}</p>
</body></html>"""

    output_dir = os.path.join(BASE_DIR, 'inventario', 'informes')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'analisis_ia_{fecha}.pdf')
    weasyprint.HTML(string=html).write_pdf(output_path)
    print(f'PDF generado: {output_path}')
    return output_path, analisis


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fecha', required=True)
    args = parser.parse_args()
    path, texto = generar_analisis(args.fecha)
    print(f'\n{texto}')
