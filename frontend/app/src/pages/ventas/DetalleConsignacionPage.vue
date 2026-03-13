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
          <span class="bc-link" @click="goBack">{{ encabezado?.nombre_cliente || '…' }}</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">{{ id_orden }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ encabezado?.nombre_cliente || id_orden }}</h1>
          <span class="page-subtitle">{{ id_orden }}</span>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- KPIs del encabezado -->
      <div v-if="encabezado && !loading" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Ciudad</span>
          <span class="kpi-value kpi-text">{{ encabezado.ciudad || '—' }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Vendedor</span>
          <span class="kpi-value kpi-text">{{ encabezado.vendedor || '—' }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Fecha creación</span>
          <span class="kpi-value kpi-text">{{ fmtFecha(encabezado.fecha_de_creacion) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Fecha entrega</span>
          <span class="kpi-value kpi-text">{{ encabezado.fecha_de_entrega || '—' }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Total orden</span>
          <span class="kpi-value">{{ fmtMoney(encabezado.total_neto) }}</span>
        </div>
      </div>

      <!-- Tabla ítems -->
      <OsDataTable
        title="Ítems de la orden"
        :rows="items"
        :columns="cols"
        :loading="loading"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const route    = useRoute()
const router   = useRouter()
const API      = '/api'
const id_orden = decodeURIComponent(route.params.id_orden)

const encabezado = ref(null)
const items      = ref([])
const cols       = ref([])
const loading    = ref(true)

const VISIBLE = ['cod_articulo', 'descripcion_articulo', 'cantidad', 'precio_unitario', 'total']

const LABELS = {
  cod_articulo:         'Cód. Artículo',
  descripcion_articulo: 'Producto',
  cantidad:             'Cantidad',
  precio_unitario:      'Precio unitario',
  total:                'Total',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function fmtMoney(v) {
  const n = parseFloat(String(v || '0').replace(',', '.'))
  if (isNaN(n)) return '—'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function fmtFecha(v) {
  if (!v) return '—'
  return String(v).slice(0, 10)
}

function goBack() {
  if (encabezado.value?.id_cliente) {
    router.push(`/ventas/consignacion-cliente/${encodeURIComponent(encabezado.value.id_cliente)}`)
  } else {
    router.push('/ventas/consignacion')
  }
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/ventas/consignacion-orden/${encodeURIComponent(id_orden)}`)
    encabezado.value = data.encabezado
    items.value = data.items || []
    if (data.items?.length > 0) {
      cols.value = Object.keys(data.items[0]).map(key => ({
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
.page-subtitle     { font-size: 13px; color: var(--text-tertiary); }

.kpi-section { display: flex; gap: 12px; flex-wrap: wrap; }
.kpi-card    {
  flex: 1; min-width: 140px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 4px;
}
.kpi-label      { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value      { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.kpi-value.kpi-text { font-size: 13px; font-weight: 500; }
</style>
