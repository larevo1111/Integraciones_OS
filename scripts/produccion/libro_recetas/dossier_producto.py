#!/usr/bin/env python3
"""Imprime el dossier completo de un producto: todas sus OPs con materiales,
co-productos, costos y pistas de nombres. Para alimentar el razonamiento manual.

Uso:
  python3 dossier_producto.py <cod_articulo> [--n_ops 10]
"""
import sys
from collections import Counter, defaultdict
from _common import q_effi, to_float, peso_desde_nombre, FECHA_INICIO_UNIVERSO


def detalle_op(id_orden: str):
    producidos = q_effi(
        """
        SELECT cod_articulo AS cod, descripcion_articulo_producido AS nombre,
               cantidad, precio_minimo_ud AS precio
        FROM zeffi_articulos_producidos
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
        """,
        (id_orden,),
    )
    materiales = q_effi(
        """
        SELECT cod_material AS cod, descripcion_material AS nombre,
               cantidad, costo_ud AS costo_unit
        FROM zeffi_materiales
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
        """,
        (id_orden,),
    )
    costos = q_effi(
        """
        SELECT costo_de_produccion AS cp, cantidad, costo_ud
        FROM zeffi_otros_costos
        WHERE id_orden = %s AND vigencia = 'Orden vigente'
        """,
        (id_orden,),
    )
    return {'producidos': producidos, 'materiales': materiales, 'costos': costos}


def ops_articulo(cod: str, n: int = 10):
    return q_effi(
        """
        SELECT DISTINCT ap.id_orden,
               LEFT(e.fecha_de_creacion, 19) AS fecha,
               e.nombre_encargado
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia = 'Orden vigente'
          AND e.vigencia = 'Vigente'
          AND e.fecha_de_creacion >= %s
        ORDER BY e.fecha_de_creacion DESC
        LIMIT %s
        """,
        (cod, FECHA_INICIO_UNIVERSO, n),
    )


def nombre_articulo(cod: str) -> str:
    r = q_effi(
        "SELECT nombre FROM zeffi_inventario WHERE id = %s LIMIT 1", (cod,)
    )
    return r[0]['nombre'] if r else '???'


def costo_manual_actual(cod: str) -> float:
    r = q_effi(
        """
        SELECT costo_manual
        FROM zeffi_inventario
        WHERE id = %s AND vigencia = 'Vigente'
        LIMIT 1
        """,
        (cod,),
    )
    return to_float(r[0]['costo_manual']) if r else 0.0


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 dossier_producto.py <cod> [--n_ops 10]')
        sys.exit(1)
    cod = sys.argv[1]
    n = 10
    if '--n_ops' in sys.argv:
        n = int(sys.argv[sys.argv.index('--n_ops') + 1])

    nombre = nombre_articulo(cod)
    peso = peso_desde_nombre(nombre)

    print('=' * 80)
    print(f'DOSSIER  cod={cod}  {nombre}')
    if peso:
        print(f'Pista del nombre: {peso[0]} {peso[1]}')
    print('=' * 80)

    ops = ops_articulo(cod, n)
    if not ops:
        print('(Sin OPs vigentes desde 2025-01-01)')
        return

    # Aggregados para razonamiento
    mats_acc = defaultdict(list)   # cod → [(cant, cant_prod, op_id, nombre, costo)]
    prods_acc = defaultdict(list)  # cod → [(cant, op_id, nombre, precio)]
    costos_acc = defaultdict(list) # tipo → [(cant, cant_prod, costo_ud, op_id)]

    print(f'\nOPs analizadas ({len(ops)}):\n')
    for op in ops:
        d = detalle_op(op['id_orden'])
        # Nuestra cantidad producida en esta OP
        nuestra = sum(to_float(p['cantidad']) for p in d['producidos'] if p['cod'] == cod)
        if nuestra <= 0:
            continue

        print(f"--- OP {op['id_orden']}  {op['fecha']}  encargado={op['nombre_encargado']}")
        print(f"    Producido de NUESTRO {cod}: {nuestra}")

        # Co-productos
        co = [p for p in d['producidos'] if p['cod'] != cod]
        if co:
            print('    Co-productos:')
            for p in co:
                pn = (p['nombre'] or '')[:55]
                pp = peso_desde_nombre(p['nombre'])
                pp_tag = f" [{pp[0]}{pp[1]}]" if pp else ''
                print(f"      {p['cod']:<6} {pn:<55} cant={p['cantidad']} precio={p['precio']}{pp_tag}")
                prods_acc[p['cod']].append({
                    'cant': to_float(p['cantidad']),
                    'op_id': op['id_orden'],
                    'nombre': p['nombre'],
                    'precio': to_float(p['precio']),
                })

        # Materiales
        print('    Materiales:')
        for m in d['materiales']:
            mn = (m['nombre'] or '')[:55]
            mp = peso_desde_nombre(m['nombre'])
            mp_tag = f" [{mp[0]}{mp[1]}]" if mp else ''
            print(
                f"      {m['cod']:<6} {mn:<55} "
                f"cant={m['cantidad']} costo={m['costo_unit']}{mp_tag}"
            )
            mats_acc[m['cod']].append({
                'cant': to_float(m['cantidad']),
                'cant_prod': nuestra,
                'ratio': to_float(m['cantidad']) / nuestra,
                'op_id': op['id_orden'],
                'nombre': m['nombre'],
                'costo': to_float(m['costo_unit']),
            })

        # Costos de producción
        if d['costos']:
            print('    Costos de producción:')
            for c in d['costos']:
                print(
                    f"      {c['cp']:<55} cant={c['cantidad']} costo_ud={c['costo_ud']}"
                )
                costos_acc[c['cp']].append({
                    'cant': to_float(c['cantidad']),
                    'cant_prod': nuestra,
                    'costo_ud': to_float(c['costo_ud']),
                    'op_id': op['id_orden'],
                })
        print()

    # ─── Resumen consolidado ────────────────────────────────────────────
    print('=' * 80)
    print('RESUMEN CONSOLIDADO')
    print('=' * 80)

    # Precio histórico del producto principal (último vigente >100)
    precio_hist = q_effi(
        """
        SELECT precio_minimo_ud
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia = 'Orden vigente' AND e.vigencia = 'Vigente'
          AND CAST(REPLACE(ap.precio_minimo_ud, ',', '') AS DECIMAL(18,4)) > 0
        ORDER BY e.fecha_de_creacion DESC
        LIMIT 1
        """,
        (cod,),
    )
    precio_ult_principal = to_float(precio_hist[0]['precio_minimo_ud']) if precio_hist else 0
    print(f"\nPRECIO mínimo de venta (último vigente de {cod}): {precio_ult_principal}")

    # Materiales consolidados
    print('\nMATERIALES consolidados (por cod):')
    print(f"{'COD':<6} {'NOMBRE':<55} {'N_OPS':>5} {'CANT_PROM':>10} {'RATIO_PROM':>12} {'COSTO_PROM':>10} {'COSTO_ACTUAL':>12}")
    for mcod, entries in sorted(mats_acc.items(), key=lambda x: -len(x[1])):
        n_ops = len(entries)
        cant_prom = sum(e['cant'] for e in entries) / n_ops
        ratio_prom = sum(e['ratio'] for e in entries) / n_ops
        costo_prom = sum(e['costo'] for e in entries) / n_ops
        costo_actual = costo_manual_actual(mcod)
        mname = (entries[0]['nombre'] or '')[:54]
        print(
            f"{mcod:<6} {mname:<55} {n_ops:>5} "
            f"{cant_prom:>10.4f} {ratio_prom:>12.6f} {costo_prom:>10.2f} {costo_actual:>12.2f}"
        )

    # Co-productos consolidados (excluyendo el principal)
    print('\nCO-PRODUCTOS consolidados:')
    for pcod, entries in sorted(prods_acc.items(), key=lambda x: -len(x[1])):
        if pcod == cod:
            continue
        n_ops = len(entries)
        cant_prom = sum(e['cant'] for e in entries) / n_ops
        precios = [e['precio'] for e in entries if e['precio'] > 0]
        precio_ult = precios[0] if precios else 0
        pname = (entries[0]['nombre'] or '')[:54]
        print(
            f"{pcod:<6} {pname:<55} {n_ops:>5} cant_prom={cant_prom:>10.4f} precio_ult={precio_ult}"
        )

    # Costos consolidados
    if costos_acc:
        print('\nCOSTOS DE PRODUCCIÓN consolidados:')
        for tipo, entries in costos_acc.items():
            n_ops = len(entries)
            cant_prom = sum(e['cant'] for e in entries) / n_ops
            costo_ud_prom = sum(e['costo_ud'] for e in entries) / n_ops
            print(
                f"  {tipo:<55} n_ops={n_ops} cant_prom={cant_prom:.2f} costo_ud_prom={costo_ud_prom:.2f}"
            )


if __name__ == '__main__':
    main()
