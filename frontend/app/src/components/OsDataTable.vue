<template>
  <div class="os-table-wrapper">

    <!-- ── TOOLBAR ── -->
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-title">{{ title }}</span>
        <span v-if="!loading" class="row-count">{{ filteredRows.length }}</span>
      </div>
      <div class="toolbar-right">
        <!-- Filtrar -->
        <div class="toolbar-btn-wrap" ref="filterRef">
          <button class="toolbar-btn" :class="{ active: activeFilters.length > 0 }" @click.stop="showFilter = !showFilter">
            <FilterIcon :size="14" />
            <span>Filtrar</span>
            <span v-if="activeFilters.length > 0" class="btn-badge">{{ activeFilters.length }}</span>
          </button>
          <!-- Popup filtros -->
          <div v-if="showFilter" class="popup filter-popup" @click.stop>
            <div class="pp-section-label">Filtros</div>
            <div class="filter-list">
              <div v-for="(f, i) in activeFilters" :key="i" class="filter-row">
                <select v-model="f.field" class="pp-select">
                  <option v-for="col in filterableCols" :key="col.key" :value="col.key">{{ col.label }}</option>
                </select>
                <select v-model="f.op" class="pp-select pp-select-op">
                  <option value="contains">contiene</option>
                  <option value="eq">igual a</option>
                  <option value="gte">≥</option>
                  <option value="lte">≤</option>
                </select>
                <input v-model="f.value" class="pp-input" placeholder="valor" @keyup.enter="showFilter = false" />
                <button class="pp-icon-btn" @click="removeFilter(i)"><XIcon :size="12" /></button>
              </div>
              <div v-if="activeFilters.length === 0" class="pp-empty">Sin filtros activos</div>
            </div>
            <div class="pp-footer">
              <button class="pp-action-btn" @click="addFilter"><PlusIcon :size="13" />Añadir filtro</button>
              <button v-if="activeFilters.length > 0" class="pp-action-btn danger" @click="activeFilters = []">Limpiar todo</button>
            </div>
          </div>
        </div>

        <!-- Campos (Display) -->
        <div class="toolbar-btn-wrap" ref="fieldsRef">
          <button class="toolbar-btn" @click.stop="showFields = !showFields">
            <SlidersHorizontalIcon :size="14" />
            <span>Campos</span>
          </button>
          <!-- Popup campos -->
          <div v-if="showFields" class="popup fields-popup" @click.stop>
            <div class="pp-section-label">Propiedades visibles</div>
            <div class="fields-pills">
              <button
                v-for="col in localColumns"
                :key="col.key"
                class="field-pill"
                :class="{ active: col.visible }"
                @click="col.visible = !col.visible"
              >{{ col.label }}</button>
            </div>
            <div class="pp-divider" />
            <div class="pp-footer">
              <button class="pp-action-btn" @click="showAll">Mostrar todos</button>
              <button class="pp-action-btn" @click="hideAll">Ocultar todos</button>
            </div>
          </div>
        </div>

        <!-- Exportar -->
        <div class="toolbar-btn-wrap" ref="exportRef">
          <button class="toolbar-btn" @click.stop="showExport = !showExport">
            <DownloadIcon :size="14" />
            <span>Exportar</span>
          </button>
          <!-- Popup export -->
          <div v-if="showExport" class="popup export-popup" @click.stop>
            <div class="pp-section-label">Exportar como</div>
            <div class="export-list">
              <button class="export-row" @click="doExport('csv')">
                <FileTextIcon :size="15" class="export-icon" />
                <span class="export-label">CSV</span>
                <span class="export-desc">Separado por comas</span>
              </button>
              <button class="export-row" @click="doExport('xlsx')">
                <TableIcon :size="15" class="export-icon" />
                <span class="export-label">Excel</span>
                <span class="export-desc">Archivo .xlsx</span>
              </button>
              <button class="export-row" @click="doExport('pdf')">
                <FileIcon :size="15" class="export-icon" />
                <span class="export-label">PDF</span>
                <span class="export-desc">Documento PDF</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── TABLA ── -->
    <div class="table-scroll">
      <table class="os-table">
        <thead>
          <tr>
            <th v-for="col in visibleColumns" :key="col.key" @click="setSort(col.key)" class="th">
              <div class="th-inner">
                {{ col.label }}
                <span v-if="sortKey === col.key" class="sort-icon">
                  <component :is="sortDir === 'asc' ? ChevronUpIcon : ChevronDownIcon" :size="12" />
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Skeleton loading -->
          <template v-if="loading">
            <tr v-for="n in 8" :key="n" class="skeleton-row">
              <td v-for="col in visibleColumns" :key="col.key">
                <div class="skeleton-cell" />
              </td>
            </tr>
          </template>
          <!-- Datos -->
          <template v-else>
            <tr
              v-for="(row, idx) in sortedRows"
              :key="row._pk || row.mes || row._key || idx"
              class="data-row"
              :class="{ selected: isSelected(row) }"
              @click="selectRow(row)"
            >
              <td v-for="col in visibleColumns" :key="col.key" class="td">
                <span class="cell-value">{{ formatCell(row[col.key], col.key) }}</span>
              </td>
            </tr>
            <!-- Vacío -->
            <tr v-if="sortedRows.length === 0">
              <td :colspan="visibleColumns.length" class="empty-cell">
                <div class="empty-state">
                  <InboxIcon :size="24" />
                  <span>Sin resultados</span>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ── PIE: total filas ── -->
    <div v-if="!loading && sortedRows.length > 0" class="table-footer">
      {{ sortedRows.length }} filas
      <span v-if="activeFilters.length > 0"> · {{ rows.length - sortedRows.length }} filtradas</span>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  FilterIcon, SlidersHorizontalIcon, DownloadIcon, XIcon, PlusIcon,
  ChevronUpIcon, ChevronDownIcon, FileTextIcon, TableIcon, FileIcon, InboxIcon
} from 'lucide-vue-next'

const props = defineProps({
  rows:    { type: Array,   default: () => [] },
  columns: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
  title:   { type: String,  default: '' },
  recurso: { type: String,  default: '' },
  mes:     { type: String,  default: '' },
})

const emit = defineEmits(['row-click'])

// ── Columnas locales (copia para mutar visible) ──────
const localColumns = ref([])
watch(() => props.columns, (cols) => {
  localColumns.value = cols.map(c => ({ ...c }))
}, { immediate: true })

const visibleColumns  = computed(() => localColumns.value.filter(c => c.visible))
const filterableCols  = computed(() => localColumns.value)

// ── Filtros ──────────────────────────────────────────
const showFilter    = ref(false)
const showFields    = ref(false)
const showExport    = ref(false)
const activeFilters = ref([])

function addFilter() {
  activeFilters.value.push({ field: localColumns.value[0]?.key || '', op: 'contains', value: '' })
}
function removeFilter(i) { activeFilters.value.splice(i, 1) }

const filteredRows = computed(() => {
  if (activeFilters.value.length === 0) return props.rows
  return props.rows.filter(row => {
    return activeFilters.value.every(f => {
      const val = String(row[f.field] ?? '').toLowerCase()
      const fv  = String(f.value).toLowerCase()
      if (f.op === 'contains') return val.includes(fv)
      if (f.op === 'eq')       return val === fv
      if (f.op === 'gte')      return parseFloat(row[f.field]) >= parseFloat(f.value)
      if (f.op === 'lte')      return parseFloat(row[f.field]) <= parseFloat(f.value)
      return true
    })
  })
})

// ── Ordenamiento ─────────────────────────────────────
const sortKey = ref('')
const sortDir = ref('asc')
function setSort(key) {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortKey.value = key; sortDir.value = 'asc' }
}
const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value
  return [...filteredRows.value].sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    const n = (v) => parseFloat(String(v).replace(',', '.'))
    const r = isNaN(n(av)) ? String(av).localeCompare(String(bv)) : n(av) - n(bv)
    return sortDir.value === 'asc' ? r : -r
  })
})

// ── Selección de fila ─────────────────────────────────
const selectedRow = ref(null)
function selectRow(row) {
  selectedRow.value = row
  emit('row-click', row)
}
function isSelected(row) {
  if (!selectedRow.value) return false
  const s = selectedRow.value
  if (s._pk   != null) return row._pk   === s._pk
  if (s._key  != null) return row._key  === s._key
  if (s.mes   != null) return row.mes   === s.mes
  return false
}

// ── Campos ───────────────────────────────────────────
function showAll() { localColumns.value.forEach(c => c.visible = true) }
function hideAll() { localColumns.value.forEach(c => c.visible = false) }

// ── Exportar ─────────────────────────────────────────
function doExport(format) {
  showExport.value = false
  const visibleKeys = visibleColumns.value.map(c => c.key)
  const filters = activeFilters.value.length > 0 ? JSON.stringify(activeFilters.value) : undefined
  const params = new URLSearchParams({ format, fields: JSON.stringify(visibleKeys) })
  if (props.mes) params.set('mes', props.mes)
  if (filters)   params.set('filters', filters)
  window.open(`/api/export/${props.recurso}?${params}`, '_blank')
}

// ── Formato de celda ─────────────────────────────────
function formatCell(val, key) {
  if (val === null || val === undefined) return '—'
  // Porcentajes
  if (key.includes('_pct') || key.includes('_margen')) {
    const n = parseFloat(val)
    return isNaN(n) ? val : (n * 100).toFixed(1) + '%'
  }
  // Moneda
  if (key.startsWith('fin_') || key.startsWith('cto_') || key.startsWith('car_') || key.includes('ventas') || key.includes('ticket') || key.includes('costo') || key.includes('utilidad')) {
    const n = parseFloat(String(val).replace(',', '.'))
    if (!isNaN(n)) return '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 })
  }
  return val
}

// ── Cerrar popups al hacer clic fuera ────────────────
function handleOutsideClick() {
  showFilter.value = false
  showFields.value = false
  showExport.value = false
}
onMounted(() => document.addEventListener('click', handleOutsideClick))
onUnmounted(() => document.removeEventListener('click', handleOutsideClick))
</script>

<style scoped>
/* ── WRAPPER ── */
.os-table-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ── TOOLBAR ── */
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-toolbar);
}
.toolbar-left { display: flex; align-items: center; gap: 8px; }
.table-title  { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.row-count    {
  font-size: 11px; font-weight: 500;
  color: var(--text-tertiary);
  background: rgba(0,0,0,0.06);
  padding: 1px 7px; border-radius: var(--radius-full);
}
.toolbar-right { display: flex; align-items: center; gap: 4px; }

/* ── TOOLBAR BUTTONS ── */
.toolbar-btn-wrap { position: relative; }
.toolbar-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 12px; font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms, color 80ms, border-color 80ms;
  white-space: nowrap;
  font-family: var(--font-sans);
}
.toolbar-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }
.toolbar-btn.active { color: var(--accent); border-color: var(--accent-border); background: var(--accent-muted); }
.btn-badge {
  background: var(--accent); color: white;
  font-size: 10px; font-weight: 700;
  padding: 0 5px; border-radius: var(--radius-full);
  min-width: 16px; text-align: center;
}

/* ── POPUPS — base ── */
.popup {
  position: absolute; top: calc(100% + 6px); right: 0;
  background: var(--bg-modal);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 200;
  min-width: 240px;
  animation: popup-in 120ms ease-out;
  overflow: hidden;
}
@keyframes popup-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0)    scale(1); }
}

/* Label de sección (encabezado sin botón X, como Linear) */
.pp-section-label {
  padding: 10px 14px 6px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--text-tertiary);
}

/* Divider interno */
.pp-divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }

/* Footer */
.pp-footer {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 10px 10px;
  border-top: 1px solid var(--border-subtle);
}
.pp-action-btn {
  display: inline-flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 8px; border-radius: var(--radius-sm);
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  transition: background 60ms; font-family: var(--font-sans);
}
.pp-action-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.pp-action-btn.danger:hover { color: var(--color-error); }

/* Vacío */
.pp-empty { padding: 10px 14px; font-size: 12px; color: var(--text-tertiary); }

/* Ícono btn dentro de popup */
.pp-icon-btn {
  width: 22px; height: 22px; border-radius: var(--radius-sm); border: none;
  background: transparent; color: var(--text-tertiary); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: background 60ms;
}
.pp-icon-btn:hover { background: var(--bg-card-hover); color: var(--color-error); }

/* ── FILTRAR ── */
.filter-popup { min-width: 440px; }
.filter-list  { padding: 2px 10px 6px; display: flex; flex-direction: column; gap: 5px; max-height: 220px; overflow-y: auto; }
.filter-row   { display: flex; align-items: center; gap: 5px; }
.pp-select {
  height: 27px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  font-size: 12px; color: var(--text-primary);
  padding: 0 7px; outline: none;
  font-family: var(--font-sans); cursor: pointer;
}
.pp-select:focus { border-color: var(--accent); }
.pp-select        { min-width: 130px; }
.pp-select-op     { min-width: 80px; }
.pp-input {
  flex: 1; height: 27px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  font-size: 12px; color: var(--text-primary);
  padding: 0 8px; outline: none;
  font-family: var(--font-sans);
}
.pp-input:focus { border-color: var(--accent); }

/* ── CAMPOS — pills ── */
.fields-popup { min-width: 280px; }
.fields-pills {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 6px 12px 10px;
  max-height: 220px; overflow-y: auto;
}
.field-pill {
  display: inline-flex; align-items: center;
  height: 26px; padding: 0 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; transition: all 80ms;
  font-family: var(--font-sans);
}
.field-pill:hover { border-color: var(--border-strong); color: var(--text-primary); }
.field-pill.active {
  background: var(--accent-muted);
  border-color: var(--accent-border);
  color: var(--accent);
  font-weight: 500;
}

/* ── EXPORTAR ── */
.export-popup { min-width: 220px; }
.export-list  { padding: 4px 6px 8px; display: flex; flex-direction: column; gap: 1px; }
.export-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: var(--radius-md);
  border: none; background: transparent; width: 100%;
  cursor: pointer; transition: background 80ms;
  font-family: var(--font-sans);
}
.export-row:hover { background: var(--bg-card-hover); }
.export-icon { color: var(--text-tertiary); flex-shrink: 0; }
.export-label { font-size: 13px; color: var(--text-primary); font-weight: 500; flex: 1; text-align: left; }
.export-desc  { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }

/* ── TABLA ── */
.table-scroll { overflow-x: auto; }
.os-table     { width: 100%; border-collapse: collapse; font-size: 13px; }

.th {
  text-align: left; padding: 0 12px;
  height: 36px;
  font-size: 11px; font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg-app);
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap; cursor: pointer; user-select: none;
  position: sticky; top: 0; z-index: 5;
}
.th:hover { color: var(--text-secondary); }
.th-inner { display: flex; align-items: center; gap: 4px; }

.data-row { cursor: pointer; transition: background 60ms; }
.data-row:hover    { background: var(--bg-row-hover); }
.data-row.selected { background: var(--bg-row-selected); }

.td {
  padding: 0 12px;
  height: 36px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  white-space: nowrap;
  max-width: 240px; overflow: hidden; text-overflow: ellipsis;
}
.cell-value { font-size: 13px; }

/* skeleton */
.skeleton-row td { padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); }
.skeleton-cell { height: 14px; border-radius: var(--radius-sm); background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.09) 50%, rgba(0,0,0,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* vacío */
.empty-cell { padding: 48px 16px; text-align: center; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--text-tertiary); font-size: 13px; }

/* footer */
.table-footer { padding: 8px 14px; font-size: 12px; color: var(--text-tertiary); border-top: 1px solid var(--border-subtle); }

/* botones helper */
.icon-btn {
  width: 24px; height: 24px; border-radius: var(--radius-sm); border: none;
  background: transparent; color: var(--text-tertiary); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 60ms;
}
.icon-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.icon-btn.danger:hover { background: var(--color-error-bg); color: var(--color-error); }
.btn-ghost-sm {
  display: inline-flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 8px; border-radius: var(--radius-sm);
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  transition: background 60ms; font-family: var(--font-sans);
}
.btn-ghost-sm:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.btn-ghost-sm.danger:hover { color: var(--color-error); }
</style>
