<template>
  <div class="proyecto-selector" ref="wrapRef">
    <button class="proyecto-btn" @click.stop="abrirMenu" :class="{ 'has-value': modelValue }">
      <span v-if="proyectoSeleccionado" class="proyecto-dot" :style="{ background: proyectoSeleccionado.color }"></span>
      <span class="proyecto-btn-label">{{ proyectoSeleccionado?.nombre || 'Sin asignar' }}</span>
      <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">expand_more</span>
    </button>

    <Teleport to="body">
      <div v-if="abierto" class="proyecto-dropdown" :style="dropdownStyle" @click.stop>
        <!-- Buscar -->
        <div class="proyecto-search-wrap">
          <span class="material-icons" style="font-size:14px">search</span>
          <input ref="searchRef" v-model="busqueda" class="proyecto-search" placeholder="Buscar..." @keydown.escape="cerrar" />
        </div>

        <!-- Lista agrupada -->
        <div class="proyecto-lista">
          <!-- Sin asignar -->
          <div class="proyecto-option" :class="{ selected: !modelValue }" @click="seleccionar(null)">
            <span class="proyecto-dot" style="background:var(--border-default)"></span>
            <span>Sin asignar</span>
            <span v-if="!modelValue" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
          </div>

          <!-- Grupos por tipo -->
          <template v-for="sec in SECCIONES" :key="sec.tipo">
            <template v-if="gruposFiltrados[sec.tipo]?.length">
              <div class="grupo-header">{{ sec.label }}</div>
              <div
                v-for="p in gruposFiltrados[sec.tipo]"
                :key="p.id"
                class="proyecto-option"
                :class="{ selected: modelValue === p.id }"
                @click="seleccionar(p.id)"
              >
                <span class="proyecto-dot" :style="{ background: p.color }"></span>
                <span class="proyecto-nombre">{{ p.nombre }}</span>
                <span v-if="modelValue === p.id" class="material-icons" style="font-size:14px;margin-left:auto;color:var(--accent)">check</span>
              </div>
            </template>
          </template>

          <div v-if="totalFiltrado === 0 && busqueda" class="proyecto-empty">
            Sin resultados para "{{ busqueda }}"
          </div>
        </div>

        <!-- Crear nuevos -->
        <div class="proyecto-crear-wrap">
          <div v-for="sec in SECCIONES" :key="sec.tipo" class="proyecto-crear" @click="emitCrear(sec.tipo)">
            <span class="material-icons" style="font-size:14px">add</span>
            {{ sec.btnCrear }}
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
  modelValue: { type: Number, default: null },
  proyectos:  { type: Array, default: null }
})
const emit = defineEmits(['update:modelValue', 'crear-item'])

const SECCIONES = [
  { tipo: 'proyecto',   label: 'Proyectos',    btnCrear: 'Nuevo proyecto' },
  { tipo: 'dificultad', label: 'Dificultades',  btnCrear: 'Nueva dificultad' },
  { tipo: 'compromiso', label: 'Compromisos',   btnCrear: 'Nuevo compromiso' },
  { tipo: 'idea',       label: 'Ideas',          btnCrear: 'Nueva idea' },
]

const wrapRef       = ref(null)
const searchRef     = ref(null)
const abierto       = ref(false)
const busqueda      = ref('')
const lista         = ref([])
const extras        = ref([])
const dropdownStyle = ref({})

const proyectosData = computed(() => {
  const base = props.proyectos !== null ? props.proyectos : lista.value
  if (!extras.value.length) return base
  const ids = new Set(base.map(p => p.id))
  return [...base, ...extras.value.filter(p => !ids.has(p.id))]
})

const proyectoSeleccionado = computed(() => proyectosData.value.find(p => p.id === props.modelValue) || null)

const gruposFiltrados = computed(() => {
  const result = {}
  for (const sec of SECCIONES) {
    let items = proyectosData.value.filter(p => (p.tipo || 'proyecto') === sec.tipo)
    if (busqueda.value) {
      const q = busqueda.value.toLowerCase()
      items = items.filter(p => p.nombre.toLowerCase().includes(q))
    }
    result[sec.tipo] = items
  }
  return result
})

const totalFiltrado = computed(() =>
  Object.values(gruposFiltrados.value).reduce((s, arr) => s + arr.length, 0)
)

async function cargarProyectos() {
  if (props.proyectos !== null) return
  try {
    const data = await api('/api/gestion/proyectos')
    lista.value = data.proyectos || []
  } catch {}
}

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const goUp = spaceBelow < 280 && rect.top > spaceBelow
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
  if (!lista.value.length && props.proyectos === null) await cargarProyectos()
  calcularPosicion()
  abierto.value = true
  busqueda.value = ''
  await nextTick()
  searchRef.value?.focus()
}

function cerrar() { abierto.value = false; busqueda.value = '' }
function seleccionar(id) { emit('update:modelValue', id); cerrar() }

function emitCrear(tipo) {
  cerrar()
  emit('crear-item', tipo)
}

// Para agregar items creados externamente
function agregarItem(p) {
  if (props.proyectos === null) lista.value.push(p)
  else extras.value.push(p)
}

defineExpose({ agregarItem })

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
  min-width: 220px; max-height: 360px;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.proyecto-lista { flex: 1; overflow-y: auto; }
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

/* Grupo header */
.grupo-header {
  padding: 8px 12px 3px;
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--text-tertiary);
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

/* Crear nuevos */
.proyecto-crear-wrap {
  border-top: 1px solid var(--border-subtle);
}
.proyecto-crear {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; font-size: 12px; color: var(--accent);
  cursor: pointer; transition: background 60ms;
}
.proyecto-crear:hover { background: var(--accent-muted); }
</style>
