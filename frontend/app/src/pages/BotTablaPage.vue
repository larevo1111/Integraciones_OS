<template>
  <div class="btp-root" @click="closeAll">

    <!-- Loading -->
    <div v-if="loading" class="btp-center">
      <div class="btp-spinner" />
      <span class="btp-hint">Cargando tabla…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="btp-center">
      <span style="font-size:32px">⚠️</span>
      <span class="btp-hint">{{ error }}</span>
    </div>

    <!-- Contenido -->
    <template v-else>

      <!-- Header -->
      <div class="btp-header">
        <span class="btp-pregunta">{{ pregunta }}</span>
        <span class="btp-count">{{ displayRows.length }} filas</span>
      </div>

      <!-- Toolbar sticky -->
      <div class="btp-toolbar" @click.stop>

        <!-- Izquierda: badges -->
        <div class="btp-toolbar-left">
          <span v-if="activeFilterCount > 0" class="btp-badge btp-badge-filter" @click="clearAllFilters">
            ⚡ {{ activeFilterCount }} ✕
          </span>
          <span v-if="activeAggregateCount > 0" class="btp-badge btp-badge-agg">
            Σ {{ activeAggregateCount }}
          </span>
          <span v-if="groupByKey" class="btp-badge btp-badge-group" @click="groupByKey = null">
            G {{ labelOf(groupByKey) }} ✕
          </span>
        </div>

        <!-- Derecha: botones -->
        <div class="btp-toolbar-right">

          <!-- Campos -->
          <div class="btp-btn-wrap" ref="fieldsRef">
            <button class="btp-btn" @click.stop="showFields = !showFields; showExport = false">
              ⊞ Campos
            </button>
            <div v-if="showFields" class="btp-popup btp-fields-popup" @click.stop>
              <div class="btp-pp-label">Columnas visibles</div>
              <div class="btp-fields-pills">
                <button
                  v-for="col in localColumns"
                  :key="col.key"
                  class="btp-pill"
                  :class="{ active: col.visible }"
                  @click="col.visible = !col.visible"
                >{{ col.label }}</button>
              </div>
              <div class="btp-pp-footer">
                <button class="btp-pp-action" @click="showAll">Todos</button>
                <button class="btp-pp-action" @click="hideAll">Ninguno</button>
              </div>
            </div>
          </div>

          <!-- Exportar -->
          <div class="btp-btn-wrap" ref="exportRef">
            <button class="btp-btn" @click.stop="showExport = !showExport; showFields = false">
              ↓ Exportar
            </button>
            <div v-if="showExport" class="btp-popup btp-export-popup" @click.stop>
              <div class="btp-pp-label">Exportar como</div>
              <button class="btp-export-row" @click="doExport('csv')">
                <span class="btp-export-label">CSV</span>
                <span class="btp-export-desc">Separado por comas</span>
              </button>
              <button class="btp-export-row" @click="doExport('xlsx')">
                <span class="btp-export-label">Excel</span>
                <span class="btp-export-desc">Archivo .xlsx</span>
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- Tabla -->
      <div class="btp-table-scroll">
        <table class="btp-table">
          <thead>
            <tr>
              <th
                v-for="col in visibleColumns"
                :key="col.key"
                class="btp-th"
                :class="{
                  'btp-th-filtered': hasFilter(col.key),
                  'btp-th-sorted':   sortKey === col.key,
                  'btp-th-agg':      !!columnAggregates[col.key],
                  'btp-th-open':     colPopup === col.key,
                  'btp-th-group':    groupByKey === col.key,
                }"
                @click.stop="openColPopup(col.key, $event)"
              >
                <div class="btp-th-inner">
                  <span class="btp-th-label">{{ col.label }}</span>
                  <span v-if="sortKey === col.key" class="btp-sort-icon">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                  <span v-if="hasFilter(col.key)" class="btp-filter-dot" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <!-- Fila totales (siempre visible si hay aggs) -->
            <tr v-if="hasAggregates && sortedRows.length > 0" class="btp-agg-row">
              <td
                v-for="col in visibleColumns"
                :key="col.key"
                class="btp-td btp-agg-td"
              >
                <template v-if="columnAggregates[col.key]">
                  <span class="btp-agg-label">{{ aggIcon(columnAggregates[col.key]) }}</span>
                  <span class="btp-agg-value">{{ formatCell(computeAggregate(col.key, columnAggregates[col.key], sortedRows), col) }}</span>
                </template>
              </td>
            </tr>

            <!-- Filas normales o agrupadas -->
            <tr
              v-for="(row, idx) in displayRows"
              :key="idx"
              class="btp-data-row"
              :class="{ 'btp-group-row': groupByKey }"
            >
              <td v-for="col in visibleColumns" :key="col.key" class="btp-td">
                <span class="btp-cell">{{ groupByKey && row[col.key] === '—' ? '—' : formatCell(row[col.key], col) }}</span>
              </td>
            </tr>

            <!-- Vacío -->
            <tr v-if="displayRows.length === 0 && !loading">
              <td :colspan="visibleColumns.length" class="btp-empty">
                Sin resultados
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </template>

    <!-- Popup de columna (fuera del scroll) -->
    <Teleport to="body">
      <div v-if="colPopup" class="btp-overlay" @click="colPopup = null">
        <div class="btp-col-popup" :style="colPopupStyle" @click.stop>

          <!-- Filtrar -->
          <div class="btp-cp-section">
            <label class="btp-cp-label">Filtrar</label>
            <select
              class="btp-cp-select"
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
            <div class="btp-cp-inputs">
              <input
                class="btp-cp-input"
                :placeholder="getFilterOp(colPopup) === 'between' ? 'Desde' : 'Valor'"
                :value="getFilterVal(colPopup)"
                @input="setFilterVal(colPopup, $event.target.value)"
                @keyup.enter="colPopup = null"
                @keyup.escape="colPopup = null"
              />
              <input
                v-if="getFilterOp(colPopup) === 'between'"
                class="btp-cp-input"
                placeholder="Hasta"
                :value="getFilterVal2(colPopup)"
                @input="setFilterVal2(colPopup, $event.target.value)"
                @keyup.enter="colPopup = null"
              />
            </div>
          </div>

          <div class="btp-cp-divider" />

          <!-- Ordenar -->
          <div class="btp-cp-section">
            <label class="btp-cp-label">Ordenar</label>
            <button class="btp-cp-row" :class="{ active: sortKey === colPopup && sortDir === 'asc' }" @click="setSort(colPopup, 'asc')">
              ↑ Ascendente
            </button>
            <button class="btp-cp-row" :class="{ active: sortKey === colPopup && sortDir === 'desc' }" @click="setSort(colPopup, 'desc')">
              ↓ Descendente
            </button>
          </div>

          <!-- Subtotal (solo numéricas) -->
          <template v-if="isNumeric(colPopup)">
            <div class="btp-cp-divider" />
            <div class="btp-cp-section">
              <label class="btp-cp-label">Subtotal</label>
              <button
                v-for="agg in aggOptions"
                :key="agg.value"
                class="btp-cp-row"
                :class="{ active: columnAggregates[colPopup] === agg.value }"
                @click="toggleAggregate(colPopup, agg.value)"
              >
                <span class="btp-cp-icon">{{ agg.icon }}</span> {{ agg.label }}
              </button>
            </div>
          </template>

          <!-- Agrupar -->
          <div class="btp-cp-divider" />
          <div class="btp-cp-section">
            <label class="btp-cp-label">Agrupar</label>
            <button
              class="btp-cp-row"
              :class="{ active: groupByKey === colPopup }"
              @click="toggleGroupBy(colPopup)"
            >
              <span class="btp-cp-icon">⊞</span>
              {{ groupByKey === colPopup ? 'Desagrupar' : 'Agrupar por esta columna' }}
            </button>
          </div>

          <!-- Limpiar -->
          <template v-if="hasFilter(colPopup) || columnAggregates[colPopup] || sortKey === colPopup || groupByKey === colPopup">
            <div class="btp-cp-divider" />
            <div class="btp-cp-section">
              <button class="btp-cp-clear" @click="clearColumn(colPopup)">Limpiar todo</button>
            </div>
          </template>

        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// ── Estado ─────────────────────────────────────────────
const loading   = ref(true)
const error     = ref(null)
const pregunta  = ref('')
const allRows   = ref([])    // rows normalizados a objetos
const localColumns = ref([]) // { key, label, visible, type }

// ── Cargar datos ───────────────────────────────────────
onMounted(async () => {
  // Telegram Web App init
  const tg = window.Telegram?.WebApp
  if (tg) {
    tg.ready()
    tg.expand()
  }
  document.addEventListener('click', handleOutsideClick)

  const token = route.query.token
  if (!token) { error.value = 'Token no especificado'; loading.value = false; return }

  try {
    const res = await fetch(`/api/bot/tabla?token=${token}`)
    const data = await res.json()
    if (!data.ok) { error.value = data.error || 'Error al cargar la tabla'; loading.value = false; return }

    pregunta.value = data.pregunta || ''

    // Normalizar columnas
    const cols = data.columnas || []
    localColumns.value = cols.map(c => ({
      key:     c,
      label:   c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      visible: true,
      type:    'text'  // se actualiza tras cargar filas
    }))

    // Normalizar filas (array de arrays o array de objetos)
    const filas = data.filas || []
    allRows.value = filas.map(f => {
      if (Array.isArray(f)) {
        const obj = {}
        cols.forEach((c, i) => { obj[c] = f[i] ?? null })
        return obj
      }
      return f
    })

    // Detectar tipos de columna con sample
    localColumns.value.forEach(col => {
      col.type = isNumericKey(col.key) ? 'number' : 'text'
    })

  } catch (e) {
    error.value = 'Error de conexión: ' + e.message
  } finally {
    loading.value = false
  }
})
onUnmounted(() => document.removeEventListener('click', handleOutsideClick))

// ── Columnas visibles ──────────────────────────────────
const visibleColumns = computed(() => localColumns.value.filter(c => c.visible))

// ── Popups toolbar ─────────────────────────────────────
const showFields = ref(false)
const showExport = ref(false)

function showAll() { localColumns.value.forEach(c => c.visible = true) }
function hideAll() { localColumns.value.forEach(c => c.visible = false) }

function closeAll() {
  showFields.value = false
  showExport.value = false
  colPopup.value = null
}
function handleOutsideClick() { closeAll() }

// ── Popup de columna ───────────────────────────────────
const colPopup      = ref(null)
const colPopupStyle = ref({})

function openColPopup(key, evt) {
  if (colPopup.value === key) { colPopup.value = null; return }
  // Posicionar popup: debajo del th en desktop, centrado en móvil
  const th = evt?.currentTarget
  if (th) {
    const rect  = th.getBoundingClientRect()
    const isMobile = window.innerWidth < 768
    if (isMobile) {
      colPopupStyle.value = {
        top:  (rect.bottom + 4) + 'px',
        left: '50%',
        transform: 'translateX(-50%)',
      }
    } else {
      colPopupStyle.value = {
        top:  (rect.bottom + 4) + 'px',
        left: Math.min(rect.left, window.innerWidth - 280) + 'px',
      }
    }
  }
  colPopup.value = key
}

// ── Filtros ────────────────────────────────────────────
const columnFilters = ref({})

function getFilterOp(key)  { return columnFilters.value[key]?.op  || 'eq' }
function getFilterVal(key) { return columnFilters.value[key]?.val || '' }
function getFilterVal2(key){ return columnFilters.value[key]?.val2 || '' }

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
function hasFilter(key) { return (columnFilters.value[key]?.val || '').trim() !== '' }
const activeFilterCount = computed(() => Object.keys(columnFilters.value).filter(k => hasFilter(k)).length)

function clearAllFilters() { columnFilters.value = {} }

const filteredRows = computed(() => {
  const keys = Object.keys(columnFilters.value).filter(k => hasFilter(k))
  if (!keys.length) return allRows.value
  return allRows.value.filter(row => keys.every(key => {
    const f = columnFilters.value[key]
    const fv = f.val.trim()
    if (!fv) return true
    const raw = row[key]
    const rawNum = parseFloat(String(raw ?? '').replace(',', '.'))
    const fNum  = parseFloat(fv)
    const val   = String(raw ?? '').toLowerCase()
    switch (f.op) {
      case 'eq':       return val === fv.toLowerCase()
      case 'contains': return val.includes(fv.toLowerCase())
      case 'gt':       return !isNaN(fNum) && !isNaN(rawNum) && rawNum > fNum
      case 'lt':       return !isNaN(fNum) && !isNaN(rawNum) && rawNum < fNum
      case 'gte':      return !isNaN(fNum) && !isNaN(rawNum) && rawNum >= fNum
      case 'lte':      return !isNaN(fNum) && !isNaN(rawNum) && rawNum <= fNum
      case 'between': {
        const fv2   = f.val2?.trim()
        const fNum2 = parseFloat(fv2)
        if (isNaN(rawNum) || isNaN(fNum)) return false
        if (!fv2 || isNaN(fNum2)) return rawNum >= fNum
        return rawNum >= fNum && rawNum <= fNum2
      }
      default: return val.includes(fv.toLowerCase())
    }
  }))
})

// ── Ordenar ────────────────────────────────────────────
const sortKey = ref('')
const sortDir = ref('asc')

function setSort(key, dir) {
  if (sortKey.value === key && sortDir.value === dir) { sortKey.value = '' }
  else { sortKey.value = key; sortDir.value = dir }
}

const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value
  return [...filteredRows.value].sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    const n  = v => parseFloat(String(v ?? '').replace(',', '.'))
    const r  = isNaN(n(av)) ? String(av ?? '').localeCompare(String(bv ?? '')) : n(av) - n(bv)
    return sortDir.value === 'asc' ? r : -r
  })
})

// ── Agregados (subtotales) ─────────────────────────────
const columnAggregates = ref({})
const aggOptions = [
  { value: 'sum', label: 'Suma',     icon: 'Σ' },
  { value: 'avg', label: 'Promedio', icon: 'x̄' },
  { value: 'max', label: 'Máximo',   icon: '↑' },
  { value: 'min', label: 'Mínimo',   icon: '↓' },
]

function toggleAggregate(key, aggType) {
  if (columnAggregates.value[key] === aggType) {
    const copy = { ...columnAggregates.value }; delete copy[key]; columnAggregates.value = copy
  } else {
    columnAggregates.value = { ...columnAggregates.value, [key]: aggType }
  }
}

const activeAggregateCount = computed(() => Object.keys(columnAggregates.value).length)
const hasAggregates        = computed(() => activeAggregateCount.value > 0)

function computeAggregate(key, aggType, rows) {
  const vals = rows.map(r => parseFloat(String(r[key] ?? '').replace(',', '.'))).filter(n => !isNaN(n))
  if (!vals.length) return null
  if (aggType === 'sum') return vals.reduce((a, b) => a + b, 0)
  if (aggType === 'avg') return vals.reduce((a, b) => a + b, 0) / vals.length
  if (aggType === 'max') return Math.max(...vals)
  if (aggType === 'min') return Math.min(...vals)
  return null
}

function aggIcon(t) { return { sum: 'Σ', avg: 'x̄', max: '↑', min: '↓' }[t] || '' }

// ── Agrupar ────────────────────────────────────────────
const groupByKey = ref(null)

function toggleGroupBy(key) {
  groupByKey.value = groupByKey.value === key ? null : key
  colPopup.value = null
}

const groupedRows = computed(() => {
  if (!groupByKey.value) return null
  const groups = {}
  for (const row of sortedRows.value) {
    const val = String(row[groupByKey.value] ?? '—')
    if (!groups[val]) groups[val] = []
    groups[val].push(row)
  }
  return Object.entries(groups).map(([groupVal, rows]) => {
    const out = {}
    for (const col of localColumns.value) {
      if (col.key === groupByKey.value) {
        out[col.key] = groupVal
      } else if (columnAggregates.value[col.key]) {
        out[col.key] = computeAggregate(col.key, columnAggregates.value[col.key], rows)
      } else {
        out[col.key] = '—'
      }
    }
    out._groupCount = rows.length
    return out
  })
})

const displayRows = computed(() => groupedRows.value || sortedRows.value)

// ── Detectar numérico ──────────────────────────────────
function isNumericKey(key) {
  const sample = allRows.value.slice(0, 8)
  if (!sample.length) return false
  return sample.every(r => {
    const v = r[key]
    if (v === null || v === undefined || v === '') return true
    const s = String(v).trim()
    return s !== '' && !isNaN(Number(s))
  })
}
function isNumeric(key) {
  const col = localColumns.value.find(c => c.key === key)
  if (col?.type === 'number') return true
  return isNumericKey(key)
}

// ── Formato de celda ───────────────────────────────────
function fmtNum(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  const decimals = (Math.abs(n) - Math.floor(Math.abs(n))) > 0.0005
    ? Math.min(String(n.toFixed(3)).replace(/0+$/, '').split('.')[1]?.length || 0, 3)
    : 0
  return n.toLocaleString('de-DE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function formatCell(val, col) {
  if (val === null || val === undefined || val === '—') return val === '—' ? '—' : '—'
  if (col && isNumeric(col.key)) {
    const n = parseFloat(String(val).replace(',', '.'))
    if (!isNaN(n)) return fmtNum(n)
  }
  return val
}

function labelOf(key) {
  return localColumns.value.find(c => c.key === key)?.label || key
}

// ── Limpiar columna ────────────────────────────────────
function clearColumn(key) {
  const cf = { ...columnFilters.value };   delete cf[key];  columnFilters.value = cf
  const ca = { ...columnAggregates.value }; delete ca[key]; columnAggregates.value = ca
  if (sortKey.value === key) sortKey.value = ''
  if (groupByKey.value === key) groupByKey.value = null
  colPopup.value = null
}

// ── Exportar client-side ───────────────────────────────
async function doExport(format) {
  showExport.value = false
  const visibleKeys = visibleColumns.value.map(c => c.key)
  const header = visibleKeys.map(k => labelOf(k))
  const rows   = displayRows.value.map(r => visibleKeys.map(k => {
    const v = r[k]
    if (v === null || v === undefined) return ''
    return v
  }))

  if (format === 'csv') {
    const lines = [header, ...rows].map(row =>
      row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')
    ).join('\n')
    const blob = new Blob(['\uFEFF' + lines], { type: 'text/csv;charset=utf-8;' })
    triggerDownload(blob, 'tabla.csv')
  }

  if (format === 'xlsx') {
    const XLSX = await import('xlsx')
    const ws = XLSX.utils.aoa_to_sheet([header, ...rows])
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Datos')
    XLSX.writeFile(wb, 'tabla.xlsx')
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a   = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>

<style scoped>
/* ── ROOT ── */
.btp-root {
  min-height: 100vh;
  background: var(--bg-app);
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
}

/* ── CENTRO (loading / error) ── */
.btp-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
}
.btp-hint { font-size: 14px; color: var(--text-secondary); text-align: center; }
.btp-spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--border-default);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: btp-spin 0.8s linear infinite;
}
@keyframes btp-spin { to { transform: rotate(360deg); } }

/* ── HEADER ── */
.btp-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px 8px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
}
.btp-pregunta {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
  line-height: 1.4;
}
.btp-count {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── TOOLBAR ── */
.btp-toolbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-toolbar);
  border-bottom: 1px solid var(--border-default);
}
.btp-toolbar-left  { display: flex; align-items: center; gap: 5px; flex: 1; flex-wrap: wrap; }
.btp-toolbar-right { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }

/* Badges */
.btp-badge {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 500;
  padding: 2px 8px; border-radius: var(--radius-full);
  cursor: pointer; user-select: none;
  transition: all 80ms;
}
.btp-badge-filter {
  color: var(--accent); background: var(--accent-muted);
  border: 1px solid var(--accent-border);
}
.btp-badge-agg {
  color: var(--color-success); background: rgba(22,163,74,0.1);
  border: 1px solid rgba(22,163,74,0.25);
}
.btp-badge-group {
  color: #d97706; background: rgba(217,119,6,0.1);
  border: 1px solid rgba(217,119,6,0.25);
}

/* Botones toolbar */
.btp-btn-wrap { position: relative; }
.btp-btn {
  display: inline-flex; align-items: center; gap: 4px;
  height: 32px; padding: 0 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 13px; font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms, color 80ms;
  white-space: nowrap;
  font-family: var(--font-sans);
  min-height: 44px; /* touch target */
}
.btp-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Popups de toolbar */
.btp-popup {
  position: absolute; top: calc(100% + 6px); right: 0;
  background: var(--bg-modal);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 200;
  min-width: 220px;
  animation: btp-popup-in 120ms ease-out;
  overflow: hidden;
}
@keyframes btp-popup-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.btp-pp-label {
  padding: 10px 14px 6px;
  font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--text-tertiary);
}
.btp-pp-footer {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 10px 10px;
  border-top: 1px solid var(--border-subtle);
}
.btp-pp-action {
  flex: 1; height: 28px; padding: 0 8px;
  border-radius: var(--radius-sm);
  border: none; background: transparent;
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans);
  transition: background 60ms;
}
.btp-pp-action:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Campos pills */
.btp-fields-pills {
  display: flex; flex-wrap: wrap; gap: 5px;
  padding: 4px 12px 8px;
  max-height: 200px; overflow-y: auto;
}
.btp-pill {
  display: inline-flex; align-items: center;
  height: 28px; padding: 0 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-default);
  background: transparent;
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans);
  transition: all 80ms;
}
.btp-pill:hover { border-color: var(--border-strong); color: var(--text-primary); }
.btp-pill.active { background: var(--accent-muted); border-color: var(--accent-border); color: var(--accent); font-weight: 500; }

/* Exportar */
.btp-export-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; width: 100%;
  border: none; background: transparent;
  cursor: pointer; font-family: var(--font-sans);
  transition: background 80ms;
}
.btp-export-row:hover { background: var(--bg-card-hover); }
.btp-export-label { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.btp-export-desc  { font-size: 11px; color: var(--text-tertiary); }

/* ── TABLA ── */
.btp-table-scroll { overflow-x: auto; flex: 1; }
.btp-table {
  width: 100%; border-collapse: collapse;
  font-size: 13px;
}

.btp-th {
  text-align: left;
  padding: 0 12px;
  height: 36px;
  font-size: 11px; font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg-app);
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
  cursor: pointer; user-select: none;
  position: sticky; top: 0; z-index: 5;
  transition: color 80ms;
}
.btp-th:hover { color: var(--text-secondary); }
.btp-th-filtered { color: var(--accent); }
.btp-th-sorted   { color: var(--text-primary); }
.btp-th-agg      { border-bottom-color: var(--color-success); }
.btp-th-open     { color: var(--accent); background: var(--accent-muted); }
.btp-th-group    { color: #d97706; background: rgba(217,119,6,0.08); }

.btp-th-inner { display: flex; align-items: center; gap: 4px; }
.btp-th-label { flex: 1; }
.btp-sort-icon { font-size: 12px; color: var(--accent); }
.btp-filter-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }

/* Fila totales */
.btp-agg-row { background: rgba(22,163,74,0.04); }
.btp-agg-td {
  font-weight: 600;
  border-bottom: 2px solid rgba(22,163,74,0.25);
  position: sticky; top: 36px; z-index: 4;
  background: rgba(22,163,74,0.06);
}
.btp-agg-label { font-size: 10px; color: var(--color-success); margin-right: 4px; font-weight: 700; }
.btp-agg-value { font-size: 13px; }

/* Filas datos */
.btp-data-row { transition: background 60ms; }
.btp-data-row:hover { background: var(--bg-row-hover); }
.btp-group-row { font-weight: 500; }

.btp-td {
  padding: 0 12px;
  height: 40px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  white-space: nowrap;
  max-width: 220px; overflow: hidden; text-overflow: ellipsis;
}
.btp-cell { font-size: 13px; }

/* Vacío */
.btp-empty { padding: 48px 16px; text-align: center; color: var(--text-tertiary); font-size: 14px; }
</style>

<style>
/* ── POPUP COLUMNA (Teleport a body — NO scoped) ── */
.btp-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}
.btp-col-popup {
  position: fixed;
  min-width: 220px;
  max-width: 300px;
  background: var(--bg-modal, #fff);
  border: 1px solid var(--border-strong, #ccc);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
  z-index: 10000;
  animation: btp-popup-in 120ms ease-out;
  padding: 8px 0;
  max-height: 90vh;
  overflow-y: auto;
}
@keyframes btp-popup-in {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.btp-cp-section { padding: 4px 12px; }
.btp-cp-label {
  font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--text-tertiary, #888);
  display: block; margin-bottom: 4px;
}
.btp-cp-divider { height: 1px; background: var(--border-subtle, #eee); margin: 6px 0; }
.btp-cp-select {
  width: 100%; height: 36px;
  border-radius: 6px;
  border: 1px solid var(--border-default, #ddd);
  background: var(--bg-input, #fff);
  font-size: 13px; color: var(--text-primary, #1a1a1a);
  padding: 0 8px; outline: none;
  font-family: inherit; cursor: pointer;
  margin-bottom: 6px;
}
.btp-cp-select:focus { border-color: var(--accent, #5e6ad2); }
.btp-cp-inputs { display: flex; flex-direction: column; gap: 4px; }
.btp-cp-input {
  width: 100%; height: 36px;
  border-radius: 6px;
  border: 1px solid var(--border-default, #ddd);
  background: var(--bg-input, #fff);
  font-size: 13px; color: var(--text-primary, #1a1a1a);
  padding: 0 10px; outline: none;
  font-family: inherit; box-sizing: border-box;
}
.btp-cp-input:focus { border-color: var(--accent, #5e6ad2); }
.btp-cp-row {
  display: flex; align-items: center; gap: 8px;
  width: 100%; min-height: 40px; padding: 0 8px;
  border-radius: 6px;
  border: none; background: transparent;
  font-size: 13px; color: var(--text-secondary, #666);
  cursor: pointer; font-family: inherit;
  transition: all 60ms; text-align: left;
}
.btp-cp-row:hover { background: var(--bg-card-hover, #f5f5f5); color: var(--text-primary, #1a1a1a); }
.btp-cp-row.active { background: var(--accent-muted, rgba(94,106,210,0.08)); color: var(--accent, #5e6ad2); font-weight: 500; }
.btp-cp-icon { font-weight: 700; min-width: 16px; text-align: center; }
.btp-cp-clear {
  width: 100%; min-height: 36px; border: none; background: transparent;
  font-size: 12px; color: var(--text-tertiary, #999); cursor: pointer;
  border-radius: 6px; font-family: inherit; transition: all 60ms;
}
.btp-cp-clear:hover { background: var(--bg-card-hover, #f5f5f5); color: var(--color-error, #dc2626); }
</style>
