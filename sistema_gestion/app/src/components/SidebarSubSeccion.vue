<template>
  <div class="sidebar-sub-section">
    <div
      ref="headerEl"
      class="sidebar-sub-header"
      :class="{ 'sub-header-active': popoverMode && abiertoPopover }"
      @click="onHeaderClick"
    >
      <span class="sub-header-label" style="flex:1">{{ label }}</span>
      <span v-if="count" class="sidebar-count">{{ count }}</span>
      <q-btn v-if="addAccion" flat dense round size="xs" icon="add" class="sidebar-add-btn" @click.stop="$emit('add')" />
      <q-icon :name="iconExpand" size="14px" class="sub-header-chevron" />
    </div>

    <q-menu
      v-if="popoverMode && headerEl"
      :target="headerEl"
      v-model="abiertoPopover"
      no-parent-event
      anchor="top right" self="top left"
      :offset="[8, 0]"
      class="sidebar-popover"
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

function onHeaderClick() {
  if (props.popoverMode) {
    abiertoPopover.value = !abiertoPopover.value
    return
  }
  emit('toggle')
}
</script>

<style scoped>
.sidebar-sub-header {
  cursor: pointer;
  transition: background 80ms, color 80ms;
}
.sidebar-sub-header:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}
.sub-header-active {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}
.sub-header-label { color: inherit; }
.sub-header-chevron {
  color: var(--text-tertiary);
  margin-left: 4px;
  flex-shrink: 0;
}
.sub-header-active .sub-header-chevron { color: var(--accent); }
</style>

<style>
/* Popover floating estilo HubSpot/Linear (referencia: produccion/floating-submenu) */
.sidebar-popover {
  background: var(--bg-sidebar);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
}
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
  padding: 8px 12px 6px;
  letter-spacing: 0.4px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-subtle);
}
</style>
