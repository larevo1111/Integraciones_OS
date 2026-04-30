# Cod 553 — Envase 110cc C/Tapa  B. 46 - ESTERILIZADO

**Bodega**: Principal  
**Stock actual**: -88.00  
**Costo unitario**: $1.500  
**Análisis**: 2026-04-28

## Diagnóstico

- Ajuste de inventario AJUSTE DE INVENTARIO: 364 (2026-04-20 21:40:32) generó egreso de 62.00. Si superaba el stock real, queda fantasma.
- Sobreconsumo en OPs: ingresaron 31.00, salieron 137.00.

## Stock por bodega (todas)

| Bodega | Stock |
|---|---|
| Principal | -88.00 |

## Trazabilidad en esta bodega

| Fecha | Transacción | Tipo | Cantidad | Ref |
|---|---|---|---|---|
| 2026-04-15 21:11:17 | AJUSTE DE INVENTARIO: 361 | Creación de transacción | +80.00 |  |
| 2026-04-20 21:40:32 | AJUSTE DE INVENTARIO: 364 | Creación de transacción | -62.00 |  |
| 2026-04-23 10:56:03 | ORDEN DE PRODUCCIÓN: 2198 | Creación de transacción | -24.00 |  |
| 2026-04-23 11:09:37 | ORDEN DE PRODUCCIÓN: 2200 | Creación de transacción | -19.00 |  |
| 2026-04-23 11:09:55 | ORDEN DE PRODUCCIÓN: 2201 | Creación de transacción | -19.00 |  |
| 2026-04-23 11:10:01 | ORDEN DE PRODUCCIÓN: 2200 | Anulación de transacción | +19.00 |  |
| 2026-04-24 10:26:24 | ORDEN DE PRODUCCIÓN: 2204 | Creación de transacción | -12.00 |  |
| 2026-04-24 10:33:37 | ORDEN DE PRODUCCIÓN: 2205 | Creación de transacción | -12.00 |  |
| 2026-04-27 12:20:24 | ORDEN DE PRODUCCIÓN: 2214 | Creación de transacción | -7.00 |  |
| 2026-04-27 20:12:26 | ORDEN DE PRODUCCIÓN: 2217 | Creación de transacción | -26.00 |  |
| 2026-04-27 20:53:15 | ORDEN DE PRODUCCIÓN: 2220 | Creación de transacción | -12.00 |  |
| 2026-04-27 20:56:19 | ORDEN DE PRODUCCIÓN: 2220 | Anulación de transacción | +12.00 |  |
| 2026-04-28 12:36:54 | ORDEN DE PRODUCCIÓN: 2225 | Creación de transacción | -6.00 |  |

## Conteos físicos previos

| Fecha conteo | Bodega | Teórico | Físico | Diferencia | Estado |
|---|---|---|---|---|---|
| 2026-03-31 | Principal | 0.00 | 80.00 | 80.00 | verificado |
| 2026-04-20 | Principal | 80.00 | 18.00 | -62.00 | contado |
| 2026-04-22 | Principal | 18.00 | None | None | pendiente |
| 2026-04-28 | Principal | -82.00 | None | None | pendiente |

## Acción sugerida

Ajuste de **Ingreso** de **88.00** unidades en bodega `Principal` para llevar a 0.

Costo unitario aplicado: $1.500

---
*Generado automáticamente — auditoria_inventarios_negativos_2026-04-28.md*