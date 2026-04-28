<template>
  <div class="sidebar-sub-section" @mouseenter="onHover" @mouseleave="onUnhover">
    <div ref="headerEl" class="sidebar-sub-header" @click="onHeaderClick">
      <q-icon :name="iconExpand" size="14px" />
      <span class="q-ml-xs" style="flex:1">{{ label }}</span>
      <span v-if="count" class="sidebar-count">{{ count }}</span>
      <q-btn v-if="addAccion" flat dense round size="xs" icon="add" class="sidebar-add-btn" @click.stop="$emit('add')" />
    </div>

    <q-menu
      v-if="popoverMode && headerEl"
      :target="headerEl"
      v-model="abiertoPopover"
      no-parent-event
      anchor="center right" self="center left"
      :offset="[8, 0]"
      class="sidebar-popover"
      @mouseenter="onHover"
      @mouseleave="onUnhover"
    >
      <q-list dense class="sidebar-popover-list">
        <q-item-label v-if="label" header class="sidebar-popover-title">
          <span style="flex:1">{{ label }}</span>
          <q-btn v-if="addAccion" flat dense round size="xs" icon="add" @click.stop="$emit('add')" />
        </q-item-label>
        <slot />
      </q-list>
    </q-menu>

    <template v-if="!popoverMode && abierto">
      <slot />
    </template>
  </div>
</template>

<style scoped>
.sidebar-popover-list {
  background: var(--bg-sidebar);
  color: var(--text-primary);
  min-width: 240px;
  max-width: 340px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 4px 0;
}
.sidebar-popover-title {
  display: flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  padding: 6px 12px;
  letter-spacing: 0.4px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-subtle);
}
</style>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  label:       { type: String,  default: '' },
  count:       { type: Number,  default: 0 },
  abierto:     { type: Boolean, default: false },
  popoverMode: { type: Boolean, default: false },
  addAccion:   { type: Boolean, default: false }
})
const emit = defineEmits(['toggle', 'add'])

const iconExpand = computed(() =>
  props.popoverMode ? 'chevron_right' : (props.abierto ? 'expand_more' : 'chevron_right')
)

const headerEl = ref(null)
const abiertoPopover = ref(false)
let timer = null
function onHover() {
  if (!props.popoverMode) return
  clearTimeout(timer)
  abiertoPopover.value = true
}
function onUnhover() {
  if (!props.popoverMode) return
  timer = setTimeout(() => { abiertoPopover.value = false }, 180)
}
function onHeaderClick() {
  if (props.popoverMode) return
  emit('toggle')
}
</script>
