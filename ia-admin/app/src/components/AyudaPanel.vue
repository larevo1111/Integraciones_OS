<template>
  <div class="ayuda-wrap">
    <button class="ayuda-toggle" @click="abierto = !abierto" :aria-expanded="abierto">
      <span class="ayuda-icon">?</span>
      <span class="ayuda-label">{{ abierto ? 'Cerrar ayuda' : 'Ayuda' }}</span>
      <ChevronDownIcon :size="13" :style="{ transform: abierto ? 'rotate(180deg)' : '', transition: 'transform 150ms' }" />
    </button>

    <transition name="ayuda-slide">
      <div v-if="abierto" class="ayuda-panel">
        <slot />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ChevronDownIcon } from 'lucide-vue-next'

const abierto = ref(false)
defineProps({ titulo: { type: String, default: 'Ayuda' } })
</script>

<style scoped>
.ayuda-wrap { margin-bottom: 20px; }

.ayuda-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  background: none; border: 1px solid var(--border-default);
  border-radius: var(--radius-md); padding: 5px 12px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  transition: border-color 120ms, color 120ms;
}
.ayuda-toggle:hover { border-color: var(--border-strong); color: var(--text-primary); }

.ayuda-icon {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--bg-surface); border: 1px solid var(--border-strong);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: var(--text-secondary);
  flex-shrink: 0;
}

.ayuda-panel {
  margin-top: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-left: 3px solid #5e6ad2;
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.65;
}

/* Slide animation */
.ayuda-slide-enter-active,
.ayuda-slide-leave-active { transition: all 180ms ease; overflow: hidden; }
.ayuda-slide-enter-from,
.ayuda-slide-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.ayuda-slide-enter-to,
.ayuda-slide-leave-from { opacity: 1; max-height: 800px; }
</style>
