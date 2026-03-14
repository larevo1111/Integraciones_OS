<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-link" @click="router.push('/ventas/resumen-facturacion')">Resumen Facturación</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">{{ titulo }}</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">{{ titulo }}</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">

      <!-- KPIs -->
      <div v-if="!loading && rows.length > 0" class="kpi-section">
        <div class="kpi-card">
          <span class="kpi-label">Facturas</span>
          <span class="kpi-value">{{ rows.length }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">{{ modoGrupo ? 'Total grupo' : 'Total producto' }}</span>
          <span class="kpi-value">{{ fmtMoney(kpiVenta) }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Clientes distintos</span>
          <span class="kpi-value">{{ kpiClientes }}</span>
        </div>
      </div>

      <OsDataTable
        :title="modoGrupo ? 'Facturas del grupo' : 'Facturas del producto'"
        :rows="rows"
        :columns="cols"
        :loading="loading"
        @row-click="onFacturaClick"
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

const route  = useRoute()
const router = useRouter()
const API    = '/api'

// modo = 'producto' | 'grupo'
const modoGrupo = route.path.includes('/facturas-grupo/')
const clave     = decodeURIComponent(modoGrupo ? route.params.grupo : route.params.cod_articulo)

const rows   = ref([])
const cols   = ref([])
const loading = ref(true)

const titulo = ref(clave)

const VISIBLE = [
  'id_numeracion', 'fecha_de_creacion', 'cliente', 'ciudad', 'vendedor',
  modoGrupo ? 'cantidad_grupo' : 'cantidad_producto',
  modoGrupo ? 'fin_venta_grupo' : 'fin_venta_producto',
  'fin_total_neto', 'estado_cxc'
]

const LABELS = {
  id_numeracion:     'No Fac',
  fecha_de_creacion: 'Fecha',
  cliente:           'Cliente',
  ciudad:            'Ciudad',
  vendedor:          'Vendedor',
  fin_subtotal:      'Subtotal',
  fin_total_neto:    'Total neto',
  estado_cxc:        'Estado CxC',
  cantidad_producto: 'Cantidad',
  fin_venta_producto:'Venta producto',
  cantidad_grupo:    'Cantidad',
  fin_venta_grupo:   'Venta grupo',
}

function labelFromKey(key) {
  return LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const kpiVenta = computed(() => {
  const campo = modoGrupo ? 'fin_venta_grupo' : 'fin_venta_producto'
  return rows.value.reduce((s, r) => s + (parseFloat(r[campo]) || 0), 0)
})

const kpiClientes = computed(() => new Set(rows.value.map(r => r.id_cliente)).size)

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  return '$' + Math.round(n).toLocaleString('de-DE')
}

function onFacturaClick(row) {
  router.push(`/ventas/detalle-factura/${row.id_interno}/${row.id_numeracion}`)
}

onMounted(async () => {
  try {
    const url = modoGrupo
      ? `${API}/ventas/facturas-grupo/${encodeURIComponent(clave)}`
      : `${API}/ventas/facturas-producto/${encodeURIComponent(clave)}`
    const { data } = await axios.get(url)
    rows.value = data
    if (data.length > 0) {
      cols.value = Object.keys(data[0]).map(key => ({
        key,
        label: labelFromKey(key),
        visible: VISIBLE.includes(key)
      }))
      // Título: usar la descripción del primer registro si existe
      titulo.value = clave
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
.bc-current        { color: var(--text-secondary); }
.bc-link           { color: var(--text-secondary); cursor: pointer; }
.bc-link:hover     { color: var(--text-primary); }
.page-title-row    { display: flex; align-items: center; gap: 12px; }
.page-title        { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.kpi-section { display: flex; gap: 12px; flex-wrap: wrap; }
.kpi-card    {
  flex: 1; min-width: 140px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 4px;
}
.kpi-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
</style>
