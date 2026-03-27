<template>
  <Teleport to="body">
    <div class="jp-overlay" @click="$emit('cancelar')">
      <div class="jp-popover" :style="posStyle" @click.stop>
        <div class="jp-title">{{ titulo }}</div>
        <div class="jp-hora-wrap">
          <span class="material-icons" style="font-size:16px;color:var(--text-tertiary)">schedule</span>
          <input
            v-model="horaEditable"
            type="time"
            step="60"
            class="jp-hora-input"
          />
        </div>
        <div class="jp-actions">
          <button class="jp-btn jp-btn-cancel" @click="$emit('cancelar')">Cancelar</button>
          <button class="jp-btn jp-btn-confirm" @click="confirmar">Confirmar</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { hoyLocal } from 'src/services/fecha'

const props = defineProps({
  titulo: String,
  fecha: String,   // 'YYYY-MM-DD' — para construir el datetime completo
  anchorEl: Object
})

const emit = defineEmits(['confirmar', 'cancelar'])

const anchorRect = ref(null)
const horaEditable = ref('')

onMounted(() => {
  // Inicializar con la hora actual en formato HH:MM
  const ahora = new Date()
  horaEditable.value = ahora.toTimeString().slice(0, 5)

  if (props.anchorEl) {
    const el = props.anchorEl.$el || props.anchorEl
    anchorRect.value = el.getBoundingClientRect()
  }
})

function confirmar() {
  // Construir datetime completo combinando fecha del día + hora editada por el usuario
  const fecha = props.fecha || hoyLocal()
  const datetime = `${fecha}T${horaEditable.value}:00`
  emit('confirmar', new Date(datetime).toISOString())
}

const posStyle = computed(() => {
  if (!anchorRect.value) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
  const r = anchorRect.value
  return {
    position: 'fixed',
    top: `${r.bottom + 8}px`,
    right: `${window.innerWidth - r.right}px`
  }
})
</script>

<style scoped>
.jp-overlay {
  position: fixed; inset: 0;
  z-index: 9000;
}
.jp-popover {
  position: fixed;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 14px 16px;
  min-width: 210px;
  z-index: 9001;
}
.jp-title {
  font-size: 12px; font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.jp-hora-wrap {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 14px;
}
.jp-hora-input {
  font-size: 15px; font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border-default);
  padding: 2px 4px;
  width: 100px;
  cursor: pointer;
}
.jp-hora-input:focus {
  outline: none;
  border-bottom-color: var(--accent);
}
.jp-actions {
  display: flex; gap: 8px; justify-content: flex-end;
}
.jp-btn {
  padding: 5px 14px;
  border-radius: var(--radius-md);
  font-size: 12px; font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-default);
  transition: background 80ms;
}
.jp-btn-cancel {
  background: transparent;
  color: var(--text-secondary);
}
.jp-btn-cancel:hover { background: var(--bg-row-hover); }
.jp-btn-confirm {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.jp-btn-confirm:hover { background: var(--accent-hover); }
</style>
