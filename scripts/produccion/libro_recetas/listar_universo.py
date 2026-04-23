#!/usr/bin/env python3
"""Lista el universo de productos producidos desde 2025-01-01, agrupados por familia.

Uso:
  python3 listar_universo.py                  # muestra todo
  python3 listar_universo.py --familia mieles # filtra por familia
  python3 listar_universo.py --pendientes     # solo los que NO tienen receta en BD VPS
  python3 listar_universo.py --resumen        # conteos por familia + estado
"""
import sys
from _common import q_effi, DbRecetas, familia_por_nombre, FECHA_INICIO_UNIVERSO


def universo_effi():
    """Devuelve lista de dicts: {cod, nombre, n_ops, ultima_op}."""
    return q_effi(
        """
        SELECT ap.cod_articulo AS cod,
               MAX(ap.descripcion_articulo_producido) AS nombre,
               COUNT(DISTINCT ap.id_orden) AS n_ops,
               MAX(LEFT(e.fecha_de_creacion, 10)) AS ultima_op
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.vigencia = 'Orden vigente'
          AND e.vigencia = 'Vigente'
          AND e.fecha_de_creacion >= %s
          AND UPPER(ap.descripcion_articulo_producido) NOT LIKE 'DESPER%%'
        GROUP BY ap.cod_articulo
        ORDER BY n_ops DESC
        """,
        (FECHA_INICIO_UNIVERSO,),
    )


def recetas_existentes():
    """Devuelve dict {cod_articulo: (estado, confianza)}."""
    with DbRecetas() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cod_articulo, estado, confianza FROM prod_recetas")
            return {r['cod_articulo']: (r['estado'], r['confianza']) for r in cur.fetchall()}


def main():
    args = sys.argv[1:]
    filtro_familia = None
    solo_pendientes = False
    solo_resumen = False

    if '--familia' in args:
        filtro_familia = args[args.index('--familia') + 1]
    if '--pendientes' in args:
        solo_pendientes = True
    if '--resumen' in args:
        solo_resumen = True

    productos = universo_effi()
    existentes = recetas_existentes()

    # Enriquecer con familia + estado receta
    for p in productos:
        p['familia'] = familia_por_nombre(p['nombre'])
        p['receta_estado'], p['receta_confianza'] = existentes.get(
            p['cod'], ('—', '—')
        )

    # Filtros
    if filtro_familia:
        productos = [p for p in productos if p['familia'] == filtro_familia]
    if solo_pendientes:
        productos = [p for p in productos if p['receta_estado'] == '—']

    # Resumen
    if solo_resumen:
        fams = {}
        for p in productos:
            f = p['familia']
            fams.setdefault(f, {'total': 0, 'con_receta': 0, 'validadas': 0})
            fams[f]['total'] += 1
            if p['receta_estado'] != '—':
                fams[f]['con_receta'] += 1
            if p['receta_estado'] == 'validada':
                fams[f]['validadas'] += 1
        print(f"{'FAMILIA':<15} {'TOTAL':>7} {'RECETA':>7} {'VALIDAS':>8}")
        print('-' * 41)
        for f, s in sorted(fams.items(), key=lambda x: -x[1]['total']):
            print(
                f"{f:<15} {s['total']:>7} {s['con_receta']:>7} {s['validadas']:>8}"
            )
        print('-' * 41)
        total = sum(s['total'] for s in fams.values())
        crecta = sum(s['con_receta'] for s in fams.values())
        val = sum(s['validadas'] for s in fams.values())
        print(f"{'TOTAL':<15} {total:>7} {crecta:>7} {val:>8}")
        return

    # Listado detallado
    print(
        f"{'COD':<6} {'NOMBRE':<55} {'FAMILIA':<13} {'OPS':>4} {'ULTIMA':<11} {'ESTADO':<10} {'CONF':<6}"
    )
    print('-' * 108)
    for p in productos:
        nombre = (p['nombre'] or '')[:54]
        print(
            f"{p['cod']:<6} {nombre:<55} {p['familia']:<13} "
            f"{p['n_ops']:>4} {p['ultima_op']:<11} "
            f"{p['receta_estado']:<10} {p['receta_confianza']:<6}"
        )
    print(f"\nTotal: {len(productos)} productos")


if __name__ == '__main__':
    main()
