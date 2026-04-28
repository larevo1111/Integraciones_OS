<template>
  <div class="resp-selector" ref="wrapRef">
    <!-- Chips seleccionados -->
    <div class="resp-chips">
      <span
        v-for="u in seleccionados"
        :key="u.email"
        class="resp-chip"
      >
        <span class="resp-avatar-sm">{{ iniciales(u.nombre) }}</span>
        {{ u.nombre.split(' ')[0] }}
        <span class="resp-chip-remove" @click.stop="quitar(u.email)">×</span>
      </span>

      <!-- Botón agregar -->
      <button class="resp-add-btn" @click.stop="abrirMenu">
        <span class="material-icons" style="font-size:14px">person_add</span>
        <span v-if="!seleccionados.length">Responsable</span>
      </button>
    </div>

    <!-- Dropdown -->
    <Teleport to="body">
      <div v-if="abierto" class="resp-dropdown" :style="dropdownStyle" @click.stop>
        <div class="resp-search-wrap">
          <span class="material-icons" style="font-size:14px">search</span>
          <input ref="searchRef" v-model="busqueda" class="resp-search" placeholder="Buscar..." @keydown.escape="cerrar" />
        </div>

        <div style="overflow-y:auto;max-height:200px">
          <div
            v-for="u in usuariosFiltrados"
            :key="u.email"
            class="resp-option"
            :class="{ selected: modelValue.includes(u.email) }"
            @click="toggle(u.email)"
          >
            <span class="resp-avatar">{{ iniciales(u.nombre) }}</span>
            <span class="resp-option-nombre">{{ u.nombre }}</span>
            <span v-if="modelValue.includes(u.email)" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
          </div>

          <div v-if="!usuariosFiltrados.length" class="resp-empty">
            {{ busqueda ? 'Sin resultados' : 'Sin usuarios' }}
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },  // array de emails
  usuarios:   { type: Array, default: null },       // si se pasa, no carga de API
  single:     { type: Boolean, default: false }     // si true: selección única (reemplaza)
})
const emit = defineEmits(['update:modelValue'])

const wrapRef    = ref(null)
const searchRef  = ref(null)
const abierto    = ref(false)
const busqueda   = ref('')
const lista      = ref([])
const dropdownStyle = ref({})

const usuariosData = computed(() => props.usuarios !== null ? props.usuarios : lista.value)
const seleccionados = computed(() => usuariosData.value.filter(u => props.modelValue.includes(u.email)))
const usuariosFiltrados = computed(() => {
  if (!busqueda.value) return usuariosData.value
  // Multi-palabra AND (regla CLAUDE.md §Quicksearch)
  const words = busqueda.value.toLowerCase().trim().split(/\s+/)
  return usuariosData.value.filter(u => {
    const t = (u.nombre || '').toLowerCase()
    return words.every(w => t.includes(w))
  })
})

async function cargarUsuarios() {
  if (props.usuarios !== null) return
  try {
    const data = await api('/api/gestion/usuarios')
    lista.value = data.usuarios || []
  } catch {}
}

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const goUp = (window.innerHeight - rect.bottom) < 220 && rect.top > 220
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 220)}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top}px` }
      : { top: `${rect.bottom + 4}px` })
  }
}

async function abrirMenu() {
  if (lista.value.length === 0 && props.usuarios === null) await cargarUsuarios()
  calcularPosicion()
  abierto.value = true
  busqueda.value = ''
  await nextTick()
  searchRef.value?.focus()
}

function cerrar() { abierto.value = false; busqueda.value = '' }

function toggle(email) {
  let nueva
  if (props.single) {
    nueva = props.modelValue.includes(email) ? [] : [email]
    if (nueva.length) cerrar()  // auto-cierra al seleccionar
  } else {
    nueva = props.modelValue.includes(email)
      ? props.modelValue.filter(x => x !== email)
      : [...props.modelValue, email]
  }
  emit('update:modelValue', nueva)
}

function quitar(email) {
  emit('update:modelValue', props.modelValue.filter(x => x !== email))
}

function iniciales(nombre) {
  return nombre.split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase()
}

function onClickOutside(e) {
  if (!wrapRef.value?.contains(e.target)) cerrar()
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.resp-selector { display: inline-flex; align-items: center; position: relative; }

.resp-chips {
  display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
}

.resp-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 6px; height: 22px;
  background: var(--bg-row-hover);
  border: 1px solid var(--border-subtle);
  border-radius: 11px;
  font-size: 11px; color: var(--text-secondary);
  white-space: nowrap;
}
.resp-chip-remove {
  cursor: pointer; font-size: 14px; line-height: 1;
  opacity: 0.6; margin-left: 1px;
  transition: opacity 80ms;
}
.resp-chip-remove:hover { opacity: 1; }

.resp-avatar-sm {
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--border-default);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 700; color: var(--text-secondary);
  flex-shrink: 0;
}

.resp-add-btn {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 6px; height: 24px;
  background: transparent; border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 12px; color: var(--text-tertiary);
  cursor: pointer; transition: border-color 80ms, color 80ms;
}
.resp-add-btn:hover { border-color: var(--accent); color: var(--accent); }

.resp-dropdown {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 220px;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.resp-search-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}
.resp-search {
  background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); flex: 1;
}
.resp-option {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.resp-option:hover, .resp-option.selected { background: var(--bg-row-hover); color: var(--text-primary); }
.resp-avatar {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--bg-row-hover);
  border: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; color: var(--text-secondary);
  flex-shrink: 0;
}
.resp-option-nombre { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resp-empty { padding: 8px 12px; font-size: 12px; color: var(--text-tertiary); font-style: italic; }
</style>
