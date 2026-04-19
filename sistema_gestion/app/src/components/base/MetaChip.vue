<template>
  <button
    type="button"
    :class="['meta-chip-base', { 'meta-chip-empty': !hasValue, 'meta-chip-filled': hasValue }]"
    :style="chipStyle"
  >
    <q-icon v-if="icon" :name="icon" size="14px" class="meta-chip-icon" />
    <span v-if="dotColor" class="meta-chip-dot" :style="{ background: dotColor }"></span>
    <span class="meta-chip-label">{{ displayLabel }}</span>
    <q-menu
      ref="menuRef"
      :anchor="menuAnchor"
      :self="menuSelf"
      :offset="[0, 6]"
      class="meta-chip-menu"
      @before-show="$emit('open')"
    >
      <slot :close="closeMenu" />
    </q-menu>
  </button>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'

const props = defineProps({
  icon:          { type: String, default: null },
  label:         { type: String, default: '' },
  value:         { type: [String, Number, Boolean, Object, Array], default: null },
  valueLabel:    { type: String, default: null },
  valueColor:    { type: String, default: null },
  valueBg:       { type: String, default: null },
  dotColor:      { type: String, default: null }
})

defineEmits(['open'])

const $q = useQuasar()
const menuRef = ref(null)

const hasValue = computed(() => {
  const v = props.value
  if (v === null || v === undefined || v === '') return false
  if (Array.isArray(v)) return v.length > 0
  return true
})

const displayLabel = computed(() => {
  if (hasValue.value) return props.valueLabel || props.label
  return props.label
})

const chipStyle = computed(() => {
  if (!hasValue.value) return {}
  const st = {}
  if (props.valueBg) st.background = props.valueBg
  if (props.valueColor) st.color = props.valueColor
  return st
})

const menuAnchor = computed(() => $q.screen.lt.md ? 'top middle' : 'bottom left')
const menuSelf   = computed(() => $q.screen.lt.md ? 'bottom middle' : 'top left')

function closeMenu() {
  menuRef.value?.hide()
}

defineExpose({ closeMenu })
</script>

<style scoped>
.meta-chip-base {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 26px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 80ms;
  font-family: var(--font-sans);
  outline: none;
  user-select: none;
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.meta-chip-base:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.meta-chip-empty {
  background: transparent;
  color: var(--text-tertiary);
  border: 1px solid var(--border-subtle);
}
.meta-chip-empty:hover {
  background: var(--bg-row-hover);
  color: var(--text-secondary);
  border-color: var(--border-default);
}
.meta-chip-filled {
  background: var(--bg-row-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  font-weight: 500;
}
.meta-chip-filled:hover {
  background: var(--bg-row-selected);
  border-color: var(--border-default);
}
.meta-chip-icon {
  opacity: 0.75;
  flex-shrink: 0;
}
.meta-chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.meta-chip-label {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
