<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Resumen Facturación</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-link" @click="router.push(`/ventas/detalle-mes/${mes}`)">{{ nombreMes(mes) }}</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">{{ kpi?.nombre || cod_articulo }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ kpi?.nombre || cod_articulo }}</h1>
          <span class="page-subtitle">{{ nombreMes(mes) }}</span>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- ── KPIs ── -->
      <div v-if="loadingKpi" class="kpi-grid">
        <div v-for="n in 6" :key="n" class="kpi-card skeleton-kpi" />
      </div>
      <template v-else-if="kpi">

        <!-- Financiero -->
        <div class="kpi-section">
          <div class="kpi-section-label">Financiero</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Ventas Netas s/IVA</span>
              <span class="kpi-value">{{ fmt$(kpi.fin_ventas_netas_sin_iva) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">% del mes</span>
              <span class="kpi-value">{{ fmtPct(kpi.fin_pct_del_mes) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Precio Promedio</span>
              <span class="kpi-value">{{ fmt$(kpi.fin_precio_promedio) }}</span>
            </div>
          </div>
        </div>

        <!-- Volumen -->
        <div class="kpi-section">
          <div class="kpi-section-label">Volumen</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Unidades Vendidas</span>
              <span class="kpi-value">{{ fmtNum(kpi.vol_unidades_vendidas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Facturas</span>
              <span class="kpi-value">{{ kpi.vol_num_facturas }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Clientes Activos</span>
              <span class="kpi-value">{{ kpi.cli_clientes_activos }}</span>
            </div>
          </div>
        </div>

        <!-- Info -->
        <div class="kpi-section">
          <div class="kpi-section-label">Producto</div>
          <div class="kpi-grid kpi-grid-wide">
            <div class="kpi-card">
              <span class="kpi-label">Código</span>
              <span class="kpi-value kpi-text">{{ kpi.cod_articulo || cod_articulo }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Categoría</span>
              <span class="kpi-value kpi-text">{{ kpi.categoria || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Top Cliente</span>
              <span class="kpi-value kpi-text">{{ kpi.top_cliente_nombre || '—' }}</span>
            </div>
          </div>
        </div>

      </template>

      <!-- ── SEPARADOR ── -->
      <div class="section-divider" />

      <!-- ── ACORDEONES ── -->
      <div class="acordeones">

        <!-- Canales -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('canales')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.canales }" />
              <span class="ac-title">Por canal de ventas</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resCanales.length }} canales</span>
          </button>
          <div v-if="abiertos.canales" class="acordeon-body">
            <OsDataTable title="Canales" :rows="resCanales" :columns="colsCanales" :loading="loadingCanales"
              @row-dblclick="row => router.push(`/ventas/detalle-canal/${mes}/${encodeURIComponent(row.canal)}`)" />
          </div>
        </div>

        <!-- Clientes -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('clientes')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.clientes }" />
              <span class="ac-title">Clientes que compraron</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resClientes.length }} clientes</span>
          </button>
          <div v-if="abiertos.clientes" class="acordeon-body">
            <OsDataTable title="Clientes" :rows="resClientes" :columns="colsClientes" :loading="loadingClientes"
              @row-dblclick="row => router.push(`/ventas/detalle-cliente/${mes}/${encodeURIComponent(row.id_cliente)}`)" />
          </div>
        </div>

        <!-- Facturas -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('facturas')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.facturas }" />
              <span class="ac-title">Facturas</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resFacturas.length }} facturas</span>
          </button>
          <div v-if="abiertos.facturas" class="acordeon-body">
            <OsDataTable title="Facturas" recurso="facturas" :rows="resFacturas" :columns="colsFacturas" :loading="loadingFacturas" :mes="mes"
              @row-dblclick="row => router.push({ path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`, query: { mes, desde: 'producto', desde_id: cod_articulo, desde_label: kpi?.nombre || cod_articulo } })" />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const route       = useRoute()
const router      = useRouter()
const API         = '/api'
const mes         = route.params.mes
const cod_articulo = decodeURIComponent(route.params.cod_articulo)

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
function nombreMes(m) {
  if (!m) return m
  const [y, mo] = m.split('-')
  return `${MESES[parseInt(mo) - 1]} ${y}`
}

// ── KPI ──────────────────────────────────────────────
const kpi        = ref(null)
const loadingKpi = ref(true)

async function loadKpi() {
  loadingKpi.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-producto`, {
      params: { mes, filters: JSON.stringify([{ field: 'cod_articulo', op: 'eq', value: cod_articulo }]) }
    })
    kpi.value = data[0] || null
  } finally { loadingKpi.value = false }
}

// ── Tablas ───────────────────────────────────────────
const resCanales  = ref([]); const loadingCanales  = ref(false)
const resClientes = ref([]); const loadingClientes = ref(false)
const resFacturas = ref([]); const loadingFacturas = ref(false)

const colsCanales  = ref([])
const colsClientes = ref([])
const colsFacturas = ref([])

const VISIBLE = {
  'producto_canales':                  ['canal','fin_ventas_netas_sin_iva','vol_unidades_vendidas','cli_clientes_activos'],
  'producto_clientes':                 ['id_cliente','cliente','fin_ventas_netas_sin_iva','vol_unidades_vendidas'],
  'zeffi_facturas_venta_encabezados':  ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc','dias_mora'],
}

function colsFromData(data, tabla) {
  if (!data.length) return []
  const visible = VISIBLE[tabla] || []
  return Object.keys(data[0]).map(key => ({ key, label: labelFromKey(key), visible: visible.includes(key) }))
}

function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'
  return key.replace(/^_pk$/, 'N°').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '').replace(/^Vol /, '').replace(/^Cli /, '').replace(/^Cto /, '').trim()
}

async function loadColumns(tabla, destRef) {
  const { data: cols } = await axios.get(`${API}/columnas/${tabla}`)
  const visible = VISIBLE[tabla] || []
  destRef.value = cols.map(key => ({ key, label: labelFromKey(key), visible: visible.includes(key) }))
}

// ── Acordeones ───────────────────────────────────────
const abiertos = ref({ canales: false, clientes: false, facturas: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return
  const loaders = {
    canales:  () => loadAd(`${API}/ventas/producto-canales`,  resCanales,  loadingCanales,  'producto_canales'),
    clientes: () => loadAd(`${API}/ventas/producto-clientes`, resClientes, loadingClientes, 'producto_clientes'),
    facturas: () => loadAd(`${API}/ventas/producto-facturas`, resFacturas, loadingFacturas, 'zeffi_facturas_venta_encabezados'),
  }
  if (loaders[key]) loaders[key]()
}

async function loadAd(url, dataRef, loadingRef, tabla) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes, cod_articulo } })
    dataRef.value = data
    const colsMap = { 'producto_canales': colsCanales, 'producto_clientes': colsClientes, 'zeffi_facturas_venta_encabezados': colsFacturas }
    if (colsMap[tabla] && !colsMap[tabla].value.length) {
      colsMap[tabla].value = colsFromData(data, tabla)
    }
  } finally { loadingRef.value = false }
}

function fmt$(v) {
  const n = parseFloat(String(v || 0).replace(',', '.'))
  return isNaN(n) ? '—' : '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}
function fmtPct(v) { const n = parseFloat(v); return isNaN(n) ? '—' : (n * 100).toFixed(1) + '%' }
function fmtNum(v) { const n = parseFloat(v); return isNaN(n) ? '—' : n.toLocaleString('es-CO', { maximumFractionDigits: 0 }) }

onMounted(async () => {
  await Promise.all([
    loadKpi(),
    loadColumns('zeffi_facturas_venta_encabezados', colsFacturas),
  ])
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
.acordeones       { display: flex; flex-direction: column; gap: 8px; }
.acordeon         { border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-card); }
.acordeon-header  { display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0 14px; height: 42px; border: none; background: transparent; cursor: pointer; transition: background 80ms; font-family: var(--font-sans); }
.acordeon-header:hover { background: var(--bg-card-hover); }
.ac-left     { display: flex; align-items: center; gap: 8px; }
.ac-chevron  { color: var(--text-tertiary); transition: transform 150ms ease-out; }
.ac-chevron.open { transform: rotate(90deg); }
.ac-title    { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ac-mes-tag  { font-size: 11px; font-weight: 500; color: var(--accent); background: var(--accent-muted); border: 1px solid var(--accent-border); padding: 1px 7px; border-radius: var(--radius-full); }
.ac-count    { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
</style>
