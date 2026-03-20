<template>
  <aside v-if="tarea" class="tarea-panel">
    <!-- Header -->
    <div class="tarea-panel-header">
      <!-- Breadcrumb para subtareas -->
      <div v-if="tarea.parent_id" class="subtarea-breadcrumb" @click="$emit('abrir-padre', tarea.parent_id)">
        <span class="material-icons" style="font-size:13px">arrow_back</span>
        <span>{{ padreNombre || 'Tarea padre' }}</span>
      </div>
      <div style="display:flex;align-items:flex-start;gap:8px">
        <EstadoBadge :estado="tarea.estado" @click="ciclarEstado" style="margin-top:2px;flex-shrink:0" />
        <textarea
          class="tarea-panel-titulo"
          :value="tarea.titulo"
          rows="1"
          @blur="e => e.target.value.trim() && e.target.value !== tarea.titulo && actualizar('titulo', e.target.value.trim())"
          @keydown.enter.prevent="e => { e.target.blur() }"
        />
        <button class="btn-icon" @click="$emit('cerrar')"><span class="material-icons" style="font-size:18px">close</span></button>
      </div>
    </div>

    <!-- Body -->
    <div class="tarea-panel-body">
      <!-- Campos -->
      <div class="field-row" style="align-items:flex-start;padding-top:4px">
        <span class="field-label" style="padding-top:2px">Estado</span>
        <div class="prioridad-chips">
          <button
            v-for="e in ESTADOS"
            :key="e.key"
            class="prioridad-chip"
            :class="{ active: tarea.estado === e.key }"
            :style="tarea.estado === e.key ? { background: e.color + '22', borderColor: e.color, color: e.color } : {}"
            @click="actualizar('estado', e.key)"
          >
            <span class="p-dot" :style="{ background: e.color }"></span>
            {{ e.label }}
          </button>
        </div>
      </div>
      <div class="field-row" style="align-items:flex-start;padding-top:4px">
        <span class="field-label" style="padding-top:2px">Prioridad</span>
        <div class="prioridad-chips">
          <button
            v-for="p in PRIORIDADES"
            :key="p.key"
            class="prioridad-chip"
            :class="{ active: tarea.prioridad === p.key }"
            :style="tarea.prioridad === p.key ? { background: p.color + '22', borderColor: p.color, color: p.color } : {}"
            @click="actualizar('prioridad', p.key)"
          >
            <span class="p-dot" :style="{ background: p.color }"></span>
            {{ p.key }}
          </button>
        </div>
      </div>
      <div class="field-row">
        <span class="field-label">Categoría</span>
        <CategoriaSelector
          :model-value="tarea.categoria_id"
          :categorias="categorias"
          @update:model-value="actualizar('categoria_id', $event)"
        />
      </div>
      <div class="field-row">
        <span class="field-label">Proyecto</span>
        <ProyectoSelector
          :model-value="tarea.proyecto_id"
          :proyectos="proyectos"
          @update:model-value="actualizar('proyecto_id', $event)"
          @proyecto-creado="p => $emit('proyecto-creado', p)"
        />
      </div>
      <div class="field-row" style="align-items:flex-start">
        <span class="field-label" style="padding-top:4px">Etiquetas</span>
        <EtiquetasSelector
          :model-value="(tarea.etiquetas||[]).map(e=>e.id)"
          :etiquetas="etiquetas"
          @update:model-value="actualizarEtiquetas"
          @etiqueta-creada="e => etiquetas.push(e)"
        />
      </div>
      <div class="field-row" style="align-items:flex-start">
        <span class="field-label" style="padding-top:4px">Responsable</span>
        <ResponsablesSelector
          :single="true"
          :model-value="tarea.responsable ? [tarea.responsable] : []"
          :usuarios="usuarios"
          @update:model-value="v => actualizar('responsable', v[0] || null)"
        />
      </div>
      <!-- Fecha estimada (campo principal) -->
      <div class="field-row">
        <span class="field-label">Fecha estimada</span>
        <input type="date" class="input-field" style="height:28px;font-size:12px"
          :value="tarea.fecha_limite ? String(tarea.fecha_limite).slice(0,10) : ''"
          @change="actualizarFechaEstimada($event.target.value)" />
      </div>

      <div v-if="esProduccion" class="field-row" style="align-items:flex-start">
        <span class="field-label" style="padding-top:8px">OP Effi</span>
        <div style="flex:1;min-width:0">
          <OpSelector :modelValue="tarea.id_op || ''" @update:modelValue="val => { actualizar('id_op', val); cargarDetalleOp(val) }" />
        </div>
      </div>

      <!-- Detalle OP expandido -->
      <div v-if="esProduccion && detalleOp" class="op-detail-card">
        <p class="op-detail-titulo">OP {{ detalleOp.id_orden }} — {{ detalleOp.articulos }}</p>
        <div class="op-detail-meta">
          <span class="op-detail-badge" :class="detalleOp.estado?.toLowerCase().replace(' ','-')">{{ detalleOp.estado }}</span>
          <span v-if="detalleOp.fecha_final" class="op-detail-fecha">Vence: {{ formatFechaOp(detalleOp.fecha_final) }}</span>
          <span v-if="detalleOp.nombre_encargado" class="op-detail-encargado">· {{ detalleOp.nombre_encargado }}</span>
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
            :tiempo-base="tarea.tiempo_real_min"
            :cronometro-activo="!!tarea.cronometro_activo"
            :cronometro-inicio="tarea.cronometro_inicio"
            @update="onCronometroUpdate"
            @tick="secs => segsVivo = secs"
          />
          <input type="number" class="input-field t-input" style="margin-left:4px"
            :value="Math.floor(segsVivo / 3600)"
            :disabled="!!tarea.cronometro_activo"
            min="0"
            @change="actualizarTiempoReal('h', $event.target.value)" />
          <span class="t-sep">h</span>
          <input type="number" class="input-field t-input"
            :value="Math.floor((segsVivo % 3600) / 60)"
            :disabled="!!tarea.cronometro_activo"
            min="0" max="59"
            @change="actualizarTiempoReal('m', $event.target.value)" />
          <span class="t-sep">m</span>
          <span v-if="tarea.cronometro_activo" class="crono-seg">:{{ String(segsVivo % 60).padStart(2, '0') }}s</span>
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

      <!-- Descripción -->
      <p class="input-label">Descripción</p>
      <textarea
        class="input-field"
        rows="5"
        :value="tarea.descripcion"
        placeholder="Agrega detalles, pasos a seguir..."
        @blur="actualizar('descripcion', $event.target.value)"
      />

      <!-- Notas -->
      <p class="input-label" style="margin-top:12px">Notas</p>
      <textarea
        class="input-field"
        rows="3"
        :value="tarea.notas"
        placeholder="Notas rápidas..."
        @blur="actualizar('notas', $event.target.value)"
      />

      <!-- Acordeón: más campos (al final) -->
      <div class="accordion-toggle" style="margin-top:12px" @click="mostrarFechas = !mostrarFechas">
        <span class="material-icons" style="font-size:13px">{{ mostrarFechas ? 'expand_more' : 'chevron_right' }}</span>
        <span style="font-size:10px;color:var(--text-tertiary)">Más campos</span>
      </div>
      <template v-if="mostrarFechas">
        <div class="field-row">
          <span class="field-label">Inicio estimado</span>
          <input type="date" class="input-field" style="height:28px;font-size:12px"
            :value="tarea.fecha_inicio_estimada ? String(tarea.fecha_inicio_estimada).slice(0,10) : ''"
            @change="actualizar('fecha_inicio_estimada', $event.target.value || null)" />
        </div>
        <div class="field-row" :class="{ 'field-row-disabled': !esCompletada }">
          <span class="field-label">Inicio real</span>
          <input type="date" class="input-field" style="height:28px;font-size:12px"
            :value="tarea.fecha_inicio_real ? String(tarea.fecha_inicio_real).slice(0,10) : ''"
            :disabled="!esCompletada"
            @change="actualizar('fecha_inicio_real', $event.target.value || null)" />
        </div>
        <div class="field-row" :class="{ 'field-row-disabled': !esCompletada }">
          <span class="field-label">Fin real</span>
          <input type="date" class="input-field" style="height:28px;font-size:12px"
            :value="tarea.fecha_fin_real ? String(tarea.fecha_fin_real).slice(0,10) : ''"
            :disabled="!esCompletada"
            @change="actualizar('fecha_fin_real', $event.target.value || null)" />
        </div>
      </template>
    </div>

    <!-- Footer -->
    <div class="tarea-panel-footer" style="flex-direction:column;gap:6px">
      <!-- Popover de tiempo (solo si no tiene tiempo real) -->
      <Transition name="popover">
        <div v-if="popoverTiempo" class="popover-tiempo">
          <span style="font-size:10px;color:var(--text-tertiary)">¿Cuánto te tomó?</span>
          <div style="display:flex;align-items:center;gap:4px;margin-top:4px">
            <input ref="popoverHRef" type="number" class="input-field" style="width:48px;height:26px;font-size:11px" v-model.number="tiempoFinalH" min="0" placeholder="0" />
            <span style="font-size:10px;color:var(--text-tertiary)">h</span>
            <input type="number" class="input-field" style="width:42px;height:26px;font-size:11px" v-model.number="tiempoFinalM" min="0" max="59" placeholder="0" />
            <span style="font-size:10px;color:var(--text-tertiary)">m</span>
            <button class="btn btn-ghost btn-sm" style="padding:0 6px" @click="popoverTiempo=false;completarSin()">Saltar</button>
            <button class="btn btn-accent btn-sm" style="padding:0 8px" @click="confirmarCompletar">✓</button>
          </div>
        </div>
      </Transition>
      <div style="display:flex;gap:6px;width:100%">
        <button class="btn btn-danger btn-sm" @click="$emit('eliminar', tarea)">Eliminar</button>
        <div style="flex:1" />
        <button class="btn btn-secondary btn-sm" @click="$emit('cerrar')">Cerrar</button>
        <button class="btn btn-accent btn-sm" @click="completar">✓ Completar</button>
      </div>
    </div>
  </aside>

  <!-- Toast deshacer -->
  <ToastUndo ref="toastRef" />
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { api } from 'src/services/api'
import EstadoBadge          from './EstadoBadge.vue'
import Cronometro           from './Cronometro.vue'
import ProyectoSelector     from './ProyectoSelector.vue'
import CategoriaSelector    from './CategoriaSelector.vue'
import EtiquetasSelector    from './EtiquetasSelector.vue'
import ResponsablesSelector from './ResponsablesSelector.vue'
import OpSelector           from './OpSelector.vue'
import ToastUndo            from './ToastUndo.vue'

const ESTADOS = [
  { key: 'Pendiente',   label: 'Pendiente',   color: '#6b7280' },
  { key: 'En Progreso', label: 'En Progreso', color: '#3b82f6' },
  { key: 'Completada',  label: 'Completada',  color: '#22c55e' },
  { key: 'Cancelada',   label: 'Cancelada',   color: '#ef4444' }
]

const PRIORIDADES = [
  { key: 'Urgente', color: '#ef4444' },
  { key: 'Alta',    color: '#f59e0b' },
  { key: 'Media',   color: '#6b7280' },
  { key: 'Baja',    color: '#374151' }
]

const props = defineProps({
  tarea:      { type: Object, default: null },
  usuarios:   { type: Array, default: () => [] },
  categorias: { type: Array, default: () => [] },
  proyectos:  { type: Array, default: () => [] },
  etiquetas:  { type: Array, default: () => [] }
})
const emit = defineEmits(['cerrar', 'eliminar', 'actualizada', 'proyecto-creado', 'abrir-padre'])

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

// Mostrar OP Effi solo si la categoría seleccionada es Producción
const esProduccion = computed(() => {
  if (!props.tarea?.categoria_id) return false
  const cat = props.categorias.find(c => c.id === props.tarea.categoria_id)
  return cat?.nombre?.toLowerCase().includes('produccion') || false
})

// Detalle OP
const detalleOp = ref(null)

async function cargarDetalleOp(idOp) {
  if (!idOp) { detalleOp.value = null; return }
  try {
    const data = await api(`/api/gestion/op/${encodeURIComponent(idOp)}`)
    detalleOp.value = data.op || null
  } catch { detalleOp.value = null }
}

function formatFechaOp(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
}

watch(() => props.tarea?.id_op, idOp => cargarDetalleOp(idOp), { immediate: true })

// Toast deshacer
const toastRef = ref(null)

const LABELS_CAMPO = {
  estado: 'Estado', prioridad: 'Prioridad', categoria_id: 'Categoría',
  proyecto_id: 'Proyecto', responsable: 'Responsable', fecha_limite: 'Fecha',
  id_op: 'OP Effi', descripcion: 'Descripción', notas: 'Notas',
  tiempo_estimado_min: 'T. estimado', tiempo_real_min: 'T. real'
}

// Cronómetro integrado en T. real (segsVivo en segundos para mostrar :ss en vivo)
const cronometroRef = ref(null)
const segsVivo      = ref((props.tarea?.tiempo_real_min || 0) * 60)

// Sincronizar segsVivo con props cuando no está corriendo
watch(() => props.tarea?.tiempo_real_min, v => {
  if (!props.tarea?.cronometro_activo) segsVivo.value = (v || 0) * 60
})

// Auto-start cuando estado cambia a "En Progreso"
watch(() => props.tarea?.estado, (nuevo, viejo) => {
  if (nuevo === 'En Progreso' && viejo !== 'En Progreso' && !props.tarea?.cronometro_activo) {
    cronometroRef.value?.iniciar()
  }
})

// Popover completar
const popoverTiempo   = ref(false)
const popoverHRef     = ref(null)
const tiempoFinalH    = ref(0)
const tiempoFinalM    = ref(0)

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

function ciclarEstado() {
  const ciclo = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  actualizar('estado', ciclo[props.tarea.estado] || 'Pendiente')
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

function onCronometroUpdate(evento, dato) {
  if (evento === 'detenido') {
    // dato = tiempo_real_min (número) — /detener ya guardó en DB
    emit('actualizada', { ...props.tarea, cronometro_activo: 0, tiempo_real_min: dato })
  } else {
    // dato = cronometro_inicio ISO string (para que TareaItem muestre bien el tiempo)
    emit('actualizada', { ...props.tarea, cronometro_activo: 1, cronometro_inicio: dato })
  }
}

function actualizarTiempoReal(parte, val) {
  const h = parte === 'h' ? parseInt(val)||0 : Math.floor((props.tarea.tiempo_real_min||0)/60)
  const m = parte === 'm' ? parseInt(val)||0 : (props.tarea.tiempo_real_min||0)%60
  actualizar('tiempo_real_min', h*60+m)
}

function completar() {
  const min = props.tarea.tiempo_real_min || 0
  if (min > 0) {
    // Ya tiene tiempo real → completar directo
    confirmarCompletar()
    return
  }
  tiempoFinalH.value = 0
  tiempoFinalM.value = 0
  popoverTiempo.value = true
  setTimeout(() => popoverHRef.value?.focus(), 50)
}

async function confirmarCompletar() {
  const totalMin = tiempoFinalH.value*60 + tiempoFinalM.value
  popoverTiempo.value = false
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/completar`, {
      method: 'POST',
      body: JSON.stringify({ tiempo_real_min: totalMin || undefined })
    })
    emit('actualizada', data.tarea)
  } catch(e) { console.error(e) }
}

async function completarSin() {
  popoverTiempo.value = false
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/completar`, { method: 'POST' })
    emit('actualizada', data.tarea)
  } catch(e) { console.error(e) }
}
</script>

<style scoped>
.subtarea-breadcrumb {
  display: flex; align-items: center; gap: 4px;
  padding: 2px 0 6px;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: color 80ms;
  user-select: none;
}
.subtarea-breadcrumb:hover { color: var(--accent); }

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

/* Popover completar */
.popover-tiempo {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 8px 10px;
  width: 100%;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.popover-enter-active, .popover-leave-active {
  transition: opacity 120ms, transform 120ms;
}
.popover-enter-from, .popover-leave-to {
  opacity: 0; transform: translateY(4px);
}
</style>
