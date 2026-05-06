# Inconsistencia: cod 113 — VAINILLA EN VAINA UNIDAD

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **113** |
| Nombre | VAINILLA EN VAINA UNIDAD |
| Grupo / Unidad | MP / UND |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | 0.0 |
| Físico (contado) | 20.0 |
| **Diferencia** | **+20.0** |
| Costo unit | $25,499 |
| **Impacto económico** | **$+509,980** |
| Severidad | critica |

## Diagnóstico

**Causa probable**: `REQUIERE_REVISION_MANUAL` (confianza 30%)

No se encontró causa determinista clara. Requiere revisión manual con la operación.

## OPs donde se consumió como MATERIAL (1)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 1934 | 2026-02-11 15:07:13 | 10,00 | Procesada | Vigente | Deivy Andres Gonzalez Gut | Vainilla en vainas 10uds. secadas en horno (3 cicl |

## Remisiones de compra recientes (2)

| Fecha | Remisión | Cant | Costo unit | Proveedor |
|---|---|---:|---:|---|
| 2026-03-30 23:09:20 | 464 | 20,00 | 9300,50 | NIT: 3506889. Santiago Sierra |
| 2026-02-11 15:06:40 | 432 | 10,00 | 9300,50 | NIT: 3506889. Santiago Sierra |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-04-15 21:11:16 | AJUSTE DE INVENTARIO: 361 | -20,00 | Principal | Transacción vigente |
| 2026-03-30 23:09:20 | NOTA DE REMISIÓN DE COMPRA: 464 | 20,00 | Principal | Transacción vigente |
| 2026-02-11 15:07:13 | ORDEN DE PRODUCCIÓN: 1934 | -10,00 | Principal | Transacción vigente |
| 2026-02-11 15:06:40 | NOTA DE REMISIÓN DE COMPRA: 432 | 10,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **INGRESO** de **20.0 UND** en bodega ["Principal"] para igualar físico.


---

## 🔬 Análisis humano (revisión manual)

**Causa raíz refinada**: `AJUSTE_PREVIO_INCORRECTO`

El AJUSTE DE INVENTARIO #361 (15-abr) sacó 20 unds de Effi cuando físicamente las 20 unds SÍ estaban (compra remisión #464 del 30-mar fue de 20 unds Santi). El físico contado al 30-abr = 20 unds confirma que el ajuste #361 fue erróneo. Probable: alguien intentó corregir un negativo y tocó cod equivocado, O se ajustaron egresos no documentados.

### Acción recomendada

INGRESO de 20 unds de vainilla en bodega Principal. Físico es correcto, ajuste #361 fue el error.

**Estado final**: `requiere_ajuste`
