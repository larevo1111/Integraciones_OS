<template>
  <q-expansion-item
    v-if="tarea?.id && tarea?.id_op"
    v-model="abierto"
    dense
    header-class="text-caption text-weight-medium"
    label="Detalles de producción"
  >
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
import { ref, watch } from 'vue'
import { api } from 'src/services/api'
import { fmtNum, parseDecimal } from 'src/services/numero'

const props = defineProps({
  tarea: { type: Object, required: true }
})

const abierto    = ref(false)
const cargando   = ref(false)
const materiales = ref([])
const productos  = ref([])

async function cargar() {
  if (!props.tarea?.id || !props.tarea.id_op) {
    materiales.value = []
    productos.value  = []
    return
  }
  cargando.value = true
  try {
    const data = await api(`/api/gestion/op/${encodeURIComponent(props.tarea.id_op)}/ficha`)
    materiales.value = data.materiales || []
    productos.value  = data.productos  || []
  } catch (e) {
    console.error('[DetallesProduccion] cargar:', e)
  } finally {
    cargando.value = false
  }
}

watch(abierto, v => { if (v) cargar() })
watch(() => [props.tarea?.id, props.tarea?.id_op], () => { if (abierto.value) cargar() })

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
.dp-nombre {
  font-size: 11px;
  line-height: 1.3;
  word-break: break-word;
  color: var(--text-primary);
}
.linea { border-bottom: 1px solid var(--border-subtle); }
.linea:last-child { border-bottom: none; }
</style>
