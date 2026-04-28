# Cod 379 — DS AJI VARIEDADES x KG

**Bodega**: Principal  
**Stock actual**: -0.45  
**Costo unitario**: $50.000  
**Análisis**: 2026-04-28

## Diagnóstico

- Ajuste de inventario AJUSTE DE INVENTARIO: 242 (2025-03-03 22:10:54) generó egreso de 86.00. Si superaba el stock real, queda fantasma.
- Sobreconsumo en OPs: ingresaron 30.04, salieron 31.53.

## Stock por bodega (todas)

| Bodega | Stock |
|---|---|
| Principal | -0.45 |

## Trazabilidad en esta bodega

| Fecha | Transacción | Tipo | Cantidad | Ref |
|---|---|---|---|---|
| 2025-03-17 20:17:54 | ORDEN DE PRODUCCIÓN: 832 | Anulación de transacción | +14.00 |  |
| 2025-03-17 20:18:48 | ORDEN DE PRODUCCIÓN: 831 | Anulación de transacción | +0.05 |  |
| 2025-03-17 20:26:14 | ORDEN DE PRODUCCIÓN: 833 | Creación de transacción | -0.05 |  |
| 2025-05-09 16:22:52 | AJUSTE DE INVENTARIO: 326 | Creación de transacción | -14.00 |  |
| 2025-05-12 15:55:10 | NOTA DE REMISIÓN DE COMPRA: 339 | Creación de transacción | +0.25 | Proveedor: Ricardo Alonso Garcia Garcia. CC 8160663 |
| 2025-05-12 16:43:14 | ORDEN DE PRODUCCIÓN: 1083 | Creación de transacción | -0.25 |  |
| 2025-05-19 14:11:09 | ORDEN DE PRODUCCIÓN: 1083 | Anulación de transacción | +0.25 |  |
| 2025-05-19 14:12:58 | ORDEN DE PRODUCCIÓN: 1104 | Creación de transacción | -0.25 |  |
| 2025-06-27 16:43:45 | ORDEN DE PRODUCCIÓN: 1104 | Anulación de transacción | +0.25 |  |
| 2025-06-27 16:44:02 | ORDEN DE PRODUCCIÓN: 1273 | Creación de transacción | -0.25 |  |
| 2025-06-27 16:45:01 | ORDEN DE PRODUCCIÓN: 1273 | Anulación de transacción | +0.25 |  |
| 2025-06-27 16:45:49 | ORDEN DE PRODUCCIÓN: 1274 | Creación de transacción | -0.25 |  |
| 2025-06-27 16:46:20 | ORDEN DE PRODUCCIÓN: 1274 | Anulación de transacción | +0.25 |  |
| 2025-06-27 16:46:34 | ORDEN DE PRODUCCIÓN: 1275 | Creación de transacción | -0.25 |  |
| 2025-09-04 00:39:12 | NOTA DE REMISIÓN DE COMPRA: 374 | Creación de transacción | +0.50 | Proveedor: Ricardo Alonso Garcia Garcia. CC 8160663 |
| 2025-09-04 00:39:27 | ORDEN DE PRODUCCIÓN: 1446 | Creación de transacción | -0.25 |  |
| 2025-09-11 10:49:20 | NOTA DE REMISIÓN DE COMPRA: 378 | Creación de transacción | +0.50 | Proveedor: LA DESPENSA DE LAS ESPECIAS. CC 5118114 |
| 2025-09-11 10:50:12 | NOTA DE REMISIÓN DE COMPRA: 374 | Anulación de transacción | -0.50 | Proveedor: Ricardo Alonso Garcia Garcia. CC 8160663 |
| 2025-09-16 07:54:21 | ORDEN DE PRODUCCIÓN: 1446 | Anulación de transacción | +0.25 |  |
| 2025-09-16 07:56:46 | ORDEN DE PRODUCCIÓN: 1480 | Creación de transacción | -0.25 |  |
| 2025-09-16 07:59:41 | ORDEN DE PRODUCCIÓN: 1480 | Anulación de transacción | +0.25 |  |
| 2025-09-16 08:00:01 | ORDEN DE PRODUCCIÓN: 1482 | Creación de transacción | -0.25 |  |
| 2025-10-29 00:20:15 | AJUSTE DE INVENTARIO: 350 | Creación de transacción | -0.25 |  |
| 2025-12-07 01:02:21 | NOTA DE REMISIÓN DE COMPRA: 407 | Creación de transacción | +0.49 | Proveedor: Jenifer Alexandra Cano Garcia. CC 1128457413 |
| 2025-12-11 12:33:20 | ORDEN DE PRODUCCIÓN: 1751 | Creación de transacción | -0.49 |  |
| 2026-01-13 09:55:21 | ORDEN DE PRODUCCIÓN: 1751 | Anulación de transacción | +0.49 |  |
| 2026-01-13 17:17:59 | ORDEN DE PRODUCCIÓN: 1823 | Creación de transacción | -0.49 |  |
| 2026-03-30 21:36:55 | NOTA DE REMISIÓN DE COMPRA: 454 | Creación de transacción | +0.27 | Proveedor: Jenifer Alexandra Cano Garcia. NIT 1128457413 |
| 2026-04-15 21:11:17 | AJUSTE DE INVENTARIO: 361 | Creación de transacción | -0.27 |  |
| 2026-04-28 12:40:09 | ORDEN DE PRODUCCIÓN: 2229 | Creación de transacción | -0.45 |  |

## Conteos físicos previos

| Fecha conteo | Bodega | Teórico | Físico | Diferencia | Estado |
|---|---|---|---|---|---|
| 2026-03-31 | Principal | 0.27 | 0.00 | -0.27 | verificado |
| 2026-04-22 | Principal | 0.00 | None | None | pendiente |

## Acción sugerida

Ajuste de **Ingreso** de **0.45** unidades en bodega `Principal` para llevar a 0.

Costo unitario aplicado: $50.000

---
*Generado automáticamente — auditoria_inventarios_negativos_2026-04-28.md*