<template>
  <q-expansion-item
    v-if="tarea?.id"
    v-model="abierto"
    dense
    header-class="text-caption text-weight-medium"
    label="Detalles de producción"
  >
    <!-- OP vinculada -->
    <div class="q-pa-sm q-gutter-y-sm">
      <div class="text-caption text-grey">OP vinculada</div>
      <OpSelector
        :modelValue="tarea.id_op || ''"
        @update:modelValue="onChangeOp"
      />
      <div v-if="tarea.id_op && detalleOp" class="op-box q-pa-sm rounded-borders text-body2">
        OP-{{ detalleOp.id_orden }} · {{ detalleOp.articulos }}
      </div>
    </div>

    <!-- Materiales + Productos -->
    <template v-if="tarea.id_op">
      <!-- Materiales -->
      <div v-if="materiales.length" class="q-pa-sm">
        <div class="text-caption text-grey q-mb-xs">Materiales consumidos</div>
        <div class="row q-col-gutter-xs text-caption text-grey">
          <div class="col-7">Material</div>
          <div class="col-2 text-right">Estimado</div>
          <div class="col-3 text-right">Real</div>
        </div>
        <q-separator class="q-mt-xs" />
        <div
          v-for="l in materiales" :key="l.id"
          class="row q-col-gutter-xs q-py-xs items-start linea"
        >
          <div class="col-7 dp-nombre">
            <span class="text-grey q-mr-xs">{{ l.cod_articulo }}</span>{{ l.descripcion }}
          </div>
          <div class="col-2 text-right text-caption text-grey q-pt-xs">
            {{ fmtNum(l.cantidad_teorica) }}
            <div class="text-caption text-grey">{{ l.unidad }}</div>
          </div>
          <div class="col-3 text-right">
            <q-input
              dense outlined hide-bottom-space
              input-class="text-right text-weight-medium"
              :model-value="formValor(l)"
              :placeholder="fmtNum(l.cantidad_teorica)"
              inputmode="decimal"
              @update:model-value="v => onInput(l, v)"
              @blur="guardarLinea(l)"
            />
            <div v-if="diffText(l)" class="text-caption" :class="diffClass(l)">
              {{ diffText(l) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Productos -->
      <div v-if="productos.length" class="q-pa-sm">
        <div class="text-caption text-grey q-mb-xs">Artículos producidos</div>
        <div class="row q-col-gutter-xs text-caption text-grey">
          <div class="col-7">Artículo</div>
          <div class="col-2 text-right">Estimado</div>
          <div class="col-3 text-right">Real</div>
        </div>
        <q-separator class="q-mt-xs" />
        <div
          v-for="l in productos" :key="l.id"
          class="row q-col-gutter-xs q-py-xs items-start linea"
        >
          <div class="col-7 dp-nombre">
            <span class="text-grey q-mr-xs">{{ l.cod_articulo }}</span>{{ l.descripcion }}
          </div>
          <div class="col-2 text-right text-caption text-grey q-pt-xs">
            {{ fmtNum(l.cantidad_teorica) }}
            <div class="text-caption text-grey">{{ l.unidad }}</div>
          </div>
          <div class="col-3 text-right">
            <q-input
              dense outlined hide-bottom-space
              input-class="text-right text-weight-medium"
              :model-value="formValor(l)"
              :placeholder="fmtNum(l.cantidad_teorica)"
              inputmode="decimal"
              @update:model-value="v => onInput(l, v)"
              @blur="guardarLinea(l)"
            />
            <div v-if="diffText(l)" class="text-caption" :class="diffClass(l)">
              {{ diffText(l) }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="!materiales.length && !productos.length && !cargando" class="q-pa-sm text-caption text-grey text-center">
        Esta OP aún no tiene materiales ni artículos registrados en Effi.
      </div>
    </template>

    <!-- Tiempos -->
    <div class="q-pa-sm">
      <div class="text-caption text-grey q-mb-xs">Tiempos de la actividad</div>
      <div
        v-for="t in TIEMPOS_DEF" :key="t.key"
        class="row items-center q-py-xs"
      >
        <div class="col text-body2">{{ t.label }}</div>
        <q-input
          dense outlined hide-bottom-space
          style="width: 70px"
          input-class="text-right"
          :model-value="tiempos[t.key] ?? ''"
          placeholder="—"
          inputmode="numeric"
          @update:model-value="v => tiempos[t.key] = parseInt(v) || null"
          @blur="guardarTiempos"
        />
        <span class="text-caption text-grey q-ml-xs" style="width:30px">min</span>
      </div>
      <q-separator class="q-my-xs" />
      <div class="row items-center q-py-xs">
        <div class="col text-body2 text-weight-medium">Total</div>
        <div style="width:70px" class="text-right text-weight-medium">{{ totalTiempos }}</div>
        <span class="text-caption text-grey q-ml-xs" style="width:30px">min</span>
      </div>
    </div>
  </q-expansion-item>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api } from 'src/services/api'
import { parseDecimal, fmtNum } from 'src/services/numero'
import OpSelector from './OpSelector.vue'

const props = defineProps({
  tarea: { type: Object, required: true }
})
const emit = defineEmits(['actualizar-id-op'])

const TIEMPOS_DEF = [
  { key: 'alistamiento', label: 'Alistamiento' },
  { key: 'produccion',   label: 'Producción'  },
  { key: 'empaque',      label: 'Empaque'     },
  { key: 'limpieza',     label: 'Limpieza'    },
]

const abierto    = ref(false)
const cargando   = ref(false)
const materiales = ref([])
const productos  = ref([])
const detalleOp  = ref(null)
const tiempos    = reactive({ alistamiento: null, produccion: null, empaque: null, limpieza: null })
const borrador   = reactive({})

async function cargar() {
  if (!props.tarea?.id || !props.tarea.id_op) {
    materiales.value = []
    productos.value  = []
    detalleOp.value  = null
    return
  }
  cargando.value = true
  try {
    const data = await api(`/api/gestion/tareas/${props.tarea.id}/produccion`)
    materiales.value = data.materiales || []
    productos.value  = data.productos  || []
    tiempos.alistamiento = data.tiempos?.alistamiento ?? null
    tiempos.produccion   = data.tiempos?.produccion   ?? null
    tiempos.empaque      = data.tiempos?.empaque      ?? null
    tiempos.limpieza     = data.tiempos?.limpieza     ?? null
    for (const k of Object.keys(borrador)) delete borrador[k]
    // Cargar descripción de la OP (una vez)
    try {
      const op = await api(`/api/gestion/op/${encodeURIComponent(props.tarea.id_op)}`)
      detalleOp.value = op?.op || null
    } catch { detalleOp.value = null }
  } catch (e) {
    console.error('[DetallesProduccion] cargar:', e)
  } finally {
    cargando.value = false
  }
}

watch(abierto, v => { if (v) cargar() })
watch(() => [props.tarea?.id, props.tarea?.id_op], () => { if (abierto.value) cargar() })

function onChangeOp(val) { emit('actualizar-id-op', val) }

function formValor(l) {
  if (borrador[l.id] !== undefined) return borrador[l.id]
  return l.cantidad_real == null ? '' : fmtNum(l.cantidad_real)
}
function onInput(l, valor) { borrador[l.id] = valor }

function realNum(l) {
  const v = parseDecimal(borrador[l.id] !== undefined ? borrador[l.id] : l.cantidad_real)
  return v
}
function diffValor(l) {
  const r = realNum(l)
  if (r == null) return null
  const teo = Number(l.cantidad_teorica) || 0
  const d = r - teo
  return Math.abs(d) < 1e-9 ? null : d
}
function diffText(l) {
  const d = diffValor(l)
  if (d == null) return ''
  return (d > 0 ? '+' : '') + fmtNum(d) + ' ' + (l.unidad || '')
}
function diffClass(l) {
  const d = diffValor(l)
  if (d == null) return ''
  return d > 0 ? 'text-positive' : 'text-negative'
}

async function guardarLinea(l) {
  const raw = borrador[l.id]
  if (raw === undefined) return
  const valor = parseDecimal(raw)
  if (valor === l.cantidad_real) { delete borrador[l.id]; return }
  try {
    await api(`/api/gestion/tareas/${props.tarea.id}/produccion/lineas/${l.id}`, {
      method: 'PUT', body: JSON.stringify({ cantidad_real: valor })
    })
    l.cantidad_real = valor
    delete borrador[l.id]
  } catch (e) { console.error('[guardarLinea]', e) }
}

const totalTiempos = computed(() => TIEMPOS_DEF.reduce((s, t) => s + (parseInt(tiempos[t.key]) || 0), 0))

let _tiemposTimeout = null
function guardarTiempos() {
  clearTimeout(_tiemposTimeout)
  _tiemposTimeout = setTimeout(async () => {
    try {
      await api(`/api/gestion/tareas/${props.tarea.id}/produccion/tiempos`, {
        method: 'PUT', body: JSON.stringify({
          alistamiento: tiempos.alistamiento,
          produccion:   tiempos.produccion,
          empaque:      tiempos.empaque,
          limpieza:     tiempos.limpieza,
        })
      })
    } catch (e) { console.error('[guardarTiempos]', e) }
  }, 300)
}
</script>

<style scoped>
.op-box {
  background: var(--bg-row-hover);
  color: var(--text-primary);
  font-size: 12px;
}
.dp-nombre {
  font-size: 12px;
  line-height: 1.35;
  word-break: break-word;
  color: var(--text-primary);
}
.linea { border-bottom: 1px solid var(--border-subtle); }
.linea:last-child { border-bottom: none; }
</style>
