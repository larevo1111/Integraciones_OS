<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Cartera CxC</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Cartera — Cuentas por Cobrar</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- KPIs -->
      <div v-if="!loading && resCliente.length > 0" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Total pendiente</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalPendiente) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Clientes con saldo</span>
          <span class="kpi-value">{{ kpis.numClientes }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Facturas pendientes</span>
          <span class="kpi-value">{{ kpis.numFacturas }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Saldo en mora (+30 días)</span>
          <span class="kpi-value kpi-danger">{{ fmtMoney(kpis.totalMora) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Mayor antigüedad</span>
          <span class="kpi-value kpi-danger">{{ kpis.antiguedadMax }} días</span>
        </div>
      </div>

      <!-- Tabla cartera por cliente -->
      <OsDataTable
        title="Cartera por cliente"
        recurso="cartera-cliente"
        :rows="resCliente"
        :columns="colsCliente"
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

const router     = useRouter()
const API = '/api'
const resCliente = ref([])
const loading    = ref(true)
const colsCliente = ref([])

const VISIBLE = [
  'cliente', 'ciudad', 'vendedor', 'plazo',
  'num_facturas_pendientes', 'total_pendiente',
  'saldo_1_30', 'saldo_31_60', 'saldo_61_90', 'saldo_mas_90',
  'promedio_antiguedad', 'antiguedad_max'
]

const LABELS = {
  cliente:                 'Cliente',
  ciudad:                  'Ciudad',
  vendedor:                'Vendedor',
  plazo:                   'Plazo',
  num_facturas_pendientes: 'Facturas pend.',
  total_pendiente:         'Total pendiente',
  saldo_1_30:              '1–30 días',
  saldo_31_60:             '31–60 días',
  saldo_61_90:             '61–90 días',
  saldo_mas_90:            '+90 días',
  promedio_antiguedad:     'Prom. antigüedad',
  antiguedad_max:          'Antigüedad máx.',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const kpis = computed(() => {
  const rows = resCliente.value
  return {
    totalPendiente: rows.reduce((s, r) => s + (parseFloat(r.total_pendiente) || 0), 0),
    numClientes:    rows.length,
    numFacturas:    rows.reduce((s, r) => s + (parseInt(r.num_facturas_pendientes) || 0), 0),
    totalMora:      rows.reduce((s, r) => s + (parseFloat(r.saldo_31_60) || 0)
                                           + (parseFloat(r.saldo_61_90) || 0)
                                           + (parseFloat(r.saldo_mas_90) || 0), 0),
    antiguedadMax:  rows.reduce((m, r) => Math.max(m, parseInt(r.antiguedad_max) || 0), 0),
  }
})

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/cartera-cliente`)
    resCliente.value = data
    if (data.length > 0) {
      colsCliente.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key), visible: VISIBLE.includes(key)
      }))
    }
  } finally { loading.value = false }
})

function onRowClick(row) {
  router.push(`/ventas/cartera/${encodeURIComponent(row.id_cliente)}`)
}
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

.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

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
.kpi-danger { color: var(--color-error, #ef4444); }
</style>
