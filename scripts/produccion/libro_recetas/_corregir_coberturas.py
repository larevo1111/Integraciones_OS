#!/usr/bin/env python3
"""Corrige recetas Coberturas (4 productos) con ratios verificados en histórico."""
from override_receta import override

# 319 — Cobertura 73% SIN TEMPLAR (lote fijo 4kg, 7 materiales idénticos en todas OPs)
override({
    'cod_articulo': '319', 'familia': 'coberturas',
    'patron': 'lote_fijo', 'unidad': 'kg', 'cantidad_lote_std': 4.0,
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 10, 'ops_referencia': ['2172', '2165', '2164', '2138', '2132'],
    'notas': ('Cobertura 73% sin templar — lote fijo 4kg. 7 materiales fijos. '
              '5 OPs coincidentes al 100% (CV=0.0). Costo total materiales/lote ≈$173,648.'),
    'materiales': [
        {'cod': '73',  'cantidad_por_lote': 2.30, 'ratio_por_unidad': 0.575},
        {'cod': '193', 'cantidad_por_lote': 0.70, 'ratio_por_unidad': 0.175},
        {'cod': '244', 'cantidad_por_lote': 0.64, 'ratio_por_unidad': 0.160},
        {'cod': '183', 'cantidad_por_lote': 0.40, 'ratio_por_unidad': 0.100},
        {'cod': '373', 'cantidad_por_lote': 0.35, 'ratio_por_unidad': 0.0875},
        {'cod': '134', 'cantidad_por_lote': 0.12, 'ratio_por_unidad': 0.030},
        {'cod': '500', 'cantidad_por_lote': 0.01, 'ratio_por_unidad': 0.0025},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 2.35, 'costo_unit': 7000}],
})

# 485 — Manteca de Cacao TEMPLADA (1:1 desde manteca normal, MO lote fijo ~1.5h)
override({
    'cod_articulo': '485', 'familia': 'coberturas',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 7, 'ops_referencia': ['2178', '1864', '1387', '1228'],
    'notas': ('Manteca cacao TEMPLADA — ratio 1:1 con manteca 193. '
              'M.O. en práctica es ~1.5h por lote (no escala con kg, templar 1-3kg toma lo mismo).'),
    'materiales': [
        {'cod': '193', 'cantidad_por_lote': 1.00, 'ratio_por_unidad': 1.00},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 1.5, 'costo_unit': 7000}],
})

# 581 — Cobertura 73% TEMPLADA (método siembra: 93% 319 + 7% 485)
override({
    'cod_articulo': '581', 'familia': 'coberturas',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'alta', 'estado': 'validada',
    'n_ops': 2, 'ops_referencia': ['2191', '2128'],
    'notas': ('Cobertura 73% TEMPLADA — método siembra: 93% cobertura sin templar 319 + '
              '7% manteca templada 485. 2 OPs con ratios consistentes (CV=0.015). '
              'M.O. ~2-3.5h por lote según tamaño. El correcto es tipo_costo_id=13 (M.O. HORA).'),
    'materiales': [
        {'cod': '319', 'cantidad_por_lote': 0.930, 'ratio_por_unidad': 0.930},
        {'cod': '485', 'cantidad_por_lote': 0.070, 'ratio_por_unidad': 0.070},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.35, 'costo_unit': 7000}],
})

# 583 — Cobertura 100% TEMPLADA (1 OP sola)
override({
    'cod_articulo': '583', 'familia': 'coberturas',
    'patron': 'escalable', 'unidad': 'kg',
    'confianza': 'baja', 'estado': 'borrador',
    'n_ops': 1, 'ops_referencia': ['2181'],
    'notas': ('Cobertura 100% TEMPLADA — sin azúcar. Solo 1 OP histórica. '
              '90% chocolate mesa 73 + 10% manteca cacao 193. Se hace directo desde materia prima '
              '(no hay "sin templar" intermedia como en la 73%). PRECIO venta pendiente confirmar con Santi.'),
    'materiales': [
        {'cod': '73',  'cantidad_por_lote': 0.900, 'ratio_por_unidad': 0.900},
        {'cod': '193', 'cantidad_por_lote': 0.100, 'ratio_por_unidad': 0.100},
    ],
    'costos': [{'tipo_costo_id': 13, 'nombre': 'M.O. HORA ORIGEN SILVESTRE (Hora)',
                'cantidad_por_lote': 0.5, 'costo_unit': 7000}],
})

print("✓ 4 coberturas corregidas")
