# Inconsistencia: cod 137 — MANI SIN CASCARA X KILO

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **137** |
| Nombre | MANI SIN CASCARA X KILO |
| Grupo / Unidad | MP / KG |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | 18.0 |
| Físico (contado) | 0.0 |
| **Diferencia** | **-18.0** |
| Costo unit | $11,000 |
| **Impacto económico** | **$-198,000** |
| Severidad | significativa |

## Diagnóstico

**Causa probable**: `REQUIERE_REVISION_MANUAL` (confianza 30%)

No se encontró causa determinista clara. Requiere revisión manual con la operación.

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-04-15 21:11:16 | AJUSTE DE INVENTARIO: 361 | 18,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **EGRESO** de **18.0 KG** en bodega ["Principal"] para igualar físico.


---

## 🔬 Análisis humano (revisión manual)

**Causa raíz refinada**: `AJUSTE_HISTORICO_FANTASMA`

Único movimiento en trazabilidad reciente: AJUSTE DE INVENTARIO #361 (15-abr) que sumó 18 kg al stock. Antes y después: cero movimientos. Físico contado = 0 kg. El ajuste #361 creó stock de maní que físicamente no existía (probablemente regularización contable de compra que nunca llegó, o error de digitación al ajustar otro cod). Es típico patrón "ajuste fantasma".

### Acción recomendada

EGRESO de 18 kg maní para igualar realidad física (que es 0). El ajuste #361 fue el error original.

**Estado final**: `requiere_ajuste`
