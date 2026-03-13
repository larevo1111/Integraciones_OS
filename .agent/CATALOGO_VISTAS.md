# Catálogo de Vistas — ERP Origen Silvestre

> **Leer antes de crear cualquier página nueva.**
> Si la vista que necesitas ya existe, reutilízala (especialmente vistas de detalle de documentos).
> Si no existe, agrégala aquí al terminar.

---

## Regla de navegación (ver MANIFESTO §12)

```
Nivel 1 — Resumen agrupado  →  click  →  Nivel 2 — Lista documentos  →  click  →  Nivel 3 — Detalle documento
```

Toda fila es clickeable. El Nivel 3 SIEMPRE reutiliza la vista canónica del tipo de documento.

---

## Módulo Ventas — Facturación (resúmenes analíticos)

| Nivel | Ruta | Archivo Vue | Fuente de datos |
|---|---|---|---|
| 1 — Resumen por mes | `/ventas/resumen-facturacion` | `ResumenFacturacionPage.vue` | `resumen_ventas_facturas_mes` |
| 2 — Detalle de un mes | `/ventas/detalle-mes/:mes` | `DetalleFacturacionMesPage.vue` | `resumen_ventas_facturas_*` |
| 2 — Detalle canal+mes | `/ventas/detalle-canal/:mes/:canal` | `DetalleCanalMesPage.vue` | `canal-clientes`, `canal-productos`, `canal-facturas` |
| 2 — Detalle cliente+mes | `/ventas/detalle-cliente/:mes/:id_cliente` | `DetalleClienteMesPage.vue` | `resumen-cliente`, `cliente-productos`, `facturas` |
| 2 — Detalle producto+mes | `/ventas/detalle-producto/:mes/:cod_articulo` | `DetalleProductoMesPage.vue` | `producto-canales`, `producto-clientes`, `producto-facturas` |
| **3 — Detalle factura** ⭐ | `/ventas/detalle-factura/:id_interno/:id_numeracion` | `DetalleFacturaPage.vue` | `factura/:id_interno/:id_numeracion` |

> ⭐ Vista canónica de factura. Cualquier módulo que muestre una factura debe navegar aquí.

---

## Módulo Ventas — Cartera CxC

| Nivel | Ruta | Archivo Vue | Fuente de datos |
|---|---|---|---|
| 1 — Resumen por cliente | `/ventas/cartera` | `CarteraPage.vue` | `/api/ventas/cartera-cliente` |
| 2 — Facturas del cliente | `/ventas/cartera/:id_cliente` | `DetalleCarteraClientePage.vue` | `/api/ventas/cartera-cliente/:id_cliente` |
| 3 — Detalle factura ⭐ | `/ventas/detalle-factura/:id_interno/:id_numeracion` | `DetalleFacturaPage.vue` | (reutiliza vista canónica) |

**Navegación:**
```
CarteraPage → click cliente → DetalleCarteraClientePage → click factura → DetalleFacturaPage
```

---

## Módulo Ventas — Consignación

| Nivel | Ruta | Archivo Vue | Fuente de datos |
|---|---|---|---|
| 1 — Resumen por cliente | `/ventas/consignacion` | `ConsignacionPage.vue` | `/api/ventas/consignacion` (GROUP BY cliente) |
| 2 — Órdenes del cliente | `/ventas/consignacion-cliente/:id_cliente` | `ConsignacionClientePage.vue` | `/api/ventas/consignacion-cliente/:id_cliente` |
| **3 — Detalle orden** ⭐ | `/ventas/consignacion-orden/:id_orden` | `DetalleConsignacionPage.vue` | `/api/ventas/consignacion-orden/:id_orden` |

**Navegación:**
```
ConsignacionPage → click cliente → ConsignacionClientePage → click orden → DetalleConsignacionPage
```

**Filtro datos:** `WHERE vigencia = 'Vigente'` en todos los niveles.
**Total activo (2026-03-13):** 13 órdenes, 9 clientes, total bruto $7.380.375, total neto $7.763.832.

---

## Pendientes (placeholder en routes.js)

| Módulo | Ruta prevista | Estado |
|---|---|---|
| Resumen Remisiones | `/ventas/resumen-remisiones` | Placeholder |
| Pedidos pendientes | `/ventas/pedidos-pendientes` | Placeholder |
| Facturas (listado) | `/ventas/facturas` | Placeholder |
| Remisiones (listado) | `/ventas/remisiones` | Placeholder |
| Cotizaciones (listado) | `/ventas/cotizaciones` | Placeholder |

---

## Convenciones de nomenclatura

| Patrón ruta | Significado |
|---|---|
| `/ventas/{mod}` | Nivel 1: resumen agrupado |
| `/ventas/{mod}-cliente/:id` | Nivel 2: documentos del cliente |
| `/ventas/{mod}-orden/:id` | Nivel 3: detalle de una orden/documento |
| `/ventas/detalle-factura/:a/:b` | Nivel 3 canónico: detalle de factura (reutilizable) |
| `/ventas/detalle-mes/:mes` | Nivel 2 temporal: detalle de período mensual |
