# Skill: ERP Frontend — Origen Silvestre

> Stack completo del ERP web: Vue 3 + Quasar + API Express + MySQL Hostinger.
> URL pública: **erp.oscomunidad.com** — Cloudflare Tunnel → localhost:9100
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

**Gotcha importante:** `fecha_de_creacion` en `zeffi_facturas_venta_encabezados` es TEXT (`'YYYY-MM-DD HH:MM:SS'`). Para filtrar por mes usar `LEFT(fecha_de_creacion, 7)`.

### Endpoints actuales
| Endpoint | Tabla | Filtro mes |
|---|---|---|
| `GET /api/ventas/resumen-mes` | `resumen_ventas_facturas_mes` | campo `mes` |
| `GET /api/ventas/resumen-canal` | `resumen_ventas_facturas_canal_mes` | `?mes=YYYY-MM` |
| `GET /api/ventas/resumen-cliente` | `resumen_ventas_facturas_cliente_mes` | `?mes=YYYY-MM` |
| `GET /api/ventas/resumen-producto` | `resumen_ventas_facturas_producto_mes` | `?mes=YYYY-MM` |
| `GET /api/ventas/facturas` | `zeffi_facturas_venta_encabezados` | `?mes=YYYY-MM` |
| `GET /api/columnas/:tabla` | SHOW COLUMNS | — |
| `GET /api/export/:recurso` | cualquier tabla del MAP | `?format=csv\|xlsx\|pdf` |
| `GET /api/health` | — | — |

Para agregar un endpoint nuevo:
1. Agregar la ruta en `server.js`
2. Agregar el recurso al MAP de exports si se necesita exportar
3. Reiniciar: `systemctl restart os-erp-frontend`

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

## 8. PÁGINAS EXISTENTES

| Página | Ruta URL | Archivo |
|---|---|---|
| Resumen Facturación | `/ventas/resumen-facturacion` | `pages/ventas/ResumenFacturacionPage.vue` |
