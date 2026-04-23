#!/usr/bin/env python3
"""Corrige recetas propóleo (3 productos): razonamiento sobre OPs multi-producto.

Patrón detectado:
- Propóleo 150g (21): envase 86 (110cc) + etiqueta 298 + etiqueta tapa 90
- Propóleo 265g (169): envase 87 (230cc) + etiqueta 299 + etiqueta tapa 90
- Propóleo 600g (237): envase 88 (500cc) + etiqueta 300 + etiqueta tapa 90

Materia prima común: 147 (Propóleo Apica x kilo) — se asigna por peso del producto.
Etiqueta tapa 90 siempre va 1:1.
M.O. ~0.03h por unidad (se distribuye por share de unidades producidas).
"""
from override_receta import override


PROPOLEOS = [
    # (cod, gramos, envase_cod, envase_nombre_corto, etiqueta_cod, n_ops, ejemplo_ops)
    ('21',  150, '86', '110cc', '298', 25, ['446', '310', '271']),
    ('169', 265, '87', '230cc', '299', 26, ['446', '310', '271']),
    ('237', 600, '88', '500cc', '300', 11, ['446', '310', '191']),
]

for cod, grs, env_cod, env_nm, etq_cod, n_ops, ops_ref in PROPOLEOS:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod,
        'familia': 'propoleo',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n_ops, 'ops_referencia': ops_ref,
        'notas': (
            f'Propóleo {grs}g. Se envasa junto a otras presentaciones en OPs multi-producto. '
            f'Por unidad: {kg}kg propóleo granel (147) + 1 envase {env_cod} ({env_nm}) + '
            f'1 etiqueta {etq_cod} (Propóleo {grs}) + 1 etiqueta tapa 90. '
            f'Envase confirmado por correlación 1:1 con producción en OPs históricas.'
        ),
        'materiales': [
            {'cod': '147', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env_cod, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq_cod, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [
            {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
             'cantidad_por_lote': 0.03, 'costo_unit': 7000},
        ],
    })

print("✓ 3 propóleos corregidos con razonamiento sobre envases")
