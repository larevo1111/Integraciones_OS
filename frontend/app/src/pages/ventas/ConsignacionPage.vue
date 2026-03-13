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
      <div v-if="!loading && rows.length > 0" class="kpi-section">
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

      <!-- Tabla resumen por cliente -->
      <OsDataTable
        title="Consignación por cliente"
        recurso="consignacion"
        :rows="rows"
        :columns="cols"
        :loading="loading"
        @row-click="onRowClick"
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
const rows    = ref([])
const cols    = ref([])
const loading = ref(true)

const VISIBLE = [
  'nombre_cliente', 'ciudad', 'vendedor',
  'num_ordenes', 'fin_total_consignacion',
  'fecha_primera_orden', 'fecha_ultima_orden'
]

const LABELS = {
  nombre_cliente:        'Cliente',
  ciudad:                'Ciudad',
  vendedor:              'Vendedor',
  num_ordenes:           'Órdenes',
  fin_total_consignacion:'Total consignación',
  fecha_primera_orden:   'Primera orden',
  fecha_ultima_orden:    'Última orden',
  id_cliente:            'ID Cliente',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const kpis = computed(() => ({
  numClientes:       rows.value.length,
  numOrdenes:        rows.value.reduce((s, r) => s + (parseInt(r.num_ordenes) || 0), 0),
  totalConsignacion: rows.value.reduce((s, r) => s + (parseFloat(r.fin_total_consignacion) || 0), 0),
}))

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClick(row) {
  router.push(`/ventas/consignacion-cliente/${encodeURIComponent(row.id_cliente)}`)
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/consignacion`)
    rows.value = data
    if (data.length > 0) {
      cols.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key), visible: VISIBLE.includes(key)
      }))
    }
  } finally { loading.value = false }
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
</style>
