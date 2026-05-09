<template>
  <div v-if="puntosCriticos.length || sinReceta" class="op-section">
    <div class="op-section-title">Puntos críticos</div>

    <div v-if="sinReceta" class="op-empty">
      Esta OP no tiene puntos críticos definidos en la receta.
    </div>

    <div v-else class="pc-list">
      <div v-for="pc in puntosCriticos" :key="pc.id" class="pc-row">
        <div class="pc-header">
          <span class="pc-nombre">{{ pc.parametro }}</span>
          <span v-if="pc.instrumento" class="cal-mini">· {{ pc.instrumento }}</span>
          <q-space />
          <span v-if="medicion(pc.id)?.actualizada_por || medicion(pc.id)?.registrado_por" class="cal-mini">
            {{ short(medicion(pc.id).actualizada_por || medicion(pc.id).registrado_por) }}
          </span>
        </div>

        <!-- Numérico -->
        <template v-if="pc.tipo === 'numerico'">
          <div class="pc-input-row">
            <input
              type="number" inputmode="decimal" step="any"
              :value="medicion(pc.id)?.valor_numerico ?? ''"
              :placeholder="rangoPlaceholder(pc)"
              :disabled="readOnly"
              @blur="onBlurNumerico(pc, $event.target.value)"
              class="pc-input"
            />
            <span class="pc-unidad">{{ pc.unidad || '' }}</span>
            <span v-if="rangoVisual(pc)" class="pc-rango" :class="rangoClass(pc)">
              {{ rangoVisual(pc) }}
            </span>
          </div>
        </template>

        <!-- Booleano -->
        <template v-else-if="pc.tipo === 'booleano'">
          <div class="pc-chips">
            <button type="button"
              :class="['pc-chip', medicionVal(pc, 'valor_booleano') === 1 ? 'pc-chip-active pc-chip-si' : '']"
              :disabled="readOnly"
              @click="onChipBooleano(pc, 1)">Sí</button>
            <button type="button"
              :class="['pc-chip', medicionVal(pc, 'valor_booleano') === 0 ? 'pc-chip-active pc-chip-no' : '']"
              :disabled="readOnly"
              @click="onChipBooleano(pc, 0)">No</button>
          </div>
        </template>

        <!-- Selección -->
        <template v-else-if="pc.tipo === 'seleccion'">
          <div class="pc-chips">
            <button type="button" v-for="op in opcionesDe(pc)" :key="op"
              :class="['pc-chip', medicionVal(pc, 'valor_texto') === op ? 'pc-chip-active pc-chip-si' : '']"
              :disabled="readOnly"
              @click="onSeleccion(pc, op)">{{ op }}</button>
          </div>
        </template>

        <!-- Texto -->
        <template v-else>
          <input type="text"
            :value="medicion(pc.id)?.valor_texto ?? ''"
            :disabled="readOnly"
            @blur="onBlurTexto(pc, $event.target.value)"
            class="pc-input pc-input-full"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'

const $q = useQuasar()

const props = defineProps({
  idOp:     { type: [String, Number], required: true },
  readOnly: { type: Boolean, default: false },
})

const puntosCriticos = ref([]) // de la receta
const mediciones     = ref([]) // valores actuales en BD
const sinReceta      = ref(false)

function medicion(pcRecetaId) {
  return mediciones.value.find(m => m.pc_receta_id === pcRecetaId) || null
}
function medicionVal(pc, key) {
  const m = medicion(pc.id)
  if (!m) return null
  return key === 'valor_booleano' && m[key] != null ? Number(m[key]) : m[key]
}
function opcionesDe(pc) {
  if (!pc.opciones_json) return []
  try { const o = JSON.parse(pc.opciones_json); return Array.isArray(o) ? o : [] } catch { return [] }
}
function rangoPlaceholder(pc) {
  if (pc.rango_min == null && pc.rango_max == null) return ''
  return `${pc.rango_min ?? ''}–${pc.rango_max ?? ''}`
}
function rangoVisual(pc) {
  const m = medicion(pc.id)
  if (!m || m.valor_numerico == null || m.valor_numerico === '') return ''
  return m.dentro_rango === 1 ? '✓ rango' : '✗ fuera'
}
function rangoClass(pc) {
  const m = medicion(pc.id)
  if (!m) return ''
  if (m.dentro_rango === 1) return 'pc-rango-ok'
  if (m.dentro_rango === 0) return 'pc-rango-fail'
  return ''
}
function short(email) {
  if (!email) return ''
  return email.split('@')[0]
}

async function cargar() {
  try {
    const sug = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/calidad/sugerencia`)
    puntosCriticos.value = sug.puntos_criticos || []
    sinReceta.value = !puntosCriticos.value.length
    const meds = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/pc-proceso`)
    mediciones.value = meds.mediciones || []
  } catch (e) {
    console.error('[PuntosCriticosPanel cargar]', e)
  }
}

async function persistir(pc, valores) {
  try {
    const body = {
      parametro: pc.parametro,
      tipo: pc.tipo,
      unidad: pc.unidad,
      rango_min: pc.rango_min,
      rango_max: pc.rango_max,
      ...valores,
    }
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/pc-proceso/${pc.id}`, {
      method: 'PATCH',
      body: JSON.stringify(body)
    })
    // Actualizar localmente con el resultado del server (incluye dentro_rango calculado)
    const idx = mediciones.value.findIndex(m => m.pc_receta_id === pc.id)
    const updated = {
      pc_receta_id: pc.id,
      valor_numerico: valores.valor_numerico ?? null,
      valor_booleano: valores.valor_booleano ?? null,
      valor_texto:    valores.valor_texto ?? null,
      dentro_rango:   r.dentro_rango,
      registrado_por: idx >= 0 ? mediciones.value[idx].registrado_por : 'tú',
      actualizada_por: 'tú',
    }
    if (idx >= 0) mediciones.value[idx] = { ...mediciones.value[idx], ...updated }
    else mediciones.value.push(updated)
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error guardando PC', position: 'top', timeout: 3000 })
  }
}

function onBlurNumerico(pc, raw) {
  const v = raw === '' ? null : Number(String(raw).replace(',', '.'))
  if (v != null && isNaN(v)) return
  const actual = medicion(pc.id)?.valor_numerico
  if (Number(actual) === v || (actual == null && v == null)) return
  persistir(pc, { valor_numerico: v })
}
function onBlurTexto(pc, raw) {
  const v = raw == null ? null : String(raw)
  const actual = medicion(pc.id)?.valor_texto
  if (actual === v || (!actual && !v)) return
  persistir(pc, { valor_texto: v })
}
function onChipBooleano(pc, val) {
  const actual = medicionVal(pc, 'valor_booleano')
  const nuevo = actual === val ? null : val
  persistir(pc, { valor_booleano: nuevo })
}
function onSeleccion(pc, val) {
  const actual = medicionVal(pc, 'valor_texto')
  const nuevo = actual === val ? null : val
  persistir(pc, { valor_texto: nuevo })
}

watch(() => props.idOp, cargar)
onMounted(cargar)

defineExpose({ recargar: cargar, mediciones })
</script>

<style scoped>
.op-section {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.op-section-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
}
.op-empty { font-size: 11px; color: var(--text-tertiary); font-style: italic; padding: 4px 0; }

.pc-list { display: flex; flex-direction: column; gap: 6px; }
.pc-row {
  background: var(--bg-row-hover); border-radius: 6px; padding: 8px 10px;
}
.pc-header {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; margin-bottom: 6px;
}
.pc-nombre { color: var(--text-primary); }
.cal-mini { font-size: 11px; color: var(--text-tertiary); }

.pc-input-row { display: flex; align-items: center; gap: 6px; }
.pc-input {
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 13px; font-family: inherit;
  min-height: 32px; width: 90px; text-align: right;
}
.pc-input:disabled { opacity: 0.6; cursor: not-allowed; }
.pc-input:focus { outline: 2px solid var(--accent); }
.pc-input-full { width: 100%; text-align: left; }
.pc-unidad { font-size: 12px; color: var(--text-tertiary); width: 35px; }

.pc-rango {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
}
.pc-rango-ok   { background: #2db14a33; color: #2db14a; }
.pc-rango-fail { background: #e74c3c33; color: #e74c3c; }

.pc-chips { display: flex; gap: 4px; flex-wrap: wrap; }
.pc-chip {
  background: var(--bg-card); color: var(--text-secondary);
  border: 1px solid var(--border-default); border-radius: 12px;
  padding: 4px 12px; font-size: 12px; cursor: pointer;
  font-family: inherit; min-height: 30px;
}
.pc-chip:hover:not(:disabled) { background: var(--border-subtle); }
.pc-chip:disabled { opacity: 0.6; cursor: not-allowed; }
.pc-chip.pc-chip-active { font-weight: 600; }
.pc-chip.pc-chip-si { background: #2db14a33; color: #2db14a; border-color: #2db14a; }
.pc-chip.pc-chip-no { background: #e74c3c33; color: #e74c3c; border-color: #e74c3c; }

@media (max-width: 600px) {
  .pc-input { width: 75px; }
}
</style>
