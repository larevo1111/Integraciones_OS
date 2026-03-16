<template>
  <div
    class="tarea-item"
    :class="{ selected: seleccionada, completada: esCompletada }"
    @click="$emit('click', tarea)"
  >
    <EstadoBadge :estado="tarea.estado" @click="$emit('cambiar-estado', tarea)" />
    <div class="cat-dot" :style="{ background: tarea.categoria_color }" />
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
        :src="`https://ui-avatars.com/api/?name=${encodeURIComponent(tarea.responsable)}&size=20&background=1e1e1e&color=888&rounded=true`"
        class="avatar-mini"
        :title="tarea.responsable"
      />

      <span class="tarea-fecha" :class="clasesFecha">{{ fechaDisplay }}</span>
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
  usuarioActual: { type: String, default: '' }
})
defineEmits(['click', 'cambiar-estado'])

const esCompletada = computed(() => ['Completada','Cancelada'].includes(props.tarea.estado))

// Fecha display
const fechaDisplay = computed(() => {
  const f = props.tarea.fecha_limite
  if (!f) return ''
  const d     = new Date(f + 'T00:00:00')
  const hoy   = new Date(); hoy.setHours(0,0,0,0)
  const manana = new Date(hoy); manana.setDate(hoy.getDate()+1)
  const ayer   = new Date(hoy); ayer.setDate(hoy.getDate()-1)
  if (d.getTime() === hoy.getTime())    return 'Hoy'
  if (d.getTime() === manana.getTime()) return 'Mañana'
  if (d.getTime() === ayer.getTime())   return 'Ayer'
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
})

const clasesFecha = computed(() => {
  const f = props.tarea.fecha_limite
  if (!f) return ''
  const d   = new Date(f + 'T00:00:00')
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  if (d < hoy) return 'vencida'
  if (d.getTime() === hoy.getTime()) return 'hoy'
  return ''
})

// Cronómetro en tiempo real para filas activas
const tiempoCronometro = ref('00:00')
let interval = null

function calcularTiempo() {
  if (!props.tarea.cronometro_activo || !props.tarea.cronometro_inicio) return
  const base = (props.tarea.tiempo_real_min || 0) * 60
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
