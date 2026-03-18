<template>
  <div class="cat-selector" ref="wrapRef">
    <button class="cat-btn" @click.stop="toggle" :class="{ 'has-value': modelValue }">
      <span v-if="catSeleccionada" class="cat-dot" :style="{ background: catSeleccionada.color }"></span>
      <span class="cat-btn-label">{{ catSeleccionada?.nombre?.replace(/_/g,' ') || 'Sin categoría' }}</span>
      <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">expand_more</span>
    </button>

    <Teleport to="body">
      <div v-if="abierto" class="cat-dropdown" :style="dropdownStyle" @click.stop>
        <div class="cat-lista">
          <div
            v-for="c in categorias"
            :key="c.id"
            class="cat-option"
            :class="{ selected: modelValue === c.id }"
            @click="seleccionar(c.id)"
          >
            <span class="cat-dot" :style="{ background: c.color }"></span>
            <span class="cat-nombre">{{ c.nombre.replace(/_/g,' ') }}</span>
            <span v-if="modelValue === c.id" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  categorias: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const wrapRef       = ref(null)
const abierto       = ref(false)
const dropdownStyle = ref({})

const catSeleccionada = computed(() => props.categorias.find(c => c.id === props.modelValue) || null)

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceAbove = rect.top
  const spaceBelow = window.innerHeight - rect.bottom
  const goUp = spaceAbove > spaceBelow && spaceBelow < 260
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 180)}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top}px` }
      : { top: `${rect.bottom + 4}px` })
  }
}

function toggle() {
  if (abierto.value) { cerrar(); return }
  calcularPosicion()
  abierto.value = true
}

function cerrar() { abierto.value = false }

function seleccionar(id) {
  emit('update:modelValue', id)
  cerrar()
}

function onClickOutside(e) {
  if (!wrapRef.value?.contains(e.target)) cerrar()
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.cat-selector { position: relative; display: inline-block; flex: 1; }

.cat-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px; height: 26px; width: 100%;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; transition: border-color 80ms, background 80ms;
  white-space: nowrap;
}
.cat-btn:hover { border-color: var(--border-default); background: var(--bg-row-hover); }
.cat-btn.has-value { color: var(--text-primary); border-color: var(--border-default); }
.cat-btn-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; text-align: left; }

.cat-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}

.cat-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  max-height: 280px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.cat-lista {
  overflow-y: auto;
  flex: 1;
}
.cat-option {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.cat-option:hover, .cat-option.selected { background: var(--bg-row-hover); color: var(--text-primary); }
.cat-nombre { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
