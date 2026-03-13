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
          <span class="bc-current">{{ nombreMes(mes) }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Indicadores: {{ nombreMes(mes) }}</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- ── KPIs ── -->
      <div v-if="loadingKpi" class="kpi-grid">
        <div v-for="n in 12" :key="n" class="kpi-card skeleton-kpi" />
      </div>
      <template v-else-if="kpi">

        <!-- Grupo Financiero -->
        <div class="kpi-section">
          <div class="kpi-section-label">Financiero</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Ventas Netas s/IVA</span>
              <span class="kpi-value">{{ fmt$(kpi.fin_ventas_netas_sin_iva) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Devoluciones</span>
              <span class="kpi-value kpi-neg">{{ fmt$(kpi.fin_devoluciones) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Ingresos Netos</span>
              <span class="kpi-value kpi-pos">{{ fmt$(kpi.fin_ingresos_netos) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Descuentos</span>
              <span class="kpi-value">{{ fmt$(kpi.fin_descuentos) }} <span class="kpi-sub">{{ fmtPct(kpi.fin_pct_descuento) }}</span></span>
            </div>
          </div>
        </div>

        <!-- Grupo Costo / Margen -->
        <div class="kpi-section">
          <div class="kpi-section-label">Margen</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Utilidad Bruta</span>
              <span class="kpi-value kpi-pos">{{ fmt$(kpi.cto_utilidad_bruta) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Margen</span>
              <span class="kpi-value" :class="kpi.cto_margen_utilidad_pct >= 0.3 ? 'kpi-pos' : 'kpi-warn'">
                {{ fmtPct(kpi.cto_margen_utilidad_pct) }}
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Costo Total</span>
              <span class="kpi-value">{{ fmt$(kpi.cto_costo_total) }}</span>
            </div>
          </div>
        </div>

        <!-- Grupo Volumen -->
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
              <span class="kpi-label">Unidades Vendidas</span>
              <span class="kpi-value">{{ fmtNum(kpi.vol_unidades_vendidas) }}</span>
            </div>
          </div>
        </div>

        <!-- Grupo Clientes -->
        <div class="kpi-section">
          <div class="kpi-section-label">Clientes</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Clientes Activos</span>
              <span class="kpi-value">{{ kpi.cli_clientes_activos }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Clientes Nuevos</span>
              <span class="kpi-value kpi-pos">{{ kpi.cli_clientes_nuevos }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Venta por Cliente</span>
              <span class="kpi-value">{{ fmt$(kpi.cli_vtas_por_cliente) }}</span>
            </div>
          </div>
        </div>

        <!-- Grupo Proyección (solo si pry_dia_del_mes > 0) -->
        <div v-if="kpi.pry_dia_del_mes > 0" class="kpi-section">
          <div class="kpi-section-label">Proyección</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Proyección Mes</span>
              <span class="kpi-value">{{ fmt$(kpi.pry_proyeccion_mes) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Ritmo</span>
              <span class="kpi-value" :class="kpi.pry_ritmo_pct >= 1 ? 'kpi-pos' : 'kpi-warn'">
                {{ fmtPct(kpi.pry_ritmo_pct) }}
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Día del mes</span>
              <span class="kpi-value">{{ kpi.pry_dia_del_mes }}</span>
            </div>
          </div>
        </div>

        <!-- Grupo vs Año Anterior -->
        <div class="kpi-section">
          <div class="kpi-section-label">vs Año Anterior</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-label">Ventas (año ant.)</span>
              <span class="kpi-value">{{ fmt$(kpi.ant_ventas_netas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Variación</span>
              <span class="kpi-value" :class="kpi.ant_var_ventas_pct >= 0 ? 'kpi-pos' : 'kpi-neg'">
                {{ fmtPct(kpi.ant_var_ventas_pct) }}
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Consig. PP (año ant.)</span>
              <span class="kpi-value">{{ fmt$(kpi.ant_consignacion_pp) }}</span>
            </div>
          </div>
        </div>

        <!-- Grupo Top -->
        <div class="kpi-section">
          <div class="kpi-section-label">Top del mes</div>
          <div class="kpi-grid kpi-grid-wide">
            <div class="kpi-card">
              <span class="kpi-label">Top Canal</span>
              <span class="kpi-value kpi-text">{{ kpi.top_canal }}</span>
              <span class="kpi-sub-value">{{ fmt$(kpi.top_canal_ventas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Top Cliente</span>
              <span class="kpi-value kpi-text">{{ kpi.top_cliente }}</span>
              <span class="kpi-sub-value">{{ fmt$(kpi.top_cliente_ventas) }}</span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">Top Producto</span>
              <span class="kpi-value kpi-text">{{ kpi.top_producto_nombre }}</span>
              <span class="kpi-sub-value">{{ fmt$(kpi.top_producto_ventas) }}</span>
            </div>
          </div>
        </div>

      </template>

      <!-- ── SEPARADOR ── -->
      <div class="section-divider" />

      <!-- ── TABLAS ACORDEÓN ── -->
      <div class="acordeones">

        <!-- Por canal -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('canal')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.canal }" />
              <span class="ac-title">Por canal de ventas</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resCanal.length }} registros</span>
          </button>
          <div v-if="abiertos.canal" class="acordeon-body">
            <OsDataTable title="Por canal" recurso="resumen-canal" :rows="resCanal" :columns="colsCanal" :loading="loadingCanal" :mes="mes"
              @row-click="row => router.push(`/ventas/detalle-canal/${mes}/${encodeURIComponent(row.canal)}`)" />
          </div>
        </div>

        <!-- Por cliente -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('cliente')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.cliente }" />
              <span class="ac-title">Por cliente</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resCliente.length }} registros</span>
          </button>
          <div v-if="abiertos.cliente" class="acordeon-body">
            <OsDataTable title="Por cliente" recurso="resumen-cliente" :rows="resCliente" :columns="colsCliente" :loading="loadingCliente" :mes="mes"
              @row-click="row => router.push(`/ventas/detalle-cliente/${mes}/${encodeURIComponent(row.id_cliente)}`)" />
          </div>
        </div>

        <!-- Por producto -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('producto')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.producto }" />
              <span class="ac-title">Por producto</span>
              <span class="ac-mes-tag">{{ mes }}</span>
            </div>
            <span class="ac-count">{{ resProducto.length }} registros</span>
          </button>
          <div v-if="abiertos.producto" class="acordeon-body">
            <OsDataTable title="Por producto" recurso="resumen-producto" :rows="resProducto" :columns="colsProducto" :loading="loadingProducto" :mes="mes"
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
              @row-click="row => router.push({ path: `/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`, query: { mes, desde: 'mes' } })" />
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
    const { data } = await axios.get(`${API}/ventas/resumen-mes`, {
      params: { filters: JSON.stringify([{ field: 'mes', op: 'eq', value: mes }]) }
    })
    kpi.value = data[0] || null
  } finally { loadingKpi.value = false }
}

// ── Tablas ───────────────────────────────────────────
const resCanal        = ref([]); const loadingCanal        = ref(false)
const resCliente      = ref([]); const loadingCliente      = ref(false)
const resProducto     = ref([]); const loadingProducto     = ref(false)
const resFacturas     = ref([]); const loadingFacturas     = ref(false)
const resCotizaciones = ref([]); const loadingCotizaciones = ref(false)
const resRemisiones   = ref([]); const loadingRemisiones   = ref(false)

const colsCanal        = ref([])
const colsCliente      = ref([])
const colsProducto     = ref([])
const colsFacturas     = ref([])
const colsCotizaciones = ref([])
const colsRemisiones   = ref([])

const DEFAULT_VISIBLE = {
  'resumen_ventas_facturas_canal_mes':   ['mes','canal','fin_ventas_netas_sin_iva','fin_pct_del_mes','vol_num_facturas','cli_clientes_activos','top_cliente','con_consignacion_pp'],
  'resumen_ventas_facturas_cliente_mes': ['mes','cliente','ciudad','canal','fin_ventas_netas_sin_iva','vol_num_facturas','cli_es_nuevo','top_producto_nombre'],
  'resumen_ventas_facturas_producto_mes':['mes','cod_articulo','nombre','categoria','fin_ventas_netas_sin_iva','fin_pct_del_mes','vol_unidades_vendidas','cli_clientes_activos'],
  'zeffi_facturas_venta_encabezados':    ['id_numeracion','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc','dias_mora'],
  'zeffi_cotizaciones_ventas_encabezados': ['fecha_de_creacion','id_cotizacion','cliente','ciudad','vendedor','total_bruto','descuentos','total_neto','estado_cotizacion','estado'],
  'zeffi_remisiones_venta_encabezados':  ['fecha_de_creacion','id_remision','cliente','ciudad','vendedor','total_neto','estado_remision','estado_cxc','dias_mora'],
}

function labelFromKey(key) {
  if (key === 'id_numeracion') return 'No Fac'
  return key
    .replace(/^_pk$/, 'N°')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '').replace(/^Vol /, '').replace(/^Cli /, '')
    .replace(/^Cto /, '').replace(/^Con /, '').replace(/^Top /, 'Top ')
    .replace(/^Pry /, 'Pry ').replace(/^Ant /, 'Ant ')
    .trim()
}

async function loadColumns(tabla, destRef) {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/${tabla}`)
    destRef.value = cols.map(key => ({
      key,
      label: labelFromKey(key),
      visible: (DEFAULT_VISIBLE[tabla] || []).includes(key)
    }))
  } catch(e) { console.error('Error columnas', tabla, e) }
}

// ── Acordeones ───────────────────────────────────────
const abiertos = ref({ canal: false, cliente: false, producto: false, facturas: false, cotizaciones: false, remisiones: false })

async function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
  if (!abiertos.value[key]) return
  const loaders = {
    canal:        () => load('canal',        `${API}/ventas/resumen-canal`,      resCanal,        loadingCanal),
    cliente:      () => load('cliente',      `${API}/ventas/resumen-cliente`,    resCliente,      loadingCliente),
    producto:     () => load('producto',     `${API}/ventas/resumen-producto`,   resProducto,     loadingProducto),
    facturas:     () => load('facturas',     `${API}/ventas/facturas`,           resFacturas,     loadingFacturas),
    cotizaciones: () => load('cotizaciones', `${API}/ventas/cotizaciones`,       resCotizaciones, loadingCotizaciones),
    remisiones:   () => load('remisiones',   `${API}/ventas/remisiones`,         resRemisiones,   loadingRemisiones),
  }
  if (loaders[key]) loaders[key]()
}

async function load(_, url, dataRef, loadingRef) {
  if (loadingRef.value) return
  loadingRef.value = true
  try {
    const { data } = await axios.get(url, { params: { mes } })
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
    loadColumns('resumen_ventas_facturas_canal_mes',      colsCanal),
    loadColumns('resumen_ventas_facturas_cliente_mes',    colsCliente),
    loadColumns('resumen_ventas_facturas_producto_mes',   colsProducto),
    loadColumns('zeffi_facturas_venta_encabezados',       colsFacturas),
    loadColumns('zeffi_cotizaciones_ventas_encabezados',  colsCotizaciones),
    loadColumns('zeffi_remisiones_venta_encabezados',     colsRemisiones),
  ])
})
</script>

<style scoped>
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

/* Header */
.page-header       { border-bottom: 1px solid var(--border-subtle); background: var(--bg-app); padding: 0 24px; flex-shrink: 0; }
.page-header-inner { padding: 16px 0 12px; }
.breadcrumb        { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-tertiary); margin-bottom: 8px; }
.bc-link           { cursor: pointer; transition: color 80ms; }
.bc-link:hover     { color: var(--accent); }
.bc-current        { color: var(--text-secondary); }
.page-title-row    { display: flex; align-items: center; gap: 12px; }
.page-title        { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

/* KPI Sections */
.kpi-section       { display: flex; flex-direction: column; gap: 8px; }
.kpi-section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); }

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 6px;
}
.kpi-grid-wide { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }

/* KPI Card */
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 10px 12px;
  display: flex; flex-direction: column; gap: 3px;
}
.kpi-label     { font-size: 10px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value     { font-size: 14px; font-weight: 600; color: var(--text-primary); line-height: 1.2; }
.kpi-value.kpi-text { font-size: 12px; font-weight: 500; }
.kpi-sub       { font-size: 11px; font-weight: 400; color: var(--text-tertiary); margin-left: 4px; }
.kpi-sub-value { font-size: 11px; color: var(--text-tertiary); }
.kpi-pos       { color: var(--color-success); }
.kpi-neg       { color: var(--color-error); }
.kpi-warn      { color: var(--color-warning); }

/* Skeleton KPI */
.skeleton-kpi {
  height: 60px;
  background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.09) 50%, rgba(0,0,0,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Separador */
.section-divider { height: 1px; background: var(--border-subtle); }

/* Acordeones */
.acordeones       { display: flex; flex-direction: column; gap: 8px; }
.acordeon         { border: 1px solid var(--border-default); border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-card); }
.acordeon-header  {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 0 14px; height: 42px;
  border: none; background: transparent; cursor: pointer;
  transition: background 80ms; font-family: var(--font-sans);
}
.acordeon-header:hover { background: var(--bg-card-hover); }
.ac-left     { display: flex; align-items: center; gap: 8px; }
.ac-chevron  { color: var(--text-tertiary); transition: transform 150ms ease-out; }
.ac-chevron.open { transform: rotate(90deg); }
.ac-title    { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.ac-mes-tag  { font-size: 11px; font-weight: 500; color: var(--accent); background: var(--accent-muted); border: 1px solid var(--accent-border); padding: 1px 7px; border-radius: var(--radius-full); }
.ac-count    { font-size: 12px; color: var(--text-tertiary); }
.acordeon-body { border-top: 1px solid var(--border-subtle); }
</style>
