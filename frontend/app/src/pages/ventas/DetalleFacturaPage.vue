<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Ventas</span>
          <template v-if="qMes">
            <ChevronRightIcon :size="13" />
            <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Resumen Facturación</span>
            <ChevronRightIcon :size="13" />
            <span class="bc-link" @click="router.push(`/ventas/detalle-mes/${qMes}`)">{{ nombreMes(qMes) }}</span>
            <template v-if="qDesde !== 'mes' && DESDE_CONFIG[qDesde]?.path">
              <ChevronRightIcon :size="13" />
              <span class="bc-link" @click="router.push(DESDE_CONFIG[qDesde].path)">{{ DESDE_CONFIG[qDesde].label }}</span>
            </template>
          </template>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Factura #{{ id_numeracion }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Factura #{{ id_numeracion }}</h1>
          <span v-if="encabezado" class="page-subtitle">{{ encabezado.cliente }}</span>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- ── ENCABEZADO KPIs ── -->
      <div v-if="loading" class="kpi-grid">
        <div v-for="n in 8" :key="n" class="kpi-card skeleton-kpi" />
      </div>
      <template v-else-if="encabezado">

        <!-- Cliente / Fecha -->
        <div class="kpi-section">
          <div class="kpi-section-label">Factura</div>
          <div class="kpi-grid kpi-grid-wide">
            <div class="kpi-card">
              <span class="kpi-label">Fecha</span>
              <span class="kpi-value kpi-text">{{ encabezado.fecha_de_creacion?.slice(0,10) || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Cliente</span>
              <span class="kpi-value kpi-text">{{ encabezado.cliente || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Ciudad</span>
              <span class="kpi-value kpi-text">{{ encabezado.ciudad || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Vendedor</span>
              <span class="kpi-value kpi-text">{{ encabezado.vendedor || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Totales -->
        <div class="kpi-section">
          <div class="kpi-section-label">Totales</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Subtotal</span>
              <span class="kpi-value">{{ fmt$(encabezado.subtotal) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Descuentos</span>
              <span class="kpi-value kpi-neg">{{ fmt$(encabezado.descuentos) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Total Neto</span>
              <span class="kpi-value kpi-pos">{{ fmt$(encabezado.total_neto) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Estado CxC</span>
              <span class="kpi-value kpi-text">{{ encabezado.estado_cxc || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Días Mora</span>
              <span class="kpi-value" :class="(encabezado.dias_mora || 0) > 0 ? 'kpi-neg' : ''">
                {{ encabezado.dias_mora ?? '—' }}
              </span>
            </div>
          </div>
        </div>

      </template>

      <!-- ── SEPARADOR ── -->
      <div class="section-divider" />

      <!-- ── ITEMS TABLE ── -->
      <div class="acordeon">
        <div class="acordeon-header-static">
          <span class="ac-title">Ítems de la factura</span>
          <span class="ac-count">{{ items.length }} líneas</span>
        </div>
        <div class="acordeon-body">
          <OsDataTable
            title="Ítems"
            :rows="items"
            :columns="colsItems"
            :loading="loading"
          />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const route        = useRoute()
const router       = useRouter()
const API          = '/api'
const id_interno   = route.params.id_interno
const id_numeracion = route.params.id_numeracion

// Contexto de navegación (desde dónde llegamos)
const qMes        = route.query.mes        || ''
const qDesde      = route.query.desde      || ''
const qDesdeId    = route.query.desde_id   || ''
const qDesdeLabel = route.query.desde_label || ''

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
function nombreMes(m) {
  if (!m) return m
  const [y, mo] = m.split('-')
  return `${MESES[parseInt(mo) - 1]} ${y}`
}

const DESDE_CONFIG = {
  cliente:  { label: qDesdeLabel, path: qMes && qDesdeId ? `/ventas/detalle-cliente/${qMes}/${encodeURIComponent(qDesdeId)}` : null },
  canal:    { label: qDesdeLabel, path: qMes && qDesdeId ? `/ventas/detalle-canal/${qMes}/${encodeURIComponent(qDesdeId)}` : null },
  producto: { label: qDesdeLabel, path: qMes && qDesdeId ? `/ventas/detalle-producto/${qMes}/${encodeURIComponent(qDesdeId)}` : null },
  mes:      { label: null, path: qMes ? `/ventas/detalle-mes/${qMes}` : null },
}

const encabezado = ref(null)
const items      = ref([])
const colsItems  = ref([])
const loading    = ref(true)

const VISIBLE_ITEMS = ['id_numeracion','cod_articulo','descripcion_articulo','cantidad','precio_unitario','descuento_total','precio_bruto_total','bodega']

function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'
  if (key === 'descripcion_articulo') return 'Producto'
  return key.replace(/^_pk$/, 'N°').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).trim()
}

async function loadFactura() {
  loading.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/factura/${id_interno}/${id_numeracion}`)
    encabezado.value = data.encabezado
    items.value      = data.items || []
    if (items.value.length) {
      colsItems.value = Object.keys(items.value[0]).map(key => ({
        key, label: labelFromKey(key),
        visible: VISIBLE_ITEMS.includes(key)
      }))
    }
  } finally { loading.value = false }
}

function fmt$(v) {
  const n = parseFloat(String(v || 0).replace(',', '.'))
  return isNaN(n) ? '—' : '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

onMounted(loadFactura)
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
.kpi-section       { display: flex; flex-direction: column; gap: 8px; }
.kpi-section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); }
.kpi-grid          { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; }
.kpi-grid-wide     { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
.kpi-card          { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: var(--radius-lg); padding: 10px 12px; display: flex; flex-direction: column; gap: 3px; }
.kpi-label         { font-size: 10px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value         { font-size: 14px; font-weight: 600; color: var(--text-primary); line-height: 1.2; }
.kpi-value.kpi-text { font-size: 12px; font-weight: 500; }
.kpi-pos           { color: var(--color-success); }
.kpi-neg           { color: var(--color-error); }
.skeleton-kpi { height: 60px; background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.09) 50%, rgba(0,0,0,0.05) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.section-divider { height: 1px; background: var(--border-subtle); }
.acordeon         { border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-card); }
.acordeon-header-static { display: flex; align-items: center; justify-content: space-between; padding: 0 14px; height: 42px; }
.ac-title    { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ac-count    { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
</style>
