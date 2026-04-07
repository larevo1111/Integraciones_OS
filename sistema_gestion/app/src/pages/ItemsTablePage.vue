<template>
  <div class="items-page">
    <!-- Tabla -->
    <OsDataTable
      :title="CONFIG[tipo].title"
      :columns="columnas"
      :rows="filasFiltradas"
      :loading="cargando"
      @row-click="abrirDetalle"
    >
      <template #toolbar>
        <select v-model="filtroEstado" class="filtro-select">
          <option value="">Estado</option>
          <option v-for="e in CONFIG[tipo].estados" :key="e" :value="e">{{ e }}</option>
        </select>
        <select v-model="filtroPrioridad" class="filtro-select">
          <option value="">Prioridad</option>
          <option v-for="p in ['Baja','Media','Alta','Urgente']" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-model="filtroCategoria" class="filtro-select">
          <option value="">Categoría</option>
          <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
        <button class="btn-crear" @click="abrirCrear">
          <span class="material-icons" style="font-size:14px">add</span>
          Nuevo
        </button>
      </template>
      <template #cell-nombre="{ row, value }">
        <div style="display:flex;align-items:flex-start;gap:6px">
          <span :style="`width:8px;height:8px;border-radius:50%;background:${row.color||'#607D8B'};flex-shrink:0;margin-top:4px`" />
          <span style="font-weight:500">{{ value }}</span>
        </div>
      </template>
      <template #cell-estado="{ value }">
        <span :style="`display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:500;background:${(ESTADO_COLORS[value]||'#78909C')}20;color:${ESTADO_COLORS[value]||'#78909C'}`">{{ value }}</span>
      </template>
      <template #cell-prioridad="{ value }">
        <span :style="`color:${PRIORIDAD_COLORS[value]||'#78909C'};font-weight:500`">{{ value }}</span>
      </template>
      <template #cell-fecha_estimada_fin="{ value }">
        {{ value ? new Date(value).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }) : '—' }}
      </template>
      <template #cell-responsables_str="{ value }">
        {{ value ? value.split(',').map(e => e.split('@')[0]).join(', ') : '—' }}
      </template>
    </OsDataTable>

    <!-- Panel lateral -->
    <ProyectoPanel
      v-if="panelVisible"
      :item="panelItem"
      :tipo="tipo"
      :categorias="categorias"
      :usuarios="usuarios"
      :etiquetas="etiquetas"
      @cerrar="panelVisible = false"
      @guardado="onGuardado"
      @eliminado="onEliminado"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { api } from 'src/services/api'
import OsDataTable from 'src/components/OsDataTable.vue'
import ProyectoPanel from 'src/components/ProyectoPanel.vue'

const props = defineProps({
  tipo: { type: String, required: true },
})

const CONFIG = {
  proyecto:   { title: 'Proyectos',    btnCrear: 'Nuevo proyecto',    estados: ['Activo','Completado','Archivado'] },
  dificultad: { title: 'Dificultades', btnCrear: 'Nueva dificultad',  estados: ['Abierta','En progreso','Resuelta','Cerrada'] },
  compromiso: { title: 'Compromisos',  btnCrear: 'Nuevo compromiso',  estados: ['Pendiente','En progreso','Cumplido','Cancelado'] },
  idea:       { title: 'Ideas',        btnCrear: 'Nueva idea',        estados: ['Nueva','En evaluación','Aprobada','Descartada'] },
}

const ESTADO_COLORS = {
  Activo: '#00C853', Completado: '#63B3ED', Archivado: '#78909C',
  Abierta: '#FFA726', 'En progreso': '#42A5F5', Resuelta: '#00C853', Cerrada: '#78909C',
  Pendiente: '#FFA726', Cumplido: '#00C853', Cancelado: '#78909C',
  Nueva: '#42A5F5', 'En evaluación': '#FFA726', Aprobada: '#00C853', Descartada: '#78909C',
}

const PRIORIDAD_COLORS = {
  Baja: '#78909C', Media: '#42A5F5', Alta: '#FFA726', Urgente: '#EF5350',
}

const columnas = [
  { key: 'nombre',           label: 'Nombre',      sortable: true, visible: true, width: '280px' },
  { key: 'estado',           label: 'Estado',       sortable: true, visible: true },
  { key: 'prioridad',        label: 'Prioridad',    sortable: true, visible: true },
  { key: 'categoria_nombre', label: 'Categoría',    sortable: true, visible: true },
  { key: 'responsables_str', label: 'Responsable',  sortable: true, visible: true },
  { key: 'fecha_estimada_fin', label: 'Fecha est.', sortable: true, visible: true },
  { key: 'tareas_pendientes', label: 'Tareas',      sortable: true, visible: true, numeric: true },
]

const items      = ref([])
const cargando   = ref(false)
const categorias = ref([])
const usuarios   = ref([])
const etiquetas  = ref([])

const filtroEstado    = ref('')
const filtroPrioridad = ref('')
const filtroCategoria = ref('')

const filasFiltradas = computed(() => {
  let result = items.value
  if (filtroEstado.value)    result = result.filter(i => i.estado === filtroEstado.value)
  if (filtroPrioridad.value) result = result.filter(i => i.prioridad === filtroPrioridad.value)
  if (filtroCategoria.value) result = result.filter(i => i.categoria_id === filtroCategoria.value)
  return result
})

const panelVisible = ref(false)
const panelItem    = ref(null)
const recargarSidebar = inject('recargarSidebar', () => {})

async function cargar() {
  cargando.value = true
  try {
    const data = await api(`/api/gestion/proyectos?tipo=${props.tipo}`)
    items.value = (data.proyectos || []).map(p => ({
      ...p,
      responsables_str: (p.responsables || []).join(','),
    }))
  } catch {} finally { cargando.value = false }
}

async function cargarDatos() {
  try {
    const [cats, usrs, etqs] = await Promise.all([
      api('/api/gestion/categorias'),
      api('/api/gestion/usuarios'),
      api('/api/gestion/etiquetas'),
    ])
    categorias.value = cats.categorias || cats || []
    usuarios.value   = usrs.usuarios   || usrs || []
    etiquetas.value  = etqs.etiquetas  || etqs || []
  } catch {}
}

function abrirCrear() {
  panelItem.value = null
  panelVisible.value = true
  if (!categorias.value.length) cargarDatos()
}

function abrirDetalle(row) {
  panelItem.value = row
  panelVisible.value = true
  if (!categorias.value.length) cargarDatos()
}

function onGuardado(p) {
  if (p._accion === 'creado') {
    items.value.unshift({ ...p, responsables_str: (p.responsables || []).join(',') })
    panelVisible.value = false
  } else {
    const idx = items.value.findIndex(x => x.id === p.id)
    if (idx !== -1) items.value[idx] = { ...items.value[idx], ...p, responsables_str: (p.responsables || []).join(',') }
  }
  recargarSidebar()
}

function onEliminado(p) {
  items.value = items.value.filter(x => x.id !== p.id)
  recargarSidebar()
}

// Recargar cuando cambia el tipo (Vue Router reutiliza el componente)
watch(() => props.tipo, () => {
  filtroEstado.value = ''
  filtroPrioridad.value = ''
  filtroCategoria.value = ''
  panelVisible.value = false
  cargar()
})

onMounted(() => { cargar(); cargarDatos() })
</script>

<style scoped>
.items-page { padding: 0; }
.btn-crear {
  display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 12px; border-radius: var(--radius-md);
  border: none; background: #fff; color: #111;
  font-size: 12px; font-weight: 600; cursor: pointer;
  font-family: var(--font-sans);
}
.btn-crear:hover { background: #e8e8e8; }
.filtro-select {
  height: 28px; padding: 0 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: var(--bg-card);
  color: var(--text-primary); font-size: 12px; font-family: var(--font-sans);
}
.filtro-select:focus { outline: none; border-color: var(--accent); }
@media (max-width: 600px) {
  .filtro-select { font-size: 11px; padding: 0 4px; }
  .btn-crear { padding: 0 8px; font-size: 11px; }
}
</style>
