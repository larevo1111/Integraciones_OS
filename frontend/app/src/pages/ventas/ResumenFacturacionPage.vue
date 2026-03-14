<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Resumen Facturación</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Resumen Facturación</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- Pill Tabs -->
      <div class="pill-tabs">
        <button class="pill-tab" :class="{ active: tabActivo === 'mes' }"      @click="tabActivo = 'mes'">Por mes</button>
        <button class="pill-tab" :class="{ active: tabActivo === 'producto' }" @click="onTabProducto">Por producto</button>
        <button class="pill-tab" :class="{ active: tabActivo === 'grupo' }"    @click="onTabGrupo">Por grupo</button>
      </div>

      <!-- ── BARRA DE FILTROS (solo tabs producto/grupo) ── -->
      <div v-if="tabActivo !== 'mes'" class="filter-bar">

        <!-- Fila 1: Todas + años + rango personalizado -->
        <div class="filter-row">
          <button
            class="filter-pill"
            :class="{ active: filtroActivo === 'todas' }"
            @click="aplicarTodas"
          >Todas</button>

          <div class="filter-sep"></div>

          <button
            v-for="anio in aniosDisponibles"
            :key="anio"
            class="filter-pill"
            :class="{ active: anioSeleccionado === anio }"
            @click="seleccionarAnio(anio)"
          >{{ anio }}</button>

          <div class="filter-sep"></div>

          <div class="filter-range">
            <span class="filter-range-label">Desde</span>
            <input
              v-model="desdeInput"
              type="date"
              class="filter-date-input"
              @change="aplicarRangoPersonalizado"
            />
            <span class="filter-range-label">Hasta</span>
            <input
              v-model="hastaInput"
              type="date"
              class="filter-date-input"
              @change="aplicarRangoPersonalizado"
            />
            <button
              v-if="desdeInput || hastaInput"
              class="filter-clear"
              title="Limpiar fechas"
              @click="limpiarRango"
            >
              <XIcon :size="12" />
            </button>
          </div>
        </div>

        <!-- Fila 2: Trimestres (solo cuando hay año seleccionado) -->
        <div v-if="anioSeleccionado" class="filter-row filter-row-q">
          <span class="filter-q-label">{{ anioSeleccionado }}</span>
          <ChevronRightIcon :size="11" class="filter-q-arrow" />
          <button
            v-for="q in [1,2,3,4]"
            :key="q"
            class="filter-pill filter-pill-q"
            :class="{ active: trimestreActivo === q }"
            @click="seleccionarTrimestre(q)"
          >Q{{ q }}</button>
        </div>

      </div>

      <!-- Tab: Por mes -->
      <OsDataTable
        v-if="tabActivo === 'mes'"
        title="Resumen por mes"
        recurso="resumen-mes"
        :rows="resMes"
        :columns="colsMes"
        :loading="loadingMes"
        @row-click="onMesClick"
      />

      <!-- Tab: Por producto -->
      <OsDataTable
        v-if="tabActivo === 'producto'"
        title="Resumen por producto"
        :rows="resProducto"
        :columns="colsProducto"
        :loading="loadingProducto"
        @row-click="row => router.push(`/ventas/facturas-producto/${encodeURIComponent(row.cod_articulo)}`)"
      />

      <!-- Tab: Por grupo -->
      <OsDataTable
        v-if="tabActivo === 'grupo'"
        title="Resumen por grupo"
        :rows="resGrupo"
        :columns="colsGrupo"
        :loading="loadingGrupo"
        @row-click="row => router.push(`/ventas/facturas-grupo/${encodeURIComponent(row.grupo_producto)}`)"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon, XIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const router = useRouter()
const API = '/api'

const tabActivo = ref('mes')

// ── Tab por mes ────────────────────────────────────────
const resMes     = ref([])
const loadingMes = ref(true)
const colsMes    = ref([])
const DEFAULT_VISIBLE_MES = ['mes','fin_ventas_netas_sin_iva','fin_ingresos_netos','fin_devoluciones','vol_num_facturas','vol_ticket_promedio','cli_clientes_activos','cli_clientes_nuevos','top_canal','top_cliente','con_consignacion_pp']

// ── Tab por producto ───────────────────────────────────
const resProducto     = ref([])
const loadingProducto = ref(false)
const colsProducto    = ref([])
let colsProductoInit  = false   // columnas generadas una vez

// ── Tab por grupo ──────────────────────────────────────
const resGrupo     = ref([])
const loadingGrupo = ref(false)
const colsGrupo    = ref([])
let colsGrupoInit  = false

// ── Filtro de fechas ───────────────────────────────────
const aniosDisponibles  = ref([])
const anioSeleccionado  = ref(null)
const trimestreActivo   = ref(null)
const filtroActivo      = ref('todas')   // 'todas' | 'anio' | 'trimestre' | 'rango'
const desdeInput        = ref('')
const hastaInput        = ref('')

const TRIMESTRES = {
  1: { desde: '-01-01', hasta: '-03-31' },
  2: { desde: '-04-01', hasta: '-06-30' },
  3: { desde: '-07-01', hasta: '-09-30' },
  4: { desde: '-10-01', hasta: '-12-31' },
}

// ── Column labels ──────────────────────────────────────
const VISIBLE_PRODUCTO = ['cod_articulo','grupo_producto','cantidad_total','fin_ventas_netas','fin_costo_total','fin_utilidad_bruta','margen_pct','fin_notas_credito','num_facturas','num_clientes']
const LABELS_PRODUCTO  = {
  cod_articulo:       'Cód.',
  grupo_producto:     'Grupo producto',
  descripcion:        'Descripción',
  cantidad_total:     'Cantidad',
  fin_ventas_brutas:  'Ventas brutas',
  fin_descuentos:     'Descuentos',
  fin_ventas_netas:   'Ventas netas',
  fin_costo_total:    'Costo total',
  fin_utilidad_bruta: 'Utilidad bruta',
  margen_pct:         'Margen %',
  fin_notas_credito:  'Notas crédito',
  cantidad_nc:        'Cant. NC',
  num_facturas:       'Facturas',
  num_clientes:       'Clientes',
}
const VISIBLE_GRUPO = ['grupo_producto','cantidad_total','fin_ventas_netas','fin_costo_total','fin_utilidad_bruta','margen_pct','fin_notas_credito','num_facturas','num_clientes','num_referencias']
const LABELS_GRUPO  = {
  grupo_producto:     'Grupo producto',
  cantidad_total:     'Cantidad',
  fin_ventas_brutas:  'Ventas brutas',
  fin_descuentos:     'Descuentos',
  fin_ventas_netas:   'Ventas netas',
  fin_costo_total:    'Costo total',
  fin_utilidad_bruta: 'Utilidad bruta',
  margen_pct:         'Margen %',
  fin_notas_credito:  'Notas crédito',
  num_facturas:       'Facturas',
  num_clientes:       'Clientes',
  num_referencias:    'Referencias',
}

// ── Helpers ────────────────────────────────────────────
function labelFromKey(key) {
  return key
    .replace(/^_pk$/, 'N°').replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '').replace(/^Vol /, '').replace(/^Cli /, '')
    .replace(/^Cto /, '').replace(/^Con /, '')
    .replace(/^Top /, 'Top ').replace(/^Pry /, 'Pry ').replace(/^Ant /, 'Ant ')
    .trim()
}

function buildParams(extra = {}) {
  const p = {}
  if (desdeInput.value) p.desde = desdeInput.value
  if (hastaInput.value) p.hasta = hastaInput.value
  return { params: { ...p, ...extra } }
}

function setColumns(data, labels, visible, colsRef, initFlag) {
  if (!initFlag && data.length > 0) {
    colsRef.value = Object.keys(data[0]).map(key => ({
      key,
      label: labels[key] || labelFromKey(key),
      visible: visible.includes(key),
    }))
  }
}

// ── Carga de datos ─────────────────────────────────────
async function loadColumns() {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/resumen_ventas_facturas_mes`)
    colsMes.value = cols.map(key => ({
      key, label: labelFromKey(key), visible: DEFAULT_VISIBLE_MES.includes(key),
    }))
  } catch(e) { console.error(e) }
}

async function loadMes() {
  loadingMes.value = true
  try { const { data } = await axios.get(`${API}/ventas/resumen-mes`); resMes.value = data }
  finally { loadingMes.value = false }
}

async function loadProducto() {
  loadingProducto.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-por-producto`, buildParams())
    resProducto.value = data
    setColumns(data, LABELS_PRODUCTO, VISIBLE_PRODUCTO, colsProducto, colsProductoInit)
    colsProductoInit = true
  } finally { loadingProducto.value = false }
}

async function loadGrupo() {
  loadingGrupo.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-por-grupo`, buildParams())
    resGrupo.value = data
    setColumns(data, LABELS_GRUPO, VISIBLE_GRUPO, colsGrupo, colsGrupoInit)
    colsGrupoInit = true
  } finally { loadingGrupo.value = false }
}

async function recargarTabActiva() {
  if (tabActivo.value === 'producto') await loadProducto()
  else if (tabActivo.value === 'grupo')   await loadGrupo()
}

// ── Acciones de filtro ─────────────────────────────────
function aplicarTodas() {
  anioSeleccionado.value  = null
  trimestreActivo.value   = null
  filtroActivo.value      = 'todas'
  desdeInput.value        = ''
  hastaInput.value        = ''
  recargarTabActiva()
}

function seleccionarAnio(anio) {
  anioSeleccionado.value = anio
  trimestreActivo.value  = null
  filtroActivo.value     = 'anio'
  desdeInput.value       = `${anio}-01-01`
  hastaInput.value       = `${anio}-12-31`
  recargarTabActiva()
}

function seleccionarTrimestre(q) {
  if (!anioSeleccionado.value) return
  trimestreActivo.value = q
  filtroActivo.value    = 'trimestre'
  desdeInput.value      = `${anioSeleccionado.value}${TRIMESTRES[q].desde}`
  hastaInput.value      = `${anioSeleccionado.value}${TRIMESTRES[q].hasta}`
  recargarTabActiva()
}

function aplicarRangoPersonalizado() {
  if (!desdeInput.value && !hastaInput.value) return
  anioSeleccionado.value = null
  trimestreActivo.value  = null
  filtroActivo.value     = 'rango'
  recargarTabActiva()
}

function limpiarRango() {
  desdeInput.value  = ''
  hastaInput.value  = ''
  aplicarTodas()
}

// ── Tab handlers ───────────────────────────────────────
function onTabProducto() {
  tabActivo.value = 'producto'
  loadProducto()
}
function onTabGrupo() {
  tabActivo.value = 'grupo'
  loadGrupo()
}
function onMesClick(row) { router.push(`/ventas/detalle-mes/${row.mes}`) }

// ── Init ───────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    loadColumns(),
    loadMes(),
    axios.get(`${API}/ventas/anios-facturas`).then(r => { aniosDisponibles.value = r.data }),
  ])
})
</script>

<style scoped>
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
.page-header  { border-bottom: 1px solid var(--border-subtle); background: var(--bg-app); padding: 0 24px; flex-shrink: 0; }
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb   { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px; }
.bc-current   { color: var(--text-secondary); }
.page-title-row { display: flex; align-items: center; gap: 12px; }
.page-title   { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }
.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }

/* ── Pill Tabs ── §26 */
.pill-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.pill-tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 20px;
  border: 1px solid var(--border-subtle); background: transparent;
  color: var(--text-tertiary); cursor: pointer;
  font-size: 12px; font-weight: 400; font-family: inherit;
  transition: border-color 70ms, color 70ms, background 70ms;
  white-space: nowrap;
}
.pill-tab:hover { border-color: var(--border-default); color: var(--text-secondary); }
.pill-tab.active {
  border-color: var(--border-default); background: var(--bg-surface);
  color: var(--text-primary); font-weight: 500;
}

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 8px);
}

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

/* Separador vertical entre grupos */
.filter-sep {
  width: 1px;
  height: 16px;
  background: var(--border-subtle);
  margin: 0 4px;
  flex-shrink: 0;
}

/* Pills de filtro — más pequeños que los tabs */
.filter-pill {
  display: inline-flex; align-items: center;
  padding: 3px 10px; border-radius: 20px;
  border: 1px solid var(--border-subtle); background: transparent;
  color: var(--text-tertiary); cursor: pointer;
  font-size: 11px; font-weight: 400; font-family: inherit;
  transition: border-color 70ms, color 70ms, background 70ms;
  white-space: nowrap; line-height: 1.4;
}
.filter-pill:hover { border-color: var(--border-default); color: var(--text-secondary); }
.filter-pill.active {
  border-color: var(--border-default); background: var(--bg-surface);
  color: var(--text-primary); font-weight: 500;
}

/* Q pills aún más pequeños */
.filter-pill-q { padding: 2px 8px; font-size: 11px; }

/* Fila de trimestres */
.filter-row-q { padding-left: 2px; }
.filter-q-label {
  font-size: 11px; font-weight: 600; color: var(--text-tertiary);
  letter-spacing: 0.03em;
}
.filter-q-arrow { color: var(--text-tertiary); flex-shrink: 0; }

/* Inputs de fecha */
.filter-range {
  display: flex; align-items: center; gap: 6px;
  margin-left: 2px;
}
.filter-range-label {
  font-size: 11px; color: var(--text-tertiary);
  white-space: nowrap;
}
.filter-date-input {
  height: 26px;
  padding: 0 8px;
  width: 128px;
  background: var(--bg-input);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  font-size: 12px;
  font-family: inherit;
  color: var(--text-primary);
  outline: none;
  transition: border-color 100ms, box-shadow 100ms;
  -webkit-appearance: none;
  cursor: pointer;
}
.filter-date-input:hover:not(:focus) { border-color: var(--border-default); }
.filter-date-input:focus {
  border-color: var(--accent, #5e6ad2);
  box-shadow: 0 0 0 3px var(--accent-muted, rgba(94,106,210,0.15));
}
/* Icono del calendario nativo */
.filter-date-input::-webkit-calendar-picker-indicator {
  opacity: 0.5;
  cursor: pointer;
  filter: var(--calendar-icon-filter, invert(1));
}
.filter-date-input::-webkit-calendar-picker-indicator:hover { opacity: 0.9; }

/* Botón limpiar rango */
.filter-clear {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  border: none; background: transparent;
  color: var(--text-tertiary); cursor: pointer;
  transition: background 70ms, color 70ms;
  flex-shrink: 0;
}
.filter-clear:hover { background: var(--bg-surface); color: var(--text-primary); }
</style>
