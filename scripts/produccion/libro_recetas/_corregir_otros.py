#!/usr/bin/env python3
"""Corrige familia "otros" (22 productos) — heterogénea.

Grupos detectados:
1. Graneles tostados: macadamia (196), almendras (508), marañón (516), crema almendra (479)
2. Frutos secos envasados: 509-514 (almendra/macadamia/marañón, 100g y 200g)
3. Mix frutos secos: 316 (100g), 278 (200g)
4. Chocobeetal: 275 granel + 405(130g), 406(230g), 407(90g), 557(65g), 517(50g)
5. Propóleo 65g degustación (307)
6. Envases con panal: 325, 326 (intermedios)
7. DS Crema Macadamia (367)
"""
from override_receta import override

# ── 1. Graneles frutos secos tostados ───────────────────────────────────
GRANELES_FRUTOS = [
    ('196', 'Macadamia', 'macadamia cruda', 10),
    ('508', 'Almendras', 'almendras crudas', 8),
    ('516', 'Marañón', 'marañón crudo', 4),
]
for cod, nom, desc, n in GRANELES_FRUTOS:
    override({
        'cod_articulo': cod, 'familia': 'otros',
        'patron': 'escalable', 'unidad': 'kg',
        'confianza': 'media', 'estado': 'validada',
        'n_ops': n,
        'notas': (f'{nom} tostada x kilo — granel. Proceso: tostar {desc}. '
                  f'Rendimiento aproximado 1:1 (puede haber 5-10% merma por tostado).'),
        'materiales': [],  # Compra directa + tostado
        'costos': [{'tipo_costo_id': 14, 'nombre': 'TOSTADO Y DESCASCARILLADO ARBOL DE CACAO',
                    'cantidad_por_lote': 1, 'costo_unit': 4800}],
    })

override({
    'cod_articulo': '479', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'borrador',
    'n_ops': 4,
    'notas': ('Crema de Almendra x kilo — granel pasta de almendras. '
              'Proceso: tostar almendras + moler. Rendimiento ~1:1. Revisar proceso específico con Santi.'),
    'materiales': [{'cod': '508', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0}],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# ── 2. Frutos secos envasados (bolsa doy pack + etiqueta específica) ────
FRUTOS_ENVASADOS = [
    # (cod, gramos, granel, etq_del, n_ops, nombre)
    ('509', 100, '508', '505', 3, 'Almendra 100g'),
    ('510', 200, '508', '506', 2, 'Almendra 200g'),
    ('511', 200, '196', '504', 4, 'Macadamia 200g'),
    ('512', 100, '196', '503', 4, 'Macadamia 100g'),
    ('513', 100, '516', '501', 4, 'Marañón 100g'),
    ('514', 200, '516', '502', 3, 'Marañón 200g'),
]
for cod, grs, granel, etq, n, name in FRUTOS_ENVASADOS:
    kg = grs / 1000.0
    override({
        'cod_articulo': cod, 'familia': 'otros',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'media', 'estado': 'validada',
        'n_ops': n,
        'notas': (f'{name} envasada. Por unidad: {kg}kg granel {granel} + bolsa doy pack 332 + '
                  f'etiqueta {etq}. Frutos secos se envasan junto en OPs multi-producto.'),
        'materiales': [
            {'cod': granel, 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
            {'cod': '332', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
            {'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        ],
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.02, 'costo_unit': 7000}],
    })

# ── 3. Mix Frutos Secos ──────────────────────────────────────────────────
override({
    'cod_articulo': '316', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 4,
    'notas': ('Mix Frutos Secos 100g. Bolsa doy pack 332 + etiqueta 329 (Mix 100g). '
              'Composición: aproximada 33% almendra + 33% macadamia + 33% marañón (revisar con Santi).'),
    'materiales': [
        {'cod': '508', 'cantidad_por_lote': 0.033, 'ratio_por_unidad': 0.033},
        {'cod': '196', 'cantidad_por_lote': 0.033, 'ratio_por_unidad': 0.033},
        {'cod': '516', 'cantidad_por_lote': 0.034, 'ratio_por_unidad': 0.034},
        {'cod': '332', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '329', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

override({
    'cod_articulo': '278', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'borrador',
    'n_ops': 4,
    'notas': ('Mix Frutos Secos 200g. Bolsa doy pack + etiqueta "Mix 200g" (cod pendiente de verificar). '
              'Composición aproximada 33/33/33% almendra/macadamia/marañón.'),
    'materiales': [
        {'cod': '508', 'cantidad_por_lote': 0.067, 'ratio_por_unidad': 0.067},
        {'cod': '196', 'cantidad_por_lote': 0.067, 'ratio_por_unidad': 0.067},
        {'cod': '516', 'cantidad_por_lote': 0.066, 'ratio_por_unidad': 0.066},
        {'cod': '332', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# ── 4. CHOCOBEETAL (línea de chocolate con betabel) ─────────────────────
override({
    'cod_articulo': '275', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 9,
    'notas': ('Chocobeetal x kg — granel. Chocolate con remolacha/betabel. '
              'Composición específica pendiente de revisar con Santi.'),
    'materiales': [],
    'costos': [],
})

CHOCOBEETAL_ENVASADO = [
    ('405', 130, '86',  '400', 10, 'Chocobeetal 130g'),
    ('406', 230, '87',  '401', 10, 'Chocobeetal 230g'),
    ('407', 90,  '138', '399', 4,  'Chocobeetal 90g'),
    ('557', 65,  '232', '399', 5,  'Chocobeetal 65g deg'),
    ('517', 50,  '232', None,  1,  'Chocobeetal 50g'),
]
for cod, grs, env, etq, n, name in CHOCOBEETAL_ENVASADO:
    kg = grs / 1000.0
    mats = [
        {'cod': '275', 'cantidad_por_lote': kg, 'ratio_por_unidad': kg},
        {'cod': env, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ]
    if etq:
        mats.append({'cod': etq, 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    mats.append({'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1})
    override({
        'cod_articulo': cod, 'familia': 'otros',
        'patron': 'escalable', 'unidad': 'und',
        'confianza': 'media' if n >= 3 else 'baja',
        'estado': 'validada' if n >= 3 else 'borrador',
        'n_ops': n,
        'notas': (f'{name}. Por unidad: {kg}kg granel Chocobeetal 275 + envase {env} + '
                  f'etiqueta {etq or "pendiente"} + tapa 90.'),
        'materiales': mats,
        'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                    'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
    })

# ── 5. Propóleo 65g degustación (307) ────────────────────────────────────
override({
    'cod_articulo': '307', 'familia': 'propoleo',  # fix familia
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 7,
    'notas': ('Propóleo OS degustación 65g. Envase 232 (50cc) + etiqueta 90 (tapa). '
              'Sin etiqueta frontal dedicada — va al granel.'),
    'materiales': [
        {'cod': '147', 'cantidad_por_lote': 0.065, 'ratio_por_unidad': 0.065},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# ── 6. Envases con panal (325, 326) — productos intermedios ─────────────
override({
    'cod_articulo': '325', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 2,
    'notas': ('Envase 230g con panal x und — producto intermedio (envase pre-llenado con panal de miel '
              'que se usa como insumo en Miel Panal 275g).'),
    'materiales': [],
    'costos': [],
})

override({
    'cod_articulo': '326', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 2,
    'notas': ('Envase 110cc con panal — producto intermedio para Miel Panal 150g.'),
    'materiales': [],
    'costos': [],
})

# ── 7. DS Crema Macadamia (productos viejos) ────────────────────────────
override({
    'cod_articulo': '367', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 3,
    'notas': ('DS Crema de Macadamia x gr OCT31 — variante histórica. '
              'Revisar con Santi si se sigue produciendo.'),
    'materiales': [],
    'costos': [],
})

print("✓ Otros (22) procesados")
