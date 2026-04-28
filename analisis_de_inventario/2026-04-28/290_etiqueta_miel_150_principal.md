# Cod 290 — Etiqueta Miel 150

**Bodega**: Principal  
**Stock actual**: -22.00  
**Costo unitario**: $300  
**Análisis**: 2026-04-28

## Diagnóstico

- Ajuste de inventario AJUSTE DE INVENTARIO: 350 (2025-10-29 00:20:15) generó egreso de 89.00. Si superaba el stock real, queda fantasma.
- Sobreconsumo en OPs: ingresaron 510.00, salieron 1083.00.

## Stock por bodega (todas)

| Bodega | Stock |
|---|---|
| Principal | -22.00 |

## Trazabilidad en esta bodega

| Fecha | Transacción | Tipo | Cantidad | Ref |
|---|---|---|---|---|
| 2025-12-02 10:17:21 | ORDEN DE PRODUCCIÓN: 1600 | Anulación de transacción | +24.00 |  |
| 2025-12-02 10:20:15 | ORDEN DE PRODUCCIÓN: 1708 | Creación de transacción | -24.00 |  |
| 2025-12-02 10:22:12 | ORDEN DE PRODUCCIÓN: 1708 | Anulación de transacción | +24.00 |  |
| 2025-12-02 10:22:53 | ORDEN DE PRODUCCIÓN: 1709 | Creación de transacción | -24.00 |  |
| 2025-12-04 23:35:32 | ORDEN DE PRODUCCIÓN: 1660 | Anulación de transacción | +20.00 |  |
| 2025-12-04 23:47:38 | ORDEN DE PRODUCCIÓN: 1706 | Anulación de transacción | +15.00 |  |
| 2025-12-04 23:54:40 | ORDEN DE PRODUCCIÓN: 1720 | Creación de transacción | -35.00 |  |
| 2025-12-09 14:46:15 | AJUSTE DE INVENTARIO: 356 | Creación de transacción | +4.00 |  |
| 2025-12-15 10:18:22 | ORDEN DE PRODUCCIÓN: 1760 | Creación de transacción | -4.00 |  |
| 2026-02-05 12:38:25 | ORDEN DE PRODUCCIÓN: 1760 | Anulación de transacción | +4.00 |  |
| 2026-02-05 13:12:39 | NOTA DE REMISIÓN DE COMPRA: 426 | Creación de transacción | +90.00 | Proveedor: Idex Edwin Etiquetas. NIT 3005698734 |
| 2026-02-05 13:13:14 | ORDEN DE PRODUCCIÓN: 1887 | Creación de transacción | -25.00 |  |
| 2026-02-05 14:55:14 | ORDEN DE PRODUCCIÓN: 1896 | Creación de transacción | -18.00 |  |
| 2026-02-15 22:41:12 | ORDEN DE PRODUCCIÓN: 1887 | Anulación de transacción | +25.00 |  |
| 2026-02-15 22:59:32 | ORDEN DE PRODUCCIÓN: 1975 | Creación de transacción | -71.00 |  |
| 2026-02-16 21:44:16 | NOTA DE REMISIÓN DE COMPRA: 441 | Creación de transacción | +120.00 | Proveedor: Idex Edwin Etiquetas. NIT 3005698734 |
| 2026-02-28 17:22:12 | ORDEN DE PRODUCCIÓN: 2021 | Creación de transacción | -25.00 |  |
| 2026-04-09 07:43:21 | ORDEN DE PRODUCCIÓN: 2126 | Creación de transacción | -36.00 |  |
| 2026-04-09 07:43:43 | ORDEN DE PRODUCCIÓN: 2126 | Anulación de transacción | +36.00 |  |
| 2026-04-09 07:44:20 | ORDEN DE PRODUCCIÓN: 2127 | Creación de transacción | -36.00 |  |
| 2026-04-15 21:11:16 | AJUSTE DE INVENTARIO: 361 | Creación de transacción | -72.00 |  |
| 2026-04-17 12:32:53 | ORDEN DE PRODUCCIÓN: 2127 | Anulación de transacción | +36.00 |  |
| 2026-04-17 12:34:10 | ORDEN DE PRODUCCIÓN: 2156 | Creación de transacción | -23.00 |  |
| 2026-04-22 15:51:52 | ORDEN DE PRODUCCIÓN: 2196 | Creación de transacción | -8.00 |  |
| 2026-04-23 11:11:03 | ORDEN DE PRODUCCIÓN: 2196 | Anulación de transacción | +8.00 |  |
| 2026-04-23 11:11:57 | ORDEN DE PRODUCCIÓN: 2202 | Creación de transacción | -8.00 |  |
| 2026-04-24 10:26:24 | ORDEN DE PRODUCCIÓN: 2204 | Creación de transacción | -12.00 |  |
| 2026-04-27 12:20:24 | ORDEN DE PRODUCCIÓN: 2214 | Creación de transacción | -7.00 |  |
| 2026-04-27 20:53:15 | ORDEN DE PRODUCCIÓN: 2220 | Creación de transacción | -12.00 |  |
| 2026-04-27 20:56:19 | ORDEN DE PRODUCCIÓN: 2220 | Anulación de transacción | +12.00 |  |

## Conteos físicos previos

| Fecha conteo | Bodega | Teórico | Físico | Diferencia | Estado |
|---|---|---|---|---|---|
| 2026-03-31 | Principal | 100.00 | 28.00 | -72.00 | verificado |
| 2026-04-22 | Principal | 5.00 | None | None | pendiente |
| 2026-04-28 | Principal | -22.00 | None | None | pendiente |

## Acción sugerida

Ajuste de **Ingreso** de **22.00** unidades en bodega `Principal` para llevar a 0.

Costo unitario aplicado: $300

---
*Generado automáticamente — auditoria_inventarios_negativos_2026-04-28.md*