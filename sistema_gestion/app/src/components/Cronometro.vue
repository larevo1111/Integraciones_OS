<template>
  <div class="crono-inline">
    <!-- Cuando corriendo: dot pulsante + botón pause + botón stop -->
    <template v-if="activo">
      <span class="crono-dot" />
      <button class="crono-btn activo" @click="pausar" title="Pausar (guarda segmento)">
        <span class="material-icons" style="font-size:12px">pause</span>
      </button>
      <button class="crono-btn crono-btn-stop" @click="detener" title="Detener">
        <span class="material-icons" style="font-size:11px">stop</span>
      </button>
    </template>
    <!-- Cuando parado: botón play -->
    <button v-else class="crono-btn" @click="iniciar" title="Iniciar">
      <span class="material-icons" style="font-size:12px">play_arrow</span>
    </button>
    <!-- Tiempo display -->
    <span class="crono-display" :class="{ corriendo: activo }">{{ display }}</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  tareaId:          { type: Number, required: true },
  tiempoBase:       { type: Number, default: 0 },
  cronometroActivo: { type: Boolean, default: false },
  cronometroInicio: { type: String, default: null }
})
const emit = defineEmits(['update'])

const activo   = ref(props.cronometroActivo)
const segundos = ref(0)
let interval   = null

// Tiempo acumulado LOCAL — se actualiza inmediatamente cuando el API de detener responde,
// sin esperar que el padre actualice el prop (evita el "reinicio" visual al reanudar).
const tiempoAcumulado = ref(props.tiempoBase || 0)
watch(() => props.tiempoBase, v => {
  // Solo sincronizar cuando el cronómetro NO está corriendo
  // (si corre, tiempoAcumulado ya es correcto y no debe pisarse)
  if (!activo.value) tiempoAcumulado.value = v || 0
})

function calcularSegundos() {
  if (!props.cronometroInicio) return 0
  return Math.floor((Date.now() - new Date(props.cronometroInicio).getTime()) / 1000)
}

const totalSegundos = computed(() => tiempoAcumulado.value * 60 + segundos.value)

const display = computed(() => {
  const total = totalSegundos.value
  if (!activo.value && total === 0) return '—'
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
  else     { stopInterval(); segundos.value = 0 }
})

onUnmounted(() => stopInterval())

async function iniciar() {
  try {
    await api(`/api/gestion/tareas/${props.tareaId}/iniciar`, { method: 'POST' })
    activo.value   = true
    segundos.value = 0   // nuevo segmento arranca desde 0, tiempoAcumulado ya tiene el historial
    startInterval()
    emit('update', 'iniciado')
  } catch (e) { console.error(e) }
}

// Pausa: guarda el segmento, puede reanudarse (tiempoAcumulado queda con el total)
async function pausar() {
  stopInterval()
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    tiempoAcumulado.value = data.tiempo_real_min || 0   // ← actualizar local ANTES de que el padre actualice el prop
    activo.value   = false
    segundos.value = 0
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) { console.error(e) }
}

// Stop: misma lógica que pausa — la diferencia semántica la maneja el usuario
async function detener() {
  stopInterval()
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    tiempoAcumulado.value = data.tiempo_real_min || 0
    activo.value   = false
    segundos.value = 0
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) { console.error(e) }
}

defineExpose({ display, activo })
</script>
