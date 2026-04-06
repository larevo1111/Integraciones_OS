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
import { calcTotalSeg } from 'src/services/crono'

const props = defineProps({
  tareaId:          { type: Number, required: true },
  tarea:            { type: Object, required: true }
})
const emit = defineEmits(['update', 'tick'])

const activo = ref(!!props.tarea?.crono_inicio)
let interval = null
let inicioLocal = null

// Calcula total usando la misma función que todos los demás componentes
function getTotal() {
  if (inicioLocal && activo.value) {
    // Post-play inmediato: usar timestamp local hasta que la prop se actualice
    const acum = props.tarea?.crono_acumulado_seg || 0
    return acum + Math.max(0, Math.floor((Date.now() - inicioLocal.getTime()) / 1000))
  }
  return calcTotalSeg(props.tarea)
}

const totalSegundos = ref(getTotal())
const totalMinutos  = computed(() => Math.floor(totalSegundos.value / 60))

function startInterval() {
  stopInterval()
  totalSegundos.value = getTotal()
  interval = setInterval(() => {
    totalSegundos.value = getTotal()
    emit('tick', totalSegundos.value)
  }, 1000)
}
function stopInterval() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => {
  totalSegundos.value = getTotal()
  if (activo.value) startInterval()
  emit('tick', totalSegundos.value)
})

watch(() => props.tarea?.crono_inicio, val => {
  activo.value = !!val
  if (val) inicioLocal = null  // prop actualizada, no necesito el local
  totalSegundos.value = getTotal()
  if (val) startInterval()
  else stopInterval()
})

onUnmounted(() => stopInterval())

async function iniciar() {
  try {
    const data = await api(`/api/gestion/tareas/${props.tareaId}/iniciar`, { method: 'POST' })
    inicioLocal = new Date()
    activo.value = true
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
    inicioLocal = null
    totalSegundos.value = data.tarea?.crono_acumulado_seg || getTotal()
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
    inicioLocal = null
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
.crono-controls { display: flex; align-items: center; gap: 4px; }
.crono-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent, #3b82f6); animation: pulse 1s infinite; flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .5; transform: scale(.7); }
}
.crono-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border: 1px solid var(--border-subtle);
  border-radius: 4px; background: transparent; cursor: pointer;
  color: var(--text-secondary); transition: all 80ms;
}
.crono-btn:hover { background: var(--bg-hover); }
.crono-btn.activo { border-color: var(--accent); color: var(--accent); }
.crono-btn-reset { color: var(--text-tertiary); }
.crono-btn-reset:hover { color: var(--text-secondary); }
</style>
