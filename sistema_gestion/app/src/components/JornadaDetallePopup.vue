<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('cerrar')">
      <div class="modal">

        <!-- Header -->
        <div class="modal-header">
          <div class="modal-header-left">
            <span class="modal-title">Jornada</span>
            <span class="modal-fecha">{{ fmtFechaConDia(jornada.fecha) }}</span>
            <span class="badge" :class="badgeClass">{{ estadoLabel }}</span>
          </div>
          <button class="modal-close" @click="$emit('cerrar')">
            <span class="material-icons" style="font-size:18px">close</span>
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">

          <!-- Fila: Usuario + Nombre -->
          <div class="sec">
            <div class="row-2col">
              <div class="field">
                <span class="field-label">Usuario</span>
                <span class="field-val">{{ jornada.usuario }}</span>
              </div>
              <div class="field">
                <span class="field-label">Nombre</span>
                <span class="field-val">{{ jornada.Nombre_Usuario || '—' }}</span>
              </div>
            </div>

            <!-- Fila: Inicio + Fin -->
            <div class="row-2col" style="margin-top:10px">
              <div class="field">
                <span class="field-label">Inicio</span>
                <span v-if="!editando" class="field-val">{{ fmt(jornada.hora_inicio) }}</span>
                <input v-else v-model="editHoraInicio" type="datetime-local" class="field-input" />
                <span class="field-audit">registro: {{ fmt(jornada.hora_inicio_registro) }}</span>
              </div>
              <div class="field">
                <span class="field-label">Fin</span>
                <span v-if="!editando" class="field-val">{{ fmt(jornada.hora_fin) || '—' }}</span>
                <input v-else v-model="editHoraFin" type="datetime-local" class="field-input" />
                <span v-if="jornada.hora_fin_registro" class="field-audit">registro: {{ fmt(jornada.hora_fin_registro) }}</span>
              </div>
            </div>

            <!-- Fila: Tiempos -->
            <div class="row-3col" style="margin-top:10px">
              <div class="field">
                <span class="field-label">T. Laborado</span>
                <span class="field-val td-laborado">{{ formatMins(jornada.tiempo_laborado_min) }}</span>
              </div>
              <div class="field">
                <span class="field-label">T. Total</span>
                <span class="field-val">{{ formatMins(jornada.tiempo_total_min) }}</span>
              </div>
              <div class="field">
                <span class="field-label">T. Pausas</span>
                <span class="field-val td-pausa">{{ formatMins(jornada.tiempo_pausa_min) }}</span>
              </div>
            </div>

            <!-- Observaciones -->
            <div class="field" style="margin-top:10px">
              <span class="field-label">Observaciones</span>
              <span v-if="!editando" class="field-val">{{ jornada.observaciones || '—' }}</span>
              <textarea v-else v-model="editObservaciones" class="field-textarea" rows="2" placeholder="Sin observaciones" />
            </div>
          </div>

          <!-- Sección: Pausas -->
          <div class="sec">
            <div class="sec-label">Pausas ({{ pausas.length }})</div>

            <div v-if="!pausas.length && !mostrarFormPausa && editPausaId === null" class="empty-pausas">Sin pausas registradas</div>

            <!-- Tabla de pausas -->
            <div v-if="pausas.length" class="pausas-scroll">
              <table class="pausas-table">
                <thead>
                  <tr>
                    <th class="pth">Tipo</th>
                    <th class="pth">Inicio</th>
                    <th class="pth">Fin</th>
                    <th class="pth">Duración</th>
                    <th class="pth pth-obs">Obs.</th>
                    <th v-if="esAdmin" class="pth pth-actions"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in pausas" :key="p.id" class="ptr">
                    <td class="ptd">{{ p.tipos_nombre || '—' }}</td>
                    <td class="ptd ptd-mono">{{ fmtHora(p.hora_inicio) }}</td>
                    <td class="ptd ptd-mono">{{ fmtHora(p.hora_fin) || '—' }}</td>
                    <td class="ptd ptd-mono">{{ durPausa(p) }}</td>
                    <td class="ptd pth-obs">{{ p.observaciones || '—' }}</td>
                    <td v-if="esAdmin" class="ptd ptd-actions">
                      <button class="btn-edit-pausa" @click="abrirEditPausa(p)" title="Editar pausa">
                        <span class="material-icons" style="font-size:14px">edit</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Form inline para EDITAR pausa existente -->
            <div v-if="editPausaId !== null" class="nueva-pausa-form">
              <div class="npf-label">Editar pausa</div>
              <div class="npf-chips">
                <button
                  v-for="t in tiposPausa"
                  :key="t.id"
                  class="npf-chip"
                  :class="{ selected: epTipos.includes(t.id) }"
                  @click="toggleEpTipo(t.id)"
                >{{ t.nombre }}</button>
              </div>
              <div v-if="epErrorTipos" class="npf-error">Selecciona al menos un tipo</div>
              <div class="row-2col" style="margin-top:8px">
                <div class="field">
                  <span class="field-label">Hora inicio</span>
                  <input v-model="epHoraInicio" type="time" step="60" class="field-input" />
                  <span class="field-audit">registro: {{ fmt(editPausaRegistroInicio) }}</span>
                </div>
                <div class="field">
                  <span class="field-label">Hora fin</span>
                  <input v-model="epHoraFin" type="time" step="60" class="field-input" />
                  <span v-if="editPausaRegistroFin" class="field-audit">registro: {{ fmt(editPausaRegistroFin) }}</span>
                </div>
              </div>
              <div v-if="epErrorTiempo" class="npf-error">{{ epErrorTiempo }}</div>
              <div class="field" style="margin-top:8px">
                <span class="field-label">Observaciones <span style="color:var(--text-tertiary);font-weight:400">(opcional)</span></span>
                <textarea v-model="epObservaciones" class="field-textarea" rows="1" placeholder="Comentario..." />
              </div>
              <div class="npf-actions">
                <button class="btn-admin btn-cancel" @click="cerrarEditPausa">Cancelar</button>
                <button class="btn-admin btn-guardar" :disabled="guardandoEditPausa" @click="guardarEditPausa">
                  {{ guardandoEditPausa ? 'Guardando...' : 'Guardar' }}
                </button>
              </div>
            </div>

            <!-- Form inline para AÑADIR pausa retroactiva -->
            <div v-if="mostrarFormPausa" class="nueva-pausa-form">
              <div class="npf-label">Nueva pausa</div>
              <div class="npf-chips">
                <button
                  v-for="t in tiposPausa"
                  :key="t.id"
                  class="npf-chip"
                  :class="{ selected: npTipos.includes(t.id) }"
                  @click="toggleNpTipo(t.id)"
                >{{ t.nombre }}</button>
              </div>
              <div v-if="npErrorTipos" class="npf-error">Selecciona al menos un tipo</div>
              <div class="row-2col" style="margin-top:8px">
                <div class="field">
                  <span class="field-label">Hora inicio</span>
                  <input v-model="npHoraInicio" type="time" step="60" class="field-input" />
                </div>
                <div class="field">
                  <span class="field-label">Hora fin</span>
                  <input v-model="npHoraFin" type="time" step="60" class="field-input" />
                </div>
              </div>
              <div v-if="npErrorTiempo" class="npf-error">{{ npErrorTiempo }}</div>
              <div class="field" style="margin-top:8px">
                <span class="field-label">Observaciones <span style="color:var(--text-tertiary);font-weight:400">(opcional)</span></span>
                <textarea v-model="npObservaciones" class="field-textarea" rows="1" placeholder="Comentario..." />
              </div>
              <div class="npf-actions">
                <button class="btn-admin btn-cancel" @click="cerrarFormPausa">Cancelar</button>
                <button class="btn-admin btn-guardar" :disabled="guardandoPausa" @click="guardarNuevaPausa">
                  {{ guardandoPausa ? 'Guardando...' : 'Guardar pausa' }}
                </button>
              </div>
            </div>

            <!-- Botón añadir pausa — DEBAJO de la tabla -->
            <button
              v-if="esAdmin && !mostrarFormPausa && editPausaId === null"
              class="btn-add-pausa"
              @click="abrirNuevaPausa"
            >
              <span class="material-icons" style="font-size:14px">add</span>
              Añadir pausa
            </button>
          </div>

          <!-- Sección: Acciones admin -->
          <div v-if="esAdmin" class="sec sec-admin">
            <div class="sec-label">Administración</div>
            <div class="admin-actions">
              <button v-if="!editando" class="btn-admin" @click="iniciarEdicion">
                <span class="material-icons" style="font-size:15px">edit</span>
                Editar horas y notas
              </button>
              <template v-else>
                <button class="btn-admin btn-guardar" :disabled="guardando" @click="guardar">
                  <span class="material-icons" style="font-size:15px">check</span>
                  {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
                </button>
                <button class="btn-admin btn-cancel" @click="cancelarEdicion">
                  <span class="material-icons" style="font-size:15px">close</span>
                  Cancelar
                </button>
              </template>
              <button
                v-if="puedeReabrir && !editando"
                class="btn-admin btn-reabrir"
                :disabled="reabriendo"
                @click="reabrir"
              >
                <span class="material-icons" style="font-size:15px">lock_open</span>
                {{ reabriendo ? 'Reabriendo...' : 'Reabrir jornada' }}
              </button>
            </div>
            <p v-if="error" class="admin-error">{{ error }}</p>
          </div>

        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  jornada: { type: Object, required: true },
  esAdmin: { type: Boolean, default: false },
})
const emit = defineEmits(['cerrar', 'actualizada'])

const pausas = computed(() => props.jornada.pausas || [])

// Estado
const estadoLabel = computed(() => {
  if (!props.jornada.hora_inicio) return 'Sin jornada'
  if (props.jornada.hora_fin)     return 'Finalizada'
  return 'Activa'
})
const badgeClass = computed(() => {
  if (!props.jornada.hora_inicio) return 'badge-gray'
  if (props.jornada.hora_fin)     return 'badge-blue'
  return 'badge-green'
})

// Reabrir — solo si fue hace menos de 1h
const puedeReabrir = computed(() => {
  if (!props.jornada.hora_fin || !props.jornada.hora_fin_registro) return false
  const ms = Date.now() - new Date(props.jornada.hora_fin_registro).getTime()
  return ms < 60 * 60 * 1000
})

// Edición jornada
const editando          = ref(false)
const editHoraInicio    = ref('')
const editHoraFin       = ref('')
const editObservaciones = ref('')
const guardando         = ref(false)
const reabriendo        = ref(false)
const error             = ref('')

// Nueva pausa
const tiposPausa       = ref([])
const mostrarFormPausa = ref(false)
const npTipos          = ref([])
const npHoraInicio     = ref('')
const npHoraFin        = ref('')
const npObservaciones  = ref('')
const npErrorTipos     = ref(false)
const npErrorTiempo    = ref('')
const guardandoPausa   = ref(false)

// Editar pausa existente
const editPausaId               = ref(null)
const editPausaRegistroInicio   = ref(null)
const editPausaRegistroFin      = ref(null)
const epTipos                   = ref([])
const epHoraInicio              = ref('')
const epHoraFin                 = ref('')
const epObservaciones           = ref('')
const epErrorTipos              = ref(false)
const epErrorTiempo             = ref('')
const guardandoEditPausa        = ref(false)

onMounted(async () => {
  if (props.esAdmin) {
    try {
      const data = await api('/api/gestion/tipos-pausa')
      tiposPausa.value = data.tipos || data || []
    } catch { /* silencio */ }
  }
})

// ── Nueva pausa ──
function toggleNpTipo(id) {
  const idx = npTipos.value.indexOf(id)
  if (idx >= 0) npTipos.value.splice(idx, 1)
  else npTipos.value.push(id)
  npErrorTipos.value = false
}

function abrirNuevaPausa() {
  cerrarEditPausa()
  npTipos.value = []
  npObservaciones.value = ''
  npErrorTipos.value = false
  npErrorTiempo.value = ''
  const ahora = new Date()
  const hace30 = new Date(ahora - 30 * 60000)
  const hace15 = new Date(ahora - 15 * 60000)
  npHoraInicio.value = hace30.toTimeString().slice(0, 5)
  npHoraFin.value    = hace15.toTimeString().slice(0, 5)
  mostrarFormPausa.value = true
}

function cerrarFormPausa() { mostrarFormPausa.value = false }

async function guardarNuevaPausa() {
  if (!npTipos.value.length) { npErrorTipos.value = true; return }
  if (!npHoraInicio.value || !npHoraFin.value) { npErrorTiempo.value = 'Completa los dos horarios'; return }

  const fecha = String(props.jornada.fecha).slice(0, 10)
  const ini = new Date(`${fecha}T${npHoraInicio.value}:00`)
  const fin = new Date(`${fecha}T${npHoraFin.value}:00`)
  if (fin <= ini) { npErrorTiempo.value = 'La hora de fin debe ser después del inicio'; return }

  guardandoPausa.value = true
  npErrorTiempo.value = ''
  try {
    await api(`/api/gestion/jornadas/${props.jornada.id}/pausas/iniciar`, {
      method: 'POST',
      body: JSON.stringify({
        tipos: npTipos.value,
        observaciones: npObservaciones.value.trim() || null,
        hora_inicio: ini.toISOString(),
        hora_fin: fin.toISOString(),
      })
    })
    mostrarFormPausa.value = false
    emit('actualizada')
  } catch (e) {
    npErrorTiempo.value = e.message || 'Error al guardar pausa'
  } finally {
    guardandoPausa.value = false
  }
}

// ── Editar pausa existente ──
function abrirEditPausa(p) {
  cerrarFormPausa()
  editPausaId.value = p.id
  editPausaRegistroInicio.value = p.hora_inicio_registro
  editPausaRegistroFin.value = p.hora_fin_registro

  // Extraer HH:MM de las horas editables
  epHoraInicio.value = p.hora_inicio ? new Date(p.hora_inicio).toTimeString().slice(0, 5) : ''
  epHoraFin.value    = p.hora_fin ? new Date(p.hora_fin).toTimeString().slice(0, 5) : ''
  epObservaciones.value = p.observaciones || ''

  // Resolver tipos seleccionados a partir de nombres
  const nombres = (p.tipos_nombre || '').split(',').map(n => n.trim()).filter(Boolean)
  epTipos.value = tiposPausa.value.filter(t => nombres.includes(t.nombre)).map(t => t.id)

  epErrorTipos.value = false
  epErrorTiempo.value = ''
}

function cerrarEditPausa() {
  editPausaId.value = null
  editPausaRegistroInicio.value = null
  editPausaRegistroFin.value = null
}

function toggleEpTipo(id) {
  const idx = epTipos.value.indexOf(id)
  if (idx >= 0) epTipos.value.splice(idx, 1)
  else epTipos.value.push(id)
  epErrorTipos.value = false
}

async function guardarEditPausa() {
  if (!epTipos.value.length) { epErrorTipos.value = true; return }

  const fecha = String(props.jornada.fecha).slice(0, 10)
  let horaInicioISO = null
  let horaFinISO = null
  if (epHoraInicio.value) horaInicioISO = new Date(`${fecha}T${epHoraInicio.value}:00`).toISOString()
  if (epHoraFin.value) horaFinISO = new Date(`${fecha}T${epHoraFin.value}:00`).toISOString()

  if (horaInicioISO && horaFinISO && new Date(horaFinISO) <= new Date(horaInicioISO)) {
    epErrorTiempo.value = 'La hora de fin debe ser después del inicio'
    return
  }

  guardandoEditPausa.value = true
  epErrorTiempo.value = ''
  try {
    await api(`/api/gestion/jornadas/${props.jornada.id}/pausas/${editPausaId.value}/editar`, {
      method: 'PUT',
      body: JSON.stringify({
        hora_inicio: horaInicioISO,
        hora_fin: horaFinISO,
        observaciones: epObservaciones.value.trim() || null,
        tipos: epTipos.value,
      })
    })
    editPausaId.value = null
    emit('actualizada')
  } catch (e) {
    epErrorTiempo.value = e.message || 'Error al guardar'
  } finally {
    guardandoEditPausa.value = false
  }
}

// ── Edición jornada ──
function toLocalISO(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function iniciarEdicion() {
  editHoraInicio.value    = toLocalISO(props.jornada.hora_inicio)
  editHoraFin.value       = toLocalISO(props.jornada.hora_fin)
  editObservaciones.value = props.jornada.observaciones || ''
  error.value = ''
  editando.value = true
}

function cancelarEdicion() { editando.value = false; error.value = '' }

async function guardar() {
  guardando.value = true
  error.value = ''
  try {
    await api(`/api/gestion/jornadas/${props.jornada.id}/editar-admin`, {
      method: 'PUT',
      body: JSON.stringify({
        hora_inicio:    editHoraInicio.value    || null,
        hora_fin:       editHoraFin.value       || null,
        observaciones:  editObservaciones.value || null,
      })
    })
    editando.value = false
    emit('actualizada')
  } catch (e) {
    error.value = e.message || 'Error al guardar'
  } finally {
    guardando.value = false
  }
}

async function reabrir() {
  reabriendo.value = true
  error.value = ''
  try {
    await api(`/api/gestion/jornadas/${props.jornada.id}/reabrir`, { method: 'PUT' })
    emit('actualizada')
  } catch (e) {
    error.value = e.message || 'Error al reabrir'
  } finally {
    reabriendo.value = false
  }
}

// ── Formateo ──
const DIAS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

function fmtFechaConDia(val) {
  if (!val) return ''
  const s = String(val).slice(0, 10)
  const [y, m, d] = s.split('-')
  const date = new Date(Number(y), Number(m) - 1, Number(d))
  return `${DIAS[date.getDay()]} ${Number(d)} ${MESES[date.getMonth()]} ${y}`
}

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
}
function fmtHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}
function formatMins(mins) {
  if (mins === null || mins === undefined) return '—'
  const m = Math.round(mins); if (!m) return '0m'
  const h = Math.floor(m / 60), r = m % 60
  return h > 0 ? `${h}h${r > 0 ? ' ' + r + 'm' : ''}` : `${m}m`
}
function durPausa(p) {
  if (!p.hora_inicio) return '—'
  const fin = p.hora_fin ? new Date(p.hora_fin) : new Date()
  const min = Math.round((fin - new Date(p.hora_inicio)) / 60000)
  return formatMins(min)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 5000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.modal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%; max-width: 580px;
  max-height: 85vh; display: flex; flex-direction: column;
  animation: modal-in 150ms ease-out;
}
@keyframes modal-in {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to   { opacity: 1; transform: none; }
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.modal-header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.modal-title       { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.modal-fecha       { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.modal-close {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  border: none; background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: background 80ms, color 80ms; flex-shrink: 0;
}
.modal-close:hover { background: var(--bg-card-hover); color: var(--text-primary); }

.modal-body { overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 18px; }

.sec       { display: flex; flex-direction: column; gap: 8px; }
.sec-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-tertiary);
}

/* Grids */
.row-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.row-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }

.field      { display: flex; flex-direction: column; gap: 3px; }
.field-label { font-size: 11px; color: var(--text-tertiary); font-weight: 500; }
.field-val   { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.field-audit { font-size: 10px; color: var(--text-tertiary); margin-top: 1px; }
.field-input {
  height: 28px; padding: 0 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: var(--bg-card-hover);
  color: var(--text-primary); font-size: 12px; font-family: var(--font-sans);
}
.field-input:focus { outline: none; border-color: var(--accent); }
.field-textarea {
  padding: 6px 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-default); background: var(--bg-card-hover);
  color: var(--text-primary); font-size: 12px; font-family: var(--font-sans);
  resize: vertical; min-height: 40px;
}
.field-textarea:focus { outline: none; border-color: var(--accent); }

/* Tabla pausas */
.empty-pausas { font-size: 12px; color: var(--text-tertiary); font-style: italic; }
.pausas-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.pausas-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 400px; }
.pth {
  text-align: left; padding: 4px 8px; height: 28px;
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-tertiary); border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
}
.pth-obs { min-width: 60px; }
.pth-actions { width: 32px; }
.ptd {
  padding: 0 8px; height: 32px; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary); white-space: nowrap;
}
.ptd-mono { font-variant-numeric: tabular-nums; }
.ptd-actions { text-align: center; }
.ptr:last-child .ptd { border-bottom: none; }

/* Botón edit dentro de fila */
.btn-edit-pausa {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: var(--radius-sm);
  border: none; background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: all 80ms; padding: 0;
}
.btn-edit-pausa:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Botón añadir pausa — debajo de la tabla */
.btn-add-pausa {
  display: inline-flex; align-items: center; gap: 4px;
  height: 28px; padding: 0 10px; border-radius: var(--radius-sm);
  border: 1px dashed var(--border-default); background: transparent;
  font-size: 11px; font-weight: 500; color: var(--text-tertiary);
  cursor: pointer; font-family: var(--font-sans); transition: all 80ms;
  margin-top: 6px; align-self: flex-start;
}
.btn-add-pausa:hover { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }

/* Form nueva/editar pausa */
.nueva-pausa-form {
  margin-top: 8px; padding: 12px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  display: flex; flex-direction: column; gap: 6px;
}
.npf-label { font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.npf-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.npf-chip {
  padding: 4px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-default); background: transparent;
  color: var(--text-secondary); font-size: 11px; font-weight: 500;
  cursor: pointer; transition: all 80ms;
}
.npf-chip:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.npf-chip.selected { background: var(--accent-muted); border-color: var(--accent-border); color: var(--accent); }
.npf-error { font-size: 11px; color: var(--color-error, #ef5350); margin-top: 2px; }
.npf-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }

/* Admin */
.sec-admin { background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px; }
.admin-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.btn-admin {
  display: inline-flex; align-items: center; gap: 6px;
  height: 32px; padding: 0 12px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans); transition: all 80ms;
}
.btn-admin:hover:not(:disabled) { background: var(--bg-card-hover); color: var(--text-primary); border-color: var(--border-strong); }
.btn-admin:disabled { opacity: 0.5; cursor: default; }
.btn-guardar { border-color: var(--accent-border); color: var(--accent); background: var(--accent-muted); }
.btn-guardar:hover:not(:disabled) { background: var(--accent); color: #fff; }
.btn-cancel  { border-color: var(--border-default); }
.btn-reabrir { border-color: rgba(99,179,237,0.3); color: #63B3ED; background: rgba(99,179,237,0.08); }
.btn-reabrir:hover:not(:disabled) { background: rgba(99,179,237,0.15); }
.admin-error { font-size: 12px; color: var(--color-error); margin: 6px 0 0; }

/* Badges */
.badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: var(--radius-full); font-weight: 500; }
.badge-green { background: rgba(0,200,83,0.12); color: var(--accent); }
.badge-blue  { background: rgba(99,179,237,0.12); color: #63B3ED; }
.badge-gray  { background: rgba(160,160,160,0.08); color: var(--text-tertiary); }

/* Tiempo */
.td-pausa   { color: var(--color-warning); }
.td-laborado { color: var(--accent); }

@media (max-width: 600px) {
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal { max-height: 95vh; border-radius: var(--radius-lg) var(--radius-lg) 0 0; max-width: 100%; }
  .modal-body { padding: 14px 14px; }
  .row-2col { grid-template-columns: 1fr 1fr; gap: 8px; }
  .row-3col { grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .pausas-scroll { margin: 0 -14px; padding: 0 14px; }
  .nueva-pausa-form { padding: 10px; }
  .npf-chip { padding: 6px 12px; font-size: 12px; }
  .btn-add-pausa { height: 32px; padding: 0 14px; font-size: 12px; }
  .btn-edit-pausa { width: 32px; height: 32px; }
  .btn-edit-pausa .material-icons { font-size: 16px !important; }
}
</style>
