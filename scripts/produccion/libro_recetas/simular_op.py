#!/usr/bin/env python3
"""Simula una OP usando la receta propuesta y compara contra la última OP real.

Lógica:
1. Tomar la ÚLTIMA OP vigente del producto.
2. Construir receta y aplicarla a la misma cantidad producida.
3. Diffear material por material, co-producto por co-producto, costo por costo.
4. Reportar discrepancias en % (tolerancia 5% materiales, 10% costos).

Uso:
  python3 simular_op.py <cod>
"""
import sys
from _common import q_effi, to_float, FECHA_INICIO_UNIVERSO
from construir_receta import construir
from dossier_producto import detalle_op


TOL_MATERIAL = 0.05   # 5%
TOL_COSTO = 0.10      # 10%


def ultima_op(cod: str):
    r = q_effi(
        """
        SELECT DISTINCT ap.id_orden, LEFT(e.fecha_de_creacion, 19) AS fecha
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia='Orden vigente' AND e.vigencia='Vigente'
          AND e.fecha_de_creacion >= %s
        ORDER BY e.fecha_de_creacion DESC
        LIMIT 1
        """,
        (cod, FECHA_INICIO_UNIVERSO),
    )
    return r[0] if r else None


def simular(cod: str):
    op = ultima_op(cod)
    if not op:
        print(f'Sin OPs vigentes para cod={cod}')
        return

    det = detalle_op(op['id_orden'])
    cant_real = sum(to_float(p['cantidad']) for p in det['producidos'] if p['cod'] == cod)

    # Construir receta con esa cantidad como referencia
    receta = construir(cod, cant_real)

    print('=' * 80)
    print(f"SIMULACIÓN  cod={cod}  {receta['nombre']}")
    print(f"OP de referencia: {op['id_orden']}  fecha {op['fecha']}  cantidad real={cant_real}")
    print('=' * 80)

    # ─── Materiales ──────────────────────────────────────────────────
    real_mat = {
        m['cod']: {
            'cantidad': to_float(m['cantidad']),
            'costo_unit': to_float(m.get('costo_unit') or 0),
            'nombre': m['nombre'],
        }
        for m in det['materiales']
    }
    prop_mat = {
        m['cod']: {
            'cantidad': m['cantidad_por_lote'],
            'costo_unit': m['costo_unit_actual'],
            'nombre': m['nombre'],
        }
        for m in receta['materiales']
    }

    print('\nMATERIALES — diff:')
    print(f"{'COD':<6} {'NOMBRE':<40} {'REAL':>10} {'PROP':>10} {'DIFF%':>8} {'STATUS':<8}")
    mat_problemas = 0
    for cod_m in sorted(set(real_mat) | set(prop_mat)):
        r = real_mat.get(cod_m)
        p = prop_mat.get(cod_m)
        n = (r or p)['nombre'][:39] if (r or p) else ''
        if r and p:
            diff = (p['cantidad'] - r['cantidad']) / max(r['cantidad'], 0.001)
            status = 'OK' if abs(diff) <= TOL_MATERIAL else 'WARN'
            if status == 'WARN':
                mat_problemas += 1
            print(f"{cod_m:<6} {n:<40} {r['cantidad']:>10.4f} {p['cantidad']:>10.4f} {diff*100:>+7.1f}% {status:<8}")
        elif r:
            print(f"{cod_m:<6} {n:<40} {r['cantidad']:>10.4f} {'—':>10} {'—':>8} FALTA_P")
            mat_problemas += 1
        else:
            print(f"{cod_m:<6} {n:<40} {'—':>10} {p['cantidad']:>10.4f} {'—':>8} EXTRA_P")
            mat_problemas += 1

    # ─── Co-productos ────────────────────────────────────────────────
    real_prod = {
        pp['cod']: to_float(pp['cantidad'])
        for pp in det['producidos']
    }
    prop_prod = {p['cod']: p['cantidad_por_lote'] for p in receta['productos']}

    print('\nPRODUCTOS — diff:')
    print(f"{'COD':<6} {'REAL':>10} {'PROP':>10} {'DIFF%':>8} {'STATUS':<8}")
    prod_problemas = 0
    for cod_p in sorted(set(real_prod) | set(prop_prod)):
        r = real_prod.get(cod_p)
        p = prop_prod.get(cod_p)
        if r and p:
            diff = (p - r) / max(r, 0.001)
            status = 'OK' if abs(diff) <= TOL_MATERIAL else 'WARN'
            if status == 'WARN':
                prod_problemas += 1
            print(f"{cod_p:<6} {r:>10.4f} {p:>10.4f} {diff*100:>+7.1f}% {status:<8}")
        elif r:
            print(f"{cod_p:<6} {r:>10.4f} {'—':>10} {'—':>8} FALTA_P")
            prod_problemas += 1
        else:
            print(f"{cod_p:<6} {'—':>10} {p:>10.4f} {'—':>8} EXTRA_P")

    # ─── Costos ──────────────────────────────────────────────────────
    real_costos = {c['cp']: {'cant': to_float(c['cantidad']), 'ud': to_float(c['costo_ud'])} for c in det['costos']}
    prop_costos = {c['cp']: {'cant': c['cantidad_por_lote'], 'ud': c['costo_unit']} for c in receta['costos_produccion']}

    print('\nCOSTOS PRODUCCIÓN — diff:')
    costo_problemas = 0
    for key in sorted(set(real_costos) | set(prop_costos)):
        r = real_costos.get(key)
        p = prop_costos.get(key)
        if r and p:
            diff_cant = (p['cant'] - r['cant']) / max(r['cant'], 0.001)
            status = 'OK' if abs(diff_cant) <= TOL_COSTO else 'WARN'
            if status == 'WARN':
                costo_problemas += 1
            print(f"  {key[:55]:<55} real={r['cant']:.2f} prop={p['cant']:.2f} diff={diff_cant*100:+.1f}% {status}")
        elif r:
            print(f"  {key[:55]:<55} real={r['cant']:.2f} FALTA_P")
            costo_problemas += 1
        else:
            print(f"  {key[:55]:<55} prop={p['cant']:.2f} EXTRA_P")

    # ─── Veredicto ───────────────────────────────────────────────────
    print('\n' + '=' * 80)
    total = mat_problemas + prod_problemas + costo_problemas
    veredicto = 'VÁLIDA' if total == 0 else f'REVISAR ({total} discrepancias)'
    print(f"VEREDICTO: {veredicto}")
    print(
        f"  Materiales WARN: {mat_problemas}  "
        f"Productos WARN: {prod_problemas}  "
        f"Costos WARN: {costo_problemas}"
    )
    print('=' * 80)
    return {
        'cod': cod, 'op_ref': op['id_orden'],
        'mat_problemas': mat_problemas,
        'prod_problemas': prod_problemas,
        'costo_problemas': costo_problemas,
        'valida': total == 0,
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python3 simular_op.py <cod>')
        sys.exit(1)
    simular(sys.argv[1])
