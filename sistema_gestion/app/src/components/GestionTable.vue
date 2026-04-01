<template>
  <div class="os-table-wrapper">

    <!-- TOOLBAR -->
    <div class="table-toolbar">
      <div class="toolbar-left">
        <span class="table-title">{{ title }}</span>
        <span v-if="!loading" class="row-count">{{ filteredRows.length }}</span>
        <span v-if="activeFilterCount > 0" class="filter-badge" @click="clearAllFilters" title="Limpiar filtros">
          <span class="material-icons" style="font-size:11px">filter_list</span>
          {{ activeFilterCount }}
          <span class="material-icons" style="font-size:10px">close</span>
        </span>
        <span v-if="activeAggCount > 0" class="agg-badge">Σ {{ activeAggCount }}</span>
      </div>
      <div class="toolbar-right">
        <!-- Slot para controles externos (filtros de fecha, etc.) -->
        <slot name="toolbar" />
        <!-- Campos -->
        <div class="toolbar-btn-wrap" ref="fieldsRef">
          <button class="toolbar-btn" @click.stop="showFields = !showFields">
            <span class="material-icons" style="font-size:14px">tune</span>
            <span>Campos</span>
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
      </div>
    </div>

    <!-- TABLA -->
    <div class="table-scroll">
      <table class="os-table">
        <thead>
          <tr>
            <th
              v-for="col in visibleColumns"
              :key="col.key"
              class="th"
              :class="{
                'th-sorted': sortKey === col.key,
                'th-filtered': hasFilter(col.key),
                'th-popup-open': colPopup === col.key
              }"
              :style="col.width ? { width: col.width } : {}"
              @click.stop="openColPopup(col.key, $event)"
            >
              <div class="th-inner">
                <span class="th-label">{{ col.label }}</span>
                <span v-if="sortKey === col.key" class="material-icons sort-icon">
                  {{ sortDir === 'asc' ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}
                </span>
                <span v-if="hasFilter(col.key)" class="th-filter-dot" />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Skeleton -->
          <template v-if="loading">
            <tr v-for="n in 6" :key="n" class="skeleton-row">
              <td v-for="col in visibleColumns" :key="col.key" class="td">
                <div class="skeleton-cell" />
              </td>
            </tr>
          </template>
          <template v-else>
            <!-- Subtotales sticky -->
            <tr v-if="hasAggregates && sortedRows.length > 0" class="agg-row">
              <td v-for="col in visibleColumns" :key="col.key" class="td agg-td">
                <template v-if="columnAggs[col.key]">
                  <span class="agg-label">{{ aggIcon(columnAggs[col.key]) }}</span>
                  <span class="agg-value">{{ formatCell(computeAgg(col.key), col.key) }}</span>
                </template>
              </td>
            </tr>
            <!-- Datos -->
            <tr
              v-for="(row, idx) in sortedRows"
              :key="row.id || idx"
              class="data-row"
              @click="emit('row-click', row)"
            >
              <td v-for="col in visibleColumns" :key="col.key" class="td">
                <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                  {{ formatCell(row[col.key], col.key) }}
                </slot>
              </td>
            </tr>
            <!-- Vacío -->
            <tr v-if="sortedRows.length === 0">
              <td :colspan="visibleColumns.length" class="td-empty">
                <span class="material-icons" style="font-size:24px;opacity:0.3">inbox</span>
                <span>Sin resultados</span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- POPUP COLUMNA — Teleport para no quedar atrapado por overflow -->
    <Teleport to="body">
      <div v-if="colPopup" class="col-popup-overlay" @click="colPopup = null">
        <div class="col-popup" :style="colPopupStyle" @click.stop>
          <!-- Filtro -->
          <div class="cp-section">
            <label class="cp-label">Filtrar</label>
            <div class="cp-filter-row">
              <select class="cp-select" :value="getFilterOp(colPopup)" @change="setFilterOp(colPopup, $event.target.value)">
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
              />
            </div>
          </div>
          <!-- Ordenar -->
          <div class="cp-section">
            <label class="cp-label">Ordenar</label>
            <div class="cp-sort-btns">
              <button class="cp-sort-btn" :class="{ active: sortKey === colPopup && sortDir === 'asc' }" @click="setSort(colPopup, 'asc')">
                <span class="material-icons" style="font-size:12px">keyboard_arrow_up</span> Ascendente
              </button>
              <button class="cp-sort-btn" :class="{ active: sortKey === colPopup && sortDir === 'desc' }" @click="setSort(colPopup, 'desc')">
                <span class="material-icons" style="font-size:12px">keyboard_arrow_down</span> Descendente
              </button>
            </div>
          </div>
          <!-- Subtotal (solo numéricas) -->
          <template v-if="isNumericCol(colPopup)">
            <div class="cp-divider" />
            <div class="cp-section">
              <label class="cp-label">Subtotal</label>
              <div class="cp-agg-btns">
                <button v-for="a in AGG_OPTS" :key="a.v" class="cp-agg-btn" :class="{ active: columnAggs[colPopup] === a.v }" @click="toggleAgg(colPopup, a.v)">
                  {{ a.icon }} {{ a.label }}
                </button>
              </div>
            </div>
          </template>
          <!-- Limpiar -->
          <div v-if="hasFilter(colPopup) || columnAggs[colPopup] || sortKey === colPopup" class="cp-footer">
            <button class="cp-clear-btn" @click="clearColumn(colPopup)">Limpiar todo</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  title:   { type: String,  default: '' },
  rows:    { type: Array,   default: () => [] },
  columns: { type: Array,   default: () => [] },  // [{key, label, visible}]
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['row-click'])

const AGG_OPTS = [
  { v: 'sum', label: 'Suma',     icon: 'Σ' },
  { v: 'avg', label: 'Promedio', icon: 'x̄' },
  { v: 'max', label: 'Máximo',   icon: '↑' },
  { v: 'min', label: 'Mínimo',   icon: '↓' },
]

// ── Columnas ─────────────────────────────────────────
const localColumns = ref([])
watch(() => props.columns, cols => { localColumns.value = cols.map(c => ({ ...c })) }, { immediate: true })
const visibleColumns = computed(() => localColumns.value.filter(c => c.visible))
function showAll() { localColumns.value.forEach(c => c.visible = true) }
function hideAll() { localColumns.value.forEach(c => c.visible = false) }

// ── Popup toolbar ─────────────────────────────────────
const showFields = ref(false)
const fieldsRef  = ref(null)

// ── Filtros por columna ──────────────────────────────
const columnFilters = ref({})
function getFilterOp(key)  { return columnFilters.value[key]?.op  || 'eq' }
function getFilterVal(key)  { return columnFilters.value[key]?.val || '' }
function getFilterVal2(key) { return columnFilters.value[key]?.val2 || '' }
function setFilterOp(key, op)  { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), op } } }
function setFilterVal(key, val)  { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val } } }
function setFilterVal2(key, val2) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val2 } } }
function hasFilter(key) { return !!(columnFilters.value[key]?.val?.trim()) }
const activeFilterCount = computed(() => Object.keys(columnFilters.value).filter(k => hasFilter(k)).length)
function clearAllFilters() { columnFilters.value = {} }

const filteredRows = computed(() => {
  const keys = Object.keys(columnFilters.value).filter(k => hasFilter(k))
  if (!keys.length) return props.rows
  return props.rows.filter(row => keys.every(key => {
    const f   = columnFilters.value[key]
    const fv  = f.val.trim()
    const raw = row[key]
    const n   = v => parseFloat(String(v).replace(',', '.'))
    const val = String(raw ?? '').toLowerCase()
    switch (f.op) {
      case 'eq':      return val === fv.toLowerCase()
      case 'contains':return val.includes(fv.toLowerCase())
      case 'gt':      return !isNaN(n(raw)) && n(raw) > n(fv)
      case 'lt':      return !isNaN(n(raw)) && n(raw) < n(fv)
      case 'gte':     return !isNaN(n(raw)) && n(raw) >= n(fv)
      case 'lte':     return !isNaN(n(raw)) && n(raw) <= n(fv)
      case 'between': { const fv2 = f.val2?.trim(); return !isNaN(n(raw)) && n(raw) >= n(fv) && (!fv2 || n(raw) <= n(fv2)) }
      default:        return val.includes(fv.toLowerCase())
    }
  }))
})

// ── Ordenamiento ──────────────────────────────────────
const sortKey = ref('')
const sortDir = ref('asc')
function setSort(key, dir) {
  if (sortKey.value === key && sortDir.value === dir) { sortKey.value = '' } else { sortKey.value = key; sortDir.value = dir }
}
const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value
  return [...filteredRows.value].sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    const n  = v => parseFloat(String(v).replace(',', '.'))
    const r  = isNaN(n(av)) ? String(av ?? '').localeCompare(String(bv ?? '')) : n(av) - n(bv)
    return sortDir.value === 'asc' ? r : -r
  })
})

// ── Subtotales ────────────────────────────────────────
const columnAggs = ref({})
const activeAggCount = computed(() => Object.keys(columnAggs.value).length)
const hasAggregates  = computed(() => activeAggCount.value > 0)
function toggleAgg(key, v) {
  if (columnAggs.value[key] === v) { const c = { ...columnAggs.value }; delete c[key]; columnAggs.value = c }
  else { columnAggs.value = { ...columnAggs.value, [key]: v } }
}
function computeAgg(key) {
  const t  = columnAggs.value[key]
  const vs = sortedRows.value.map(r => parseFloat(String(r[key]).replace(',','.'))).filter(n => !isNaN(n))
  if (!vs.length) return null
  if (t === 'sum') return vs.reduce((a, b) => a + b, 0)
  if (t === 'avg') return vs.reduce((a, b) => a + b, 0) / vs.length
  if (t === 'max') return Math.max(...vs)
  if (t === 'min') return Math.min(...vs)
  return null
}
function aggIcon(t) { return { sum:'Σ', avg:'x̄', max:'↑', min:'↓' }[t] || '' }

// ── Numérico ──────────────────────────────────────────
function isNumericCol(key) {
  const numKeys = ['tiempo_total_min','tiempo_pausa_min','tiempo_laborado_min','num_pausas']
  if (numKeys.includes(key)) return true
  const sample = props.rows.slice(0, 5)
  if (!sample.length) return false
  return sample.every(r => { const v = r[key]; if (v === null || v === undefined) return true; return !isNaN(Number(String(v).trim())) })
}

// ── Formato celda ─────────────────────────────────────
function formatCell(val, key) {
  if (val === null || val === undefined) return '—'
  return val
}

// ── Popup de columna ─────────────────────────────────
const colPopup      = ref(null)
const colPopupStyle = ref({})
const colFilterInput = ref(null)

function openColPopup(key, event) {
  if (colPopup.value === key) { colPopup.value = null; return }
  const th   = event.currentTarget
  const rect = th.getBoundingClientRect()
  colPopupStyle.value = {
    top:  (rect.bottom + 4) + 'px',
    left: Math.max(4, Math.min(rect.left, window.innerWidth - 230)) + 'px',
  }
  colPopup.value = key
  nextTick(() => { if (colFilterInput.value) colFilterInput.value.focus() })
}

function clearColumn(key) {
  const cf = { ...columnFilters.value }; delete cf[key]; columnFilters.value = cf
  const ca = { ...columnAggs.value };    delete ca[key]; columnAggs.value    = ca
  if (sortKey.value === key) sortKey.value = ''
  colPopup.value = null
}

// ── Cerrar popups toolbar al click fuera ──────────────
function handleOutsideClick() { showFields.value = false }
onMounted(() => document.addEventListener('click', handleOutsideClick))
onUnmounted(() => document.removeEventListener('click', handleOutsideClick))
</script>

<style scoped>
.os-table-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: visible;
  position: relative;
}

/* TOOLBAR */
.table-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  height: 44px; padding: 0 14px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.toolbar-left  { display: flex; align-items: center; gap: 8px; }
.toolbar-right { display: flex; align-items: center; gap: 4px; }
.table-title   { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.row-count     {
  font-size: 11px; font-weight: 500; color: var(--text-tertiary);
  background: rgba(255,255,255,0.06);
  padding: 1px 7px; border-radius: var(--radius-full);
}
.filter-badge {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 11px; font-weight: 500; padding: 1px 7px;
  border-radius: var(--radius-full); cursor: pointer;
  color: var(--accent); background: var(--accent-muted);
  border: 1px solid var(--accent-border); transition: all 80ms;
}
.filter-badge:hover { background: var(--accent); color: #fff; }
.agg-badge {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 500; padding: 1px 7px;
  border-radius: var(--radius-full);
  color: var(--color-success); background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
}

/* TOOLBAR BUTTONS */
.toolbar-btn-wrap { position: relative; }
.toolbar-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans); white-space: nowrap;
  transition: background 80ms, color 80ms, border-color 80ms;
}
.toolbar-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }

/* POPUP BASE */
.popup {
  position: absolute; top: calc(100% + 6px); right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 200; min-width: 240px; overflow: hidden;
  animation: popup-in 120ms ease-out;
}
@keyframes popup-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to   { opacity: 1; transform: none; }
}
.pp-section-label {
  padding: 10px 14px 6px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary);
}
.pp-divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }
.pp-footer  { display: flex; gap: 4px; padding: 6px 10px 10px; border-top: 1px solid var(--border-subtle); }
.pp-action-btn {
  height: 26px; padding: 0 8px; border-radius: var(--radius-sm);
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-sans); transition: background 60ms;
}
.pp-action-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* CAMPOS PILLS */
.fields-popup { min-width: 280px; }
.fields-pills { display: flex; flex-wrap: wrap; gap: 6px; padding: 6px 12px 10px; max-height: 220px; overflow-y: auto; }
.field-pill {
  display: inline-flex; align-items: center;
  height: 26px; padding: 0 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-sans); transition: all 80ms;
}
.field-pill:hover { border-color: var(--border-strong); color: var(--text-primary); }
.field-pill.active { background: var(--accent-muted); border-color: var(--accent-border); color: var(--accent); }

/* TABLA */
.table-scroll { overflow-x: auto; }
.os-table { width: 100%; border-collapse: collapse; font-size: 13px; }

.th {
  text-align: left; padding: 0 12px; height: 36px;
  font-size: 11px; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  position: sticky; top: 0; z-index: 5;
  cursor: pointer; user-select: none; white-space: nowrap;
  transition: color 80ms;
}
.th:hover { color: var(--text-secondary); }
.th-inner  { display: flex; align-items: center; gap: 4px; }
.th-label  { flex: 1; }
.sort-icon { font-size: 14px !important; color: var(--accent); }
.th-sorted { color: var(--accent); }
.th-filter-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.th-popup-open { background: var(--bg-card-hover); }

.td {
  padding: 6px 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary); vertical-align: middle;
  word-break: break-word;
}
.data-row { cursor: pointer; transition: background 60ms; }
.data-row:hover .td { background: var(--bg-row-hover); }

/* SUBTOTALES */
.agg-row .td {
  background: rgba(16,185,129,0.06);
  border-bottom: 2px solid rgba(16,185,129,0.25);
  position: sticky; top: 36px; z-index: 4;
}
.agg-td { display: flex; flex-direction: column; justify-content: center; gap: 1px; height: 36px; }
.agg-label { font-size: 9px; color: var(--color-success); font-weight: 600; line-height: 1; }
.agg-value { font-size: 12px; color: var(--color-success); font-weight: 600; line-height: 1; }

/* SKELETON */
.skeleton-cell {
  height: 14px; border-radius: 4px;
  background: var(--border-subtle);
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%,100%{opacity:.4} 50%{opacity:.9} }

/* EMPTY */
.td-empty {
  height: 80px; text-align: center; color: var(--text-tertiary);
  font-size: 13px; border-bottom: none;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
}

@media (max-width: 768px) {
  .table-toolbar { height: auto; min-height: 44px; flex-wrap: wrap; gap: 6px; padding: 8px 10px; }
  .toolbar-right { flex-wrap: wrap; gap: 6px; }
  .os-table { font-size: 12px; }
  .th { padding: 0 8px; font-size: 10px; }
  .td { padding: 6px 8px; }
}

/* POPUP COLUMNA (global — Teleport) */
</style>

<style>
/* Sin scoped — popup usa Teleport to body */
.col-popup-overlay {
  position: fixed; inset: 0; z-index: 9999; background: transparent;
}
.col-popup {
  position: fixed; z-index: 10000;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 10px 12px; min-width: 210px;
  display: flex; flex-direction: column; gap: 8px;
  font-size: 12px; color: var(--text-primary);
  animation: popup-col-in 100ms ease-out;
}
@keyframes popup-col-in {
  from { opacity: 0; transform: translateY(-3px); }
  to   { opacity: 1; transform: none; }
}
.cp-section { display: flex; flex-direction: column; gap: 5px; }
.cp-label   { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); }
.cp-filter-row { display: flex; gap: 4px; }
.cp-select {
  flex: 1; height: 26px; padding: 0 6px;
  border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  background: var(--bg-card-hover); color: var(--text-primary);
  font-size: 12px; font-family: var(--font-sans);
}
.cp-filter-inputs { display: flex; flex-direction: column; gap: 4px; }
.cp-input {
  width: 100%; height: 26px; padding: 0 8px;
  border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  background: var(--bg-card-hover); color: var(--text-primary);
  font-size: 12px; font-family: var(--font-sans);
}
.cp-input:focus, .cp-select:focus { outline: none; border-color: var(--accent); }
.cp-sort-btns { display: flex; flex-direction: column; gap: 3px; }
.cp-sort-btn {
  display: flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-sans); transition: all 80ms;
}
.cp-sort-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }
.cp-sort-btn.active { background: var(--accent-muted); border-color: var(--accent-border); color: var(--accent); }
.cp-divider { height: 1px; background: var(--border-subtle); }
.cp-agg-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; }
.cp-agg-btn {
  display: flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 6px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 11px; color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-sans); transition: all 80ms;
}
.cp-agg-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.cp-agg-btn.active { background: rgba(16,185,129,0.1); border-color: rgba(16,185,129,0.35); color: var(--color-success); }
.cp-footer { border-top: 1px solid var(--border-subtle); padding-top: 6px; }
.cp-clear-btn {
  width: 100%; height: 26px; border-radius: var(--radius-sm);
  border: none; background: transparent;
  font-size: 12px; color: var(--color-error); cursor: pointer;
  font-family: var(--font-sans); transition: background 60ms;
}
.cp-clear-btn:hover { background: var(--color-error-bg); }
</style>
