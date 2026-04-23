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
        <div v-if="tarea.id_op_original" class="text-caption text-grey q-mt-xs">
          OP orig: {{ tarea.id_op_original }}
        </div>
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
              dense filled hide-bottom-space
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
              dense filled hide-bottom-space
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
        class="row items-center dp-tiempo-fila"
      >
        <div class="col dp-tiempo-lbl">{{ t.label }}</div>
        <q-input
          dense filled hide-bottom-space
          style="width: 70px"
          input-class="text-right"
          :model-value="tiempos[t.key] ?? ''"
          placeholder="—"
          inputmode="numeric"
          @update:model-value="v => tiempos[t.key] = parseInt(v) || null"
          @blur="guardarTiempos"
        />
        <span class="text-caption text-grey q-ml-xs" style="width:26px">min</span>
      </div>
      <q-separator class="q-my-xs" />
      <div class="row items-center dp-tiempo-fila">
        <div class="col dp-tiempo-lbl text-weight-medium">Total</div>
        <div style="width:70px" class="text-right text-weight-medium">{{ totalTiempos }}</div>
        <span class="text-caption text-grey q-ml-xs" style="width:26px">min</span>
      </div>
    </div>

    <!-- Acciones sobre la OP (sutiles) -->
    <div v-if="tarea.id_op && detalleOp" class="q-px-sm q-pb-sm row q-gutter-xs">
      <q-btn
        v-if="puedeProcesar"
        flat dense no-caps size="sm"
        color="warning"
        icon="check_circle_outline"
        label="Procesar"
        :loading="procesando"
        :disable="detalleOp.estado === 'Procesada' || detalleOp.estado === 'Validado'"
        @click="marcarProcesada"
      />
      <q-btn
        v-if="puedeValidar"
        flat dense no-caps size="sm"
        color="positive"
        icon="verified"
        label="Validar"
        :loading="validando"
        :disable="detalleOp.estado === 'Validado'"
        @click="validarOp"
      />
    </div>
  </q-expansion-item>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { parseDecimal, fmtNum } from 'src/services/numero'
import { useAuthStore } from 'src/stores/authStore'
import OpSelector from './OpSelector.vue'

const $q = useQuasar()
const auth = useAuthStore()

const props = defineProps({
  tarea: { type: Object, required: true }
})
const emit = defineEmits(['actualizar-id-op', 'actualizada'])

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
const procesando = ref(false)
const validando  = ref(false)

const miNivel = computed(() => auth.usuario?.nivel || 1)
const esResponsable = computed(() => {
  const r = props.tarea?.responsables || (props.tarea?.responsable ? [props.tarea.responsable] : [])
  return r.includes(auth.usuario?.email)
})
const puedeProcesar = computed(() => {
  // Responsable o nivel > responsable (simplificado: si es nivel alto, puede)
  return esResponsable.value || miNivel.value >= 5
})
const puedeValidar = computed(() => miNivel.value >= 5)

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

async function marcarProcesada() {
  $q.dialog({
    title: 'Marcar OP como procesada',
    message: `Esto cambiará el estado de la OP ${props.tarea.id_op} a "Procesada" en Effi. El cambio puede tardar ~30-60 segundos.`,
    cancel: true, persistent: false,
    dark: true,
    ok: { label: 'Procesar', color: 'warning' }
  }).onOk(async () => {
    procesando.value = true
    try {
      const r = await api(`/api/gestion/tareas/${props.tarea.id}/produccion/procesar`, { method: 'POST' })
      $q.notify({ type: 'positive', message: `OP ${r.id_op} → Procesada`, position: 'top' })
      await cargar()
      emit('actualizada')
    } catch (e) {
      $q.notify({ type: 'negative', message: e.message || 'Error al procesar OP', position: 'top', timeout: 6000 })
    } finally { procesando.value = false }
  })
}

async function validarOp() {
  $q.dialog({
    title: 'Validar OP',
    message: `Esto anulará la OP ${props.tarea.id_op}, creará una nueva con los valores reales reportados y la marcará como "Validado". Demora ~2-3 minutos. ¿Continuar?`,
    cancel: 'Cancelar', ok: { label: 'Validar', color: 'positive' }, persistent: true,
    dark: true
  }).onOk(async () => {
    validando.value = true
    $q.notify({ type: 'info', message: 'Validando OP… puede tardar 2-3 min.', position: 'top', timeout: 0, group: 'validar-prog' })
    try {
      const r = await api(`/api/gestion/tareas/${props.tarea.id}/produccion/validar`, { method: 'POST' })
      $q.notify({ type: 'positive', message: `OP ${r.id_op_anterior} → anulada · OP ${r.id_op_nueva} → Validado`, position: 'top', timeout: 6000 })
      emit('actualizada')
      await cargar()
    } catch (e) {
      $q.notify({ type: 'negative', message: e.message || 'Error al validar OP', position: 'top', timeout: 8000 })
    } finally {
      $q.notify({ group: 'validar-prog', message: '', timeout: 1 })
      validando.value = false
    }
  })
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

.dp-tiempo-fila { padding: 2px 0; }
.dp-tiempo-lbl  { font-size: 11px; color: var(--text-primary); }
/* Inputs de tiempo aún más compactos */
.dp-tiempo-fila :deep(.q-field--dense .q-field__control),
.dp-tiempo-fila :deep(.q-field--dense .q-field__native) {
  min-height: 26px !important;
  height: 26px !important;
}

/* Forzar contraste de q-input en dark mode del proyecto (no usa body--dark de Quasar) */
:deep(.q-field--filled .q-field__control) {
  background: var(--bg-row-hover) !important;
}
:deep(.q-field--filled .q-field__control:before) { border-bottom-color: var(--border-default) !important; }
:deep(.q-field__native),
:deep(.q-field__input) {
  color: var(--text-primary) !important;
}
:deep(.q-placeholder::placeholder) { color: var(--text-tertiary) !important; opacity: 1; }
</style>
