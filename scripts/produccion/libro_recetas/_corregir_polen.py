#!/usr/bin/env python3
"""Corrige recetas polen puro (3 productos). Los 3 productos de "infusión con polen"
se manejan en familia infusiones.

Matches envase-producto confirmados por SQL (ocurrencia cantidad exacta):
- Polen 80g (20): envase 86 (110cc) — 24/29 OPs match
- Polen 150g (171): envase 87 (230cc) — 28/32 OPs match
- Polen 320g (231): envase 88 (500cc) — 33/35 OPs match

Densidad del polen ~0.65 g/ml (menos denso que miel).
"""
from override_receta import override


POLENES = [
    # (cod, gramos, envase_cod, envase_cc, etiqueta_cod, n_ops)
    ('20',  80,  '86', '110cc', '295', 16),
    ('171', 150, '87', '230cc', '296', 17),
    ('231', 320, '88', '500cc', '297', 15),
]

for cod, grs, env_cod, env_cc, etq_cod, n_ops in POLENES:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod,
        'familia': 'polen',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n_ops, 'ops_referencia': [],
        'notas': (
            f'Polen abeja {grs}g. OPs multi-producto (envasan 80g/150g/320g juntos). '
            f'Por unidad: {kg}kg polen granel (146) + 1 envase {env_cod} ({env_cc}) + '
            f'1 etiqueta {etq_cod} (Polen {grs}) + 1 etiqueta tapa 90. '
            f'Envase confirmado por match de cantidad en ≥80% de OPs. Densidad polen ~0.65 g/ml.'
        ),
        'materiales': [
            {'cod': '146', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env_cod, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq_cod, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [
            {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
             'cantidad_por_lote': 0.03, 'costo_unit': 7000},
        ],
    })

print("✓ 3 polenes puros corregidos")
