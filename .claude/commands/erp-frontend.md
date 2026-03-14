# Skill: ERP Frontend — Origen Silvestre

> Stack completo del ERP web: Vue 3 + Quasar + API Express + MySQL Hostinger.
> URL pública: **menu.oscomunidad.com** — Cloudflare Tunnel → localhost:9100
> Diseño: Linear.app (modo claro) — respetar `frontend/design-system/MANUAL_ESTILOS.md`

---

## 1. ARQUITECTURA

```
erp.oscomunidad.com
      ↓ Cloudflare Tunnel
  localhost:9100
      ↓ Express (frontend/api/server.js)
   ├── /api/* → consultas MySQL Hostinger (SSH tunnel)
   └── /* → sirve dist/spa (Quasar build)
```

**Un solo servidor en puerto 9100** sirve tanto la API como el frontend estático.

### Servicios systemd
| Servicio | Qué hace | Cómo reiniciar |
|---|---|---|
| `os-erp-frontend` | Express + frontend en puerto 9100 | `systemctl restart os-erp-frontend` |

### Paths clave
| Recurso | Ruta |
|---|---|
| API Express | `frontend/api/server.js` |
| DB helper | `frontend/api/db.js` |
| App Vue | `frontend/app/src/` |
| Build Quasar | `cd frontend/app && npx quasar build` |
| Dist (servida) | `frontend/app/dist/spa/` |
| Páginas | `frontend/app/src/pages/` |
| Componentes | `frontend/app/src/components/` |
| Layouts | `frontend/app/src/layouts/` |
| Router | `frontend/app/src/router/routes.js` |
| CSS global | `frontend/app/src/css/app.scss` |
| Design system | `frontend/design-system/MANUAL_ESTILOS.md` |

---

## 2. BASE DE DATOS (API)

La API Express se conecta a **MySQL Hostinger** vía SSH tunnel.

```
Host MySQL: u768061575_os_integracion (Hostinger)
SSH: 109.106.250.195:65002 con key ~/.ssh/sos_erp
User MySQL: u768061575_osserver / Epist2487.
```

**Tablas disponibles en Hostinger:**
- 41 tablas `zeffi_*` (datos crudos de Effi)
- 8 tablas `resumen_ventas_*` (analíticas calculadas)
- `crm_contactos` (488 contactos del CRM)
- `catalogo_articulos` (500 artículos, 176 con `grupo_producto` asignado) — se sincroniza automáticamente vía `sync_hostinger.py`

**Gotcha importante — nombres de columnas en tablas de detalle:**
- `fecha_de_creacion` → solo en **encabezados** (facturas/remisiones/cotizaciones)
- `fecha_creacion_factura` → en **zeffi_facturas_venta_detalle** (NO `fecha_de_creacion`)
- `fecha_creacion` → en **zeffi_remisiones_venta_detalle** (otro nombre distinto)
- `descripcion_articulo` → nombre del producto en detalle (NO existe `nombre_articulo`)
- NO existe columna `id_item` en `zeffi_facturas_venta_detalle`

### Endpoints activos en server.js

**Resumen analítico (tablas Hostinger `resumen_ventas_*`)**
| Endpoint | Tabla | Parámetros |
|---|---|---|
| `GET /api/ventas/resumen-mes` | `resumen_ventas_facturas_mes` | `?mes=YYYY-MM&filters=[]` |
| `GET /api/ventas/resumen-canal` | `resumen_ventas_facturas_canal_mes` | `?mes=YYYY-MM&filters=[]` |
| `GET /api/ventas/resumen-cliente` | `resumen_ventas_facturas_cliente_mes` | `?mes=YYYY-MM&filters=[]` |
| `GET /api/ventas/resumen-producto` | `resumen_ventas_facturas_producto_mes` | `?mes=YYYY-MM&filters=[]` |

**Encabezados Effi (con filtro mes y filters genérico)**
| Endpoint | Tabla |
|---|---|
| `GET /api/ventas/facturas` | `zeffi_facturas_venta_encabezados` |
| `GET /api/ventas/remisiones` | `zeffi_remisiones_venta_encabezados` |
| `GET /api/ventas/cotizaciones` | `zeffi_cotizaciones_ventas_encabezados` |

**Resumen por producto y grupo (con filtro fechas)**
| Endpoint | Descripción | Parámetros |
|---|---|---|
| `GET /api/ventas/resumen-por-producto` | Totales históricos por artículo con costo, utilidad, margen, NC | `?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` |
| `GET /api/ventas/resumen-por-grupo` | Totales históricos agrupados por `grupo_producto` (catalogo_articulos) | `?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` |
| `GET /api/ventas/facturas-producto/:cod_articulo` | Lista de facturas donde aparece ese artículo | path param |
| `GET /api/ventas/facturas-grupo/:grupo` | Lista de facturas con artículos de ese grupo | path param |
| `GET /api/ventas/anios-facturas` | Array de años distintos en `zeffi_facturas_venta_detalle` | — |

**Ad-hoc de drill-down (usados en páginas de detalle)**
| Endpoint | Descripción | Parámetros |
|---|---|---|
| `GET /api/ventas/cliente-productos` | Productos comprados por un cliente en un mes | `?mes&id_cliente` |
| `GET /api/ventas/canal-clientes` | Clientes de un canal en un mes | `?mes&canal` |
| `GET /api/ventas/canal-productos` | Productos de un canal en un mes | `?mes&canal` |
| `GET /api/ventas/canal-facturas` | Encabezados de facturas del canal | `?mes&canal` |
| `GET /api/ventas/canal-remisiones` | Encabezados de remisiones del canal | `?mes&canal` |
| `GET /api/ventas/producto-canales` | Canales donde se vendió el producto | `?mes&cod_articulo` |
| `GET /api/ventas/producto-clientes` | Clientes que compraron el producto | `?mes&cod_articulo` |
| `GET /api/ventas/producto-facturas` | Facturas donde aparece el producto | `?mes&cod_articulo` |
| `GET /api/ventas/factura/:id_interno/:id_numeracion` | Encabezado + ítems de una factura específica | path params |

**Utilidad**
| Endpoint | Descripción |
|---|---|
| `GET /api/columnas/:tabla` | Lista columnas de cualquier tabla Hostinger |
| `GET /api/export/:recurso` | Export CSV/XLSX/PDF (`?format=csv\|xlsx\|pdf`) |
| `GET /api/health` | Health check |

Para agregar un endpoint nuevo:
1. Agregar la ruta en `server.js`
2. Reiniciar: `sudo systemctl restart os-erp-frontend`
3. **NO requiere rebuild Quasar** — el rebuild solo es necesario cuando cambian archivos `.vue`

---

## 3. COMPONENTE `OsDataTable.vue`

Componente reutilizable para tablas. Ubicación: `frontend/app/src/components/OsDataTable.vue`

### Props
| Prop | Tipo | Descripción |
|---|---|---|
| `title` | String | Título en toolbar |
| `rows` | Array | Datos |
| `columns` | Array | Definición de columnas `{key, label, visible}` |
| `loading` | Boolean | Activa skeleton rows |
| `recurso` | String | Slug para export (ej: `'resumen-mes'`) |
| `mes` | String | Mes activo para export filtrado (`'2026-02'`) |
| `tooltips` | Object | Diccionario `{key: 'descripción'}` para atributo `title` en headers. **Opcional** — si no se pasa, el componente carga `/api/tooltips` automáticamente con caché global. |

### Tooltips automáticos (desde 2026-03-13)
OsDataTable carga `/api/tooltips` automáticamente al montarse — caché global entre instancias. **No se necesita pasar el prop `tooltips` en ninguna página.** Aparecen como tooltip nativo (atributo HTML `title`) al hacer hover sobre el header de columna. Para agregar o editar tooltips: modificar `COLUMN_TOOLTIPS` en `frontend/api/server.js`.

### Eventos
| Evento | Payload |
|---|---|
| `row-click` | objeto fila completa |

### Formato columnas
```js
const cols = [
  { key: 'mes',        label: 'Mes',        visible: true },
  { key: 'fin_ventas', label: 'Ventas',      visible: true },
  { key: 'canal',      label: 'Canal',       visible: false },
]
```

### Selección de filas — cómo funciona
`isSelected` identifica la fila seleccionada según su PK:
- Si la fila tiene `_pk` → compara por `_pk`
- Si la fila tiene `_key` → compara por `_key` (tablas compuestas `mes|col`)
- Si la fila tiene `mes` → compara por `mes` (tabla resumen_mes)

**Importante:** las columnas `_pk` y `_key` se pueden incluir en `columns` con `visible: false` para que `isSelected` funcione sin mostrarlas.

### Formateo automático de celdas
- Keys con `_pct` o `_margen` → porcentaje (`n * 100` + `%`)
- Keys que empiezan con `fin_`, `cto_`, `car_` o contienen `ventas/ticket/costo/utilidad` → moneda COP (`$1.234.567`)

---

## 4. PATRÓN DE PÁGINA

Estructura estándar de una página de datos:

```vue
<template>
  <div class="page-wrap">
    <!-- Header con breadcrumb + título -->
    <div class="page-header">...</div>

    <!-- Contenido -->
    <div class="page-content">
      <!-- Tabla principal -->
      <OsDataTable ... @row-click="onRowClick" />

      <!-- Acordeones con drill-down -->
      <div class="acordeones">
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('seccion')">...</button>
          <div v-if="abiertos.seccion" class="acordeon-body">
            <OsDataTable ... />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

**Patrón de carga con drill-down por mes:**
```js
const mesSel = ref(null)

function onMesClick(row) {
  mesSel.value = mesSel.value === row.mes ? null : row.mes
}

watch(mesSel, async (mes) => {
  if (!mes) { resDetalle.value = []; return }
  loadingDetalle.value = true
  const url = mes ? `/api/ventas/resumen-detalle?mes=${mes}` : '/api/ventas/resumen-detalle'
  resDetalle.value = await fetch(url).then(r => r.json())
  loadingDetalle.value = false
})
```

---

## 5. MENÚ Y RUTAS

El menú se genera dinámicamente desde la tabla `sys_menu` en Hostinger (36 registros, 7 módulos + 29 submenús).

Las rutas Vue están en `frontend/app/src/router/routes.js`.

Patrón de ruta:
```js
{
  path: '/ventas/resumen-facturacion',
  component: () => import('pages/ventas/ResumenFacturacionPage.vue')
}
```

El layout principal (`MainLayout.vue`) incluye el sidebar izquierdo con el menú.

---

## 6. DEPLOY

Cualquier cambio en el frontend Vue requiere **rebuild**:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app
npx quasar build
# No es necesario reiniciar el servicio — Express sirve el dist directamente
```

Cambios en la API (`server.js` o `db.js`) requieren reiniciar el servicio:
```bash
systemctl restart os-erp-frontend
```

Para verificar estado:
```bash
systemctl status os-erp-frontend
curl http://localhost:9100/api/health
```

---

## 7. CSS Y DISEÑO

Variables CSS globales en `frontend/app/src/css/app.scss`.
**Siempre leer `frontend/design-system/MANUAL_ESTILOS.md` antes de crear cualquier elemento visual.**

Clases utilitarias clave:
- `.page-wrap` → contenedor de página
- `.page-header` / `.page-content` → estructura de página
- `.acordeon` / `.acordeon-header` / `.acordeon-body` → secciones plegables
- `.data-row.selected` → fila seleccionada en tabla

---

## 8. PÁGINAS EXISTENTES Y NAVEGACIÓN DRILL-DOWN

### Módulo Ventas — Jerarquía completa

```
ResumenFacturacionPage  →  /ventas/resumen-facturacion
  ├─ tab Por mes: click fila mes   →  DetalleFacturacionMesPage  /ventas/detalle-mes/:mes
  │    ├─ click canal    →  DetalleCanalMesPage    /ventas/detalle-canal/:mes/:canal
  │    ├─ click cliente  →  DetalleClienteMesPage  /ventas/detalle-cliente/:mes/:id_cliente
  │    ├─ click producto →  DetalleProductoMesPage /ventas/detalle-producto/:mes/:cod_articulo
  │    └─ click factura  →  DetalleFacturaPage     /ventas/detalle-factura/:id_interno/:id_numeracion
  ├─ tab Por producto: click artículo → DetalleFacturasProductoPage /ventas/facturas-producto/:cod_articulo
  │    └─ click factura  →  DetalleFacturaPage
  └─ tab Por grupo: click grupo → DetalleFacturasProductoPage /ventas/facturas-grupo/:grupo
       └─ click factura  →  DetalleFacturaPage
```

| Página | Ruta URL | Archivo |
|---|---|---|
| Resumen Facturación (3 tabs) | `/ventas/resumen-facturacion` | `pages/ventas/ResumenFacturacionPage.vue` |
| Detalle Mes | `/ventas/detalle-mes/:mes` | `pages/ventas/DetalleFacturacionMesPage.vue` |
| Detalle Canal | `/ventas/detalle-canal/:mes/:canal` | `pages/ventas/DetalleCanalMesPage.vue` |
| Detalle Cliente | `/ventas/detalle-cliente/:mes/:id_cliente` | `pages/ventas/DetalleClienteMesPage.vue` |
| Detalle Producto (por mes) | `/ventas/detalle-producto/:mes/:cod_articulo` | `pages/ventas/DetalleProductoMesPage.vue` |
| Detalle Factura ⭐ | `/ventas/detalle-factura/:id_interno/:id_numeracion` | `pages/ventas/DetalleFacturaPage.vue` |
| Facturas de un producto | `/ventas/facturas-producto/:cod_articulo` | `pages/ventas/DetalleFacturasProductoPage.vue` |
| Facturas de un grupo | `/ventas/facturas-grupo/:grupo` | `pages/ventas/DetalleFacturasProductoPage.vue` |

### Patrón de navegación drill-down con contexto

Cuando se navega a `DetalleFacturaPage` desde cualquier página, se pasan query params para que el breadcrumb muestre el árbol completo:

```javascript
// Desde DetalleClienteMesPage:
router.push({
  path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`,
  query: { mes, desde: 'cliente', desde_id: id_cliente, desde_label: kpi?.cliente || id_cliente }
})

// Desde DetalleCanalMesPage:
router.push({
  path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`,
  query: { mes, desde: 'canal', desde_id: canal, desde_label: canal }
})

// Desde DetalleProductoMesPage:
router.push({
  path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`,
  query: { mes, desde: 'producto', desde_id: cod_articulo, desde_label: kpi?.nombre || cod_articulo }
})

// Desde DetalleFacturacionMesPage (nivel mes directo):
router.push({
  path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`,
  query: { mes, desde: 'mes' }
})
```

El resultado visual en el breadcrumb:
`Ventas > Resumen Facturación > Enero 2025 > MANDALAIRE > Factura #FEV-606`

### Label especial: id_numeracion → "No Fac"

En todas las páginas, `labelFromKey('id_numeracion')` debe retornar `'No Fac'`. Agregar siempre esta excepción al inicio de `labelFromKey`:

```javascript
function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'
  if (key === 'descripcion_articulo') return 'Producto'
  // ... resto de transformaciones
}
```
