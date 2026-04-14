<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-link" @click="router.push('/ventas/cartera')">Cuentas por Cobrar</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">{{ nombreCliente }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ nombreCliente || id_cliente }}</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- KPIs -->
      <div v-if="!loading && rows.length > 0" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Total pendiente</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalPendiente) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Facturas pendientes</span>
          <span class="kpi-value">{{ kpis.numFacturas }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Antigüedad máx.</span>
          <span class="kpi-value kpi-danger">{{ kpis.antiguedadMax }} días</span>
        </div>
      </div>

      <!-- Tabla facturas -->
      <OsDataTable
        :title="`Facturas pendientes — ${nombreCliente || id_cliente}`"
        recurso="cartera"
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
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const route      = useRoute()
const router     = useRouter()
const API        = '/api'
const id_cliente = decodeURIComponent(route.params.id_cliente)

const rows    = ref([])
const cols    = ref([])
const loading = ref(true)

const VISIBLE = [
  'tipo_doc', 'id_numeracion', 'fecha_de_creacion', 'vendedor',
  'fin_total_neto', 'fin_pendiente', 'dias_antiguedad', 'estado_cxc'
]

const LABELS = {
  tipo_doc:         'Tipo',
  id_numeracion:    'Documento',
  fecha_de_creacion:'Fecha',
  vendedor:         'Vendedor',
  fin_total_neto:   'Total',
  fin_pendiente:    'Pendiente',
  dias_antiguedad:  'Días antigüedad',
  estado_cxc:       'Estado CxC',
  cliente:          'Cliente',
  id_cliente:       'ID Cliente',
  ciudad:           'Ciudad',
  formas_de_pago:   'Forma de pago',
  id_interno:       'ID Interno',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const nombreCliente = computed(() => rows.value[0]?.cliente || '')

const kpis = computed(() => ({
  totalPendiente: rows.value.reduce((s, r) => s + (parseFloat(r.fin_pendiente) || 0), 0),
  numFacturas:    rows.value.length,
  antiguedadMax:  rows.value.reduce((m, r) => Math.max(m, parseInt(r.dias_antiguedad) || 0), 0),
}))

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClick(row) {
  router.push({
    path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`,
    query: { desde: 'cartera', desde_id: id_cliente, desde_label: nombreCliente.value || id_cliente }
  })
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/cartera-cliente/${encodeURIComponent(id_cliente)}`)
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
.bc-link           { cursor: pointer; transition: color 80ms; }
.bc-link:hover     { color: var(--accent); }
.bc-current        { color: var(--text-secondary); }
.page-title-row    { display: flex; align-items: center; gap: 10px; }
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
.kpi-label  { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value  { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.kpi-danger { color: var(--color-error, #ef4444); }
</style>
