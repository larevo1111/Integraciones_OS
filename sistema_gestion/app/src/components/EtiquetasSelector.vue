<template>
  <div class="etiquetas-selector" ref="wrapRef">
    <!-- Chips seleccionadas -->
    <div class="etiquetas-chips">
      <span
        v-for="e in seleccionadas"
        :key="e.id"
        class="etiqueta-chip"
        :style="e.color ? { background: e.color + '22', borderColor: e.color + '66', color: e.color } : {}"
      >
        {{ e.nombre }}
        <span class="etiqueta-chip-remove" @click.stop="quitar(e.id)">&times;</span>
      </span>

      <!-- Botón agregar -->
      <button class="etiqueta-add-btn" @click.stop="abrirMenu">
        <span class="material-icons" style="font-size:14px">label_outline</span>
        <span v-if="!seleccionadas.length">Etiqueta</span>
      </button>
    </div>

    <!-- Dropdown -->
    <Teleport to="body">
      <div v-if="abierto" class="etq-dropdown" :style="dropdownStyle" @click.stop>
        <!-- Buscar -->
        <div class="etq-search-wrap">
          <span class="material-icons" style="font-size:14px">search</span>
          <input ref="searchRef" v-model="busqueda" class="etq-search" placeholder="Buscar o crear..." @keydown.escape="cerrar" />
        </div>

        <!-- Lista -->
        <div class="etq-lista">
          <div
            v-for="e in etiquetasFiltradas"
            :key="e.id"
            class="etq-row"
            :class="{ 'etq-row-selected': modelValue.includes(e.id) }"
          >
            <!-- Zona clickeable: selección -->
            <div class="etq-select-zone" @click="toggle(e.id)">
              <span v-if="modelValue.includes(e.id)" class="material-icons etq-check">check_circle</span>
              <span v-else class="material-icons etq-check-empty">radio_button_unchecked</span>
              <span class="etq-dot" :style="{ background: e.color || 'var(--text-tertiary)' }"></span>
              <span class="etq-nombre">{{ e.nombre }}</span>
            </div>
            <!-- Botón ⋮ separado — NO afecta selección -->
            <button class="etq-menu-btn" @click.stop="abrirEdicion(e)">
              <span class="material-icons" style="font-size:15px">more_vert</span>
            </button>
          </div>

          <div v-if="!etiquetasFiltradas.length && busqueda" class="etq-empty">Sin resultados</div>
        </div>

        <!-- Panel edición (reemplaza la lista cuando está activo) -->
        <div v-if="editando" class="etq-edit-panel">
          <div class="etq-edit-header">
            <button class="etq-edit-icon" @click="cancelarEdicion" title="Volver">
              <span class="material-icons" style="font-size:16px">close</span>
            </button>
            <form class="etq-edit-form" @submit.prevent="confirmarRename">
              <input
                ref="editInputRef"
                v-model="editandoNombre"
                class="etq-edit-input"
                placeholder="Nombre..."
              />
            </form>
            <button class="etq-edit-icon etq-icon-save" @click="confirmarRename" title="Guardar">
              <span class="material-icons" style="font-size:16px">check</span>
            </button>
            <button class="etq-edit-icon etq-icon-delete" @click="eliminarEtiqueta" title="Eliminar">
              <span class="material-icons" style="font-size:16px">delete_outline</span>
            </button>
          </div>
        </div>

        <!-- Crear nueva -->
        <div v-if="busqueda && !coincidenciaExacta && !editando" class="etq-crear" @click="crearEtiqueta">
          <span class="material-icons" style="font-size:14px">add</span>
          Crear "{{ busqueda }}"
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  etiquetas:  { type: Array, default: null }
})
const emit = defineEmits(['update:modelValue', 'etiqueta-creada', 'etiqueta-actualizada', 'etiqueta-eliminada'])

const wrapRef       = ref(null)
const searchRef     = ref(null)
const editInputRef  = ref(null)
const abierto       = ref(false)
const busqueda      = ref('')
const lista         = ref([])
const dropdownStyle = ref({})

// Edición
const editando       = ref(null)  // objeto etiqueta o null
const editandoNombre = ref('')

const extras = ref([])  // etiquetas creadas localmente (cuando se pasa prop)
const etiquetasData = computed(() => {
  const base = props.etiquetas !== null ? props.etiquetas : lista.value
  if (!extras.value.length) return base
  const ids = new Set(base.map(e => e.id))
  return [...base, ...extras.value.filter(e => !ids.has(e.id))]
})
const seleccionadas = computed(() => etiquetasData.value.filter(e => props.modelValue.includes(e.id)))
const etiquetasFiltradas = computed(() => {
  if (!busqueda.value) return etiquetasData.value
  return etiquetasData.value.filter(e => e.nombre.toLowerCase().includes(busqueda.value.toLowerCase()))
})
const coincidenciaExacta = computed(() =>
  etiquetasData.value.some(e => e.nombre.toLowerCase() === busqueda.value.toLowerCase())
)

async function cargarEtiquetas() {
  if (props.etiquetas !== null) return
  try {
    const data = await api('/api/gestion/etiquetas')
    lista.value = data.etiquetas || []
  } catch {}
}

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const goUp = (window.innerHeight - rect.bottom) < 220 && rect.top > 220
  const ddWidth = Math.min(Math.max(rect.width, 220), 280)
  const leftPos = Math.max(8, Math.min(rect.left, window.innerWidth - ddWidth - 8))
  dropdownStyle.value = {
    position: 'fixed',
    left: `${leftPos}px`,
    width: `${ddWidth}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top}px` }
      : { top: `${rect.bottom + 4}px` })
  }
}

async function abrirMenu() {
  if (lista.value.length === 0 && props.etiquetas === null) await cargarEtiquetas()
  calcularPosicion()
  abierto.value = true
  busqueda.value = ''
  editando.value = null
  await nextTick()
  searchRef.value?.focus()
}

function cerrar() {
  abierto.value = false
  busqueda.value = ''
  editando.value = null
}

function toggle(id) {
  const nueva = props.modelValue.includes(id)
    ? props.modelValue.filter(x => x !== id)
    : [...props.modelValue, id]
  emit('update:modelValue', nueva)
}

function quitar(id) {
  emit('update:modelValue', props.modelValue.filter(x => x !== id))
}

async function crearEtiqueta() {
  if (!busqueda.value.trim()) return
  try {
    const data = await api('/api/gestion/etiquetas', {
      method: 'POST',
      body: JSON.stringify({ nombre: busqueda.value.trim() })
    })
    if (props.etiquetas === null) lista.value.push(data.etiqueta)
    else extras.value.push(data.etiqueta)
    emit('etiqueta-creada', data.etiqueta)
    // Auto-seleccionar la nueva
    emit('update:modelValue', [...props.modelValue, data.etiqueta.id])
    busqueda.value = ''
  } catch (e) { console.error(e) }
}

// ─── Edición ───
async function abrirEdicion(e) {
  editando.value = e
  editandoNombre.value = e.nombre
  await nextTick()
  editInputRef.value?.focus()
  editInputRef.value?.select()
}

function cancelarEdicion() {
  editando.value = null
  editandoNombre.value = ''
}

async function confirmarRename() {
  const nombre = editandoNombre.value.trim()
  if (!nombre || !editando.value || nombre === editando.value.nombre) { cancelarEdicion(); return }
  try {
    const data = await api(`/api/gestion/etiquetas/${editando.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ nombre })
    })
    if (props.etiquetas === null) {
      const idx = lista.value.findIndex(x => x.id === editando.value.id)
      if (idx !== -1) lista.value[idx] = { ...lista.value[idx], nombre }
    }
    emit('etiqueta-actualizada', data.etiqueta)
    cancelarEdicion()
  } catch (err) { console.error(err) }
}

async function eliminarEtiqueta() {
  if (!editando.value) return
  const id = editando.value.id
  try {
    await api(`/api/gestion/etiquetas/${id}`, { method: 'DELETE' })
    if (props.etiquetas === null) {
      lista.value = lista.value.filter(x => x.id !== id)
    }
    if (props.modelValue.includes(id)) {
      emit('update:modelValue', props.modelValue.filter(x => x !== id))
    }
    emit('etiqueta-eliminada', id)
    cancelarEdicion()
  } catch (err) { console.error(err) }
}

function onClickOutside(ev) {
  if (abierto.value && !wrapRef.value?.contains(ev.target) && !ev.target.closest('.etq-dropdown')) {
    cerrar()
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.etiquetas-selector { display: inline-flex; align-items: center; position: relative; }

.etiquetas-chips { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }

.etiqueta-chip {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 6px; height: 20px;
  background: var(--bg-row-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  font-size: 11px; color: var(--text-secondary);
  white-space: nowrap;
}
.etiqueta-chip-remove {
  cursor: pointer; font-size: 14px; line-height: 1;
  opacity: 0.6; margin-left: 1px;
  transition: opacity 80ms;
}
.etiqueta-chip-remove:hover { opacity: 1; }

.etiqueta-add-btn {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 6px; height: 24px;
  background: transparent; border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-tertiary);
  cursor: pointer; transition: border-color 80ms, color 80ms;
}
.etiqueta-add-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ─── Dropdown ─── */
.etq-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 200px;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.etq-search-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.etq-search {
  background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); flex: 1;
  font-family: var(--font-sans);
}

/* ─── Lista ─── */
.etq-lista { overflow-y: auto; max-height: 200px; }

.etq-row {
  display: flex; align-items: center;
  padding: 0 4px 0 0;
  transition: background 60ms;
}
.etq-row:hover { background: var(--bg-row-hover); }
.etq-row-selected { background: var(--bg-row-hover); }

.etq-select-zone {
  display: flex; align-items: center; gap: 8px;
  flex: 1; min-width: 0;
  padding: 7px 4px 7px 12px;
  cursor: pointer;
}
.etq-check { font-size: 15px; color: var(--accent); flex-shrink: 0; }
.etq-check-empty { font-size: 15px; color: var(--border-default); flex-shrink: 0; }
.etq-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.etq-nombre { flex: 1; font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.etq-row-selected .etq-nombre { color: var(--text-primary); }

.etq-menu-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; flex-shrink: 0;
  background: transparent; border: none; cursor: pointer;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  transition: background 60ms, color 60ms;
}
.etq-menu-btn:hover { background: var(--bg-surface, var(--bg-row-hover)); color: var(--text-primary); }

.etq-empty { padding: 8px 12px; font-size: 12px; color: var(--text-tertiary); font-style: italic; }

/* ─── Panel edición (fila compacta) ─── */
.etq-edit-panel { border-top: 1px solid var(--border-subtle); }
.etq-edit-header {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 6px;
}
.etq-edit-form { flex: 1; min-width: 0; }
.etq-edit-input {
  width: 100%; padding: 4px 8px; font-size: 12px;
  background: var(--bg-surface, var(--bg-row-hover));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary); outline: none;
  font-family: var(--font-sans);
}
.etq-edit-input:focus { border-color: var(--accent); }
.etq-edit-icon {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; flex-shrink: 0;
  border: none; background: transparent; cursor: pointer;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary); transition: background 60ms, color 60ms;
}
.etq-edit-icon:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.etq-icon-save { color: var(--accent); }
.etq-icon-save:hover { background: var(--accent-muted); }
.etq-icon-delete:hover { color: #ef4444; background: rgba(239,68,68,0.1); }

/* ─── Crear ─── */
.etq-crear {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; font-size: 13px; color: var(--accent);
  cursor: pointer; border-top: 1px solid var(--border-subtle);
  transition: background 60ms;
}
.etq-crear:hover { background: var(--accent-muted); }
</style>
