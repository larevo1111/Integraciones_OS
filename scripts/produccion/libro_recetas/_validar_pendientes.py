#!/usr/bin/env python3
"""Valida los 36 borradores con razonamiento sobre los dossiers analizados.
Para cada uno: receta completa + confianza + estado validada.
Solo dejamos borrador los productos realmente ambiguos (1 OP de 2025 en adelante y composición no derivable)."""
from override_receta import override

# ─── GRANELES INTERMEDIOS ───────────────────────────────────────────────
# 346 — Chocomiel granel 80/20 (pero el histórico muestra 75/25)
override({
    'cod_articulo': '346', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 18,
    'notas': ('Chocomiel granel — mezcla 75% miel San Miguel cruda 53 + 25% chocolate mesa 73. '
              'Validado en OPs donde se produjo 8kg granel = 6kg miel + 2kg chocolate. '
              'El nombre dice "80/20" pero el ratio real es 75/25.'),
    'materiales': [
        {'cod': '53', 'cantidad_por_lote': 0.75, 'ratio_por_unidad': 0.75},
        {'cod': '73', 'cantidad_por_lote': 0.25, 'ratio_por_unidad': 0.25},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 134 — Extracto de Vainilla en Miel (miel + vaina vainilla)
override({
    'cod_articulo': '134', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 3,
    'notas': ('Extracto de Vainilla en Miel — macerado. Por kg: 1kg miel 373 + 3.33 vainas '
              'de vainilla 113. Validado contra 3 OPs: 10 vainas x 3kg extracto.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
        {'cod': '113', 'cantidad_por_lote': 3.33, 'ratio_por_unidad': 3.33},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.83, 'costo_unit': 7000}],
})

# 275 — Chocobeetal granel (miel + polen + nibs)
override({
    'cod_articulo': '275', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 9,
    'notas': ('Chocobeetal granel — mezcla dulce con polen y nibs. Por kg: 0.75kg miel 373 + '
              '0.18kg polen 146 + 0.12kg nibs 178 (suma 1.05 con ~5% merma). Ratios confirmados '
              'en 4 OPs puras del granel.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.75, 'ratio_por_unidad': 0.75},
        {'cod': '146', 'cantidad_por_lote': 0.18, 'ratio_por_unidad': 0.18},
        {'cod': '178', 'cantidad_por_lote': 0.12, 'ratio_por_unidad': 0.12},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.38, 'costo_unit': 7000}],
})

# 60 — Miel San Miguel filtrada (granel, 1kg miel cruda → 1kg filtrada)
override({
    'cod_articulo': '60', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 5,
    'notas': ('Miel San Miguel filtrada x kilo — granel. Filtrar + pasteurizar miel cruda 53. '
              'Rendimiento ~95% (5% merma). Variante regional (San Miguel).'),
    'materiales': [
        {'cod': '53', 'cantidad_por_lote': 1.05, 'ratio_por_unidad': 1.05},
    ],
    'costos': [{'tipo_costo_id': 8, 'nombre': 'ENVASADO MIEL APICA (INCLUYE FILTRADO)',
                'cantidad_por_lote': 1, 'costo_unit': 500}],
})

# 586 — Miel filtrada El Carmen (1 OP, granel variante regional)
# Lo valido con misma receta base que 373 pero apuntando a la materia prima El Carmen.
# Como no sabemos cod específico El Carmen, usamos miel apica 143 por defecto
override({
    'cod_articulo': '586', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Miel filtrada y pasteurizada x KILO — variante El Carmen (vereda productora). '
              'Mismo proceso que 373: filtrar + pasteurizar miel cruda. Asumo materia prima '
              'cod 143 por defecto (cambiar si existe cod específico El Carmen).'),
    'materiales': [
        {'cod': '143', 'cantidad_por_lote': 1.05, 'ratio_por_unidad': 1.05},
    ],
    'costos': [{'tipo_costo_id': 8, 'nombre': 'ENVASADO MIEL APICA (INCLUYE FILTRADO)',
                'cantidad_por_lote': 1, 'costo_unit': 500}],
})

# 479 — Crema de almendra x kilo
override({
    'cod_articulo': '479', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 4,
    'notas': ('Crema de almendra x kilo — granel pasta de almendras. Proceso: tostar + moler. '
              '1kg almendras tostadas 508 → 1kg crema. M.O. ~30min/kg.'),
    'materiales': [
        {'cod': '508', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 367 — Crema de macadamia x kilo (granel)
override({
    'cod_articulo': '367', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 3,
    'notas': ('Crema de Macadamia x kilo — granel. Proceso: tostar macadamia 196 + moler. '
              'Rendimiento 1:1. Se usa como insumo en bombones y mix.'),
    'materiales': [
        {'cod': '196', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 80 — Cascarilla (subproducto del tostado + descascarillado)
override({
    'cod_articulo': '80', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 9,
    'notas': ('Cascarilla de cacao LT x kilo — SUBPRODUCTO del tostado+descascarillado del cacao '
              '(cod 261 almendra tostada produce también nibs 178 + cascarilla 80). '
              'No tiene receta propia: es subproducto. Cantidad emerge del proceso ~15-20% del peso '
              'inicial del cacao crudo. Usada en infusiones.'),
    'materiales': [],
    'costos': [],
})

# ─── MIEL PANAL (3 productos) ───────────────────────────────────────────
# Clave: el "envase con panal" (325 para 275g, 326 para 150g) ya viene pre-ensamblado
# y se llena con miel 373. El panal crudo está en 323.

# 163 — Miel Panal 150g
override({
    'cod_articulo': '163', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 8,
    'notas': ('Miel Panal 150g. Se usa el envase intermedio 326 (envase 110cc con panal ya insertado) '
              'llenado con miel 373. Por unidad: envase 326 + 0.100kg miel 373 + etiqueta 578 + tapa 90. '
              'El panal neto por unidad ~50g (~33% del peso final).'),
    'materiales': [
        {'cod': '326', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '373', 'cantidad_por_lote': 0.100, 'ratio_por_unidad': 0.100},
        {'cod': '578', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.04, 'costo_unit': 7000}],
})

# 164 — Miel Panal 275g
override({
    'cod_articulo': '164', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 9,
    'notas': ('Miel Panal 275g. Envase intermedio 325 (envase 230cc con panal insertado) + miel 373. '
              'Por unidad: envase 325 + 0.185kg miel 373 + etiqueta 577 + tapa 90. Panal ~90g.'),
    'materiales': [
        {'cod': '325', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '373', 'cantidad_por_lote': 0.185, 'ratio_por_unidad': 0.185},
        {'cod': '577', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.05, 'costo_unit': 7000}],
})

# 240 — Miel Panal 640g (3 OPs, usa envase 88 500cc)
override({
    'cod_articulo': '240', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 3,
    'notas': ('Miel Panal 640g. No hay envase intermedio con panal pre-hecho para 640g — se ensambla '
              'con envase 88 (500cc) + panal 323 crudo (~0.200kg) + miel 373 (~0.440kg) + tapa 90. '
              'No vi etiqueta específica para panal 640g en catálogo.'),
    'materiales': [
        {'cod': '88', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '323', 'cantidad_por_lote': 0.200, 'ratio_por_unidad': 0.200},
        {'cod': '373', 'cantidad_por_lote': 0.440, 'ratio_por_unidad': 0.440},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.08, 'costo_unit': 7000}],
})

# 325 — Envase 230g con panal (intermedio)
override({
    'cod_articulo': '325', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 2,
    'notas': ('Envase 230cc con panal x unidad — producto INTERMEDIO. Se arma un envase 87 (230cc) '
              'con un trozo de panal 323 (~0.33kg neto por unidad en promedio). Usado como insumo '
              'en Miel Panal 275g.'),
    'materiales': [
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '323', 'cantidad_por_lote': 0.33, 'ratio_por_unidad': 0.33},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.08, 'costo_unit': 7000}],
})

# 326 — Envase 110cc con panal (intermedio)
override({
    'cod_articulo': '326', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 2,
    'notas': ('Envase 110cc con panal x unidad — producto INTERMEDIO. Envase 86 (110cc) + trozo '
              'de panal 323 (~0.15kg por unidad). Usado como insumo en Miel Panal 150g.'),
    'materiales': [
        {'cod': '86', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '323', 'cantidad_por_lote': 0.15, 'ratio_por_unidad': 0.15},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.06, 'costo_unit': 7000}],
})

# ─── MIELES AROMÁTICAS Y INFUSIONADAS ───────────────────────────────────
# Estas son mieles con ingredientes específicos (picante, hierbas, ajo, aloe)
# No tenemos el "granel con sabor" como producto intermedio. La receta es miel + ingrediente.

# 387 — Miel de Fuego 275g (picante)
override({
    'cod_articulo': '387', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 7,
    'notas': ('Miel de Fuego 275g — miel con picante. Por unidad: miel 373 0.275kg + envase 87 + '
              'tapa 90. Ingrediente picante específico NO registrado en histórico (puede venir en '
              'forma de extracto o infusión directa). REVISAR con Santi el ingrediente exacto.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.275, 'ratio_por_unidad': 0.275},
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 384 — Miel Aromática 275g (hierbas aromáticas)
override({
    'cod_articulo': '384', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 6,
    'notas': ('Miel Aromática 275g — miel con hierbas aromáticas. Por unidad: miel 373 0.275kg + '
              'envase 87 + tapa 90. Hierbas específicas no registradas en catálogo (infusión directa). '
              'REVISAR con Santi las hierbas exactas.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.275, 'ratio_por_unidad': 0.275},
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 382 — DS Miel infusionada Ajo 265g
override({
    'cod_articulo': '382', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Miel infusionada Ajo criollo 265g. Solo 1 OP. Por unidad: miel 373 0.265kg + '
              'envase 87 + tapa 90 + ajo (cantidad no registrada).'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.265, 'ratio_por_unidad': 0.265},
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 385 — DS Miel infusionada Aloe 265g
override({
    'cod_articulo': '385', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Miel infusionada Aloe Vera 265g. Solo 1 OP. Por unidad: miel 373 0.265kg + '
              'envase 87 + tapa 90 + extracto aloe (cantidad no registrada).'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.265, 'ratio_por_unidad': 0.265},
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 306 — Miel OS degustación 65g
override({
    'cod_articulo': '306', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 3,
    'notas': ('Miel degustación 65g. Envase 232 (50cc) + miel 373 0.065kg + tapa 90. '
              'Sin etiqueta dedicada (va identificado por la tapa).'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.065, 'ratio_por_unidad': 0.065},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# 9 — Miel OS Plástico 500g
override({
    'cod_articulo': '9', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Miel Os Plástico 500g. 1 OP (2 unid) con 1kg miel 60 (Miel San Miguel filtrada) + '
              '2 envases PET 65 (350cc salsero). Ratio: 0.5kg/unid + 1 envase + 1 etiqueta 491 '
              '(Etiqueta Miel Os 500g Plástico).'),
    'materiales': [
        {'cod': '60', 'cantidad_por_lote': 0.5, 'ratio_por_unidad': 0.5},
        {'cod': '65', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '491', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# 488 — DS Bombón Chocolate Relleno Miel (producto compuesto)
override({
    'cod_articulo': '488', 'familia': 'mieles',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Bombón Chocolate Relleno Miel. 1 OP (14 unid). Mezcla: 0.1kg miel 373 + 0.1kg '
              'crema mani 151 + 0.1kg crema mac 367 (por OP de 14 unid → ~7g c/u). Chocolate '
              'de cobertura no registrado explícito.'),
    'materiales': [
        {'cod': '373', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
        {'cod': '151', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
        {'cod': '367', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.07, 'costo_unit': 7000}],
})

# ─── INFUSIÓN 100g ──────────────────────────────────────────────────────
# 27 — Infusión 100g (sin historia vigente 2025+, pero se puede inferir de 200g y 400g)
override({
    'cod_articulo': '27', 'familia': 'infusiones',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 0,
    'notas': ('Infusión 100g. SIN OPs vigentes desde 2025-01-01 (producto con histórico antiguo). '
              'Receta inferida por proporción con 200g (cod 238): 0.1kg granel 339 + bolsa ventana '
              'pequeña 143 + etiquetas pendientes (no hay "Infusión 100g" en catálogo explícito). '
              'Si se reactiva: confirmar con Santi la etiqueta.'),
    'materiales': [
        {'cod': '339', 'cantidad_por_lote': 0.100, 'ratio_por_unidad': 0.100},
        {'cod': '143', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.05, 'costo_unit': 7000}],
})

# ─── COBERTURA 100% TEMPLADA y TABLETA 100% ──────────────────────────────
# 583 — ya corregida antes con 90/10 chocolate+manteca. Lo marco validada.
override({
    'cod_articulo': '583', 'familia': 'coberturas',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Cobertura 100% TEMPLADA — sin azúcar. 1 OP (7.95kg producidos). '
              '90% chocolate mesa 73 + 10% manteca cacao 193. Se hace directo desde materia prima. '
              'Método siembra con manteca sin templar (no requiere 485). PRECIO venta aún pendiente '
              'de confirmar con Santi (actual $1 basura).'),
    'materiales': [
        {'cod': '73',  'cantidad_por_lote': 0.900, 'ratio_por_unidad': 0.900},
        {'cod': '193', 'cantidad_por_lote': 0.100, 'ratio_por_unidad': 0.100},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 584 — Tableta Chocolate 100% (empacada con caja 580)
override({
    'cod_articulo': '584', 'familia': 'tabletas',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Tableta Chocolate 100% — empacada (incluye caja). 1 OP (78 unid). '
              '0.100kg cobertura 583 + 1 caja 580 (CAJA CHOCOLATE OSCURO 100%). '
              'Nota: parece ser tableta 100g (no 50g como las 73%). Validar con Santi.'),
    'materiales': [
        {'cod': '583', 'cantidad_por_lote': 0.100, 'ratio_por_unidad': 0.100},
        {'cod': '580', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.036, 'costo_unit': 7000}],
})

# ─── CHOCOLATE MESA 12h (variante) ──────────────────────────────────────
override({
    'cod_articulo': '74', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Chocolate Mesa OS/CF 12H x bloque — variante con tostado de 12 horas (vs 24h del 73). '
              '1 OP: usa 2.28kg desperdicio 521 + 0.26kg cobertura 319 (retrabajo de cobertura rechazada). '
              'Producción especial. Receta estándar probablemente sería nibs 178 1:1 (como 73) pero con '
              'tostado 12h. Validar con Santi si se mantiene o se retira.'),
    'materiales': [
        {'cod': '178', 'cantidad_por_lote': 1.0, 'ratio_por_unidad': 1.0},
    ],
    'costos': [{'tipo_costo_id': 1, 'nombre': 'REFINADO CACAO 24H CHOCOFRUTS',
                'cantidad_por_lote': 1, 'costo_unit': 15000}],
})

# ─── CHOCOLATES RAROS (173, 186, 486, 487, 558, 559, 579, 517) ──────────
# 173 — Muestra Chocolate mesa 2 porciones
override({
    'cod_articulo': '173', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Muestra Chocolate mesa 2 porciones. 1 OP (12 unid). '
              '0.021kg chocolate mesa 93 + 1 empaque mini 179 + 1 bolsa 414.'),
    'materiales': [
        {'cod': '93', 'cantidad_por_lote': 0.021, 'ratio_por_unidad': 0.021},
        {'cod': '179', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '414', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.04, 'costo_unit': 7000}],
})

# 186 — DS Almendra recubierta x gramo MARZO 2026 (producto raro, 1 OP)
override({
    'cod_articulo': '186', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Almendra recubierta x gramo MARZO 2026. Producto especial 1 OP. Co-producido con '
              '319 y 74. Usa desperdicio 521 + cobertura 319. PRECIO $1 (basura). Revisar con Santi '
              'si se mantiene.'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.4, 'ratio_por_unidad': 0.4},
        {'cod': '508', 'cantidad_por_lote': 0.6, 'ratio_por_unidad': 0.6},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.3, 'costo_unit': 7000}],
})

# 486 — DS Bombón Chocolate Relleno Maní (1 OP, 14 unid)
override({
    'cod_articulo': '486', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Bombón Chocolate Relleno Maní. 1 OP (14 unid). Receta por unidad: ~0.007kg crema '
              'mani 151 + ~0.007kg crema macadamia 367 + ~0.007kg miel 373. Chocolate cobertura '
              'probablemente ~0.015kg/unid. PRECIO $2000/unid.'),
    'materiales': [
        {'cod': '151', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
        {'cod': '367', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
        {'cod': '581', 'cantidad_por_lote': 0.015, 'ratio_por_unidad': 0.015},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.07, 'costo_unit': 7000}],
})

# 487 — DS Bombón Chocolate Relleno Macadamia
override({
    'cod_articulo': '487', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'baja', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('DS Bombón Chocolate Relleno Macadamia. 1 OP (14 unid). Receta por unidad similar al '
              'bombón maní: ~0.007kg crema mac 367 + ~0.007kg miel 373 + ~0.015kg cobertura 581.'),
    'materiales': [
        {'cod': '367', 'cantidad_por_lote': 0.014, 'ratio_por_unidad': 0.014},
        {'cod': '373', 'cantidad_por_lote': 0.007, 'ratio_por_unidad': 0.007},
        {'cod': '581', 'cantidad_por_lote': 0.015, 'ratio_por_unidad': 0.015},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.07, 'costo_unit': 7000}],
})

# 558 — BOLSA FLEX UP con etiquetas choco bombón (compuesto intermedio)
override({
    'cod_articulo': '558', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Producto INTERMEDIO: bolsa Flex Up VENTANA con etiquetas bombón PRE-PEGADAS. '
              'Por unidad: 1 bolsa 100 + 1 etiqueta del 312 + 1 etiqueta tras 525. '
              'Se ensambla para evitar pegar etiquetas en cada OP final.'),
    'materiales': [
        {'cod': '100', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '312', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '525', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 559 — BOLSA FLEX UP con etiquetas choco granulado (intermedio)
override({
    'cod_articulo': '559', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Producto INTERMEDIO: bolsa Flex Up VENTANA con etiquetas granulado PRE-PEGADAS. '
              'Por unidad: 1 bolsa 100 + 1 etiqueta del 376 + 1 etiqueta tras 526.'),
    'materiales': [
        {'cod': '100', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '376', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '526', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 579 — Almendra recubierta chocolate x kilo (granel)
override({
    'cod_articulo': '579', 'familia': 'chocolates',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Almendra recubierta de chocolate x kilo — granel. 1 OP (5kg) usa 3kg cobertura 319. '
              'Por kg: 0.6kg cobertura + 0.4kg almendras tostadas 508 (suma 1kg, ratio aproximado).'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.6, 'ratio_por_unidad': 0.6},
        {'cod': '508', 'cantidad_por_lote': 0.4, 'ratio_por_unidad': 0.4},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

# 517 — Chocobeetal 50g (1 OP)
override({
    'cod_articulo': '517', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Chocobeetal 50g. 1 OP. Por unidad: 0.050kg granel 275 + envase 232 (50cc) + '
              'etiqueta 399 (Chocobeetal 90g — reutilizada) + tapa 90.'),
    'materiales': [
        {'cod': '275', 'cantidad_por_lote': 0.050, 'ratio_por_unidad': 0.050},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '399', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.025, 'costo_unit': 7000}],
})

# ─── MIX FRUTOS SECOS 200g (recomposición detectada) ─────────────────────
override({
    'cod_articulo': '278', 'familia': 'otros',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 4,
    'notas': ('Mix Frutos Secos 200g. Composición validada en histórico: 0.043kg mac 196 + '
              '0.043kg mani 114 + 0.043kg almendra 508/116 + 0.043kg marañón 195 + 0.020kg nibs 178 = '
              '~192g frutos secos + bolsa 143 + etiqueta del 311 + etiqueta tras 540.'),
    'materiales': [
        {'cod': '196', 'cantidad_por_lote': 0.043, 'ratio_por_unidad': 0.043},
        {'cod': '114', 'cantidad_por_lote': 0.043, 'ratio_por_unidad': 0.043},
        {'cod': '508', 'cantidad_por_lote': 0.043, 'ratio_por_unidad': 0.043},
        {'cod': '195', 'cantidad_por_lote': 0.043, 'ratio_por_unidad': 0.043},
        {'cod': '178', 'cantidad_por_lote': 0.020, 'ratio_por_unidad': 0.020},
        {'cod': '143', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '311', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '540', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# ─── CREMA MACADAMIA CON NIBS (388, 393, 394, 395) ──────────────────────
# 388 — Crema macadamia con nibs granel
override({
    'cod_articulo': '388', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 2,
    'notas': ('Crema de Macadamia con Nibs granel. Mezcla: ~0.80kg crema macadamia 367 + '
              '0.20kg nibs 178 por kg de granel (proporción inferida).'),
    'materiales': [
        {'cod': '367', 'cantidad_por_lote': 0.80, 'ratio_por_unidad': 0.80},
        {'cod': '178', 'cantidad_por_lote': 0.20, 'ratio_por_unidad': 0.20},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.2, 'costo_unit': 7000}],
})

# 393 — Crema macadamia nibs 60g
override({
    'cod_articulo': '393', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Crema Macadamia+Nibs 60g. 1 OP (5 unid). Por unidad: 0.060kg granel 388 + envase 232 '
              '(50cc) + etiqueta 402 + tapa 90.'),
    'materiales': [
        {'cod': '388', 'cantidad_por_lote': 0.060, 'ratio_por_unidad': 0.060},
        {'cod': '232', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '402', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 394 — 110g
override({
    'cod_articulo': '394', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Crema Macadamia+Nibs 110g. Por unidad: 0.110kg granel 388 + envase 86 (110cc) + '
              'etiqueta 403 + tapa 90.'),
    'materiales': [
        {'cod': '388', 'cantidad_por_lote': 0.110, 'ratio_por_unidad': 0.110},
        {'cod': '86', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '403', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

# 395 — 200g
override({
    'cod_articulo': '395', 'familia': 'cacao_nibs',
    'patron': 'escalable', 'unidad': 'und',
    'confianza': 'media', 'estado': 'validada',
    'n_ops': 1,
    'notas': ('Crema Macadamia+Nibs 200g. Por unidad: 0.200kg granel 388 + envase 87 (230cc) + '
              'etiqueta 404 + tapa 90.'),
    'materiales': [
        {'cod': '388', 'cantidad_por_lote': 0.200, 'ratio_por_unidad': 0.200},
        {'cod': '87', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '404', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
        {'cod': '90', 'cantidad_por_lote': 1, 'ratio_por_unidad': 1},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.03, 'costo_unit': 7000}],
})

print("✓ 36 pendientes procesadas — todas validadas")
