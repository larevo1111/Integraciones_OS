# Inconsistencia: cod 349 — Miel OS Carmen 640 grs

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **349** |
| Nombre | Miel OS Carmen 640 grs |
| Grupo / Unidad | PT / UND |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | 12.0 |
| Físico (contado) | 0.0 |
| **Diferencia** | **-12.0** |
| Costo unit | $14,010 |
| **Impacto económico** | **$-168,120** |
| Severidad | significativa |

## Diagnóstico

**Causa probable**: `REQUIERE_REVISION_MANUAL` (confianza 30%)

No se encontró causa determinista clara. Requiere revisión manual con la operación.

## OPs donde se produjo como PRODUCTO (1)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2227 | 2026-04-28 12:38:39 | 12,00 | Validado | Vigente | Deivy Andres Gonzalez Gut | Miel OS Carmen 640 grs - Usr: Santiago Sierra - Op |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-04-28 12:38:39 | ORDEN DE PRODUCCIÓN: 2227 | 12,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **EGRESO** de **12.0 UND** en bodega ["Principal"] para igualar físico.


---

## 🔬 Análisis humano (revisión manual)

**Causa raíz refinada**: `PRODUCCION_NO_FISICA_OP_2227`

Único movimiento: OP 2227 (28-abr Validada) que produjo 12 unds de Miel OS Carmen 640. Sin ventas, sin remisiones, sin ajustes posteriores. Físico contado = 0 unds. La OP 2227 reportó producción de 12 unds en Effi pero físicamente NO se hicieron, O las 12 unds se entregaron/vendieron sin documentar. Mirando el contexto: la 2227 es parte del lote de envasado del 28-abr, posiblemente Deivy reportó producción estimada cuando todavía no había llenado todas las botellas.

### Acción recomendada

EGRESO de 12 unds. Investigar con Deivy si la 2227 reportó cantidades planificadas vs reales.

**Estado final**: `requiere_ajuste`
