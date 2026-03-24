# Contexto: ERP Frontend
**Actualizado**: 2026-03-23

## Advertencia importante

`menu.oscomunidad.com` **NO es el ERP definitivo**. Es una **app temporal de visualización de datos** mientras se construye el ERP real. La usan Santi y Jen para ver información de ventas.

El **ERP real** está en `u768061575_os_comunidad` (Hostinger) — **⚠️ NO TOCAR**.

## Stack técnico

| Componente | Detalle |
|---|---|
| Framework | Vue 3 + Quasar |
| API backend | Express.js |
| URL pública | menu.oscomunidad.com |
| Puerto API | 9100 |
| Systemd | `os-erp-frontend` |
| Directorio | `frontend/` |
| Build prod | `cd frontend/app && npx quasar build` |
| Dev | `cd frontend/app && npx quasar dev` |

## Regla ABSOLUTA antes de cualquier trabajo frontend

1. Leer `frontend/design-system/MANUAL_ESTILOS.md` — fuente de verdad única del diseño
2. Ver capturas en `frontend/design-system/screenshots/` (88 imágenes de Linear.app)
3. Seguir el manual al pie de la letra: colores, tipografía, espaciado, CSS
4. Si el elemento NO está en el manual → DETENERSE. Preguntar a Santi y definirlo juntos antes de implementar
5. Una vez definido el elemento nuevo, actualizar el manual inmediatamente

Después de cualquier cambio Vue/JS: `cd frontend/app && npx quasar build`

## Módulos y páginas activas

### Módulo Ventas

| Página | Ruta | Estado |
|---|---|---|
| ResumenFacturacionPage | `/ventas/resumen` | ✅ 3 pestañas: Por mes / Por producto / Por grupo |
| DetalleFacturacionMesPage | `/ventas/detalle-mes/:mes` | ✅ KPIs + 6 tablas acordeón + drill-down |
| DetalleClienteMesPage | `/ventas/detalle-cliente/:mes/:id_cliente` | ✅ |
| DetalleCanalMesPage | `/ventas/detalle-canal/:mes/:canal` | ✅ |
| DetalleProductoMesPage | `/ventas/detalle-producto/:mes/:cod_articulo` | ✅ |
| DetalleFacturaPage | `/ventas/detalle-factura/:id_interno/:id_numeracion` | ✅ Vista canónica |
| DetalleFacturasProductoPage | `/ventas/facturas-producto/:cod` y `/ventas/facturas-grupo/:grupo` | ✅ Reutilizable |
| CarteraPage | `/ventas/cartera` | ✅ KPIs + tabla resumen por cliente |
| DetalleCarteraClientePage | `/ventas/cartera/:id_cliente` | ✅ Facturas pendientes del cliente |
| ConsignacionPage | `/ventas/consignacion` | ✅ 2 tabs: Por cliente / Por producto. Filtro: `vigencia='Vigente'` |
| DetalleConsignacionPage | `/ventas/consignacion-orden/:id_orden` | ✅ |
| ConsignacionProductoPage | `/ventas/consignacion-producto/:cod_articulo` | ✅ |

### ResumenFacturacionPage — detalle

Tab "Por mes": tabla histórica mensual (click → DetalleFacturacionMesPage)
Tab "Por producto": totales por artículo con costo, utilidad, margen, NC; filter bar fechas; drill-down a DetalleFacturasProductoPage
Tab "Por grupo": agrupado por grupo_producto; mismas métricas; drill-down a DetalleFacturasProductoPage

## Jerarquía de navegación drill-down

```
ResumenFacturacionPage — tab Por mes
  └─ click fila → DetalleFacturacionMesPage (mes)
       ├─ click canal    → DetalleCanalMesPage
       ├─ click cliente  → DetalleClienteMesPage
       ├─ click producto → DetalleProductoMesPage
       └─ click factura  → DetalleFacturaPage ★ (vista canónica)

ResumenFacturacionPage — tab Por producto (con filtro fechas)
  └─ click fila → DetalleFacturasProductoPage (/facturas-producto/:cod)
       └─ click factura → DetalleFacturaPage ★

ResumenFacturacionPage — tab Por grupo (con filtro fechas)
  └─ click fila → DetalleFacturasProductoPage (/facturas-grupo/:grupo)
       └─ click factura → DetalleFacturaPage ★

ConsignacionPage — tab Por cliente
  └─ click → ConsignacionClientePage → click orden → DetalleConsignacionPage

ConsignacionPage — tab Por producto
  └─ click → ConsignacionProductoPage → click orden → DetalleConsignacionPage
```

## Componente OsDataTable

`components/OsDataTable.vue` — tabla reutilizable

**Props**: `rows`, `columns ({key,label,visible})`, `loading`, `title`, `recurso`, `mes`, `tooltips`
**Emits**: `row-click`

Características:
- **Fila de subtotales al TOPE** (justo debajo del `<thead>`, sticky `top: 36px; z-index: 4`) — NO al pie
- Mini-popup por columna: Filtro (6 operadores), Ordenamiento, Subtotal (Σ x̄ ↑ ↓)
- Tooltips: carga `/api/tooltips` automáticamente (caché global, no necesita prop)
- Formato auto: `fin_/cto_/car_` → `$COP`, `_pct/_margen` → `%` (×100), resto → número con `.` miles
- Botón export (CSV/XLSX/PDF) via `/api/export/:recurso`

## API Express — endpoints activos (server.js)

```
GET  /api/ventas/resumen-mes|canal|cliente|producto    — tablas resumen Hostinger
GET  /api/ventas/facturas|cotizaciones|remisiones       — encabezados zeffi (filtro mes)
GET  /api/ventas/resumen-por-producto                  — toda la vida por cod_articulo, JOIN catalogo_articulos. Acepta ?desde=&hasta=
GET  /api/ventas/resumen-por-grupo                     — toda la vida por grupo_producto. Acepta ?desde=&hasta=
GET  /api/ventas/anios-facturas                        — años distintos disponibles
GET  /api/ventas/facturas-producto/:cod_articulo        — facturas donde aparece el producto
GET  /api/ventas/facturas-grupo/:grupo                  — facturas donde aparece cualquier ref. del grupo
GET  /api/ventas/cliente-productos|canal-clientes|canal-productos|canal-facturas|canal-remisiones
GET  /api/ventas/producto-canales|producto-clientes|producto-facturas
GET  /api/ventas/factura/:id_interno/:id_numeracion     — encabezado + ítems
GET  /api/ventas/cartera|cartera-cliente|cartera-cliente/:id
GET  /api/ventas/consignacion                          — OVs activas (vigencia='Vigente')
GET  /api/ventas/consignacion/:id_orden                 — detalle orden
GET  /api/ventas/consignacion-cliente/:id_cliente
GET  /api/ventas/consignacion-por-producto
GET  /api/ventas/consignacion-producto/:cod_articulo
GET  /api/tooltips                                     — ~60 descripciones de columnas
GET  /api/columnas/:tabla                              — columnas de cualquier tabla Hostinger
GET  /api/export/:recurso                              — CSV / XLSX / PDF
```

La API lee de Hostinger (`u768061575_os_integracion`) para tablas analíticas, y de `effi_data` local para zeffi_*.

## App IA Admin

| Recurso | Detalle |
|---|---|
| URL | ia.oscomunidad.com |
| Puerto | 9200 |
| Systemd | `os-ia-admin.service` |
| Directorio | `ia-admin/` |

## Tabla sys_menu

En Hostinger `u768061575_os_integracion`: 36 registros (7 módulos + 29 submenús).

## Estado módulo Ventas (resumen)

ResumenFacturacionPage tiene 3 pestañas pill:
1. **Por mes** — tabla histórica mensual
2. **Por producto** — totales por artículo con costo, utilidad, margen, NC; filter bar fechas
3. **Por grupo** — agrupado por grupo_producto; mismas métricas

OsDataTable: fila de subtotales al TOP (sticky debajo del header, `top: 36px; z-index: 4`).

## Gotcha precio_neto_total

`precio_neto_total` en detalle de facturas **incluye IVA**.
Usar `precio_bruto_total - descuento_total` para ventas netas sin IVA.

## Próximos módulos pendientes

- Páginas de Remisiones
- Módulo Clientes
- Módulo Productos

## Archivos clave

| Archivo | Propósito |
|---|---|
| `frontend/app/` | Proyecto Vue+Quasar |
| `frontend/api/` | API Express |
| `frontend/api/server.js` | Endpoints activos |
| `frontend/app/src/pages/ventas/` | Páginas del módulo Ventas |
| `frontend/app/src/components/OsDataTable.vue` | Tabla reutilizable principal |
| `frontend/design-system/MANUAL_ESTILOS.md` | Manual de estilos v2.0 — obligatorio leer |
| `frontend/design-system/screenshots/` | 88 capturas de referencia Linear.app |
