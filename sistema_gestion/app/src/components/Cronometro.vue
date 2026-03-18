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

// segundosAcumulados: acumulador LOCAL en segundos (no depende de la precisión en minutos del DB).
// Al pausar se suman los segundos del segmento actual ANTES de resetear.
// Al detener (stop completo) se resetea a 0.
// Al reanudar, segundos arranca desde 0 y segundosAcumulados ya tiene el historial.
const segundosAcumulados = ref((props.tiempoBase || 0) * 60)

// Cuando el padre actualiza tiempoBase (p.ej. al recargar), sincronizamos — pero solo
// si no estamos en medio de una operación local (skipNextSync) y el cronómetro está parado.
let skipNextSync = false
watch(() => props.tiempoBase, v => {
  if (skipNextSync) { skipNextSync = false; return }
  if (!activo.value) segundosAcumulados.value = (v || 0) * 60
})

function calcularSegundos() {
  if (!props.cronometroInicio) return 0
  return Math.floor((Date.now() - new Date(props.cronometroInicio).getTime()) / 1000)
}

const totalSegundos = computed(() => segundosAcumulados.value + segundos.value)

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
    segundos.value = 0   // nuevo segmento arranca desde 0; segundosAcumulados ya tiene historial
    startInterval()
    emit('update', 'iniciado')
  } catch (e) { console.error(e) }
}

// Pausa: guarda el segmento en DB y acumula localmente en segundos (no en minutos del DB).
async function pausar() {
  stopInterval()
  const segActual = segundos.value  // capturar ANTES de resetear
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    segundosAcumulados.value += segActual  // acumular localmente — no depende de data.tiempo_real_min
    skipNextSync = true  // el padre propagará el prop con valor viejo (en minutos) — ignorar
    activo.value   = false
    segundos.value = 0
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) {
    // Si falla el API, restaurar el intervalo para no perder el conteo
    segundos.value = segActual
    startInterval()
    console.error(e)
  }
}

// Detener completo: resetea todo (nueva tarea o trabajo terminado)
async function detener() {
  stopInterval()
  const segActual = segundos.value
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    segundosAcumulados.value = 0  // reset total al detener
    skipNextSync = true
    activo.value   = false
    segundos.value = 0
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) {
    segundos.value = segActual
    startInterval()
    console.error(e)
  }
}

defineExpose({ display, activo })
</script>
