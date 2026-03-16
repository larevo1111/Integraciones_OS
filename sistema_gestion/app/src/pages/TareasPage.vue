<template>
  <div style="display:flex;height:100%;overflow:hidden">

    <!-- Lista principal -->
    <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0">

      <!-- Barra de filtros -->
      <div class="filtros-bar">
        <button v-for="f in FILTROS" :key="f.key" class="chip" :class="{ active: filtroActivo === f.key }" @click="filtroActivo = f.key">
          {{ f.label }}
          <span v-if="f.key === 'hoy' && conteoHoy" class="chip-count">{{ conteoHoy }}</span>
        </button>

        <!-- Agrupar por -->
        <div style="position:relative;margin-left:auto">
          <button class="chip chip-agrupar" @click="menuAgrupar = !menuAgrupar">
            <span class="material-icons" style="font-size:13px">sort</span>
            {{ AGRUPACIONES.find(a => a.key === agruparPor)?.label }}
            <span class="material-icons" style="font-size:13px">expand_more</span>
          </button>
          <div v-if="menuAgrupar" class="dropdown-menu" @mouseleave="menuAgrupar=false">
            <div
              v-for="ag in AGRUPACIONES"
              :key="ag.key"
              class="dropdown-item"
              :class="{ active: agruparPor === ag.key }"
              @click="agruparPor = ag.key; menuAgrupar = false"
            >
              <span class="material-icons" style="font-size:14px">{{ agruparPor === ag.key ? 'radio_button_checked' : 'radio_button_unchecked' }}</span>
              {{ ag.label }}
            </div>
          </div>
        </div>

        <!-- Botón nueva tarea -->
        <button class="btn btn-primary btn-sm" @click="mostrarForm = true">
          <span class="material-icons" style="font-size:14px">add</span> Nueva
        </button>
      </div>

      <!-- Lista de tareas agrupadas -->
      <div class="page-body lista-tareas" v-if="!cargando">
        <div v-if="!grupos.length" class="empty-state">
          <span class="material-icons" style="font-size:32px">check_circle_outline</span>
          <p>No hay tareas con estos filtros</p>
          <button class="btn btn-secondary btn-sm" @click="mostrarForm = true">Crear tarea</button>
        </div>

        <template v-for="grupo in grupos" :key="grupo.key">
          <!-- Header del grupo -->
          <div class="grupo-header">
            <div class="grupo-color-bar" :style="{ background: grupo.color }" />
            <span class="grupo-nombre">{{ grupo.nombre }}</span>
            <span class="grupo-count">{{ grupo.tareas.length }}</span>
          </div>

          <!-- Tareas del grupo -->
          <TareaItem
            v-for="t in grupo.tareas"
            :key="t.id"
            :tarea="t"
            :seleccionada="tareaSeleccionada?.id === t.id"
            :usuario-actual="auth.usuario?.email"
            @click="seleccionar"
            @cambiar-estado="cambiarEstado"
          />
        </template>

        <!-- Completadas (colapsables) -->
        <template v-if="completadas.length">
          <div class="completadas-header" @click="mostrarCompletadas = !mostrarCompletadas">
            <span class="material-icons" style="font-size:16px">{{ mostrarCompletadas ? 'expand_more' : 'chevron_right' }}</span>
            Completadas ({{ completadas.length }})
          </div>
          <template v-if="mostrarCompletadas">
            <TareaItem
              v-for="t in completadas"
              :key="t.id"
              :tarea="t"
              :seleccionada="tareaSeleccionada?.id === t.id"
              :usuario-actual="auth.usuario?.email"
              @click="seleccionar"
              @cambiar-estado="cambiarEstado"
            />
          </template>
        </template>
      </div>

      <!-- Loading -->
      <div v-else class="empty-state"><span class="material-icons spin">refresh</span></div>

      <!-- FAB mobile -->
      <button class="fab d-mobile-only" @click="mostrarForm = true">
        <span class="material-icons">add</span>
      </button>
    </div>

    <!-- Panel lateral derecho -->
    <Transition name="panel">
      <TareaPanel
        v-if="tareaSeleccionada"
        :tarea="tareaSeleccionada"
        :usuarios="usuarios"
        @cerrar="tareaSeleccionada = null"
        @actualizada="onTareaActualizada"
        @eliminar="eliminar"
        class="d-desktop-only"
      />
    </Transition>

    <!-- Form nueva/editar tarea -->
    <TareaForm
      v-model="mostrarForm"
      :categorias="categorias"
      :usuarios="usuarios"
      @guardada="onTareaGuardada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import TareaItem  from 'src/components/TareaItem.vue'
import TareaPanel from 'src/components/TareaPanel.vue'
import TareaForm  from 'src/components/TareaForm.vue'

const auth = useAuthStore()

// Estado
const tareas           = ref([])
const completadas      = ref([])
const categorias       = ref([])
const usuarios         = ref([])
const cargando         = ref(true)
const tareaSeleccionada = ref(null)
const mostrarForm      = ref(false)
const mostrarCompletadas = ref(false)
const menuAgrupar      = ref(false)
const filtroActivo     = ref('hoy')
const agruparPor       = ref(localStorage.getItem('gestion_agrupar') || 'categoria')

const FILTROS = [
  { key: 'hoy',    label: 'Hoy' },
  { key: 'manana', label: 'Mañana' },
  { key: 'ayer',   label: 'Ayer' },
  { key: 'semana', label: 'Esta semana' },
  { key: 'mias',   label: 'Mis tareas' },
  { key: 'todas',  label: 'Todas' }
]
const AGRUPACIONES = [
  { key: 'categoria', label: 'Categoría' },
  { key: 'prioridad', label: 'Prioridad' },
  { key: 'fecha',     label: 'Fecha' }
]

const conteoHoy = computed(() => tareas.value.filter(t => t.fecha_limite === hoyISO()).length)

function hoyISO() {
  return new Date().toISOString().slice(0,10)
}

watch(agruparPor, val => localStorage.setItem('gestion_agrupar', val))
watch(filtroActivo, () => cargarTareas())

// Agrupaciones
const ORDEN_PRIORIDAD = ['Urgente','Alta','Media','Baja']
const COLORES_PRIORIDAD = { Urgente: '#ef4444', Alta: '#f59e0b', Media: '#6b7280', Baja: '#374151' }

const grupos = computed(() => {
  if (!tareas.value.length) return []

  if (agruparPor.value === 'categoria') {
    const map = {}
    tareas.value.forEach(t => {
      const k = t.categoria_id
      if (!map[k]) map[k] = { key: k, nombre: t.categoria_nombre, color: t.categoria_color, tareas: [] }
      map[k].tareas.push(t)
    })
    return Object.values(map)
  }

  if (agruparPor.value === 'prioridad') {
    const map = {}
    tareas.value.forEach(t => {
      const p = t.prioridad || 'Media'
      if (!map[p]) map[p] = { key: p, nombre: p, color: COLORES_PRIORIDAD[p], tareas: [] }
      map[p].tareas.push(t)
    })
    return ORDEN_PRIORIDAD.filter(p => map[p]).map(p => map[p])
  }

  if (agruparPor.value === 'fecha') {
    const map = {}
    tareas.value.forEach(t => {
      const f = t.fecha_limite || 'Sin fecha'
      if (!map[f]) map[f] = { key: f, nombre: formatGrupoFecha(f), color: '#6b7280', tareas: [] }
      map[f].tareas.push(t)
    })
    return Object.values(map).sort((a, b) => {
      if (a.key === 'Sin fecha') return 1
      if (b.key === 'Sin fecha') return -1
      return a.key.localeCompare(b.key)
    })
  }

  return []
})

function formatGrupoFecha(iso) {
  if (iso === 'Sin fecha') return 'Sin fecha'
  const d = new Date(iso + 'T00:00:00')
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  if (d.getTime() === hoy.getTime()) return 'Hoy'
  if (d.getTime() === hoy.getTime() + 86400000) return 'Mañana'
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })
}

async function cargarTareas() {
  cargando.value = true
  try {
    const params = new URLSearchParams()
    if (filtroActivo.value === 'mias') { params.set('solo_mias', '1') }
    else if (filtroActivo.value !== 'todas') { params.set('filtro', filtroActivo.value) }

    const [dataTareas, dataCompletadas] = await Promise.all([
      api(`/api/gestion/tareas?${params}`),
      api('/api/gestion/tareas/completadas')
    ])
    tareas.value     = dataTareas.tareas || []
    completadas.value = dataCompletadas.tareas || []
  } catch (e) {
    console.error(e)
  } finally {
    cargando.value = false
  }
}

async function cargarCatalogos() {
  const [dataCat, dataUsr] = await Promise.all([
    api('/api/gestion/categorias'),
    api('/api/gestion/usuarios')
  ])
  categorias.value = dataCat.categorias || []
  usuarios.value   = dataUsr.usuarios   || []
}

function seleccionar(tarea) {
  tareaSeleccionada.value = tareaSeleccionada.value?.id === tarea.id ? null : tarea
}

async function cambiarEstado(tarea) {
  const CICLO = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  const nuevoEstado = CICLO[tarea.estado] || 'Pendiente'
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}`, { method: 'PUT', body: JSON.stringify({ estado: nuevoEstado }) })
    onTareaActualizada(data.tarea)
  } catch (e) { console.error(e) }
}

function onTareaActualizada(tareaActualizada) {
  const esCompletada = ['Completada','Cancelada'].includes(tareaActualizada.estado)
  tareas.value = tareas.value.filter(t => t.id !== tareaActualizada.id)
  completadas.value = completadas.value.filter(t => t.id !== tareaActualizada.id)
  if (esCompletada) completadas.value.unshift(tareaActualizada)
  else              tareas.value.push(tareaActualizada)
  if (tareaSeleccionada.value?.id === tareaActualizada.id) tareaSeleccionada.value = tareaActualizada
}

function onTareaGuardada(tarea) {
  tareas.value.push(tarea)
  tareaSeleccionada.value = tarea
}

async function eliminar(tarea) {
  if (!confirm(`¿Eliminar "${tarea.titulo}"?`)) return
  try {
    await api(`/api/gestion/tareas/${tarea.id}`, { method: 'DELETE' })
    tareas.value = tareas.value.filter(t => t.id !== tarea.id)
    if (tareaSeleccionada.value?.id === tarea.id) tareaSeleccionada.value = null
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  await Promise.all([cargarTareas(), cargarCatalogos()])
})
</script>

<style scoped>
.d-desktop-only { }
.d-mobile-only  { display: none; }
@media (max-width: 768px) {
  .d-desktop-only { display: none; }
  .d-mobile-only  { display: flex; }
}

/* Dropdown agrupar */
.dropdown-menu {
  position: absolute; right: 0; top: calc(100% + 4px);
  background: var(--bg-modal);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 160px;
  z-index: 50;
  overflow: hidden;
}
.dropdown-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 60ms;
}
.dropdown-item:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.dropdown-item.active { color: var(--accent); }

/* Panel */
.panel-enter-active, .panel-leave-active { transition: transform 200ms ease-out, opacity 200ms; }
.panel-enter-from, .panel-leave-to { transform: translateX(20px); opacity: 0; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
