#!/usr/bin/env python3
"""Corrige recetas cacao_nibs (11 productos).

Match SQL:
NIBS 100g (317): bolsa 332 (doy pack) + etq 331 (del) + etq 530 (tras)
NIBS 200g (308): bolsa 143 (flex up) + etq 289 (del)
ALMENDRA 100g (318): bolsa 332 + etq 330 (del) + etq 539 (tras)
ALMENDRA 200g (315): bolsa 143 + etq 310 (del) + etq 549 (tras)

Graneles:
178 = Nibs de cacao x kg LT — granel nibs (producto intermedio, se obtiene del cacao crudo)
261 = Almendra de cacao tostada x kilo — granel almendras tostadas
80 = Cascarilla de cacao LT x kilo — subproducto del cacao
"""
from override_receta import override

ENVASADOS = [
    # (cod, gramos, producto_granel, bolsa, etq_del, etq_tras, n_ops, tipo)
    ('317', 100, '178', '332', '331', '530', 20, 'Nibs 100g'),
    ('308', 200, '178', '143', '289', None,  9, 'Nibs 200g'),
    ('318', 100, '261', '332', '330', '539', 12, 'Almendra 100g'),
    ('315', 200, '261', '143', '310', '549', 7, 'Almendra 200g'),
]
for cod, grs, granel, bolsa, etq_d, etq_t, n, tipo in ENVASADOS:
    kg = grs / 1000.0
    mats = [
        {'cod': granel, 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
        {'cod': bolsa, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': etq_d, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ]
    if etq_t:
        mats.append({'cod': etq_t, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    override({
        'cod_articulo': cod, 'familia': 'cacao_nibs',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': n,
        'notas': (f'{tipo}. Por unidad: {kg}kg granel {granel} + bolsa {bolsa} + etq {etq_d} '
                  f'{"+ etq trasera "+etq_t if etq_t else ""}. Match confirmado SQL.'),
        'materiales': mats,
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── Graneles ────────────────────────────────────────────────────────────
override({
    'cod_articulo': '178', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 10,
    'notas': ('Nibs de cacao x kg LT — granel. Se obtiene por tostado + descascarillado de cacao crudo. '
              'Se usa como ingrediente en tabletas nibs y como materia prima de chocolate.'),
    'materiales': [],  # Partida directa — en BD como producto comprado LT
    'costos': [{'tipo_costo_id': 7, 'nombre': 'OBTENCIÓN NIBS DE CACAO X KG INTAL',
                'cantidad_por_lote': 1, 'costo_unit': 4845}],
})

override({
    'cod_articulo': '261', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 3,
    'notas': ('Almendra de cacao tostada x kilo — granel. Se obtiene por tostado del cacao crudo '
              '(antes de descascarillar para obtener nibs).'),
    'materiales': [],
    'costos': [{'tipo_costo_id': 14, 'nombre': 'TOSTADO Y DESCASCARILLADO ARBOL DE CACAO',
                'cantidad_por_lote': 1, 'costo_unit': 4800}],
})

override({
    'cod_articulo': '80', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 9,
    'notas': ('Cascarilla de cacao LT x kilo — SUBPRODUCTO del tostado+descascarillado. '
              'No se "produce" independiente — es residuo del proceso. Revisar con Santi si lleva receta propia.'),
    'materiales': [],
    'costos': [],
})

# ── Cremas de macadamia con nibs (1 OP cada una) ────────────────────────
CREMAS_MAC = [
    ('393',  60, 'Crema Macadamia c/nibs 60g',  1),
    ('394', 110, 'Crema Macadamia c/nibs 110g', 1),
    ('395', 200, 'Crema Macadamia c/nibs 200g', 1),
    ('388', 1,   'DS Crema Macadamia c/nibs x gr', 2),
]
for cod, grs, name, n in CREMAS_MAC:
    kg = grs / 1000.0 if grs > 1 else None
    override({
        'cod_articulo': cod, 'familia': 'cacao_nibs',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'baja', 'estado': 'borrador',
        'n_ops': n,
        'notas': (f'{name}. Producto discontinuado o muy escaso (≤2 OPs). '
                  f'Probable composición: crema macadamia + nibs. REQUIERE revisión específica con Santi.'),
        'materiales': [],
        'costos': [],
    })

print("✓ Cacao/Nibs (11) procesados")
