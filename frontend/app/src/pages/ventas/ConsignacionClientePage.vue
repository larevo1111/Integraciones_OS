<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span class="bc-link" @click="router.push('/ventas/consignacion')">Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-link" @click="router.push('/ventas/consignacion')">Consignación</span>
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
          <span class="kpi-label">Órdenes activas</span>
          <span class="kpi-value">{{ rows.length }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Total consignación</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalConsignacion) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Días máx. en calle</span>
          <span class="kpi-value">{{ kpis.diasMax }}</span>
        </div>
      </div>

      <!-- Tabla órdenes del cliente -->
      <OsDataTable
        :title="`Órdenes — ${nombreCliente || id_cliente}`"
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
  'id_orden', 'ciudad', 'vendedor',
  'total_neto_num', 'fecha_de_creacion', 'fecha_de_entrega', 'dias_en_calle'
]

const LABELS = {
  id_orden:         'N° Orden',
  ciudad:           'Ciudad',
  vendedor:         'Vendedor',
  total_neto_num:   'Total',
  fecha_de_creacion:'Fecha creación',
  fecha_de_entrega: 'Fecha entrega',
  dias_en_calle:    'Días en calle',
  nombre_cliente:   'Cliente',
  id_cliente:       'ID Cliente',
  vigencia:         'Vigencia',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const nombreCliente = computed(() => rows.value[0]?.nombre_cliente || '')

const kpis = computed(() => {
  const today = new Date()
  return {
    totalConsignacion: rows.value.reduce((s, r) => s + (parseFloat(r.total_neto_num) || 0), 0),
    diasMax: rows.value.reduce((m, r) => Math.max(m, r.dias_en_calle || 0), 0),
  }
})

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClick(row) {
  router.push(`/ventas/consignacion-orden/${encodeURIComponent(row.id_orden)}`)
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/consignacion-cliente/${encodeURIComponent(id_cliente)}`)
    const today = new Date()
    data.forEach(r => {
      if (r.fecha_de_creacion) {
        const d = new Date(r.fecha_de_creacion.replace(' ', 'T'))
        r.dias_en_calle = Math.floor((today - d) / 86400000)
      } else {
        r.dias_en_calle = null
      }
    })
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
.kpi-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
</style>
