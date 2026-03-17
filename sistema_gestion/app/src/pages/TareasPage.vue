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
      </div>

      <!-- QuickAdd (solo desktop) -->
      <div class="quickadd-wrap d-desktop-only">
        <div class="quickadd-row" :class="{ activo: qaActivo }">
          <span class="material-icons quickadd-plus">add</span>
          <input
            ref="qaInputRef"
            class="quickadd-input"
            v-model="qaTitulo"
            placeholder="Agregar una tarea..."
            @focus="qaActivo = true"
            @keydown.enter.prevent="qaAgregar"
            @keydown.escape="qaCancelar"
          />
          <template v-if="qaActivo">
            <button class="btn btn-ghost btn-sm" @click="qaCancelar">Cancelar</button>
            <button class="btn btn-primary btn-sm" :disabled="!qaTitulo || qaGuardando" @click="qaAgregar">
              {{ qaGuardando ? '...' : 'Agregar' }}
            </button>
          </template>
        </div>

        <!-- Categorías chips + OP -->
        <div v-if="qaActivo" class="quickadd-cats">
          <button
            v-for="c in categorias"
            :key="c.id"
            class="cat-chip"
            :class="{ selected: qaCatId === c.id }"
            @click="qaCatId = c.id"
          >
            <span class="cat-dot" :style="{ background: c.color }"></span>
            {{ c.nombre.replace(/_/g, ' ') }}
          </button>
        </div>
        <!-- Proyecto + etiquetas + OP -->
        <div v-if="qaActivo" class="quickadd-extra">
          <ProyectoSelector
            v-model="qaProyectoId"
            :proyectos="proyectos"
            @proyecto-creado="p => proyectos.push(p)"
          />
          <EtiquetasSelector
            v-model="qaEtiquetas"
            :etiquetas="etiquetas"
            @etiqueta-creada="e => etiquetas.push(e)"
          />
        </div>
        <div v-if="qaActivo && qaCatEsProduccion" class="quickadd-op">
          <OpSelector v-model="qaOp" style="max-width:360px" />
        </div>
      </div>

      <!-- Chip de proyecto activo -->
      <div v-if="proyectoFiltro" class="proyecto-filtro-bar">
        <span class="proyecto-dot-bar" :style="{ background: proyectoFiltro.color || '#607D8B' }"></span>
        <span>{{ proyectoFiltro.nombre }}</span>
        <RouterLink to="/tareas" class="proyecto-filtro-clear" title="Ver todas">
          <span class="material-icons" style="font-size:14px">close</span>
        </RouterLink>
      </div>

      <!-- Lista de tareas -->
      <div class="page-body lista-tareas" v-if="!cargando">
        <div v-if="!grupos.length && !completadas.length" class="empty-state">
          <span class="material-icons" style="font-size:32px">check_circle_outline</span>
          <p>No hay tareas con estos filtros</p>
        </div>

        <template v-for="grupo in grupos" :key="grupo.key">
          <div class="grupo-header">
            <div class="grupo-color-bar" :style="{ background: grupo.color }" />
            <span class="grupo-nombre">{{ grupo.nombre }}</span>
            <span class="grupo-count">{{ grupo.tareas.length }}</span>
          </div>
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

        <!-- Completadas al fondo (colapsables) -->
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

      <div v-else class="empty-state"><span class="material-icons spin">refresh</span></div>

      <!-- FAB mobile -->
      <button class="fab d-mobile-only" @click="mostrarForm = true">
        <span class="material-icons">add</span>
      </button>
    </div>

    <!-- Panel lateral derecho (desktop) -->
    <Transition name="panel">
      <TareaPanel
        v-if="tareaSeleccionada"
        :tarea="tareaSeleccionada"
        :usuarios="usuarios"
        :categorias="categorias"
        :proyectos="proyectos"
        :etiquetas="etiquetas"
        @cerrar="tareaSeleccionada = null"
        @actualizada="onTareaActualizada"
        @eliminar="eliminar"
        @proyecto-creado="p => proyectos.push(p)"
        class="d-desktop-only"
      />
    </Transition>

    <!-- Bottom sheet / modal nueva tarea (mobile) -->
    <TareaForm
      v-model="mostrarForm"
      :categorias="categorias"
      :proyectos="proyectos"
      :etiquetas="etiquetas"
      :usuarios="usuarios"
      @guardada="onTareaGuardada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import TareaItem          from 'src/components/TareaItem.vue'
import TareaPanel         from 'src/components/TareaPanel.vue'
import TareaForm          from 'src/components/TareaForm.vue'
import OpSelector         from 'src/components/OpSelector.vue'
import ProyectoSelector   from 'src/components/ProyectoSelector.vue'
import EtiquetasSelector  from 'src/components/EtiquetasSelector.vue'

const auth  = useAuthStore()
const route = useRoute()

// Estado principal
const tareas            = ref([])
const completadas       = ref([])
const categorias        = ref([])
const proyectos         = ref([])
const etiquetas         = ref([])
const usuarios          = ref([])
const cargando          = ref(true)
const tareaSeleccionada = ref(null)
const mostrarForm       = ref(false)
const mostrarCompletadas = ref(false)
const menuAgrupar       = ref(false)
const filtroActivo      = ref('hoy')
const agruparPor        = ref(localStorage.getItem('gestion_agrupar') || 'categoria')

// Filtro por proyecto (desde query param)
const proyectoFiltroId = computed(() => route.query.proyecto_id ? Number(route.query.proyecto_id) : null)
const proyectoFiltro   = computed(() => proyectos.value.find(p => p.id === proyectoFiltroId.value) || null)

// QuickAdd desktop
const qaActivo      = ref(false)
const qaTitulo      = ref('')
const qaCatId       = ref(null)
const qaOp          = ref('')
const qaProyectoId  = ref(null)
const qaGuardando   = ref(false)
const qaInputRef    = ref(null)
const qaEtiquetas   = ref([])

const qaCatEsProduccion = computed(() =>
  categorias.value.find(c => c.id === qaCatId.value)?.es_produccion
)

watch(categorias, (cats) => {
  if (cats.length && !qaCatId.value) qaCatId.value = cats[0].id
}, { immediate: true })

function qaCancelar() {
  qaActivo.value    = false
  qaTitulo.value    = ''
  qaOp.value        = ''
  qaProyectoId.value = null
  qaEtiquetas.value  = []
}

async function qaAgregar() {
  if (!qaTitulo.value || qaGuardando.value) return
  qaGuardando.value = true
  try {
    const body = {
      titulo:       qaTitulo.value,
      categoria_id: qaCatId.value || categorias.value[0]?.id,
      proyecto_id:  qaProyectoId.value ?? proyectoFiltroId.value ?? null,
      id_op:        qaOp.value || null,
      etiquetas:    qaEtiquetas.value,
      fecha_limite: filtroActivo.value === 'hoy'    ? hoyISO() :
                    filtroActivo.value === 'manana'  ? mananaISO() : null
    }
    const data = await api('/api/gestion/tareas', { method: 'POST', body: JSON.stringify(body) })
    onTareaGuardada(data.tarea)
    qaTitulo.value     = ''
    qaOp.value         = ''
    qaProyectoId.value = null
    qaEtiquetas.value  = []
    qaActivo.value     = false
  } catch (e) { console.error(e) } finally { qaGuardando.value = false }
}

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

function hoyISO()    { return new Date().toISOString().slice(0,10) }
function mananaISO() { const d = new Date(); d.setDate(d.getDate()+1); return d.toISOString().slice(0,10) }

watch(agruparPor, val => localStorage.setItem('gestion_agrupar', val))
watch(filtroActivo, () => cargarTareas())
watch(() => route.query.proyecto_id, () => cargarTareas())

const ORDEN_PRIORIDAD    = ['Urgente','Alta','Media','Baja']
const COLORES_PRIORIDAD  = { Urgente: '#ef4444', Alta: '#f59e0b', Media: '#6b7280', Baja: '#374151' }

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
    if (proyectoFiltroId.value) params.set('proyecto_id', proyectoFiltroId.value)
    const [dataTareas, dataCompletadas] = await Promise.all([
      api(`/api/gestion/tareas?${params}`),
      api('/api/gestion/tareas/completadas')
    ])
    tareas.value      = dataTareas.tareas || []
    completadas.value = dataCompletadas.tareas || []
  } catch (e) { console.error(e) } finally { cargando.value = false }
}

async function cargarCatalogos() {
  const [resCat, resUsr, resProy, resEtq] = await Promise.allSettled([
    api('/api/gestion/categorias'),
    api('/api/gestion/usuarios'),
    api('/api/gestion/proyectos?estado=Activo'),
    api('/api/gestion/etiquetas')
  ])
  if (resCat.status  === 'fulfilled') categorias.value = resCat.value.categorias   || []
  if (resUsr.status  === 'fulfilled') usuarios.value   = resUsr.value.usuarios     || []
  if (resProy.status === 'fulfilled') proyectos.value  = resProy.value.proyectos   || []
  if (resEtq.status  === 'fulfilled') etiquetas.value  = resEtq.value.etiquetas    || []
}

function seleccionar(tarea) {
  tareaSeleccionada.value = tareaSeleccionada.value?.id === tarea.id ? null : tarea
}

async function cambiarEstado(tarea) {
  const CICLO = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}`, { method: 'PUT', body: JSON.stringify({ estado: CICLO[tarea.estado] || 'Pendiente' }) })
    onTareaActualizada(data.tarea)
  } catch (e) { console.error(e) }
}

function onTareaActualizada(t) {
  const esCompletada = ['Completada','Cancelada'].includes(t.estado)
  tareas.value      = tareas.value.filter(x => x.id !== t.id)
  completadas.value = completadas.value.filter(x => x.id !== t.id)
  if (esCompletada) completadas.value.unshift(t)
  else              tareas.value.push(t)
  if (tareaSeleccionada.value?.id === t.id) tareaSeleccionada.value = t
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
  .d-desktop-only { display: none !important; }
  .d-mobile-only  { display: flex; }
}

/* QuickAdd */
.quickadd-wrap {
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 16px 10px;
}
.quickadd-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0 6px;
}
.quickadd-plus {
  font-size: 18px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.quickadd-row.activo .quickadd-plus { color: var(--accent); }
.quickadd-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--text-primary);
  font-family: var(--font-sans);
}
.quickadd-input::placeholder { color: var(--text-tertiary); }

/* Category chips */
.quickadd-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-bottom: 4px;
  padding-left: 26px;
}
.cat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 80ms;
  font-family: var(--font-sans);
  white-space: nowrap;
}
.cat-chip:hover { border-color: var(--border-default); color: var(--text-primary); }
.cat-chip.selected {
  background: var(--bg-row-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
}
.cat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* OP row */
.quickadd-op {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 0 26px;
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

/* QuickAdd extra (proyecto + etiquetas) */
.quickadd-extra {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0 6px 26px;
  flex-wrap: wrap;
}

/* Chip filtro proyecto activo */
.proyecto-filtro-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 16px;
  background: var(--bg-row-hover);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px; color: var(--text-secondary);
}
.proyecto-dot-bar {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.proyecto-filtro-clear {
  display: inline-flex; align-items: center;
  margin-left: auto; color: var(--text-tertiary);
  text-decoration: none; transition: color 80ms;
}
.proyecto-filtro-clear:hover { color: var(--text-primary); }
</style>
