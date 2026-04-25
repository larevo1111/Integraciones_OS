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
      <div v-if="tarea.id_op && detalleOp" class="op-box q-pa-sm rounded-borders">
        <div class="row items-center q-gutter-xs">
          <div class="col text-body2">OP-{{ detalleOp.id_orden }} · {{ detalleOp.articulos }}</div>
          <q-badge v-if="detalleOp.estado" :class="estadoBadgeClass" :label="detalleOp.estado" />
        </div>
        <div class="row items-center q-mt-xs">
          <q-btn
            flat dense no-caps size="sm"
            color="primary"
            icon="edit"
            label="Editar en la OP"
            @click="abrirOp"
          />
          <q-space />
        </div>
      </div>
    </div>

    <!-- Materiales + Productos (solo lectura) -->
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
          <div class="col-3 text-right text-weight-medium q-pt-xs">
            <span :class="diffClass(l)">
              {{ l.cantidad_real == null ? '—' : fmtNum(l.cantidad_real) }}
            </span>
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
          <div class="col-3 text-right text-weight-medium q-pt-xs">
            <span :class="diffClass(l)">
              {{ l.cantidad_real == null ? '—' : fmtNum(l.cantidad_real) }}
            </span>
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
  </q-expansion-item>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from 'src/services/api'
import { fmtNum, parseDecimal } from 'src/services/numero'
import OpSelector from './OpSelector.vue'

const props = defineProps({
  tarea: { type: Object, required: true }
})
const emit = defineEmits(['actualizar-id-op', 'abrir-op'])

const abierto    = ref(false)
const cargando   = ref(false)
const materiales = ref([])
const productos  = ref([])
const detalleOp  = ref(null)

const estadoBadgeClass = computed(() => {
  const e = (detalleOp.value?.estado || '').toLowerCase()
  if (e === 'validado')  return 'bg-positive text-white'
  if (e === 'procesada') return 'bg-warning text-black'
  if (e === 'anulada')   return 'bg-grey-7 text-white'
  return 'bg-grey-5 text-black'  // Generada o desconocido
})

async function cargar() {
  if (!props.tarea?.id || !props.tarea.id_op) {
    materiales.value = []
    productos.value  = []
    detalleOp.value  = null
    return
  }
  cargando.value = true
  try {
    // Leemos la ficha de la OP (nuevo endpoint, fuente de verdad a nivel OP).
    const data = await api(`/api/gestion/op/${encodeURIComponent(props.tarea.id_op)}/ficha`)
    materiales.value = data.materiales || []
    productos.value  = data.productos  || []
    detalleOp.value  = data.cabecera ? {
      id_orden: data.cabecera.id_orden,
      estado:   data.cabecera.estado,
      articulos: [...(data.productos || [])].map(p => p.descripcion).filter(Boolean).join(' / ')
    } : null
  } catch (e) {
    console.error('[DetallesProduccion] cargar:', e)
  } finally {
    cargando.value = false
  }
}

watch(abierto, v => { if (v) cargar() })
watch(() => [props.tarea?.id, props.tarea?.id_op], () => { if (abierto.value) cargar() })

function onChangeOp(val) { emit('actualizar-id-op', val) }
function abrirOp() {
  if (props.tarea.id_op) emit('abrir-op', props.tarea.id_op)
}

function diffValor(l) {
  const r = parseDecimal(l.cantidad_real)
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
</script>

<style scoped>
.op-box {
  background: var(--bg-row-hover);
  color: var(--text-primary);
  font-size: 12px;
}
.dp-nombre {
  font-size: 11px;
  line-height: 1.3;
  word-break: break-word;
  color: var(--text-primary);
}
.linea { border-bottom: 1px solid var(--border-subtle); }
.linea:last-child { border-bottom: none; }
</style>
