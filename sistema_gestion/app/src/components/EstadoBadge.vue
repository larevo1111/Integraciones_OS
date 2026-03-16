<template>
  <div
    class="estado-circle"
    :class="estadoClass"
    :title="estado"
    @click.stop="$emit('click')"
  />
</template>

<script setup>
import { computed } from 'vue'
defineEmits(['click'])
const props = defineProps({ estado: { type: String, default: 'Pendiente' } })

const estadoClass = computed(() => {
  const e = (props.estado || '').toLowerCase().replace(' ', '-')
  if (e === 'en-progreso' || e === 'en_progreso') return 'en-progreso'
  if (e === 'completada')  return 'completada'
  if (e === 'cancelada')   return 'cancelada'
  return 'pendiente'
})
</script>
