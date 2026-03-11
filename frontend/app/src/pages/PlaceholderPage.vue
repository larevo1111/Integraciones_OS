<template>
  <div class="placeholder-page">
    <div class="placeholder-inner">
      <div class="placeholder-icon"><HammerIcon :size="28" /></div>
      <p>{{ titulo }}</p>
      <span>Esta vista está en construcción</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { HammerIcon } from 'lucide-vue-next'

const route = useRoute()
const titulo = computed(() => {
  const parts = route.path.split('/').filter(Boolean)
  return parts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' › ')
})
</script>

<style scoped>
.placeholder-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 60vh;
}
.placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-tertiary);
}
.placeholder-icon { opacity: 0.25; }
.placeholder-inner p    { font-size: 15px; color: var(--text-secondary); margin: 0; font-weight: 500; }
.placeholder-inner span { font-size: 13px; color: var(--text-tertiary); }
</style>
