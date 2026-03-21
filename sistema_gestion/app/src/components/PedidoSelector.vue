<template>
  <div class="op-selector" ref="wrapRef">

    <!-- Input trigger -->
    <div class="op-input-wrap" :class="{ abierto: abierto, 'tiene-valor': !!modelValue }">
      <input
        ref="inputRef"
        class="op-input"
        v-show="!modelValue || abierto"
        v-model="query"
        placeholder="Buscar pedido o cliente..."
        @focus="abrir"
        @input="buscar"
        @keydown.escape="cerrar"
        @keydown.down.prevent="moverFoco(1)"
        @keydown.up.prevent="moverFoco(-1)"
        @keydown.enter.prevent="seleccionar(resultados[focoIdx])"
      />
      <!-- Valor seleccionado (tag) -->
      <div v-if="modelValue && !abierto" class="op-tag">
        <span class="op-tag-num">Ped. {{ modelValue }}</span>
        <span class="op-tag-desc">{{ clienteSeleccionado }}</span>
        <!-- Acciones hover -->
        <div class="op-tag-acciones">
          <a
            class="op-tag-accion"
            :href="`https://effi.com.co/app/cotizacion?id=${modelValue}&id=${modelValue}`"
            target="_blank"
            rel="noopener"
            title="Ver en Effi"
            @click.stop
          >
            <span class="material-icons" style="font-size:13px">open_in_new</span>
          </a>
          <button
            class="op-tag-accion"
            :class="{ 'cargando-pdf': descargandoPdf }"
            title="Ver PDF"
            @click.stop="verPdf"
          >
            <span v-if="!descargandoPdf" class="material-icons" style="font-size:13px">picture_as_pdf</span>
            <span v-else class="material-icons spin" style="font-size:13px">refresh</span>
          </button>
        </div>
        <button class="op-tag-clear" @click.stop="limpiar">
          <span class="material-icons" style="font-size:14px">close</span>
        </button>
      </div>
    </div>

    <!-- Dropdown -->
    <Teleport to="body">
    <Transition name="opdrop">
      <div v-if="abierto" class="op-dropdown" :style="dropdownStyle">

        <div v-if="cargando" class="op-estado">
          <span class="material-icons spin" style="font-size:14px">refresh</span>
          Buscando pedidos...
        </div>

        <div v-else-if="!resultados.length" class="op-estado">
          <span class="material-icons" style="font-size:14px;color:var(--text-tertiary)">search_off</span>
          {{ query ? 'Sin resultados para "' + query + '"' : 'No hay pedidos' }}
        </div>

        <template v-else>
          <div class="op-hint">{{ resultados.length }} pedido{{ resultados.length !== 1 ? 's' : '' }}</div>
          <div
            v-for="(p, i) in resultados"
            :key="p.id_cotizacion"
            class="op-item"
            :class="{ focused: focoIdx === i, selected: modelValue === p.id_cotizacion }"
            @mouseenter="focoIdx = i"
            @click="seleccionar(p)"
          >
            <div class="op-item-left">
              <span class="op-num">Ped. {{ p.id_cotizacion }}</span>
              <span class="op-articulos">{{ truncar(p.cliente || '—', 55) }}</span>
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
  modelValue: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const wrapRef    = ref(null)
const inputRef   = ref(null)
const query      = ref('')
const abierto    = ref(false)
const cargando   = ref(false)
const resultados = ref([])
const focoIdx    = ref(0)
const clienteSeleccionado = ref('')
const dropdownStyle    = ref({})
const descargandoPdf   = ref(false)

let debounceTimer = null

function calcularPosicion() {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  const goUp = spaceAbove > spaceBelow && spaceBelow < 300
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: 9999,
    ...(goUp
      ? { bottom: `${window.innerHeight - rect.top + 4}px`, maxHeight: `${Math.min(spaceAbove - 8, 280)}px` }
      : { top: `${rect.bottom + 4}px`, maxHeight: `${Math.min(spaceBelow - 8, 280)}px` })
  }
}

function abrir() {
  calcularPosicion()
  abierto.value = true
  if (!resultados.value.length) cargar('')
}

function cerrar() {
  abierto.value = false
  focoIdx.value = 0
  if (!props.modelValue) query.value = ''
}

function limpiar() {
  emit('update:modelValue', '')
  query.value = ''
  clienteSeleccionado.value = ''
  abierto.value = false
}

function buscar() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => cargar(query.value), 250)
}

async function cargar(q) {
  cargando.value = true
  focoIdx.value  = 0
  try {
    const params = q ? `?q=${encodeURIComponent(q)}` : ''
    const data = await api(`/api/gestion/pedidos${params}`)
    resultados.value = data.pedidos || []
  } catch { resultados.value = [] } finally { cargando.value = false }
}

function seleccionar(p) {
  if (!p) return
  emit('update:modelValue', p.id_cotizacion)
  clienteSeleccionado.value = truncar(p.cliente || '', 40)
  query.value = ''
  abierto.value = false
}

function moverFoco(dir) {
  const max = resultados.value.length - 1
  focoIdx.value = Math.max(0, Math.min(max, focoIdx.value + dir))
}

function truncar(str, n) {
  return str && str.length > n ? str.slice(0, n) + '…' : str
}

async function verPdf() {
  if (descargandoPdf.value || !props.modelValue) return
  descargandoPdf.value = true
  try {
    const token = localStorage.getItem('gestion_jwt')
    const resp  = await fetch(`/api/gestion/pedido/${encodeURIComponent(props.modelValue)}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!resp.ok) throw new Error('Error al generar PDF')
    const blob = await resp.blob()
    const url  = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.target = '_blank'; a.rel = 'noopener'
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 30000)
  } catch (e) {
    console.error(e)
    alert('No se pudo obtener el PDF. Intenta desde Effi directamente.')
  } finally {
    descargandoPdf.value = false
  }
}

function onClickOutside(e) {
  if (wrapRef.value && !wrapRef.value.contains(e.target)) cerrar()
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

watch(() => props.modelValue, async (val) => {
  if (val && !clienteSeleccionado.value) {
    try {
      const data = await api(`/api/gestion/pedido/${encodeURIComponent(val)}`)
      clienteSeleccionado.value = truncar(data.pedido?.cliente || '', 40)
    } catch {}
  }
}, { immediate: true })
</script>

<style scoped>
.op-selector { position: relative; width: 100%; }
.op-input-wrap {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px;
  background: var(--bg-input); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); cursor: text;
  transition: border-color 120ms; min-height: 36px;
}
.op-input-wrap.abierto, .op-input-wrap:focus-within { border-color: var(--accent); outline: none; }
.op-input {
  flex: 1; background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary); font-family: var(--font-sans); min-width: 0;
}
.op-input::placeholder { color: var(--text-tertiary); }
.op-tag { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.op-tag-num { font-size: 12px; font-weight: 700; color: var(--text-primary); white-space: nowrap; }
.op-tag-desc {
  font-size: 12px; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;
}
.op-tag-acciones {
  display: flex; align-items: center; gap: 1px;
  opacity: 0; transition: opacity 100ms; flex-shrink: 0;
}
.op-input-wrap:hover .op-tag-acciones { opacity: 1; }
@media (max-width: 768px) { .op-tag-acciones { opacity: 1; } }
.op-tag-accion {
  background: none; border: none; cursor: pointer; color: var(--text-tertiary);
  display: flex; align-items: center; padding: 2px 3px;
  border-radius: var(--radius-sm); text-decoration: none;
  transition: color 80ms, background 80ms;
}
.op-tag-accion:hover { color: var(--accent); background: var(--accent-muted); }
.op-tag-accion.cargando-pdf { color: var(--accent); }
.op-tag-clear {
  background: none; border: none; cursor: pointer; color: var(--text-tertiary);
  display: flex; align-items: center; padding: 0 2px; flex-shrink: 0;
}
.op-tag-clear:hover { color: var(--text-primary); }
.op-dropdown {
  background: var(--bg-modal); border: 1px solid var(--border-default);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  overflow: hidden; overflow-y: auto;
}
.op-hint {
  padding: 6px 12px 4px; font-size: 10px; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-subtle);
}
.op-estado {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 12px; font-size: 13px; color: var(--text-tertiary);
}
.op-item {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 9px 12px; cursor: pointer; transition: background 60ms;
  border-bottom: 1px solid var(--border-subtle);
}
.op-item:last-child { border-bottom: none; }
.op-item.focused, .op-item:hover { background: var(--bg-row-hover); }
.op-item.selected { background: var(--accent-muted); }
.op-item-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.op-num { font-size: 12px; font-weight: 700; color: var(--accent); }
.op-articulos {
  font-size: 12px; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.op-dropdown::-webkit-scrollbar { width: 4px; }
.op-dropdown::-webkit-scrollbar-track { background: transparent; }
.op-dropdown::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 2px; }
.opdrop-enter-active, .opdrop-leave-active { transition: opacity 120ms, transform 120ms; }
.opdrop-enter-from, .opdrop-leave-to { opacity: 0; transform: translateY(-4px); }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
