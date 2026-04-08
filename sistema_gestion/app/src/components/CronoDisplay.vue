<template>
  <span v-if="visible" class="crono-display" :class="{ pausado: !tarea.crono_inicio }">
    <span v-if="tarea.crono_inicio" class="crono-display-dot" />
    {{ texto }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { formatHHMMSS, calcDuracionVivo } from 'src/services/crono'

const props = defineProps({
  tarea: { type: Object, required: true }
})

// Una sola regla: visible si NO es Pendiente
const visible = computed(() => props.tarea && props.tarea.estado !== 'Pendiente')

const segundos = ref(calcDuracionVivo(props.tarea))
const texto = computed(() => formatHHMMSS(segundos.value))

let interval = null

function actualizar() {
  segundos.value = calcDuracionVivo(props.tarea)
}

function start() {
  stop()
  actualizar()
  interval = setInterval(actualizar, 1000)
}
function stop() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => {
  actualizar()
  if (props.tarea?.estado === 'En Progreso' && props.tarea?.crono_inicio) start()
})

onUnmounted(stop)

watch(
  () => [props.tarea?.estado, props.tarea?.crono_inicio, props.tarea?.duracion_usuario_seg, props.tarea?.duracion_cronometro_seg],
  () => {
    actualizar()
    if (props.tarea?.estado === 'En Progreso' && props.tarea?.crono_inicio) start()
    else stop()
  }
)
</script>

<style scoped>
.crono-display {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; color: var(--accent);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.crono-display.pausado { color: var(--accent); opacity: 0.8; }
.crono-display-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  animation: crono-pulse 1s infinite;
  flex-shrink: 0;
}
@keyframes crono-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .5; transform: scale(.7); }
}
</style>
