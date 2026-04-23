#!/usr/bin/env python3
"""Corrige recetas Crema de Maní (5 productos).

Mapeo envase-etiqueta por producto (verificado SQL):
- 130g (25):  envase 135 (130cc) + etiqueta 301 (Crema Maní 130) + tapa 90
- 230g (187): envase 87 (230cc)  + etiqueta 302 (Crema Maní 230) + tapa 90
- 500g (241): envase 88 (500cc)  + etiqueta 264 (Crema Maní 500) + tapa 90
- 65g (305):  envase 232 (50cc)  + etiqueta 301 (reutiliza 130) + tapa 90
- 1kg (151):  granel — es la materia prima, no se envasa
"""
from override_receta import override

# Crema mani envasada
ENVASADOS = [
    # (cod, gramos, envase, etiqueta, n_ops)
    ('25',  130, '135', '301', 23),
    ('187', 230, '87',  '302', 20),
    ('241', 500, '88',  '264', 26),
]
for cod, grs, env, etq, n in ENVASADOS:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'cremas_mani',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n,
        'notas': (
            f'Crema de Maní {grs}g. OPs multi-producto (envasan 130/230/500 juntos). '
            f'Por unidad: {kg}kg granel 151 + envase {env} + etiqueta {etq} + tapa 90. '
            f'Match confirmado cantidad 1:1 en ≥80% OPs.'
        ),
        'materiales': [
            {'cod': '151', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# Degustación
override({
    'cod_articulo': '305', 'familia': 'cremas_mani',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 13,
    'notas': ('Crema Maní degustación 65g. Envase 232 (50cc). '
              'Etiqueta no específica — revisar con Santi si hay etiqueta 65 dedicada.'),
    'materiales': [
        {'cod': '151', 'cantidad_por_lote': 0.065, 'ratio_por_unidad': 0.065},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# Granel crema maní (materia prima interna)
override({
    'cod_articulo': '151', 'familia': 'cremas_mani',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 29,
    'notas': ('Crema de Maní granel (materia prima). '
              'Proceso: tostar maní sin cáscara + moler. '
              'Rendimiento ~1:1 (1kg maní → 1kg crema).'),
    'materiales': [
        {'cod': '114', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

print("✓ Cremas de Maní (5) procesadas")
