<template>
  <div class="op-section cal-section">
    <!-- Header -->
    <div class="op-section-title cal-header">
      <span>Calidad</span>
      <span v-if="estaFirmada" class="cal-badge cal-aprobado-bg" :class="badgeClase">
        {{ resultadoLabel }}
      </span>
      <span v-else-if="hayBorrador" class="cal-badge cal-badge-borrador">
        🕐 Borrador
      </span>
      <q-space />
      <span v-if="estaFirmada" class="cal-firma-info">
        Firmada por {{ short(insp?.firmada_por) }} · {{ fmtFechaCorta(insp?.firmada_en) }}
      </span>
    </div>

    <!-- Form siempre abierto -->
    <div v-if="cargado" class="cal-form">
      <!-- Bloque 1: Muestreo -->
      <div class="cal-block">
        <div class="cal-block-title">1. Muestreo</div>
        <div class="cal-row">
          <span class="cal-lbl">Tamaño lote</span>
          <span class="cal-val">{{ tamanoLote || '—' }} <span class="cal-mini">uds</span></span>
        </div>
        <div class="cal-row">
          <label class="cal-lbl">Tamaño muestra</label>
          <input type="number" inputmode="numeric" min="0"
            :value="form.tamano_muestra ?? ''"
            :disabled="readOnly"
            @blur="onBlur('tamano_muestra', $event.target.value, 'int')"
            class="cal-input cal-input-sm" />
          <span class="cal-mini">AQL sug.: {{ aqlSugerido }}</span>
        </div>
      </div>

      <!-- Bloque 2: Inspección visual -->
      <div class="cal-block">
        <div class="cal-block-title">2. Inspección visual</div>
        <div v-for="check in checksGenericos" :key="check.key" class="cal-check-row">
          <span class="cal-check-lbl">{{ check.label }}</span>
          <div class="cal-chips">
            <button type="button" v-for="op in opcionesSiNoNa" :key="op.v"
              :class="['cal-chip', form[check.key] === op.v ? 'cal-chip-active cal-chip-' + op.v : '']"
              :disabled="readOnly"
              @click="onChip(check.key, op.v)">{{ op.l }}</button>
          </div>
        </div>
      </div>

      <!-- Bloque 3: Defectos -->
      <div class="cal-block">
        <div class="cal-block-title">3. Defectos</div>
        <div v-for="d in defectosFields" :key="d.key" class="cal-def-row">
          <span class="cal-def-lbl">{{ d.label }}</span>
          <div class="cal-def-stepper">
            <button type="button" class="cal-step-btn"
              :disabled="readOnly"
              @click="onStep(d.key, -1)">−</button>
            <input type="number" inputmode="numeric" min="0"
              :value="form[d.key] ?? 0"
              :disabled="readOnly"
              @blur="onBlur(d.key, $event.target.value, 'int')"
              class="cal-input cal-input-step" />
            <button type="button" class="cal-step-btn"
              :disabled="readOnly"
              @click="onStep(d.key, 1)">+</button>
          </div>
          <span v-if="d.key === 'defectos_criticos' && (form.defectos_criticos || 0) > 0" class="cal-mini cal-warn">tolerancia 0</span>
        </div>
      </div>

      <!-- Bloque 4: Resultado -->
      <div class="cal-block">
        <div class="cal-block-title">4. Resultado</div>
        <div class="cal-chips cal-result-chips">
          <button type="button"
            :class="['cal-chip', form.resultado === 'aprobado' ? 'cal-chip-active cal-chip-aprobado' : '']"
            :disabled="readOnly"
            @click="onChipResultado('aprobado')">Aprobado</button>
          <button type="button"
            :class="['cal-chip', form.resultado === 'rechazado' ? 'cal-chip-active cal-chip-rechazado' : '']"
            :disabled="readOnly"
            @click="onChipResultado('rechazado')">Rechazado</button>
        </div>
        <textarea
          :value="form.observacion ?? ''"
          :disabled="readOnly"
          @blur="onBlur('observacion', $event.target.value, 'str')"
          placeholder="Observación (opcional)"
          rows="2" class="cal-textarea"></textarea>
        <div v-if="insp?.actualizada_por && !estaFirmada" class="cal-mini cal-firma-line">
          Última edición: {{ short(insp.actualizada_por) }} · {{ fmtFechaCorta(insp.actualizada_en) }}
        </div>
      </div>

      <!-- Acciones -->
      <div class="cal-acciones">
        <q-space />
        <q-btn v-if="!estaFirmada && !readOnly && !opCerrada"
          unelevated dense no-caps size="sm" color="primary"
          :loading="firmando"
          :disable="!puedeFirmar"
          @click="firmar"
          label="Firmar inspección" />
        <q-btn v-if="estaFirmada && puedeReabrir && !opCerrada"
          flat dense no-caps size="sm" color="warning"
          :loading="reabriendo"
          @click="reabrir"
          label="Reabrir" />
      </div>
      <div v-if="!estaFirmada && !readOnly && !opCerrada && !puedeFirmar" class="cal-mini cal-firma-falta">
        Para firmar: elegí Aprobado o Rechazado en el bloque 4.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'

const $q   = useQuasar()
const auth = useAuthStore()

const props = defineProps({
  idOp:      { type: [String, Number], required: true },
  estadoOp:  { type: String, default: '' },
  esAnulada: { type: Boolean, default: false },
})
const emit = defineEmits(['actualizada'])

const opcionesSiNoNa = [
  { v: 'si', l: 'Sí' },
  { v: 'no', l: 'No' },
  { v: 'na', l: 'N/A' },
]
const checksGenericos = [
  { key: 'visual_normal',     label: 'Visual normal' },
  { key: 'tapado_sellado',    label: 'Bien tapado/sellado' },
  { key: 'etiqueta_normal',   label: 'Etiqueta normal' },
  { key: 'sabor_olor_normal', label: 'Sabor/olor normal' },
]
const defectosFields = [
  { key: 'defectos_criticos', label: 'Críticos' },
  { key: 'defectos_mayores',  label: 'Mayores' },
  { key: 'defectos_menores',  label: 'Menores' },
]

const insp = ref(null)
const tamanoLote = ref(null)
const aqlSugerido = ref(0)
const cargado = ref(false)
const firmando = ref(false)
const reabriendo = ref(false)

const form = reactive({
  tamano_muestra:    null,
  visual_normal:     null,
  tapado_sellado:    null,
  etiqueta_normal:   null,
  sabor_olor_normal: null,
  defectos_criticos: 0,
  defectos_mayores:  0,
  defectos_menores:  0,
  resultado:         null,
  observacion:       '',
})

const opCerrada = computed(() => props.estadoOp === 'Validado' || props.esAnulada)
const estaFirmada = computed(() => insp.value?.firmada === 1)
const readOnly = computed(() => estaFirmada.value || opCerrada.value)
const hayBorrador = computed(() =>
  !estaFirmada.value && (
    form.tamano_muestra != null || form.visual_normal || form.tapado_sellado ||
    form.etiqueta_normal || form.sabor_olor_normal ||
    (form.defectos_criticos || 0) > 0 || (form.defectos_mayores || 0) > 0 ||
    (form.defectos_menores || 0) > 0 || form.resultado || form.observacion
  )
)
const puedeFirmar = computed(() => !!form.resultado)
const miNivel = computed(() => auth.usuario?.nivel || 1)
const puedeReabrir = computed(() => miNivel.value >= 5)
const resultadoLabel = computed(() => {
  if (form.resultado === 'aprobado') return '🟢 Aprobado'
  if (form.resultado === 'rechazado') return '🔴 Rechazado'
  if (form.resultado === 'liberado_observacion') return '🟡 Liberado c/obs'
  return '—'
})
const badgeClase = computed(() => {
  if (form.resultado === 'aprobado')  return 'cal-aprobado'
  if (form.resultado === 'rechazado') return 'cal-rechazado'
  if (form.resultado === 'liberado_observacion') return 'cal-liberado'
  return ''
})

function fmtFechaCorta(s) {
  if (!s) return ''
  const d = new Date(s); if (isNaN(d)) return String(s)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) + ' ' + d.toTimeString().slice(0, 5)
}
function short(email) { return (email || '').split('@')[0] || '—' }

function aplicarRespuesta(i) {
  insp.value = i
  if (i) {
    Object.assign(form, {
      tamano_muestra:    i.tamano_muestra,
      visual_normal:     i.visual_normal,
      tapado_sellado:    i.tapado_sellado,
      etiqueta_normal:   i.etiqueta_normal,
      sabor_olor_normal: i.sabor_olor_normal,
      defectos_criticos: i.defectos_criticos ?? 0,
      defectos_mayores:  i.defectos_mayores ?? 0,
      defectos_menores:  i.defectos_menores ?? 0,
      resultado:         i.resultado,
      observacion:       i.observacion ?? '',
    })
  }
}

async function cargar() {
  cargado.value = false
  try {
    const sug = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad/sugerencia`)
    tamanoLote.value = sug.tamano_lote_unidades || null
    aqlSugerido.value = sug.aql_sugerido || 0
    if (form.tamano_muestra == null && aqlSugerido.value) form.tamano_muestra = aqlSugerido.value

    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad`)
    aplicarRespuesta(r.inspeccion)
  } catch (e) { console.error('[CalidadPanel cargar]', e) }
  finally { cargado.value = true }
}

async function patch(payload) {
  if (readOnly.value) return
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad`, {
      method: 'PATCH', body: JSON.stringify(payload)
    })
    // Recargar para tener datos del server (incl. actualizada_por/en)
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad`)
    aplicarRespuesta(r.inspeccion)
    emit('actualizada')
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error guardando', position: 'top', timeout: 3000 })
  }
}

function onChip(key, val) {
  const nuevo = form[key] === val ? null : val
  if (form[key] === nuevo) return
  form[key] = nuevo
  patch({ [key]: nuevo })
}
function onChipResultado(val) {
  if (form.resultado === val) return
  form.resultado = val
  patch({ resultado: val })
}
function onBlur(key, raw, kind) {
  let v = raw
  if (kind === 'int')  v = raw === '' ? null : Math.max(0, parseInt(raw, 10) || 0)
  if (kind === 'str')  v = raw == null ? null : String(raw).trim() || null
  if ((form[key] ?? null) === (v ?? null)) return
  form[key] = v
  patch({ [key]: v })
}
function onStep(key, delta) {
  const nuevo = Math.max(0, (form[key] || 0) + delta)
  if (form[key] === nuevo) return
  form[key] = nuevo
  patch({ [key]: nuevo })
}

async function firmar() {
  if (!puedeFirmar.value) return
  firmando.value = true
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad/firmar`, { method: 'POST' })
    $q.notify({ type: 'positive', message: 'Inspección firmada', position: 'top', timeout: 2500 })
    await cargar()
    emit('actualizada')
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error al firmar', position: 'top' })
  } finally { firmando.value = false }
}

async function reabrir() {
  $q.dialog({
    title: 'Reabrir inspección',
    message: 'La inspección volverá a borrador y podrás editarla. ¿Continuar?',
    cancel: 'Cancelar', ok: { label: 'Reabrir', color: 'warning' }, persistent: false, dark: true
  }).onOk(async () => {
    reabriendo.value = true
    try {
      await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad/reabrir`, { method: 'POST' })
      $q.notify({ type: 'info', message: 'Inspección reabierta para edición', position: 'top', timeout: 2500 })
      await cargar()
      emit('actualizada')
    } catch (e) {
      $q.notify({ type: 'negative', message: e.message || 'Error al reabrir', position: 'top' })
    } finally { reabriendo.value = false }
  })
}

watch(() => props.idOp, cargar)
onMounted(cargar)

defineExpose({ insp, recargar: cargar, ultimaInsp: insp })
</script>

<style scoped>
.op-section {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.op-section-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
  display: flex; align-items: center; gap: 6px;
}
.cal-firma-info { font-size: 10px; color: var(--text-tertiary); text-transform: none; font-weight: 400; }

.cal-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
}
.cal-badge.cal-aprobado  { background: #2db14a33; color: #2db14a; }
.cal-badge.cal-rechazado { background: #e74c3c33; color: #e74c3c; }
.cal-badge.cal-liberado  { background: #ffa72633; color: #ffa726; }
.cal-badge-borrador      { background: var(--bg-row-hover); color: var(--text-tertiary); }

.cal-form { padding: 4px 0; }

.cal-block {
  background: var(--bg-row-hover); border-radius: 6px;
  padding: 10px; margin-bottom: 8px;
}
.cal-block-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-secondary); margin-bottom: 8px;
}

.cal-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px;
}
.cal-lbl { width: 130px; color: var(--text-tertiary); font-size: 12px; }
.cal-val { color: var(--text-primary); font-weight: 500; }
.cal-mini { font-size: 11px; color: var(--text-tertiary); }
.cal-warn { color: #ffa726; font-weight: 500; }

.cal-input {
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 13px; font-family: inherit;
  min-height: 32px;
}
.cal-input:disabled { opacity: 0.6; cursor: not-allowed; }
.cal-input:focus { outline: 2px solid var(--accent); }
.cal-input-sm { width: 70px; }
.cal-input-step { width: 50px; text-align: center; border-radius: 0; }

.cal-check-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;
}
.cal-check-lbl { font-size: 13px; flex: 1; min-width: 130px; }

.cal-chips { display: flex; gap: 4px; flex-wrap: wrap; }
.cal-chip {
  background: var(--bg-card); color: var(--text-secondary);
  border: 1px solid var(--border-default); border-radius: 12px;
  padding: 4px 12px; font-size: 12px; cursor: pointer;
  font-family: inherit; min-height: 30px;
}
.cal-chip:hover:not(:disabled) { background: var(--border-subtle); }
.cal-chip:disabled { opacity: 0.6; cursor: not-allowed; }
.cal-chip.cal-chip-active { font-weight: 600; }
.cal-chip.cal-chip-si        { background: #2db14a33; color: #2db14a; border-color: #2db14a; }
.cal-chip.cal-chip-no        { background: #e74c3c33; color: #e74c3c; border-color: #e74c3c; }
.cal-chip.cal-chip-na        { background: var(--bg-row-hover); color: var(--text-tertiary); border-color: var(--text-tertiary); }
.cal-chip.cal-chip-aprobado  { background: #2db14a33; color: #2db14a; border-color: #2db14a; }
.cal-chip.cal-chip-rechazado { background: #e74c3c33; color: #e74c3c; border-color: #e74c3c; }

.cal-def-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cal-def-lbl { width: 80px; font-size: 13px; }
.cal-def-stepper { display: flex; align-items: center; gap: 0; }
.cal-step-btn {
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default);
  width: 30px; height: 32px; cursor: pointer;
  font-size: 16px; font-weight: 600; font-family: inherit;
}
.cal-step-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.cal-step-btn:hover:not(:disabled) { background: var(--accent-muted); }
.cal-step-btn:first-child { border-radius: 4px 0 0 4px; border-right: none; }
.cal-step-btn:last-child  { border-radius: 0 4px 4px 0; border-left: none; }

.cal-result-chips { margin-bottom: 8px; }
.cal-textarea {
  width: 100%;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 13px; font-family: inherit; resize: vertical;
}
.cal-textarea:disabled { opacity: 0.6; cursor: not-allowed; }
.cal-textarea:focus { outline: 2px solid var(--accent); }
.cal-firma-line { margin-top: 6px; }

.cal-acciones {
  display: flex; align-items: center; gap: 8px; padding-top: 4px;
}
.cal-firma-falta { text-align: right; color: #ffa726; padding-top: 4px; font-style: italic; }

@media (max-width: 600px) {
  .cal-lbl { width: 110px; }
}
</style>
