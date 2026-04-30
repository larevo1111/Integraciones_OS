# Cod 298 — Etiqueta Propóleo 150

**Bodega**: Principal  
**Stock actual**: -24.00  
**Costo unitario**: $300  
**Análisis**: 2026-04-28

## Diagnóstico

- Ajuste de inventario AJUSTE DE INVENTARIO: 170 (2024-11-01 15:34:34) generó egreso de 26.00. Si superaba el stock real, queda fantasma.
- Sobreconsumo en OPs: ingresaron 421.00, salieron 944.00.

## Stock por bodega (todas)

| Bodega | Stock |
|---|---|
| Principal | -24.00 |

## Trazabilidad en esta bodega

| Fecha | Transacción | Tipo | Cantidad | Ref |
|---|---|---|---|---|
| 2025-10-29 00:20:15 | AJUSTE DE INVENTARIO: 350 | Creación de transacción | +18.00 |  |
| 2025-11-07 12:44:32 | ORDEN DE PRODUCCIÓN: 1625 | Creación de transacción | -12.00 |  |
| 2025-11-24 21:13:06 | ORDEN DE PRODUCCIÓN: 1625 | Anulación de transacción | +12.00 |  |
| 2025-11-24 21:13:37 | ORDEN DE PRODUCCIÓN: 1666 | Creación de transacción | -12.00 |  |
| 2025-12-05 14:08:49 | ORDEN DE PRODUCCIÓN: 1730 | Creación de transacción | -12.00 |  |
| 2025-12-05 14:09:00 | ORDEN DE PRODUCCIÓN: 1730 | Anulación de transacción | +12.00 |  |
| 2025-12-09 14:46:15 | AJUSTE DE INVENTARIO: 356 | Creación de transacción | +12.00 |  |
| 2025-12-10 10:51:30 | ORDEN DE PRODUCCIÓN: 1745 | Creación de transacción | -12.00 |  |
| 2025-12-16 10:54:08 | ORDEN DE PRODUCCIÓN: 1772 | Creación de transacción | -20.00 |  |
| 2026-01-02 13:14:34 | ORDEN DE PRODUCCIÓN: 1794 | Creación de transacción | -7.00 |  |
| 2026-01-02 13:14:44 | ORDEN DE PRODUCCIÓN: 1794 | Anulación de transacción | +7.00 |  |
| 2026-01-02 13:15:03 | ORDEN DE PRODUCCIÓN: 1795 | Creación de transacción | -7.00 |  |
| 2026-01-23 14:00:08 | ORDEN DE PRODUCCIÓN: 1858 | Creación de transacción | -24.00 |  |
| 2026-02-05 13:26:35 | ORDEN DE PRODUCCIÓN: 1772 | Anulación de transacción | +20.00 |  |
| 2026-02-05 13:27:21 | ORDEN DE PRODUCCIÓN: 1888 | Creación de transacción | -20.00 |  |
| 2026-02-06 14:14:14 | ORDEN DE PRODUCCIÓN: 1795 | Anulación de transacción | +7.00 |  |
| 2026-02-06 14:15:05 | ORDEN DE PRODUCCIÓN: 1904 | Creación de transacción | -17.00 |  |
| 2026-02-06 22:12:19 | ORDEN DE PRODUCCIÓN: 1858 | Anulación de transacción | +24.00 |  |
| 2026-02-06 22:15:39 | ORDEN DE PRODUCCIÓN: 1915 | Creación de transacción | -24.00 |  |
| 2026-02-16 21:46:27 | NOTA DE REMISIÓN DE COMPRA: 442 | Creación de transacción | +80.00 | Proveedor: Idex Edwin Etiquetas. NIT 3005698734 |
| 2026-02-19 08:53:53 | ORDEN DE PRODUCCIÓN: 2000 | Creación de transacción | -24.00 |  |
| 2026-03-02 14:14:26 | ORDEN DE PRODUCCIÓN: 2027 | Creación de transacción | -30.00 |  |
| 2026-03-12 17:37:31 | ORDEN DE PRODUCCIÓN: 2050 | Creación de transacción | -33.00 |  |
| 2026-03-31 19:41:03 | ORDEN DE PRODUCCIÓN: 2050 | Anulación de transacción | +33.00 |  |
| 2026-03-31 19:42:46 | ORDEN DE PRODUCCIÓN: 2106 | Creación de transacción | -20.00 |  |
| 2026-04-07 09:46:30 | ORDEN DE PRODUCCIÓN: 2119 | Creación de transacción | -24.00 |  |
| 2026-04-15 21:11:16 | AJUSTE DE INVENTARIO: 361 | Creación de transacción | -3.00 |  |
| 2026-04-17 12:23:21 | ORDEN DE PRODUCCIÓN: 2119 | Anulación de transacción | +24.00 |  |
| 2026-04-17 12:25:05 | ORDEN DE PRODUCCIÓN: 2153 | Creación de transacción | -10.00 |  |
| 2026-04-23 10:56:03 | ORDEN DE PRODUCCIÓN: 2198 | Creación de transacción | -24.00 |  |

## Conteos físicos previos

| Fecha conteo | Bodega | Teórico | Físico | Diferencia | Estado |
|---|---|---|---|---|---|
| 2026-03-31 | Principal | 13.00 | 10.00 | -3.00 | verificado |
| 2026-04-22 | Principal | 0.00 | None | None | pendiente |
| 2026-04-28 | Principal | -24.00 | None | None | pendiente |

## Acción sugerida

Ajuste de **Ingreso** de **24.00** unidades en bodega `Principal` para llevar a 0.

Costo unitario aplicado: $300

---
*Generado automáticamente — auditoria_inventarios_negativos_2026-04-28.md*