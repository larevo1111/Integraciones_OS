<template>
  <aside v-if="tarea" class="tarea-panel">
    <!-- Header -->
    <div class="tarea-panel-header">
      <!-- Fila 1: tipo + acciones -->
      <div class="panel-header-row">
        <div v-if="tarea.parent_id" class="subtarea-breadcrumb" @click="$emit('abrir-padre', tarea.parent_id)">
          <span class="material-icons" style="font-size:13px">arrow_back</span>
          <span>{{ padreNombre || 'Tarea padre' }}</span>
        </div>
        <span v-else class="panel-header-tipo">Tarea</span>
        <div class="panel-header-actions">
          <button v-if="hayCambiosPendientes" class="btn-icon" title="Guardar cambios" @click="guardarPendientes">
            <span class="material-icons" style="font-size:18px;color:var(--accent)">check</span>
          </button>
          <button class="btn-icon" title="Eliminar" @click="$emit('eliminar', tarea)">
            <span class="material-icons" style="font-size:16px">delete_outline</span>
          </button>
          <button class="btn-icon" title="Cerrar" @click="intentarCerrar">
            <span class="material-icons" style="font-size:18px">close</span>
          </button>
        </div>
      </div>
      <!-- Fila 2: estado + título -->
      <div class="panel-header-titulo-row">
        <EstadoBadge :estado="tarea.estado" @click="ciclarEstado" style="margin-top:2px;flex-shrink:0" />
        <textarea
          ref="tituloTextareaRef"
          class="tarea-panel-titulo"
          :value="tarea.titulo"
          rows="1"
          @input="autoResizeTitulo"
          @blur="e => e.target.value.trim() && e.target.value !== tarea.titulo && actualizar('titulo', e.target.value.trim())"
          @keydown.enter.prevent="e => { e.target.blur() }"
        />
      </div>
    </div>

    <!-- Body -->
    <div class="tarea-panel-body">
      <!-- Fila de chips compartida (estado, categoría, prioridad, etiquetas, fecha, responsable, proyecto) -->
      <TareaMetaChips
        show-estado
        :estado="tarea.estado"
        :categoria-id="tarea.categoria_id"
        :prioridad="tarea.prioridad"
        :etiquetas="(tarea.etiquetas||[]).map(e=>e.id)"
        :fecha-limite="fechaChipISO"
        :fecha-readonly="esCompletada"
        :responsables="tarea.responsables || (tarea.responsable ? [tarea.responsable] : [])"
        :proyecto-id="tarea.proyecto_id"
        :categorias="categorias"
        :etiquetas-disponibles="etiquetas"
        :usuarios="usuarios"
        :proyectos="proyectos"
        @update:estado="cambiarEstado"
        @update:categoria-id="val => actualizar('categoria_id', val)"
        @update:prioridad="val => actualizar('prioridad', val)"
        @update:etiquetas="actualizarEtiquetas"
        @update:fecha-limite="actualizarFechaEstimada"
        @update:responsables="val => actualizar('responsables', val)"
        @update:proyecto-id="val => actualizar('proyecto_id', val)"
        @crear-item="tipo => $emit('crear-item', tipo)"
        @etiqueta-creada="e => etiquetas.push(e)"
        @etiqueta-actualizada="e => { const i = etiquetas.findIndex(x => x.id === e.id); if (i !== -1) etiquetas[i] = e }"
        @etiqueta-eliminada="id => { const i = etiquetas.findIndex(x => x.id === id); if (i !== -1) etiquetas.splice(i, 1) }"
      />

      <!-- Detalles de producción: OP + materiales + productos (solo lectura) -->
      <DetallesProduccion
        v-if="esProduccion"
        :tarea="tarea"
        @actualizar-id-op="val => actualizar('id_op', val)"
        @abrir-op="id => $router.push({ path: '/ops-tabla', query: { op_id: id } })"
      />

      <!-- Categoría de producción (visible solo si hay OP vinculada) -->
      <div v-if="esProduccion && tarea.id_op" class="field-row">
        <span class="field-label">Cat. producción</span>
        <div style="flex:1;display:flex;flex-wrap:wrap;gap:4px">
          <q-chip
            v-for="cp in categoriasProduccion" :key="cp.id"
            :color="tarea.categoria_produccion_id === cp.id ? 'primary' : ''"
            :text-color="tarea.categoria_produccion_id === cp.id ? 'white' : 'grey-6'"
            :outline="tarea.categoria_produccion_id !== cp.id"
            size="sm" clickable dense
            :label="cp.nombre"
            style="font-size:11px;height:22px"
            @click="actualizar('categoria_produccion_id', tarea.categoria_produccion_id === cp.id ? null : cp.id)"
          />
        </div>
      </div>


      <!-- Remisión (solo Empaque) -->
      <div v-if="esEmpaque" class="field-row" style="align-items:flex-start">
        <span class="field-label" style="padding-top:8px">Remisión</span>
        <div style="flex:1;min-width:0">
          <RemisionSelector
            :modelValue="tarea.id_remision || ''"
            @update:modelValue="val => actualizar('id_remision', val)"
          />
        </div>
      </div>

      <!-- Pedido (solo Empaque) -->
      <div v-if="esEmpaque" class="field-row" style="align-items:flex-start">
        <span class="field-label" style="padding-top:8px">Pedido</span>
        <div style="flex:1;min-width:0">
          <PedidoSelector
            :modelValue="tarea.id_pedido || ''"
            @update:modelValue="val => actualizar('id_pedido', val)"
          />
        </div>
      </div>

      <div class="divider" />

      <!-- T. real con cronómetro integrado -->
      <div class="field-row">
        <span class="field-label">T. real</span>
        <div class="tiempos-compact">
          <Cronometro
            ref="cronometroRef"
            :tarea-id="tarea.id"
            :tarea="tarea"
            @update="onCronometroUpdate"
          />
          <CronoDisplay :tarea="tarea" />
        </div>
      </div>
      <!-- Tiempo estimado -->
      <div class="field-row">
        <span class="field-label">T. estimado</span>
        <div class="tiempos-compact">
          <input type="number" class="input-field t-input" :value="Math.floor((tarea.tiempo_estimado_min||0)/60)" min="0" @change="actualizarTiempoEst('h', $event.target.value)" />
          <span class="t-sep">h</span>
          <input type="number" class="input-field t-input" :value="(tarea.tiempo_estimado_min||0)%60" min="0" max="59" @change="actualizarTiempoEst('m', $event.target.value)" />
          <span class="t-sep">m</span>
        </div>
      </div>

      <div class="divider" />

      <!-- Subtareas (solo si no es a su vez una subtarea) -->
      <div v-if="!tarea.parent_id" class="subtareas-section">
        <div class="subtareas-header">
          <span class="input-label" style="margin:0">Subtareas <span v-if="subtareas.length" style="color:var(--text-tertiary);font-weight:400">({{ subtareas.length }})</span></span>
        </div>
        <form class="subtarea-quickadd" @submit.prevent="crearSubtarea">
          <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">subdirectory_arrow_right</span>
          <input
            ref="subInputRef"
            v-model="nuevaSubtitulo"
            class="subtarea-input"
            placeholder="Agregar subtarea..."
            @keydown.escape="nuevaSubtitulo = ''"
          />
          <button v-if="nuevaSubtitulo.trim()" type="submit" class="btn-sub-ok" title="Agregar">
            <span class="material-icons" style="font-size:13px">check</span>
          </button>
        </form>
        <div v-for="s in subtareas" :key="s.id" class="sub-link" @click="$emit('abrir-subtarea', s)">
          <button class="sub-link-circle" :class="{ done: s.estado === 'Completada', cancelada: s.estado === 'Cancelada' }" @click.stop="toggleEstadoSubtarea(s)">
            <span v-if="s.estado === 'Completada'" class="material-icons" style="font-size:11px">check</span>
            <span v-else-if="s.estado === 'Cancelada'" class="material-icons" style="font-size:11px">close</span>
          </button>
          <span class="sub-link-title" :class="{ done: s.estado === 'Completada' }">{{ s.titulo }}</span>
        </div>
      </div>

      <div v-if="!tarea.parent_id" class="divider" />

      <!-- Descripción -->
      <p class="input-label">Descripción</p>
      <textarea
        class="input-field"
        rows="5"
        :value="camposPendientes.descripcion !== undefined ? camposPendientes.descripcion : tarea.descripcion"
        placeholder="Agrega detalles, pasos a seguir..."
        @input="camposPendientes.descripcion = $event.target.value"
        @blur="guardarCampoPendiente('descripcion', $event.target.value)"
      />

      <!-- Notas -->
      <p class="input-label" style="margin-top:12px">Notas</p>
      <textarea
        class="input-field"
        rows="3"
        :value="camposPendientes.notas !== undefined ? camposPendientes.notas : tarea.notas"
        placeholder="Notas rápidas..."
        @input="camposPendientes.notas = $event.target.value"
        @blur="guardarCampoPendiente('notas', $event.target.value)"
      />

      <!-- Acordeón: más campos (al final) -->
      <div class="accordion-toggle" style="margin-top:12px" @click="mostrarFechas = !mostrarFechas">
        <span class="material-icons" style="font-size:13px">{{ mostrarFechas ? 'expand_more' : 'chevron_right' }}</span>
        <span style="font-size:10px;color:var(--text-tertiary)">Más campos</span>
      </div>
      <template v-if="mostrarFechas">
        <!-- Las 3 duraciones, siempre visibles, en formato HH:MM:SS -->
        <div class="field-row">
          <span class="field-label">Duración usuario</span>
          <span style="font-size:12px;color:var(--text-primary);font-variant-numeric:tabular-nums">{{ duracionUsuarioFmt }}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Duración cronómetro</span>
          <span style="font-size:12px;color:var(--text-secondary);font-variant-numeric:tabular-nums">{{ duracionCronometroFmt }}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Duración sistema</span>
          <span style="font-size:12px;color:var(--text-secondary);font-variant-numeric:tabular-nums">{{ duracionSistemaFmt }}</span>
        </div>
        <div class="divider" style="margin:8px 0"></div>
        <div class="field-row">
          <span class="field-label">Fecha estimada</span>
          <input type="date" class="input-field" style="height:28px;font-size:12px"
            :value="tarea.fecha_limite ? String(tarea.fecha_limite).slice(0,10) : ''"
            @change="actualizarFechaEstimada($event.target.value || null)" />
        </div>
        <div class="field-row">
          <span class="field-label">Inicio estimado</span>
          <input type="datetime-local" class="input-field" style="height:28px;font-size:12px"
            :value="tarea.fecha_inicio_estimada ? String(tarea.fecha_inicio_estimada).replace(' ', 'T').slice(0,16) : ''"
            @change="actualizar('fecha_inicio_estimada', $event.target.value || null)" />
        </div>
        <div v-if="tarea.fecha_inicio_real" class="field-row">
          <span class="field-label">Inicio real</span>
          <span style="font-size:12px;color:var(--text-secondary)">{{ fmtDT(tarea.fecha_inicio_real) }}</span>
        </div>
        <div v-if="tarea.fecha_fin_real" class="field-row">
          <span class="field-label">Fin real</span>
          <span style="font-size:12px;color:var(--text-secondary)">{{ fmtDT(tarea.fecha_fin_real) }}</span>
        </div>
        <div class="divider" style="margin:8px 0"></div>
        <div v-if="tarea.fecha_creacion" class="field-row">
          <span class="field-label">Fecha creación</span>
          <span style="font-size:12px;color:var(--text-tertiary)">{{ fmtDT(tarea.fecha_creacion) }}</span>
        </div>
        <div v-if="tarea.fecha_ult_modificacion" class="field-row">
          <span class="field-label">Última modificación</span>
          <span style="font-size:12px;color:var(--text-tertiary)">{{ fmtDT(tarea.fecha_ult_modificacion) }}</span>
        </div>
        <div v-if="tarea.usuario_creador" class="field-row">
          <span class="field-label">Creada por</span>
          <span style="font-size:12px;color:var(--text-tertiary)">{{ tarea.usuario_creador }}</span>
        </div>
      </template>
    </div>

  </aside>

  <!-- Modal guardar cambios -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="mostrarConfirmGuardar" class="confirm-overlay" @click.self="mostrarConfirmGuardar = false">
        <div class="confirm-box">
          <p class="confirm-msg">¿Guardar los cambios?</p>
          <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-accent" @click="confirmarGuardarYCerrar">Guardar</button>
            <button class="confirm-btn confirm-btn-danger" @click="descartarYCerrar">Descartar</button>
            <button class="confirm-btn" @click="mostrarConfirmGuardar = false">Cancelar</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Toast deshacer -->
  <ToastUndo ref="toastRef" />
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'
import { parseBackendDate, localISO, TZ_NAME } from 'src/services/fecha'
import { crearSubtarea as crearSubtareaFn } from 'src/composables/useTareas'
import EstadoBadge          from './EstadoBadge.vue'
import Cronometro           from './Cronometro.vue'
import CronoDisplay         from './CronoDisplay.vue'
import TareaMetaChips       from './TareaMetaChips.vue'
import DetallesProduccion   from './DetallesProduccion.vue'
import RemisionSelector     from './RemisionSelector.vue'
import PedidoSelector       from './PedidoSelector.vue'
import ToastUndo            from './ToastUndo.vue'


const props = defineProps({
  tarea:      { type: Object, default: null },
  usuarios:   { type: Array, default: () => [] },
  categorias: { type: Array, default: () => [] },
  proyectos:  { type: Array, default: () => [] },
  etiquetas:  { type: Array, default: () => [] }
})
const emit = defineEmits(['cerrar', 'eliminar', 'actualizada', 'crear-item', 'abrir-padre', 'abrir-subtarea', 'subtareas-cambiadas', 'completar-tarea'])

// ── Subtareas ──
const subtareas    = ref([])
const nuevaSubtitulo = ref('')

async function cargarSubtareas() {
  if (!props.tarea?.id || props.tarea.parent_id) { subtareas.value = []; return }
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/subtareas`)
    subtareas.value = data.subtareas || data.tareas || []
  } catch { subtareas.value = [] }
}

async function crearSubtarea() {
  const titulo = nuevaSubtitulo.value.trim()
  if (!titulo || !props.tarea?.id) return
  try {
    await crearSubtareaFn(props.tarea, titulo, {
      responsable: props.tarea.responsable,
      responsables: props.tarea.responsables || (props.tarea.responsable ? [props.tarea.responsable] : [])
    })
    nuevaSubtitulo.value = ''
    await cargarSubtareas()
    emit('subtareas-cambiadas')
  } catch (e) { console.error(e) }
}

async function toggleEstadoSubtarea(s) {
  const ciclo = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  const next = ciclo[s.estado] || 'Pendiente'
  try {
    await api(`/api/gestion/tareas/${s.id}`, { method: 'PUT', body: JSON.stringify({ estado: next }) })
    await cargarSubtareas()
    emit('subtareas-cambiadas')
  } catch (e) { console.error(e) }
}

watch(() => props.tarea?.id, cargarSubtareas, { immediate: true })

// Limpiar pendientes al cambiar de tarea
watch(() => props.tarea?.id, () => {
  Object.keys(camposPendientes).forEach(k => delete camposPendientes[k])
})

// Breadcrumb subtarea
const padreNombre = ref('')
watch(() => props.tarea?.parent_id, async (parentId) => {
  if (!parentId) { padreNombre.value = ''; return }
  try {
    const data = await api(`/api/gestion/tareas/${parentId}`)
    padreNombre.value = data.tarea?.titulo || ''
  } catch { padreNombre.value = '' }
}, { immediate: true })

// Acordeón fechas
const mostrarFechas = ref(false)

const esCompletada = computed(() =>
  ['Completada', 'Cancelada'].includes(props.tarea?.estado)
)

// En completadas el chip principal muestra fecha_fin_real (no editable);
// la fecha estimada queda en "Más campos".
const fechaChipISO = computed(() => {
  const t = props.tarea
  if (!t) return ''
  const raw = esCompletada.value ? (t.fecha_fin_real || t.fecha_limite) : t.fecha_limite
  if (!raw) return ''
  const d = parseBackendDate(raw)
  return d ? localISO(d) : ''
})

function fmtDT(val) {
  if (!val) return ''
  const d = parseBackendDate(val); if (!d) return ''
  return d.toLocaleString('es-CO', { timeZone: TZ_NAME, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Mostrar OP Effi solo si la categoría seleccionada es Producción
const esProduccion = computed(() => {
  if (!props.tarea?.categoria_id) return false
  const cat = props.categorias.find(c => c.id === props.tarea.categoria_id)
  return cat?.es_produccion || cat?.nombre?.toLowerCase().includes('produccion') || false
})

// Mostrar Remisión/Pedido solo si la categoría es Empaque
const esEmpaque = computed(() => {
  if (!props.tarea?.categoria_id) return false
  const cat = props.categorias.find(c => c.id === props.tarea.categoria_id)
  return cat?.es_empaque || false
})

// Toast deshacer
const toastRef = ref(null)

const LABELS_CAMPO = {
  estado: 'Estado', prioridad: 'Prioridad', categoria_id: 'Categoría',
  proyecto_id: 'Proyecto', responsable: 'Responsable', fecha_limite: 'Fecha',
  id_op: 'OP Effi', id_remision: 'Remisión', id_pedido: 'Pedido', descripcion: 'Descripción', notas: 'Notas',
  tiempo_estimado_min: 'T. estimado'
}

// Título auto-resize
const tituloTextareaRef = ref(null)
function autoResizeTitulo() {
  const el = tituloTextareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}
watch(() => props.tarea?.id, () => nextTick(autoResizeTitulo))
// Cargar catálogo de categorías de producción una vez
const categoriasProduccion = ref([])
async function _cargarCatProduccion() {
  if (categoriasProduccion.value.length) return
  try {
    const r = await api('/api/gestion/categorias-produccion')
    categoriasProduccion.value = r.categorias || []
  } catch (e) { console.warn('[TareaPanel] cat producción:', e?.message) }
}

onMounted(() => { nextTick(autoResizeTitulo); _cargarCatProduccion() })

// Cronómetro
import { formatHHMMSS, calcDuracionVivo, calcDuracionSistema } from 'src/services/crono'
const cronometroRef = ref(null)

// Las 3 duraciones formateadas para "Más campos" — reactivas con tick para En Progreso
const _tickRef = ref(0)
let _tickInterval = null
function _startTick() {
  _stopTick()
  _tickInterval = setInterval(() => { _tickRef.value++ }, 1000)
}
function _stopTick() { if (_tickInterval) { clearInterval(_tickInterval); _tickInterval = null } }
watch(() => [props.tarea?.estado, props.tarea?.crono_inicio], () => {
  if (props.tarea?.estado === 'En Progreso') _startTick()
  else _stopTick()
}, { immediate: true })
onUnmounted(_stopTick)

const duracionUsuarioFmt    = computed(() => { _tickRef.value; return formatHHMMSS(calcDuracionVivo(props.tarea)) })
const duracionCronometroFmt = computed(() => {
  _tickRef.value
  // En En Progreso, igual al usuario (con vivo). En otros estados, valor guardado
  if (props.tarea?.estado === 'En Progreso') return formatHHMMSS(calcDuracionVivo(props.tarea))
  return formatHHMMSS(props.tarea?.duracion_cronometro_seg || 0)
})
const duracionSistemaFmt    = computed(() => { _tickRef.value; return formatHHMMSS(calcDuracionSistema(props.tarea)) })


// Al setear fecha_estimada: sincroniza fecha_inicio_estimada si no tiene valor
async function actualizarFechaEstimada(valor) {
  const body = { fecha_limite: valor || null }
  if (!props.tarea.fecha_inicio_estimada) body.fecha_inicio_estimada = valor || null
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}`, {
      method: 'PUT',
      body: JSON.stringify(body)
    })
    emit('actualizada', data.tarea)
  } catch (e) { console.error(e) }
}

// ─── Cambios pendientes (descripción, notas) ───
const camposPendientes = reactive({})

const hayCambiosPendientes = computed(() => {
  for (const [campo, val] of Object.entries(camposPendientes)) {
    if (val !== undefined && val !== (props.tarea[campo] || '')) return true
  }
  return false
})

function guardarCampoPendiente(campo, valor) {
  const id = props.tarea?.id
  if (!id) { delete camposPendientes[campo]; return }
  if (valor !== (props.tarea[campo] || '')) {
    // Usar ID capturado — protege contra cambio de tarea durante blur
    api(`/api/gestion/tareas/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ [campo]: valor })
    }).then(data => emit('actualizada', data.tarea))
     .catch(e => console.error(e))
  }
  delete camposPendientes[campo]
}

async function guardarPendientes() {
  for (const [campo, val] of Object.entries(camposPendientes)) {
    if (val !== undefined && val !== (props.tarea[campo] || '')) {
      await actualizar(campo, val)
    }
  }
  Object.keys(camposPendientes).forEach(k => delete camposPendientes[k])
}

const mostrarConfirmGuardar = ref(false)

function intentarCerrar() {
  // Auto-guardar cambios pendientes al cerrar (sin pedir confirmación)
  if (hayCambiosPendientes.value) guardarPendientes()
  emit('cerrar')
}

function confirmarGuardarYCerrar() {
  mostrarConfirmGuardar.value = false
  guardarPendientes().then(() => emit('cerrar'))
}

function descartarYCerrar() {
  mostrarConfirmGuardar.value = false
  Object.keys(camposPendientes).forEach(k => delete camposPendientes[k])
  emit('cerrar')
}

async function actualizar(campo, valor) {
  if (!props.tarea) return
  const valorAnterior = props.tarea[campo]  // guardar antes de actualizar
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}`, {
      method: 'PUT',
      body: JSON.stringify({ [campo]: valor })
    })
    emit('actualizada', data.tarea)
    // Mostrar toast solo si el valor realmente cambió
    if (valorAnterior !== valor) {
      const label = LABELS_CAMPO[campo] || campo
      await nextTick()
      toastRef.value?.mostrar(
        `${label} actualizado`,
        () => actualizar(campo, valorAnterior)
      )
    }
  } catch (e) { console.error(e) }
}

// 5S — Una sola función para cambiar estado, llama al endpoint correcto
async function cambiarEstado(nuevoEstado) {
  if (!props.tarea) return
  if (nuevoEstado === 'Completada') { completar(); return }
  const endpoints = {
    'En Progreso': 'iniciar',
    'Cancelada':   'cancelar',
    'Pendiente':   'revertir'
  }
  const endpoint = endpoints[nuevoEstado]
  if (!endpoint) return
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/${endpoint}`, { method: 'POST' })
    if (data?.tarea) emit('actualizada', data.tarea)
  } catch (e) { console.error(e) }
}

function ciclarEstado() {
  const ciclo = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  cambiarEstado(ciclo[props.tarea.estado] || 'Pendiente')
}


async function actualizarEtiquetas(ids) {
  if (!props.tarea) return
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}`, {
      method: 'PUT',
      body: JSON.stringify({ etiquetas: ids })
    })
    emit('actualizada', data.tarea)
  } catch (e) { console.error(e) }
}

function actualizarTiempoEst(parte, val) {
  const h = parte === 'h' ? parseInt(val)||0 : Math.floor((props.tarea.tiempo_estimado_min||0)/60)
  const m = parte === 'm' ? parseInt(val)||0 : (props.tarea.tiempo_estimado_min||0)%60
  actualizar('tiempo_estimado_min', h*60+m)
}

function onCronometroUpdate(tareaActualizada) {
  if (tareaActualizada) emit('actualizada', tareaActualizada)
}

// completar() — delega al padre (TareasPage) para abrir el modal único
function completar() {
  emit('completar-tarea', props.tarea)
}
</script>

<style scoped>
.tarea-panel-titulo {
  flex: 1; min-width: 0; resize: none; overflow: hidden;
  background: transparent; border: none; outline: none;
  font-size: 15px; font-weight: 600; color: var(--text-primary);
  font-family: var(--font-sans); line-height: 1.3;
  padding: 0; margin: 0;
}
.panel-header-titulo-row {
  display: flex; align-items: flex-start; gap: 8px;
}
.crono-pausado {
  font-size: 12px; font-weight: 600; color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.subtarea-breadcrumb {
  display: flex; align-items: center; gap: 4px;
  padding: 2px 0 6px;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: color 80ms;
  user-select: none;
}
.subtarea-breadcrumb:hover { color: var(--accent); }

/* Sección Subtareas en TareaPanel */
.subtareas-section { display: flex; flex-direction: column; gap: 4px; }
.subtareas-header { display: flex; align-items: center; }
.subtarea-quickadd {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; border-radius: var(--radius-sm);
  background: var(--bg-row-hover);
}
.subtarea-input {
  flex: 1; min-width: 0; background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); font-family: var(--font-sans);
}
.subtarea-input::placeholder { color: var(--text-tertiary); }
.btn-sub-ok {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border: none; border-radius: var(--radius-sm);
  background: var(--accent); color: #fff; cursor: pointer;
}
.sub-link {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background 80ms;
}
.sub-link:hover { background: var(--bg-row-hover); }
.sub-link-circle {
  display: flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; flex-shrink: 0;
  border: 1.5px solid var(--border-strong);
  border-radius: var(--radius-full);
  background: transparent; color: #000; cursor: pointer; padding: 0;
}
.sub-link-circle.done { background: var(--color-success); border-color: var(--color-success); }
.sub-link-circle.cancelada { background: var(--text-tertiary); border-color: var(--text-tertiary); color: var(--bg-app); }
.sub-link-title {
  font-size: 14px; color: var(--text-primary); flex: 1; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sub-link-title.done { text-decoration: line-through; color: var(--text-tertiary); }
@media (max-width: 768px) {
  .sub-link-title { font-size: 15px; }
}

.prioridad-chips {
  display: flex; gap: 4px; flex-wrap: wrap;
}
.prioridad-chip {
  padding: 2px 8px; height: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: 11px;
  background: transparent;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: all 80ms;
  white-space: nowrap;
}
.prioridad-chip:hover { border-color: var(--border-default); color: var(--text-secondary); }
.prioridad-chip.active { font-weight: 500; }
.p-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  opacity: 0.85;
}
.accordion-toggle {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 0 2px; cursor: pointer;
  user-select: none;
  color: var(--text-tertiary);
  transition: color 80ms;
}
.accordion-toggle:hover { color: var(--text-secondary); }
.field-row-disabled { opacity: 0.45; pointer-events: none; }

/* Tiempos Real | Estimado — una sola fila compacta */
.tiempos-compact {
  display: flex; align-items: center; gap: 3px; flex-wrap: nowrap;
}
.t-lbl {
  font-size: 9px; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.04em;
  font-weight: 500; flex-shrink: 0; margin-right: 1px;
}
.t-sep {
  font-size: 10px; color: var(--text-tertiary); flex-shrink: 0;
}
.crono-seg {
  font-size: 10px; color: var(--accent); font-variant-numeric: tabular-nums;
  flex-shrink: 0; margin-left: 2px;
}
.t-div {
  font-size: 11px; color: var(--border-subtle); margin: 0 5px; flex-shrink: 0;
}
.t-input {
  width: 32px !important; height: 20px !important;
  font-size: 10px !important; text-align: center; padding: 0 2px !important;
}

/* Confirm modal */
.confirm-overlay {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
}
.confirm-box {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  min-width: 260px;
  box-shadow: var(--shadow-lg);
}
.confirm-msg {
  font-size: 14px; font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 16px;
}
.confirm-actions {
  display: flex; gap: 8px; justify-content: flex-end;
}
.confirm-btn {
  padding: 6px 14px; border-radius: var(--radius-sm);
  font-size: 12px; font-family: var(--font-sans);
  border: 1px solid var(--border-default);
  background: transparent; color: var(--text-secondary);
  cursor: pointer; transition: all 80ms;
}
.confirm-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.confirm-btn-accent {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
.confirm-btn-accent:hover { opacity: 0.9; background: var(--accent); color: #fff; }
.confirm-btn-danger {
  color: #ef4444; border-color: #ef444466;
}
.confirm-btn-danger:hover { background: rgba(239,68,68,0.1); }

.modal-enter-active, .modal-leave-active { transition: opacity 120ms; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

</style>
