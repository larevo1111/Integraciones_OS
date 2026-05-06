# Inconsistencia: cod 586 — MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **586** |
| Nombre | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO |
| Grupo / Unidad | MP / KG |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | 14.27 |
| Físico (contado) | 0.0 |
| **Diferencia** | **-14.27** |
| Costo unit | $22,000 |
| **Impacto económico** | **$-313,940** |
| Severidad | critica |

## Diagnóstico

**Causa probable**: `REQUIERE_REVISION_MANUAL` (confianza 30%)

No se encontró causa determinista clara. Requiere revisión manual con la operación.

## OPs donde se consumió como MATERIAL (7)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2227 | 2026-04-28 12:38:39 | 7,68 | Validado | Vigente | Deivy Andres Gonzalez Gut | Miel OS Carmen 640 grs - Usr: Santiago Sierra - Op |
| 2220 | 2026-04-27 20:53:15 | 18,78 | Generada | Anulado | Deivy Andres Gonzalez Gut | TEST POST DIRECTO ? anular después - replica OP 22 |
| 2215 | 2026-04-27 13:28:16 | 0,93 | Validado | Vigente | Deivy Andres Gonzalez Gut | Producción crema de maní x kilo ? 12 kg con miel d |
| 2214 | 2026-04-27 12:20:24 | 13,45 | Validado | Vigente | Deivy Andres Gonzalez Gut | Envasado mieles del Carmen pasteurizada ? 6 unid 1 |
| 2204 | 2026-04-24 10:26:24 | 18,78 | Validado | Vigente | Deivy Andres Gonzalez Gut |  |
| 2201 | 2026-04-23 11:09:55 | 3,25 | Generada | Anulado | Deivy Andres Gonzalez Gut |  |
| 2200 | 2026-04-23 11:09:37 | 3,25 | Generada | Anulado | LAURA MARCELA ECHAVARRIA  |  |

## OPs donde se produjo como PRODUCTO (5)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2235 | 2026-04-29 11:08:03 | 10,10 | Validado | Vigente | Deivy Andres Gonzalez Gut | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO - Us |
| 2230 | 2026-04-28 22:07:54 | 0,01 | Generada | Anulado | ALIEXPRESS |  |
| 2223 | 2026-04-28 11:29:37 | 12,00 | Validado | Vigente | Deivy Andres Gonzalez Gut | MIEL FILTRADA PASTEURIZADA - EL CARMEN x KILO - Us |
| 2203 | 2026-04-24 10:15:28 | 20,00 | Validado | Vigente | DEIVY ANDRES GONZALEZ GUT | LOTE |
| 2187 | 2026-04-22 11:53:11 | 13,00 | Validado | Vigente | DEIVY ANDRES GONZALEZ GUT | LOTE 2179 |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-05-03 22:33:43 | ORDEN DE PRODUCCIÓN: 2230 | -0,01 | Principal | Transacción anulada |
| 2026-04-29 12:48:25 | ORDEN DE PRODUCCIÓN: 2201 | 3,25 | Principal | Transacción anulada |
| 2026-04-29 11:08:03 | ORDEN DE PRODUCCIÓN: 2235 | 10,10 | Principal | Transacción vigente |
| 2026-04-28 22:07:54 | ORDEN DE PRODUCCIÓN: 2230 | 0,01 | Principal | Transacción anulada |
| 2026-04-28 12:38:39 | ORDEN DE PRODUCCIÓN: 2227 | -7,68 | Principal | Transacción vigente |
| 2026-04-28 11:29:37 | ORDEN DE PRODUCCIÓN: 2223 | 12,00 | Principal | Transacción vigente |
| 2026-04-27 20:56:19 | ORDEN DE PRODUCCIÓN: 2220 | 18,78 | Principal | Transacción anulada |
| 2026-04-27 20:53:15 | ORDEN DE PRODUCCIÓN: 2220 | -18,78 | Principal | Transacción anulada |
| 2026-04-27 13:28:17 | ORDEN DE PRODUCCIÓN: 2215 | -0,93 | Principal | Transacción vigente |
| 2026-04-27 12:20:24 | ORDEN DE PRODUCCIÓN: 2214 | -13,45 | Principal | Transacción vigente |
| 2026-04-24 10:26:24 | ORDEN DE PRODUCCIÓN: 2204 | -18,78 | Principal | Transacción vigente |
| 2026-04-24 10:15:28 | ORDEN DE PRODUCCIÓN: 2203 | 20,00 | Principal | Transacción vigente |
| 2026-04-23 11:10:01 | ORDEN DE PRODUCCIÓN: 2200 | 3,25 | Principal | Transacción anulada |
| 2026-04-23 11:09:55 | ORDEN DE PRODUCCIÓN: 2201 | -3,25 | Principal | Transacción anulada |
| 2026-04-23 11:09:37 | ORDEN DE PRODUCCIÓN: 2200 | -3,25 | Principal | Transacción anulada |
| 2026-04-22 11:53:11 | ORDEN DE PRODUCCIÓN: 2187 | 13,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **EGRESO** de **14.27 KG** en bodega ["Principal"] para igualar físico.


---

## 🔬 Análisis humano (revisión manual)

**Causa raíz refinada**: `SOBRECONSUMO_NO_REGISTRADO`

Trazabilidad muestra entradas (+55.10 kg de 4 OPs producción) y consumos (-58.84 kg en 4 OPs validadas). Diferencia neta +14.27 kg en teórico, pero físico = 0. Las OPs consumidoras (2227, 2215, 2214, 2204) reportaron cantidades estimadas de miel — probablemente el consumo REAL fue mayor (envasado con mermas, derrames, ajustes en planta no reportados). Desfase típico de pasteurización + envasado manual.

### Acción recomendada

EGRESO de 14.27 kg de miel Carmen en bodega Principal. Causa raíz: las OPs validadas usaron cantidades estimadas, no reales — sobreconsumo del 24% sobre lo programado.

**Estado final**: `requiere_ajuste`
