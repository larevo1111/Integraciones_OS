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
      <div v-if="!loadingFacturas && resCartera.length > 0" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Total pendiente</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalPendiente) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Facturas pendientes</span>
          <span class="kpi-value">{{ kpis.numFacturas }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Clientes con saldo</span>
          <span class="kpi-value">{{ kpis.numClientes }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Total mora</span>
          <span class="kpi-value kpi-danger">{{ fmtMoney(kpis.totalMora) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Mayor mora</span>
          <span class="kpi-value kpi-danger">{{ kpis.maxDiasMora }} días</span>
        </div>
      </div>

      <!-- Tabla facturas pendientes -->
      <OsDataTable
        title="Facturas con saldo pendiente"
        recurso="cartera"
        :rows="resCartera"
        :columns="colsCartera"
        :loading="loadingFacturas"
        @row-click="onFacturaClick"
      />

      <!-- Tabla resumen por cliente -->
      <OsDataTable
        title="Cartera por cliente"
        :rows="resCliente"
        :columns="colsCliente"
        :loading="loadingCliente"
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

const resCartera      = ref([])
const loadingFacturas = ref(true)
const colsCartera     = ref([])

const resCliente      = ref([])
const loadingCliente  = ref(true)
const colsCliente     = ref([])

const VISIBLE_CARTERA = ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','total_neto','pdte_de_cobro','estado_cxc','dias_mora','valor_mora','formas_de_pago']
const VISIBLE_CLIENTE = ['cliente','ciudad','vendedor','num_facturas_pendientes','total_pendiente','total_mora','max_dias_mora','factura_mas_antigua']

function labelFromKey(key) {
  const MAP = {
    id_numeracion: 'N° Factura',
    fecha_de_creacion: 'Fecha',
    pdte_de_cobro: 'Saldo pendiente',
    estado_cxc: 'Estado CxC',
    dias_mora: 'Días mora',
    valor_mora: 'Valor mora',
    total_neto: 'Total factura',
    formas_de_pago: 'Forma de pago',
    num_facturas_pendientes: 'Facturas pend.',
    total_pendiente: 'Total pendiente',
    total_mora: 'Total mora',
    max_dias_mora: 'Máx días mora',
    factura_mas_antigua: 'Factura más antigua',
  }
  if (MAP[key]) return MAP[key]
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).trim()
}

const kpis = computed(() => {
  const rows = resCartera.value
  const totalPendiente = rows.reduce((s, r) => s + (parseFloat(r.pdte_de_cobro) || 0), 0)
  const totalMora = rows.reduce((s, r) => s + (parseFloat(r.valor_mora) || 0), 0)
  const maxDiasMora = rows.reduce((m, r) => Math.max(m, parseInt(r.dias_mora) || 0), 0)
  const clientes = new Set(rows.map(r => r.id_cliente))
  return { totalPendiente, totalMora, maxDiasMora, numFacturas: rows.length, numClientes: clientes.size }
})

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

async function loadCartera() {
  loadingFacturas.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/cartera`)
    resCartera.value = data
    if (data.length > 0) {
      colsCartera.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key), visible: VISIBLE_CARTERA.includes(key)
      }))
    }
  } finally { loadingFacturas.value = false }
}

async function loadCarteraCliente() {
  loadingCliente.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/cartera-cliente`)
    resCliente.value = data
    if (data.length > 0) {
      colsCliente.value = Object.keys(data[0]).map(key => ({
        key, label: labelFromKey(key), visible: VISIBLE_CLIENTE.includes(key)
      }))
    }
  } finally { loadingCliente.value = false }
}

function onFacturaClick(row) {
  if (row.id_interno && row.id_numeracion) {
    router.push(`/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`)
  }
}

onMounted(() => {
  loadCartera()
  loadCarteraCliente()
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

.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

/* KPIs */
.kpi-section {
  display: flex; gap: 12px; flex-wrap: wrap;
}
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
