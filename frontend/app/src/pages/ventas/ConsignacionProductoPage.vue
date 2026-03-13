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
          <span class="bc-current">{{ descripcion || cod_articulo }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ descripcion || cod_articulo }}</h1>
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
          <span class="kpi-label">Cantidad en calle</span>
          <span class="kpi-value">{{ kpis.cantidadTotal }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Total producto</span>
          <span class="kpi-value">{{ fmtMoney(kpis.totalProducto) }}</span>
        </div>
      </div>

      <!-- Tabla órdenes del producto -->
      <OsDataTable
        :title="`Órdenes con ${descripcion || cod_articulo}`"
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

const route       = useRoute()
const router      = useRouter()
const API         = '/api'
const cod_articulo = decodeURIComponent(route.params.cod_articulo)

const rows    = ref([])
const cols    = ref([])
const loading = ref(true)

const VISIBLE = [
  'id_orden', 'nombre_cliente', 'ciudad', 'vendedor',
  'cantidad_producto', 'fin_total_producto', 'fecha_de_creacion', 'fecha_de_entrega', 'dias_en_calle'
]

const LABELS = {
  id_orden:           'N° Orden',
  nombre_cliente:     'Cliente',
  ciudad:             'Ciudad',
  vendedor:           'Vendedor',
  cantidad_producto:  'Cantidad',
  fin_total_producto: 'Total producto',
  fin_total_orden:    'Total orden',
  fecha_de_creacion:  'Fecha creación',
  fecha_de_entrega:   'Fecha entrega',
  dias_en_calle:      'Días en calle',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const descripcion = computed(() => rows.value[0]?._descripcion || '')

const kpis = computed(() => ({
  cantidadTotal: rows.value.reduce((s, r) => s + (parseFloat(r.cantidad_producto) || 0), 0),
  totalProducto: rows.value.reduce((s, r) => s + (parseFloat(r.fin_total_producto) || 0), 0),
}))

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onRowClick(row) {
  router.push(`/ventas/consignacion-orden/${encodeURIComponent(row.id_orden)}`)
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/consignacion-producto/${encodeURIComponent(cod_articulo)}`)
    const today = new Date()
    data.forEach(r => {
      r._descripcion = r.descripcion_articulo || ''
      if (r.fecha_de_creacion) {
        const d = new Date(r.fecha_de_creacion.replace(' ', 'T'))
        r.dias_en_calle = Math.floor((today - d) / 86400000)
      } else {
        r.dias_en_calle = null
      }
    })
    rows.value = data
    if (data.length > 0) {
      cols.value = Object.keys(data[0])
        .filter(k => k !== '_descripcion')
        .map(key => ({ key, label: labelFromKey(key), visible: VISIBLE.includes(key) }))
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
