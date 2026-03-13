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
          <span class="bc-current">{{ canal }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ canal }}</h1>
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
              <span class="kpi-label">Descuentos</span>
              <span class="kpi-value">{{ fmt$(kpi.fin_descuentos) }}</span>
            </div>
          </div>
        </div>

        <!-- Volumen -->
        <div class="kpi-section">
          <div class="kpi-section-label">Volumen</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Facturas</span>
              <span class="kpi-value">{{ kpi.vol_num_facturas }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Ticket Promedio</span>
              <span class="kpi-value">{{ fmt$(kpi.vol_ticket_promedio) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Unidades</span>
              <span class="kpi-value">{{ fmtNum(kpi.vol_unidades_vendidas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Clientes Activos</span>
              <span class="kpi-value">{{ kpi.cli_clientes_activos }}</span>
            </div>
          </div>
        </div>

        <!-- Top -->
        <div class="kpi-section">
          <div class="kpi-section-label">Top del canal</div>
          <div class="kpi-grid kpi-grid-wide">
            <div class="kpi-card">
              <span class="kpi-label">Top Cliente</span>
              <span class="kpi-value kpi-text">{{ kpi.top_cliente || '—' }}</span>
              <span class="kpi-sub-value">{{ fmt$(kpi.top_cliente_ventas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Top Producto</span>
              <span class="kpi-value kpi-text">{{ kpi.top_producto_nombre || '—' }}</span>
              <span class="kpi-sub-value">{{ fmt$(kpi.top_producto_ventas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Consignación PP</span>
              <span class="kpi-value">{{ fmt$(kpi.con_consignacion_pp) }}</span>
            </div>
          </div>
        </div>

      </template>

      <!-- ── SEPARADOR ── -->
      <div class="section-divider" />

      <!-- ── ACORDEONES ── -->
      <div class="acordeones">

        <!-- Clientes -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('clientes')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.clientes }" />
              <span class="ac-title">Clientes</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resClientes.length }} clientes</span>
          </button>
          <div v-if="abiertos.clientes" class="acordeon-body">
            <OsDataTable title="Clientes" :rows="resClientes" :columns="colsClientes" :loading="loadingClientes"
              @row-click="row => router.push(`/ventas/detalle-cliente/${mes}/${encodeURIComponent(row.id_cliente)}`)" />
          </div>
        </div>

        <!-- Productos -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('productos')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.productos }" />
              <span class="ac-title">Productos</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resProductos.length }} referencias</span>
          </button>
          <div v-if="abiertos.productos" class="acordeon-body">
            <OsDataTable title="Productos" :rows="resProductos" :columns="colsProductos" :loading="loadingProductos"
              @row-click="row => router.push(`/ventas/detalle-producto/${mes}/${encodeURIComponent(row.cod_articulo)}`)" />
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
              @row-click="row => router.push({ path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`, query: { mes, desde: 'canal', desde_id: canal, desde_label: canal } })" />
          </div>
        </div>

        <!-- Remisiones -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('remisiones')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.remisiones }" />
              <span class="ac-title">Remisiones</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resRemisiones.length }} registros</span>
          </button>
          <div v-if="abiertos.remisiones" class="acordeon-body">
            <OsDataTable title="Remisiones" recurso="remisiones" :rows="resRemisiones" :columns="colsRemisiones" :loading="loadingRemisiones" :mes="mes" />
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

const route  = useRoute()
const router = useRouter()
const API    = '/api'
const mes    = route.params.mes
const canal  = decodeURIComponent(route.params.canal)

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
    const { data } = await axios.get(`${API}/ventas/resumen-canal`, {
      params: { mes, filters: JSON.stringify([{ field: 'canal', op: 'eq', value: canal }]) }
    })
    kpi.value = data[0] || null
  } finally { loadingKpi.value = false }
}

// ── Tablas ───────────────────────────────────────────
const resClientes   = ref([]); const loadingClientes   = ref(false)
const resProductos  = ref([]); const loadingProductos  = ref(false)
const resFacturas   = ref([]); const loadingFacturas   = ref(false)
const resRemisiones = ref([]); const loadingRemisiones = ref(false)

const colsClientes   = ref([])
const colsProductos  = ref([])
const colsFacturas   = ref([])
const colsRemisiones = ref([])

const VISIBLE = {
  'canal_clientes':                    ['id_cliente','cliente','fin_ventas_netas_sin_iva','vol_num_facturas','vol_unidades_vendidas'],
  'canal_productos':                   ['cod_articulo','nombre','fin_ventas_netas_sin_iva','vol_unidades_vendidas','vol_num_facturas'],
  'zeffi_facturas_venta_encabezados':  ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc','dias_mora'],
  'zeffi_remisiones_venta_encabezados': ['fecha_de_creacion','id_remision','cliente','ciudad','vendedor','total_neto','estado_remision','estado_cxc','dias_mora'],
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
const abiertos = ref({ clientes: false, productos: false, facturas: false, remisiones: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return
  const loaders = {
    clientes:   () => loadAd(`${API}/ventas/canal-clientes`,  resClientes,   loadingClientes,   'canal_clientes'),
    productos:  () => loadAd(`${API}/ventas/canal-productos`,  resProductos,  loadingProductos,  'canal_productos'),
    facturas:   () => loadAd(`${API}/ventas/canal-facturas`,   resFacturas,   loadingFacturas,   'zeffi_facturas_venta_encabezados'),
    remisiones: () => loadAd(`${API}/ventas/canal-remisiones`, resRemisiones, loadingRemisiones, 'zeffi_remisiones_venta_encabezados'),
  }
  if (loaders[key]) loaders[key]()
}

async function loadAd(url, dataRef, loadingRef, tabla) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes, canal } })
    dataRef.value = data
    const colsMap = {
      'canal_clientes':   colsClientes,
      'canal_productos':  colsProductos,
      'zeffi_facturas_venta_encabezados':   colsFacturas,
      'zeffi_remisiones_venta_encabezados': colsRemisiones,
    }
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
    loadColumns('zeffi_remisiones_venta_encabezados', colsRemisiones),
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
.kpi-sub-value     { font-size: 11px; color: var(--text-tertiary); }
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
