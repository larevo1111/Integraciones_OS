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

      <!-- KPIs -->
      <div v-if="!loadingClientes && rowsClientes.length > 0" class="kpi-section">
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

      <!-- Pill Tabs -->
      <div class="pill-tabs">
        <button
          class="pill-tab"
          :class="{ active: tabActivo === 'clientes' }"
          @click="tabActivo = 'clientes'"
        >
          Por cliente
          <span v-if="rowsClientes.length > 0" class="pill-tab-badge">{{ rowsClientes.length }}</span>
        </button>
        <button
          class="pill-tab"
          :class="{ active: tabActivo === 'productos' }"
          @click="tabActivo = 'productos'"
        >
          Por producto
          <span v-if="rowsProductos.length > 0" class="pill-tab-badge">{{ rowsProductos.length }}</span>
        </button>
      </div>

      <!-- Tab: Por cliente -->
      <OsDataTable
        v-if="tabActivo === 'clientes'"
        title="Consignación por cliente"
        recurso="consignacion"
        :rows="rowsClientes"
        :columns="colsClientes"
        :loading="loadingClientes"
        @row-click="onRowClickCliente"
      />

      <!-- Tab: Por producto -->
      <OsDataTable
        v-if="tabActivo === 'productos'"
        title="Consignación por producto"
        :rows="rowsProductos"
        :columns="colsProductos"
        :loading="loadingProductos"
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

const router  = useRouter()
const API     = '/api'

const tabActivo = ref('clientes')

// ── Tab clientes ──────────────────────────────────────
const rowsClientes    = ref([])
const colsClientes    = ref([])
const loadingClientes = ref(true)

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

// ── Tab productos ─────────────────────────────────────
const rowsProductos    = ref([])
const colsProductos    = ref([])
const loadingProductos = ref(true)

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

// ── Helpers ───────────────────────────────────────────
function labelFromKey(key, labels) {
  return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const kpis = computed(() => ({
  numClientes:       rowsClientes.value.length,
  numOrdenes:        rowsClientes.value.reduce((s, r) => s + (parseInt(r.num_ordenes) || 0), 0),
  totalConsignacion: rowsClientes.value.reduce((s, r) => s + (parseFloat(r.fin_total_consignacion) || 0), 0),
}))

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClickCliente(row) {
  router.push(`/ventas/consignacion-cliente/${encodeURIComponent(row.id_cliente)}`)
}

onMounted(async () => {
  // Cargar ambas tabs en paralelo
  const [resClientes, resProductos] = await Promise.allSettled([
    axios.get(`${API}/ventas/consignacion`),
    axios.get(`${API}/ventas/consignacion-por-producto`),
  ])

  if (resClientes.status === 'fulfilled') {
    const data = resClientes.value.data
    rowsClientes.value = data
    if (data.length > 0) {
      colsClientes.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key, LABELS_CLIENTES), visible: VISIBLE_CLIENTES.includes(key)
      }))
    }
  }
  loadingClientes.value = false

  if (resProductos.status === 'fulfilled') {
    const data = resProductos.value.data
    rowsProductos.value = data
    if (data.length > 0) {
      colsProductos.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key, LABELS_PRODUCTOS), visible: VISIBLE_PRODUCTOS.includes(key)
      }))
    }
  }
  loadingProductos.value = false
})
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

.kpi-section { display: flex; gap: 12px; flex-wrap: wrap; }
.kpi-card    {
  flex: 1; min-width: 160px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 4px;
}
.kpi-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }

/* Pill Tabs — Manual sección 26 */
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
  border-color: var(--accent-border);
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}
.pill-tab-badge {
  background: var(--color-accent);
  color: white;
  border-radius: 10px;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
}
</style>
