# Reporte de verificación de ajustes — Inventario 30-abr-2026

**Fecha verificación**: 2026-05-07 10:30
**Método**: ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md)
**Fórmula**: `físico_30abr + Σ(traza_post EXCLUYENDO #371,#372) = stock_actual_effi`

## Resultado general

| Estado | N° | Comentario |
|---|---:|---|
| ✅ OK | 38 | Cuadran exacto (tolerancia ±0.05) |
| ❌ FAIL | 6 | Requieren investigación |
| ⚠️ EXCEPCIÓN | 6 | Justificadas en notas.md (no aplica fórmula directa) |
| **TOTAL** | **50** | |

## Universo verificado

- **20 grandes** (todos los críticos + significativos)
- **30 menores** (sample aleatorio de 149)

## Detalle por cod

| cod | Sev | Bodega | físico | Σtraza | esperado | stock_effi | delta | resultado |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 73 | significativa | Principal | 0.4 | 15.13 | 15.53 | 15.53 | -0.00 | OK |
| 137 | significativa | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 146 | significativa | Principal | 5.5 | 0.00 | 5.50 | 5.50 | +0.00 | OK |
| 178 | significativa | Principal | 23.1 | 46.35 | 69.45 | 69.45 | +0.00 | OK |
| 193 | significativa | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 349 | significativa | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 411 | critica | Principal | 12.0 | -2.00 | 10.00 | 12.00 | +2.00 | EXCEPCION |
| 478 | significativa | Principal | 1.4 | 0.00 | 1.40 | 1.40 | +0.00 | OK |
| 493 | significativa | Principal | 8.0 | 25.00 | 33.00 | 33.00 | +0.00 | OK |
| 585 | critica | Principal | 0.0 | -111.00 | -111.00 | 0.00 | +111.00 | EXCEPCION |
| 586 | critica | Principal | 0.0 | 0.00 | 0.00 | -0.01 | -0.01 | OK |
| 593 | critica | Principal | 97.5 | 97.40 | 194.90 | 97.40 | -97.50 | EXCEPCION |
| 15 | significativa | Principal | 3.0 | 49.00 | 52.00 | 52.00 | +0.00 | OK |
| 85 | significativa | Principal | 41.0 | 0.00 | 41.00 | 0.00 | -41.00 | EXCEPCION |
| 88 | significativa | Principal | 48.0 | 0.00 | 48.00 | 0.00 | -48.00 | EXCEPCION |
| 93 | significativa | Principal | 2.8 | 0.00 | 2.80 | 2.80 | +0.00 | OK |
| 113 | critica | Principal | 20.0 | 0.00 | 20.00 | 20.00 | +0.00 | OK |
| 114 | significativa | Principal | 5.3 | -0.30 | 5.00 | 5.00 | +0.00 | OK |
| 319 | critica | Principal | 0.0 | -5.45 | -5.45 | -5.45 | +0.00 | OK |
| 342 | significativa | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 187 | menor | Principal | 12.0 | -1.00 | 11.00 | 13.00 | +2.00 | FAIL |
| 86 | menor | Principal | 72.0 | 0.00 | 72.00 | 112.00 | +40.00 | FAIL |
| 400 | menor | Principal | 15.0 | 0.00 | 15.00 | 15.00 | +0.00 | OK |
| 343 | menor | Principal | 27.0 | -8.00 | 19.00 | 19.00 | +0.00 | OK |
| 326 | menor | Principal | 29.0 | 0.00 | 29.00 | 29.00 | +0.00 | OK |
| 264 | menor | Principal | 73.0 | 0.00 | 73.00 | 73.00 | +0.00 | OK |
| 173 | menor | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 536 | menor | Principal | 205.0 | 0.00 | 205.00 | 205.00 | +0.00 | OK |
| 163 | menor | Principal | 7.0 | 0.00 | 7.00 | 7.00 | +0.00 | OK |
| 579 | menor | Principal | 0.0 | 0.00 | 0.00 | 0.00 | +0.00 | OK |
| 90 | menor | Principal | 0.0 | -253.00 | -253.00 | -253.00 | +0.00 | OK |
| 87 | menor | Principal | 74.0 | 0.00 | 74.00 | 102.00 | +28.00 | EXCEPCION |
| 164 | menor | Principal | 0.0 | -2.00 | -2.00 | 0.00 | +2.00 | FAIL |
| 322 | menor | Principal | 92.0 | 0.00 | 92.00 | 92.00 | +0.00 | OK |
| 331 | menor | Principal | 13.0 | -30.00 | -17.00 | -17.00 | +0.00 | OK |
| 291 | menor | Principal | 83.0 | -72.00 | 11.00 | 11.00 | +0.00 | OK |
| 598 | menor | Principal | 8.0 | 0.00 | 8.00 | 8.00 | +0.00 | OK |
| 312 | menor | Principal | 51.0 | 0.00 | 51.00 | 51.00 | +0.00 | OK |
| 557 | menor | Productos No Conformes | 5.0 | 0.00 | 5.00 | 5.00 | +0.00 | OK |
| 577 | menor | Principal | 7.0 | 0.00 | 7.00 | 7.00 | +0.00 | OK |
| 325 | menor | Principal | 29.0 | 0.00 | 29.00 | 29.00 | +0.00 | OK |
| 403 | menor | Principal | 55.0 | 0.00 | 55.00 | 0.00 | -55.00 | FAIL |
| 405 | menor | Principal | 13.0 | -2.00 | 11.00 | 13.00 | +2.00 | FAIL |
| 21 | menor | Principal | 16.0 | -5.00 | 11.00 | 12.00 | +1.00 | FAIL |
| 289 | menor | Principal | 40.0 | -12.00 | 28.00 | 28.00 | +0.00 | OK |
| 405 | menor | Productos No Conformes | 9.0 | 0.00 | 9.00 | 9.00 | +0.00 | OK |
| 525 | menor | Principal | 46.0 | 0.00 | 46.00 | 46.00 | +0.00 | OK |
| 528 | menor | Principal | 25.0 | 0.00 | 25.00 | 25.00 | +0.00 | OK |
| 283 | menor | Principal | 30.0 | 0.00 | 30.00 | 30.00 | +0.00 | OK |
| 554 | menor | Principal | 9.0 | -8.00 | 1.00 | 1.00 | +0.00 | OK |

## ❌ FAILS — investigar

- **cod 187** (CREMA DE MANI OS 230 GRS): físico 12.0 + Σ -1.00 = esperado 11.00, Effi reporta 13.00, delta +2.00
- **cod 86** (Envase Vidrio R mb110h Flint, 110cc, B. ): físico 72.0 + Σ 0.00 = esperado 72.00, Effi reporta 112.00, delta +40.00
- **cod 164** (Miel OS Panal 275 grs): físico 0.0 + Σ -2.00 = esperado -2.00, Effi reporta 0.00, delta +2.00
- **cod 403** (ETIQUETA CREMA DE MACADAMIA CON NIBS DE ): físico 55.0 + Σ 0.00 = esperado 55.00, Effi reporta 0.00, delta -55.00
- **cod 405** (CHOCOBEETAL OS 130 GRS): físico 13.0 + Σ -2.00 = esperado 11.00, Effi reporta 13.00, delta +2.00
- **cod 21** (PROPOLEO OS 150 grs): físico 16.0 + Σ -5.00 = esperado 11.00, Effi reporta 12.00, delta +1.00

## ⚠️ Excepciones documentadas

- **cod 411** (Chocolate Puro Cacao 500 grs Granulado L): delta +2.00 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
- **cod 585** (ALMENDRA DE CACAO SAN LUIS x KG): delta +111.00 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
- **cod 593** (NIBS DE CACAO SL x KG): delta -97.50 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
- **cod 85** (Envase Vidrio R 1264 Flint, 750cc, B. 63): delta -41.00 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
- **cod 88** (Envase Vidrio 1263 Flint, 500cc, b.63, C): delta -48.00 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
- **cod 87** (Envase Vidrio R 2670 Flint, 230cc, B.63,): delta +28.00 — ver [METODO_TESTEO_AJUSTES.md](../METODO_TESTEO_AJUSTES.md) §Excepciones conocidas
