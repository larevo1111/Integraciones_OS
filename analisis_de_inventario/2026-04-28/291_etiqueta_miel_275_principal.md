# Cod 291 — Etiqueta Miel 275

**Bodega**: Principal  
**Stock actual**: -9.00  
**Costo unitario**: $300  
**Análisis**: 2026-04-28

## Diagnóstico

- Ajuste de inventario AJUSTE DE INVENTARIO: 340 (2025-08-25 16:03:28) generó egreso de 166.00. Si superaba el stock real, queda fantasma.
- Sobreconsumo en OPs: ingresaron 466.00, salieron 892.00.

## Stock por bodega (todas)

| Bodega | Stock |
|---|---|
| Principal | -9.00 |

## Trazabilidad en esta bodega

| Fecha | Transacción | Tipo | Cantidad | Ref |
|---|---|---|---|---|
| 2025-11-07 12:23:56 | ORDEN DE PRODUCCIÓN: 1622 | Creación de transacción | -8.00 |  |
| 2025-11-24 12:04:51 | ORDEN DE PRODUCCIÓN: 1660 | Creación de transacción | -20.00 |  |
| 2025-11-24 20:21:56 | ORDEN DE PRODUCCIÓN: 1664 | Creación de transacción | -8.00 |  |
| 2025-11-24 20:22:23 | ORDEN DE PRODUCCIÓN: 1622 | Anulación de transacción | +8.00 |  |
| 2025-11-29 00:00:23 | ORDEN DE PRODUCCIÓN: 1703 | Creación de transacción | -20.00 |  |
| 2025-12-02 10:17:21 | ORDEN DE PRODUCCIÓN: 1600 | Anulación de transacción | +5.00 |  |
| 2025-12-02 10:20:15 | ORDEN DE PRODUCCIÓN: 1708 | Creación de transacción | -5.00 |  |
| 2025-12-02 10:22:12 | ORDEN DE PRODUCCIÓN: 1708 | Anulación de transacción | +5.00 |  |
| 2025-12-02 10:22:53 | ORDEN DE PRODUCCIÓN: 1709 | Creación de transacción | -5.00 |  |
| 2025-12-04 23:35:32 | ORDEN DE PRODUCCIÓN: 1660 | Anulación de transacción | +20.00 |  |
| 2025-12-04 23:47:27 | ORDEN DE PRODUCCIÓN: 1703 | Anulación de transacción | +20.00 |  |
| 2025-12-04 23:54:40 | ORDEN DE PRODUCCIÓN: 1720 | Creación de transacción | -72.00 |  |
| 2025-12-09 14:40:23 | AJUSTE DE INVENTARIO: 355 | Creación de transacción | -8.00 |  |
| 2025-12-15 10:18:22 | ORDEN DE PRODUCCIÓN: 1760 | Creación de transacción | -7.00 |  |
| 2026-02-05 12:38:25 | ORDEN DE PRODUCCIÓN: 1760 | Anulación de transacción | +7.00 |  |
| 2026-02-05 13:12:39 | NOTA DE REMISIÓN DE COMPRA: 426 | Creación de transacción | +80.00 | Proveedor: Idex Edwin Etiquetas. NIT 3005698734 |
| 2026-02-05 13:13:14 | ORDEN DE PRODUCCIÓN: 1887 | Creación de transacción | -25.00 |  |
| 2026-02-15 22:41:12 | ORDEN DE PRODUCCIÓN: 1887 | Anulación de transacción | +25.00 |  |
| 2026-02-15 22:59:32 | ORDEN DE PRODUCCIÓN: 1975 | Creación de transacción | -59.00 |  |
| 2026-02-16 21:44:16 | NOTA DE REMISIÓN DE COMPRA: 441 | Creación de transacción | +96.00 | Proveedor: Idex Edwin Etiquetas. NIT 3005698734 |
| 2026-02-28 19:36:17 | ORDEN DE PRODUCCIÓN: 2024 | Creación de transacción | -24.00 |  |
| 2026-04-09 07:43:21 | ORDEN DE PRODUCCIÓN: 2126 | Creación de transacción | -24.00 |  |
| 2026-04-09 07:43:43 | ORDEN DE PRODUCCIÓN: 2126 | Anulación de transacción | +24.00 |  |
| 2026-04-09 07:44:20 | ORDEN DE PRODUCCIÓN: 2127 | Creación de transacción | -24.00 |  |
| 2026-04-15 21:11:16 | AJUSTE DE INVENTARIO: 361 | Creación de transacción | -73.00 |  |
| 2026-04-17 12:32:53 | ORDEN DE PRODUCCIÓN: 2127 | Anulación de transacción | +24.00 |  |
| 2026-04-17 12:34:10 | ORDEN DE PRODUCCIÓN: 2156 | Creación de transacción | -24.00 |  |
| 2026-04-24 10:26:24 | ORDEN DE PRODUCCIÓN: 2204 | Creación de transacción | -12.00 |  |
| 2026-04-27 20:53:15 | ORDEN DE PRODUCCIÓN: 2220 | Creación de transacción | -12.00 |  |
| 2026-04-27 20:56:19 | ORDEN DE PRODUCCIÓN: 2220 | Anulación de transacción | +12.00 |  |

## Conteos físicos previos

| Fecha conteo | Bodega | Teórico | Físico | Diferencia | Estado |
|---|---|---|---|---|---|
| 2026-03-31 | Principal | 100.00 | 27.00 | -73.00 | verificado |
| 2026-04-22 | Principal | 3.00 | None | None | pendiente |
| 2026-04-28 | Principal | -9.00 | None | None | pendiente |

## Acción sugerida

Ajuste de **Ingreso** de **9.00** unidades en bodega `Principal` para llevar a 0.

Costo unitario aplicado: $300

---
*Generado automáticamente — auditoria_inventarios_negativos_2026-04-28.md*