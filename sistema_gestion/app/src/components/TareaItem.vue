<template>
  <div
    class="tarea-item"
    :class="{ selected: seleccionada, completada: esCompletada, 'is-subtarea': !!tarea.parent_id }"
    @click="$emit('click', tarea)"
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
      <!-- Cronómetro activo (corriendo en tiempo real) -->
      <span v-if="tarea.cronometro_activo" class="cronometro-activo">
        <span class="cronometro-dot" />
        {{ tiempoCronometro }}
      </span>

      <!-- Chip categoría: dot coloreado + nombre, fondo tinted -->
      <span
        v-if="tarea.categoria_nombre && !tarea.cronometro_activo"
        class="meta-chip"
        :style="{ background: hexAlpha(tarea.categoria_color, 0.12), color: tarea.categoria_color }"
        :title="tarea.categoria_nombre"
      >
        <span class="meta-chip-dot" :style="{ background: tarea.categoria_color }" />
        {{ catNombreCorto }}
      </span>

      <!-- Chip duración real -->
      <span
        v-if="tarea.tiempo_real_min > 0 && !tarea.cronometro_activo"
        class="meta-chip meta-chip-dur"
        title="Tiempo real"
      >{{ duracionDisplay }}</span>

      <!-- Chip fecha -->
      <span
        v-if="fechaDisplay"
        class="meta-chip meta-chip-fecha"
        :class="clasesFecha"
      >{{ fechaDisplay }}</span>

      <!-- Chip proyecto -->
      <span
        v-if="tarea.proyecto_nombre && !tarea.cronometro_activo"
        class="meta-chip"
        :style="{ background: hexAlpha(tarea.proyecto_color, 0.10), color: 'var(--text-tertiary)' }"
        :title="tarea.proyecto_nombre"
      >
        <span class="meta-chip-dot" :style="{ background: tarea.proyecto_color || '#888' }" />
        {{ proyNombreCorto }}
      </span>

      <!-- Botón agregar subtarea ↳ — solo para tareas padre, siempre visible (sutil) -->
      <button
        v-if="!tarea.parent_id && !esCompletada"
        class="btn-add-sub"
        title="Agregar subtarea"
        @click.stop="$emit('agregar-subtarea', tarea)"
      >
        <span class="material-icons" style="font-size:11px">subdirectory_arrow_right</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import EstadoBadge from './EstadoBadge.vue'

const props = defineProps({
  tarea:         { type: Object, required: true },
  seleccionada:  { type: Boolean, default: false },
  usuarioActual: { type: String, default: '' },
  expandida:     { type: Boolean, default: false }
})
defineEmits(['click', 'cambiar-estado', 'agregar-subtarea', 'toggle-subtareas'])

const esCompletada = computed(() => ['Completada','Cancelada'].includes(props.tarea.estado))

// Helper: hex color + alpha → rgba string
function hexAlpha(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(136,136,136,${alpha})`
  const r = parseInt(hex.slice(1,3), 16)
  const g = parseInt(hex.slice(3,5), 16)
  const b = parseInt(hex.slice(5,7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

// Nombres truncados para chips (CSS maneja el ellipsis, JS solo para extremos)
const catNombreCorto = computed(() => {
  const n = (props.tarea.categoria_nombre || '').replace(/_/g, ' ')
  return n.length > 14 ? n.slice(0, 13) + '…' : n
})
const proyNombreCorto = computed(() => {
  const n = props.tarea.proyecto_nombre || ''
  return n.length > 14 ? n.slice(0, 13) + '…' : n
})

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
  if (d.getTime() === manana.getTime()) return 'Mañana'
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

// Duración real display compacto
const duracionDisplay = computed(() => {
  const min = props.tarea.tiempo_real_min || 0
  if (!min) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
})

// Cronómetro en tiempo real (solo cuando cronometro_activo)
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

/* Botón agregar subtarea ↳ — siempre en DOM, visible sutil */
.btn-add-sub {
  display: flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; flex-shrink: 0;
  background: transparent; border: none;
  color: var(--text-tertiary); cursor: pointer;
  opacity: 0.3; transition: opacity 100ms, color 100ms;
  margin-left: 1px;
}
.tarea-item:hover .btn-add-sub { opacity: 0.7; }
.btn-add-sub:hover { color: var(--accent) !important; opacity: 1 !important; }

/* Subtarea: indentación + fuente diferenciada */
.is-subtarea { padding-left: 28px !important; }
.is-subtarea .tarea-titulo { font-size: 11px; color: var(--text-secondary); }
</style>
