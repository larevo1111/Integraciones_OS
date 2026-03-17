<template>
  <div class="proyecto-selector" ref="wrapRef">
    <button class="proyecto-btn" @click.stop="abrirMenu" :class="{ 'has-value': modelValue }">
      <span v-if="proyectoSeleccionado" class="proyecto-dot" :style="{ background: proyectoSeleccionado.color }"></span>
      <span class="proyecto-btn-label">{{ proyectoSeleccionado?.nombre || 'Sin proyecto' }}</span>
      <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">expand_more</span>
    </button>

    <Teleport to="body">
      <div v-if="abierto" class="proyecto-dropdown" :style="dropdownStyle" @click.stop>
        <!-- Buscar -->
        <div class="proyecto-search-wrap">
          <span class="material-icons" style="font-size:14px">search</span>
          <input ref="searchRef" v-model="busqueda" class="proyecto-search" placeholder="Buscar proyecto..." @keydown.escape="cerrar" />
        </div>

        <!-- Opción sin proyecto -->
        <div class="proyecto-option" :class="{ selected: !modelValue }" @click="seleccionar(null)">
          <span class="proyecto-dot" style="background:var(--border-default)"></span>
          <span>Sin proyecto</span>
          <span v-if="!modelValue" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
        </div>

        <!-- Proyectos filtrados -->
        <div
          v-for="p in proyectosFiltrados"
          :key="p.id"
          class="proyecto-option"
          :class="{ selected: modelValue === p.id }"
          @click="seleccionar(p.id)"
        >
          <span class="proyecto-dot" :style="{ background: p.color }"></span>
          <span class="proyecto-nombre">{{ p.nombre }}</span>
          <span v-if="modelValue === p.id" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
        </div>

        <!-- Sin resultados -->
        <div v-if="!proyectosFiltrados.length && busqueda" class="proyecto-empty">
          Sin resultados para "{{ busqueda }}"
        </div>

        <!-- Crear nuevo -->
        <div class="proyecto-crear" @click="abrirModalCrear">
          <span class="material-icons" style="font-size:14px">add</span>
          {{ busqueda && !coincidenciaExacta ? `Crear "${busqueda}"` : 'Nuevo proyecto' }}
        </div>
      </div>
    </Teleport>

    <!-- Modal crear proyecto -->
    <ProyectoModal
      v-model="mostrarModal"
      :proyecto-editar="null"
      @guardado="onProyectoCreado"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'
import ProyectoModal from './ProyectoModal.vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  proyectos:  { type: Array, default: null }  // si se pasa, no carga de API
})
const emit = defineEmits(['update:modelValue', 'proyecto-creado'])

const wrapRef      = ref(null)
const searchRef    = ref(null)
const abierto      = ref(false)
const busqueda     = ref('')
const lista        = ref([])
const mostrarModal = ref(false)
const dropdownStyle = ref({})

const proyectosData = computed(() => props.proyectos !== null ? props.proyectos : lista.value)
const proyectoSeleccionado = computed(() => proyectosData.value.find(p => p.id === props.modelValue) || null)
const proyectosFiltrados = computed(() => {
  if (!busqueda.value) return proyectosData.value
  return proyectosData.value.filter(p => p.nombre.toLowerCase().includes(busqueda.value.toLowerCase()))
})
const coincidenciaExacta = computed(() =>
  proyectosData.value.some(p => p.nombre.toLowerCase() === busqueda.value.toLowerCase())
)

async function cargarProyectos() {
  if (props.proyectos !== null) return
  try {
    const data = await api('/api/gestion/proyectos?estado=Activo')
    lista.value = data.proyectos || []
  } catch {}
}

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceAbove = rect.top
  const spaceBelow = window.innerHeight - rect.bottom
  const goUp = spaceAbove > spaceBelow && spaceBelow < 220
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
  if (lista.value.length === 0 && props.proyectos === null) await cargarProyectos()
  calcularPosicion()
  abierto.value = true
  busqueda.value = ''
  await nextTick()
  searchRef.value?.focus()
}

function cerrar() { abierto.value = false; busqueda.value = '' }

function seleccionar(id) {
  emit('update:modelValue', id)
  cerrar()
}

function abrirModalCrear() {
  cerrar()
  mostrarModal.value = true
}

function onProyectoCreado(p) {
  if (props.proyectos === null) lista.value.push(p)
  emit('proyecto-creado', p)
  seleccionar(p.id)
}

function onClickOutside(e) {
  if (!wrapRef.value?.contains(e.target)) cerrar()
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.proyecto-selector { position: relative; display: inline-block; }

.proyecto-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px; height: 26px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-secondary);
  cursor: pointer; transition: border-color 80ms, background 80ms;
  white-space: nowrap; max-width: 200px;
}
.proyecto-btn:hover { border-color: var(--border-default); background: var(--bg-row-hover); }
.proyecto-btn.has-value { color: var(--text-primary); border-color: var(--border-default); }
.proyecto-btn-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }

.proyecto-dot {
  width: 8px; height: 8px;
  border-radius: 50%; flex-shrink: 0;
}

.proyecto-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 200px; max-height: 280px;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.proyecto-search-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.proyecto-search {
  background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); flex: 1;
}
.proyecto-option {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.proyecto-option:hover, .proyecto-option.selected { background: var(--bg-row-hover); color: var(--text-primary); }
.proyecto-nombre { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.proyecto-empty {
  padding: 8px 12px; font-size: 12px; color: var(--text-tertiary); font-style: italic;
}
.proyecto-crear {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; font-size: 13px; color: var(--accent);
  cursor: pointer; border-top: 1px solid var(--border-subtle);
  transition: background 60ms;
}
.proyecto-crear:hover { background: var(--accent-muted); }
</style>
