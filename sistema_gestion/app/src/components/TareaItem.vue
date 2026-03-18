<template>
  <div
    class="tarea-item"
    :class="{ selected: seleccionada, completada: esCompletada, 'is-subtarea': !!tarea.parent_id }"
    @click="$emit('click', tarea)"
    @mouseenter="hover = true"
    @mouseleave="hover = false"
  >
    <EstadoBadge :estado="tarea.estado" @click="$emit('cambiar-estado', tarea)" />
    <div class="cat-dot" :style="{ background: tarea.categoria_color }" />

    <!-- Indicador subtareas expandibles (solo tareas padre) -->
    <button
      v-if="tarea.subtareas_total > 0 && !tarea.parent_id"
      class="subtareas-badge"
      :class="{ expandida: expandida }"
      @click.stop="$emit('toggle-subtareas', tarea)"
      :title="expandida ? 'Contraer subtareas' : 'Expandir subtareas'"
    >
      <span class="material-icons" style="font-size:10px">{{ expandida ? 'expand_more' : 'chevron_right' }}</span>
      {{ tarea.subtareas_completadas }}/{{ tarea.subtareas_total }}
    </button>

    <span class="tarea-titulo">{{ tarea.titulo }}</span>

    <div class="tarea-meta">
      <!-- Cronómetro activo -->
      <span v-if="tarea.cronometro_activo" class="cronometro-activo">
        <span class="cronometro-dot" />
        {{ tiempoCronometro }}
      </span>

      <PrioridadIcon :prioridad="tarea.prioridad" />

      <!-- Avatar responsable (solo si no es el usuario actual) -->
      <img
        v-if="tarea.responsable && tarea.responsable !== usuarioActual"
        :src="`https://ui-avatars.com/api/?name=${encodeURIComponent(tarea.responsable_nombre || tarea.responsable)}&size=16&background=1e1e1e&color=888&rounded=true`"
        class="avatar-mini"
        :title="tarea.responsable_nombre || tarea.responsable"
      />

      <!-- Duración real (si existe y no hay cronómetro activo) -->
      <span
        v-if="tarea.tiempo_real_min > 0 && !tarea.cronometro_activo"
        class="tarea-duracion"
        title="Tiempo real"
      >{{ duracionDisplay }}</span>

      <span class="tarea-fecha" :class="clasesFecha">{{ fechaDisplay }}</span>

      <!-- Botón + agregar subtarea (hover, solo tareas padre) -->
      <button
        v-if="hover && !tarea.parent_id && !esCompletada"
        class="btn-add-subtarea"
        title="Agregar subtarea"
        @click.stop="$emit('agregar-subtarea', tarea)"
      >+</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import EstadoBadge   from './EstadoBadge.vue'
import PrioridadIcon from './PrioridadIcon.vue'

const props = defineProps({
  tarea:         { type: Object, required: true },
  seleccionada:  { type: Boolean, default: false },
  usuarioActual: { type: String, default: '' },
  expandida:     { type: Boolean, default: false }
})
defineEmits(['click', 'cambiar-estado', 'agregar-subtarea', 'toggle-subtareas'])

const hover = ref(false)

const esCompletada = computed(() => ['Completada','Cancelada'].includes(props.tarea.estado))

function isoFecha(f) {
  if (!f) return null
  const s = typeof f === 'string' ? f : f.toISOString()
  return s.slice(0, 10)
}

const fechaDisplay = computed(() => {
  const iso = isoFecha(props.tarea.fecha_limite)
  if (!iso) return ''
  const d      = new Date(iso + 'T00:00:00')
  const hoy    = new Date(); hoy.setHours(0,0,0,0)
  const manana = new Date(hoy); manana.setDate(hoy.getDate()+1)
  const ayer   = new Date(hoy); ayer.setDate(hoy.getDate()-1)
  if (d.getTime() === hoy.getTime())    return 'Hoy'
  if (d.getTime() === manana.getTime()) return 'Mañ'
  if (d.getTime() === ayer.getTime())   return 'Ayer'
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
})

const clasesFecha = computed(() => {
  const iso = isoFecha(props.tarea.fecha_limite)
  if (!iso) return ''
  const d   = new Date(iso + 'T00:00:00')
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  if (d < hoy) return 'vencida'
  if (d.getTime() === hoy.getTime()) return 'hoy'
  return ''
})

// Duración real display (compacto: 1h30 / 45m)
const duracionDisplay = computed(() => {
  const min = props.tarea.tiempo_real_min || 0
  if (!min) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h}h${m}`
  if (h) return `${h}h`
  return `${m}m`
})

// Cronómetro en tiempo real
const tiempoCronometro = ref('00:00')
let interval = null

function calcularTiempo() {
  if (!props.tarea.cronometro_activo || !props.tarea.cronometro_inicio) return
  const base  = (props.tarea.tiempo_real_min || 0) * 60
  const extra = Math.floor((Date.now() - new Date(props.tarea.cronometro_inicio).getTime()) / 1000)
  const total = base + extra
  const m = Math.floor(total / 60)
  const s = total % 60
  tiempoCronometro.value = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

onMounted(() => {
  if (props.tarea.cronometro_activo) {
    calcularTiempo()
    interval = setInterval(calcularTiempo, 1000)
  }
})
onUnmounted(() => { if (interval) clearInterval(interval) })
</script>

<style scoped>
/* Indicador ▶ N/M de subtareas */
.subtareas-badge {
  display: inline-flex; align-items: center; gap: 1px;
  padding: 0 4px; height: 15px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: transparent;
  font-size: 9px; color: var(--text-tertiary);
  cursor: pointer; flex-shrink: 0;
  transition: border-color 80ms, color 80ms;
  white-space: nowrap;
}
.subtareas-badge:hover, .subtareas-badge.expandida {
  border-color: var(--accent);
  color: var(--accent);
}

/* Botón + agregar subtarea — solo visible en hover, derecha extrema */
.btn-add-subtarea {
  display: flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; flex-shrink: 0;
  background: transparent; border: none;
  font-size: 14px; color: var(--text-tertiary);
  cursor: pointer; line-height: 1;
  transition: color 80ms;
  margin-left: 2px;
}
.btn-add-subtarea:hover { color: var(--accent); }

/* Subtarea: indentación + fuente diferenciada */
.is-subtarea {
  padding-left: 28px !important;
}
.is-subtarea .tarea-titulo {
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
