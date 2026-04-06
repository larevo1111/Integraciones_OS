<template>
  <div class="crono-controls">
    <span v-if="activo" class="crono-dot" />
    <button class="crono-btn" :class="{ activo }" @click="toggle" :title="activo ? 'Pausar' : 'Iniciar / Reanudar'">
      <span class="material-icons" style="font-size:12px">{{ activo ? 'pause' : 'play_arrow' }}</span>
    </button>
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
  acumuladoSeg:     { type: Number, default: 0 },
  cronometroActivo: { type: Boolean, default: false },
  cronometroInicio: { type: String, default: null }
})
const emit = defineEmits(['update', 'tick'])

const activo = ref(props.cronometroActivo)
let interval = null

// Parsear fecha de BD (string Colombia) a Date
function parseInicio(str) {
  if (!str) return null
  if (str.includes('Z') || str.includes('+') || str.includes('-', 10)) return new Date(str)
  return new Date(str.replace(' ', 'T') + '-05:00')
}

// Calcula el total de segundos en cualquier momento
function calcTotal() {
  let total = props.acumuladoSeg || 0
  if (activo.value && props.cronometroInicio) {
    const ini = parseInicio(props.cronometroInicio)
    if (ini) total += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
  }
  return total
}

const totalSegundos = ref(calcTotal())
const totalMinutos  = computed(() => Math.floor(totalSegundos.value / 60))

function startInterval() {
  stopInterval()
  interval = setInterval(() => {
    totalSegundos.value = calcTotal()
    emit('tick', totalSegundos.value)
  }, 1000)
}
function stopInterval() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => {
  totalSegundos.value = calcTotal()
  if (activo.value) startInterval()
  emit('tick', totalSegundos.value)
})

watch(() => props.cronometroActivo, val => {
  activo.value = val
  totalSegundos.value = calcTotal()
  if (val) startInterval()
  else stopInterval()
})

watch(() => props.acumuladoSeg, () => {
  totalSegundos.value = calcTotal()
})

onUnmounted(() => stopInterval())

async function iniciar() {
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/iniciar`, { method: 'POST' })
    activo.value = true
    totalSegundos.value = calcTotal()
    startInterval()
    emit('update', 'iniciado', data.tarea)
  } catch (e) { console.error(e) }
}

async function toggle() {
  if (activo.value) await pausar()
  else await iniciar()
}

async function pausar() {
  stopInterval()
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    activo.value = false
    totalSegundos.value = data.tarea?.crono_acumulado_seg || calcTotal()
    emit('tick', totalSegundos.value)
    emit('update', 'detenido', data.tarea)
  } catch (e) {
    startInterval()
    console.error(e)
  }
}

async function reiniciar() {
  stopInterval()
  try {
    if (activo.value) {
      await api(`/api/gestion/tareas/${props.tareaId}/detener`, { method: 'POST' })
    }
    await api(`/api/gestion/tareas/${props.tareaId}/reiniciar-tiempo`, { method: 'POST' })
    activo.value = false
    totalSegundos.value = 0
    emit('tick', 0)
    emit('update', 'detenido', null)
  } catch (e) {
    if (activo.value) startInterval()
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
