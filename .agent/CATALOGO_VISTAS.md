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

`ResumenFacturacionPage.vue` tiene **3 pestañas (pill tabs)**:
- **Por mes** — tabla histórica mensual (`resumen_ventas_facturas_mes`)
- **Por producto** — totales por artículo con costo, utilidad, margen, notas crédito; filtro de fechas y drill-down
- **Por grupo** — agrupado por `grupo_producto` (desde `catalogo_articulos`); mismas métricas; filtro de fechas y drill-down

Las pestañas Por producto y Por grupo tienen **filter bar** con: botón Todas, pills de año (dinámicos desde BD), trimestres Q1–Q4 contextuales (segunda fila con año label), e inputs de fecha nativa desde/hasta.

| Nivel | Ruta | Archivo Vue | Fuente de datos |
|---|---|---|---|
| 1 — Resumen por mes | `/ventas/resumen-facturacion` (tab Por mes) | `ResumenFacturacionPage.vue` | `resumen_ventas_facturas_mes` |
| 1 — Resumen por producto | `/ventas/resumen-facturacion` (tab Por producto) | `ResumenFacturacionPage.vue` | `/api/ventas/resumen-por-producto` |
| 1 — Resumen por grupo | `/ventas/resumen-facturacion` (tab Por grupo) | `ResumenFacturacionPage.vue` | `/api/ventas/resumen-por-grupo` |
| 2 — Facturas de un producto | `/ventas/facturas-producto/:cod_articulo` | `DetalleFacturasProductoPage.vue` | `/api/ventas/facturas-producto/:cod_articulo` |
| 2 — Facturas de un grupo | `/ventas/facturas-grupo/:grupo` | `DetalleFacturasProductoPage.vue` | `/api/ventas/facturas-grupo/:grupo` |
| 2 — Detalle de un mes | `/ventas/detalle-mes/:mes` | `DetalleFacturacionMesPage.vue` | `resumen_ventas_facturas_*` |
| 2 — Detalle canal+mes | `/ventas/detalle-canal/:mes/:canal` | `DetalleCanalMesPage.vue` | `canal-clientes`, `canal-productos`, `canal-facturas` |
| 2 — Detalle cliente+mes | `/ventas/detalle-cliente/:mes/:id_cliente` | `DetalleClienteMesPage.vue` | `resumen-cliente`, `cliente-productos`, `facturas` |
| 2 — Detalle producto+mes | `/ventas/detalle-producto/:mes/:cod_articulo` | `DetalleProductoMesPage.vue` | `producto-canales`, `producto-clientes`, `producto-facturas` |
| **3 — Detalle factura** ⭐ | `/ventas/detalle-factura/:id_interno/:id_numeracion` | `DetalleFacturaPage.vue` | `factura/:id_interno/:id_numeracion` |

> ⭐ Vista canónica de factura. Cualquier módulo que muestre una factura debe navegar aquí.

**Nota:** `DetalleFacturasProductoPage.vue` es reutilizable para ambas rutas. Detecta el modo via `route.path.includes('/facturas-grupo/')` y ajusta columnas, KPIs y endpoint automáticamente.

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
