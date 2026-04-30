#!/usr/bin/env python3
"""
Depuración 2026-04-30 — artículos inventariables sin movimiento desde 2025-04-30.

Universo  : 504 cods del inventario físico del 31 marzo 2026 (inv_conteos)
Quitados  : 94 ya anulados en Effi el 29-abr (depuración previa)
Filtro    : SIN movimiento (ventas vigentes, compras vigentes, OPs vigentes
            como material O producto producido) desde 2025-04-30.

Salida    : inventario/analisis_de_inventario/2026-04-30/
              depuracion_inventariables_inactivos.csv
              depuracion_inventariables_inactivos.md
"""
import os
import sys
import csv
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'scripts'))
from lib import inventario, integracion  # type: ignore

OUT_DIR = os.path.join(REPO, 'inventario', 'analisis_de_inventario', '2026-04-30')
os.makedirs(OUT_DIR, exist_ok=True)

CORTE = '2025-04-30'              # ventana: sin movimiento desde esta fecha
FECHA_INV = '2026-03-31'          # inventario base
ANULADOS_CSV = os.path.join(REPO, 'inventario', 'analisis_de_inventario',
                             '2026-04-29', 'depuracion_articulos_inactivos.csv')


def leer_anulados_94():
    """Devuelve set de cods marcados con X (case-insensitive) en la depuración previa."""
    anulados = set()
    with open(ANULADOS_CSV, encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # header
        for row in reader:
            if len(row) >= 3 and row[2].strip().lower() == 'x':
                anulados.add(row[0].strip())
    return anulados


def main():
    anulados = leer_anulados_94()
    print(f"[1/5] Anulados previos cargados: {len(anulados)}")

    # Universo: cods del inventario marzo 31
    with inventario(dict_cursor=True) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT id_effi FROM inv_conteos WHERE fecha_inventario=%s",
            (FECHA_INV,)
        )
        cods_marzo = {r['id_effi'].strip() for r in cur.fetchall() if r['id_effi']}
    print(f"[2/5] Cods en inventario {FECHA_INV}: {len(cods_marzo)}")

    universo_pre = cods_marzo - anulados
    print(f"[3/5] Universo neto (marzo - anulados): {len(universo_pre)}")

    # Cruzar con zeffi_inventario VIGENTES + ventas/compras/OPs en una sola conexión
    with integracion(dict_cursor=True) as conn:
        cur = conn.cursor()
        # Subset vigente del universo
        in_clause = ','.join(['%s'] * len(universo_pre))
        cur.execute(
            f"""SELECT id, nombre, categoria, tipo_de_articulo,
                       stock_total_empresa, costo_manual
                  FROM zeffi_inventario
                 WHERE id IN ({in_clause})""",
            tuple(universo_pre)
        )
        articulos = {r['id'].strip(): r for r in cur.fetchall()}
        print(f"[4/5] Vigentes hoy de ese universo: {len(articulos)}")

        # Diccionarios de movimientos por cod (todos los conteos de una)
        cur.execute(
            f"""SELECT cod_articulo AS cod, COUNT(*) AS n, MAX(fecha_creacion_factura) AS ult
                  FROM zeffi_facturas_venta_detalle
                 WHERE cod_articulo IN ({in_clause})
                   AND vigencia_factura='Vigente'
                   AND fecha_creacion_factura >= %s
                 GROUP BY cod_articulo""",
            tuple(universo_pre) + (CORTE,)
        )
        ventas_recientes = {r['cod'].strip(): r['n'] for r in cur.fetchall()}

        cur.execute(
            f"""SELECT cod_articulo AS cod, COUNT(*) AS n
                  FROM zeffi_facturas_compra_detalle
                 WHERE cod_articulo IN ({in_clause})
                   AND vigencia LIKE '%%vigente%%'
                   AND COALESCE(fecha_compra, fecha_factura) >= %s
                 GROUP BY cod_articulo""",
            tuple(universo_pre) + (CORTE,)
        )
        compras_recientes = {r['cod'].strip(): r['n'] for r in cur.fetchall()}

        cur.execute(
            f"""SELECT cod_material AS cod, COUNT(*) AS n
                  FROM zeffi_materiales
                 WHERE cod_material IN ({in_clause})
                   AND vigencia LIKE '%%vigente%%'
                   AND fecha_creacion >= %s
                 GROUP BY cod_material""",
            tuple(universo_pre) + (CORTE,)
        )
        op_mat_recientes = {r['cod'].strip(): r['n'] for r in cur.fetchall()}

        cur.execute(
            f"""SELECT cod_articulo AS cod, COUNT(*) AS n
                  FROM zeffi_articulos_producidos
                 WHERE cod_articulo IN ({in_clause})
                   AND vigencia LIKE '%%vigente%%'
                   AND fecha_creacion >= %s
                 GROUP BY cod_articulo""",
            tuple(universo_pre) + (CORTE,)
        )
        op_prod_recientes = {r['cod'].strip(): r['n'] for r in cur.fetchall()}

    candidatos = []
    for cod, art in articulos.items():
        if cod in ventas_recientes: continue
        if cod in compras_recientes: continue
        if cod in op_mat_recientes: continue
        if cod in op_prod_recientes: continue
        candidatos.append(art)
    print(f"[5/5] Candidatos sin movimientos desde {CORTE}: {len(candidatos)}")

    # Calcular valor inventario
    def f(v):
        if not v: return 0.0
        try: return float(str(v).replace(',', '.'))
        except: return 0.0

    candidatos_enriched = []
    for a in candidatos:
        cod = a['id'].strip()
        stock = f(a.get('stock_total_empresa'))
        costo = f(a.get('costo_manual'))
        valor = stock * costo
        accion = ('REVISAR — tiene stock' if stock > 0
                  else 'CANDIDATO ANULAR — sin stock')
        # Categorías "no inventariables" puras pero presentes:
        cat = (a.get('categoria') or '').strip()
        tipo = (a.get('tipo_de_articulo') or '').strip()
        if cat == 'GASTOS' or tipo in ('Servicio', 'Activo fijo (Propiedad, planta y equipo)'):
            accion = 'NO TOCAR (catálogo permanente)'
        candidatos_enriched.append({
            'cod': cod,
            'nombre': (a.get('nombre') or '').strip(),
            'x': '',
            'categoria': cat,
            'tipo': tipo,
            'stock_actual': stock,
            'costo_unit': costo,
            'valor_inventario': valor,
            'accion_sugerida': accion,
        })

    # Orden: 1) categoría, 2) cod ascendente
    candidatos_enriched.sort(key=lambda r: (r['categoria'] or 'zzz', int(r['cod']) if r['cod'].isdigit() else 9999))

    # CSV
    csv_path = os.path.join(OUT_DIR, 'depuracion_inventariables_inactivos.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'cod', 'nombre', '', 'categoria', 'tipo',
            'stock', 'costo_unit', 'valor_inventario', 'accion_sugerida'
        ])
        for r in candidatos_enriched:
            writer.writerow([
                r['cod'], r['nombre'], r['x'], r['categoria'], r['tipo'],
                _fmt(r['stock_actual']),
                _fmt(r['costo_unit']),
                _fmt(r['valor_inventario']),
                r['accion_sugerida'],
            ])
    print(f"\nCSV: {csv_path} ({len(candidatos_enriched)} filas)")

    # MD
    md_path = os.path.join(OUT_DIR, 'depuracion_inventariables_inactivos.md')
    _generar_md(md_path, candidatos_enriched, len(cods_marzo), len(anulados),
                len(universo_pre), len(articulos))
    print(f"MD : {md_path}")

    print(f"\nResumen:")
    print(f"  Total inventario marzo 31:        {len(cods_marzo)}")
    print(f"  Anulados previos:                 {len(anulados)}")
    print(f"  Vigentes hoy de ese universo:     {len(articulos)}")
    print(f"  Candidatos sin movimiento 1 año:  {len(candidatos_enriched)}")


def _fmt(n):
    if n == int(n): return str(int(n))
    return f"{n:.2f}".rstrip('0').rstrip('.').replace('.', ',')


def _generar_md(path, rows, total_marzo, anulados, universo_pre, vigentes_hoy):
    # Agrupar por categoría
    por_cat = {}
    for r in rows:
        cat = r['categoria'] or '(sin categoría)'
        por_cat.setdefault(cat, []).append(r)
    valor_total = sum(r['valor_inventario'] for r in rows)
    con_stock = sum(1 for r in rows if r['stock_actual'] > 0)
    sin_stock = len(rows) - con_stock

    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# Depuración inventariables inactivos — 2026-04-30\n\n")
        f.write(f"**Criterio:** vigentes en Effi + presentes en inventario físico "
                f"del 31 marzo 2026 + sin movimientos (ventas/compras/OPs material/OPs producto) "
                f"desde **2025-04-30** (1 año).\n\n")
        f.write(f"## Trazabilidad del universo\n\n")
        f.write(f"| Paso | Cods |\n|---|---|\n")
        f.write(f"| 1. Inventario físico 31-mar-2026 | {total_marzo} |\n")
        f.write(f"| 2. − anulados el 29-abr (94) | {universo_pre} |\n")
        f.write(f"| 3. ∩ vigentes hoy en zeffi_inventario | {vigentes_hoy} |\n")
        f.write(f"| 4. **Sin movimientos desde 2025-04-30** | **{len(rows)}** |\n\n")
        f.write(f"## Resumen\n\n")
        f.write(f"- **Candidatos a depurar: {len(rows)}**\n")
        f.write(f"- Sin stock (anular limpio): {sin_stock}\n")
        f.write(f"- Con stock > 0 (revisar antes): {con_stock}\n")
        f.write(f"- Valor inventario actual de los candidatos: ${valor_total:,.0f}\n\n")
        f.write(f"## Por categoría\n\n")
        f.write(f"| Categoría | N° artículos | Con stock |\n|---|---|---|\n")
        for cat in sorted(por_cat, key=lambda c: -len(por_cat[c])):
            items = por_cat[cat]
            cs = sum(1 for r in items if r['stock_actual'] > 0)
            f.write(f"| {cat} | {len(items)} | {cs} |\n")
        f.write(f"\n## Cómo usar este archivo\n\n")
        f.write(f"1. Abrí `depuracion_inventariables_inactivos.csv` en LibreOffice/Excel.\n")
        f.write(f"2. Marcá con **x** (en columna 3) los que querés ANULAR en Effi.\n")
        f.write(f"3. Guardá el CSV.\n")
        f.write(f"4. Ejecutá `python3 scripts/import_articulo_anular_post.py` para anularlos.\n\n")
        f.write(f"## Lista completa\n\n")
        f.write(f"Ordenada por categoría → cod.\n\n")
        f.write(f"| cod | nombre | categoría | tipo | stock | costo unit | valor | acción |\n")
        f.write(f"|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['cod']} | {r['nombre']} | {r['categoria'] or '—'} | "
                    f"{r['tipo'] or '—'} | {_fmt(r['stock_actual']) if r['stock_actual'] else '—'} | "
                    f"{_fmt(r['costo_unit']) if r['costo_unit'] else '—'} | "
                    f"{_fmt(r['valor_inventario']) if r['valor_inventario'] else '—'} | "
                    f"{r['accion_sugerida']} |\n")


if __name__ == '__main__':
    main()
