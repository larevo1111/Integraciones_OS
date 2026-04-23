#!/usr/bin/env python3
"""Corrige recetas de chocolates (17 productos).

Patrones detectados por match cantidad SQL:
BOMBÓN 250g puro (272):  bolsa 143 + etq 283 (del) + etq 528 (tras)
BOMBÓN 500g puro (16):   bolsa 100 + etq 312 (del) + etq 525 (tras)
GRANULADO 250g (410):    bolsa 143 + etq 377 (del) + etq 527 (tras)
GRANULADO 500g (411):    bolsa 100 + etq 376 (del) + etq 526 (tras)
1000g granulado (498):   bolsa 309
1000g bombones (551):    bolsa 309
Chocolate mesa moldeado 93: granel, chocolate mesa 73 + nibs 178 (mezcla)
Chocolate mesa bloque 73: granel, nibs 178 base
"""
from override_receta import override

# ── Chocolates puros envasados ─────────────────────────────────────────
ENVASADOS = [
    # (cod, gramos, bolsa, etq_delantera, etq_trasera, n_ops, presentacion)
    ('272', 250, '143', '283', '528', 50, 'Bombón 250g'),
    ('16',  500, '100', '312', '525', 41, 'Bombón 500g'),
    ('410', 250, '143', '377', '527', 26, 'Granulado 250g'),
    ('411', 500, '100', '376', '526', 22, 'Granulado 500g'),
]
for cod, grs, bolsa, etq_d, etq_t, n, pres in ENVASADOS:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'chocolates',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n,
        'notas': (
            f'Chocolate Puro Cacao 100% {pres}. '
            f'Por unidad: {kg}kg chocolate granel (93 mesa moldeado) + bolsa {bolsa} + '
            f'etiqueta delantera {etq_d} + etiqueta trasera {etq_t}. '
            f'Match envase confirmado por SQL ≥80%.'
        ),
        'materiales': [
            {'cod': '93', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': bolsa, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq_d, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq_t, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.04, 'costo_unit': 7000}],
    })

# ── Chocolates 1000g ────────────────────────────────────────────────────
override({
    'cod_articulo': '498', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 6,
    'notas': ('DS Chocolate 1000g Granulado. Bolsa 309 (plana transparente). '
              'Etiqueta no confirmada. Chocolate granel 93.'),
    'materiales': [
        {'cod': '93', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
        {'cod': '309', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.05, 'costo_unit': 7000}],
})

override({
    'cod_articulo': '551', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 4,
    'notas': ('Chocolate 1000g Bombones. Bolsa 309. Chocolate granel 93.'),
    'materiales': [
        {'cod': '93', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
        {'cod': '309', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.05, 'costo_unit': 7000}],
})

# ── Graneles Chocolate Mesa (73, 74, 93) ────────────────────────────────
# 93 (Chocolate mesa moldeado) — se produce a partir de 73 (chocolate mesa bloque)
override({
    'cod_articulo': '93', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 80,
    'notas': ('Chocolate Mesa Moldeado x kg — granel que se usa en cobertura 319 y productos envasados. '
              'Se produce desde chocolate mesa bloque 73 (24h refinado) + moldeado. Ratio 1:1 aproximado.'),
    'materiales': [
        {'cod': '73', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 6, 'nombre': 'REFINADO Y ENMOLDADO HECTOR BAKAU',
                'cantidad_por_lote': 1, 'costo_unit': 15000}],
})

# 73 (Chocolate Mesa Bloque 24h) — granel base
override({
    'cod_articulo': '73', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 57,
    'notas': ('Chocolate Mesa OS/CF 24H x bloque KG — granel refinado. '
              'Se produce desde nibs de cacao 178 + refinado 24h. '
              'Ratio aproximado: 1kg nibs → ~1kg chocolate (tras refinado).'),
    'materiales': [
        {'cod': '178', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 1, 'nombre': 'REFINADO CACAO 24H CHOCOFRUTS',
                'cantidad_por_lote': 1, 'costo_unit': 15000}],
})

# 74 (Chocolate Mesa Bloque 12h) — variante, 1 OP
override({
    'cod_articulo': '74', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1,
    'notas': ('Chocolate Mesa OS/CF 12H bloque — variante 12h. Solo 1 OP histórica. '
              'Revisar con Santi si se mantiene o solo es variación de 73.'),
    'materiales': [{'cod': '178', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0}],
    'costos': [],
})

# ── Chocolate Puro Granulado x kilo (granel) ────────────────────────────
override({
    'cod_articulo': '478', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 17,
    'notas': ('Chocolate Puro Granulado x Kilo — granel intermedio para presentaciones envasadas. '
              'Base: chocolate mesa moldeado 93.'),
    'materiales': [
        {'cod': '93', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.3, 'costo_unit': 7000}],
})

# ── Productos complejos / 1 OP — marcar borrador con notas ──────────────
BORRADORES = [
    ('173', 'Muestra Chocolate de mesa 2 porciones', 1,
     'Muestra — 1 OP histórica. Revisar con Santi gramaje y presentación.'),
    ('186', 'DS Almendra cacao recubierta x gramo', 1,
     'Variante almendra recubierta. Solo 1 OP. Revisar con Santi.'),
    ('486', 'DS Bombón Chocolate Relleno Maní', 1,
     'Bombón relleno maní. Solo 1 OP. Producto compuesto, requiere análisis específico.'),
    ('487', 'DS Bombón Chocolate Relleno Macadamia', 1,
     'Bombón relleno macadamia. Solo 1 OP. Producto compuesto, requiere análisis específico.'),
    ('558', 'BOLSA FLEX UP con etiquetas choco bombón', 1,
     'Producto compuesto: bolsa + etiquetas pre-ensambladas. Solo 1 OP.'),
    ('559', 'BOLSA FLEX UP con etiquetas choco granulado', 1,
     'Producto compuesto: bolsa + etiquetas pre-ensambladas. Solo 1 OP.'),
    ('579', 'Almendra recubierta chocolate x kilo', 1,
     'Granel almendra recubierta. Solo 1 OP. Revisar con Santi.'),
]
for cod, name, n, note in BORRADORES:
    override({
        'cod_articulo': cod, 'familia': 'chocolates',
        'patron': 'escalable', 'unidad': 'und' if 'und' in name.lower() or 'bombón' in name.lower() or 'muestra' in name.lower() else 'kg',
        'confianza': 'baja', 'estado': 'borrador',
        'n_ops': n, 'notas': note,
        'materiales': [],
        'costos': [],
    })

print("✓ Chocolates (17) procesados")
