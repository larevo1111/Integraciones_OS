<template>
  <aside v-if="tarea" class="tarea-panel">
    <!-- Header -->
    <div class="tarea-panel-header">
      <div style="display:flex;align-items:flex-start;gap:8px">
        <EstadoBadge :estado="tarea.estado" @click="ciclarEstado" style="margin-top:2px;flex-shrink:0" />
        <p class="tarea-panel-titulo">{{ tarea.titulo }}</p>
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
        <select class="input-field select-field" style="height:28px;font-size:12px" :value="tarea.categoria_id" @change="actualizar('categoria_id', Number($event.target.value))">
          <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre.replace(/_/g, ' ') }}</option>
        </select>
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
      <div class="field-row">
        <span class="field-label">Fecha</span>
        <input type="date" class="input-field" style="height:28px;font-size:12px" :value="tarea.fecha_limite" @change="actualizar('fecha_limite', $event.target.value)" />
      </div>
      <div v-if="tarea.es_produccion || tarea.id_op" class="field-row">
        <span class="field-label">OP Effi</span>
        <input class="input-field" style="height:28px;font-size:12px" :value="tarea.id_op" placeholder="Nro. OP" @blur="actualizarOP($event.target.value)" />
      </div>

      <div class="divider" />

      <!-- Cronómetro -->
      <Cronometro
        :tarea-id="tarea.id"
        :tiempo-base="tarea.tiempo_real_min"
        :cronometro-activo="!!tarea.cronometro_activo"
        :cronometro-inicio="tarea.cronometro_inicio"
        @update="onCronometroUpdate"
      />

      <!-- Tiempo estimado -->
      <div class="field-row" style="margin-top:8px">
        <span class="field-label">Estimado</span>
        <div style="display:flex;align-items:center;gap:6px">
          <input type="number" class="input-field" style="height:28px;width:60px;font-size:12px" :value="Math.floor((tarea.tiempo_estimado_min||0)/60)" min="0" @change="actualizarTiempoEst('h', $event.target.value)" /> h
          <input type="number" class="input-field" style="height:28px;width:50px;font-size:12px" :value="(tarea.tiempo_estimado_min||0)%60" min="0" max="59" @change="actualizarTiempoEst('m', $event.target.value)" /> min
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
    </div>

    <!-- Footer -->
    <div class="tarea-panel-footer">
      <button class="btn btn-danger btn-sm" @click="$emit('eliminar', tarea)">Eliminar</button>
      <div style="flex:1" />
      <button class="btn btn-secondary btn-sm" @click="$emit('cerrar')">Cerrar</button>
      <button class="btn btn-accent btn-sm" @click="completar">✓ Completar</button>
    </div>

    <!-- Modal completar (tiempo real) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="modalCompletar" class="modal-overlay" @click.self="modalCompletar=false">
          <div class="modal" style="max-width:360px">
            <div class="modal-header">
              <span class="modal-title">¿Cuánto tiempo te tomó?</span>
              <button class="btn-icon" @click="modalCompletar=false"><span class="material-icons">close</span></button>
            </div>
            <div class="modal-body">
              <p style="font-size:13px;color:var(--text-secondary);margin:0 0 16px">El cronómetro registró {{ tiempoRegistradoDisplay }}. Puedes ajustarlo:</p>
              <div style="display:flex;align-items:center;gap:8px">
                <input type="number" class="input-field" style="width:70px" v-model.number="tiempoFinalH" min="0" /> h
                <input type="number" class="input-field" style="width:60px" v-model.number="tiempoFinalM" min="0" max="59" /> min
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-ghost btn-sm" @click="completarSin">Saltar</button>
              <button class="btn btn-accent btn-sm" @click="confirmarCompletar">✓ Completar</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from 'src/services/api'
import EstadoBadge       from './EstadoBadge.vue'
import Cronometro        from './Cronometro.vue'
import ProyectoSelector  from './ProyectoSelector.vue'
import EtiquetasSelector    from './EtiquetasSelector.vue'
import ResponsablesSelector from './ResponsablesSelector.vue'

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
const emit = defineEmits(['cerrar', 'eliminar', 'actualizada', 'proyecto-creado'])

// Modal completar
const modalCompletar  = ref(false)
const tiempoFinalH    = ref(0)
const tiempoFinalM    = ref(0)

const tiempoRegistradoDisplay = computed(() => {
  const min = props.tarea?.tiempo_real_min || 0
  return `${Math.floor(min/60)}h ${min%60}min`
})

watch(() => props.tarea?.id, () => {
  // nada — refresca automáticamente
})

async function actualizar(campo, valor) {
  if (!props.tarea) return
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}`, {
      method: 'PUT',
      body: JSON.stringify({ [campo]: valor })
    })
    emit('actualizada', data.tarea)
  } catch (e) { console.error(e) }
}

function ciclarEstado() {
  const ciclo = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente', 'Cancelada': 'Pendiente' }
  actualizar('estado', ciclo[props.tarea.estado] || 'Pendiente')
}

async function actualizarOP(val) {
  if (val !== props.tarea.id_op) actualizar('id_op', val)
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

function onCronometroUpdate(evento, tiempoMin) {
  if (evento === 'detenido') actualizar('tiempo_real_min', tiempoMin)
  emit('actualizada', { ...props.tarea, cronometro_activo: evento === 'iniciado' ? 1 : 0 })
}

function completar() {
  const min = props.tarea.tiempo_real_min || 0
  tiempoFinalH.value = Math.floor(min/60)
  tiempoFinalM.value = min % 60
  modalCompletar.value = true
}

async function confirmarCompletar() {
  const totalMin = tiempoFinalH.value*60 + tiempoFinalM.value
  modalCompletar.value = false
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/completar`, {
      method: 'POST',
      body: JSON.stringify({ tiempo_real_min: totalMin })
    })
    emit('actualizada', data.tarea)
  } catch(e) { console.error(e) }
}

async function completarSin() {
  modalCompletar.value = false
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/completar`, { method: 'POST' })
    emit('actualizada', data.tarea)
  } catch(e) { console.error(e) }
}
</script>

<style scoped>
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
</style>
