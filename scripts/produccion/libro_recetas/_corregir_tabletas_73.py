#!/usr/bin/env python3
"""Corrige recetas tabletas 73% según skill produccion-recetas §3.
Ratios validados en OPs 2191/2194/2195 (2026-04-22)."""
from override_receta import override


# Tabletas SIN empacar (480-484) — receta por unidad (50g)
# Patrón lote_fijo (moldería 136 unid típico) pero el ratio es fijo por unidad.
# Uso escalable porque la moldería varía por OP y lo realmente estable es el ratio.

# Puro: 50g cobertura
override({
    'cod_articulo': '480',
    'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'cantidad_lote_std': None,
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 5, 'ops_referencia': ['2194', '2065', '2033', '1950', '1918'],
    'notas': ('Tableta puro 50g sin empacar. Cobertura 319 a 0.050 kg/unid (100% cobertura, sin inclusión). '
              'M.O. ~0.0074h/unid (1h por 136 unid). Ratio validado en skill §3 y OP 2194.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.050, 'ratio_por_unidad': 0.050},
    ],
    'costos': [
        {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
         'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
})

# Mani: 35g cobertura + 15g maní
override({
    'cod_articulo': '481',
    'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'cantidad_lote_std': None,
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 3, 'ops_referencia': ['2194', '2063'],
    'notas': ('Tableta maní 50g sin empacar. 35g cobertura 319 + 15g maní 114 (70%/30%). '
              'Ratio validado en skill §3 y OP 2194.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.035, 'ratio_por_unidad': 0.035},
        {'cod': '114', 'cantidad_por_lote': 0.015, 'ratio_por_unidad': 0.015},
    ],
    'costos': [
        {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
         'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
})

# Macadamia: 35g cobertura + 15g macadamia
override({
    'cod_articulo': '482',
    'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 3, 'ops_referencia': ['2194', '2174', '2064'],
    'notas': ('Tableta macadamia 50g sin empacar. 35g cobertura 319 + 15g macadamia 196. Validado skill §3.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.035, 'ratio_por_unidad': 0.035},
        {'cod': '196', 'cantidad_por_lote': 0.015, 'ratio_por_unidad': 0.015},
    ],
    'costos': [
        {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
         'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
})

# Almendra: 35g cobertura + 15g almendras
override({
    'cod_articulo': '483',
    'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 2, 'ops_referencia': ['2194', '2062'],
    'notas': ('Tableta almendra 50g sin empacar. 35g cobertura 319 + 15g almendras 508. Validado skill §3.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.035, 'ratio_por_unidad': 0.035},
        {'cod': '508', 'cantidad_por_lote': 0.015, 'ratio_por_unidad': 0.015},
    ],
    'costos': [
        {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
         'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
})

# Nibs: 40g cobertura + 10g nibs
override({
    'cod_articulo': '484',
    'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 2, 'ops_referencia': ['2194', '2162'],
    'notas': ('Tableta nibs 50g sin empacar. 40g cobertura 319 + 10g nibs 178 (80%/20%). Validado skill §3.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.040, 'ratio_por_unidad': 0.040},
        {'cod': '178', 'cantidad_por_lote': 0.010, 'ratio_por_unidad': 0.010},
    ],
    'costos': [
        {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
         'cantidad_por_lote': 0.0074, 'costo_unit': 7000},
    ],
})

# Tabletas EMPACADAS (320, 493-496) — receta = su tableta sin empacar + caja 412
# M.O. 4.5h / 136 unid = 0.033h/unid

_EMPACADAS = {
    '320': ('480', 'puro'),
    '494': ('481', 'maní'),
    '493': ('482', 'macadamia'),
    '495': ('483', 'almendra'),
    '496': ('484', 'nibs'),
}
for emp, (sin_emp, sabor) in _EMPACADAS.items():
    override({
        'cod_articulo': emp,
        'familia': 'tabletas',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'alta', 'estado': 'validada',
        'n_ops': 5, 'ops_referencia': ['2195', '2109', '2104', '1972', '1951'],
        'notas': (f'Tableta {sabor} 50g EMPACADA. 1 tableta sin empacar {sin_emp} + 1 caja 412. '
                  f'M.O. 0.033h/unid (~4.5h por 136 unid). Validado en OP 2195.'),
        'materiales': [
            {'cod': sin_emp, 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
            {'cod': '412', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
        ],
        'costos': [
            {'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
             'cantidad_por_lote': 0.033, 'costo_unit': 7000},
        ],
    })

print("✓ 10 tabletas 73% corregidas según skill")
