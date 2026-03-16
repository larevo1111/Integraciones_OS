<template>
  <div class="cronometro-panel">
    <span class="material-icons" style="color:var(--text-tertiary);font-size:18px">timer</span>
    <span class="cronometro-tiempo" :class="{ corriendo: activo }">{{ display }}</span>
    <button v-if="!activo" class="btn btn-sm btn-secondary" @click="iniciar">
      <span class="material-icons" style="font-size:14px">play_arrow</span> Iniciar
    </button>
    <button v-else class="btn btn-sm btn-secondary" @click="detener">
      <span class="material-icons" style="font-size:14px">stop</span> Detener
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  tareaId:       { type: Number, required: true },
  tiempoBase:    { type: Number, default: 0 },     // tiempo_real_min ya acumulado
  cronometroActivo:  { type: Boolean, default: false },
  cronometroInicio:  { type: String, default: null }  // ISO datetime del inicio activo
})
const emit = defineEmits(['update'])

const activo    = ref(props.cronometroActivo)
const segundos  = ref(0)
let interval    = null

// Calcular segundos desde el inicio guardado en BD
function calcularSegundos() {
  if (!props.cronometroInicio) return 0
  const inicio = new Date(props.cronometroInicio)
  return Math.floor((Date.now() - inicio.getTime()) / 1000)
}

const totalSegundos = computed(() => {
  const base = (props.tiempoBase || 0) * 60
  return base + segundos.value
})

const display = computed(() => {
  const total = totalSegundos.value
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return h > 0
    ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
})

function startInterval() {
  stopInterval()
  interval = setInterval(() => { segundos.value++ }, 1000)
}
function stopInterval() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => {
  if (activo.value) {
    segundos.value = calcularSegundos()
    startInterval()
  }
})

watch(() => props.cronometroActivo, val => {
  activo.value = val
  if (val) { segundos.value = calcularSegundos(); startInterval() }
  else     { stopInterval() }
})

onUnmounted(() => stopInterval())

async function iniciar() {
  try {
    await api(`/api/gestion/tareas/${props.tareaId}/iniciar`, { method: 'POST' })
    activo.value   = true
    segundos.value = 0
    startInterval()
    emit('update', 'iniciado')
  } catch (e) { console.error(e) }
}

async function detener() {
  stopInterval()
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    activo.value = false
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) { console.error(e) }
}

defineExpose({ display, activo })
</script>
