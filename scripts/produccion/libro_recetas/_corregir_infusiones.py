#!/usr/bin/env python3
"""Corrige infusiones cacao+menta+polen (3 productos envasados + granel) y Tableta 100% (584)."""
from override_receta import override

# Granel infusión
override({
    'cod_articulo': '339', 'familia': 'infusiones',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 16,
    'notas': ('Granel de infusión de cacao+menta+polen. Mezcla en proceso antes de envasar. '
              'Composición aproximada: cacao granel + polen + menta. REVISAR ratios exactos de composición.'),
    'materiales': [],  # Composición específica requiere revisión directa con Santi
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# Envasados (238=200g, 497=400g, 27=100g)
ENVASADOS = [
    ('27',  100, 'Infusión Cacao+menta+polen 100g',  None, None, None, 1),
    ('238', 200, 'Infusión 200g', '100', '284', '524', 22),
    ('497', 400, 'Infusión 400g', '100', None,  None,  15),
]
for cod, grs, name, bolsa, etq_d, etq_t, n in ENVASADOS:
    kg = grs / 1000.0
    mats = [{'cod': '339', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg}]
    if bolsa:
        mats.append({'cod': bolsa, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    if etq_d:
        mats.append({'cod': etq_d, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    if etq_t:
        mats.append({'cod': etq_t, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    override({
        'cod_articulo': cod, 'familia': 'infusiones',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta' if bolsa else 'baja',
        'estado': 'validada' if bolsa else 'borrador',
        'n_ops': n,
        'notas': (f'{name}. Por unidad: {kg}kg granel 339. '
                  f'{"Bolsa "+bolsa+" + etiquetas." if bolsa else "Bolsa/etiqueta pendiente de confirmar."}'),
        'materiales': mats,
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.07, 'costo_unit': 7000}],
    })

# Tableta Chocolate 100% (cod 584) — 1 OP sola
override({
    'cod_articulo': '584', 'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1,
    'notas': ('Tableta Chocolate 100% — nueva variante (cobertura 100% sin azúcar templada). '
              'Solo 1 OP histórica. Probable receta: cobertura 583 (100% templada) a 50g/unid. '
              'REQUIERE confirmación con Santi.'),
    'materiales': [
        {'cod': '583', 'cantidad_por_lote': 0.050, 'ratio_por_unidad': 0.050},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.0074, 'costo_unit': 7000}],
})

print("✓ Infusiones (4) + Tableta 100% procesadas")
