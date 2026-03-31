<template>
  <div class="inv-app" :class="{ 'panel-open': panelAbierto }">

    <!-- SIDE PANEL RETRÁCTIL — Inventarios -->
    <aside class="inv-panel" :class="{ open: panelAbierto }">
      <div class="inv-panel-header">
        <span class="inv-panel-title">Inventarios</span>
        <button class="action-btn" @click="panelAbierto = false"><span class="material-icons" style="font-size:18px">chevron_left</span></button>
      </div>
      <div class="inv-panel-list">
        <div v-for="f in fechasInventario" :key="f.fecha_inventario" class="inv-panel-item" :class="{ active: FECHA === f.fecha_inventario }" @click="cambiarFecha(f.fecha_inventario)">
          <div class="inv-panel-item-fecha">{{ formatFechaCorta(f.fecha_inventario) }}</div>
          <div class="inv-panel-item-stats">
            <span>{{ f.inventariables }} artículos</span>
            <span class="inv-panel-item-pct">{{ f.contados }}/{{ f.inventariables }}</span>
          </div>
        </div>
        <div v-if="!fechasInventario.length" class="inv-panel-empty">Sin inventarios</div>
      </div>
    </aside>

    <!-- MAIN CONTENT -->
    <div class="inv-content">

      <!-- HEADER -->
      <div class="inv-header">
        <div class="inv-header-left">
          <button v-if="!panelAbierto" class="inv-panel-toggle" @click="panelAbierto = true" title="Inventarios">
            <span class="material-icons" style="font-size:18px">menu</span>
          </button>
          <div class="inv-avatar">{{ iniciales }}</div>
          <div class="inv-user-info">
            <span class="inv-user-name">{{ usuario }}</span>
            <span class="inv-title">Inventario {{ fechaDisplay }}</span>
          </div>
        </div>
        <div class="inv-header-right">
          <div class="inv-clock">{{ reloj }}</div>
          <div class="inv-progress-wrap">
            <div class="inv-progress-track">
              <div class="inv-progress-ok" :style="{ width: pctOk + '%' }"></div>
              <div class="inv-progress-diff" :style="{ width: pctDiff + '%' }"></div>
            </div>
            <span class="inv-progress-text">{{ resumen.contados || 0 }} / {{ resumen.total || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- TOOLBAR -->
      <div class="inv-toolbar">
        <div class="inv-search-box">
          <span class="material-icons inv-search-icon">search</span>
          <input v-model="busqueda" class="inv-search-input" type="text" placeholder="Buscar por nombre o código..." @input="debounceSearch">
        </div>
        <button class="inv-btn-scan">
          <span class="material-icons" style="font-size:16px">qr_code_scanner</span>
          Escanear
        </button>
      </div>

      <!-- FILTROS + BODEGAS -->
      <div class="inv-filters-row">
        <!-- Filtros estado -->
        <button v-for="f in filtros" :key="f.key" class="inv-pill" :class="{ active: filtroActivo === f.key }" @click="filtroActivo = f.key; cargarArticulos()">
          {{ f.label }}<span class="inv-pill-count">{{ f.count }}</span>
        </button>

        <span class="inv-separator"></span>

        <!-- Bodegas label + chips -->
        <span class="inv-bodegas-label">Bodegas</span>
        <button class="inv-pill inv-pill-bodega" :class="{ active: bodegaActiva === null }" @click="seleccionarBodega(null)">
          Todas
        </button>
        <button
          v-for="b in bodegasConStock"
          :key="b.bodega"
          class="inv-pill inv-pill-bodega"
          :class="{ active: bodegaActiva === b.bodega }"
          @click="seleccionarBodega(b.bodega)"
        >
          {{ b.bodega }}<span class="inv-pill-count">{{ b.total }}</span>
        </button>

        <!-- + para más bodegas -->
        <div class="inv-bodega-add-wrap">
          <button class="inv-bodega-add-btn" @click.stop="mostrarListaBodegas = !mostrarListaBodegas" title="Más bodegas">
            <span class="material-icons" style="font-size:14px">add</span>
          </button>
          <div v-if="mostrarListaBodegas" class="inv-bodega-dropdown" @click.stop>
            <div class="inv-bodega-dropdown-title">Otras bodegas</div>
            <div v-for="b in bodegasSinStock" :key="b.bodega" class="inv-bodega-dropdown-item" @click="seleccionarBodega(b.bodega); mostrarListaBodegas = false">
              {{ b.bodega }}
            </div>
            <div v-if="!bodegasSinStock.length" class="inv-bodega-dropdown-empty">Todas las bodegas con stock ya están visibles</div>
          </div>
        </div>
      </div>

    <!-- TABLA -->
    <div class="inv-table-container">
      <table class="inv-table">
        <colgroup>
          <col style="width:32px">
          <col style="width:60px">
          <col>
          <col style="width:200px">
          <col style="width:270px">
        </colgroup>
        <thead>
          <tr>
            <th class="th th-nosort"></th>
            <th v-for="col in columns" :key="col.key" class="th"
                :class="{ 'th-sorted': sortKey === col.key, 'th-filtered': hasFilter(col.key), 'th-popup-open': colPopup === col.key }"
                @click.stop="openColPopup(col.key, $event)">
              <div class="th-inner">
                <span class="th-label">{{ col.label }}</span>
                <span v-if="sortKey === col.key" class="material-icons sort-icon">{{ sortDir === 'asc' ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}</span>
                <span v-if="hasFilter(col.key)" class="th-filter-dot"></span>
              </div>
            </th>
            <th class="th th-nosort th-conteo">Conteo</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in sortedRows" :key="a.id" :class="clasesFila(a)">
            <td class="td td-center"><span class="status-dot" :class="claseDot(a)"></span></td>
            <td class="td cell-id">{{ a.id_effi }}</td>
            <td class="td cell-articulo">{{ a.nombre }}</td>
            <td class="td cell-categoria">{{ a.categoria }}</td>
            <td class="td">
              <div class="conteo-cell">
                <div class="teorico-block">
                  <span class="teorico-label">Teórico</span>
                  <span class="teorico-value">{{ fmtNum(a.inventario_teorico) }}</span>
                </div>
                <input class="count-input" :class="claseInput(a)" type="number" inputmode="numeric" placeholder="—" :value="a.inventario_fisico" @change="onConteo(a, $event)">
                <span class="diff-badge" :class="claseBadge(a)">{{ textoBadge(a) }}</span>
                <button class="action-btn" :class="{ 'has-note': a.notas }" @click.stop="abrirNotas(a)">
                  <span class="material-icons" style="font-size:16px">more_vert</span>
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!articulos.length && !cargando">
            <td colspan="5" class="td td-empty">
              <span class="material-icons" style="font-size:24px;opacity:0.3">inbox</span>
              <span>{{ busqueda ? 'Sin resultados para "' + busqueda + '"' : 'No hay artículos' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    </div><!-- /inv-content -->

    <!-- FAB -->
    <button class="inv-fab" @click="mostrarAgregar = true"><span class="material-icons">add</span></button>

    <!-- POPUP COLUMNA — idéntico a GestionTable -->
    <Teleport to="body">
      <div v-if="colPopup" class="col-popup-overlay" @click="colPopup = null">
        <div class="col-popup" :style="colPopupStyle" @click.stop>
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
              <input ref="colFilterInput" class="cp-input" :placeholder="getFilterOp(colPopup) === 'between' ? 'Desde' : 'Valor'" :value="getFilterVal(colPopup)" @input="setFilterVal(colPopup, $event.target.value)" @keyup.enter="colPopup = null" @keyup.escape="colPopup = null">
              <input v-if="getFilterOp(colPopup) === 'between'" class="cp-input" placeholder="Hasta" :value="getFilterVal2(colPopup)" @input="setFilterVal2(colPopup, $event.target.value)">
            </div>
          </div>
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
          <div v-if="hasFilter(colPopup) || sortKey === colPopup" class="cp-footer">
            <button class="cp-clear-btn" @click="clearColumn(colPopup)">Limpiar todo</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- MODAL AGREGAR -->
    <div v-if="mostrarAgregar" class="inv-overlay" @click.self="mostrarAgregar = false">
      <div class="inv-modal">
        <div class="inv-modal-header">
          <span>Agregar artículo{{ bodegaActiva ? ' a ' + bodegaActiva : '' }}</span>
          <button class="action-btn" @click="mostrarAgregar = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <input v-model="busquedaAgregar" class="inv-modal-search" type="text" placeholder="Buscar artículo por nombre o código..." @input="buscarParaAgregar">
          <div class="inv-modal-results">
            <div v-for="r in resultadosAgregar" :key="r.id" class="inv-modal-result-item" @click="agregarArticulo(r)">
              <span class="inv-modal-result-name">{{ r.nombre }}</span>
              <span class="inv-modal-result-id">{{ r.id }}</span>
            </div>
            <div v-if="busquedaAgregar && !resultadosAgregar.length" class="inv-modal-empty">Sin resultados</div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL NOTAS -->
    <div v-if="mostrarNotas" class="inv-overlay" @click.self="cerrarNotas">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header">
          <span>Nota — {{ articuloNota?.nombre }}</span>
          <button class="action-btn" @click="cerrarNotas"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <textarea v-model="textoNota" class="inv-nota-textarea" rows="4" placeholder="Observaciones del conteo..."></textarea>
          <button class="inv-btn-primary" @click="guardarNota">Guardar nota</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const API = window.location.origin
const FECHA = ref('2026-03-30')

const usuario = ref('Santiago')
const iniciales = ref('SS')
const bodegas = ref([])
const bodegaActiva = ref('Principal')
const articulos = ref([])
const resumen = ref({})
const busqueda = ref('')
const filtroActivo = ref(null)
const cargando = ref(false)
const reloj = ref('')
const mostrarAgregar = ref(false)
const busquedaAgregar = ref('')
const resultadosAgregar = ref([])
const mostrarNotas = ref(false)
const articuloNota = ref(null)
const textoNota = ref('')
const panelAbierto = ref(false)
const fechasInventario = ref([])
const mostrarListaBodegas = ref(false)

// Columns definition
const columns = [
  { key: 'id_effi', label: 'ID' },
  { key: 'nombre', label: 'Artículo' },
  { key: 'categoria', label: 'Categoría' },
]

// ── Reloj ──
let clockInterval
function actualizarReloj() {
  const now = new Date()
  const dias = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']
  const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  const h = String(now.getHours()).padStart(2,'0')
  const m = String(now.getMinutes()).padStart(2,'0')
  const s = String(now.getSeconds()).padStart(2,'0')
  reloj.value = `${dias[now.getDay()]} ${now.getDate()} ${meses[now.getMonth()]} ${now.getFullYear()} · ${h}:${m}:${s}`
}

const fechaDisplay = computed(() => {
  const d = new Date(FECHA.value + 'T12:00:00')
  const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
  return `${meses[d.getMonth()]} ${d.getDate()} ${d.getFullYear()}`
})

function formatFechaCorta(f) {
  const d = new Date(f + 'T12:00:00')
  const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  return `${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()}`
}

function cambiarFecha(f) {
  FECHA.value = f
  bodegaActiva.value = 'Principal'
  filtroActivo.value = null
  busqueda.value = ''
  columnFilters.value = {}
  sortKey.value = ''
  cargarBodegas(); cargarResumen(); cargarArticulos()
  panelAbierto.value = false
}

// ── Bodegas ──
const bodegasConStock = computed(() => bodegas.value.filter(b => b.total > 0))
const bodegasSinStock = computed(() => bodegas.value.filter(b => b.total === 0))

// ── Filtros estado ──
const filtros = computed(() => [
  { key: null, label: 'Todos', count: resumen.value.total || 0 },
  { key: 'pendientes', label: 'Pendientes', count: resumen.value.pendientes || 0 },
  { key: 'contados', label: 'Contados', count: resumen.value.contados || 0 },
  { key: 'diferencias', label: 'Diferencias', count: resumen.value.con_diferencia || 0 },
])

const pctOk = computed(() => resumen.value.total ? ((resumen.value.ok || 0) / resumen.value.total) * 100 : 0)
const pctDiff = computed(() => resumen.value.total ? ((resumen.value.con_diferencia || 0) / resumen.value.total) * 100 : 0)

// ── Filtros por columna (patrón GestionTable) ──
const columnFilters = ref({})
function getFilterOp(key) { return columnFilters.value[key]?.op || 'eq' }
function getFilterVal(key) { return columnFilters.value[key]?.val || '' }
function getFilterVal2(key) { return columnFilters.value[key]?.val2 || '' }
function setFilterOp(key, op) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), op } } }
function setFilterVal(key, val) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val } } }
function setFilterVal2(key, val2) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val2 } } }
function hasFilter(key) { return !!(columnFilters.value[key]?.val?.trim()) }

// ── Filtrado local ──
const filteredRows = computed(() => {
  const keys = Object.keys(columnFilters.value).filter(k => hasFilter(k))
  if (!keys.length) return articulos.value
  return articulos.value.filter(row => keys.every(key => {
    const f = columnFilters.value[key]
    const fv = f.val.trim()
    const raw = row[key]
    const n = v => parseFloat(String(v).replace(',', '.'))
    const val = String(raw ?? '').toLowerCase()
    switch (f.op) {
      case 'eq': return val === fv.toLowerCase()
      case 'contains': return val.includes(fv.toLowerCase())
      case 'gt': return !isNaN(n(raw)) && n(raw) > n(fv)
      case 'lt': return !isNaN(n(raw)) && n(raw) < n(fv)
      case 'gte': return !isNaN(n(raw)) && n(raw) >= n(fv)
      case 'lte': return !isNaN(n(raw)) && n(raw) <= n(fv)
      case 'between': { const fv2 = f.val2?.trim(); return !isNaN(n(raw)) && n(raw) >= n(fv) && (!fv2 || n(raw) <= n(fv2)) }
      default: return val.includes(fv.toLowerCase())
    }
  }))
})

// ── Ordenamiento ──
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
    const n = v => parseFloat(String(v).replace(',', '.'))
    const r = isNaN(n(av)) ? String(av ?? '').localeCompare(String(bv ?? '')) : n(av) - n(bv)
    return sortDir.value === 'asc' ? r : -r
  })
})

// ── Popup columna ──
const colPopup = ref(null)
const colPopupStyle = ref({})
const colFilterInput = ref(null)

function openColPopup(key, event) {
  if (colPopup.value === key) { colPopup.value = null; return }
  const th = event.currentTarget
  const rect = th.getBoundingClientRect()
  colPopupStyle.value = {
    top: (rect.bottom + 4) + 'px',
    left: Math.max(4, Math.min(rect.left, window.innerWidth - 230)) + 'px',
  }
  colPopup.value = key
  nextTick(() => { if (colFilterInput.value) colFilterInput.value.focus() })
}

function clearColumn(key) {
  const cf = { ...columnFilters.value }; delete cf[key]; columnFilters.value = cf
  if (sortKey.value === key) sortKey.value = ''
  colPopup.value = null
}

// ── API ──
async function fetchApi(path) { return (await fetch(API + path)).json() }

async function cargarFechas() { fechasInventario.value = await fetchApi('/api/inventario/fechas') }
async function cargarBodegas() { bodegas.value = await fetchApi(`/api/inventario/bodegas/todas?fecha=${FECHA.value}`) }
async function cargarResumen() {
  let url = `/api/inventario/resumen?fecha=${FECHA.value}`
  if (bodegaActiva.value) url += `&bodega=${encodeURIComponent(bodegaActiva.value)}`
  resumen.value = await fetchApi(url)
}

async function cargarArticulos() {
  cargando.value = true
  let url = `/api/inventario/articulos?fecha=${FECHA.value}`
  if (bodegaActiva.value) url += `&bodega=${encodeURIComponent(bodegaActiva.value)}`
  if (filtroActivo.value) url += `&filtro=${filtroActivo.value}`
  if (busqueda.value) url += `&busqueda=${encodeURIComponent(busqueda.value)}`
  articulos.value = await fetchApi(url)
  cargando.value = false
}

function seleccionarBodega(nombre) {
  bodegaActiva.value = nombre
  filtroActivo.value = null
  busqueda.value = ''
  columnFilters.value = {}
  sortKey.value = ''
  cargarArticulos()
  cargarResumen()
}

let searchTimeout
function debounceSearch() { clearTimeout(searchTimeout); searchTimeout = setTimeout(() => cargarArticulos(), 300) }

// ── Conteo ──
async function onConteo(articulo, event) {
  const valor = parseFloat(event.target.value)
  if (isNaN(valor)) return
  const res = await fetch(API + `/api/inventario/articulos/${articulo.id}/conteo`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inventario_fisico: valor, contado_por: usuario.value })
  }).then(r => r.json())
  articulo.inventario_fisico = valor
  articulo.diferencia = res.diferencia
  articulo.estado = 'contado'
  cargarResumen()
  cargarBodegas()
}

// ── Notas ──
function abrirNotas(a) { articuloNota.value = a; textoNota.value = a.notas || ''; mostrarNotas.value = true }
function cerrarNotas() { mostrarNotas.value = false; articuloNota.value = null }
async function guardarNota() {
  if (!articuloNota.value) return
  await fetch(API + `/api/inventario/articulos/${articuloNota.value.id}/nota`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notas: textoNota.value })
  })
  articuloNota.value.notas = textoNota.value
  cerrarNotas()
}

// ── Agregar ──
let agregarTimeout
function buscarParaAgregar() {
  clearTimeout(agregarTimeout)
  agregarTimeout = setTimeout(async () => {
    if (!busquedaAgregar.value || busquedaAgregar.value.length < 2) { resultadosAgregar.value = []; return }
    resultadosAgregar.value = await fetchApi(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busquedaAgregar.value)}`)
  }, 300)
}
async function agregarArticulo(art) {
  await fetch(API + `/api/inventario/articulos/agregar`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, bodega: bodegaActiva.value || 'Principal', id_effi: art.id, contado_por: usuario.value })
  })
  mostrarAgregar.value = false; busquedaAgregar.value = ''; resultadosAgregar.value = []
  cargarArticulos(); cargarResumen(); cargarBodegas()
}

// ── Helpers visuales ──
function fmtNum(n) { return n != null ? Math.round(n) : '—' }
function clasesFila(a) { return a.estado === 'contado' ? (a.diferencia === 0 ? 'row-ok' : 'row-diff') : '' }
function claseDot(a) { if (a.estado === 'pendiente') return 'dot-pending'; if (a.diferencia === 0) return 'dot-ok'; return Math.abs(a.diferencia) >= 10 ? 'dot-critical' : 'dot-warning' }
function claseInput(a) { if (a.inventario_fisico == null) return ''; if (a.diferencia === 0) return 'input-ok'; return Math.abs(a.diferencia) >= 10 ? 'input-critical' : 'input-warning' }
function claseBadge(a) { if (a.estado === 'pendiente') return 'badge-empty'; if (a.diferencia === 0) return 'badge-ok'; return Math.abs(a.diferencia) >= 10 ? 'badge-error' : 'badge-warning' }
function textoBadge(a) { if (a.estado === 'pendiente') return '—'; if (a.diferencia === 0) return 'OK'; return (a.diferencia > 0 ? '+' : '') + Math.round(a.diferencia) }

onMounted(async () => {
  actualizarReloj(); clockInterval = setInterval(actualizarReloj, 1000)
  document.addEventListener('click', () => { mostrarListaBodegas.value = false })
  await cargarFechas(); await cargarBodegas(); await cargarResumen(); await cargarArticulos()
})
onUnmounted(() => clearInterval(clockInterval))
</script>

<style scoped>
.inv-app { display: flex; height: 100vh; overflow: hidden; }
.inv-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* SIDE PANEL */
.inv-panel { width: 0; overflow: hidden; background: var(--bg-sidebar); border-right: 1px solid var(--border-default); display: flex; flex-direction: column; transition: width 0.2s ease; flex-shrink: 0; }
.inv-panel.open { width: 240px; }
.inv-panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-subtle); }
.inv-panel-title { font-size: 13px; font-weight: 600; }
.inv-panel-list { flex: 1; overflow-y: auto; padding: 6px; }
.inv-panel-item { padding: 8px 10px; border-radius: 4px; cursor: pointer; margin-bottom: 2px; transition: background 0.08s; }
.inv-panel-item:hover { background: rgba(255,255,255,0.04); }
.inv-panel-item.active { background: var(--accent-muted); }
.inv-panel-item-fecha { font-size: 13px; font-weight: 500; }
.inv-panel-item.active .inv-panel-item-fecha { color: var(--accent); }
.inv-panel-item-stats { font-size: 11px; color: var(--text-tertiary); display: flex; justify-content: space-between; margin-top: 2px; }
.inv-panel-item-pct { font-family: 'Fragment Mono', monospace; }
.inv-panel-empty { text-align: center; color: var(--text-tertiary); padding: 24px; font-size: 12px; }
.inv-panel-toggle { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-secondary); cursor: pointer; border-radius: 4px; margin-right: 4px; }
.inv-panel-toggle:hover { background: rgba(255,255,255,0.06); }

/* HEADER */
.inv-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-default); }
.inv-header-left { display: flex; align-items: center; gap: 10px; }
.inv-avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--accent-muted); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; }
.inv-user-info { display: flex; flex-direction: column; }
.inv-user-name { font-size: 13px; font-weight: 500; }
.inv-title { font-size: 12px; color: var(--accent); font-weight: 500; }
.inv-header-right { display: flex; align-items: center; gap: 16px; }
.inv-clock { font-size: 11px; color: var(--text-tertiary); font-family: 'Fragment Mono', 'JetBrains Mono', monospace; }
.inv-progress-wrap { display: flex; align-items: center; gap: 10px; width: 240px; }
.inv-progress-track { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; display: flex; }
.inv-progress-ok { background: var(--color-ok); height: 100%; transition: width 0.3s ease; }
.inv-progress-diff { background: var(--color-warning); height: 100%; transition: width 0.3s ease; }
.inv-progress-text { font-size: 12px; color: var(--text-secondary); font-family: 'Fragment Mono', monospace; white-space: nowrap; }

/* TOOLBAR */
.inv-toolbar { padding: 8px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border-subtle); }
.inv-search-box { flex: 1; display: flex; align-items: center; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: 4px; padding: 0 10px; height: 32px; gap: 8px; }
.inv-search-box:focus-within { border-color: var(--accent); }
.inv-search-icon { font-size: 18px; color: var(--text-tertiary); }
.inv-search-input { flex: 1; background: none; border: none; color: var(--text-primary); font-size: 13px; outline: none; }
.inv-search-input::placeholder { color: var(--text-tertiary); }
.inv-btn-scan { height: 32px; padding: 0 12px; background: var(--accent-muted); border: 1px solid var(--accent-border); border-radius: 4px; color: var(--accent); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.inv-btn-scan:hover { background: rgba(0,200,83,0.18); }

/* FILTROS + BODEGAS */
.inv-filters-row { padding: 6px 16px; display: flex; align-items: center; gap: 4px; border-bottom: 1px solid var(--border-subtle); flex-wrap: wrap; }
.inv-pill { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; background: transparent; color: var(--text-secondary); transition: all 0.1s ease-out; white-space: nowrap; }
.inv-pill:hover { background: rgba(255,255,255,0.04); }
.inv-pill.active { background: var(--accent-muted); color: var(--accent); border-color: var(--accent-border); }
.inv-pill-count { font-size: 11px; opacity: 0.7; margin-left: 4px; font-family: 'Fragment Mono', monospace; }
.inv-separator { width: 1px; height: 20px; background: var(--border-strong); margin: 0 6px; flex-shrink: 0; }
.inv-bodegas-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-tertiary); margin-right: 2px; }
.inv-pill-bodega { }
.inv-bodega-add-wrap { position: relative; }
.inv-bodega-add-btn { width: 24px; height: 24px; border-radius: 12px; border: 1px dashed var(--border-strong); background: transparent; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.1s; }
.inv-bodega-add-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-muted); }
.inv-bodega-dropdown { position: absolute; top: calc(100% + 6px); left: 0; background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-strong); border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.7); min-width: 200px; z-index: 100; padding: 4px; animation: popup-col-in 100ms ease-out; }
.inv-bodega-dropdown-title { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); padding: 8px 10px 4px; }
.inv-bodega-dropdown-item { padding: 7px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; color: var(--text-secondary); }
.inv-bodega-dropdown-item:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
.inv-bodega-dropdown-empty { padding: 12px 10px; font-size: 12px; color: var(--text-tertiary); text-align: center; }

/* TABLE */
.inv-table-container { flex: 1; overflow: auto; }
.inv-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.inv-table thead { position: sticky; top: 0; z-index: 5; }

.th { text-align: left; padding: 0 12px; height: 36px; font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-default); background: var(--bg-card, #1c1c1e); position: sticky; top: 0; z-index: 5; cursor: pointer; user-select: none; white-space: nowrap; transition: color 80ms; }
.th:hover { color: var(--text-secondary); }
.th-nosort { cursor: default; }
.th-nosort:hover { color: var(--text-tertiary); }
.th-inner { display: flex; align-items: center; gap: 4px; }
.th-label { flex: 1; }
.sort-icon { font-size: 14px !important; color: var(--accent); }
.th-sorted { color: var(--accent); }
.th-filter-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.th-filtered { color: var(--accent); }
.th-popup-open { background: var(--bg-row-hover); }
.th-conteo { text-align: right; padding-right: 48px; }

.td { padding: 0 12px; height: 44px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); vertical-align: middle; white-space: nowrap; }
.inv-table tr:hover .td { background: var(--bg-row-hover); }
.inv-table tr.row-ok .td { background: rgba(34,197,94,0.02); }
.inv-table tr.row-diff .td { background: rgba(248,161,1,0.03); }
.td-center { text-align: center; }
.td-empty { height: 80px; text-align: center; color: var(--text-tertiary); font-size: 13px; border-bottom: none; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; }

.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-pending { border: 1.5px solid var(--color-pending); background: transparent; }
.dot-ok { background: var(--color-ok); box-shadow: 0 0 6px rgba(34,197,94,0.3); }
.dot-warning { background: var(--color-warning); box-shadow: 0 0 6px rgba(245,158,11,0.3); }
.dot-critical { background: var(--color-error); box-shadow: 0 0 6px rgba(248,113,113,0.3); }

.cell-id { font-size: 12px; color: var(--text-tertiary); font-family: 'Fragment Mono', monospace; }
.cell-articulo { font-size: 13px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; }
.cell-categoria { font-size: 12px; overflow: hidden; text-overflow: ellipsis; }

/* CONTEO CELL */
.conteo-cell { display: flex; align-items: center; justify-content: flex-end; gap: 8px; height: 44px; }
.teorico-block { display: flex; flex-direction: column; align-items: flex-end; min-width: 40px; }
.teorico-label { font-size: 9px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; }
.teorico-value { font-size: 13px; color: var(--text-secondary); font-family: 'Fragment Mono', monospace; font-weight: 500; }
.count-input { width: 52px; height: 32px; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-primary); font-size: 14px; font-weight: 500; font-family: 'Fragment Mono', monospace; text-align: center; outline: none; -moz-appearance: textfield; }
.count-input::-webkit-inner-spin-button, .count-input::-webkit-outer-spin-button { -webkit-appearance: none; }
.count-input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(0,200,83,0.15); }
.input-ok { border-color: var(--color-ok); background: rgba(34,197,94,0.06); }
.input-warning { border-color: var(--color-warning); background: rgba(245,158,11,0.06); }
.input-critical { border-color: var(--color-error); background: rgba(248,113,113,0.06); }
.diff-badge { font-size: 11px; font-weight: 600; font-family: 'Fragment Mono', monospace; padding: 2px 6px; border-radius: 10px; min-width: 32px; text-align: center; }
.badge-ok { background: rgba(34,197,94,0.12); color: #4ade80; }
.badge-warning { background: rgba(245,158,11,0.12); color: #fbbf24; }
.badge-error { background: rgba(248,113,113,0.12); color: #f87171; }
.badge-empty { color: var(--text-tertiary); }

.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; }
.action-btn:hover { background: rgba(255,255,255,0.06); color: var(--text-secondary); }
.action-btn.has-note { color: var(--accent); }

/* FAB */
.inv-fab { position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; border-radius: 50%; background: var(--accent); color: #000; border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(0,200,83,0.4); display: flex; align-items: center; justify-content: center; z-index: 20; }
.inv-fab:hover { transform: scale(1.08); }

/* MODALS */
.inv-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 50; display: flex; align-items: center; justify-content: center; }
.inv-modal { background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-default); border-radius: 8px; width: 460px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 20px 80px rgba(0,0,0,0.8); }
.inv-modal-sm { width: 380px; }
.inv-modal-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border-subtle); font-weight: 500; }
.inv-modal-body { padding: 16px; }
.inv-modal-search { width: 100%; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 8px 12px; margin-bottom: 12px; color: var(--text-primary); font-size: 13px; outline: none; }
.inv-modal-search:focus { border-color: var(--accent); }
.inv-modal-results { max-height: 300px; overflow-y: auto; }
.inv-modal-result-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-radius: 4px; cursor: pointer; }
.inv-modal-result-item:hover { background: rgba(255,255,255,0.04); }
.inv-modal-result-name { font-size: 13px; }
.inv-modal-result-id { font-size: 11px; color: var(--text-tertiary); font-family: 'Fragment Mono', monospace; }
.inv-modal-empty { text-align: center; color: var(--text-tertiary); padding: 20px; }
.inv-nota-textarea { width: 100%; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 10px; color: var(--text-primary); font-size: 13px; font-family: inherit; resize: vertical; margin-bottom: 12px; outline: none; }
.inv-nota-textarea:focus { border-color: var(--accent); }
.inv-btn-primary { background: var(--accent); color: #000; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: 600; cursor: pointer; width: 100%; }
.inv-btn-primary:hover { background: var(--accent-hover); }
</style>

<!-- POPUP COLUMNA — sin scoped (Teleport to body) -->
<style>
.col-popup-overlay { position: fixed; inset: 0; z-index: 9999; background: transparent; }
.col-popup { position: fixed; z-index: 10000; background: #1c1c1e; border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.7); padding: 10px 12px; min-width: 210px; display: flex; flex-direction: column; gap: 8px; font-size: 12px; color: #fff; animation: popup-col-in 100ms ease-out; }
@keyframes popup-col-in { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: none; } }
.cp-section { display: flex; flex-direction: column; gap: 5px; }
.cp-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: #5f6369; }
.cp-filter-row { display: flex; gap: 4px; }
.cp-select { flex: 1; height: 26px; padding: 0 6px; border: 1px solid rgba(255,255,255,0.10); border-radius: 4px; background: #1a1a1e; color: #fff; font-size: 12px; font-family: inherit; }
.cp-filter-inputs { display: flex; flex-direction: column; gap: 4px; }
.cp-input { width: 100%; height: 26px; padding: 0 8px; border: 1px solid rgba(255,255,255,0.10); border-radius: 4px; background: #1a1a1e; color: #fff; font-size: 12px; font-family: inherit; }
.cp-input:focus, .cp-select:focus { outline: none; border-color: #00C853; }
.cp-sort-btns { display: flex; flex-direction: column; gap: 3px; }
.cp-sort-btn { display: flex; align-items: center; gap: 5px; height: 28px; padding: 0 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.10); background: transparent; font-size: 12px; color: #8a8f98; cursor: pointer; font-family: inherit; transition: all 80ms; }
.cp-sort-btn:hover { background: #1a1a1e; color: #fff; border-color: rgba(255,255,255,0.18); }
.cp-sort-btn.active { background: rgba(0,200,83,0.12); border-color: rgba(0,200,83,0.35); color: #00C853; }
.cp-footer { border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; }
.cp-clear-btn { width: 100%; height: 26px; border-radius: 4px; border: none; background: transparent; font-size: 12px; color: #f87171; cursor: pointer; font-family: inherit; }
.cp-clear-btn:hover { background: rgba(248,113,113,0.08); }
</style>
