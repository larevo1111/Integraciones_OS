<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Mercancía en Consignación</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Mercancía en Consignación</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- Pill Tabs nivel 1: Hoy / A fecha -->
      <div class="pill-tabs">
        <button class="pill-tab" :class="{ active: tabPeriodo === 'hoy' }" @click="tabPeriodo = 'hoy'">Hoy</button>
        <button class="pill-tab" :class="{ active: tabPeriodo === 'fecha' }" @click="onTabFecha">A fecha de corte</button>
      </div>

      <!-- Selector de fecha (solo tab fecha) -->
      <div v-if="tabPeriodo === 'fecha'" class="filter-bar">
        <div class="filter-row">
          <span class="filter-range-label">Fecha de corte</span>
          <input v-model="fechaCorte" type="date" class="filter-date-input" @change="cargarFecha" />
        </div>
      </div>

      <!-- KPIs -->
      <div v-if="!loadingClientesActivo && clientesActivos.length > 0" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Clientes con consignación</span>
          <span class="kpi-value">{{ kpis.numClientes }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Órdenes activas</span>
          <span class="kpi-value">{{ kpis.numOrdenes }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Total en consignación</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalConsignacion) }}</span>
        </div>
      </div>

      <!-- Pill Tabs nivel 2: Por cliente / Por producto -->
      <div class="pill-tabs">
        <button class="pill-tab" :class="{ active: tabVista === 'clientes' }" @click="tabVista = 'clientes'">
          Por cliente
          <span v-if="clientesActivos.length > 0" class="pill-tab-badge">{{ clientesActivos.length }}</span>
        </button>
        <button class="pill-tab" :class="{ active: tabVista === 'productos' }" @click="tabVista = 'productos'">
          Por producto
          <span v-if="productosActivos.length > 0" class="pill-tab-badge">{{ productosActivos.length }}</span>
        </button>
      </div>

      <!-- Tabla: Por cliente -->
      <OsDataTable
        v-if="tabVista === 'clientes'"
        :title="tabPeriodo === 'hoy' ? 'Consignación por cliente' : `Consignación al ${fechaCorte} — por cliente`"
        recurso="consignacion"
        :rows="clientesActivos"
        :columns="colsClientesActivos"
        :loading="loadingClientesActivo"
        @row-click="onRowClickCliente"
      />

      <!-- Tabla: Por producto -->
      <OsDataTable
        v-if="tabVista === 'productos'"
        :title="tabPeriodo === 'hoy' ? 'Consignación por producto' : `Consignación al ${fechaCorte} — por producto`"
        :rows="productosActivos"
        :columns="colsProductosActivos"
        :loading="loadingProductosActivo"
        @row-click="onRowClickProducto"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const router = useRouter()
const API = '/api'

const tabPeriodo = ref('hoy')
const tabVista = ref('clientes')
const fechaCorte = ref('')

// ── Datos Hoy ────────────────────────────────────────
const rowsClientesHoy = ref([])
const colsClientesHoy = ref([])
const loadingClientesHoy = ref(true)
const rowsProductosHoy = ref([])
const colsProductosHoy = ref([])
const loadingProductosHoy = ref(true)

// ── Datos A fecha ────────────────────────────────────
const rowsClientesFecha = ref([])
const colsClientesFecha = ref([])
const loadingClientesFecha = ref(false)
const rowsProductosFecha = ref([])
const colsProductosFecha = ref([])
const loadingProductosFecha = ref(false)

// ── Computed: datos activos según pestaña ────────────
const clientesActivos = computed(() => tabPeriodo.value === 'hoy' ? rowsClientesHoy.value : rowsClientesFecha.value)
const colsClientesActivos = computed(() => tabPeriodo.value === 'hoy' ? colsClientesHoy.value : colsClientesFecha.value)
const loadingClientesActivo = computed(() => tabPeriodo.value === 'hoy' ? loadingClientesHoy.value : loadingClientesFecha.value)
const productosActivos = computed(() => tabPeriodo.value === 'hoy' ? rowsProductosHoy.value : rowsProductosFecha.value)
const colsProductosActivos = computed(() => tabPeriodo.value === 'hoy' ? colsProductosHoy.value : colsProductosFecha.value)
const loadingProductosActivo = computed(() => tabPeriodo.value === 'hoy' ? loadingProductosHoy.value : loadingProductosFecha.value)

const VISIBLE_CLIENTES = [
  'nombre_cliente', 'ciudad', 'vendedor',
  'num_ordenes', 'fin_total_consignacion',
  'fecha_primera_orden', 'fecha_ultima_orden'
]

const LABELS_CLIENTES = {
  nombre_cliente:        'Cliente',
  ciudad:                'Ciudad',
  vendedor:              'Vendedor',
  num_ordenes:           'Órdenes',
  fin_total_consignacion:'Total consignación',
  fecha_primera_orden:   'Primera orden',
  fecha_ultima_orden:    'Última orden',
  id_cliente:            'ID Cliente',
}

const VISIBLE_PRODUCTOS = [
  'cod_articulo', 'descripcion_articulo',
  'num_clientes', 'num_ordenes', 'cantidad_total', 'fin_total'
]

const LABELS_PRODUCTOS = {
  cod_articulo:         'Cód.',
  descripcion_articulo: 'Producto',
  num_clientes:         'Clientes',
  num_ordenes:          'Órdenes',
  cantidad_total:       'Cantidad',
  fin_total:            'Total',
}

function labelFromKey(key, labels) {
  return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function buildColumns(data, labels, visible) {
  if (!data.length) return []
  return Object.keys(data[0]).map(key => ({
    key, label: labelFromKey(key, labels), visible: visible.includes(key)
  }))
}

const kpis = computed(() => ({
  numClientes:       clientesActivos.value.length,
  numOrdenes:        clientesActivos.value.reduce((s, r) => s + (parseInt(r.num_ordenes) || 0), 0),
  totalConsignacion: clientesActivos.value.reduce((s, r) => s + (parseFloat(r.fin_total_consignacion) || 0), 0),
}))

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClickCliente(row) {
  router.push(`/ventas/consignacion-cliente/${encodeURIComponent(row.id_cliente)}`)
}

function onRowClickProducto(row) {
  router.push(`/ventas/consignacion-producto/${encodeURIComponent(row.cod_articulo)}`)
}

onMounted(async () => {
  const [resC, resP] = await Promise.allSettled([
    axios.get(`${API}/ventas/consignacion`),
    axios.get(`${API}/ventas/consignacion-por-producto`),
  ])
  if (resC.status === 'fulfilled') {
    rowsClientesHoy.value = resC.value.data
    colsClientesHoy.value = buildColumns(resC.value.data, LABELS_CLIENTES, VISIBLE_CLIENTES)
  }
  loadingClientesHoy.value = false
  if (resP.status === 'fulfilled') {
    rowsProductosHoy.value = resP.value.data
    colsProductosHoy.value = buildColumns(resP.value.data, LABELS_PRODUCTOS, VISIBLE_PRODUCTOS)
  }
  loadingProductosHoy.value = false
})

function onTabFecha() {
  tabPeriodo.value = 'fecha'
}

async function cargarFecha() {
  if (!fechaCorte.value) return
  loadingClientesFecha.value = true
  loadingProductosFecha.value = true
  const [resC, resP] = await Promise.allSettled([
    axios.get(`${API}/ventas/consignacion-fecha`, { params: { fecha: fechaCorte.value } }),
    axios.get(`${API}/ventas/consignacion-por-producto-fecha`, { params: { fecha: fechaCorte.value } }),
  ])
  if (resC.status === 'fulfilled') {
    rowsClientesFecha.value = resC.value.data
    colsClientesFecha.value = buildColumns(resC.value.data, LABELS_CLIENTES, VISIBLE_CLIENTES)
  }
  loadingClientesFecha.value = false
  if (resP.status === 'fulfilled') {
    rowsProductosFecha.value = resP.value.data
    colsProductosFecha.value = buildColumns(resP.value.data, LABELS_PRODUCTOS, VISIBLE_PRODUCTOS)
  }
  loadingProductosFecha.value = false
}
</script>

<style scoped>
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

.page-header       { border-bottom: 1px solid var(--border-subtle); background: var(--bg-app); padding: 0 24px; flex-shrink: 0; }
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb        { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px; }
.bc-current        { color: var(--text-secondary); }
.page-title-row    { display: flex; align-items: center; gap: 12px; }
.page-title        { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.pill-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.pill-tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent; color: var(--text-tertiary);
  cursor: pointer; font-size: 12px; font-weight: 400;
  font-family: inherit; transition: border-color 70ms, color 70ms, background 70ms;
  white-space: nowrap;
}
.pill-tab:hover { border-color: var(--border-default); color: var(--text-secondary); }
.pill-tab.active {
  border-color: var(--border-default);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-weight: 500;
}
.pill-tab-badge {
  background: var(--color-accent); color: white;
  border-radius: 10px; padding: 0 5px;
  font-size: 10px; font-weight: 600; line-height: 16px;
}

.filter-bar { display: flex; flex-direction: column; gap: 8px; }
.filter-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.filter-range-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
.filter-date-input {
  padding: 4px 8px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: var(--bg-input);
  font-size: 13px; color: var(--text-primary);
}

.kpi-section { display: flex; gap: 12px; flex-wrap: wrap; }
.kpi-card {
  flex: 1; min-width: 160px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 4px;
}
.kpi-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
</style>
