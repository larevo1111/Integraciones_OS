<template>
  <div class="items-page">
    <!-- Tabla -->
    <OsDataTable
      :title="CONFIG[tipo].title"
      :columns="columnas"
      :rows="filasFiltradas"
      :loading="cargando"
      :selected-ids="ms.selectedIds.value"
      @row-click="abrirDetalle"
      @select-toggle="ms.toggle"
    >
      <template #toolbar>
        <button class="btn-crear" @click="abrirCrear">
          <span class="material-icons" style="font-size:14px">add</span>
          <span class="btn-crear-label">Nuevo</span>
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

    <!-- Barra de acciones múltiples -->
    <MultiActionBar
      :count="ms.selectedIds.value.length"
      :acciones="['estado','prioridad','categoria','etiquetas','responsable','eliminar']"
      :estados="CONFIG[tipo].estados"
      :categorias="categorias"
      :etiquetas="etiquetas"
      :usuarios="usuarios"
      @cerrar="ms.clear"
      @aplicar="onAplicarMulti"
      @crear-etiqueta="onCrearEtiquetaMulti"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { api } from 'src/services/api'
import OsDataTable from 'src/components/OsDataTable.vue'
import ProyectoPanel from 'src/components/ProyectoPanel.vue'
import MultiActionBar from 'src/components/MultiActionBar.vue'
import { useMultiSelect } from 'src/composables/useMultiSelect'

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

const items      = ref([])
const cargando   = ref(false)
const categorias = ref([])
const usuarios   = ref([])
const etiquetas  = ref([])

// Columnas con options multi-select en el header de cada columna
const columnas = computed(() => [
  { key: 'nombre',           label: 'Nombre',       sortable: true, visible: true, width: '280px' },
  { key: 'estado',           label: 'Estado',       sortable: true, visible: true,
    options: (CONFIG[props.tipo]?.estados || []).map(e => ({ value: e, label: e, color: ESTADO_COLORS[e] })) },
  { key: 'prioridad',        label: 'Prioridad',    sortable: true, visible: true,
    options: ['Baja','Media','Alta','Urgente'].map(p => ({ value: p, label: p, color: PRIORIDAD_COLORS[p] })) },
  { key: 'categoria_nombre', label: 'Categoría',    sortable: true, visible: true,
    options: categorias.value.map(c => ({ value: c.nombre, label: c.nombre, color: c.color })) },
  { key: 'responsables_str', label: 'Responsable',  sortable: true, visible: true },
  { key: 'fecha_estimada_fin', label: 'Fecha est.', sortable: true, visible: true },
  { key: 'tareas_pendientes', label: 'Tareas',      sortable: true, visible: true, numeric: true },
])

const filasFiltradas = computed(() => {
  const result = items.value
  return result
})

const panelVisible = ref(false)
const panelItem    = ref(null)
const recargarSidebar = inject('recargarSidebar', () => {})

// ── Multi-select ──
const ms = useMultiSelect({
  endpointBase: '/api/gestion/proyectos',
  onAfter: async () => { await cargar(); recargarSidebar() }
})

async function onAplicarMulti({ tipo, valor }) {
  switch (tipo) {
    case 'estado':      return ms.bulkPut({ estado: valor })
    case 'prioridad':   return ms.bulkPut({ prioridad: valor })
    case 'categoria':   return ms.bulkPut({ categoria_id: valor })
    case 'fecha':       return ms.bulkPut({ fecha_estimada_fin: valor || null })
    case 'responsable': return ms.bulkPutWith(async id => {
      const it = items.value.find(x => x.id === id)
      const actuales = it?.responsables || []
      if (actuales.includes(valor)) return null
      return { responsables: [...actuales, valor] }
    })
    case 'etiqueta':    return ms.bulkPutWith(async id => {
      const it = items.value.find(x => x.id === id)
      const actuales = (it?.etiquetas || []).map(e => e.id || e)
      if (actuales.includes(valor)) return null
      return { etiquetas: [...actuales, valor] }
    })
    case 'quitar-etiquetas': return ms.bulkPut({ etiquetas: [] })
    case 'eliminar':
      if (!confirm(`¿Eliminar ${ms.selectedIds.value.length} elemento(s)?`)) return
      return ms.bulkDelete()
  }
}

async function onCrearEtiquetaMulti(nombre) {
  try {
    const data = await api('/api/gestion/etiquetas', { method: 'POST', body: JSON.stringify({ nombre }) })
    etiquetas.value.push(data.etiqueta)
    await onAplicarMulti({ tipo: 'etiqueta', valor: data.etiqueta.id })
  } catch (e) { console.error(e) }
}

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
  panelVisible.value = false
  cargar()
})

onMounted(() => { cargar(); cargarDatos() })
</script>

<style scoped>
.items-page { padding: 0; }
.items-page :deep(.os-table th:first-child),
.items-page :deep(.os-table td:first-child) { min-width: 240px; }
.btn-crear {
  display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 12px; border-radius: var(--radius-md);
  border: none; background: #fff; color: #111;
  font-size: 12px; font-weight: 600; cursor: pointer;
  font-family: var(--font-sans);
}
.btn-crear:hover { background: var(--bg-card-hover); }
@media (max-width: 768px) {
  .btn-crear { padding: 0 10px; min-width: 32px; }
  .btn-crear .btn-crear-label { display: none; }
}
</style>
