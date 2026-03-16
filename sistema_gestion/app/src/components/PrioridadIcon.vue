<template>
  <span class="material-icons prioridad-icon" :class="clase" :title="prioridad" style="font-size:15px">
    {{ icono }}
  </span>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ prioridad: String })
const icono = computed(() => {
  const p = (props.prioridad || '').toLowerCase()
  if (p === 'urgente') return 'priority_high'
  if (p === 'alta')    return 'keyboard_double_arrow_up'
  if (p === 'media')   return 'remove'
  return 'keyboard_arrow_down'
})
const clase = computed(() => (props.prioridad || '').toLowerCase())
</script>
