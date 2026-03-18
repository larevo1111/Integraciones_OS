<template>
  <div style="display:flex;height:100%;overflow:hidden">

    <!-- Lista principal -->
    <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0">

      <!-- Header de proyecto activo (breadcrumb) -->
      <div v-if="proyectoFiltro" class="proyecto-header-bar">
        <RouterLink :to="props.soloMias ? '/tareas' : '/equipo'" class="proyecto-back-link">
          <span class="material-icons" style="font-size:15px">arrow_back</span>
          {{ props.soloMias ? 'Mis Tareas' : 'Equipo' }}
        </RouterLink>
        <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">chevron_right</span>
        <span class="proyecto-dot-hdr" :style="{ background: proyectoFiltro.color || '#607D8B' }"></span>
        <span class="proyecto-header-nombre">{{ proyectoFiltro.nombre }}</span>
      </div>

      <!-- Barra de filtros -->
      <div class="filtros-bar-wrap">
        <div class="filtros-bar">
          <button
            v-for="f in FILTROS"
            :key="f.key"
            class="chip"
            :class="{ active: filtroActivo === f.key }"
            :ref="f.key === 'personalizado' ? (el) => btnPersonalizadoRef = el : undefined"
            @click="onFiltroClick(f.key)"
          >
            {{ f.label }}
            <span v-if="f.key === 'hoy' && conteoHoy" class="chip-count">{{ conteoHoy }}</span>
            <span v-if="f.key === 'personalizado' && filtroPersonalizadoCount" class="chip-count">{{ filtroPersonalizadoCount }}</span>
          </button>

          <!-- Agrupar por -->
          <div style="position:relative;margin-left:auto;flex-shrink:0" ref="btnAgruparWrap">
            <button class="chip chip-agrupar" @click="toggleMenuAgrupar" ref="btnAgruparRef">
              <span class="material-icons" style="font-size:13px">sort</span>
              {{ AGRUPACIONES.find(a => a.key === agruparPor)?.label }}
              <span class="material-icons" style="font-size:13px">expand_more</span>
            </button>
            <Teleport to="body">
              <div v-if="menuAgrupar" class="dropdown-menu-teleport" :style="dropdownAgruparStyle" @mouseleave="menuAgrupar=false">
                <div
                  v-for="ag in AGRUPACIONES"
                  :key="ag.key"
                  class="dropdown-item-teleport"
                  :class="{ active: agruparPor === ag.key }"
                  @click="agruparPor = ag.key; menuAgrupar = false"
                >
                  <span class="material-icons" style="font-size:14px">{{ agruparPor === ag.key ? 'radio_button_checked' : 'radio_button_unchecked' }}</span>
                  {{ ag.label }}
                </div>
              </div>
            </Teleport>
          </div>
        </div>
      </div>

      <!-- QuickAdd (desktop y mobile) -->
      <div class="quickadd-wrap">
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
            @etiqueta-actualizada="e => { const i = etiquetas.findIndex(x => x.id === e.id); if (i !== -1) etiquetas[i] = e }"
            @etiqueta-eliminada="id => { const i = etiquetas.findIndex(x => x.id === id); if (i !== -1) etiquetas.splice(i, 1) }"
          />
        </div>
        <div v-if="qaActivo && qaCatEsProduccion" class="quickadd-op">
          <OpSelector v-model="qaOp" style="max-width:360px" />
        </div>
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
          <template v-for="t in grupo.tareas" :key="t.id">
            <TareaItem
              :tarea="t"
              :seleccionada="tareaSeleccionada?.id === t.id"
              :usuario-actual="auth.usuario?.email"
              :expandida="!!subtareasExpandidas[t.id]"
              @click="seleccionar"
              @cambiar-estado="cambiarEstado"
              @agregar-subtarea="iniciarSubtarea"
              @toggle-subtareas="toggleSubtareas"
            />
            <!-- Subtareas expandidas -->
            <template v-if="subtareasExpandidas[t.id]">
              <TareaItem
                v-for="sub in subtareasData[t.id] || []"
                :key="sub.id"
                :tarea="sub"
                :seleccionada="tareaSeleccionada?.id === sub.id"
                :usuario-actual="auth.usuario?.email"
                @click="seleccionar"
                @cambiar-estado="cambiarEstado"
              />
              <!-- Inline quickadd para nueva subtarea — Enter guarda, blur guarda, × cancela -->
              <div v-if="qaSubtareaParentId === t.id" class="subtarea-quickadd" @click.stop>
                <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">subdirectory_arrow_right</span>
                <input
                  ref="qaSubInputRef"
                  v-model="qaSubTitulo"
                  class="subtarea-input"
                  placeholder="Nueva subtarea..."
                  @keydown.enter.prevent="guardarSubtarea(t)"
                  @keydown.escape="cancelarSubtarea"
                  @blur="qaSubTitulo.trim() ? guardarSubtarea(t) : cancelarSubtarea()"
                />
                <button class="btn-sub-cancel" @click="cancelarSubtarea" title="Cancelar">
                  <span class="material-icons" style="font-size:13px">close</span>
                </button>
              </div>
            </template>
          </template>
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
        @abrir-padre="abrirPadre"
        class="d-desktop-only"
      />
    </Transition>

    <!-- Bottom sheet detalle de tarea (mobile) -->
    <Teleport to="body">
      <Transition name="bsheet">
        <div v-if="tareaSeleccionada && isMobile" class="bsheet-overlay" @click.self="tareaSeleccionada = null">
          <div class="bsheet-panel">
            <div class="bsheet-handle"></div>
            <TareaPanel
              :tarea="tareaSeleccionada"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="proyectos"
              :etiquetas="etiquetas"
              @cerrar="tareaSeleccionada = null"
              @actualizada="onTareaActualizada"
              @eliminar="eliminar"
              @proyecto-creado="p => proyectos.push(p)"
              @abrir-padre="abrirPadre"
            />
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Popup filtro personalizado -->
    <FiltroPersonalizado
      v-if="mostrarFiltroPopup"
      :categorias="categorias"
      :etiquetas="etiquetas"
      :proyectos="proyectos"
      :usuarios="usuarios"
      :anchor-el="btnPersonalizadoRef"
      :valor="filtroPersonalizado || {}"
      @aplicar="onAplicarFiltro"
      @cerrar="onCerrarFiltroPopup"
    />

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
import { ref, computed, onMounted, onUnmounted, watch, nextTick, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'

const props = defineProps({
  soloMias: { type: Boolean, default: true }
})
import TareaItem            from 'src/components/TareaItem.vue'
import TareaPanel           from 'src/components/TareaPanel.vue'
import TareaForm            from 'src/components/TareaForm.vue'
import OpSelector           from 'src/components/OpSelector.vue'
import ProyectoSelector     from 'src/components/ProyectoSelector.vue'
import EtiquetasSelector    from 'src/components/EtiquetasSelector.vue'
import FiltroPersonalizado  from 'src/components/FiltroPersonalizado.vue'

const auth  = useAuthStore()
const route = useRoute()

// Detección mobile (≤768px) — controla bottom sheet vs panel lateral
const isMobile = ref(typeof window !== 'undefined' && window.innerWidth <= 768)
function onResize() { isMobile.value = window.innerWidth <= 768 }

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
const menuAgrupar            = ref(false)
const btnAgruparRef          = ref(null)
const dropdownAgruparStyle   = ref({})
const filtroActivo      = ref('hoy')
const agruparPor        = ref(localStorage.getItem('gestion_agrupar') || 'categoria')

function toggleMenuAgrupar() {
  if (!menuAgrupar.value) {
    const rect = btnAgruparRef.value?.getBoundingClientRect()
    if (rect) {
      dropdownAgruparStyle.value = {
        position: 'fixed',
        top:  `${rect.bottom + 4}px`,
        right: `${window.innerWidth - rect.right}px`,
        zIndex: 9999
      }
    }
  }
  menuAgrupar.value = !menuAgrupar.value
}

// Filtro por proyecto (desde query param)
const proyectoFiltroId = computed(() => route.query.proyecto_id ? Number(route.query.proyecto_id) : null)
const proyectoFiltro   = computed(() => proyectos.value.find(p => p.id === proyectoFiltroId.value) || null)

// Subtareas
const subtareasExpandidas = ref({})   // { [tareaId]: true }
const subtareasData       = ref({})   // { [tareaId]: [subtarea, ...] }
const qaSubtareaParentId  = ref(null)
const qaSubTitulo         = ref('')
const qaSubInputRef       = ref(null)

async function toggleSubtareas(tarea) {
  const id = tarea.id
  if (subtareasExpandidas.value[id]) {
    subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: false }
    return
  }
  // Cargar subtareas si no están en caché
  if (!subtareasData.value[id]) {
    try {
      const data = await api(`/api/gestion/tareas/${id}/subtareas`)
      subtareasData.value = { ...subtareasData.value, [id]: data.subtareas || [] }
    } catch (e) { console.error(e); return }
  }
  subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: true }
}

async function iniciarSubtarea(tarea) {
  const id = tarea.id
  // Expandir primero si no está expandido
  if (!subtareasExpandidas.value[id]) {
    if (!subtareasData.value[id]) {
      try {
        const data = await api(`/api/gestion/tareas/${id}/subtareas`)
        subtareasData.value = { ...subtareasData.value, [id]: data.subtareas || [] }
      } catch {}
    }
    subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: true }
  }
  qaSubtareaParentId.value = id
  qaSubTitulo.value = ''
  await nextTick()
  const el = Array.isArray(qaSubInputRef.value) ? qaSubInputRef.value[0] : qaSubInputRef.value
  el?.focus()
}

function cancelarSubtarea() {
  qaSubtareaParentId.value = null
  qaSubTitulo.value = ''
}

async function guardarSubtarea(padre) {
  if (!qaSubTitulo.value.trim()) return
  try {
    const data = await api('/api/gestion/tareas', {
      method: 'POST',
      body: JSON.stringify({
        titulo:      qaSubTitulo.value.trim(),
        categoria_id: padre.categoria_id,
        proyecto_id:  padre.proyecto_id || null,
        parent_id:    padre.id
      })
    })
    // Agregar al array local de subtareas
    const subs = subtareasData.value[padre.id] || []
    subtareasData.value = { ...subtareasData.value, [padre.id]: [...subs, data.tarea] }
    // Actualizar conteo en la tarea padre
    const idx = tareas.value.findIndex(t => t.id === padre.id)
    if (idx !== -1) {
      tareas.value[idx] = { ...tareas.value[idx], subtareas_total: (tareas.value[idx].subtareas_total || 0) + 1 }
    }
    qaSubTitulo.value = ''
    await nextTick()
    const el = Array.isArray(qaSubInputRef.value) ? qaSubInputRef.value[0] : qaSubInputRef.value
    el?.focus()
  } catch (e) { console.error(e) }
}

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
  { key: 'hoy',          label: 'Hoy' },
  { key: 'manana',       label: 'Mañana' },
  { key: 'ayer',         label: 'Ayer' },
  { key: 'semana',       label: 'Esta semana' },
  { key: 'todas',        label: 'Todas' },
  { key: 'personalizado', label: 'Personalizado' }
]

// Filtro personalizado
const filtroPersonalizado   = ref(null)   // null = sin filtro activo
const mostrarFiltroPopup    = ref(false)
const btnPersonalizadoRef   = ref(null)

const filtroPersonalizadoCount = computed(() => {
  if (!filtroPersonalizado.value) return 0
  const f = filtroPersonalizado.value
  return [
    f.fecha_desde, f.fecha_hasta,
    ...(f.prioridades || []),
    ...(f.categorias  || []),
    ...(f.etiquetas   || []),
    f.proyecto_id
  ].filter(Boolean).length
})

function onFiltroClick(key) {
  if (key === 'personalizado') {
    mostrarFiltroPopup.value = !mostrarFiltroPopup.value
    filtroActivo.value = 'personalizado'
  } else {
    filtroActivo.value = key
    mostrarFiltroPopup.value = false
  }
}

function onAplicarFiltro(filtros) {
  filtroPersonalizado.value = filtros
  mostrarFiltroPopup.value  = false
  cargarTareas()
}

function onCerrarFiltroPopup() {
  mostrarFiltroPopup.value = false
  if (!filtroPersonalizado.value) filtroActivo.value = 'hoy'
}
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
watch(() => props.soloMias, () => cargarTareas())

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
    // Siempre enviar fecha local del cliente para evitar desfase de zona horaria con servidor Hostinger
    params.set('fecha_hoy', hoyISO())
    if (props.soloMias) params.set('solo_mias', '1')
    if (proyectoFiltroId.value) {
      params.set('proyecto_id', proyectoFiltroId.value)
    } else if (filtroActivo.value === 'personalizado' && filtroPersonalizado.value) {
      const f = filtroPersonalizado.value
      if (f.fecha_desde)              params.set('fecha_desde',  f.fecha_desde)
      if (f.fecha_hasta)              params.set('fecha_hasta',  f.fecha_hasta)
      if (f.prioridades?.length)      params.set('prioridades',  f.prioridades.join(','))
      if (f.categorias?.length)       params.set('categorias',   f.categorias.join(','))
      if (f.etiquetas?.length)        params.set('etiquetas',    f.etiquetas.join(','))
      if (f.proyecto_id)              params.set('proyecto_id',  f.proyecto_id)
      if (f.responsables?.length)     params.set('responsables', f.responsables.join(','))
      if (f.id_op)                    params.set('id_op',        f.id_op)
    } else if (filtroActivo.value !== 'todas' && filtroActivo.value !== 'personalizado') {
      params.set('filtro', filtroActivo.value)
    }
    const completadasParams = new URLSearchParams()
    if (props.soloMias) completadasParams.set('solo_mias', '1')
    if (proyectoFiltroId.value) completadasParams.set('proyecto_id', proyectoFiltroId.value)
    const completadasUrl = `/api/gestion/tareas/completadas?${completadasParams}`
    const [dataTareas, dataCompletadas] = await Promise.all([
      api(`/api/gestion/tareas?${params}`),
      api(completadasUrl)
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
  // Ciclo del check: Pendiente→EnProgreso→Completada→Pendiente
  // Cancelada: el check no la reactiva (se gestiona desde el panel de estado)
  const CICLO = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente' }
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

async function abrirPadre(parentId) {
  // Buscar en lista local primero
  let padre = tareas.value.find(t => t.id === parentId) || completadas.value.find(t => t.id === parentId)
  if (!padre) {
    try {
      const data = await api(`/api/gestion/tareas/${parentId}`)
      padre = data.tarea
    } catch { return }
  }
  tareaSeleccionada.value = padre
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
  window.addEventListener('resize', onResize)
  await Promise.all([cargarTareas(), cargarCatalogos()])
})
onUnmounted(() => { window.removeEventListener('resize', onResize) })
</script>

<style scoped>
.d-desktop-only { }
.d-mobile-only  { display: none; }
@media (max-width: 768px) {
  .d-mobile-only  { display: flex; }
  /* QuickAdd en mobile: padding ajustado */
  .quickadd-wrap { padding: 0 12px 8px; }
  /* Chips de categoría: scroll horizontal en lugar de wrap */
  .quickadd-cats {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-left: 0;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .quickadd-cats::-webkit-scrollbar { display: none; }
  /* Extra (proyecto + etiquetas) en móvil */
  .quickadd-extra { padding-left: 0; }
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

/* Dropdown agrupar — estilos movidos a app.scss como globales (teleport) */

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
/* Header de proyecto activo */
.proyecto-header-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px; flex-shrink: 0;
}
.proyecto-back-link {
  display: inline-flex; align-items: center; gap: 3px;
  color: var(--text-tertiary); text-decoration: none;
  transition: color 80ms;
}
.proyecto-back-link:hover { color: var(--text-primary); }
.proyecto-dot-hdr {
  width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
}
.proyecto-header-nombre {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
}

/* ─── SUBTAREAS ─── */
.subtarea-quickadd {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 16px 4px 40px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}
.subtarea-input {
  flex: 1; background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary);
  font-family: var(--font-sans);
}
.subtarea-input::placeholder { color: var(--text-tertiary); }
.btn-sub-cancel {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; flex-shrink: 0;
  background: transparent; border: none; border-radius: var(--radius-sm);
  color: var(--text-tertiary); cursor: pointer;
  transition: color 80ms, background 80ms;
}
.btn-sub-cancel:hover { color: var(--color-error); background: var(--color-error-bg); }
.subtarea-add-row {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 16px 6px 42px;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: color 80ms;
}
.subtarea-add-row:hover { color: var(--accent); }
</style>
