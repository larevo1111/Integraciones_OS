<template>
  <Teleport to="body">
    <div class="pp-overlay" @click.self="$emit('cerrar')">
      <aside
        class="pp-panel"
        :class="{ 'pp-panel-full': ppSheetEstado === 'full' }"
        :style="ppDragStyle"
      >

        <!-- Handle arrastrable (solo mobile) -->
        <div
          class="pp-handle-area"
          @touchstart="ppTouchStart"
          @touchmove.prevent="ppTouchMove"
          @touchend="ppTouchEnd"
          @touchcancel="ppTouchEnd"
        >
          <div class="pp-handle"></div>
          <button v-if="ppSheetEstado === 'full'" class="pp-handle-close" @click.stop="$emit('cerrar')">
            <span class="material-icons" style="font-size:20px">close</span>
          </button>
        </div>

        <!-- ═══ SUB-PANEL: Detalle tarea ═══ -->
        <template v-if="tareaAbierta">
          <div class="pp-header">
            <button class="pp-btn-icon" @click="cerrarSubTarea" title="Volver">
              <span class="material-icons" style="font-size:18px">arrow_back</span>
            </button>
            <span class="pp-header-tipo">Tarea</span>
            <div style="display:flex;gap:4px;margin-left:auto">
              <button class="pp-btn-icon" @click="$emit('cerrar')">
                <span class="material-icons" style="font-size:18px">close</span>
              </button>
            </div>
          </div>
          <div class="pp-subtarea-wrap">
            <TareaPanel
              :tarea="tareaAbierta"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="[]"
              :etiquetas="etiquetas"
              @cerrar="cerrarSubTarea"
              @actualizada="onSubTareaActualizada"
              @crear-item="() => {}"
              @abrir-padre="() => {}"
            />
          </div>
        </template>

        <!-- ═══ CONTENIDO PRINCIPAL: Proyecto/Dificultad/etc ═══ -->
        <template v-else>
        <!-- Header -->
        <div class="pp-header">
          <span class="pp-header-tipo">{{ LABELS[tipoLocal].singular }}</span>
          <div style="display:flex;gap:4px;margin-left:auto">
            <button v-if="item?.id" class="pp-btn-icon" title="Eliminar" @click="eliminar">
              <span class="material-icons" style="font-size:16px">delete_outline</span>
            </button>
            <button class="pp-btn-icon" @click="$emit('cerrar')">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>
        </div>

        <!-- Body scroll -->
        <div class="pp-body">

          <!-- Título editable -->
          <input
            ref="tituloRef"
            class="pp-titulo"
            :value="form.nombre"
            :placeholder="LABELS[tipoLocal].placeholder"
            @blur="guardarCampo('nombre', $event.target.value.trim())"
            @keydown.enter.prevent="e => e.target.blur()"
          />

          <!-- Propiedades quick-edit -->
          <div class="pp-fields">

            <!-- Estado -->
            <div class="pp-field-row">
              <span class="pp-field-label">Estado</span>
              <div class="pp-chips">
                <button
                  v-for="e in estadosDisponibles"
                  :key="e"
                  class="pp-chip"
                  :class="{ active: form.estado === e }"
                  @click="guardarCampo('estado', e)"
                >{{ e }}</button>
              </div>
            </div>

            <!-- Prioridad -->
            <div class="pp-field-row">
              <span class="pp-field-label">Prioridad</span>
              <div class="pp-chips">
                <button
                  v-for="p in PRIORIDADES"
                  :key="p.key"
                  class="pp-chip"
                  :class="{ active: form.prioridad === p.key }"
                  :style="form.prioridad === p.key ? { background: p.color + '22', borderColor: p.color, color: p.color } : {}"
                  @click="guardarCampo('prioridad', p.key)"
                >
                  <span class="pp-dot" :style="{ background: p.color }"></span>
                  {{ p.key }}
                </button>
              </div>
            </div>

            <!-- Color -->
            <div class="pp-field-row">
              <span class="pp-field-label">Color</span>
              <div class="pp-chips">
                <button
                  v-for="c in COLORES"
                  :key="c"
                  class="pp-color-dot"
                  :class="{ active: form.color === c }"
                  :style="{ background: c }"
                  @click="guardarCampo('color', c)"
                />
              </div>
            </div>

            <!-- Categoría -->
            <div class="pp-field-row">
              <span class="pp-field-label">Categoría</span>
              <CategoriaSelector
                :model-value="form.categoria_id"
                :categorias="categorias"
                @update:model-value="guardarCampo('categoria_id', $event)"
              />
            </div>

            <!-- Responsable -->
            <div class="pp-field-row" style="align-items:flex-start">
              <span class="pp-field-label" style="padding-top:4px">Responsable</span>
              <ResponsablesSelector
                :model-value="form.responsables"
                :usuarios="usuarios"
                @update:model-value="guardarRelacion('responsables', $event)"
              />
            </div>

            <!-- Etiquetas -->
            <div class="pp-field-row" style="align-items:flex-start">
              <span class="pp-field-label" style="padding-top:4px">Etiquetas</span>
              <EtiquetasSelector
                :model-value="form.etiquetas_ids"
                :etiquetas="etiquetas"
                @update:model-value="guardarRelacion('etiquetas', $event)"
                @etiqueta-creada="e => etiquetas.push(e)"
              />
            </div>

            <!-- Fecha estimada -->
            <div class="pp-field-row">
              <span class="pp-field-label">Fecha estimada</span>
              <input
                type="date"
                class="pp-input"
                :value="form.fecha_estimada_fin ? String(form.fecha_estimada_fin).slice(0,10) : ''"
                @change="guardarCampo('fecha_estimada_fin', $event.target.value || null)"
              />
            </div>
          </div>

          <!-- Desarrollo (TipTap) -->
          <div class="pp-section">
            <span class="pp-section-label">Desarrollo</span>
            <TipTapEditor
              v-model="form.descripcion"
              :placeholder="'Describe la situación, documenta el progreso...'"
              :upload-tipo="tipoLocal"
              :upload-item-id="item?.id || ''"
              :upload-item-nombre="form.nombre"
              @update:model-value="guardarCampo('descripcion', $event)"
            />
          </div>

          <!-- Tareas vinculadas -->
          <div v-if="item?.id" class="pp-section">
            <span class="pp-section-label">Tareas vinculadas ({{ tareasVinculadas.length }})</span>
            <div v-if="!tareasVinculadas.length" class="pp-empty">Sin tareas vinculadas</div>
            <div v-for="t in tareasVinculadas" :key="t.id" class="pp-tarea-link" @click="abrirSubTarea(t)">
              <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">
                {{ t.estado === 'Completada' ? 'check_circle' : 'radio_button_unchecked' }}
              </span>
              <span :class="{ 'pp-tarea-done': t.estado === 'Completada' }">{{ t.titulo }}</span>
            </div>
          </div>

          <!-- Auditoría -->
          <div v-if="item?.id" class="pp-audit">
            <span v-if="item.usuario_creador">Creado por {{ item.usuario_creador.split('@')[0] }} · {{ fmtFecha(item.fecha_creacion) }}</span>
            <span v-if="item.usuario_ult_modificacion">Editado por {{ item.usuario_ult_modificacion.split('@')[0] }} · {{ fmtFecha(item.fecha_ult_modificacion) }}</span>
          </div>
        </div>

        <!-- Footer solo para crear (no editar) -->
        <div v-if="!item?.id" class="pp-footer">
          <button class="pp-btn-cancel" @click="$emit('cerrar')">Cancelar</button>
          <button class="pp-btn-crear" :disabled="!form.nombre?.trim() || guardando" @click="crear">
            {{ guardando ? 'Creando...' : `Crear ${LABELS[tipoLocal].singular.toLowerCase()}` }}
          </button>
        </div>
        </template>
      </aside>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { api } from 'src/services/api'
import CategoriaSelector from './CategoriaSelector.vue'
import ResponsablesSelector from './ResponsablesSelector.vue'
import EtiquetasSelector from './EtiquetasSelector.vue'
import TipTapEditor from './TipTapEditor.vue'
import TareaPanel from './TareaPanel.vue'

const props = defineProps({
  item:        { type: Object, default: null },     // null = crear nuevo
  tipo:        { type: String, default: 'proyecto' }, // proyecto|dificultad|compromiso|idea
  categorias:  { type: Array, default: () => [] },
  usuarios:    { type: Array, default: () => [] },
  etiquetas:   { type: Array, default: () => [] },
})
const emit = defineEmits(['cerrar', 'guardado', 'eliminado'])

const LABELS = {
  proyecto:    { singular: 'Proyecto',    placeholder: 'Nombre del proyecto...' },
  dificultad:  { singular: 'Dificultad',  placeholder: 'Describe la dificultad...' },
  compromiso:  { singular: 'Compromiso',  placeholder: 'Describe el compromiso...' },
  idea:        { singular: 'Idea',        placeholder: 'Describe la idea...' },
}

const ESTADOS = {
  proyecto:   ['Activo', 'Completado', 'Archivado'],
  dificultad: ['Abierta', 'En progreso', 'Resuelta', 'Cerrada'],
  compromiso: ['Pendiente', 'En progreso', 'Cumplido', 'Cancelado'],
  idea:       ['Nueva', 'En evaluación', 'Aprobada', 'Descartada'],
}
const ESTADOS_DEFAULT = { proyecto: 'Activo', dificultad: 'Abierta', compromiso: 'Pendiente', idea: 'Nueva' }

const PRIORIDADES = [
  { key: 'Baja',    color: '#78909C' },
  { key: 'Media',   color: '#42A5F5' },
  { key: 'Alta',    color: '#FFA726' },
  { key: 'Urgente', color: '#EF5350' },
]

const COLORES = ['#ef4444','#f97316','#eab308','#22c55e','#00C853','#14b8a6','#3b82f6','#8b5cf6','#ec4899','#607D8B']

const tipoLocal = computed(() => props.item?.tipo || props.tipo)
const estadosDisponibles = computed(() => ESTADOS[tipoLocal.value] || ESTADOS.proyecto)
const guardando = ref(false)
const tituloRef = ref(null)

// ─── DRAG (mobile bottom sheet) ───
const ppSheetEstado   = ref('half')
const ppDragY         = ref(0)
const ppDragging      = ref(false)
let   _ppTouchStartY  = 0
let   _ppEstadoInicio = 'half'

const ppDragStyle = computed(() =>
  ppDragging.value && ppDragY.value !== 0
    ? { transform: `translateY(${ppDragY.value}px)`, transition: 'none' }
    : {}
)
function ppTouchStart(e) {
  _ppTouchStartY  = e.touches[0].clientY
  _ppEstadoInicio = ppSheetEstado.value
  ppDragging.value = true
  ppDragY.value = 0
}
function ppTouchMove(e) {
  if (!ppDragging.value) return
  const delta = e.touches[0].clientY - _ppTouchStartY
  if (_ppEstadoInicio === 'half') {
    ppDragY.value = Math.max(-window.innerHeight * 0.46, Math.min(delta, window.innerHeight))
  } else {
    ppDragY.value = Math.max(0, delta)
  }
}
function ppTouchEnd() {
  const delta = ppDragY.value
  ppDragging.value = false
  ppDragY.value = 0
  if (_ppEstadoInicio === 'half') {
    if (delta < -80)  ppSheetEstado.value = 'full'
    else if (delta > 120) emit('cerrar')
  } else {
    if (delta > 100) ppSheetEstado.value = 'half'
  }
}
const tareasVinculadas = ref([])
const tareaAbierta = ref(null)

async function abrirSubTarea(t) {
  // Cargar detalle completo de la tarea
  try {
    const data = await api(`/api/gestion/tareas/${t.id}`)
    tareaAbierta.value = data.tarea || t
  } catch { tareaAbierta.value = t }
}

function cerrarSubTarea() {
  tareaAbierta.value = null
}

function onSubTareaActualizada(tareaActualizada) {
  // Actualizar en la lista de tareas vinculadas
  const idx = tareasVinculadas.value.findIndex(x => x.id === tareaActualizada.id)
  if (idx !== -1) tareasVinculadas.value[idx] = { ...tareasVinculadas.value[idx], ...tareaActualizada }
}

const form = ref({
  nombre: '',
  descripcion: '',
  estado: '',
  prioridad: 'Media',
  color: '#607D8B',
  categoria_id: null,
  responsables: [],
  etiquetas_ids: [],
  fecha_estimada_fin: null,
})

function initForm() {
  if (props.item) {
    form.value = {
      nombre: props.item.nombre || '',
      descripcion: props.item.descripcion || '',
      estado: props.item.estado || ESTADOS_DEFAULT[tipoLocal.value],
      prioridad: props.item.prioridad || 'Media',
      color: props.item.color || '#607D8B',
      categoria_id: props.item.categoria_id || null,
      responsables: props.item.responsables || [],
      etiquetas_ids: (props.item.etiquetas || []).map(e => e.id),
      fecha_estimada_fin: props.item.fecha_estimada_fin || null,
    }
  } else {
    form.value = {
      nombre: '',
      descripcion: '',
      estado: ESTADOS_DEFAULT[tipoLocal.value],
      prioridad: 'Media',
      color: '#607D8B',
      categoria_id: null,
      responsables: [],
      etiquetas_ids: [],
      fecha_estimada_fin: null,
    }
  }
}

watch(() => props.item, (v, old) => { if (v && (!old || v.id !== old?.id)) ppSheetEstado.value = 'half'; initForm() }, { immediate: true })

onMounted(async () => {
  await nextTick()
  if (tituloRef.value && !props.item?.id) tituloRef.value.focus()
  if (props.item?.id) cargarTareas()
})

async function cargarTareas() {
  try {
    const data = await api(`/api/gestion/tareas?proyecto_id=${props.item.id}&estado=`)
    tareasVinculadas.value = data.tareas || []
  } catch { tareasVinculadas.value = [] }
}

// ── Guardar campo individual (edit mode) ──
async function guardarCampo(campo, valor) {
  form.value[campo] = valor
  if (!props.item?.id) return // modo crear — no guardar aún
  try {
    const body = { [campo]: valor }
    await api(`/api/gestion/proyectos/${props.item.id}`, {
      method: 'PUT', body: JSON.stringify(body)
    })
    emit('guardado', { ...props.item, ...form.value, _accion: 'editado' })
  } catch (e) { console.error('Error guardando:', e) }
}

async function guardarRelacion(campo, valor) {
  if (campo === 'responsables') {
    form.value.responsables = valor
  } else if (campo === 'etiquetas') {
    form.value.etiquetas_ids = valor
  }
  if (!props.item?.id) return
  try {
    await api(`/api/gestion/proyectos/${props.item.id}`, {
      method: 'PUT', body: JSON.stringify({ [campo]: valor })
    })
    emit('guardado', { ...props.item, ...form.value, _accion: 'editado' })
  } catch (e) { console.error('Error guardando relación:', e) }
}

// ── Crear nuevo ──
async function crear() {
  if (!form.value.nombre?.trim()) return
  guardando.value = true
  try {
    const body = {
      tipo: tipoLocal.value,
      nombre: form.value.nombre.trim(),
      descripcion: form.value.descripcion || null,
      estado: form.value.estado,
      prioridad: form.value.prioridad,
      color: form.value.color,
      categoria_id: form.value.categoria_id,
      responsables: form.value.responsables,
      etiquetas: form.value.etiquetas_ids,
      fecha_estimada_fin: form.value.fecha_estimada_fin,
    }
    const data = await api('/api/gestion/proyectos', {
      method: 'POST', body: JSON.stringify(body)
    })
    emit('guardado', { ...data.proyecto, _accion: 'creado' })
    emit('cerrar')
  } catch (e) { console.error('Error creando:', e) }
  finally { guardando.value = false }
}

async function eliminar() {
  const label = LABELS[tipoLocal.value].singular.toLowerCase()
  if (!confirm(`¿Eliminar "${form.value.nombre}"? Las tareas quedarán sin ${label}.`)) return
  try {
    await api(`/api/gestion/proyectos/${props.item.id}`, { method: 'DELETE' })
    emit('eliminado', props.item)
    emit('cerrar')
  } catch (e) { console.error('Error eliminando:', e) }
}

function fmtFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const dias = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (dias === 0) return 'hoy'
  if (dias === 1) return 'ayer'
  if (dias < 7) return `hace ${dias} días`
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.pp-overlay {
  position: fixed; inset: 0; z-index: 5000;
  background: rgba(0,0,0,0.4);
  display: flex; justify-content: flex-end;
}
.pp-panel {
  width: 500px; max-width: 100%;
  height: 100vh;
  background: var(--bg-card);
  border-left: 1px solid var(--border-default);
  display: flex; flex-direction: column;
  animation: pp-slide-in 180ms ease-out;
}
@keyframes pp-slide-in {
  from { transform: translateX(100%); }
  to   { transform: none; }
}

/* Header */
.pp-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.pp-header-tipo {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-tertiary);
}
.pp-btn-icon {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  border: none; background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: all 80ms;
}
.pp-btn-icon:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Body */
.pp-body {
  flex: 1; overflow-y: auto;
  padding: 16px;
  display: flex; flex-direction: column; gap: 16px;
}

/* Título */
.pp-titulo {
  width: 100%; border: none; background: transparent;
  font-size: 18px; font-weight: 600; color: var(--text-primary);
  font-family: var(--font-sans); outline: none;
  height: 32px; padding: 0;
}
.pp-titulo::placeholder { color: var(--text-tertiary); }

/* Campos */
.pp-fields { display: flex; flex-direction: column; gap: 8px; }
.pp-field-row {
  display: flex; align-items: center; gap: 8px;
  min-height: 32px;
}
.pp-field-label {
  width: 100px; flex-shrink: 0;
  font-size: 12px; color: var(--text-tertiary); font-weight: 500;
}
.pp-input {
  height: 28px; padding: 0 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: var(--bg-card-hover);
  color: var(--text-primary); font-size: 12px; font-family: var(--font-sans);
}
.pp-input:focus { outline: none; border-color: var(--accent); }

/* Chips (estado, prioridad) */
.pp-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.pp-chip {
  padding: 3px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-default); background: transparent;
  color: var(--text-secondary); font-size: 11px; font-weight: 500;
  cursor: pointer; transition: all 80ms; font-family: var(--font-sans);
}
.pp-chip:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.pp-chip.active { background: var(--accent-muted); border-color: var(--accent-border); color: var(--accent); }

.pp-dot {
  width: 6px; height: 6px; border-radius: 50%; display: inline-block;
  margin-right: 4px;
}

/* Color dots */
.pp-color-dot {
  width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid transparent; cursor: pointer;
  transition: all 80ms;
}
.pp-color-dot:hover { transform: scale(1.15); }
.pp-color-dot.active { border-color: var(--text-primary); box-shadow: 0 0 0 2px var(--bg-card); }

/* Secciones */
.pp-section { display: flex; flex-direction: column; gap: 8px; }
.pp-section-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-tertiary);
}
.pp-empty { font-size: 12px; color: var(--text-tertiary); font-style: italic; }

/* Tareas vinculadas */
.pp-tarea-link {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 0; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; border-radius: var(--radius-sm);
  transition: background 80ms;
}
.pp-tarea-link:hover { background: var(--bg-row-hover); }
.pp-tarea-done { text-decoration: line-through; color: var(--text-tertiary); }

/* Sub-panel tarea embebido */
.pp-subtarea-wrap {
  flex: 1; overflow-y: auto;
}
.pp-subtarea-wrap :deep(.tarea-panel) {
  width: 100%; min-width: 100%;
  border-left: none; height: 100%;
}

/* Auditoría */
.pp-audit {
  display: flex; flex-direction: column; gap: 2px;
  font-size: 11px; color: var(--text-tertiary);
  padding-top: 8px; border-top: 1px solid var(--border-subtle);
}

/* Footer (modo crear) */
.pp-footer {
  display: flex; gap: 8px; justify-content: flex-end;
  padding: 12px 16px; border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.pp-btn-cancel {
  height: 32px; padding: 0 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans);
}
.pp-btn-cancel:hover { background: var(--bg-card-hover); }
.pp-btn-crear {
  height: 32px; padding: 0 16px; border-radius: var(--radius-md);
  border: none; background: #fff; color: #111;
  font-size: 12px; font-weight: 600; cursor: pointer;
  font-family: var(--font-sans);
}
.pp-btn-crear:disabled { opacity: 0.4; cursor: default; }
.pp-btn-crear:hover:not(:disabled) { background: #e8e8e8; }

/* Handle arrastrable — solo visible en mobile */
.pp-handle-area {
  display: none;
}

@media (max-width: 768px) {
  .pp-overlay { align-items: flex-end; }
  .pp-panel {
    width: 100%; height: 88vh; max-height: 88vh;
    border-left: none; border-top: 1px solid var(--border-default);
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    animation: pp-slide-up 180ms ease-out;
    transition: height 320ms cubic-bezier(0.32,0.72,0,1), border-radius 320ms ease,
                max-height 320ms cubic-bezier(0.32,0.72,0,1);
  }
  .pp-panel.pp-panel-full {
    height: 100dvh; max-height: 100dvh; border-radius: 0;
  }
  @keyframes pp-slide-up {
    from { transform: translateY(100%); }
    to   { transform: none; }
  }
  .pp-handle-area {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px 6px;
    position: relative;
    flex-shrink: 0;
    cursor: grab;
    user-select: none;
    -webkit-user-select: none;
  }
  .pp-handle {
    width: 36px; height: 4px; border-radius: 2px;
    background: var(--border-default);
  }
  .pp-handle-close {
    position: absolute; right: 12px; top: 50%;
    transform: translateY(-50%);
    background: none; border: none;
    color: var(--text-tertiary); cursor: pointer;
    display: flex; align-items: center;
    padding: 4px; border-radius: var(--radius-sm);
    transition: color 80ms;
  }
  .pp-handle-close:hover { color: var(--text-primary); }
  .pp-field-label { width: 90px; }
  .pp-titulo { font-size: 16px; }
  .pp-chips { gap: 6px; }
  .pp-chip { padding: 4px 12px; font-size: 12px; }
  .pp-subtarea-wrap { flex: 1; min-height: 0; overflow-y: auto; }
  .pp-subtarea-wrap :deep(.tarea-panel) { display: flex !important; width: 100%; min-width: 0; height: auto; border-left: none; }
  .pp-tarea-link { padding: 6px 4px; }
}
</style>
