<template>
  <div class="cal-page">

    <!-- Calendario mensual -->
    <div class="cal-header">
      <button class="cal-nav" @click="mesAnterior">
        <span class="material-icons">chevron_left</span>
      </button>
      <span class="cal-mes-label">{{ mesLabel }}</span>
      <button class="cal-nav" @click="mesSiguiente">
        <span class="material-icons">chevron_right</span>
      </button>
      <button v-if="mesOffset !== 0" class="cal-hoy-btn" @click="irAHoy">Hoy</button>
    </div>

    <div class="cal-grid">
      <div v-for="d in diasSemana" :key="d" class="cal-dow">{{ d }}</div>
      <div
        v-for="(celda, i) in celdas"
        :key="i"
        class="cal-cell"
        :class="{
          'cal-otro-mes': celda.otroMes,
          'cal-hoy': celda.iso === hoyISO,
          'cal-selected': celda.iso === fechaSel,
          'cal-tiene-tareas': conteosPorDia[celda.iso]
        }"
        @click="seleccionarDia(celda.iso)"
      >
        <span class="cal-num">{{ celda.dia }}</span>
        <span v-if="conteosPorDia[celda.iso]" class="cal-dot" />
      </div>
    </div>

    <!-- Tareas del día seleccionado -->
    <div class="cal-dia-header">
      <span class="cal-dia-label">{{ diaSelLabel }}</span>
      <span class="cal-dia-count">{{ tareasDia.length }} tarea{{ tareasDia.length !== 1 ? 's' : '' }}</span>
    </div>

    <div class="cal-lista" v-if="!cargando">
      <template v-if="tareasDia.length">
        <TareaItem
          v-for="t in tareasDia"
          :key="t.id"
          :tarea="t"
          :seleccionada="tareaSeleccionada?.id === t.id"
          :usuario-actual="auth.usuario?.email"
          :mostrar-responsable="true"
          @click="seleccionarTarea"
          @cambiar-estado="cambiarEstado"
        />
      </template>
      <div v-else class="cal-vacio">Sin tareas para este día</div>
    </div>
    <div v-else class="cal-vacio">Cargando...</div>

    <!-- Panel lateral detalle -->
    <Transition name="panel">
      <TareaPanel
        v-if="tareaSeleccionada && !isMobile"
        :tarea="tareaSeleccionada"
        :usuarios="usuarios"
        :categorias="categorias"
        :proyectos="[]"
        :etiquetas="[]"
        @cerrar="tareaSeleccionada = null"
        @actualizada="onTareaActualizada"
        class="d-desktop-only"
      />
    </Transition>

    <!-- Bottom sheet mobile -->
    <Teleport to="body">
      <Transition name="bsheet">
        <div v-if="tareaSeleccionada && isMobile" class="bsheet-overlay" @click.self="tareaSeleccionada = null">
          <div class="bsheet-panel">
            <div class="bsheet-handle-area"><div class="bsheet-handle"></div></div>
            <TareaPanel
              :tarea="tareaSeleccionada"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="[]"
              :etiquetas="[]"
              @cerrar="tareaSeleccionada = null"
              @actualizada="onTareaActualizada"
            />
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import TareaItem  from 'src/components/TareaItem.vue'
import TareaPanel from 'src/components/TareaPanel.vue'

const auth = useAuthStore()

// ─── Estado ───
const mesOffset         = ref(0)          // 0 = mes actual, -1 = anterior, +1 = siguiente
const fechaSel          = ref(hoyStr())   // YYYY-MM-DD seleccionado
const tareas            = ref([])
const categorias        = ref([])
const usuarios          = ref([])
const cargando          = ref(false)
const tareaSeleccionada = ref(null)
const isMobile          = ref(typeof window !== 'undefined' && window.innerWidth <= 768)

function onResize() { isMobile.value = window.innerWidth <= 768 }
onMounted(() => { window.addEventListener('resize', onResize); cargarCatalogos(); cargarMes() })

// ─── Helpers fecha ───
function hoyStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
const hoyISO = hoyStr()

function mesBase() {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() + mesOffset.value)
  return d
}

const mesLabel = computed(() => {
  const d = mesBase()
  const nombre = d.toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })
  return nombre.charAt(0).toUpperCase() + nombre.slice(1)
})

const diasSemana = ['L', 'M', 'M', 'J', 'V', 'S', 'D']

const celdas = computed(() => {
  const base = mesBase()
  const año = base.getFullYear()
  const mes = base.getMonth()

  const primerDia = new Date(año, mes, 1)
  let startDow = primerDia.getDay()      // 0=dom
  startDow = startDow === 0 ? 6 : startDow - 1  // 0=lun

  const ultimoDia = new Date(año, mes + 1, 0).getDate()
  const result = []

  // Días del mes anterior
  const prevUltimo = new Date(año, mes, 0).getDate()
  for (let i = startDow - 1; i >= 0; i--) {
    const d = new Date(año, mes - 1, prevUltimo - i)
    result.push({ dia: prevUltimo - i, iso: fmtISO(d), otroMes: true })
  }

  // Días del mes
  for (let d = 1; d <= ultimoDia; d++) {
    const fecha = new Date(año, mes, d)
    result.push({ dia: d, iso: fmtISO(fecha), otroMes: false })
  }

  // Completar hasta 42 celdas (6 filas)
  const rest = 42 - result.length
  for (let d = 1; d <= rest; d++) {
    const fecha = new Date(año, mes + 1, d)
    result.push({ dia: d, iso: fmtISO(fecha), otroMes: true })
  }

  return result
})

function fmtISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

// ─── Rango del mes visible (para la query) ───
const rangoMes = computed(() => {
  const c = celdas.value
  return { desde: c[0].iso, hasta: c[c.length - 1].iso }
})

// ─── Conteo por día (para los dots) ───
const conteosPorDia = computed(() => {
  const m = {}
  for (const t of tareas.value) {
    if (t.fecha_limite) { m[t.fecha_limite] = (m[t.fecha_limite] || 0) + 1 }
  }
  return m
})

// ─── Tareas del día seleccionado ───
const tareasDia = computed(() =>
  tareas.value.filter(t => t.fecha_limite === fechaSel.value)
)

const diaSelLabel = computed(() => {
  const [y, m, d] = fechaSel.value.split('-').map(Number)
  const fecha = new Date(y, m - 1, d)
  const label = fecha.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })
  return label.charAt(0).toUpperCase() + label.slice(1)
})

// ─── Navegación ───
function mesAnterior() { mesOffset.value-- }
function mesSiguiente() { mesOffset.value++ }
function irAHoy() { mesOffset.value = 0; fechaSel.value = hoyStr() }
function seleccionarDia(iso) { fechaSel.value = iso }

watch(mesOffset, () => cargarMes())

// ─── Carga datos ───
async function cargarMes() {
  cargando.value = true
  try {
    const { desde, hasta } = rangoMes.value
    const params = new URLSearchParams({
      fecha_desde: desde,
      fecha_hasta: hasta,
      fecha_hoy: hoyStr()
    })
    const data = await api(`/api/gestion/tareas?${params}`)
    tareas.value = data.tareas || []
  } catch (e) { console.error(e) }
  cargando.value = false
}

async function cargarCatalogos() {
  try {
    const [resCat, resUsr] = await Promise.allSettled([
      api('/api/gestion/categorias'),
      api('/api/gestion/usuarios')
    ])
    if (resCat.status === 'fulfilled') categorias.value = resCat.value.categorias || []
    if (resUsr.status === 'fulfilled') usuarios.value = resUsr.value.usuarios || []
  } catch {}
}

// ─── Acciones sobre tareas ───
function seleccionarTarea(tarea) {
  tareaSeleccionada.value = tareaSeleccionada.value?.id === tarea.id ? null : tarea
}

async function cambiarEstado(tarea) {
  const CICLO = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente' }
  const next = CICLO[tarea.estado] || 'Pendiente'
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}`, {
      method: 'PUT', body: JSON.stringify({ estado: next })
    })
    onTareaActualizada(data.tarea)
  } catch (e) { console.error(e) }
}

function onTareaActualizada(t) {
  const idx = tareas.value.findIndex(x => x.id === t.id)
  if (idx !== -1) tareas.value[idx] = t
  else tareas.value.push(t)
  if (tareaSeleccionada.value?.id === t.id) tareaSeleccionada.value = t
}
</script>

<style scoped>
.cal-page {
  display: flex; flex-direction: column;
  height: 100%; overflow: hidden;
}

/* Header navegación mes */
.cal-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px 8px;
  flex-shrink: 0;
}
.cal-mes-label {
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  min-width: 140px; text-align: center;
}
.cal-nav {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  background: transparent; border: none;
  color: var(--text-secondary); cursor: pointer;
  transition: background 80ms;
}
.cal-nav:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.cal-hoy-btn {
  margin-left: auto;
  padding: 2px 10px; height: 24px;
  border-radius: var(--radius-sm); border: 1px solid var(--border-default);
  background: transparent; color: var(--text-secondary);
  font-size: 11px; cursor: pointer;
  transition: all 80ms;
}
.cal-hoy-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }

/* Grid calendario */
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  padding: 0 12px 8px;
  flex-shrink: 0;
}
.cal-dow {
  text-align: center;
  font-size: 10px; font-weight: 600;
  color: var(--text-tertiary);
  padding: 4px 0;
}
.cal-cell {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 80ms;
  position: relative;
}
.cal-cell:hover { background: var(--bg-row-hover); }
.cal-num { font-size: 12px; color: var(--text-primary); line-height: 1; }
.cal-otro-mes .cal-num { color: var(--text-tertiary); opacity: 0.5; }
.cal-hoy .cal-num {
  background: var(--accent); color: #000;
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600;
}
.cal-selected { background: var(--bg-row-selected); }
.cal-selected .cal-num { color: var(--accent); font-weight: 600; }
.cal-hoy.cal-selected .cal-num { color: #000; }

.cal-dot {
  position: absolute; bottom: 3px;
  width: 4px; height: 4px; border-radius: 50%;
  background: var(--accent);
}

/* Header día seleccionado */
.cal-dia-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px 4px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.cal-dia-label {
  font-size: 13px; font-weight: 600;
  color: var(--text-primary);
}
.cal-dia-count {
  font-size: 11px; color: var(--text-tertiary);
}

/* Lista tareas */
.cal-lista {
  flex: 1; overflow-y: auto; min-height: 0;
  padding: 4px 0;
}
.cal-vacio {
  padding: 24px 16px;
  text-align: center;
  font-size: 12px; color: var(--text-tertiary);
}

/* Panel lateral desktop */
.panel-enter-active, .panel-leave-active { transition: transform 200ms ease-out, opacity 200ms; }
.panel-enter-from, .panel-leave-to { transform: translateX(20px); opacity: 0; }
</style>
