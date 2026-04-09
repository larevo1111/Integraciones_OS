<template>
  <div v-if="visible" class="crono-controls">
    <button
      class="crono-btn" :class="{ activo, loading }"
      :disabled="loading"
      @click="toggle"
      :title="activo ? 'Pausar contador' : 'Reanudar contador'"
    >
      <span class="material-icons" style="font-size:12px">{{ activo ? 'pause' : 'play_arrow' }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  tareaId:  { type: Number, required: true },
  tarea:    { type: Object, required: true }
})
const emit = defineEmits(['update'])

// Solo visible cuando la tarea está En Progreso
const visible = computed(() => props.tarea?.estado === 'En Progreso')
const activo  = computed(() => !!props.tarea?.crono_inicio)

// Guard contra doble-click: bloquea nuevos clicks mientras hay request en vuelo
// y durante al menos 500ms adicionales. Esto previene race conditions donde
// dos clicks rápidos podrían llamar al endpoint equivocado.
const loading = ref(false)
const LOCK_MIN_MS = 500

async function toggle() {
  if (loading.value) return
  loading.value = true
  const start = Date.now()
  try {
    const endpoint = activo.value ? 'pausar' : 'iniciar'
    const data = await api(`/api/gestion/tareas/${props.tareaId}/${endpoint}`, { method: 'POST' })
    if (data?.tarea) emit('update', data.tarea)
  } catch (e) { console.error(e) }
  finally {
    const elapsed = Date.now() - start
    if (elapsed < LOCK_MIN_MS) {
      await new Promise(r => setTimeout(r, LOCK_MIN_MS - elapsed))
    }
    loading.value = false
  }
}
</script>

<style scoped>
.crono-controls { display: flex; align-items: center; gap: 4px; }
.crono-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border: 1px solid var(--border-subtle);
  border-radius: 4px; background: transparent; cursor: pointer;
  color: var(--text-secondary); transition: all 80ms;
}
.crono-btn:hover:not(:disabled) { background: var(--bg-card-hover); }
.crono-btn.activo { border-color: var(--accent); color: var(--accent); }
.crono-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
