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
| `row-click` | objeto fila | Clic simple en fila | Navegar a vista de detalle (drill-down) |

> **IMPORTANTE**: Ya NO existe `row-dblclick`. Toda navegación es con click simple.

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

---

## 2. FORMATO NUMÉRICO ESTÁNDAR

**Regla global**: todos los campos numéricos/decimales del ERP usan:
- **Separador de miles**: `.` (punto)
- **Separador decimales**: `,` (coma)
- **Decimales automáticos**: 0 si es entero, hasta 3 máximo

### Función `fmtNum()` (implementada en OsDataTable)

```javascript
function fmtNum(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  let decimals = 0
  const abs = Math.abs(n)
  const remainder = abs - Math.floor(abs)
  if (remainder > 0.0005) {
    const s = n.toFixed(3)
    const trimmed = s.replace(/0+$/, '').replace(/\.$/, '')
    const parts = trimmed.split('.')
    decimals = parts[1] ? parts[1].length : 0
    if (decimals > 3) decimals = 3
  }
  return n.toLocaleString('de-DE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}
```

> Usa locale `de-DE` porque produce `.` para miles y `,` para decimales (mismo estándar colombiano de OS).

### Formateo automático de celdas en OsDataTable

| Patrón de key | Formato |
|---|---|
| `*_pct*` o `*_margen*` | `(n * 100).toFixed(1) + '%'` — valores en BD son 0–1 |
| `fin_*`, `cto_*`, `car_*`, `*ventas*`, `*ticket*`, `*costo*`, `*utilidad*` | `$` + `fmtNum(n)` |
| Otros numéricos | `fmtNum(n)` |
| `null` o `undefined` | `'—'` |

### Formatters para KPIs (en páginas de detalle)

```javascript
function fmt$(v)   { const n = parseFloat(v); return isNaN(n) ? '—' : '$' + fmtNum(n) }
function fmtPct(v) { const n = parseFloat(v); return isNaN(n) ? '—' : (n * 100).toFixed(1) + '%' }
function fmtNum(v) {
  const n = parseFloat(v); if (isNaN(n)) return '—'
  let decimals = 0
  const remainder = Math.abs(n) - Math.floor(Math.abs(n))
  if (remainder > 0.0005) {
    const s = n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '').split('.')
    decimals = Math.min(s[1]?.length || 0, 3)
  }
  return n.toLocaleString('de-DE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
```

---

## 3. MINI-POPUP POR COLUMNA (filtros + sort + subtotales)

### Comportamiento

- **Click en header de columna** → abre mini-popup anclado debajo del `<th>`
- Solo **un popup abierto** a la vez (click en otra columna cierra el anterior)
- Se renderiza con `<Teleport to="body">` para evitar problemas de z-index/overflow
- Overlay transparente cierra el popup al hacer click fuera

### Contenido del popup

1. **Filtro con operador** — select de operador + input(s) de valor:
   - `eq` — Igual a (por defecto)
   - `contains` — Contiene
   - `gt` — Mayor que
   - `lt` — Menor que
   - `gte` — Mayor o igual
   - `lte` — Menor o igual
   - `between` — Entre (muestra 2 inputs: Desde / Hasta)

2. **Ordenamiento** — dos botones toggle: Ascendente ↑ / Descendente ↓

3. **Subtotal** (solo columnas numéricas) — 4 opciones toggle:
   - Σ Suma
   - x̄ Promedio
   - ↑ Máximo
   - ↓ Mínimo

### Estado interno

```javascript
const columnFilters    = ref({})  // { [key]: { op: 'eq', val: '', val2: '' } }
const columnAggregates = ref({})  // { [key]: 'sum'|'avg'|'max'|'min'|null }
const colPopup         = ref(null)  // key de columna activa o null
const colPopupStyle    = ref({})    // { top, left } calculado desde getBoundingClientRect()
```

### Detección de columnas numéricas

```javascript
function isNumeric(key) {
  const prefijos = ['fin_','cto_','vol_','car_','cli_','pry_','ant_','con_','cat_']
  if (prefijos.some(p => key.startsWith(p))) return true
  if (key.match(/_pct|_margen|_total|_neto|_bruto|_iva|_promedio|_dias/)) return true
  // + muestreo de primeras 5 filas de datos
  const sample = rows.slice(0, 5)
  return sample.length > 0 && sample.every(r => r[key] === null || r[key] === undefined || typeof r[key] === 'number' || !isNaN(parseFloat(r[key])))
}
```

### Fila de subtotales

- Se renderiza **al inicio de la tabla** (primera fila después del `<thead>`) si hay al menos 1 columna con aggregate activo
- Es **sticky**: `position: sticky; top: 36px; z-index: 4` — queda pegada justo debajo del header al hacer scroll
- Cada celda muestra el valor agregado formateado con `fmtNum()`
- Label pequeño encima del valor: "Σ", "x̄", "↑", "↓" según tipo
- CSS clave: `border-bottom: 2px solid rgba(16,185,129,0.25); background: rgba(16,185,129,0.06)`

### CSS del popup (NO scoped — va en `<style>` sin scoped porque usa Teleport)

```css
.col-popup-overlay {
  position: fixed; inset: 0; z-index: 9999; background: transparent;
}
.col-popup {
  position: fixed; z-index: 10000;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  padding: 10px 12px; min-width: 200px;
  display: flex; flex-direction: column; gap: 8px;
  font-size: 12px; color: var(--text-primary);
}
```

---

## 4. ESTRUCTURA DE UNA VISTA CON TABLAS

### Layout obligatorio

```vue
<template>
  <div class="page-wrap">

    <!-- HEADER fijo: breadcrumb + título -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Módulo</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Nombre Vista</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Nombre Vista</h1>
        </div>
      </div>
    </div>

    <!-- CONTENT: sin overflow-y propio, deja que main-area scrollee -->
    <div class="page-content">
      <OsDataTable
        ...
        @row-click="onRowClick"
      />
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
```

---

## 5. PATRÓN: NAVEGACIÓN POR CLICK (drill-down directo)

```javascript
import { useRouter } from 'vue-router'
const router = useRouter()

// Click simple: navega directamente a vista de detalle
function onRowClick(row) {
  router.push(`/modulo/detalle/${row.campo_id}`)
}
```

> **Estándar**: click simple = navegar. No hay doble click en ninguna tabla del ERP.

---

## 6. PATRÓN: VISTA DE DETALLE CON KPI CARDS

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

---

## 7. AGRUPACIÓN DE CAMPOS POR PREFIJO (tabla `resumen_ventas_facturas_mes`)

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

## 8. ACORDEONES (patrón para vistas con sub-tablas)

### Estructura

```vue
<div class="acordeones">
  <div class="acordeon">
    <button class="acordeon-header" @click="toggleAcordeon('detalle')">
      <div class="ac-left">
        <ChevronRightIcon :size="14" class="ac-chevron" :class="{open: abiertos.detalle}" />
        <span class="ac-title">Título acordeón</span>
      </div>
      <span class="ac-count">{{ datos.length }} registros</span>
    </button>
    <div v-if="abiertos.detalle" class="acordeon-body">
      <OsDataTable ... @row-click="onRowClick" />
    </div>
  </div>
</div>
```

### CSS

```css
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
.ac-count    { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
```

### Carga lazy

```javascript
const abiertos = ref({ canal: false, facturas: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return    // solo cargar al abrir

  const loaders = {
    canal:    () => load(`/api/ventas/resumen-canal`,  resCanal,    loadingCanal),
    facturas: () => load(`/api/ventas/facturas`,       resFacturas, loadingFacturas),
  }
  if (loaders[key]) loaders[key]()
}
```

---

## 9. ENDPOINTS DE LA API

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

## 10. ERRORES FRECUENTES — NO REPETIR

| Error | Causa | Solución |
|---|---|---|
| Popup de columna se esconde | Popup dentro de `<th>` con overflow | Usar `<Teleport to="body">` con z-index 10000 + overlay |
| Popups de toolbar no aparecen | Botones sin `@click.stop` | Siempre usar `@click.stop` en botones de toolbar |
| Tabla principal se oculta al abrir acordeón | `.page-content` con `height` fija + `overflow-y: auto` | Usar `min-height` y quitar `overflow-y` de `.page-content` |
| Scroll no funciona | Scroll en `.page-content` | El único scroll es en `MainLayout.vue > .main-area` |
| Exportar abre misma pestaña | `window.location = url` | Usar `window.open(url, '_blank')` |
| Cambios no se ven | Falta rebuild Quasar | `cd frontend/app && npx quasar build` |
| Acordeón de productos retorna 0 | `d.nombre_articulo` en SQL | Usar `d.descripcion_articulo` |
| Detalle factura 0 resultados | `d.fecha_de_creacion` | Detalle usa `d.fecha_creacion_factura` |
| Error en ORDER BY detalle | `ORDER BY id_item` | NO existe en `zeffi_facturas_venta_detalle` — omitir |

---

## 11. PÁGINAS EXISTENTES

### Módulo Ventas — árbol drill-down completo

```
ResumenFacturacionPage       /ventas/resumen-facturacion
  └─ click mes → DetalleFacturacionMesPage  /ventas/detalle-mes/:mes
       ├─ click canal    → DetalleCanalMesPage    /ventas/detalle-canal/:mes/:canal
       ├─ click cliente  → DetalleClienteMesPage  /ventas/detalle-cliente/:mes/:id_cliente
       ├─ click producto → DetalleProductoMesPage /ventas/detalle-producto/:mes/:cod_articulo
       └─ click factura  → DetalleFacturaPage     /ventas/detalle-factura/:id_interno/:id_numeracion
```

> **Estándar**: toda navegación drill-down es con click simple (no doble click).

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

### Breadcrumb contextual (páginas de detalle)

```javascript
const qMes        = route.query.mes         || ''
const qDesde      = route.query.desde       || ''
const qDesdeId    = route.query.desde_id    || ''
const qDesdeLabel = route.query.desde_label || ''
```
