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
          <span class="bc-current">{{ kpi?.cliente || id_cliente }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ kpi?.cliente || id_cliente }}</h1>
          <span class="page-subtitle">{{ nombreMes(mes) }}</span>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- ── KPIs ── -->
      <div v-if="loadingKpi" class="kpi-grid">
        <div v-for="n in 8" :key="n" class="kpi-card skeleton-kpi" />
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
          </div>
        </div>

        <!-- Info -->
        <div class="kpi-section">
          <div class="kpi-section-label">Perfil</div>
          <div class="kpi-grid kpi-grid-wide">
            <div class="kpi-card">
              <span class="kpi-label">Ciudad</span>
              <span class="kpi-value kpi-text">{{ kpi.ciudad || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Canal</span>
              <span class="kpi-value kpi-text">{{ kpi.canal || '—' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">¿Cliente Nuevo?</span>
              <span class="kpi-value kpi-text" :class="kpi.cli_es_nuevo ? 'kpi-pos' : ''">{{ kpi.cli_es_nuevo ? 'Sí' : 'No' }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Top Producto</span>
              <span class="kpi-value kpi-text">{{ kpi.top_producto_nombre || '—' }}</span>
            </div>
          </div>
        </div>

      </template>

      <!-- ── SEPARADOR ── -->
      <div class="section-divider" />

      <!-- ── ACORDEONES ── -->
      <div class="acordeones">

        <!-- Productos -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('productos')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.productos }" />
              <span class="ac-title">Productos comprados</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resProductos.length }} referencias</span>
          </button>
          <div v-if="abiertos.productos" class="acordeon-body">
            <OsDataTable title="Productos" :rows="resProductos" :columns="colsProductos" :loading="loadingProductos" />
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
              @row-click="row => router.push({ path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`, query: { mes, desde: 'cliente', desde_id: id_cliente, desde_label: kpi?.cliente || id_cliente } })" />
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

        <!-- Cotizaciones -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('cotizaciones')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.cotizaciones }" />
              <span class="ac-title">Cotizaciones / Pedidos</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resCotizaciones.length }} registros</span>
          </button>
          <div v-if="abiertos.cotizaciones" class="acordeon-body">
            <OsDataTable title="Cotizaciones" recurso="cotizaciones" :rows="resCotizaciones" :columns="colsCotizaciones" :loading="loadingCotizaciones" :mes="mes" />
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

const route      = useRoute()
const router     = useRouter()
const API        = '/api'
const mes        = route.params.mes
const id_cliente = decodeURIComponent(route.params.id_cliente)

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
    const { data } = await axios.get(`${API}/ventas/resumen-cliente`, {
      params: { mes, filters: JSON.stringify([{ field: 'id_cliente', op: 'eq', value: id_cliente }]) }
    })
    kpi.value = data[0] || null
  } finally { loadingKpi.value = false }
}

// ── Tablas ───────────────────────────────────────────
const resProductos    = ref([]); const loadingProductos    = ref(false)
const resFacturas     = ref([]); const loadingFacturas     = ref(false)
const resRemisiones   = ref([]); const loadingRemisiones   = ref(false)
const resCotizaciones = ref([]); const loadingCotizaciones = ref(false)

const colsProductos    = ref([])
const colsFacturas     = ref([])
const colsRemisiones   = ref([])
const colsCotizaciones = ref([])

const DEFAULT_VISIBLE = {
  'cliente_productos':                   ['cod_articulo','nombre','fin_ventas_netas_sin_iva','vol_unidades_vendidas','vol_num_facturas'],
  'zeffi_facturas_venta_encabezados':    ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc','dias_mora'],
  'zeffi_remisiones_venta_encabezados':  ['fecha_de_creacion','id_remision','cliente','ciudad','vendedor','total_neto','estado_remision','estado_cxc','dias_mora'],
  'zeffi_cotizaciones_ventas_encabezados': ['fecha_de_creacion','id_cotizacion','cliente','ciudad','vendedor','total_bruto','descuentos','total_neto','estado_cotizacion','estado'],
}

function colsFromData(data, tabla) {
  if (!data.length) return []
  const visible = DEFAULT_VISIBLE[tabla] || []
  return Object.keys(data[0]).map(key => ({
    key,
    label: labelFromKey(key),
    visible: visible.length ? visible.includes(key) : true
  }))
}

function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'
  return key
    .replace(/^_pk$/, 'N°')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '').replace(/^Vol /, '').replace(/^Cli /, '')
    .replace(/^Cto /, '').replace(/^Con /, '').replace(/^Top /, 'Top ')
    .trim()
}

async function loadColumns(tabla, destRef) {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/${tabla}`)
    const visible = DEFAULT_VISIBLE[tabla] || []
    destRef.value = cols.map(key => ({
      key, label: labelFromKey(key),
      visible: visible.includes(key)
    }))
  } catch(e) { console.error('Error columnas', tabla, e) }
}

// ── Acordeones ───────────────────────────────────────
const abiertos = ref({ productos: false, facturas: false, remisiones: false, cotizaciones: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return
  const loaders = {
    productos:    () => loadAd('productos',    `${API}/ventas/cliente-productos`,  resProductos,    loadingProductos,    'cliente_productos'),
    facturas:     () => loadStd('facturas',    `${API}/ventas/facturas`,           resFacturas,     loadingFacturas),
    remisiones:   () => loadStd('remisiones',  `${API}/ventas/remisiones`,         resRemisiones,   loadingRemisiones),
    cotizaciones: () => loadStd('cotizaciones',`${API}/ventas/cotizaciones`,       resCotizaciones, loadingCotizaciones),
  }
  if (loaders[key]) loaders[key]()
}

async function loadAd(_, url, dataRef, loadingRef, tabla) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes, id_cliente } })
    dataRef.value = data
    if (tabla === 'cliente_productos') {
      colsProductos.value = colsFromData(data, tabla)
    }
  } finally { loadingRef.value = false }
}

async function loadStd(_, url, dataRef, loadingRef) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, {
      params: { mes, filters: JSON.stringify([{ field: 'id_cliente', op: 'eq', value: id_cliente }]) }
    })
    dataRef.value = data
  } finally { loadingRef.value = false }
}

// ── Formatters ───────────────────────────────────────
function fmt$(v) {
  const n = parseFloat(String(v || 0).replace(',', '.'))
  return isNaN(n) ? '—' : '$' + n.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}
function fmtPct(v) {
  const n = parseFloat(v)
  return isNaN(n) ? '—' : (n * 100).toFixed(1) + '%'
}
function fmtNum(v) {
  const n = parseFloat(v)
  return isNaN(n) ? '—' : n.toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

// ── Mount ────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    loadKpi(),
    loadColumns('zeffi_facturas_venta_encabezados',      colsFacturas),
    loadColumns('zeffi_remisiones_venta_encabezados',    colsRemisiones),
    loadColumns('zeffi_cotizaciones_ventas_encabezados', colsCotizaciones),
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
.kpi-warn          { color: var(--color-warning); }

.skeleton-kpi {
  height: 60px;
  background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.09) 50%, rgba(0,0,0,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
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
