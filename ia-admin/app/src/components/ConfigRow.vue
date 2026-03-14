<template>
  <div class="config-row" :class="{ editing: editando }">

    <!-- Columna: label + info -->
    <div class="col-label">
      <span class="label-text">{{ row?.label || row?.clave }}</span>
      <div class="info-wrap" v-if="row?.info">
        <button class="info-btn" @mouseenter="showTip = true" @mouseleave="showTip = false">?</button>
        <div v-if="showTip" class="tooltip">{{ row.info }}</div>
      </div>
    </div>

    <!-- Columna: clave técnica -->
    <div class="col-key mono">{{ row?.clave }}</div>

    <!-- Columna: valor -->
    <div class="col-valor">
      <template v-if="editando">
        <input
          ref="inputRef"
          v-model="valorEdit"
          class="valor-input"
          type="text"
          @keydown.enter="$emit('save', valorEdit)"
          @keydown.esc="$emit('cancel')"
        />
        <span class="unidad">{{ row?.unidad }}</span>
      </template>
      <template v-else>
        <span class="valor-display">{{ row?.valor }}</span>
        <span class="unidad">{{ row?.unidad }}</span>
      </template>
    </div>

    <!-- Columna: acciones -->
    <div class="col-actions">
      <template v-if="editando">
        <button class="btn-save" :disabled="guardando" @click="$emit('save', valorEdit)">
          {{ guardando ? '...' : 'Guardar' }}
        </button>
        <button class="btn-cancel" @click="$emit('cancel')">Cancelar</button>
      </template>
      <template v-else>
        <button class="btn-edit" @click="$emit('edit')">
          <PencilIcon :size="12" />
        </button>
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { PencilIcon } from 'lucide-vue-next'

const props = defineProps({
  row:       { type: Object, default: () => ({}) },
  editando:  { type: Boolean, default: false },
  guardando: { type: Boolean, default: false },
})
defineEmits(['edit', 'save', 'cancel'])

const showTip  = ref(false)
const valorEdit = ref('')
const inputRef  = ref(null)

watch(() => props.editando, async (val) => {
  if (val) {
    valorEdit.value = props.row?.valor ?? ''
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select()
  }
})
</script>

<style scoped>
.config-row {
  display: grid;
  grid-template-columns: 1fr 180px 160px 140px;
  align-items: center;
  padding: 10px 16px;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background 70ms;
}
.config-row:last-child { border-bottom: none; }
.config-row:hover, .config-row.editing { background: var(--bg-card-hover); }

/* Label */
.col-label { display: flex; align-items: center; gap: 6px; min-width: 0; }
.label-text { font-size: 13px; color: var(--text-primary); font-weight: 400; }

/* Info tooltip */
.info-wrap { position: relative; }
.info-btn {
  width: 16px; height: 16px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  font-size: 10px;
  font-weight: 600;
  cursor: default;
  display: flex; align-items: center; justify-content: center;
  padding: 0;
  line-height: 1;
}
.info-btn:hover { border-color: var(--accent); color: var(--accent); }
.tooltip {
  position: absolute;
  left: 24px;
  top: -4px;
  width: 280px;
  background: var(--bg-tooltip, #1a1a2e);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  z-index: 100;
  pointer-events: none;
}

/* Clave técnica */
.col-key { font-size: 11px; color: var(--text-tertiary); }
.mono { font-family: var(--font-mono, 'JetBrains Mono', monospace); }

/* Valor */
.col-valor { display: flex; align-items: center; gap: 6px; }
.valor-display { font-size: 14px; font-weight: 600; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.unidad { font-size: 11px; color: var(--text-tertiary); }
.valor-input {
  width: 80px;
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-input, var(--bg-page));
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  outline: none;
}

/* Acciones */
.col-actions { display: flex; align-items: center; gap: 6px; justify-content: flex-end; }
.btn-edit {
  width: 26px; height: 26px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0;
  transition: opacity 70ms, background 70ms;
}
.config-row:hover .btn-edit { opacity: 1; }
.btn-edit:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-default); }

.btn-save {
  padding: 4px 12px;
  font-size: 12px; font-weight: 500;
  background: var(--accent); color: white;
  border: none; border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn-save:disabled { opacity: 0.5; cursor: wait; }
.btn-cancel {
  padding: 4px 10px;
  font-size: 12px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
}
.btn-cancel:hover { border-color: var(--border-default); color: var(--text-primary); }
</style>
