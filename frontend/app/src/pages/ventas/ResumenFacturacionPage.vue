<template>
  <div class="page-wrap">

    <!-- ── PAGE HEADER ── -->
    <div class="page-header">
      <div class="page-header-inner">
        <div class="breadcrumb">
          <span>Ventas</span>
          <ChevronRightIcon :size="13" />
          <span class="bc-current">Resumen Facturación</span>
        </div>
        <div class="page-title-row">
          <h1 class="page-title">Resumen Facturación</h1>
        </div>
      </div>
    </div>

    <!-- ── CONTENT ── -->
    <div class="page-content">
      <OsDataTable
        title="Resumen por mes"
        recurso="resumen-mes"
        :rows="resMes"
        :columns="colsMes"
        :loading="loadingMes"
        @row-click="onMesClick"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ChevronRightIcon } from 'lucide-vue-next'
import OsDataTable from 'src/components/OsDataTable.vue'

const router = useRouter()
const API = '/api'

const resMes     = ref([])
const loadingMes = ref(true)
const colsMes    = ref([])

const DEFAULT_VISIBLE = ['mes','fin_ventas_netas_sin_iva','fin_ingresos_netos','fin_devoluciones','vol_num_facturas','vol_ticket_promedio','cli_clientes_activos','cli_clientes_nuevos','top_canal','top_cliente','con_consignacion_pp']

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

async function loadColumns() {
  try {
    const { data: cols } = await axios.get(`${API}/columnas/resumen_ventas_facturas_mes`)
    colsMes.value = cols.map(key => ({
      key,
      label: labelFromKey(key),
      visible: DEFAULT_VISIBLE.includes(key)
    }))
  } catch(e) { console.error('Error cargando columnas', e) }
}

async function loadMes() {
  loadingMes.value = true
  try {
    const { data } = await axios.get(`${API}/ventas/resumen-mes`)
    resMes.value = data
  } finally { loadingMes.value = false }
}

function onMesClick(row) {
  router.push(`/ventas/detalle-mes/${row.mes}`)
}

onMounted(async () => {
  await loadColumns()
  await loadMes()
})
</script>

<style scoped>
.page-wrap { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }

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

.page-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 12px; }
</style>
