<template>
  <div ref="wrapperRef" class="os-table-wrapper">

    <!-- ── TOOLBAR ── -->
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-title">{{ title }}</span>
        <span v-if="!loading" class="row-count">{{ filteredRows.length }}</span>
        <!-- Indicadores de filtros activos -->
        <template v-if="activeFilterCount > 0">
          <span class="filter-badge" @click="clearAllFilters" title="Limpiar filtros">
            <FilterIcon :size="11" />
            {{ activeFilterCount }}
            <XIcon :size="10" />
          </span>
        </template>
        <!-- Indicadores de subtotales activos -->
        <template v-if="activeAggregateCount > 0">
          <span class="agg-badge" title="Subtotales activos">
            Σ {{ activeAggregateCount }}
          </span>
        </template>
      </div>
      <div class="toolbar-right">
        <!-- Slot para controles externos (filtros de fecha, etc.) -->
        <slot name="toolbar" />
        <!-- Campos (Display) -->
        <div class="toolbar-btn-wrap" ref="fieldsRef">
          <button class="toolbar-btn" @click.stop="showFields = !showFields">
            <SlidersHorizontalIcon :size="14" />
            <span class="toolbar-btn-label">Campos</span>
          </button>
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
            <span class="toolbar-btn-label">Exportar</span>
          </button>
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
            <th
              v-for="col in visibleColumns"
              :key="col.key"
              class="th"
              :class="{
                'th-filtered': hasFilter(col.key),
                'th-sorted': sortKey === col.key,
                'th-agg': !!columnAggregates[col.key],
                'th-popup-open': colPopup === col.key
              }"
              :title="effectiveTooltips[col.key] || ''"
              @click.stop="openColPopup(col.key)"
            >
              <div class="th-inner">
                <span class="th-label">{{ col.label }}</span>
                <span v-if="sortKey === col.key" class="sort-icon">
                  <component :is="sortDir === 'asc' ? ChevronUpIcon : ChevronDownIcon" :size="12" />
                </span>
                <span v-if="hasFilter(col.key)" class="th-filter-dot" />
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
            <!-- Fila de subtotales — arriba, justo debajo del header -->
            <tr v-if="hasAggregates && sortedRows.length > 0" class="agg-row">
              <td v-for="col in visibleColumns" :key="col.key" class="td agg-td">
                <template v-if="columnAggregates[col.key]">
                  <span class="agg-label">{{ aggLabel(columnAggregates[col.key]) }}</span>
                  <span class="agg-value">{{ formatCell(computeAggregate(col.key, columnAggregates[col.key]), col.key) }}</span>
                </template>
              </td>
            </tr>
            <tr
              v-for="(row, idx) in sortedRows"
              :key="row._pk || row.mes || row._key || idx"
              class="data-row"
              :class="[{ 'multi-sel': isSelected(row) }, props.rowClass?.(row)]"
              @click="onRowClick(row, $event)"
              @touchstart.passive="onRowTouchStart(row)"
              @touchend="onRowTouchEnd"
              @touchmove.passive="onRowTouchEnd"
              @touchcancel="onRowTouchEnd"
            >
              <td v-for="col in visibleColumns" :key="col.key" class="td" :class="{ 'td-nowrap': col.nowrap }">
                <slot :name="`cell-${col.key}`" :row="row" :col="col" :value="row[col.key]">
                  <span class="cell-value">{{ formatCell(row[col.key], col.key) }}</span>
                </slot>
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
      <span v-if="activeFilterCount > 0"> · {{ rows.length - sortedRows.length }} filtradas</span>
    </div>

    <!-- ── POPUP DE COLUMNA (fuera de la tabla, al final del wrapper) ── -->
    <Teleport to="body">
      <div v-if="colPopup" class="col-popup-overlay" @click="colPopup = null">
        <div
          class="col-popup"
          :style="colPopupStyle"
          @click.stop
        >
          <!-- Filtro -->
          <div class="cp-section">
            <label class="cp-label">Filtrar</label>
            <!-- Multi-select con checkboxes (si la columna tiene options) -->
            <template v-if="getColumnOptions(colPopup).length">
              <div class="cp-options">
                <label
                  v-for="opt in getColumnOptions(colPopup)"
                  :key="opt.value"
                  class="cp-option"
                >
                  <input
                    type="checkbox"
                    :checked="isOptionSelected(colPopup, opt.value)"
                    @change="toggleOption(colPopup, opt.value)"
                  />
                  <span v-if="opt.color" class="cp-option-dot" :style="{ background: opt.color }" />
                  <span>{{ opt.label }}</span>
                </label>
              </div>
            </template>
            <!-- Filtro texto/operadores (si la columna NO tiene options) -->
            <template v-else>
              <div class="cp-filter-row">
                <select
                  class="cp-select"
                  :value="getFilterOp(colPopup)"
                  @change="setFilterOp(colPopup, $event.target.value)"
                >
                  <option value="eq">Igual a</option>
                  <option value="contains">Contiene</option>
                  <option value="gt">Mayor que</option>
                  <option value="lt">Menor que</option>
                  <option value="gte">Mayor o igual</option>
                  <option value="lte">Menor o igual</option>
                  <option value="between">Entre</option>
                </select>
              </div>
              <div class="cp-filter-inputs">
                <input
                  ref="colFilterInput"
                  class="cp-input"
                  :placeholder="getFilterOp(colPopup) === 'between' ? 'Desde' : 'Valor'"
                  :value="getFilterVal(colPopup)"
                  @input="setFilterVal(colPopup, $event.target.value)"
                  @keyup.enter="colPopup = null"
                  @keyup.escape="colPopup = null"
                />
                <input
                  v-if="getFilterOp(colPopup) === 'between'"
                  class="cp-input"
                  placeholder="Hasta"
                  :value="getFilterVal2(colPopup)"
                  @input="setFilterVal2(colPopup, $event.target.value)"
                  @keyup.enter="colPopup = null"
                  @keyup.escape="colPopup = null"
                />
              </div>
            </template>
          </div>

          <!-- Ordenar -->
          <div class="cp-section">
            <label class="cp-label">Ordenar</label>
            <div class="cp-sort-btns">
              <button
                class="cp-sort-btn"
                :class="{ active: sortKey === colPopup && sortDir === 'asc' }"
                @click="setSort(colPopup, 'asc')"
              >
                <ChevronUpIcon :size="12" /> Ascendente
              </button>
              <button
                class="cp-sort-btn"
                :class="{ active: sortKey === colPopup && sortDir === 'desc' }"
                @click="setSort(colPopup, 'desc')"
              >
                <ChevronDownIcon :size="12" /> Descendente
              </button>
            </div>
          </div>

          <!-- Subtotal (solo numéricas) -->
          <template v-if="isNumeric(colPopup)">
            <div class="cp-divider" />
            <div class="cp-section">
              <label class="cp-label">Subtotal</label>
              <div class="cp-agg-btns">
                <button
                  v-for="agg in aggOptions"
                  :key="agg.value"
                  class="cp-agg-btn"
                  :class="{ active: columnAggregates[colPopup] === agg.value }"
                  @click="toggleAggregate(colPopup, agg.value)"
                >
                  <span class="cp-agg-icon">{{ agg.icon }}</span>
                  {{ agg.label }}
                </button>
              </div>
            </div>
          </template>

          <!-- Limpiar -->
          <div v-if="hasFilter(colPopup) || columnAggregates[colPopup] || (sortKey === colPopup)" class="cp-footer">
            <button class="cp-clear-btn" @click="clearColumn(colPopup)">Limpiar todo</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
  SlidersHorizontalIcon, DownloadIcon, XIcon, FilterIcon,
  ChevronUpIcon, ChevronDownIcon, FileTextIcon, TableIcon, FileIcon, InboxIcon
} from 'lucide-vue-next'

const props = defineProps({
  rows:    { type: Array,   default: () => [] },
  columns: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
  title:   { type: String,  default: '' },
  recurso:  { type: String,  default: '' },
  mes:      { type: String,  default: '' },
  tooltips: { type: Object,  default: () => ({}) },
  selectedIds: { type: Array, default: () => [] },
  rowClass:     { type: Function, default: null },
})

const emit = defineEmits(['row-click', 'select-toggle'])

function isSelected(row) {
  return props.selectedIds.includes(row.id)
}

function onRowClick(row, e) {
  // En modo multi-select activo: click toglea
  if (props.selectedIds.length > 0) {
    e.stopPropagation()
    emit('select-toggle', row)
    return
  }
  // Ctrl/Cmd + click: inicia multi-select
  if (e.ctrlKey || e.metaKey) {
    e.stopPropagation()
    emit('select-toggle', row)
    return
  }
  // Si vino de un long-press recién disparado, ignorar el click subsiguiente
  if (_longPressTriggered) {
    _longPressTriggered = false
    e.stopPropagation()
    return
  }
  emit('row-click', row)
}

let _longPressTriggered = false
let _longPressTimer = null
function onRowTouchStart(row) {
  _longPressTriggered = false
  _longPressTimer = setTimeout(() => {
    _longPressTimer = null
    _longPressTriggered = true
    emit('select-toggle', row)
  }, 500)
}
function onRowTouchEnd() {
  if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null }
}

// ── Columnas locales (copia para mutar visible) ──────
const wrapperRef = ref(null)
const localColumns = ref([])
watch(() => props.columns, (cols) => {
  localColumns.value = cols.map(c => ({ ...c }))
}, { immediate: true, deep: true })

const visibleColumns  = computed(() => localColumns.value.filter(c => c.visible))

// ── Popups toolbar ──────────────────────────────────
const showFields    = ref(false)
const showExport    = ref(false)

// ── Popup de columna ────────────────────────────────
const colPopup = ref(null)
const colPopupStyle = ref({})

function openColPopup(key) {
  if (colPopup.value === key) {
    colPopup.value = null
    return
  }
  // Calcular posición del th clickeado — buscar SOLO dentro de esta instancia
  const root = wrapperRef.value
  const thEls = root ? root.querySelectorAll('.os-table .th') : []
  const colIdx = visibleColumns.value.findIndex(c => c.key === key)
  const thEl = thEls[colIdx]
  if (thEl) {
    const rect = thEl.getBoundingClientRect()
    colPopupStyle.value = {
      top: (rect.bottom + 4) + 'px',
      left: Math.max(4, rect.left) + 'px',
    }
  }
  colPopup.value = key
  nextTick(() => {
    const input = document.querySelector('.col-popup .cp-input')
    if (input) input.focus()
  })
}

// ── Filtros por columna ─────────────────────────────
// Cada filtro: { op: string, val: string, val2: string, selected: Array }
const columnFilters = ref({})

function getFilterOp(key) { return columnFilters.value[key]?.op || 'eq' }
function getFilterVal(key) { return columnFilters.value[key]?.val || '' }
function getFilterVal2(key) { return columnFilters.value[key]?.val2 || '' }

function setFilterOp(key, op) {
  const curr = columnFilters.value[key] || { op: 'eq', val: '', val2: '' }
  columnFilters.value = { ...columnFilters.value, [key]: { ...curr, op } }
}
function setFilterVal(key, val) {
  const curr = columnFilters.value[key] || { op: 'eq', val: '', val2: '' }
  columnFilters.value = { ...columnFilters.value, [key]: { ...curr, val } }
}
function setFilterVal2(key, val2) {
  const curr = columnFilters.value[key] || { op: 'eq', val: '', val2: '' }
  columnFilters.value = { ...columnFilters.value, [key]: { ...curr, val2 } }
}

// Multi-select por opciones (Estado, Prioridad, Categoría, etc.)
// Retorna [{ value, label, color }]
function getColumnOptions(key) {
  const col = localColumns.value.find(c => c.key === key)
  if (!col?.options) return []
  return col.options.map(o => typeof o === 'string' ? { value: o, label: o } : o)
}
function isOptionSelected(key, value) {
  return (columnFilters.value[key]?.selected || []).includes(value)
}
function toggleOption(key, value) {
  const curr = columnFilters.value[key] || { op: 'eq', val: '', val2: '', selected: [] }
  const selected = [...(curr.selected || [])]
  const idx = selected.indexOf(value)
  if (idx === -1) selected.push(value)
  else selected.splice(idx, 1)
  columnFilters.value = { ...columnFilters.value, [key]: { ...curr, selected } }
}

function hasFilter(key) {
  const f = columnFilters.value[key]
  if (!f) return false
  if ((f.selected || []).length > 0) return true
  return (f.val || '').trim() !== ''
}

const activeFilterCount = computed(() => {
  return Object.keys(columnFilters.value).filter(k => hasFilter(k)).length
})

function clearAllFilters() {
  columnFilters.value = {}
}

const filteredRows = computed(() => {
  let data = props.rows
  const keys = Object.keys(columnFilters.value).filter(k => hasFilter(k))
  if (keys.length === 0) return data

  return data.filter(row => {
    return keys.every(key => {
      const f = columnFilters.value[key]
      // Multi-select por opciones (checkboxes)
      if ((f.selected || []).length > 0) {
        return f.selected.includes(row[key])
      }
      const fv = (f.val || '').trim()
      if (!fv) return true
      const raw = row[key]
      const rawNum = parseFloat(String(raw).replace(',', '.'))
      const fNum = parseFloat(fv)
      const val = String(raw ?? '').toLowerCase()

      switch (f.op) {
        case 'eq':
          return val === fv.toLowerCase()
        case 'contains':
          return val.includes(fv.toLowerCase())
        case 'gt':
          return !isNaN(fNum) && !isNaN(rawNum) && rawNum > fNum
        case 'lt':
          return !isNaN(fNum) && !isNaN(rawNum) && rawNum < fNum
        case 'gte':
          return !isNaN(fNum) && !isNaN(rawNum) && rawNum >= fNum
        case 'lte':
          return !isNaN(fNum) && !isNaN(rawNum) && rawNum <= fNum
        case 'between': {
          const fv2 = f.val2?.trim()
          const fNum2 = parseFloat(fv2)
          if (isNaN(rawNum) || isNaN(fNum)) return false
          if (!fv2 || isNaN(fNum2)) return rawNum >= fNum
          return rawNum >= fNum && rawNum <= fNum2
        }
        default:
          return val.includes(fv.toLowerCase())
      }
    })
  })
})

// ── Ordenamiento ─────────────────────────────────────
const sortKey = ref('')
const sortDir = ref('asc')

function setSort(key, dir) {
  if (sortKey.value === key && sortDir.value === dir) {
    sortKey.value = ''
  } else {
    sortKey.value = key
    sortDir.value = dir
  }
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

// ── Subtotales / Agregados ──────────────────────────
const columnAggregates = ref({})

const aggOptions = [
  { value: 'sum', label: 'Suma',     icon: 'Σ' },
  { value: 'avg', label: 'Promedio', icon: 'x̄' },
  { value: 'max', label: 'Máximo',   icon: '↑' },
  { value: 'min', label: 'Mínimo',   icon: '↓' },
]

function toggleAggregate(key, aggType) {
  if (columnAggregates.value[key] === aggType) {
    const copy = { ...columnAggregates.value }
    delete copy[key]
    columnAggregates.value = copy
  } else {
    columnAggregates.value = { ...columnAggregates.value, [key]: aggType }
  }
}

const activeAggregateCount = computed(() => Object.keys(columnAggregates.value).length)
const hasAggregates = computed(() => activeAggregateCount.value > 0)

function computeAggregate(key, aggType) {
  const vals = sortedRows.value
    .map(r => parseFloat(String(r[key]).replace(',', '.')))
    .filter(n => !isNaN(n))
  if (vals.length === 0) return null
  if (aggType === 'sum') return vals.reduce((a, b) => a + b, 0)
  if (aggType === 'avg') return vals.reduce((a, b) => a + b, 0) / vals.length
  if (aggType === 'max') return Math.max(...vals)
  if (aggType === 'min') return Math.min(...vals)
  return null
}

function aggLabel(type) {
  const m = { sum: 'Σ', avg: 'x̄', max: '↑', min: '↓' }
  return m[type] || ''
}

// ── Detectar columna numérica ───────────────────────
function isNumeric(key) {
  if (key.startsWith('fin_') || key.startsWith('cto_') || key.startsWith('vol_') ||
      key.startsWith('cli_') || key.startsWith('car_') || key.startsWith('cat_') ||
      key.startsWith('con_') || key.startsWith('pry_') || key.startsWith('ant_') ||
      key.startsWith('year_ant_') || key.startsWith('mes_ant_') ||
      key.startsWith('rem_') ||
      key.endsWith('_min') || key.endsWith('_seg') || key.endsWith('_count') ||
      key.includes('_pct') || key.includes('ventas') || key.includes('costo') ||
      key.includes('ticket') || key.includes('utilidad') || key.includes('margen') ||
      key === 'subtotal' || key === 'total_neto' || key === 'iva' || key === 'descuento') {
    return true
  }
  const sample = props.rows.slice(0, 5)
  if (sample.length === 0) return false
  return sample.every(r => {
    const v = r[key]
    if (v === null || v === undefined || v === '') return true
    const s = String(v).trim()
    // Usar Number() en lugar de parseFloat() — es estricto: Number("2026-01") = NaN, parseFloat("2026-01") = 2026
    return s !== '' && !isNaN(Number(s))
  })
}

// ── Limpiar columna ─────────────────────────────────
function clearColumn(key) {
  const cf = { ...columnFilters.value }
  delete cf[key]
  columnFilters.value = cf

  const ca = { ...columnAggregates.value }
  delete ca[key]
  columnAggregates.value = ca

  if (sortKey.value === key) sortKey.value = ''
  colPopup.value = null
}

// ── Campos ───────────────────────────────────────────
function showAll() { localColumns.value.forEach(c => c.visible = true) }
function hideAll() { localColumns.value.forEach(c => c.visible = false) }

// ── Exportar ─────────────────────────────────────────
function doExport(format) {
  showExport.value = false
  // Si hay recurso definido, usar endpoint del servidor (ERP)
  if (props.recurso) {
    const visibleKeys = visibleColumns.value.map(c => c.key)
    const params = new URLSearchParams({ format, fields: JSON.stringify(visibleKeys) })
    if (props.mes) params.set('mes', props.mes)
    window.open(`/api/export/${props.recurso}?${params}`, '_blank')
    return
  }
  // Fallback client-side: exportar datos ya cargados
  const cols  = visibleColumns.value
  const data  = sortedRows.value
  const fname = (props.title || 'tabla').replace(/[^a-z0-9]+/gi, '_').toLowerCase()

  if (format === 'csv') {
    const header = cols.map(c => `"${c.label.replace(/"/g, '""')}"`).join(',')
    const rows   = data.map(r => cols.map(c => {
      const v = r[c.key]
      if (v === null || v === undefined) return ''
      const s = String(v).replace(/"/g, '""')
      return `"${s}"`
    }).join(','))
    const csv = '\uFEFF' + [header, ...rows].join('\n')
    downloadBlob(csv, `${fname}.csv`, 'text/csv;charset=utf-8')
  } else if (format === 'xlsx') {
    // XLSX simple como HTML-Excel (compatible con Excel)
    let html = '<table><thead><tr>'
    cols.forEach(c => html += `<th>${escapeHtml(c.label)}</th>`)
    html += '</tr></thead><tbody>'
    data.forEach(r => {
      html += '<tr>'
      cols.forEach(c => html += `<td>${escapeHtml(r[c.key] ?? '')}</td>`)
      html += '</tr>'
    })
    html += '</tbody></table>'
    downloadBlob(html, `${fname}.xls`, 'application/vnd.ms-excel')
  } else if (format === 'pdf') {
    // PDF simple vía window.print con estilo
    const win = window.open('', '_blank')
    let html = `<html><head><title>${escapeHtml(props.title || 'Tabla')}</title>
      <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; font-size: 12px; }
        h1 { font-size: 16px; margin-bottom: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
        th { background: #f0f0f0; font-weight: 600; }
      </style></head><body>
      <h1>${escapeHtml(props.title || 'Tabla')}</h1><table><thead><tr>`
    cols.forEach(c => html += `<th>${escapeHtml(c.label)}</th>`)
    html += '</tr></thead><tbody>'
    data.forEach(r => {
      html += '<tr>'
      cols.forEach(c => html += `<td>${escapeHtml(formatCell(r[c.key], c.key))}</td>`)
      html += '</tr>'
    })
    html += '</tbody></table></body></html>'
    win.document.write(html)
    win.document.close()
    setTimeout(() => win.print(), 300)
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}
function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 100)
}

// ── Formato numérico estándar ────────────────────────
// Separador miles: punto. Decimal: coma. Máximo 3 decimales, automático.
function fmtNum(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  // Determinar decimales: 0 si entero, sino hasta 3
  let decimals = 0
  const abs = Math.abs(n)
  const remainder = abs - Math.floor(abs)
  if (remainder > 0.0005) {
    // Tiene decimales
    const s = n.toFixed(3)
    // Quitar ceros finales
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

// ── Formato de celda ─────────────────────────────────
function formatCell(val, key) {
  if (val === null || val === undefined) return '—'
  // Porcentajes
  if (key.includes('_pct') || key.includes('_margen')) {
    const n = parseFloat(val)
    if (isNaN(n)) return val
    return fmtNum(n * 100) + '%'
  }
  // Duraciones en minutos → "Xh Ym"
  if (key.endsWith('_min') || key.endsWith('_seg')) {
    const n = parseFloat(String(val).replace(',', '.'))
    if (!isNaN(n)) {
      const total = key.endsWith('_seg') ? Math.floor(n / 60) : Math.floor(n)
      const h = Math.floor(total / 60), m = total % 60
      return h > 0 ? `${h}h ${m}m` : `${m}m`
    }
  }
  // Moneda (con símbolo $)
  if (key.startsWith('fin_') || key.startsWith('cto_') || key.startsWith('car_') ||
      key.includes('ventas') || key.includes('ticket') || key.includes('costo') ||
      key.includes('utilidad')) {
    const n = parseFloat(String(val).replace(',', '.'))
    if (!isNaN(n)) return '$' + fmtNum(n)
  }
  // Numéricos genéricos (no moneda, no porcentaje)
  if (isNumeric(key)) {
    const n = parseFloat(String(val).replace(',', '.'))
    if (!isNaN(n)) return fmtNum(n)
  }
  return val
}

// ── Tooltips — solo usa los que vengan como prop ─────
const effectiveTooltips = computed(() => props.tooltips || {})

// ── Cerrar popups al hacer clic fuera ────────────────
function handleOutsideClick() {
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
  overflow: visible;
  position: relative;
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
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
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

/* Mobile: toolbar flexible y botones solo ícono */
@media (max-width: 768px) {
  .table-toolbar { padding: 6px 10px; height: auto; min-height: 36px; flex-wrap: wrap; gap: 4px; }
  .toolbar-right { flex-wrap: wrap; }
  .toolbar-btn .toolbar-btn-label { display: none; }
  .toolbar-btn {
    padding: 0 8px !important;
    min-width: 32px;
  }
}

/* Badges de filtro/agg activos */
.filter-badge, .agg-badge {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 11px; font-weight: 500;
  padding: 1px 7px; border-radius: var(--radius-full);
  cursor: pointer; transition: all 80ms;
}
.filter-badge {
  color: var(--accent); background: var(--accent-muted);
  border: 1px solid var(--accent-border);
}
.filter-badge:hover { background: var(--accent); color: white; }
.agg-badge {
  color: var(--color-success); background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
}

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
.pp-section-label {
  padding: 10px 14px 6px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--text-tertiary);
}
.pp-divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }
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
  transition: color 80ms;
}
.th:hover { color: var(--text-secondary); }
.th-filtered { color: var(--accent); }
.th-sorted   { color: var(--text-primary); }
.th-agg      { border-bottom-color: var(--color-success); }
.th-popup-open { color: var(--accent); background: var(--accent-muted); }
.th-inner { display: flex; align-items: center; gap: 4px; }
.th-label { flex: 1; }
.th-filter-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent); flex-shrink: 0;
}

/* ── FILAS ── */
.data-row { cursor: pointer; transition: background 60ms; }
.data-row:hover { background: var(--bg-row-hover); }
.data-row.multi-sel {
  background: rgba(59, 130, 246, 0.10) !important;
  outline: 1px solid rgba(59, 130, 246, 0.4);
  outline-offset: -1px;
}

.td {
  padding: 8px 12px;
  min-height: 36px;
  min-width: 160px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  vertical-align: middle;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.td-nowrap {
  white-space: nowrap;
  max-width: 240px; overflow: hidden; text-overflow: ellipsis;
}
.cell-value { font-size: 13px; }

/* Fila de subtotales — encima de los datos */
.agg-row { background: rgba(16,185,129,0.04); }
.agg-td {
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid rgba(16,185,129,0.25);
  vertical-align: middle;
  position: sticky;
  top: 36px;   /* justo debajo del th (height: 36px) */
  z-index: 4;
  background: rgba(16,185,129,0.06);
}
.agg-label {
  font-size: 10px; color: var(--color-success);
  margin-right: 4px; font-weight: 700;
}
.agg-value { font-size: 13px; }

/* skeleton */
.skeleton-row td { padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); }
.skeleton-cell { height: 14px; border-radius: var(--radius-sm); background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.09) 50%, rgba(0,0,0,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* vacío */
.empty-cell { padding: 48px 16px; text-align: center; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--text-tertiary); font-size: 13px; }

/* footer */
.table-footer { padding: 8px 14px; font-size: 12px; color: var(--text-tertiary); border-top: 1px solid var(--border-subtle); }
</style>

<style>
/* ── POPUP DE COLUMNA (Teleport a body — NO scoped) ── */
.col-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}
.col-popup {
  position: fixed;
  min-width: 210px;
  max-width: 280px;
  background: var(--bg-modal, #fff);
  border: 1px solid var(--border-strong, #d0d0d0);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.16), 0 2px 8px rgba(0,0,0,0.08);
  z-index: 10000;
  animation: popup-in 120ms ease-out;
  padding: 8px 0;
}

.cp-section { padding: 4px 12px; }
.cp-label {
  font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-tertiary, #888);
  display: block; margin-bottom: 4px;
}
.cp-filter-row { margin-bottom: 6px; }
.cp-options {
  display: flex; flex-direction: column; gap: 2px;
  max-height: 220px; overflow-y: auto;
  padding: 2px 0;
}
.cp-option {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 4px; border-radius: 4px;
  font-size: 12px; color: var(--text-primary, #1a1a1a);
  cursor: pointer; transition: background 60ms;
}
.cp-option:hover { background: var(--bg-card-hover, #f5f5f5); }
.cp-option input[type="checkbox"] {
  margin: 0; cursor: pointer; accent-color: var(--accent, #00C853);
}
.cp-option-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.cp-select {
  width: 100%; height: 28px;
  border-radius: 4px;
  border: 1px solid var(--border-default, #ddd);
  background: var(--bg-input, #fff);
  font-size: 12px; color: var(--text-primary, #1a1a1a);
  padding: 0 7px; outline: none;
  font-family: inherit; cursor: pointer;
  appearance: auto;
}
.cp-select:focus { border-color: var(--accent, #5e6ad2); }

.cp-filter-inputs { display: flex; flex-direction: column; gap: 4px; }
.cp-input {
  width: 100%; height: 28px;
  border-radius: 4px;
  border: 1px solid var(--border-default, #ddd);
  background: var(--bg-input, #fff);
  font-size: 12px; color: var(--text-primary, #1a1a1a);
  padding: 0 8px; outline: none;
  font-family: inherit;
  box-sizing: border-box;
}
.cp-input:focus { border-color: var(--accent, #5e6ad2); }

.cp-sort-btns { display: flex; flex-direction: column; gap: 2px; }
.cp-sort-btn {
  display: flex; align-items: center; gap: 6px;
  height: 28px; padding: 0 8px;
  border-radius: 4px;
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary, #666);
  cursor: pointer; transition: all 60ms;
  font-family: inherit; width: 100%; text-align: left;
}
.cp-sort-btn:hover { background: var(--bg-card-hover, #f5f5f5); color: var(--text-primary, #1a1a1a); }
.cp-sort-btn.active { background: var(--accent-muted, rgba(94,106,210,0.08)); color: var(--accent, #5e6ad2); font-weight: 500; }

.cp-divider { height: 1px; background: var(--border-subtle, #eee); margin: 6px 0; }

.cp-agg-btns { display: flex; flex-direction: column; gap: 2px; }
.cp-agg-btn {
  display: flex; align-items: center; gap: 6px;
  height: 28px; padding: 0 8px;
  border-radius: 4px;
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary, #666);
  cursor: pointer; transition: all 60ms;
  font-family: inherit; width: 100%; text-align: left;
}
.cp-agg-btn:hover { background: var(--bg-card-hover, #f5f5f5); color: var(--text-primary, #1a1a1a); }
.cp-agg-btn.active { background: rgba(16,185,129,0.1); color: var(--color-success, #10b981); font-weight: 500; }
.cp-agg-icon { font-weight: 700; min-width: 14px; text-align: center; }

.cp-footer {
  padding: 4px 8px 0; border-top: 1px solid var(--border-subtle, #eee); margin-top: 4px;
}
.cp-clear-btn {
  width: 100%; height: 26px; border: none; background: transparent;
  font-size: 11px; color: var(--text-tertiary, #999); cursor: pointer;
  border-radius: 4px; transition: all 60ms;
  font-family: inherit;
}
.cp-clear-btn:hover { background: var(--bg-card-hover, #f5f5f5); color: var(--color-error, #ef4444); }
</style>
