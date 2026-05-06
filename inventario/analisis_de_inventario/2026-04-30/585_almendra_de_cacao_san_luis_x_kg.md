# Inconsistencia: cod 585 — ALMENDRA DE CACAO SAN LUIS x KG

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **585** |
| Nombre | ALMENDRA DE CACAO SAN LUIS x KG |
| Grupo / Unidad | MP / KG |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | 111.0 |
| Físico (contado) | 0.0 |
| **Diferencia** | **-111.0** |
| Costo unit | $11,000 |
| **Impacto económico** | **$-1,221,000** |
| Severidad | critica |

## Diagnóstico

**Causa probable**: `REQUIERE_REVISION_MANUAL` (confianza 30%)

No se encontró causa determinista clara. Requiere revisión manual con la operación.

## OPs donde se consumió como MATERIAL (2)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2252 | 2026-05-06 15:04:33 | 111,00 | Procesada | Vigente | Arbol de cacao - Edgard A | Cacao san luis 111 kilos -  97.4 nibs, 16.6 cascar |
| 2250 | 2026-05-06 15:00:07 | 111,00 | Generada | Anulado | Arbol de cacao - Edgard A |  |

## Remisiones de compra recientes (1)

| Fecha | Remisión | Cant | Costo unit | Proveedor |
|---|---|---:|---:|---|
| 2026-04-17 18:03:57 | 472 | 111,00 | 11000,00 | NIT: 3506889. Santiago Sierra |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-05-06 15:04:42 | ORDEN DE PRODUCCIÓN: 2250 | 111,00 | Principal | Transacción anulada |
| 2026-05-06 15:04:33 | ORDEN DE PRODUCCIÓN: 2252 | -111,00 | Principal | Transacción vigente |
| 2026-05-06 15:00:07 | ORDEN DE PRODUCCIÓN: 2250 | -111,00 | Principal | Transacción anulada |
| 2026-04-17 18:03:57 | NOTA DE REMISIÓN DE COMPRA: 472 | 111,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **EGRESO** de **111.0 KG** en bodega ["Principal"] para igualar físico.


---

## 🔬 Análisis humano (revisión manual)

**Causa raíz refinada**: `TIMING_OP_POSTERIOR_AL_CORTE`

La OP 2252 (creada HOY 06-may por Árbol de cacao) consumió 111 kg de almendra SL → produjo 97.4 kg NIBS + 16.6 kg CASCARILLA. Físicamente la transformación ya estaba hecha antes del 30-abr (los productos NIBS/CASCARILLA SL están precargados como cods 593/594 con 97.5 + 16 kg). El teórico al 30-abr aún reportaba las almendras crudas porque la OP de transformación no se había creado en Effi al momento del corte. Es un timing — el ajuste de los almendras (-111) se compensa con los productos transformados (+97.5 cod 593 y +16 cod 594).

### Acción recomendada

NO ajustar manualmente. La OP 2252 ya regulariza el consumo. Confirmar que el sync próximo de Effi traiga el teórico actualizado a 0 kg almendra SL. Los 13.5 kg restantes (111 - 97.5 - 16 = 2.5 kg merma + redondeo) son merma normal de descascarillado/tostado.

**Estado final**: `justificada`
