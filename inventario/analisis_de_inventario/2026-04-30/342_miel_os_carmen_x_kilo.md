# Inconsistencia: cod 342 — MIEL OS CARMEN X KILO

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **342** |
| Nombre | MIEL OS CARMEN X KILO |
| Grupo / Unidad | MP / KG |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | -9.84 |
| Físico (contado) | 0.0 |
| **Diferencia** | **+9.84** |
| Costo unit | $19,000 |
| **Impacto económico** | **$+186,960** |
| Severidad | significativa |

## Diagnóstico

**Causa probable**: `AJUSTE_NEG_HISTORICO` (confianza 90%)

El teórico era negativo (-9.84) — stock inválido por errores históricos. El conteo físico (0.0) corrige a un valor real positivo. Diferencia (+9.84) = legítima.

## OPs donde se consumió como MATERIAL (7)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2235 | 2026-04-29 11:08:03 | 10,10 | Validado | Vigente | Deivy Andres Gonzalez Gut | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO - Us |
| 2223 | 2026-04-28 11:29:37 | 12,60 | Validado | Vigente | Deivy Andres Gonzalez Gut | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO - Us |
| 2203 | 2026-04-24 10:15:28 | 20,00 | Validado | Vigente | DEIVY ANDRES GONZALEZ GUT | LOTE |
| 2202 | 2026-04-23 11:11:57 | 11,04 | Validado | Vigente | Deivy Andres Gonzalez Gut |  |
| 2187 | 2026-04-22 11:53:11 | 13,00 | Validado | Vigente | DEIVY ANDRES GONZALEZ GUT | LOTE 2179 |
| 2179 | 2026-04-20 14:56:01 | 13,00 | Generada | Anulado | DEIVY ANDRES GONZALEZ GUT | LOTE |
| 2171 | 2026-04-20 12:58:00 | 10,00 | Validado | Vigente | DEIVY ANDRES GONZALEZ GUT | LOTE |

## Remisiones de compra recientes (1)

| Fecha | Remisión | Cant | Costo unit | Proveedor |
|---|---|---:|---:|---|
| 2026-04-17 13:23:39 | 471 | 66,90 | 19000,00 | CC: 3184970152. Arancel Apicul |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-04-29 11:08:03 | ORDEN DE PRODUCCIÓN: 2235 | -10,10 | Principal | Transacción vigente |
| 2026-04-28 11:29:37 | ORDEN DE PRODUCCIÓN: 2223 | -12,60 | Principal | Transacción vigente |
| 2026-04-24 10:15:28 | ORDEN DE PRODUCCIÓN: 2203 | -20,00 | Principal | Transacción vigente |
| 2026-04-23 11:11:57 | ORDEN DE PRODUCCIÓN: 2202 | -11,04 | Principal | Transacción vigente |
| 2026-04-22 11:53:11 | ORDEN DE PRODUCCIÓN: 2187 | -13,00 | Principal | Transacción vigente |
| 2026-04-22 11:52:30 | ORDEN DE PRODUCCIÓN: 2179 | 13,00 | Principal | Transacción anulada |
| 2026-04-20 14:56:01 | ORDEN DE PRODUCCIÓN: 2179 | -13,00 | Principal | Transacción anulada |
| 2026-04-20 12:58:00 | ORDEN DE PRODUCCIÓN: 2171 | -10,00 | Principal | Transacción vigente |
| 2026-04-17 13:23:39 | NOTA DE REMISIÓN DE COMPRA: 471 | 66,90 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **INGRESO** de **9.84 KG** en bodega ["Principal"] para igualar físico.
