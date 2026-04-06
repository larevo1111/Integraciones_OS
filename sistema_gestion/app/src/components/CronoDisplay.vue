<template>
  <span v-if="visible" class="crono-display" :class="{ pausado: !tarea.crono_inicio }">
    <span v-if="tarea.crono_inicio" class="crono-display-dot" />
    {{ texto }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { calcTotalSeg, formatCrono } from 'src/services/crono'

const props = defineProps({
  tarea: { type: Object, required: true }
})

const visible = computed(() => props.tarea.crono_inicio || (props.tarea.crono_acumulado_seg > 0))

const texto = ref(formatCrono(calcTotalSeg(props.tarea)))
let interval = null

function actualizar() {
  texto.value = formatCrono(calcTotalSeg(props.tarea))
}

function start() {
  stop()
  actualizar()
  interval = setInterval(actualizar, 1000)
}
function stop() {
  if (interval) { clearInterval(interval); interval = null }
}

onMounted(() => { if (props.tarea.crono_inicio) start(); else actualizar() })
onUnmounted(() => stop())

watch(() => props.tarea.crono_inicio, val => {
  if (val) start()
  else { stop(); actualizar() }
})
watch(() => props.tarea.crono_acumulado_seg, () => actualizar())
</script>

<style scoped>
.crono-display {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; color: var(--accent);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.crono-display.pausado { color: var(--accent); opacity: 0.7; }
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
