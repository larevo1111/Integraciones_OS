<template>
  <Teleport to="body">
    <div class="op-overlay" @click.self="$emit('cerrar')">
      <aside class="op-panel">

        <!-- ═══ SUB-PANEL: Detalle tarea ═══ -->
        <template v-if="tareaAbierta">
          <div class="op-header">
            <button class="btn-icon" @click="tareaAbierta = null" title="Volver">
              <span class="material-icons" style="font-size:18px">arrow_back</span>
            </button>
            <span class="op-header-tipo">Tarea</span>
            <q-space />
            <button class="btn-icon" title="Cerrar" @click="$emit('cerrar')">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>
          <div class="op-subtarea-wrap">
            <TareaPanel
              :tarea="tareaAbierta"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="[]"
              :etiquetas="[]"
              @cerrar="tareaAbierta = null"
              @actualizada="onTareaActualizada"
              @crear-item="() => {}"
              @abrir-padre="() => {}"
            />
          </div>
        </template>

        <!-- ═══ CONTENIDO PRINCIPAL ═══ -->
        <template v-else>
          <!-- Header -->
          <div class="op-header">
            <span class="op-header-tipo">OP-{{ idOp }}</span>
            <q-chip v-if="ficha?.cabecera"
              :class="estadoClase"
              dense size="sm"
              :label="ficha.cabecera.estado || '—'"
              style="margin-left: 6px"
            />
            <q-space />
            <button class="btn-icon" title="Cerrar" @click="$emit('cerrar')">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>

          <div v-if="cargando && !ficha" class="op-loading">
            <q-spinner color="primary" size="32px" />
            <div class="text-caption q-mt-sm">Cargando OP...</div>
          </div>

          <div v-if="ficha" class="op-body">
            <!-- ── BLOQUE 1: CABECERA ─────────────────────────── -->
            <div class="op-section">
              <div class="op-cab-row"><span class="op-lbl">Producto</span><span class="op-val">{{ articuloPrincipal || '—' }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Encargado</span><span class="op-val">{{ ficha.cabecera.nombre_encargado || '—' }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Vigencia</span><span class="op-val">{{ ficha.cabecera.vigencia || '—' }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Creada</span><span class="op-val">{{ fmtFecha(ficha.cabecera.fecha_de_creacion) }}</span></div>
              <div class="op-cab-row"><span class="op-lbl">Sucursal/Bodega</span><span class="op-val">{{ ficha.cabecera.sucursal || '—' }} / {{ ficha.cabecera.bodega || '—' }}</span></div>
              <div v-if="ficha.detalle?.op_anterior" class="op-cab-row">
                <span class="op-lbl">OP anterior</span>
                <span class="op-val text-grey">#{{ ficha.detalle.op_anterior }}</span>
              </div>
              <div v-if="ficha.detalle?.procesado_por" class="op-cab-row">
                <span class="op-lbl">Procesada por</span>
                <span class="op-val">{{ ficha.detalle.procesado_por }} · {{ fmtFecha(ficha.detalle.procesado_en) }}</span>
              </div>
              <div v-if="ficha.detalle?.validado_por" class="op-cab-row">
                <span class="op-lbl">Validada por</span>
                <span class="op-val">{{ ficha.detalle.validado_por }} · {{ fmtFecha(ficha.detalle.validado_en) }}</span>
              </div>
            </div>

            <!-- ── BLOQUE 2: MATERIALES ───────────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Materiales</div>
              <div v-if="!ficha.materiales.length" class="op-empty">Sin materiales</div>
              <table v-else class="op-table">
                <thead><tr>
                  <th>Material</th>
                  <th class="t-right">Estimado</th>
                  <th class="t-right">Real</th>
                  <th class="t-right">Costo U</th>
                  <th v-if="puedeAgregar"></th>
                </tr></thead>
                <tbody>
                  <tr v-for="l in ficha.materiales" :key="l.id">
                    <td>
                      <span class="text-grey">{{ l.cod_articulo }}</span>
                      <span v-if="l.es_no_previsto" class="badge-no-prev">+</span>
                      <div>{{ l.descripcion }}</div>
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.cantidad_teorica) }} {{ l.unidad }}</td>
                    <td class="t-right">
                      <input
                        type="text" inputmode="decimal"
                        class="op-input-num"
                        :value="formValor(l)"
                        :placeholder="fmtNum(l.cantidad_teorica)"
                        @input="e => borrador[l.id] = e.target.value"
                        @blur="guardarLinea(l)"
                      />
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.costo_unit) }}</td>
                    <td v-if="puedeAgregar && l.es_no_previsto" class="t-right">
                      <button class="btn-icon-mini" @click="eliminarLinea(l)" title="Eliminar línea no prevista">
                        <span class="material-icons" style="font-size:14px">delete_outline</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="puedeAgregar" class="op-add-line">
                <button class="op-btn-add" @click="abrirNuevaLinea('material')">+ agregar material no previsto</button>
              </div>
            </div>

            <!-- ── BLOQUE 3: PRODUCTOS ────────────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Artículos producidos</div>
              <div v-if="!ficha.productos.length" class="op-empty">Sin productos</div>
              <table v-else class="op-table">
                <thead><tr>
                  <th>Artículo</th>
                  <th class="t-right">Estimado</th>
                  <th class="t-right">Real</th>
                  <th class="t-right">Precio U</th>
                  <th v-if="puedeAgregar"></th>
                </tr></thead>
                <tbody>
                  <tr v-for="l in ficha.productos" :key="l.id">
                    <td>
                      <span class="text-grey">{{ l.cod_articulo }}</span>
                      <span v-if="l.es_no_previsto" class="badge-no-prev">+</span>
                      <div>{{ l.descripcion }}</div>
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.cantidad_teorica) }} {{ l.unidad }}</td>
                    <td class="t-right">
                      <input
                        type="text" inputmode="decimal"
                        class="op-input-num"
                        :value="formValor(l)"
                        :placeholder="fmtNum(l.cantidad_teorica)"
                        @input="e => borrador[l.id] = e.target.value"
                        @blur="guardarLinea(l)"
                      />
                    </td>
                    <td class="t-right text-grey">{{ fmtNum(l.precio_unit) }}</td>
                    <td v-if="puedeAgregar && l.es_no_previsto" class="t-right">
                      <button class="btn-icon-mini" @click="eliminarLinea(l)" title="Eliminar línea no prevista">
                        <span class="material-icons" style="font-size:14px">delete_outline</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="puedeAgregar" class="op-add-line">
                <button class="op-btn-add" @click="abrirNuevaLinea('producto')">+ agregar producto no previsto</button>
              </div>
            </div>

            <!-- ── BLOQUE 4: TIEMPOS CONSOLIDADOS ─────────────── -->
            <div class="op-section">
              <div class="op-section-title">
                Tiempos consolidados
                <span v-if="ficha.fuente_tiempos === 'snapshot'" class="op-tag">snapshot</span>
                <span v-else class="op-tag op-tag-vivo">en vivo</span>
              </div>
              <div v-if="!ficha.tiempos.length" class="op-empty">Aún no hay tiempos registrados</div>
              <table v-else class="op-table">
                <tbody>
                  <tr v-for="t in ficha.tiempos" :key="t.categoria">
                    <td>{{ t.categoria }}</td>
                    <td class="t-right text-mono">{{ segHHMMSS(t.segundos) }}</td>
                  </tr>
                  <tr class="op-row-total">
                    <td><b>Total</b></td>
                    <td class="t-right text-mono"><b>{{ segHHMMSS(totalSeg) }}</b></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- ── BLOQUE 5: TAREAS VINCULADAS ────────────────── -->
            <div class="op-section">
              <div class="op-section-title">Tareas vinculadas ({{ ficha.tareas_vinculadas.length }})</div>
              <div v-if="!ficha.tareas_vinculadas.length" class="op-empty">Sin tareas asignadas a esta OP</div>
              <ul v-else class="op-tareas">
                <li v-for="t in ficha.tareas_vinculadas" :key="t.id" class="op-tarea" @click="abrirTarea(t)">
                  <div class="op-tarea-row1">
                    <span class="op-tarea-titulo">{{ t.titulo }}</span>
                    <span class="op-tarea-estado" :class="'estado-'+ slug(t.estado)">{{ t.estado }}</span>
                  </div>
                  <div class="op-tarea-row2">
                    <span>{{ t.responsable_nombre || t.responsable || '—' }}</span>
                    <span v-if="t.categoria_produccion_nombre" class="op-tarea-cat">{{ t.categoria_produccion_nombre }}</span>
                    <span class="op-tarea-cron">{{ segHHMMSS(t.duracion_cronometro_seg) }}</span>
                  </div>
                </li>
              </ul>
            </div>

            <!-- ── BLOQUE 6: OBSERVACIONES DEL LOTE ───────────── -->
            <div class="op-section">
              <div class="op-section-title">Observaciones del lote</div>
              <textarea
                class="op-textarea"
                rows="3"
                v-model="obsLote"
                placeholder="Notas, hallazgos, eventos del lote..."
                @blur="guardarObs"
              ></textarea>
            </div>

            <!-- ── BLOQUE 7: ACCIONES ─────────────────────────── -->
            <div class="op-section op-acciones">
              <button
                v-if="puedeProcesar"
                class="btn-procesar"
                :disabled="procesando || estado === 'Procesada' || estado === 'Validado'"
                @click="confirmarProcesar"
              >
                <span class="material-icons" style="font-size:16px">check_circle_outline</span>
                {{ procesando ? 'Procesando...' : 'Procesar' }}
              </button>
              <button
                v-if="puedeValidar"
                class="btn-validar"
                :disabled="validando || estado === 'Validado'"
                @click="confirmarValidar"
              >
                <span class="material-icons" style="font-size:16px">verified</span>
                {{ validando ? 'Validando...' : 'Validar' }}
              </button>
            </div>
          </div>
        </template>
      </aside>
    </div>

    <!-- Diálogo: agregar línea no prevista -->
    <q-dialog v-model="dialogNuevaLinea" persistent>
      <q-card style="min-width:320px">
        <q-card-section><div class="text-h6">Agregar {{ nuevaLinea.tipo }} no previsto</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="nuevaLinea.cod_articulo" label="Código artículo" dense filled />
          <q-input v-model="nuevaLinea.descripcion" label="Descripción" dense filled class="q-mt-sm" />
          <q-input v-model="nuevaLinea.unidad" label="Unidad" dense filled class="q-mt-sm" />
          <q-input v-model="nuevaLinea.cantidad_real" label="Cantidad real" dense filled class="q-mt-sm" inputmode="decimal" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancelar" @click="dialogNuevaLinea = false" />
          <q-btn unelevated label="Agregar" color="primary" :disable="!nuevaLinea.cod_articulo" @click="agregarLineaNoPrevista" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { fmtNum, parseDecimal } from 'src/services/numero'
import { useAuthStore } from 'src/stores/authStore'
import TareaPanel from './TareaPanel.vue'

const $q  = useQuasar()
const auth = useAuthStore()

const props = defineProps({
  idOp:       { type: [String, Number], required: true },
  usuarios:   { type: Array, default: () => [] },
  categorias: { type: Array, default: () => [] },
})
const emit = defineEmits(['cerrar', 'actualizada'])

const ficha       = ref(null)
const cargando    = ref(false)
const obsLote     = ref('')
const borrador    = reactive({})
const tareaAbierta = ref(null)
const procesando  = ref(false)
const validando   = ref(false)
const dialogNuevaLinea = ref(false)
const nuevaLinea = reactive({ tipo: 'material', cod_articulo: '', descripcion: '', unidad: '', cantidad_real: '' })

const miNivel = computed(() => auth.usuario?.nivel || 1)
const puedeProcesar = computed(() => miNivel.value >= 3)
const puedeValidar  = computed(() => miNivel.value >= 5)
const estado = computed(() => ficha.value?.cabecera?.estado || '')
const puedeAgregar = computed(() => estado.value === 'Generada' && miNivel.value >= 3)

const totalSeg = computed(() => (ficha.value?.tiempos || []).reduce((s, t) => s + (Number(t.segundos)||0), 0))

const articuloPrincipal = computed(() => {
  const p = ficha.value?.productos?.[0]
  return p ? p.descripcion : (ficha.value?.materiales?.[0]?.descripcion || '')
})

const estadoClase = computed(() => {
  const e = (estado.value || '').toLowerCase()
  if (e === 'validado')  return 'op-est-val'
  if (e === 'procesada') return 'op-est-proc'
  if (e === 'anulada')   return 'op-est-anul'
  return 'op-est-gen'
})

async function cargar() {
  cargando.value = true
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/ficha`)
    ficha.value = r
    obsLote.value = r.detalle?.observaciones_lote || ''
    Object.keys(borrador).forEach(k => delete borrador[k])
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error cargando OP: ' + (e.message || e), position: 'top' })
  } finally { cargando.value = false }
}

watch(() => props.idOp, cargar)
onMounted(cargar)

function fmtFecha(s) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d)) return String(s)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toTimeString().slice(0, 5)
}
function segHHMMSS(seg) {
  seg = Number(seg) || 0
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  const s = seg % 60
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':')
}
function slug(s) { return String(s || '').toLowerCase().replace(/\s+/g, '-') }
function formValor(l) {
  if (borrador[l.id] !== undefined) return borrador[l.id]
  return l.cantidad_real == null ? '' : fmtNum(l.cantidad_real)
}

async function guardarLinea(l) {
  const raw = borrador[l.id]
  if (raw === undefined) return
  const val = parseDecimal(raw)
  if (val === l.cantidad_real) { delete borrador[l.id]; return }
  try {
    const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas/${l.id}`, {
      method: 'PUT', body: JSON.stringify({ cantidad_real: val })
    })
    l.cantidad_real = r.cantidad_real
    delete borrador[l.id]
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error guardando: ' + (e.message || e), position: 'top' })
  }
}

async function guardarObs() {
  const v = (obsLote.value || '').trim() || null
  const previa = (ficha.value?.detalle?.observaciones_lote || '').trim() || null
  if (v === previa) return
  try {
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/detalle`, {
      method: 'PUT', body: JSON.stringify({ observaciones_lote: v })
    })
    if (ficha.value) {
      if (!ficha.value.detalle) ficha.value.detalle = {}
      ficha.value.detalle.observaciones_lote = v
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Error guardando obs: ' + (e.message || e), position: 'top' })
  }
}

function abrirNuevaLinea(tipo) {
  Object.assign(nuevaLinea, { tipo, cod_articulo: '', descripcion: '', unidad: '', cantidad_real: '' })
  dialogNuevaLinea.value = true
}

async function agregarLineaNoPrevista() {
  try {
    const cant = parseDecimal(nuevaLinea.cantidad_real)
    await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas`, {
      method: 'POST',
      body: JSON.stringify({
        tipo: nuevaLinea.tipo,
        cod_articulo: nuevaLinea.cod_articulo.trim(),
        descripcion: nuevaLinea.descripcion.trim(),
        unidad: nuevaLinea.unidad.trim(),
        cantidad_real: cant
      })
    })
    dialogNuevaLinea.value = false
    await cargar()
    $q.notify({ type: 'positive', message: 'Línea agregada', position: 'top' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.message || 'Error', position: 'top' })
  }
}

async function eliminarLinea(l) {
  $q.dialog({
    title: 'Eliminar línea',
    message: `¿Eliminar ${l.tipo} ${l.cod_articulo} (${l.descripcion})?`,
    cancel: true, persistent: false
  }).onOk(async () => {
    try {
      await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/lineas/${l.id}`, { method: 'DELETE' })
      await cargar()
    } catch (e) {
      $q.notify({ type: 'negative', message: e.message || 'Error', position: 'top' })
    }
  })
}

function abrirTarea(t) { tareaAbierta.value = { ...t } }
function onTareaActualizada(t) {
  if (t && ficha.value) {
    const i = ficha.value.tareas_vinculadas.findIndex(x => x.id === t.id)
    if (i !== -1) ficha.value.tareas_vinculadas[i] = { ...ficha.value.tareas_vinculadas[i], ...t }
  }
  tareaAbierta.value = null
  cargar()
}

function confirmarProcesar() {
  $q.dialog({
    title: 'Procesar OP',
    message: `Cambia el estado de la OP ${props.idOp} a "Procesada" en Effi. Demora ~30-60s.`,
    cancel: true, ok: { label: 'Procesar', color: 'warning' }, persistent: false, dark: true
  }).onOk(async () => {
    procesando.value = true
    try {
      const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/procesar`, { method: 'POST' })
      $q.notify({ type: 'positive', message: `OP ${r.id_op} → Procesada`, position: 'top' })
      await cargar(); emit('actualizada')
    } catch (e) {
      if (e?.retry) {
        setTimeout(confirmarProcesar, 3000)
      } else {
        $q.notify({ type: 'negative', message: e.message || 'Error al procesar', position: 'top', timeout: 6000 })
      }
    } finally { procesando.value = false }
  })
}

function confirmarValidar() {
  $q.dialog({
    title: 'Validar OP',
    message: `Anula la OP ${props.idOp}, crea una nueva con los reales reportados y la marca como "Validado". Demora ~2-3 min.`,
    cancel: 'Cancelar', ok: { label: 'Validar', color: 'positive' }, persistent: true, dark: true
  }).onOk(async () => {
    validando.value = true
    $q.notify({ type: 'info', message: 'Validando OP...', position: 'top', timeout: 0, group: 'op-validar' })
    try {
      const r = await api(`/api/gestion/op/${encodeURIComponent(props.idOp)}/validar`, { method: 'POST' })
      $q.notify({ type: 'positive', message: `OP ${r.id_op_anterior} → Anulada · OP ${r.id_op_nueva} → Validado`, position: 'top', timeout: 6000 })
      emit('actualizada', r.id_op_nueva)
    } catch (e) {
      if (e?.retry) {
        setTimeout(confirmarValidar, 5000)
      } else {
        $q.notify({ type: 'negative', message: e.message || 'Error al validar', position: 'top', timeout: 8000 })
      }
    } finally {
      $q.notify({ group: 'op-validar', message: '', timeout: 1 })
      validando.value = false
    }
  })
}
</script>

<style scoped>
.op-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.45); display: flex; justify-content: flex-end;
}
.op-panel {
  width: 540px; max-width: 100vw; height: 100%;
  background: var(--bg-page); color: var(--text-primary);
  display: flex; flex-direction: column;
  overflow: hidden; box-shadow: -2px 0 16px rgba(0,0,0,0.3);
}
.op-header {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px; border-bottom: 1px solid var(--border-default);
}
.op-header-tipo { font-size: 13px; font-weight: 600; }
.op-loading { padding: 60px 0; text-align: center; }
.op-body {
  flex: 1; overflow-y: auto; padding: 6px 12px 24px;
}
.op-section { padding: 10px 0; border-bottom: 1px solid var(--border-subtle); }
.op-section-title {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
  display: flex; align-items: center; gap: 6px;
}
.op-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-row-hover); color: var(--text-tertiary); font-weight: 500;
}
.op-tag-vivo { background: #2db14a33; color: #2db14a; }
.op-empty { font-size: 11px; color: var(--text-tertiary); font-style: italic; padding: 4px 0; }
.op-cab-row {
  display: flex; align-items: center;
  font-size: 12px; padding: 3px 0;
}
.op-lbl { width: 130px; color: var(--text-tertiary); font-size: 11px; }
.op-val { flex: 1; }

.op-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.op-table thead th {
  text-align: left; font-size: 10px; font-weight: 500;
  color: var(--text-tertiary); padding: 4px 4px;
  border-bottom: 1px solid var(--border-default);
}
.op-table tbody td { padding: 6px 4px; border-bottom: 1px solid var(--border-subtle); vertical-align: top; }
.op-table tbody tr:last-child td { border-bottom: none; }
.t-right { text-align: right; }
.text-mono { font-family: var(--font-mono, monospace); }
.text-grey { color: var(--text-tertiary); font-size: 11px; }
.op-row-total { background: var(--bg-row-hover); }
.op-input-num {
  width: 80px; padding: 4px 6px;
  background: var(--bg-row-hover); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  font-size: 12px; text-align: right;
}
.op-input-num:focus { outline: 2px solid var(--accent); }

.badge-no-prev {
  display: inline-block; margin-left: 4px;
  font-size: 10px; padding: 0 4px; border-radius: 6px;
  background: var(--accent); color: #fff; font-weight: 600;
}

.op-add-line { margin-top: 6px; }
.op-btn-add {
  background: transparent; color: var(--accent);
  border: 1px dashed var(--border-default);
  padding: 4px 10px; border-radius: 4px;
  font-size: 11px; cursor: pointer;
}
.op-btn-add:hover { background: var(--bg-row-hover); }

.op-tareas { list-style: none; margin: 0; padding: 0; }
.op-tarea {
  padding: 6px 8px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--border-subtle); margin-bottom: 4px;
}
.op-tarea:hover { background: var(--bg-row-hover); border-color: var(--border-default); }
.op-tarea-row1 {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-weight: 500;
}
.op-tarea-titulo { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.op-tarea-estado {
  font-size: 10px; padding: 1px 6px; border-radius: 8px;
  background: var(--bg-row-hover); color: var(--text-tertiary); margin-left: 8px;
}
.op-tarea-estado.estado-en-progreso { background: #2196f333; color: #2196f3; }
.op-tarea-estado.estado-completada { background: #2db14a33; color: #2db14a; }
.op-tarea-estado.estado-pendiente { background: #ffa72633; color: #ffa726; }
.op-tarea-row2 {
  display: flex; gap: 10px; font-size: 10px;
  color: var(--text-tertiary); margin-top: 2px;
}
.op-tarea-cat { color: var(--accent); }
.op-tarea-cron { margin-left: auto; font-family: var(--font-mono, monospace); }

.op-textarea {
  width: 100%; min-height: 60px; resize: vertical;
  background: var(--bg-row-hover); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 4px;
  padding: 6px 8px; font-size: 12px; font-family: inherit;
}
.op-textarea:focus { outline: 2px solid var(--accent); }

.op-acciones { display: flex; gap: 8px; padding-top: 12px; border-bottom: none; }
.btn-procesar, .btn-validar {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer;
  font-size: 12px; font-weight: 600;
}
.btn-procesar { background: #ffa726; color: #000; }
.btn-procesar:hover:not(:disabled) { background: #ff9800; }
.btn-validar { background: #2db14a; color: #fff; }
.btn-validar:hover:not(:disabled) { background: #1f8c38; }
.btn-procesar:disabled, .btn-validar:disabled { opacity: 0.4; cursor: not-allowed; }

.op-est-val   { background: #2db14a; color: #fff; }
.op-est-proc  { background: #ffa726; color: #000; }
.op-est-anul  { background: #888;    color: #fff; }
.op-est-gen   { background: #ccc;    color: #000; }

.btn-icon {
  background: transparent; border: none; color: var(--text-secondary);
  padding: 4px; border-radius: 4px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.btn-icon:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.btn-icon-mini {
  background: transparent; border: none; color: var(--text-tertiary);
  padding: 2px; border-radius: 4px; cursor: pointer;
}
.btn-icon-mini:hover { color: var(--negative); }

.op-subtarea-wrap {
  flex: 1; overflow-y: auto;
}

@media (max-width: 768px) {
  .op-panel { width: 100vw; }
}
</style>
