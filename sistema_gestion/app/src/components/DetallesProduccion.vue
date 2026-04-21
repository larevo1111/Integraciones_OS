<template>
  <q-expansion-item
    v-if="tarea?.id && tarea.id_op"
    v-model="abierto"
    dense
    header-class="dp-header"
    class="dp-root"
  >
    <template #header>
      <q-item-section>
        <span class="dp-title">DETALLES DE PRODUCCIÓN</span>
      </q-item-section>
      <q-item-section side v-if="cargando">
        <q-spinner-hourglass size="14px" color="primary" />
      </q-item-section>
    </template>

    <!-- Materiales -->
    <div v-if="materiales.length" class="q-mt-sm">
      <div class="dp-label q-mb-xs">Materiales consumidos</div>
      <q-list dense separator>
        <q-item v-for="l in materiales" :key="l.id" class="q-px-xs">
          <q-item-section class="dp-desc-cell">
            <div class="dp-desc" :title="l.descripcion">{{ l.descripcion }}</div>
          </q-item-section>
          <q-item-section side class="dp-teo">{{ fmtNum(l.cantidad_teorica) }}</q-item-section>
          <q-item-section side class="dp-real-cell">
            <q-input
              dense borderless
              input-class="text-right"
              :model-value="formValor(l)"
              :placeholder="fmtNum(l.cantidad_teorica)"
              inputmode="decimal"
              :class="{ 'dp-dirty': esDirty(l) }"
              @update:model-value="v => onInput(l, v)"
              @blur="guardarLinea(l)"
            />
          </q-item-section>
          <q-item-section side class="dp-unidad">{{ l.unidad || '—' }}</q-item-section>
        </q-item>
      </q-list>
    </div>

    <!-- Productos -->
    <div v-if="productos.length" class="q-mt-md">
      <div class="dp-label q-mb-xs">Artículos producidos</div>
      <q-list dense separator>
        <q-item v-for="l in productos" :key="l.id" class="q-px-xs">
          <q-item-section class="dp-desc-cell">
            <div class="dp-desc" :title="l.descripcion">{{ l.descripcion }}</div>
          </q-item-section>
          <q-item-section side class="dp-teo">{{ fmtNum(l.cantidad_teorica) }}</q-item-section>
          <q-item-section side class="dp-real-cell">
            <q-input
              dense borderless
              input-class="text-right"
              :model-value="formValor(l)"
              :placeholder="fmtNum(l.cantidad_teorica)"
              inputmode="decimal"
              :class="{ 'dp-dirty': esDirty(l) }"
              @update:model-value="v => onInput(l, v)"
              @blur="guardarLinea(l)"
            />
          </q-item-section>
          <q-item-section side class="dp-unidad">{{ l.unidad || '—' }}</q-item-section>
        </q-item>
      </q-list>
    </div>

    <div v-if="!materiales.length && !productos.length && !cargando" class="dp-empty q-mt-sm">
      Esta OP aún no tiene materiales ni artículos registrados en Effi.
    </div>

    <!-- Tiempos -->
    <div class="q-mt-md">
      <div class="dp-label q-mb-xs">Tiempos de la actividad</div>
      <q-list dense>
        <q-item v-for="t in TIEMPOS_DEF" :key="t.key" class="q-px-xs">
          <q-item-section>{{ t.label }}</q-item-section>
          <q-item-section side>
            <q-input
              dense borderless
              input-class="text-right"
              style="width:70px"
              :model-value="tiempos[t.key] ?? ''"
              placeholder="—"
              inputmode="numeric"
              @update:model-value="v => tiempos[t.key] = parseInt(v) || null"
              @blur="guardarTiempos"
            />
          </q-item-section>
          <q-item-section side class="dp-unit-min">min</q-item-section>
        </q-item>
        <q-separator />
        <q-item class="q-px-xs dp-total">
          <q-item-section><strong>Total</strong></q-item-section>
          <q-item-section side><strong>{{ totalTiempos }}</strong></q-item-section>
          <q-item-section side class="dp-unit-min">min</q-item-section>
        </q-item>
      </q-list>
    </div>
  </q-expansion-item>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api } from 'src/services/api'
import { parseDecimal, fmtNum } from 'src/services/numero'

const props = defineProps({
  tarea: { type: Object, required: true }
})

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
const tiempos    = reactive({ alistamiento: null, produccion: null, empaque: null, limpieza: null })
const borrador   = reactive({})

async function cargar() {
  if (!props.tarea?.id || !props.tarea.id_op) {
    materiales.value = []
    productos.value  = []
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
  } catch (e) {
    console.error('[DetallesProduccion] cargar:', e)
  } finally {
    cargando.value = false
  }
}

watch(abierto, v => { if (v) cargar() })
watch(() => [props.tarea?.id, props.tarea?.id_op], () => { if (abierto.value) cargar() })

function formValor(l) {
  if (borrador[l.id] !== undefined) return borrador[l.id]
  return l.cantidad_real == null ? '' : fmtNum(l.cantidad_real)
}
function onInput(l, valor) { borrador[l.id] = valor }
function esDirty(l) {
  const v = parseDecimal(borrador[l.id] !== undefined ? borrador[l.id] : l.cantidad_real)
  return v != null && v !== Number(l.cantidad_teorica)
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
.dp-title {
  font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
  color: var(--text-tertiary);
}
.dp-label {
  font-size: 11px; font-weight: 600; letter-spacing: 0.03em;
  color: var(--text-tertiary);
}
.dp-desc {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-size: 12px; color: var(--text-primary);
}
.dp-desc-cell { max-width: 0; flex: 1 1 auto; }
.dp-teo { font-size: 12px; color: var(--text-tertiary); font-variant-numeric: tabular-nums; min-width: 50px; text-align: right; }
.dp-real-cell { min-width: 80px; }
.dp-unidad { font-size: 11px; color: var(--text-tertiary); min-width: 40px; }
.dp-unit-min { font-size: 11px; color: var(--text-tertiary); }
.dp-dirty :deep(input) {
  color: var(--accent);
  font-weight: 500;
}
.dp-empty {
  font-size: 11px; color: var(--text-tertiary);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px;
  text-align: center;
}
.dp-total { border-top: none; }
</style>
