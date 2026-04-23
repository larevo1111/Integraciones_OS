#!/usr/bin/env python3
"""Construye la receta sugerida de un producto combinando:
- Lo que devuelve sugerir_receta.sugerir_iterativo() (algoritmo estadístico)
- costo_manual actualizado desde zeffi_inventario
- Último precio_min_venta vigente >0 (filtra basura)

Devuelve un dict listo para persistir o inspeccionar.

Uso:
  python3 construir_receta.py <cod> [--cantidad N] [--json]
"""
import json
import os
import sys

# Path al script sugerir_receta
_PROD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROD not in sys.path:
    sys.path.insert(0, _PROD)

from sugerir_atribuido import sugerir_atribuido  # type: ignore
from _common import q_effi, to_float, peso_desde_nombre, familia_por_nombre


def costo_actual(cod: str) -> float:
    r = q_effi(
        "SELECT costo_manual FROM zeffi_inventario WHERE id=%s AND vigencia='Vigente' LIMIT 1",
        (cod,),
    )
    return to_float(r[0]['costo_manual']) if r else 0.0


def info_articulo(cod: str):
    r = q_effi(
        "SELECT id, nombre, costo_manual FROM zeffi_inventario WHERE id=%s LIMIT 1",
        (cod,),
    )
    if not r:
        return {'id': cod, 'nombre': '???', 'costo_manual': 0}
    return r[0]


def ultimo_precio_venta(cod: str, minimo: float = 100.0) -> float:
    """Último precio_min_venta vigente del producto (filtra basura <minimo)."""
    r = q_effi(
        """
        SELECT precio_minimo_ud
        FROM zeffi_articulos_producidos ap
        JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
        WHERE ap.cod_articulo = %s
          AND ap.vigencia = 'Orden vigente' AND e.vigencia = 'Vigente'
          AND CAST(REPLACE(ap.precio_minimo_ud, ',', '.') AS DECIMAL(18,4)) >= %s
        ORDER BY e.fecha_de_creacion DESC
        LIMIT 1
        """,
        (cod, minimo),
    )
    return to_float(r[0]['precio_minimo_ud']) if r else 0.0


def unidad_medida(nombre: str) -> str:
    """Infiere la unidad (und, kg, L) a partir del nombre."""
    n = (nombre or '').lower()
    if ' x kg' in n or 'x kilo' in n or ' x k ' in n or 'x ki' in n:
        return 'kg'
    if 'x l' in n or 'litro' in n:
        return 'L'
    return 'und'


def construir(cod: str, cantidad_ref: float = None):
    """Construye la receta propuesta con atribución multi-producto."""
    info = info_articulo(cod)
    nombre = info['nombre']

    # Primera corrida para detectar patrón
    base = sugerir_atribuido(cod, 1.0, n_ops=10)

    patron = base.get('patron', 'escalable')
    cant_lote = base.get('cantidad_lote_estandar')

    if cantidad_ref is None:
        cantidad_ref = cant_lote if cant_lote else 1.0

    # Recalcular con cantidad ref para cantidades absolutas
    base = sugerir_atribuido(cod, cantidad_ref, n_ops=10)

    # Materiales enriquecidos con costo actual
    materiales = []
    for m in base.get('materiales', []):
        m_info = info_articulo(m['cod'])
        nm = m_info['nombre']
        peso = peso_desde_nombre(nm)
        m_cost = to_float(m_info.get('costo_manual') or 0)
        materiales.append({
            'cod': m['cod'],
            'nombre': nm,
            'cantidad_por_lote': m['cantidad'],
            'ratio_por_unidad': m.get('ratio', 0),
            'costo_unit_actual': m_cost,
            'n_ops_aparece': m.get('n_ops', 0),
            'pista_nombre': peso,
        })
    materiales.sort(key=lambda x: -x['cantidad_por_lote'])

    # Solo producto principal (el motor atribuido NO devuelve co-productos hermanos)
    productos = [{
        'cod': cod, 'nombre': nombre,
        'es_principal': 1,
        'cantidad_por_lote': base.get('cantidad_efectiva', cantidad_ref),
        'ratio_por_unidad': 1.0,
        'precio_min_venta_actual': ultimo_precio_venta(cod),
        'n_ops_aparece': base.get('ops_analizadas', 0),
        'pista_nombre': peso_desde_nombre(nombre),
    }]

    # Costos de producción (M.O. etc)
    costos = []
    for c in base.get('costos', []):
        costos.append({
            'cp': c['cp'],
            'cantidad_por_lote': c['cantidad'],
            'costo_unit': c.get('costo_ud', 0),
        })

    return {
        'cod_articulo': cod,
        'nombre': nombre,
        'familia': familia_por_nombre(nombre),
        'unidad': unidad_medida(nombre),
        'patron': patron,
        'cantidad_lote_std': cant_lote,
        'cantidad_referencia_usada': cantidad_ref,
        'confianza': base.get('confianza', 'baja'),
        'n_ops_analizadas': base.get('ops_analizadas', 0),
        'ops_referencia': base.get('ops_referencia', []),
        'ops_outlier_descartadas': base.get('ops_outlier_descartadas', []),
        'cv_ratios': base.get('cv_ratios', 0),
        'materiales': materiales,
        'productos': productos,
        'costos_produccion': costos,
        'observaciones': base.get('observaciones', []),
    }


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 construir_receta.py <cod> [--cantidad N] [--json]')
        sys.exit(1)
    cod = sys.argv[1]
    cantidad = None
    if '--cantidad' in sys.argv:
        cantidad = float(sys.argv[sys.argv.index('--cantidad') + 1])

    receta = construir(cod, cantidad)

    if '--json' in sys.argv:
        print(json.dumps(receta, indent=2, default=str, ensure_ascii=False))
        return

    # Output legible
    print('=' * 80)
    print(f"RECETA PROPUESTA — cod={receta['cod_articulo']}  {receta['nombre']}")
    print(f"Familia: {receta['familia']}  Unidad: {receta['unidad']}")
    print(
        f"Patrón: {receta['patron']}  "
        f"Lote std: {receta['cantidad_lote_std']}  "
        f"Confianza: {receta['confianza']}  "
        f"OPs: {receta['n_ops_analizadas']}  "
        f"CV: {receta['cv_ratios']}"
    )
    print(f"Ref usada: {receta['cantidad_referencia_usada']}")
    print('=' * 80)

    print('\nMATERIALES:')
    print(f"{'COD':<6} {'NOMBRE':<50} {'CANT':>10} {'COSTO':>10} {'N_OPS':>5} {'PISTA':<15}")
    for m in receta['materiales']:
        nm = (m['nombre'] or '')[:49]
        pista = f"{m['pista_nombre'][0]}{m['pista_nombre'][1]}" if m['pista_nombre'] else '—'
        print(
            f"{m['cod']:<6} {nm:<50} "
            f"{m['cantidad_por_lote']:>10.4f} {m['costo_unit_actual']:>10.2f} "
            f"{m['n_ops_aparece']:>5} {pista:<15}"
        )

    print('\nPRODUCTOS:')
    for p in receta['productos']:
        pn = (p['nombre'] or '')[:49]
        flag = '★' if p['es_principal'] else ' '
        pista = f"{p['pista_nombre'][0]}{p['pista_nombre'][1]}" if p['pista_nombre'] else '—'
        print(
            f"  {flag} {p['cod']:<6} {pn:<50} "
            f"cant={p['cantidad_por_lote']:>10.4f} precio={p['precio_min_venta_actual']:>10.2f} "
            f"pista={pista}"
        )

    if receta['costos_produccion']:
        print('\nCOSTOS DE PRODUCCIÓN:')
        for c in receta['costos_produccion']:
            print(f"  {c['cp']:<55} cant={c['cantidad_por_lote']:>6.2f} costo_ud={c['costo_unit']:>8.2f}")

    if receta['observaciones']:
        print('\nOBSERVACIONES:')
        for o in receta['observaciones']:
            print(f"  • {o}")

    print(f"\nOPs referencia: {receta['ops_referencia']}")
    if receta['ops_outlier_descartadas']:
        print(f"Outliers descartadas: {receta['ops_outlier_descartadas']}")


if __name__ == '__main__':
    main()
