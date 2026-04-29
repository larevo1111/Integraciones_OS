<template>
  <div class="art-selector" ref="wrapRef">
    <div class="art-input-wrap" :class="{ abierto, 'tiene-valor': !!modelValue }">
      <input
        ref="inputRef"
        class="art-input"
        v-show="!modelValue || abierto"
        v-model="query"
        :placeholder="placeholder"
        @focus="abrir"
        @input="buscar"
        @keydown.escape="cerrar"
        @keydown.down.prevent="moverFoco(1)"
        @keydown.up.prevent="moverFoco(-1)"
        @keydown.enter.prevent="seleccionar(resultados[focoIdx])"
      />
      <div v-if="modelValue && !abierto" class="art-tag" @click="abrirEdit">
        <span class="art-tag-cod">{{ modelValue.cod }}</span>
        <span class="art-tag-desc">{{ modelValue.nombre }}</span>
        <span v-if="modelValue.unidad" class="art-tag-und">{{ modelValue.unidad }}</span>
        <button class="art-tag-clear" @click.stop="limpiar" title="Quitar">
          <span class="material-icons" style="font-size:14px">close</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="artdrop">
        <div v-if="abierto" class="art-dropdown" :style="dropdownStyle">
          <div v-if="cargando" class="art-estado">
            <span class="material-icons spin" style="font-size:14px">refresh</span>
            Buscando…
          </div>
          <div v-else-if="!resultados.length" class="art-estado">
            <span class="material-icons" style="font-size:14px">search_off</span>
            {{ query ? 'Sin resultados' : 'Empieza a escribir para buscar' }}
          </div>
          <template v-else>
            <div
              v-for="(a, i) in resultados"
              :key="a.cod"
              class="art-item"
              :class="{ focused: focoIdx === i, 'art-fallback': a.score === 3 }"
              @mouseenter="focoIdx = i"
              @click="seleccionar(a)"
            >
              <div class="art-item-left">
                <div class="art-item-row1">
                  <span class="art-cod">{{ a.cod }}</span>
                  <span class="art-nombre">{{ a.nombre }}</span>
                </div>
                <div class="art-item-row2">
                  <span v-if="a.grupo" class="art-grupo">{{ a.grupo }}</span>
                  <span v-else class="art-grupo art-grupo-faltante">Sin clasificar</span>
                  <span v-if="a.unidad" class="art-unidad">{{ a.unidad }}</span>
                  <span v-if="a.costo_unit" class="art-costo">${{ formatNum(a.costo_unit) }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  modelValue: { type: Object, default: null },     // {cod, nombre, unidad, costo_unit, precio_unit, grupo}
  tipo:       { type: String, default: 'material' }, // material | producto
  placeholder:{ type: String, default: 'Buscar artículo…' },
})
const emit = defineEmits(['update:modelValue'])

const wrapRef    = ref(null)
const inputRef   = ref(null)
const query      = ref('')
const abierto    = ref(false)
const cargando   = ref(false)
const resultados = ref([])
const focoIdx    = ref(0)
const dropdownStyle = ref({})

let debounceTimer = null

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  const goUp = spaceAbove > spaceBelow && spaceBelow < 280
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top + 4}px`, maxHeight: `${Math.min(spaceAbove - 8, 320)}px` }
      : { top: `${rect.bottom + 4}px`, maxHeight: `${Math.min(spaceBelow - 8, 320)}px` })
  }
}

function abrir() {
  calcularPosicion()
  abierto.value = true
  if (!resultados.value.length && !query.value) cargar('')
}
function abrirEdit() {
  query.value = ''
  abrir()
  setTimeout(() => inputRef.value?.focus(), 0)
}
function cerrar() {
  abierto.value = false
  focoIdx.value = 0
  query.value = ''
}
function limpiar() {
  emit('update:modelValue', null)
  query.value = ''
  abierto.value = false
}
function buscar() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => cargar(query.value), 250)
}
async function cargar(q) {
  cargando.value = true
  focoIdx.value = 0
  try {
    const params = new URLSearchParams({ tipo: props.tipo })
    if (q) params.set('q', q)
    const data = await api(`/api/gestion/articulos?${params.toString()}`)
    resultados.value = data.articulos || []
  } catch { resultados.value = [] } finally { cargando.value = false }
}
function seleccionar(a) {
  if (!a) return
  emit('update:modelValue', a)
  abierto.value = false
  query.value = ''
}
function moverFoco(dir) {
  const max = resultados.value.length - 1
  focoIdx.value = Math.max(0, Math.min(max, focoIdx.value + dir))
}
function formatNum(n) {
  if (n == null) return ''
  return Number(n).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

function onClickOutside(e) {
  if (wrapRef.value && !wrapRef.value.contains(e.target)) {
    if (!e.target.closest?.('.art-dropdown')) cerrar()
  }
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

watch(() => props.tipo, () => { resultados.value = []; if (abierto.value) cargar(query.value) })
</script>

<style scoped>
.art-selector { position: relative; width: 100%; }

.art-input-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: text; min-height: 36px;
  transition: border-color 120ms;
}
.art-input-wrap.abierto, .art-input-wrap:focus-within { border-color: var(--accent); }

.art-input {
  flex: 1; background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary);
  font-family: var(--font-sans); min-width: 0;
}
.art-input::placeholder { color: var(--text-tertiary); }

.art-tag {
  display: flex; align-items: center; gap: 6px;
  flex: 1; min-width: 0; cursor: pointer;
}
.art-tag-cod {
  font-size: 11px; font-weight: 700; color: var(--accent);
  white-space: nowrap;
}
.art-tag-desc {
  font-size: 12px; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1;
}
.art-tag-und {
  font-size: 11px; color: var(--text-tertiary);
  font-weight: 500; flex-shrink: 0;
}
.art-tag-clear {
  background: none; border: none; cursor: pointer;
  color: var(--text-tertiary); display: flex; padding: 0 2px;
  flex-shrink: 0;
}
.art-tag-clear:hover { color: var(--text-primary); }

.art-dropdown {
  background: var(--bg-modal);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden; overflow-y: auto;
}

.art-estado {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 12px; font-size: 13px; color: var(--text-tertiary);
}

.art-item {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 12px; cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
  transition: background 60ms;
}
.art-item:last-child { border-bottom: none; }
.art-item.focused, .art-item:hover { background: var(--bg-row-hover); }
.art-item.art-fallback { opacity: 0.7; }

.art-item-left { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.art-item-row1 { display: flex; gap: 8px; align-items: baseline; min-width: 0; }
.art-item-row2 {
  display: flex; gap: 8px; align-items: center;
  font-size: 11px; color: var(--text-tertiary);
}

.art-cod {
  font-size: 11px; font-weight: 700; color: var(--accent); flex-shrink: 0;
}
.art-nombre {
  font-size: 13px; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;
}

.art-grupo {
  display: inline-block; font-size: 9px; font-weight: 600;
  padding: 1px 5px; border-radius: 8px;
  background: rgba(0,200,83,0.15); color: #00C853;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.art-grupo-faltante { background: rgba(255,167,38,0.15); color: #FFA726; }
.art-unidad { color: var(--text-secondary); font-weight: 500; }
.art-costo { color: var(--text-tertiary); margin-left: auto; }

.art-dropdown::-webkit-scrollbar { width: 4px; }
.art-dropdown::-webkit-scrollbar-track { background: transparent; }
.art-dropdown::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 2px; }

.artdrop-enter-active, .artdrop-leave-active { transition: opacity 120ms, transform 120ms; }
.artdrop-enter-from, .artdrop-leave-to { opacity: 0; transform: translateY(-4px); }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
