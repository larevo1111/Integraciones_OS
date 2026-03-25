<template>
  <Teleport to="body">
    <div class="jp-overlay" @click="$emit('cancelar')">
      <div class="jp-popover" :style="posStyle" @click.stop>
        <div class="jp-title">{{ titulo }}</div>
        <div class="jp-hora">
          <span class="material-icons" style="font-size:18px;color:var(--text-tertiary)">schedule</span>
          {{ hora }}
        </div>
        <div class="jp-actions">
          <button class="jp-btn jp-btn-cancel" @click="$emit('cancelar')">Cancelar</button>
          <button class="jp-btn jp-btn-confirm" @click="$emit('confirmar')">Confirmar</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  titulo: String,
  hora: String,
  anchorEl: Object
})

defineEmits(['confirmar', 'cancelar'])

const anchorRect = ref(null)

onMounted(() => {
  if (props.anchorEl) {
    const el = props.anchorEl.$el || props.anchorEl
    anchorRect.value = el.getBoundingClientRect()
  }
})

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
  min-width: 200px;
  z-index: 9001;
}
.jp-title {
  font-size: 13px; font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}
.jp-hora {
  display: flex; align-items: center; gap: 6px;
  font-size: 20px; font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  margin-bottom: 14px;
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
