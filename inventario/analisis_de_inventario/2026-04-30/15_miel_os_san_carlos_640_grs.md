# Inconsistencia: cod 15 — Miel Os San Carlos 640 grs

**Análisis**: 2026-05-06  ·  **Inventario**: 2026-04-30

## Resumen

| Campo | Valor |
|---|---|
| Cod Effi | **15** |
| Nombre | Miel Os San Carlos 640 grs |
| Grupo / Unidad | PT / UND |
| Bodega(s) | ["Principal"] |
| Teórico (al cierre) | -9.0 |
| Físico (contado) | 3.0 |
| **Diferencia** | **+12.0** |
| Costo unit | $13,690 |
| **Impacto económico** | **$+164,280** |
| Severidad | significativa |

## Diagnóstico

**Causa probable**: `AJUSTE_NEG_HISTORICO` (confianza 90%)

El teórico era negativo (-9.0) — stock inválido por errores históricos. El conteo físico (3.0) corrige a un valor real positivo. Diferencia (+12.0) = legítima.

### Otras hipótesis

- `OP_GENERADA_PRODUJO` (67%): OPs Generadas (2248) producen 48.0. Cubre 25% del sobrante de 12.0.

## OPs donde se produjo como PRODUCTO (25)

| OP | Fecha | Cant | Estado | Vigencia | Encargado | Obs |
|---|---|---:|---|---|---|---|
| 2248 | 2026-05-06 11:56:59 | 48,00 | Generada | Vigente | Deivy Andres Gonzalez Gut | Etiquetado mieles vidrio del lote OP 2241 (228 und |
| 2220 | 2026-04-27 20:53:15 | 12,00 | Generada | Anulado | Deivy Andres Gonzalez Gut | TEST POST DIRECTO ? anular después - replica OP 22 |
| 2214 | 2026-04-27 12:20:24 | 10,00 | Validado | Vigente | Deivy Andres Gonzalez Gut | Envasado mieles del Carmen pasteurizada ? 6 unid 1 |
| 2204 | 2026-04-24 10:26:24 | 12,00 | Validado | Vigente | Deivy Andres Gonzalez Gut |  |
| 2202 | 2026-04-23 11:11:57 | 6,00 | Validado | Vigente | Deivy Andres Gonzalez Gut |  |
| 2196 | 2026-04-22 15:51:52 | 6,00 | Generada | Anulado | Deivy Andres Gonzalez Gut | Envasado miel ? 6 unid 1000g + 6 unid 640g + 8 uni |
| 2158 | 2026-04-17 12:42:19 | 16,00 | Validado | Vigente | Laura Echavarria | Miel 640 
LOTE 2136 |
| 2136 | 2026-04-10 22:15:23 | 15,00 | Generada | Anulado | Laura Echavarria | Miel 640 
LOTE |
| 2108 | 2026-03-31 19:48:38 | 15,00 | Procesada | Vigente | Laura Echavarria | Miel 640 
LOTE 2058 |
| 2107 | 2026-03-31 19:44:15 | 20,00 | Procesada | Vigente | Laura Echavarria | Miel 1000, 640 
LOTE 2049 |
| 2100 | 2026-03-31 18:37:02 | 14,00 | Procesada | Vigente | Deivy Andres Gonzalez Gut | Miel 1000, 640 
LOTE 2016 |
| 2077 | 2026-03-26 21:03:36 | 24,00 | Procesada | Vigente | Deivy Andres Gonzalez Gut | MIELES SIN ETIQUETAR 
se quebro una miel 275 
LOTE |
| 2075 | 2026-03-26 12:25:32 | 48,00 | Procesada | Vigente | Deivy Andres Gonzalez Gut | MIELES SIN ETIQUETAR 
LOTE |
| 2068 | 2026-03-20 09:21:25 | 6,00 | Generada | Anulado | Laura Echavarria | Miel 640 
LOTE |
| 2058 | 2026-03-16 15:06:07 | 6,00 | Generada | Anulado | Laura Echavarria | Miel 640 
LOTE |

## Trazabilidad Effi (últimos 50 mov vigentes desde 2026-02-01)

| Fecha | Transacción | Cant | Bodega | Vigencia |
|---|---|---:|---|---|
| 2026-05-06 11:56:59 | ORDEN DE PRODUCCIÓN: 2248 | 48,00 | Principal | Transacción vigente |
| 2026-05-06 11:43:51 | NOTA CRÉDITO DE VENTA: 109 | 2,00 | Principal | Transacción vigente |
| 2026-05-06 09:11:53 | FACTURA DE VENTA: 988 | -1,00 | Principal | Transacción vigente |
| 2026-05-06 09:11:53 | REMISIÓN DE VENTA: 2374 | 1,00 | Principal | Transacción anulada |
| 2026-05-06 09:11:35 | REMISIÓN DE VENTA: 2374 | -1,00 | Principal | Transacción anulada |
| 2026-04-30 23:56:02 | FACTURA DE VENTA: 985 | -3,00 | Principal | Transacción vigente |
| 2026-04-30 23:56:02 | ORDEN DE VENTA: 713 | 3,00 | Principal | Transacción anulada |
| 2026-04-30 23:28:02 | ORDEN DE VENTA: 719 | -2,00 | Principal | Transacción vigente |
| 2026-04-30 23:24:04 | FACTURA DE VENTA: 984 | -2,00 | Principal | Transacción vigente |
| 2026-04-30 23:24:04 | ORDEN DE VENTA: 704 | 4,00 | Principal | Transacción anulada |
| 2026-04-30 23:07:21 | ORDEN DE VENTA: 718 | -1,00 | Principal | Transacción vigente |
| 2026-04-30 23:05:24 | ORDEN DE VENTA: 699 | 1,00 | Principal | Transacción anulada |
| 2026-04-30 23:02:09 | REMISIÓN DE VENTA: 2333 | 3,00 | Principal | Transacción anulada |
| 2026-04-30 23:02:08 | FACTURA DE VENTA: 982 | -3,00 | Principal | Transacción vigente |
| 2026-04-30 18:59:27 | FACTURA DE VENTA: 980 | -2,00 | Principal | Transacción vigente |
| 2026-04-30 18:59:27 | REMISIÓN DE VENTA: 2363 | 2,00 | Principal | Transacción anulada |
| 2026-04-30 18:56:02 | REMISIÓN DE VENTA: 2365 | 1,00 | Principal | Transacción anulada |
| 2026-04-30 18:50:47 | FACTURA DE VENTA: 978 | -1,00 | Principal | Transacción vigente |
| 2026-04-30 18:50:47 | REMISIÓN DE VENTA: 2368 | 1,00 | Principal | Transacción anulada |
| 2026-04-30 18:50:05 | REMISIÓN DE VENTA: 2368 | -1,00 | Principal | Transacción anulada |
| 2026-04-30 11:45:06 | REMISIÓN DE VENTA: 2365 | -1,00 | Principal | Transacción anulada |
| 2026-04-30 11:27:58 | FACTURA DE VENTA: 975 | -10,00 | Principal | Transacción vigente |
| 2026-04-30 11:27:58 | REMISIÓN DE VENTA: 2364 | 10,00 | Principal | Transacción anulada |
| 2026-04-30 11:27:37 | REMISIÓN DE VENTA: 2364 | -10,00 | Principal | Transacción anulada |
| 2026-04-30 10:50:10 | REMISIÓN DE VENTA: 2363 | -2,00 | Principal | Transacción anulada |
| 2026-04-30 09:39:20 | REMISIÓN DE VENTA: 2362 | 2,00 | Principal | Transacción anulada |
| 2026-04-30 09:39:19 | FACTURA DE VENTA: 974 | -2,00 | Principal | Transacción vigente |
| 2026-04-30 09:38:30 | REMISIÓN DE VENTA: 2362 | -2,00 | Principal | Transacción anulada |
| 2026-04-29 17:55:57 | REMISIÓN DE VENTA: 2359 | 4,00 | Principal | Transacción anulada |
| 2026-04-29 17:55:56 | FACTURA DE VENTA: 968 | -4,00 | Principal | Transacción vigente |

## Acción sugerida

- Ajuste **INGRESO** de **12.0 UND** en bodega ["Principal"] para igualar físico.
