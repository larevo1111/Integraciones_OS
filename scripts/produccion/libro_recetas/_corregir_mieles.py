#!/usr/bin/env python3
"""Corrige recetas de mieles (28 productos + granel 373/586/346/134).

Patrones detectados via análisis de match cantidad producida = cantidad envase:
- 150g → envase 86 (110cc) + etiqueta 290/578/351
- 275g → envase 87 (230cc) + etiqueta 291/577/352
- 640g → envase 88 (500cc) + etiqueta 262/353
- 1000g → envase 85 (750cc) + etiqueta 263/354
- Chocomiel 135cc → envase 86 (110cc) + etiqueta 344
- Chocomiel 250cc → envase 87 (230cc) + etiqueta 343
- Degustaciones 65g → envase 232 (50cc)

Materia prima:
- 373 = Miel filtrada y pasteurizada x kilo (granel miel Os común)
- 346 = DS Chocomiel 80/20 x kg (granel chocomiel)
- 586 = Miel filtrada x kilo El Carmen (granel variante)
- Panal = 373 también, se suma trozo de panal (no hay cod específico consistente)
- Etiqueta tapa 90 siempre va 1:1
"""
from override_receta import override


# ── MIEL OS VIDRIO (linea principal) ────────────────────────────────────
MIEL_OS_VIDRIO = [
    # (cod, gramos, envase, etiqueta, n_ops)
    ('13',  150,  '86', '290', 18),
    ('14',  275,  '87', '291', 15),
    ('15',  640,  '88', '262', 29),
    ('239', 1000, '85', '263', 30),
]
for cod, grs, env, etq, n in MIEL_OS_VIDRIO:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n, 'notas': (
            f'Miel Os Vidrio {grs}g. OPs multi-producto (envasan 150/275/640/1000 juntos). '
            f'Por unidad: {kg}kg miel granel (373) + envase {env} + etiqueta {etq} + '
            f'etiqueta tapa 90. Envase confirmado por match 1:1 cantidad en ≥85% OPs. '
            f'Densidad miel ~1.28 g/ml.'
        ),
        'materiales': [
            {'cod': '373', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── MIEL OS VIDRIO SIN ETIQUETAR ────────────────────────────────────────
MIEL_SIN_ETQ = [
    ('548', 150,  '86', 4),
    ('546', 275,  '87', 4),
    ('547', 640,  '88', 3),
    ('550', 1000, '85', 5),
]
for cod, grs, env, n in MIEL_SIN_ETQ:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n, 'notas': (
            f'Miel Os Vidrio {grs}g SIN ETIQUETAR (producto intermedio). '
            f'Por unidad: {kg}kg miel 373 + envase {env} + etiqueta tapa 90. '
            f'Las etiquetas se agregan en OP posterior.'
        ),
        'materiales': [
            {'cod': '373', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
    })

# ── MIEL CARMEN CRISTALIZADA ────────────────────────────────────────────
MIEL_CARMEN = [
    ('347', 150,  '86', '351', 1),
    ('348', 275,  '87', '352', 2),
    ('349', 640,  '88', '353', 1),
]
for cod, grs, env, etq, n in MIEL_CARMEN:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'media', 'estado': 'validada',
        'n_ops': n, 'notas': (
            f'Miel Os Carmen Cristalizada {grs}g. Variante específica (miel cristalizada de El Carmen). '
            f'Por unidad: {kg}kg miel granel 586 (El Carmen) + envase {env} + etiqueta {etq} + tapa 90.'
        ),
        'materiales': [
            {'cod': '586', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── MIEL PANAL ───────────────────────────────────────────────────────────
# Panal incluye trozos de panal — granel es miel + panal. Aproximo como miel con nota.
MIEL_PANAL = [
    ('163', 150, '86', '578', 8),
    ('164', 275, '87', '577', 9),
    ('240', 640, '88', None, 3),
]
for cod, grs, env, etq, n in MIEL_PANAL:
    kg = grs / 1000.0
    mats = [
        {'cod': '373', 'cantidad_por_lote': kg * 0.8, 'ratio_por_unidad': kg * 0.8},
        {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ]
    if etq:
        mats.append({'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'media', 'estado': 'borrador',
        'n_ops': n, 'notas': (
            f'Miel Panal {grs}g. REQUIERE CONFIRMACIÓN: el panal se suma a la miel '
            f'(estimado 80% miel 373 + 20% panal). Envase {env}. Etiqueta {etq or "pendiente"}. '
            f'Panal no tiene código propio consistente en histórico — Santi debe validar.'
        ),
        'materiales': mats,
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.05, 'costo_unit': 7000}],
    })

# ── CHOCOMIEL ───────────────────────────────────────────────────────────
CHOCOMIELES = [
    # (cod, ml, envase, etiqueta, n_ops)
    ('355', 135, '86',  '344', 21),
    ('11',  250, '87',  '343', 22),
]
for cod, ml, env, etq, n in CHOCOMIELES:
    # Chocomiel granel 346 — densidad similar a miel
    kg = ml / 1000.0 * 1.10  # ~1.1 g/ml
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n, 'notas': (
            f'Chocomiel {ml}cc. Mezcla chocolate+miel. Granel cod 346 (DS Chocomiel 80/20 x kg). '
            f'Por unidad: ~{kg:.3f}kg granel 346 + envase {env} + etiqueta {etq} + tapa 90.'
        ),
        'materiales': [
            {'cod': '346', 'cantidad_por_lote': round(kg, 4), 'ratio_por_unidad': round(kg, 4)},
            {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── Chocomiel degustación + Miel degustación (65g) ───────────────────────
override({
    'cod_articulo': '360', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 9,
    'notas': 'Chocomiel degustación 65g. Envase 232 (50cc). Etiqueta no confirmada (tal vez 344 reutilizada).',
    'materiales': [
        {'cod': '346', 'cantidad_por_lote': 0.065 * 1.10, 'ratio_por_unidad': 0.0715},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

override({
    'cod_articulo': '306', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'borrador',
    'n_ops': 3,
    'notas': 'Miel Os degustación 65g. Envase 232 (50cc). Etiqueta pendiente de confirmar con Santi.',
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.065, 'ratio_por_unidad': 0.065},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# ── MIEL AROMÁTICAS (de Fuego, Aromatica, infusionadas) ─────────────────
# Son variantes sabor — usan miel base + infusión. Dejo como borrador con hipótesis.
MIEL_VARIANTES = [
    ('387', 275, 'Miel de Fuego', 7, 'Infusión con picante — revisar ingredientes'),
    ('384', 275, 'Miel Aromática', 6, 'Infusión con hierbas aromáticas — revisar ingredientes'),
    ('382', 265, 'Miel Infus Ajo', 1, 'Solo 1 OP — revisar con Santi'),
    ('385', 265, 'Miel Infus Aloe', 1, 'Solo 1 OP — revisar con Santi'),
]
for cod, grs, name, n, extra in MIEL_VARIANTES:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'mieles',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'baja', 'estado': 'borrador',
        'n_ops': n,
        'notas': (f'{name} {grs}g. Base aproximada: miel 373 + envase 87 + tapa 90. '
                  f'{extra}. PENDIENTE revisar ingredientes aromáticos específicos.'),
        'materiales': [
            {'cod': '373', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── GRANELES (materia prima intermedia) ──────────────────────────────────
# 373 = Miel filtrada y pasteurizada x kilo — granel principal (filtrado + pasteurizado de miel cruda)
override({
    'cod_articulo': '373', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 8,
    'notas': ('Miel filtrada y pasteurizada x KILO — granel base para todas las mieles Os. '
              'Proceso: filtrar miel cruda MIEL APICA X KILO (143) y pasteurizar. '
              'Rendimiento ~95% por mermas en filtrado.'),
    'materiales': [
        {'cod': '143', 'cantidad_por_lote': 1.05, 'ratio_por_unidad': 1.05},
    ],
    'costos': [{'tipo_costo_id': 8, 'nombre': 'ENVASADO MIEL APICA (INCLUYE FILTRADO)',
                'cantidad_por_lote': 1, 'costo_unit': 500}],
})

# 586 = Miel filtrada El Carmen — análogo pero de otra fuente
override({
    'cod_articulo': '586', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1,
    'notas': ('Miel filtrada y pasteurizada El Carmen. Solo 1 OP histórica (2026-04-22). '
              'Variante de 373 pero con materia prima de El Carmen. Revisar cod exacto de miel cruda El Carmen.'),
    'materiales': [
        {'cod': '143', 'cantidad_por_lote': 1.05, 'ratio_por_unidad': 1.05},
    ],
    'costos': [{'tipo_costo_id': 8, 'nombre': 'ENVASADO MIEL APICA (INCLUYE FILTRADO)',
                'cantidad_por_lote': 1, 'costo_unit': 500}],
})

# 346 = DS Chocomiel 80/20 x kg — granel de chocomiel
override({
    'cod_articulo': '346', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'borrador',
    'n_ops': 18,
    'notas': ('Chocomiel granel — mezcla 80% miel 373 + 20% chocolate o cacao. '
              'REQUIERE verificar composición exacta. Se usa como granel para chocomiel 135/250cc.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.80, 'ratio_por_unidad': 0.80},
        {'cod': '73', 'cantidad_por_lote': 0.20, 'ratio_por_unidad': 0.20},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 134 = Extracto vainilla en miel — mezcla específica, dejo borrador
override({
    'cod_articulo': '134', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 3,
    'notas': ('Extracto de vainilla en miel — PENDIENTE revisar proporciones exactas miel/vainilla. '
              'Se usa como ingrediente en la cobertura 73%.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.2, 'costo_unit': 7000}],
})

# Resto: DS Bombón, Miel plástico 500g, Miel San Miguel (kilo) — borrador
override({
    'cod_articulo': '488', 'familia': 'mieles',
    'patron': 'lote_fijo', 'unidad': 'und', 'cantidad_lote_std': 50,
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1,
    'notas': ('DS Bombón Chocolate Relleno Miel — producto compuesto. Solo 1 OP. '
              'Requiere análisis específico (bombón + relleno de miel).'),
    'materiales': [],
    'costos': [],
})

override({
    'cod_articulo': '9', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1,
    'notas': ('Miel Os Plástico 500g — envase plástico en lugar de vidrio. Solo 1 OP. '
              'Revisar envase plástico exacto (puede ser cod 113 o similar).'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.500, 'ratio_por_unidad': 0.500},
        {'cod': '491', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},  # etiqueta plástica 500g
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

override({
    'cod_articulo': '60', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'borrador',
    'n_ops': 5,
    'notas': ('MIEL SAN MIGUEL filtrada x kilo — granel miel de San Miguel. '
              'Variante regional. Revisar con Santi el cod de materia prima.'),
    'materiales': [
        {'cod': '143', 'cantidad_por_lote': 1.05, 'ratio_por_unidad': 1.05},
    ],
    'costos': [{'tipo_costo_id': 8, 'nombre': 'ENVASADO MIEL APICA (INCLUYE FILTRADO)',
                'cantidad_por_lote': 1, 'costo_unit': 500}],
})

print("✓ Mieles (29) procesadas")
