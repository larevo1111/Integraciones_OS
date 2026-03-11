# Skill: Diseño de Vista de Tablas — ERP Origen Silvestre

> Guía completa para construir cualquier vista con tablas en el ERP.
> Referencia visual: Linear.app Projects view (modo claro).
> Stack: Vue 3 + Quasar + componente `OsDataTable.vue`.

---

## 1. COMPONENTE REUTILIZABLE: `OsDataTable.vue`

Ubicación: `frontend/app/src/components/OsDataTable.vue`

### Props

| Prop | Tipo | Descripción |
|---|---|---|
| `title` | String | Título que aparece en la toolbar izquierda |
| `rows` | Array | Array de objetos con los datos |
| `columns` | Array | Definición de columnas (ver formato abajo) |
| `loading` | Boolean | Muestra skeleton rows cuando es true |
| `recurso` | String | Slug para el endpoint de export (ej: `'resumen-mes'`) |
| `mes` | String | Mes seleccionado para drill-down (`'2026-02'`) |

### Eventos

| Evento | Payload | Cuándo |
|---|---|---|
| `row-click` | `row` (objeto) | Al hacer clic en una fila |

### Formato de columnas

```javascript
const columnas = ref([
  { key: 'mes',                  label: 'Mes',           visible: true  },
  { key: 'fin_ventas_netas',     label: 'Ventas Netas',  visible: true  },
  { key: 'fin_ventas_brutas',    label: 'Ventas Brutas', visible: false }, // oculta por defecto
])
```

Las columnas se pueden cargar dinámicamente desde la API:
```javascript
const { data: cols } = await axios.get(`${API}/columnas/nombre_tabla`)
columnas.value = cols.map(key => ({
  key,
  label: labelFromKey(key),   // función helper que convierte snake_case a legible
  visible: DEFAULT_VISIBLE.includes(key)
}))
```

---

## 2. ESTRUCTURA DE UNA VISTA CON TABLAS

### Layout obligatorio

```vue
<template>
  <div class="page-wrap">          <!-- min-height:100%, NO height:100% -->

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
          <!-- Badge de selección activa (ej: mes seleccionado) -->
          <div v-if="seleccion" class="sel-badge">
            <span>{{ seleccion }}</span>
            <button @click="seleccion = null"><XIcon :size="11" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTENT: sin overflow-y propio, deja que main-area scrollee -->
    <div class="page-content">
      <!-- Tabla principal -->
      <OsDataTable ... @row-click="onRowClick" />

      <!-- Acordeones de detalle -->
      <div class="acordeones">
        <div class="acordeon">
          <button class="acordeon-header" @click="toggle('detalle')">
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

### CSS obligatorio para toda vista con tablas

```css
/* CRÍTICO: min-height no height — permite que el contenido crezca */
.page-wrap { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }

/* CRÍTICO: SIN overflow-y ni flex:1 — el scroll lo maneja main-area del layout */
.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }

/* Page header */
.page-header {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-app);
  padding: 0 24px;
  flex-shrink: 0;
}
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px; }
.bc-current { color: var(--text-secondary); }
.page-title-row { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

/* Badge de selección (mes, canal, etc.) */
.sel-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px 3px 7px;
  border-radius: var(--radius-full);
  background: var(--accent-muted); border: 1px solid var(--accent-border);
  font-size: 12px; font-weight: 500; color: var(--accent);
}

/* Acordeones */
.acordeones { display: flex; flex-direction: column; gap: 8px; }
.acordeon { border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-card); }
.acordeon-header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 0 14px; height: 42px;
  border: none; background: transparent; cursor: pointer;
  transition: background 80ms; font-family: var(--font-sans);
}
.acordeon-header:hover { background: var(--bg-card-hover); }
.ac-left { display: flex; align-items: center; gap: 8px; }
.ac-chevron { color: var(--text-tertiary); transition: transform 150ms ease-out; }
.ac-chevron.open { transform: rotate(90deg); }
.ac-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ac-mes-tag { font-size: 11px; font-weight: 500; color: var(--accent); background: var(--accent-muted); border: 1px solid var(--accent-border); padding: 1px 7px; border-radius: var(--radius-full); }
.ac-count { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
```

---

## 3. TOOLBAR DE TABLA (estilo Linear)

La toolbar del `OsDataTable` replica exactamente el estilo de Linear.app:

```
[Título de la tabla]  [N]          [⚡ Filtrar] [≡ Campos] [↓ Exportar]
```

- **Izquierda**: título + badge con conteo de filas
- **Derecha**: 3 botones con borde `1px solid var(--border-default)`
- **Activo (Filtrar con filtros)**: badge púrpura con conteo + borde `var(--accent-border)`

### Botones toolbar

```css
.toolbar-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; transition: background 80ms, color 80ms;
}
.toolbar-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }
.toolbar-btn.active { color: var(--accent); border-color: var(--accent-border); background: var(--accent-muted); }
```

---

## 4. POPUP DE FILTROS

Aparece debajo del botón Filtrar. Permite agregar condiciones:

```
[campo ▾] [operador ▾] [valor___________] [×]
[+ Añadir filtro]                  [Limpiar]
```

**Operadores disponibles**: `contiene`, `igual a`, `mayor o igual`, `menor o igual`
**Posición**: `position: absolute; top: calc(100% + 6px); right: 0; z-index: 200`
**Ancho mínimo**: 420px

---

## 5. POPUP DE CAMPOS

Lista de checkboxes para mostrar/ocultar columnas:

```
[✓] Mes
[✓] Ventas Netas Sin IVA
[ ] Ventas Brutas
[✓] Núm. Facturas
...
[Mostrar todos]  [Ocultar todos]
```

**Ancho mínimo**: 220px

---

## 6. POPUP DE EXPORTAR

```
[📄] CSV — Separado por comas
[📊] Excel — Archivo .xlsx
[📋] PDF — Documento PDF
```

Llama a `GET /api/export/:recurso?format=csv|xlsx|pdf&mes=...&fields=[...]`

---

## 7. FORMATO DE CELDAS (función `formatCell`)

| Patrón de key | Formato |
|---|---|
| `*_pct*` o `*_margen*` | `(n * 100).toFixed(1) + '%'` — los valores en BD son 0–1 |
| `fin_*`, `cto_*`, `car_*`, `*ventas*`, `*ticket*` | `$` + `toLocaleString('es-CO', {maximumFractionDigits: 0})` |
| `null` o `undefined` | `'—'` |
| Resto | valor tal cual |

---

## 8. DRILL-DOWN POR SELECCIÓN DE FILA

Patrón estándar:

```javascript
const seleccion = ref(null)

function onRowClick(row) {
  // Toggle: clic en la misma fila la deselecciona
  seleccion.value = row.campo_id === seleccion.value ? null : row.campo_id
}

// Watcher: cuando cambia la selección, recargar datos de los acordeones abiertos
watch(seleccion, () => {
  loadDetalle1()
  loadDetalle2()
})
```

En los loaders, usar la selección como filtro:
```javascript
const params = seleccion.value ? { filtro: seleccion.value } : {}
const { data } = await axios.get(`${API}/endpoint`, { params })
```

---

## 9. ERRORES FRECUENTES — NO REPETIR

| Error | Causa | Solución |
|---|---|---|
| Tabla principal se oculta al abrir acordeón | `.page-content` tiene `height` fija + `overflow-y: auto` | Usar `min-height` y quitar `overflow-y` de `.page-content` |
| Scroll no funciona | Scroll en `.page-content` en lugar de `.main-area` | El único scroll es en `MainLayout.vue > .main-area` |
| Popups no cierran | Sin listener `click` en document | `onMounted(() => document.addEventListener('click', handleOutsideClick))` |
| Exportar abre misma pestaña | `window.location = url` | Usar `window.open(url, '_blank')` |

---

## 10. EJEMPLO COMPLETO: vista Resumen Facturación

Referencia: `frontend/app/src/pages/ventas/ResumenFacturacionPage.vue`

- Tabla principal: `resumen_ventas_facturas_mes` (15 meses)
- 4 acordeones: canal, cliente, producto, facturas del mes
- Drill-down: clic en fila de mes → filtra los 4 acordeones
- Badge en título: muestra el mes seleccionado con botón para limpiar
