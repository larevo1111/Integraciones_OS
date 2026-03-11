<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <!-- Breadcrumb sutil -->
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Resumen Facturación</span>
        </div>
        <!-- Título + mes seleccionado -->
        <div class="page-title-row">
          <h1 class="page-title">Resumen Facturación</h1>
          <div v-if="mesSel" class="mes-badge">
            <CalendarIcon :size="12" />
            <span>{{ mesSel }}</span>
            <button class="mes-clear" @click="mesSel = null" title="Limpiar selección">
              <XIcon :size="11" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- Tabla principal: resumen por mes -->
      <OsDataTable
        title="Resumen por mes"
        recurso="resumen-mes"
        :rows="resMes"
        :columns="colsMes"
        :loading="loadingMes"
        :mes="mesSel"
        @row-click="onMesClick"
      />

      <!-- ── ACORDEONES ── -->
      <div class="acordeones">

        <!-- Por canal -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('canal')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.canal }" />
              <span class="ac-title">Por canal de ventas</span>
              <span v-if="mesSel" class="ac-mes-tag">{{ mesSel }}</span>
            </div>
            <span class="ac-count">{{ resCanal.length }} registros</span>
          </button>
          <div v-if="abiertos.canal" class="acordeon-body">
            <OsDataTable
              title="Resumen por canal"
              recurso="resumen-canal"
              :rows="resCanal"
              :columns="colsCanal"
              :loading="loadingCanal"
              :mes="mesSel"
            />
          </div>
        </div>

        <!-- Por cliente -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('cliente')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.cliente }" />
              <span class="ac-title">Por cliente</span>
              <span v-if="mesSel" class="ac-mes-tag">{{ mesSel }}</span>
            </div>
            <span class="ac-count">{{ resCliente.length }} registros</span>
          </button>
          <div v-if="abiertos.cliente" class="acordeon-body">
            <OsDataTable
              title="Resumen por cliente"
              recurso="resumen-cliente"
              :rows="resCliente"
              :columns="colsCliente"
              :loading="loadingCliente"
              :mes="mesSel"
            />
          </div>
        </div>

        <!-- Por producto -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('producto')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.producto }" />
              <span class="ac-title">Por producto</span>
              <span v-if="mesSel" class="ac-mes-tag">{{ mesSel }}</span>
            </div>
            <span class="ac-count">{{ resProducto.length }} registros</span>
          </button>
          <div v-if="abiertos.producto" class="acordeon-body">
            <OsDataTable
              title="Resumen por producto"
              recurso="resumen-producto"
              :rows="resProducto"
              :columns="colsProducto"
              :loading="loadingProducto"
              :mes="mesSel"
            />
          </div>
        </div>

        <!-- Facturas del mes -->
        <div class="acordeon">
          <button class="acordeon-header" @click="toggleAcordeon('facturas')">
            <div class="ac-left">
              <ChevronRightIcon :size="14" class="ac-chevron" :class="{ open: abiertos.facturas }" />
              <span class="ac-title">Facturas del mes</span>
              <span v-if="mesSel" class="ac-mes-tag">{{ mesSel }}</span>
              <span v-else class="ac-hint">Selecciona un mes arriba</span>
            </div>
            <span class="ac-count">{{ resFacturas.length }} facturas</span>
          </button>
          <div v-if="abiertos.facturas" class="acordeon-body">
            <OsDataTable
              title="Facturas"
              recurso="facturas"
              :rows="resFacturas"
              :columns="colsFacturas"
              :loading="loadingFacturas"
              :mes="mesSel"
            />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { ChevronRightIcon, CalendarIcon, XIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const API = '/api'

// ── Estado ────────────────────────────────────────────
const mesSel = ref(null)

const resMes      = ref([]);  const loadingMes      = ref(true)
const resCanal    = ref([]);  const loadingCanal    = ref(false)
const resCliente  = ref([]);  const loadingCliente  = ref(false)
const resProducto = ref([]);  const loadingProducto = ref(false)
const resFacturas = ref([]);  const loadingFacturas = ref(false)

// ── Acordeones ────────────────────────────────────────
const abiertos = ref({ canal: false, cliente: false, producto: false, facturas: false })
function toggleAcordeon(key) {
  abiertos.value[key] = !abiertos.value[key]
}

// ── Columnas ──────────────────────────────────────────
const colsMes      = ref([])
const colsCanal    = ref([])
const colsCliente  = ref([])
const colsProducto = ref([])
const colsFacturas = ref([])

// Columnas visibles por defecto para cada tabla
const DEFAULT_VISIBLE = {
  'resumen_ventas_facturas_mes':         ['mes','fin_ventas_netas_sin_iva','fin_ingresos_netos','fin_devoluciones','vol_num_facturas','vol_ticket_promedio','cli_clientes_activos','cli_clientes_nuevos','top_canal','top_cliente','con_consignacion_pp'],
  'resumen_ventas_facturas_canal_mes':   ['mes','canal','fin_ventas_netas_sin_iva','fin_pct_del_mes','vol_num_facturas','cli_clientes_activos','top_cliente','con_consignacion_pp'],
  'resumen_ventas_facturas_cliente_mes': ['mes','cliente','ciudad','canal','fin_ventas_netas_sin_iva','vol_num_facturas','cli_es_nuevo','top_producto_nombre'],
  'resumen_ventas_facturas_producto_mes':['mes','cod_articulo','nombre','categoria','fin_ventas_netas_sin_iva','fin_pct_del_mes','vol_unidades_vendidas','cli_clientes_activos'],
  'zeffi_facturas_venta_encabezados':    ['_pk','fecha_de_creacion','cliente','ciudad','vendedor','subtotal','total_neto','estado_cxc'],
}

function labelFromKey(key) {
  return key
    .replace(/^_pk$/, 'N°')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/^Fin /, '')
    .replace(/^Vol /, '')
    .replace(/^Cli /, '')
    .replace(/^Cto /, '')
    .replace(/^Con /, '')
    .replace(/^Top /, 'Top ')
    .replace(/^Pry /, 'Pry ')
    .replace(/^Ant /, 'Ant ')
    .trim()
}

async function loadColumns(tabla, destRef, defaultVisible) {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/${tabla}`)
    destRef.value = cols.map(key => ({
      key,
      label: labelFromKey(key),
      visible: (defaultVisible || []).includes(key)
    }))
  } catch(e) { console.error('Error cargando columnas', tabla, e) }
}

// ── Cargar datos ──────────────────────────────────────
async function loadMes() {
  loadingMes.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-mes`)
    resMes.value = data
  } finally { loadingMes.value = false }
}

async function loadCanal() {
  if (!abiertos.value.canal) return
  loadingCanal.value = true
  try {
    const params = mesSel.value ? { mes: mesSel.value } : {}
    const { data } = await axios.get(`${API}/ventas/resumen-canal`, { params })
    resCanal.value = data
  } finally { loadingCanal.value = false }
}

async function loadCliente() {
  if (!abiertos.value.cliente) return
  loadingCliente.value = true
  try {
    const params = mesSel.value ? { mes: mesSel.value } : {}
    const { data } = await axios.get(`${API}/ventas/resumen-cliente`, { params })
    resCliente.value = data
  } finally { loadingCliente.value = false }
}

async function loadProducto() {
  if (!abiertos.value.producto) return
  loadingProducto.value = true
  try {
    const params = mesSel.value ? { mes: mesSel.value } : {}
    const { data } = await axios.get(`${API}/ventas/resumen-producto`, { params })
    resProducto.value = data
  } finally { loadingProducto.value = false }
}

async function loadFacturas() {
  if (!abiertos.value.facturas) return
  loadingFacturas.value = true
  try {
    const params = mesSel.value ? { mes: mesSel.value } : {}
    const { data } = await axios.get(`${API}/ventas/facturas`, { params })
    resFacturas.value = data
  } finally { loadingFacturas.value = false }
}

// ── Click en fila de resumen-mes ─────────────────────
function onMesClick(row) {
  mesSel.value = row.mes === mesSel.value ? null : row.mes
}

// ── Watchers ──────────────────────────────────────────
watch(mesSel, () => {
  loadCanal(); loadCliente(); loadProducto(); loadFacturas()
})

watch(() => abiertos.value.canal,    (v) => { if (v) loadCanal() })
watch(() => abiertos.value.cliente,  (v) => { if (v) loadCliente() })
watch(() => abiertos.value.producto, (v) => { if (v) loadProducto() })
watch(() => abiertos.value.facturas, (v) => { if (v) loadFacturas() })

// ── Mount ─────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    loadColumns('resumen_ventas_facturas_mes',          colsMes,      DEFAULT_VISIBLE['resumen_ventas_facturas_mes']),
    loadColumns('resumen_ventas_facturas_canal_mes',    colsCanal,    DEFAULT_VISIBLE['resumen_ventas_facturas_canal_mes']),
    loadColumns('resumen_ventas_facturas_cliente_mes',  colsCliente,  DEFAULT_VISIBLE['resumen_ventas_facturas_cliente_mes']),
    loadColumns('resumen_ventas_facturas_producto_mes', colsProducto, DEFAULT_VISIBLE['resumen_ventas_facturas_producto_mes']),
    loadColumns('zeffi_facturas_venta_encabezados',     colsFacturas, DEFAULT_VISIBLE['zeffi_facturas_venta_encabezados']),
  ])
  await loadMes()
})
</script>

<style scoped>
.page-wrap { display: flex; flex-direction: column; height: 100%; background: var(--bg-app); }

/* ── PAGE HEADER ── */
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

.mes-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px 3px 7px;
  border-radius: var(--radius-full);
  background: var(--accent-muted);
  border: 1px solid var(--accent-border);
  font-size: 12px; font-weight: 500; color: var(--accent);
}
.mes-clear {
  background: none; border: none; cursor: pointer; padding: 0; margin: 0;
  color: var(--accent); opacity: 0.7; display: flex; align-items: center;
}
.mes-clear:hover { opacity: 1; }

/* ── CONTENT ── */
.page-content { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }

/* ── ACORDEONES ── */
.acordeones { display: flex; flex-direction: column; gap: 8px; }

.acordeon {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-card);
}

.acordeon-header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 0 14px;
  height: 42px;
  border: none; background: transparent; cursor: pointer;
  transition: background 80ms;
  font-family: var(--font-sans);
}
.acordeon-header:hover { background: var(--bg-card-hover); }

.ac-left { display: flex; align-items: center; gap: 8px; }
.ac-chevron { color: var(--text-tertiary); transition: transform 150ms ease-out; flex-shrink: 0; }
.ac-chevron.open { transform: rotate(90deg); }
.ac-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }

.ac-mes-tag {
  font-size: 11px; font-weight: 500; color: var(--accent);
  background: var(--accent-muted); border: 1px solid var(--accent-border);
  padding: 1px 7px; border-radius: var(--radius-full);
}
.ac-hint  { font-size: 12px; color: var(--text-tertiary); }
.ac-count { font-size: 12px; color: var(--text-tertiary); }

.acordeon-body { border-top: 1px solid var(--border-subtle); }
</style>
