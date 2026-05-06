# RESUMEN — Análisis de inconsistencias inventario 2026-04-30

**Generado**: 2026-05-06
**Universo**: 281 artículos inventariables (consolidados Jenifer→Principal + 17 No Conformes)
**Valor total inventario físico**: $14.680.877

---

## 📊 Métricas globales

| Métrica | Valor |
|---|---:|
| Artículos totales | 281 |
| Con diferencia | 169 |
| Sin diferencia (OK) | 112 |
| Impacto positivo (sobrantes) | $5,484,947 |
| Impacto negativo (faltantes) | $-3,671,075 |
| **Impacto NETO** | **$1,813,871** |

## 🚦 Por severidad

| Severidad | N° | Impacto $ |
|---|---:|---:|
| critica | 6 | $1,495,917 |
| significativa | 14 | $13,688 |
| menor | 149 | $304,267 |
| ok | 112 | $0 |

## 📋 Por estado

| Estado | N° |
|---|---:|
| pendiente | 112 |
| analizado | 154 |
| justificada | 7 |
| requiere_ajuste | 8 |

---

## 🔬 Casos críticos y significativos (20) — análisis profundo individual

Cada uno tiene archivo `.md` detallado con trazabilidad Effi completa.

| Cod | Nombre | Grupo | Teórico | Físico | Dif | Impacto $ | Severidad | Estado | Causa final |
|---:|---|:---:|---:|---:|---:|---:|---|---|---|
| 593 | NIBS DE CACAO SL x KG | MP | 0.00 | 97.50 | +97.50 | $+1,852,500 | critica | justificada | `Precarga SL — cacao San Luis` |
| 585 | ALMENDRA DE CACAO SAN LUIS x KG | MP | 111.00 | 0.00 | -111.00 | $-1,221,000 | critica | justificada | `TIMING_OP_POSTERIOR_AL_CORTE` |
| 113 | VAINILLA EN VAINA UNIDAD | MP | 0.00 | 20.00 | +20.00 | $+509,980 | critica | requiere_ajuste | `AJUSTE_PREVIO_INCORRECTO` |
| 319 | COBERTURA CHOCOLATE CPM 73% OS X KILO | PP | -7.80 | 0.00 | +7.80 | $+338,770 | critica | analizado | `AJUSTE_NEG_HISTORICO` |
| 411 | Chocolate Puro Cacao 500 grs Granulado LT | PT | 3.00 | 12.00 | +9.00 | $+329,607 | critica | analizado | `PT_NO_REGISTRADO` |
| 586 | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO | MP | 14.27 | 0.00 | -14.27 | $-313,940 | critica | requiere_ajuste | `SOBRECONSUMO_NO_REGISTRADO` |
| 146 | POLEN APICA X KILO | MP | 0.08 | 5.50 | +5.42 | $+262,870 | significativa | requiere_ajuste | `COMPRA_NO_CONTABILIZADA` |
| 478 | Chocolate Puro Granulado x Kilo LT | PP | 4.71 | 1.40 | -3.31 | $-223,226 | significativa | requiere_ajuste | `CRUCE_MP_PT_VALORES_OP` |
| 93 | CHOCOLATE MESA OS MOLDEADO X KG MOLDE  9 a 12 | PP | -3.05 | 2.80 | +5.85 | $+207,207 | significativa | analizado | `AJUSTE_NEG_HISTORICO` |
| 137 | MANI SIN CASCARA X KILO | MP | 18.00 | 0.00 | -18.00 | $-198,000 | significativa | requiere_ajuste | `AJUSTE_HISTORICO_FANTASMA` |
| 342 | MIEL OS CARMEN X KILO | MP | -9.84 | 0.00 | +9.84 | $+186,960 | significativa | analizado | `AJUSTE_NEG_HISTORICO` |
| 349 | Miel OS Carmen 640 grs | PT | 12.00 | 0.00 | -12.00 | $-168,120 | significativa | requiere_ajuste | `PRODUCCION_NO_FISICA_OP_2227` |
| 15 | Miel Os San Carlos 640 grs | PT | -9.00 | 3.00 | +12.00 | $+164,280 | significativa | analizado | `AJUSTE_NEG_HISTORICO` |
| 178 | NIBS DE CACAO X KG LT | PP | 29.52 | 23.10 | -6.42 | $-154,080 | significativa | analizado | `OP_NO_EJECUTADA` |
| 193 | MANTECA DE CACAO X KG | MP | 1.40 | 0.00 | -1.40 | $-128,800 | significativa | analizado | `SOBRECONSUMO_OPS` |
| 73 | CHOCOLATE 100p X BLOQUE LT KG | PP | 3.79 | 0.40 | -3.39 | $-112,548 | significativa | analizado | `OP_NO_EJECUTADA` |
| 85 | Envase Vidrio R 1264 Flint, 750cc, B. 63 C Ta | INS | 0.00 | 41.00 | +41.00 | $+90,405 | significativa | justificada | `Remisión compra UNICOR #479` |
| 114 | MANI SIN CASCARA TOSTADO X KILO | MP | 0.00 | 5.30 | +5.30 | $+90,100 | significativa | requiere_ajuste | `AJUSTE_PREVIO_SOBREESTIMADO` |
| 493 | Tableta Chocolate 73p con Macadamia 50 grs CP | PT | 23.00 | 8.00 | -15.00 | $-78,000 | significativa | requiere_ajuste | `CRUCE_VENTAS_INTENSAS_30ABR` |
| 88 | Envase Vidrio 1263 Flint, 500cc, b.63, C Tapa | INS | 0.00 | 48.00 | +48.00 | $+74,640 | significativa | justificada | `Remisión compra UNICOR #479` |

---

## 📁 Archivos de análisis profundo

17 análisis individuales registrados en `inv_analisis_inconsistencias`:

- [15_miel_os_san_carlos_640_grs.md](15_miel_os_san_carlos_640_grs.md) — cod 15 Miel Os San Carlos 640 grs
- [73_chocolate_100p_x_bloque_lt_kg.md](73_chocolate_100p_x_bloque_lt_kg.md) — cod 73 CHOCOLATE 100p X BLOQUE LT KG
- [93_chocolate_mesa_os_moldeado_x_kg_molde_9_a_12_g.md](93_chocolate_mesa_os_moldeado_x_kg_molde_9_a_12_g.md) — cod 93 CHOCOLATE MESA OS MOLDEADO X KG MOLDE  9 a 12 g
- [113_vainilla_en_vaina_unidad.md](113_vainilla_en_vaina_unidad.md) — cod 113 VAINILLA EN VAINA UNIDAD
- [114_mani_sin_cascara_tostado_x_kilo.md](114_mani_sin_cascara_tostado_x_kilo.md) — cod 114 MANI SIN CASCARA TOSTADO X KILO
- [137_mani_sin_cascara_x_kilo.md](137_mani_sin_cascara_x_kilo.md) — cod 137 MANI SIN CASCARA X KILO
- [146_polen_apica_x_kilo.md](146_polen_apica_x_kilo.md) — cod 146 POLEN APICA X KILO
- [178_nibs_de_cacao_x_kg_lt.md](178_nibs_de_cacao_x_kg_lt.md) — cod 178 NIBS DE CACAO X KG LT
- [193_manteca_de_cacao_x_kg.md](193_manteca_de_cacao_x_kg.md) — cod 193 MANTECA DE CACAO X KG
- [319_cobertura_chocolate_cpm_73_os_x_kilo.md](319_cobertura_chocolate_cpm_73_os_x_kilo.md) — cod 319 COBERTURA CHOCOLATE CPM 73% OS X KILO
- [342_miel_os_carmen_x_kilo.md](342_miel_os_carmen_x_kilo.md) — cod 342 MIEL OS CARMEN X KILO
- [349_miel_os_carmen_640_grs.md](349_miel_os_carmen_640_grs.md) — cod 349 Miel OS Carmen 640 grs
- [411_chocolate_puro_cacao_500_grs_granulado_lt.md](411_chocolate_puro_cacao_500_grs_granulado_lt.md) — cod 411 Chocolate Puro Cacao 500 grs Granulado LT
- [478_chocolate_puro_granulado_x_kilo_lt.md](478_chocolate_puro_granulado_x_kilo_lt.md) — cod 478 Chocolate Puro Granulado x Kilo LT
- [493_tableta_chocolate_73p_con_macadamia_50_grs_cpm.md](493_tableta_chocolate_73p_con_macadamia_50_grs_cpm.md) — cod 493 Tableta Chocolate 73p con Macadamia 50 grs CPM
- [585_almendra_de_cacao_san_luis_x_kg.md](585_almendra_de_cacao_san_luis_x_kg.md) — cod 585 ALMENDRA DE CACAO SAN LUIS x KG
- [586_miel_filtrada_pasteurizada_el_carmen_x_kilo.md](586_miel_filtrada_pasteurizada_el_carmen_x_kilo.md) — cod 586 MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO

---

## 🤖 Análisis automático de menores (149)

Distribución de causas detectadas por el motor determinista:

| Causa | N° | Impacto $ |
|---|---:|---:|
| Artículo redundante | 78 | $876,999 |
| Valores incorrectos en OP | 42 | $-683,614 |
| OP no ejecutada | 17 | $-70,143 |
| SIN_CAUSA_DETERMINISTA | 9 | $197,906 |
| (sin causa) | 3 | $-16,880 |

---

## 🎯 Acciones recomendadas

### Justificadas (no requieren ajuste)
1. **Precarga SL** (cods 593, 594): material físicamente en planta antes del corte, cods creados en Effi después. Ya cubierto por OP 2252 (06-may).
2. **Remisión UNICOR #479** (cods 85, 86, 87, 88): compra de abril recibida 04-may, sumada al físico.
3. **Cod 585 ALMENDRA SL**: timing OP 2252 — se compensa con productos transformados (NIBS+CASCARILLA SL).

### Requieren ajuste manual en Effi (8 críticas/significativas)
1. **113 VAINILLA** +20 unds (INGRESO) — corregir ajuste #361 erróneo
2. **586 MIEL CARMEN** -14.27 kg (EGRESO) — sobreconsumo OPs envasado no reportado
3. **146 POLEN APICA** +5.42 kg (INGRESO) — verificar entrega APICA sin remisión
4. **478 GRANULADO LT** -3.31 kg (EGRESO) — cruce MP↔PT con cod 411
5. **137 MANI** -18 kg (EGRESO) — ajuste #361 fantasma
6. **349 MIEL CARMEN 640** -12 unds (EGRESO) — OP 2227 reportó producción no realizada
7. **114 MANI TOSTADO** +5.30 kg (INGRESO) — ajuste #369 sobreestimado
8. **493 TABLETA MACADAMIA** -15 unds (EGRESO) — ventas intensas 30-abr, auditar facturas 980-985

### Auto-justificadas por trazabilidad (ajustes negativos históricos)
- **319 COBERTURA CPM 73%** +7.80 kg → corrección de stock negativo histórico
- **411 CHOCOLATE 500 GRANULADO LT** +9 unds → PT no registrado en OP
- **93 CHOCOLATE MESA MOLDEADO** +5.85 kg → corrección stock negativo
- **15 MIEL OS SAN CARLOS 640** +12 unds → corrección stock negativo
- **342 MIEL OS CARMEN x KG** +9.84 kg → corrección stock negativo

### Identificadas con causa clara (motor determinista)
- **178 NIBS DE CACAO LT** -6.42 kg → OP_NO_EJECUTADA (OPs Generadas vigentes consumen)
- **73 CHOCOLATE 100p** -3.39 kg → OP_NO_EJECUTADA
- **193 MANTECA CACAO** -1.40 kg → SOBRECONSUMO_OPS

---

## 🗂️ Próximos pasos

1. **Generar OPs de ajuste en Effi** para los 8 casos `requiere_ajuste` (split: 1 OP de ingresos + 1 OP de egresos en bodega Principal)
2. **Aplicar la "auto-justificación" de stocks negativos** en bloque (5 casos pasan de teórico negativo a 0+)
3. **Investigar con el equipo** los casos detectados como SOBRECONSUMO_OPS — revisar recetas de empaque
4. **Cerrar inventario** en el módulo (`POST /api/inventario/cerrar-inventario`)

---

## 📚 Referencias

- Notas del inventario: [notas.md](notas.md)
- Consolidación bodegas: Principal (281) + No Conformes (17) — Jenifer disuelta
- 28-abr auditoría stocks negativos: [../2026-04-28/RESUMEN.md](../2026-04-28/RESUMEN.md)
- Skill metodológico: `.claude/skills/inventario-inconsistencias/SKILL.md`
- Manual completo: `.agent/manuales/inventario_fisico_manual.md`
