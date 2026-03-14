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
        <button
          class="pill-tab"
          :class="{ active: tabActivo === 'mes' }"
          @click="tabActivo = 'mes'"
        >
          Por mes
        </button>
        <button
          class="pill-tab"
          :class="{ active: tabActivo === 'producto' }"
          @click="onTabProducto"
        >
          Por producto
        </button>
        <button
          class="pill-tab"
          :class="{ active: tabActivo === 'grupo' }"
          @click="onTabGrupo"
        >
          Por grupo
        </button>
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
      />

      <!-- Tab: Por grupo -->
      <OsDataTable
        v-if="tabActivo === 'grupo'"
        title="Resumen por grupo"
        :rows="resGrupo"
        :columns="colsGrupo"
        :loading="loadingGrupo"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
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
let productosCargados = false

// ── Tab por grupo ──────────────────────────────────────
const resGrupo     = ref([])
const loadingGrupo = ref(false)
const colsGrupo    = ref([])
let grupoCargado   = false

const VISIBLE_PRODUCTO = ['cod_articulo','grupo_producto','cantidad_total','fin_ventas_netas','fin_costo_total','fin_utilidad_bruta','margen_pct','fin_notas_credito','num_facturas','num_clientes']
const LABELS_PRODUCTO  = {
  cod_articulo:      'Cód.',
  grupo_producto:    'Grupo producto',
  descripcion:       'Descripción',
  cantidad_total:    'Cantidad',
  fin_ventas_brutas: 'Ventas brutas',
  fin_descuentos:    'Descuentos',
  fin_ventas_netas:  'Ventas netas',
  fin_costo_total:   'Costo total',
  fin_utilidad_bruta:'Utilidad bruta',
  margen_pct:        'Margen %',
  fin_notas_credito: 'Notas crédito',
  cantidad_nc:       'Cant. NC',
  num_facturas:      'Facturas',
  num_clientes:      'Clientes',
}

const VISIBLE_GRUPO = ['grupo_producto','cantidad_total','fin_ventas_netas','fin_costo_total','fin_utilidad_bruta','margen_pct','fin_notas_credito','num_facturas','num_clientes','num_referencias']
const LABELS_GRUPO  = {
  grupo_producto:    'Grupo producto',
  cantidad_total:    'Cantidad',
  fin_ventas_brutas: 'Ventas brutas',
  fin_descuentos:    'Descuentos',
  fin_ventas_netas:  'Ventas netas',
  fin_costo_total:   'Costo total',
  fin_utilidad_bruta:'Utilidad bruta',
  margen_pct:        'Margen %',
  fin_notas_credito: 'Notas crédito',
  num_facturas:      'Facturas',
  num_clientes:      'Clientes',
  num_referencias:   'Referencias',
}

// ── Helpers ────────────────────────────────────────────
function labelFromKey(key) {
  return key
    .replace(/^_pk$/, 'N°')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '')
    .replace(/^Vol /, '')
    .replace(/^Cli /, '')
    .replace(/^Cto /, '')
    .replace(/^Con /, '')
    .replace(/^Top /, 'Top ')
    .replace(/^Pry /, 'Pry ')
    .replace(/^Ant /, 'Ant ')
    .trim()
}

async function loadColumns() {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/resumen_ventas_facturas_mes`)
    colsMes.value = cols.map(key => ({
      key,
      label: labelFromKey(key),
      visible: DEFAULT_VISIBLE_MES.includes(key)
    }))
  } catch(e) { console.error('Error cargando columnas', e) }
}

async function loadMes() {
  loadingMes.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-mes`)
    resMes.value = data
  } finally { loadingMes.value = false }
}

async function loadProducto() {
  if (productosCargados) return
  loadingProducto.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-por-producto`)
    resProducto.value = data
    if (data.length > 0) {
      colsProducto.value = Object.keys(data[0]).map(key => ({
        key,
        label: LABELS_PRODUCTO[key] || labelFromKey(key),
        visible: VISIBLE_PRODUCTO.includes(key)
      }))
    }
    productosCargados = true
  } finally { loadingProducto.value = false }
}

function onTabProducto() {
  tabActivo.value = 'producto'
  loadProducto()
}

async function loadGrupo() {
  if (grupoCargado) return
  loadingGrupo.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-por-grupo`)
    resGrupo.value = data
    if (data.length > 0) {
      colsGrupo.value = Object.keys(data[0]).map(key => ({
        key,
        label: LABELS_GRUPO[key] || labelFromKey(key),
        visible: VISIBLE_GRUPO.includes(key)
      }))
    }
    grupoCargado = true
  } finally { loadingGrupo.value = false }
}

function onTabGrupo() {
  tabActivo.value = 'grupo'
  loadGrupo()
}

function onMesClick(row) {
  router.push(`/ventas/detalle-mes/${row.mes}`)
}

onMounted(async () => {
  await loadColumns()
  await loadMes()
})
</script>

<style scoped>
.page-wrap { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }

.page-header {
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-app);
  padding: 0 24px;
  flex-shrink: 0;
}
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px;
}
.bc-current { color: var(--text-secondary); }
.page-title-row { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }

/* Pill Tabs — Manual §26 */
.pill-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pill-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 400;
  font-family: inherit;
  transition: border-color 70ms, color 70ms, background 70ms;
  white-space: nowrap;
}
.pill-tab:hover {
  border-color: var(--border-default);
  color: var(--text-secondary);
}
.pill-tab.active {
  border-color: var(--border-default);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-weight: 500;
}
</style>
