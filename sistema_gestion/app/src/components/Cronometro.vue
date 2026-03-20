<template>
  <div class="crono-controls">
    <!-- Dot pulsante cuando corre -->
    <span v-if="activo" class="crono-dot" />
    <!-- Toggle play/pause -->
    <button class="crono-btn" :class="{ activo }" @click="toggle" :title="activo ? 'Pausar' : 'Iniciar / Reanudar'">
      <span class="material-icons" style="font-size:12px">{{ activo ? 'pause' : 'play_arrow' }}</span>
    </button>
    <!-- Reiniciar conteo -->
    <button class="crono-btn crono-btn-reset" @click="reiniciar" title="Reiniciar conteo">
      <span class="material-icons" style="font-size:12px">restart_alt</span>
    </button>
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
const emit = defineEmits(['update', 'tick'])

const activo   = ref(props.cronometroActivo)
const segundos = ref(0)
let interval   = null

const segundosAcumulados = ref((props.tiempoBase || 0) * 60)
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
const totalMinutos  = computed(() => Math.floor(totalSegundos.value / 60))

function startInterval() {
  stopInterval()
  interval = setInterval(() => {
    segundos.value++
    emit('tick', totalSegundos.value)
  }, 1000)
}
function stopInterval() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => {
  if (activo.value) {
    segundos.value = calcularSegundos()
    startInterval()
  }
  emit('tick', totalSegundos.value)
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
    segundos.value = 0
    startInterval()
    emit('update', 'iniciado')
  } catch (e) { console.error(e) }
}

async function toggle() {
  if (activo.value) await pausar()
  else              await iniciar()
}

async function pausar() {
  stopInterval()
  const segActual = segundos.value
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    segundosAcumulados.value += segActual
    skipNextSync = true
    activo.value   = false
    segundos.value = 0
    emit('tick', totalSegundos.value)
    emit('update', 'detenido', data.tiempo_real_min)
  } catch (e) {
    segundos.value = segActual
    startInterval()
    console.error(e)
  }
}

async function reiniciar() {
  const estabaActivo = activo.value
  if (estabaActivo) stopInterval()
  try {
    if (estabaActivo) {
      await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    }
    await api(`/api/gestion/tareas/${props.tareaId}/reiniciar-tiempo`, { method: 'POST' })
    segundosAcumulados.value = 0
    segundos.value = 0
    skipNextSync = true
    activo.value = false
    emit('tick', 0)
  emit('update', 'detenido', 0)
  } catch (e) {
    if (estabaActivo) startInterval()
    console.error(e)
  }
}

defineExpose({ iniciar, totalMinutos })
</script>

<style scoped>
.crono-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}
.crono-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent, #3b82f6);
  animation: pulse 1s infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .5; transform: scale(.7); }
}
.crono-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 80ms;
}
.crono-btn:hover { background: var(--bg-hover); }
.crono-btn.activo { border-color: var(--accent); color: var(--accent); }
.crono-btn-reset { color: var(--text-tertiary); }
.crono-btn-reset:hover { color: var(--text-secondary); }
</style>
