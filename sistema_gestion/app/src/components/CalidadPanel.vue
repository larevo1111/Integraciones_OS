<template>
  <div class="cal-section">
    <!-- Header con resumen + botón nueva -->
    <div class="cal-header">
      <span class="cal-title">Calidad</span>
      <span v-if="ultimaInsp" class="cal-badge" :class="badgeClass">
        {{ resultadoLabel(ultimaInsp.resultado) }}
      </span>
      <q-space />
      <q-btn
        v-if="!modoNueva && estadoOp !== 'Anulada' && !esAnulada"
        flat dense no-caps size="xs"
        :label="ultimaInsp ? '+ Otra inspección' : '+ Inspección'"
        @click="iniciarNueva"
      />
    </div>

    <!-- Histórico (collapse) -->
    <div v-if="!modoNueva && inspecciones.length" class="cal-historico">
      <div v-for="i in inspecciones" :key="i.id" class="cal-insp-card" :class="resultadoClase(i.resultado)">
        <div class="cal-insp-row1">
          <span class="cal-insp-resultado">{{ resultadoLabel(i.resultado) }}</span>
          <span class="cal-insp-fecha">{{ fmtFecha(i.inspeccionado_en) }}</span>
          <span class="cal-insp-inspector">· {{ i.inspector_email?.split('@')[0] }}</span>
        </div>
        <div class="cal-insp-row2">
          {{ i.tamano_muestra || 0 }} de {{ i.tamano_lote_unidades || '?' }} muestras ·
          {{ totalDefectos(i) }} defectos ·
          {{ i.puntos_criticos?.length || 0 }} mediciones
        </div>
        <div v-if="i.observacion" class="cal-insp-obs">{{ i.observacion }}</div>
      </div>
    </div>

    <!-- Mensaje cuando no hay inspección -->
    <div v-if="!modoNueva && !inspecciones.length && !cargandoSugerencia" class="cal-empty">
      Sin inspecciones de calidad registradas.
    </div>

    <!-- Form nueva inspección -->
    <form v-if="modoNueva" class="cal-form" @submit.prevent="guardar">
      <div v-if="cargandoSugerencia" class="cal-loading">Cargando receta…</div>
      <template v-else>
        <!-- Bloque 1: Muestreo -->
        <div class="cal-block">
          <div class="cal-block-title">1. Muestreo</div>
          <div class="cal-row">
            <span class="cal-lbl">Tamaño lote</span>
            <span class="cal-val">{{ form.tamano_lote_unidades || '—' }} <span class="cal-mini">uds</span></span>
          </div>
          <div class="cal-row">
            <label class="cal-lbl" for="cal-tm">Tamaño muestra</label>
            <input id="cal-tm" type="number" inputmode="numeric" min="0"
              v-model.number="form.tamano_muestra" class="cal-input cal-input-sm" />
            <span class="cal-mini">AQL sug.: {{ aqlSugerido }}</span>
          </div>
        </div>

        <!-- Bloque 2: Inspección visual genérica -->
        <div class="cal-block">
          <div class="cal-block-title">2. Inspección visual</div>
          <div v-for="check in checksGenericos" :key="check.key" class="cal-check-row">
            <span class="cal-check-lbl">{{ check.label }}</span>
            <div class="cal-chips">
              <button type="button" v-for="op in opcionesSiNoNa" :key="op.v"
                :class="['cal-chip', form[check.key] === op.v ? 'cal-chip-active cal-chip-' + op.v : '']"
                @click="form[check.key] = op.v">{{ op.l }}</button>
            </div>
          </div>
        </div>

        <!-- Bloque 3: Mediciones (PCs dinámicos) -->
        <div class="cal-block" v-if="puntosCriticos.length">
          <div class="cal-block-title">3. Mediciones del proceso</div>
          <div v-for="(pc, idx) in form.puntos_criticos" :key="idx" class="cal-pc-row">
            <div class="cal-pc-header">
              <span class="cal-pc-nombre">{{ pc.parametro }}</span>
              <span v-if="pc.instrumento" class="cal-mini">· {{ pc.instrumento }}</span>
            </div>
            <!-- Numérico -->
            <template v-if="pc.tipo === 'numerico'">
              <div class="cal-pc-input-row">
                <input type="number" inputmode="decimal" step="any"
                  v-model.number="pc.valor_numerico" class="cal-input"
                  :placeholder="pc.rango_min != null ? `${pc.rango_min} – ${pc.rango_max ?? '∞'}` : ''" />
                <span class="cal-pc-unidad">{{ pc.unidad || '' }}</span>
                <span class="cal-pc-rango" :class="rangoClass(pc)">
                  {{ rangoLabel(pc) }}
                </span>
              </div>
            </template>
            <!-- Booleano -->
            <template v-else-if="pc.tipo === 'booleano'">
              <div class="cal-chips">
                <button type="button"
                  :class="['cal-chip', pc.valor_booleano === 1 ? 'cal-chip-active cal-chip-si' : '']"
                  @click="pc.valor_booleano = 1">Sí</button>
                <button type="button"
                  :class="['cal-chip', pc.valor_booleano === 0 ? 'cal-chip-active cal-chip-no' : '']"
                  @click="pc.valor_booleano = 0">No</button>
              </div>
            </template>
            <!-- Selección -->
            <template v-else-if="pc.tipo === 'seleccion'">
              <div class="cal-chips">
                <button type="button" v-for="op in (pc._opciones || [])" :key="op"
                  :class="['cal-chip', pc.valor_texto === op ? 'cal-chip-active cal-chip-si' : '']"
                  @click="pc.valor_texto = op">{{ op }}</button>
              </div>
            </template>
            <!-- Texto -->
            <template v-else>
              <input type="text" v-model="pc.valor_texto" class="cal-input cal-input-full" />
            </template>
          </div>
        </div>

        <!-- Bloque 4: Defectos -->
        <div class="cal-block">
          <div class="cal-block-title">4. Defectos</div>
          <div v-for="d in defectosFields" :key="d.key" class="cal-def-row">
            <span class="cal-def-lbl">{{ d.label }}</span>
            <div class="cal-def-stepper">
              <button type="button" class="cal-step-btn" @click="form[d.key] = Math.max(0, (form[d.key] || 0) - 1)">−</button>
              <input type="number" inputmode="numeric" min="0"
                v-model.number="form[d.key]" class="cal-input cal-input-step" />
              <button type="button" class="cal-step-btn" @click="form[d.key] = (form[d.key] || 0) + 1">+</button>
            </div>
            <span v-if="d.warning" class="cal-mini cal-warn">{{ d.warning }}</span>
          </div>
        </div>

        <!-- Bloque 5: Resultado -->
        <div class="cal-block">
          <div class="cal-block-title">5. Resultado</div>
          <div class="cal-chips cal-result-chips">
            <button type="button"
              :class="['cal-chip', form.resultado === 'aprobado' ? 'cal-chip-active cal-chip-aprobado' : '']"
              @click="form.resultado = 'aprobado'">Aprobado</button>
            <button type="button"
              :class="['cal-chip', form.resultado === 'rechazado' ? 'cal-chip-active cal-chip-rechazado' : '']"
              @click="form.resultado = 'rechazado'">Rechazado</button>
          </div>
          <textarea v-model="form.observacion" class="cal-textarea"
            placeholder="Observación (opcional)"
            rows="2"></textarea>
          <div class="cal-mini cal-firma">Firma: {{ inspectorEmail }} · {{ fmtFecha(new Date()) }}</div>
        </div>

        <!-- Acciones -->
        <div class="cal-acciones">
          <q-btn flat dense no-caps size="sm" label="Cancelar" @click="cancelar" />
          <q-space />
          <div class="cal-submit-wrap">
            <q-btn unelevated dense no-caps size="sm" color="primary"
              :loading="guardando"
              :disable="!puedeGuardar" label="Guardar inspección"
              type="submit" />
            <div v-if="!puedeGuardar && !guardando" class="cal-hint-falta">{{ mensajeFalta }}</div>
          </div>
        </div>
      </template>
    </form>
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

const inspectorEmail = computed(() => auth.usuario?.email || '')

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

const inspecciones      = ref([])
const ultimaInsp        = computed(() => inspecciones.value[0] || null)
const modoNueva         = ref(false)
const cargandoSugerencia = ref(false)
const guardando         = ref(false)

const aqlSugerido       = ref(0)
const puntosCriticos    = ref([])

const form = reactive({
  tamano_lote_unidades: null,
  tamano_muestra:       null,
  visual_normal:        null,
  tapado_sellado:       null,
  etiqueta_normal:      null,
  sabor_olor_normal:    null,
  defectos_criticos:    0,
  defectos_mayores:     0,
  defectos_menores:     0,
  resultado:            null,
  observacion:          '',
  puntos_criticos:      [],
})

const defectosFields = computed(() => [
  { key: 'defectos_criticos', label: 'Críticos', warning: form.defectos_criticos > 0 ? 'tolerancia 0' : '' },
  { key: 'defectos_mayores',  label: 'Mayores',  warning: '' },
  { key: 'defectos_menores',  label: 'Menores',  warning: '' },
])

const puedeGuardar = computed(() => !!form.resultado)
const mensajeFalta = computed(() => form.resultado ? '' : 'Falta: elegir Aprobado o Rechazado')

const badgeClass = computed(() => {
  if (!ultimaInsp.value) return ''
  return resultadoClase(ultimaInsp.value.resultado)
})

async function cargarInspecciones() {
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad`)
    inspecciones.value = r.inspecciones || []
  } catch (e) { console.error('[CalidadPanel cargar]', e) }
}

async function cargarSugerencia() {
  cargandoSugerencia.value = true
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad/sugerencia`)
    aqlSugerido.value = r.aql_sugerido || 0
    puntosCriticos.value = r.puntos_criticos || []
    form.tamano_lote_unidades = r.tamano_lote_unidades || null
    form.tamano_muestra = r.aql_sugerido || null
    // Inicializar puntos_criticos del form con snapshot
    form.puntos_criticos = (r.puntos_criticos || []).map(pc => ({
      pc_receta_id: pc.id,
      parametro:    pc.parametro,
      tipo:         pc.tipo,
      unidad:       pc.unidad,
      instrumento:  pc.instrumento,
      rango_min:    pc.rango_min != null ? Number(pc.rango_min) : null,
      rango_max:    pc.rango_max != null ? Number(pc.rango_max) : null,
      _opciones:    parseOpciones(pc.opciones_json),
      valor_numerico: null,
      valor_booleano: null,
      valor_texto:    null,
    }))
  } catch (e) {
    console.error('[CalidadPanel sugerencia]', e)
    $q.notify({ type: 'negative', message: 'Error cargando receta', position: 'top' })
  } finally { cargandoSugerencia.value = false }
}

function parseOpciones(j) {
  if (!j) return []
  try { const o = JSON.parse(j); return Array.isArray(o) ? o : [] } catch { return [] }
}

async function iniciarNueva() {
  // Reset form
  Object.assign(form, {
    tamano_lote_unidades: null, tamano_muestra: null,
    visual_normal: null, tapado_sellado: null, etiqueta_normal: null, sabor_olor_normal: null,
    defectos_criticos: 0, defectos_mayores: 0, defectos_menores: 0,
    resultado: null, observacion: '', puntos_criticos: [],
  })
  modoNueva.value = true
  await cargarSugerencia()
}

function cancelar() {
  modoNueva.value = false
}

async function guardar() {
  if (!puedeGuardar.value) return
  guardando.value = true
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad`, {
      method: 'POST',
      body: JSON.stringify(form)
    })
    $q.notify({ type: 'positive', message: 'Inspección registrada', position: 'top', timeout: 2000 })
    modoNueva.value = false
    await cargarInspecciones()
    emit('actualizada')
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error al guardar', position: 'top' })
  } finally { guardando.value = false }
}

function rangoClass(pc) {
  if (pc.tipo !== 'numerico' || pc.valor_numerico == null || pc.valor_numerico === '') return ''
  const v = Number(pc.valor_numerico)
  if (isNaN(v)) return ''
  const okMin = pc.rango_min == null || v >= pc.rango_min
  const okMax = pc.rango_max == null || v <= pc.rango_max
  return (okMin && okMax) ? 'cal-rango-ok' : 'cal-rango-fail'
}
function rangoLabel(pc) {
  if (pc.rango_min == null && pc.rango_max == null) return ''
  if (pc.valor_numerico == null || pc.valor_numerico === '') return `${pc.rango_min ?? ''}–${pc.rango_max ?? ''}`
  return rangoClass(pc) === 'cal-rango-ok' ? '✓ rango' : '✗ fuera'
}

function resultadoLabel(r) {
  if (r === 'aprobado') return '🟢 Aprobado'
  if (r === 'rechazado') return '🔴 Rechazado'
  if (r === 'liberado_observacion') return '🟡 Liberado c/obs'
  return r || '—'
}
function resultadoClase(r) {
  if (r === 'aprobado') return 'cal-aprobado'
  if (r === 'rechazado') return 'cal-rechazado'
  if (r === 'liberado_observacion') return 'cal-liberado'
  return ''
}
function totalDefectos(i) {
  return (i.defectos_criticos || 0) + (i.defectos_mayores || 0) + (i.defectos_menores || 0)
}
function fmtFecha(s) {
  if (!s) return ''
  const d = new Date(s)
  if (isNaN(d)) return String(s)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) + ' ' + d.toTimeString().slice(0, 5)
}

watch(() => props.idOp, () => { modoNueva.value = false; cargarInspecciones() })
onMounted(() => cargarInspecciones())

defineExpose({ ultimaInsp })
</script>

<style scoped>
.cal-section {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.cal-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
}
.cal-title { color: var(--text-tertiary); }
.cal-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-row-hover); color: var(--text-tertiary);
}
.cal-badge.cal-aprobado  { background: #2db14a33; color: #2db14a; }
.cal-badge.cal-rechazado { background: #e74c3c33; color: #e74c3c; }
.cal-badge.cal-liberado  { background: #ffa72633; color: #ffa726; }

.cal-empty { font-size: 11px; color: var(--text-tertiary); font-style: italic; padding: 4px 0; }

.cal-historico { display: flex; flex-direction: column; gap: 6px; }
.cal-insp-card {
  padding: 8px 10px; border-radius: 6px; font-size: 12px;
  border: 1px solid var(--border-subtle); background: var(--bg-row-hover);
}
.cal-insp-card.cal-aprobado  { border-left: 3px solid #2db14a; }
.cal-insp-card.cal-rechazado { border-left: 3px solid #e74c3c; }
.cal-insp-card.cal-liberado  { border-left: 3px solid #ffa726; }
.cal-insp-row1 { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cal-insp-resultado { font-weight: 600; }
.cal-insp-fecha { color: var(--text-tertiary); font-size: 11px; }
.cal-insp-inspector { color: var(--text-tertiary); font-size: 11px; }
.cal-insp-row2 { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.cal-insp-obs { font-size: 11px; color: var(--text-secondary); margin-top: 4px; font-style: italic; }

.cal-form { padding: 4px 0; }
.cal-loading { font-size: 12px; color: var(--text-tertiary); padding: 12px; text-align: center; }

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
.cal-input:focus { outline: 2px solid var(--accent); }
.cal-input-sm { width: 70px; }
.cal-input-step { width: 50px; text-align: center; }
.cal-input-full { width: 100%; }

.cal-check-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;
}
.cal-check-lbl { font-size: 13px; flex: 1; min-width: 130px; }

.cal-chips {
  display: flex; gap: 4px; flex-wrap: wrap;
}
.cal-chip {
  background: var(--bg-card); color: var(--text-secondary);
  border: 1px solid var(--border-default); border-radius: 12px;
  padding: 4px 12px; font-size: 12px; cursor: pointer;
  font-family: inherit;
  min-height: 30px;
}
.cal-chip:hover { background: var(--border-subtle); }
.cal-chip.cal-chip-active { font-weight: 600; }
.cal-chip.cal-chip-si        { background: #2db14a33; color: #2db14a; border-color: #2db14a; }
.cal-chip.cal-chip-no        { background: #e74c3c33; color: #e74c3c; border-color: #e74c3c; }
.cal-chip.cal-chip-na        { background: var(--bg-row-hover); color: var(--text-tertiary); border-color: var(--text-tertiary); }
.cal-chip.cal-chip-aprobado  { background: #2db14a33; color: #2db14a; border-color: #2db14a; }
.cal-chip.cal-chip-rechazado { background: #e74c3c33; color: #e74c3c; border-color: #e74c3c; }
.cal-chip.cal-chip-liberado  { background: #ffa72633; color: #ffa726; border-color: #ffa726; }

.cal-pc-row { padding: 6px 0; border-bottom: 1px dashed var(--border-subtle); }
.cal-pc-row:last-child { border-bottom: none; }
.cal-pc-header { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.cal-pc-nombre { color: var(--text-primary); }
.cal-pc-input-row {
  display: flex; align-items: center; gap: 6px;
}
.cal-pc-input-row .cal-input { width: 90px; text-align: right; }
.cal-pc-unidad {
  font-size: 12px; color: var(--text-tertiary); width: 35px;
}
.cal-pc-rango {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
}
.cal-rango-ok   { background: #2db14a33; color: #2db14a; }
.cal-rango-fail { background: #e74c3c33; color: #e74c3c; }

.cal-def-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.cal-def-lbl { width: 80px; font-size: 13px; }
.cal-def-stepper { display: flex; align-items: center; gap: 0; }
.cal-step-btn {
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default);
  width: 30px; height: 32px; cursor: pointer;
  font-size: 16px; font-weight: 600;
  font-family: inherit;
}
.cal-step-btn:hover { background: var(--accent-muted); }
.cal-step-btn:first-child { border-radius: 4px 0 0 4px; border-right: none; }
.cal-step-btn:last-child  { border-radius: 0 4px 4px 0; border-left: none; }
.cal-input-step { border-radius: 0; }

.cal-result-chips { margin-bottom: 8px; }
.cal-textarea {
  width: 100%;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 13px; font-family: inherit; resize: vertical;
}
.cal-textarea:focus { outline: 2px solid var(--accent); }
.cal-firma { margin-top: 6px; }

.cal-acciones {
  display: flex; align-items: center; gap: 8px; padding-top: 4px;
}
.cal-submit-wrap { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.cal-hint-falta {
  font-size: 10px; color: #ffa726; font-style: italic;
}

@media (max-width: 600px) {
  .cal-lbl { width: 110px; }
  .cal-pc-input-row .cal-input { width: 70px; }
}
</style>
