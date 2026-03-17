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
        <span class="etiqueta-chip-remove" @click.stop="quitar(e.id)">×</span>
      </span>

      <!-- Botón agregar -->
      <button class="etiqueta-add-btn" @click.stop="abrirMenu">
        <span class="material-icons" style="font-size:14px">label_outline</span>
        <span v-if="!seleccionadas.length">Etiqueta</span>
      </button>
    </div>

    <!-- Dropdown -->
    <Teleport to="body">
      <div v-if="abierto" class="etiqueta-dropdown" :style="dropdownStyle" @click.stop>
        <div class="etiqueta-search-wrap">
          <span class="material-icons" style="font-size:14px">search</span>
          <input ref="searchRef" v-model="busqueda" class="etiqueta-search" placeholder="Buscar o crear..." @keydown.escape="cerrar" />
        </div>

        <div style="overflow-y:auto;max-height:200px">
          <div
            v-for="e in etiquetasFiltradas"
            :key="e.id"
            class="etiqueta-option"
            :class="{ selected: modelValue.includes(e.id) }"
            @click="toggle(e.id)"
          >
            <span v-if="e.color" class="etiqueta-dot" :style="{ background: e.color }"></span>
            <span v-else class="etiqueta-dot" style="background:var(--text-tertiary)"></span>
            <span class="etiqueta-option-nombre">{{ e.nombre }}</span>
            <span v-if="modelValue.includes(e.id)" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
          </div>

          <div v-if="!etiquetasFiltradas.length && busqueda" class="etiqueta-empty">
            Sin resultados
          </div>
        </div>

        <!-- Crear nueva -->
        <div v-if="busqueda && !coincidenciaExacta" class="etiqueta-crear" @click="crearEtiqueta">
          <span class="material-icons" style="font-size:14px">add</span>
          Crear etiqueta "{{ busqueda }}"
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },   // array de IDs
  etiquetas:  { type: Array, default: null }         // si se pasa, no carga de API
})
const emit = defineEmits(['update:modelValue', 'etiqueta-creada'])

const wrapRef    = ref(null)
const searchRef  = ref(null)
const abierto    = ref(false)
const busqueda   = ref('')
const lista      = ref([])
const dropdownStyle = ref({})

const etiquetasData = computed(() => props.etiquetas !== null ? props.etiquetas : lista.value)
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
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 200)}px`,
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
  await nextTick()
  searchRef.value?.focus()
}

function cerrar() { abierto.value = false; busqueda.value = '' }

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
    emit('etiqueta-creada', data.etiqueta)
    toggle(data.etiqueta.id)
    busqueda.value = ''
  } catch (e) { console.error(e) }
}

function onClickOutside(e) {
  if (!wrapRef.value?.contains(e.target)) cerrar()
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.etiquetas-selector { display: inline-flex; align-items: center; position: relative; }

.etiquetas-chips {
  display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
}

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

.etiqueta-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 200px;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.etiqueta-search-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.etiqueta-search {
  background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); flex: 1;
}
.etiqueta-option {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.etiqueta-option:hover, .etiqueta-option.selected { background: var(--bg-row-hover); color: var(--text-primary); }
.etiqueta-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.etiqueta-option-nombre { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.etiqueta-empty { padding: 8px 12px; font-size: 12px; color: var(--text-tertiary); font-style: italic; }
.etiqueta-crear {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; font-size: 13px; color: var(--accent);
  cursor: pointer; border-top: 1px solid var(--border-subtle);
  transition: background 60ms;
}
.etiqueta-crear:hover { background: var(--accent-muted); }
</style>
