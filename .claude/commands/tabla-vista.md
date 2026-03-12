# Skill: Diseño de Vista de Tablas — ERP Origen Silvestre

> Guía completa para construir cualquier vista con tablas en el ERP.
> Referencia visual: Linear.app Projects view (modo claro).
> Stack: Vue 3 + Quasar + componente `OsDataTable.vue`.

---

## ⚠️ BUILD OBLIGATORIO

Después de cualquier cambio en `.vue`, `.js` del frontend, ejecutar:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/frontend/app && npx quasar build
```
El servidor sirve `dist/spa/`. Sin rebuild, los cambios NO aparecen.

---

## 1. COMPONENTE REUTILIZABLE: `OsDataTable.vue`

Ubicación: `frontend/app/src/components/OsDataTable.vue`

### Props

| Prop | Tipo | Descripción |
|---|---|---|
| `title` | String | Título que aparece en la toolbar izquierda |
| `rows` | Array | Array de objetos con los datos |
| `columns` | Array | Definición de columnas `{key, label, visible}` |
| `loading` | Boolean | Muestra skeleton rows cuando es true |
| `recurso` | String | Slug para el endpoint de export (ej: `'resumen-mes'`) |
| `mes` | String | Mes seleccionado para export filtrado (`'2026-02'`) |

### Eventos

| Evento | Payload | Cuándo | Uso típico |
|---|---|---|---|
| `row-click` | objeto fila | Clic simple | Seleccionar fila, filtrar acordeones |
| `row-dblclick` | objeto fila | Doble clic | Navegar a vista de detalle |

### Formato de columnas

```javascript
const columnas = ref([
  { key: 'mes',                  label: 'Mes',           visible: true  },
  { key: 'fin_ventas_netas',     label: 'Ventas Netas',  visible: true  },
  { key: 'fin_ventas_brutas',    label: 'Ventas Brutas', visible: false }, // oculta por defecto
])
```

Las columnas se cargan dinámicamente desde la API:
```javascript
const { data: cols } = await axios.get(`/api/columnas/nombre_tabla`)
columnas.value = cols.map(key => ({
  key,
  label: labelFromKey(key),
  visible: DEFAULT_VISIBLE.includes(key)
}))
```

### Selección de filas — cómo funciona `isSelected`
- Si la fila seleccionada tiene `_pk` → compara por `_pk`
- Si tiene `_key` → compara por `_key` (tablas compuestas `mes|col`)
- Si tiene `mes` → compara por `mes`

**Importante**: si se quieren usar `_pk` o `_key` como identificadores sin mostrarlos, incluirlos en `columns` con `visible: false`.

### Formateo automático de celdas
| Patrón de key | Formato |
|---|---|
| `*_pct*` o `*_margen*` | `(n * 100).toFixed(1) + '%'` — valores en BD son 0–1 |
| `fin_*`, `cto_*`, `car_*`, `*ventas*`, `*ticket*`, `*costo*`, `*utilidad*` | `$` + `toLocaleString('es-CO', {maximumFractionDigits: 0})` |
| `null` o `undefined` | `'—'` |

### Popups (Filtrar / Campos / Exportar)
**Bug crítico evitado**: los botones del toolbar usan `@click.stop` para evitar que el click burbujee al `document` y el `handleOutsideClick` cierre el popup de inmediato.

Los popups siguen el estilo Linear.app:
- **Filtrar**: filas [campo ▾] [op ▾] [valor] [×] + footer "Añadir filtro / Limpiar todo"
- **Campos**: pills clicables (violeta = visible, gris = oculto) + "Mostrar todos / Ocultar todos"
- **Exportar**: 3 filas limpias con ícono + label + descripción corta

---

## 2. ESTRUCTURA DE UNA VISTA CON TABLAS

### Layout obligatorio

```vue
<template>
  <div class="page-wrap">

    <!-- HEADER fijo: breadcrumb + título + badges de filtros activos -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Módulo</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Nombre Vista</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Nombre Vista</h1>
          <div v-if="seleccion" class="sel-badge">
            <span>{{ seleccion }}</span>
            <button @click="seleccion = null"><XIcon :size="11" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTENT: sin overflow-y propio, deja que main-area scrollee -->
    <div class="page-content">
      <OsDataTable
        ...
        @row-click="onRowClick"
        @row-dblclick="onRowDblclick"
      />

      <div class="acordeones">
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('detalle')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{open: abiertos.detalle}" />
              <span class="ac-title">Título acordeón</span>
              <span v-if="seleccion" class="ac-mes-tag">{{ seleccion }}</span>
            </div>
            <span class="ac-count">{{ datos.length }} registros</span>
          </button>
          <div v-if="abiertos.detalle" class="acordeon-body">
            <OsDataTable ... />
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
```

### CSS obligatorio para toda vista

```css
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
/* CRÍTICO: SIN overflow-y ni height — el scroll lo maneja main-area del layout */
.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }

.page-header       { border-bottom: 1px solid var(--border-subtle); background: var(--bg-app); padding: 0 24px; flex-shrink: 0; }
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb        { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px; }
.bc-current        { color: var(--text-secondary); }
.page-title-row    { display: flex; align-items: center; gap: 12px; }
.page-title        { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

/* Badge de selección activa */
.sel-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px 3px 7px; border-radius: var(--radius-full);
  background: var(--accent-muted); border: 1px solid var(--accent-border);
  font-size: 12px; font-weight: 500; color: var(--accent);
}

/* Acordeones */
.acordeones       { display: flex; flex-direction: column; gap: 8px; }
.acordeon         { border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-card); }
.acordeon-header  {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 0 14px; height: 42px;
  border: none; background: transparent; cursor: pointer;
  transition: background 80ms; font-family: var(--font-sans);
}
.acordeon-header:hover { background: var(--bg-card-hover); }
.ac-left     { display: flex; align-items: center; gap: 8px; }
.ac-chevron  { color: var(--text-tertiary); transition: transform 150ms ease-out; }
.ac-chevron.open { transform: rotate(90deg); }
.ac-title    { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ac-mes-tag  { font-size: 11px; font-weight: 500; color: var(--accent); background: var(--accent-muted); border: 1px solid var(--accent-border); padding: 1px 7px; border-radius: var(--radius-full); }
.ac-count    { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
```

---

## 3. PATRÓN: DRILL-DOWN POR FILA (click) + NAVEGACIÓN (doble click)

```javascript
import { useRouter } from 'vue-router'
const router = useRouter()

const seleccion = ref(null)

// Click simple: selecciona/deselecciona → filtra acordeones
function onRowClick(row) {
  seleccion.value = row.campo_id === seleccion.value ? null : row.campo_id
}

// Doble click: navega a vista de detalle
function onRowDblclick(row) {
  router.push(`/modulo/detalle/${row.campo_id}`)
}

// Watcher: recarga acordeones abiertos cuando cambia la selección
watch(seleccion, () => {
  if (abiertos.value.detalle) loadDetalle()
})
```

---

## 4. PATRÓN: VISTA DE DETALLE CON KPI CARDS

Para vistas de detalle de un ítem (ej: detalle de un mes), usar tarjetas KPI agrupadas por tema.

### Estructura de grupos KPI

```vue
<div class="kpi-section">
  <div class="kpi-section-label">Financiero</div>
  <div class="kpi-grid">
    <div class="kpi-card">
      <span class="kpi-label">Ventas Netas s/IVA</span>
      <span class="kpi-value">{{ fmt$(kpi.fin_ventas_netas_sin_iva) }}</span>
    </div>
    <!-- más cards... -->
  </div>
</div>
```

### CSS para KPI Cards

```css
.kpi-section       { display: flex; flex-direction: column; gap: 8px; }
.kpi-section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
}
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 4px;
}
.kpi-label  { font-size: 11px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value  { font-size: 20px; font-weight: 600; color: var(--text-primary); line-height: 1.2; }
.kpi-pos    { color: var(--color-success); }
.kpi-neg    { color: var(--color-error); }
.kpi-warn   { color: var(--color-warning); }
```

### Formatters estándar para KPIs

```javascript
function fmt$(v)   { const n = parseFloat(v); return isNaN(n) ? '—' : '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 }) }
function fmtPct(v) { const n = parseFloat(v); return isNaN(n) ? '—' : (n * 100).toFixed(1) + '%' }
function fmtNum(v) { const n = parseFloat(v); return isNaN(n) ? '—' : n.toLocaleString('es-CO', { maximumFractionDigits: 0 }) }
```

---

## 5. AGRUPACIÓN DE CAMPOS POR PREFIJO (tabla `resumen_ventas_facturas_mes`)

| Prefijo | Grupo | Descripción |
|---|---|---|
| `fin_*` | Financiero | Ventas brutas, netas, devoluciones, ingresos |
| `vol_*` | Volumen | Num facturas, ticket, unidades |
| `cli_*` | Clientes | Activos, nuevos, venta por cliente |
| `cto_*` | Costo/Margen | Utilidad, margen, costo total |
| `car_*` | Cartera | Saldo CxC |
| `pry_*` | Proyección | Proyección mes, ritmo (solo mes corriente) |
| `ant_*` | Año anterior | Ventas ant., variación, consignación ant. |
| `top_*` | Top del mes | Canal, cliente, producto top |
| `cat_*` | Catálogo | Num canales, referencias, venta/referencia |
| `con_*` | Consignación | Consignación PP |

Los valores `_pct` van de 0 a 1 → multiplicar por 100 para mostrar.

---

## 6. CARGA LAZY DE ACORDEONES (patrón óptimo)

```javascript
const abiertos = ref({ canal: false, facturas: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return    // solo cargar al abrir, nunca al cerrar

  const loaders = {
    canal:    () => load(`/api/ventas/resumen-canal`,  resCanal,    loadingCanal),
    facturas: () => load(`/api/ventas/facturas`,       resFacturas, loadingFacturas),
  }
  if (loaders[key]) loaders[key]()
}

async function load(url, dataRef, loadingRef) {
  if (loadingRef.value) return        // evitar doble carga
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes: mesActivo } })
    dataRef.value = data
  } finally { loadingRef.value = false }
}
```

---

## 7. ENDPOINTS DE LA API

Ver skill `/erp-frontend` para la lista completa de endpoints.
Endpoints de tablas de encabezado con filtro `?mes=YYYY-MM`:

| Endpoint | Tabla |
|---|---|
| `GET /api/ventas/resumen-mes` | `resumen_ventas_facturas_mes` |
| `GET /api/ventas/resumen-canal` | `resumen_ventas_facturas_canal_mes` |
| `GET /api/ventas/resumen-cliente` | `resumen_ventas_facturas_cliente_mes` |
| `GET /api/ventas/resumen-producto` | `resumen_ventas_facturas_producto_mes` |
| `GET /api/ventas/facturas` | `zeffi_facturas_venta_encabezados` |
| `GET /api/ventas/cotizaciones` | `zeffi_cotizaciones_ventas_encabezados` |
| `GET /api/ventas/remisiones` | `zeffi_remisiones_venta_encabezados` |

Todas usan `LEFT(fecha_de_creacion, 7) = ?mes` para filtrar (campo es TEXT `'YYYY-MM-DD HH:MM:SS'`).

---

## 8. ERRORES FRECUENTES — NO REPETIR

| Error | Causa | Solución |
|---|---|---|
| Popups no aparecen | Botones del toolbar sin `@click.stop` | Siempre usar `@click.stop` en los 3 botones de toolbar |
| Tabla principal se oculta al abrir acordeón | `.page-content` con `height` fija + `overflow-y: auto` | Usar `min-height` y quitar `overflow-y` de `.page-content` |
| Scroll no funciona | Scroll en `.page-content` | El único scroll es en `MainLayout.vue > .main-area` |
| Toda la tabla se selecciona | `isSelected` compara `undefined === undefined` | Ver el patrón actual en OsDataTable — siempre comparar con PK del item seleccionado |
| Exportar abre misma pestaña | `window.location = url` | Usar `window.open(url, '_blank')` |
| Cambios no se ven | Falta rebuild Quasar | `cd frontend/app && npx quasar build` |
| Acordeón de productos retorna 0 resultados | `d.nombre_articulo` en SQL → columna no existe | Usar `d.descripcion_articulo` (es el nombre real del producto en Hostinger) |
| Acordeón de facturas retorna 0 resultados | `d.fecha_de_creacion` en detalle → columna no existe | Detalle usa `d.fecha_creacion_factura`. Encabezados sí usan `e.fecha_de_creacion` |
| Error en ORDER BY o SELECT de detalle factura | `ORDER BY id_item` → columna no existe | NO existe `id_item` en `zeffi_facturas_venta_detalle` — omitir ORDER BY o usar otro campo |

---

## 9. PATRÓN COMPLETO: VISTA DE DETALLE CON KPIs + ACORDEONES

Para páginas de 3er nivel (ej: DetalleCanalMesPage, DetalleClienteMesPage, DetalleProductoMesPage):

### Estructura del script setup

```javascript
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const route  = useRoute()
const router = useRouter()
const API    = '/api'
const mes    = route.params.mes
// Decodificar parámetros que pueden tener espacios o caracteres especiales:
const canal  = decodeURIComponent(route.params.canal)

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
function nombreMes(m) {
  if (!m) return m
  const [y, mo] = m.split('-')
  return `${MESES[parseInt(mo) - 1]} ${y}`
}

// KPI del resumen analítico
const kpi        = ref(null)
const loadingKpi = ref(true)

async function loadKpi() {
  loadingKpi.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-canal`, {
      params: { mes, filters: JSON.stringify([{ field: 'canal', op: 'eq', value: canal }]) }
    })
    kpi.value = data[0] || null
  } finally { loadingKpi.value = false }
}

// Tablas de acordeón (cada una con su ref de datos y loading)
const resFacturas  = ref([]); const loadingFacturas  = ref(false)
const colsFacturas = ref([])

// Columnas visibles por defecto para cada tipo de tabla
const VISIBLE = {
  'zeffi_facturas_venta_encabezados': ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc','dias_mora'],
}

function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'           // ← SIEMPRE incluir
  if (key === 'descripcion_articulo') return 'Producto'  // ← si se usan productos
  return key.replace(/^_pk$/, 'N°').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '').replace(/^Vol /, '').replace(/^Cli /, '').replace(/^Cto /, '').trim()
}

function colsFromData(data, tabla) {
  if (!data.length) return []
  const visible = VISIBLE[tabla] || []
  return Object.keys(data[0]).map(key => ({ key, label: labelFromKey(key), visible: visible.includes(key) }))
}

async function loadColumns(tabla, destRef) {
  const { data: cols } = await axios.get(`${API}/columnas/${tabla}`)
  destRef.value = cols.map(key => ({ key, label: labelFromKey(key), visible: (VISIBLE[tabla] || []).includes(key) }))
}

// Acordeones lazy — solo cargan al abrirse
const abiertos = ref({ facturas: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return
  const loaders = {
    facturas: () => loadAd(`${API}/ventas/canal-facturas`, resFacturas, loadingFacturas, 'zeffi_facturas_venta_encabezados'),
  }
  if (loaders[key]) loaders[key]()
}

async function loadAd(url, dataRef, loadingRef, tabla) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes, canal } })
    dataRef.value = data
    if (!colsFacturas.value.length) colsFacturas.value = colsFromData(data, tabla)
  } finally { loadingRef.value = false }
}

onMounted(async () => {
  await Promise.all([
    loadKpi(),
    loadColumns('zeffi_facturas_venta_encabezados', colsFacturas),
  ])
})
```

### Breadcrumb con árbol contextual

Para DetalleFacturaPage (o cualquier página de 4to nivel), leer query params para construir el árbol:

```javascript
const qMes        = route.query.mes         || ''
const qDesde      = route.query.desde       || ''
const qDesdeId    = route.query.desde_id    || ''
const qDesdeLabel = route.query.desde_label || ''
```

Template del breadcrumb contextual:
```vue
<div class="breadcrumb">
  <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Ventas</span>
  <template v-if="qMes">
    <ChevronRightIcon :size="13" />
    <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Resumen Facturación</span>
    <ChevronRightIcon :size="13" />
    <span class="bc-link" @click="router.push(`/ventas/detalle-mes/${qMes}`)">{{ nombreMes(qMes) }}</span>
    <template v-if="qDesde !== 'mes' && desdeConfig[qDesde]?.path">
      <ChevronRightIcon :size="13" />
      <span class="bc-link" @click="router.push(desdeConfig[qDesde].path)">{{ desdeConfig[qDesde].label }}</span>
    </template>
  </template>
  <ChevronRightIcon :size="13" />
  <span class="bc-current">Título actual</span>
</div>
```

---

## 10. PÁGINAS EXISTENTES

### Módulo Ventas — árbol drill-down completo

```
ResumenFacturacionPage       /ventas/resumen-facturacion
  └─ dblclick mes → DetalleFacturacionMesPage  /ventas/detalle-mes/:mes
       ├─ dblclick canal    → DetalleCanalMesPage    /ventas/detalle-canal/:mes/:canal
       ├─ dblclick cliente  → DetalleClienteMesPage  /ventas/detalle-cliente/:mes/:id_cliente
       ├─ dblclick producto → DetalleProductoMesPage /ventas/detalle-producto/:mes/:cod_articulo
       └─ dblclick factura  → DetalleFacturaPage     /ventas/detalle-factura/:id_interno/:id_numeracion
```

| Página | Ruta | Archivo | Fuente KPI |
|---|---|---|---|
| Resumen Facturación | `/ventas/resumen-facturacion` | `ResumenFacturacionPage.vue` | `resumen_ventas_facturas_mes` |
| Detalle Mes | `/ventas/detalle-mes/:mes` | `DetalleFacturacionMesPage.vue` | `resumen_ventas_facturas_mes` |
| Detalle Canal | `/ventas/detalle-canal/:mes/:canal` | `DetalleCanalMesPage.vue` | `resumen_ventas_facturas_canal_mes` |
| Detalle Cliente | `/ventas/detalle-cliente/:mes/:id_cliente` | `DetalleClienteMesPage.vue` | `resumen_ventas_facturas_cliente_mes` |
| Detalle Producto | `/ventas/detalle-producto/:mes/:cod_articulo` | `DetalleProductoMesPage.vue` | `resumen_ventas_facturas_producto_mes` |
| Detalle Factura | `/ventas/detalle-factura/:id_interno/:id_numeracion` | `DetalleFacturaPage.vue` | `zeffi_facturas_venta_encabezados` + detalle |

### Registrar ruta nueva en routes.js

```javascript
// frontend/app/src/router/routes.js (dentro del children del MainLayout)
{ path: 'ventas/detalle-canal/:mes/:canal', component: () => import('pages/ventas/DetalleCanalMesPage.vue') },
```
