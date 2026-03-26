<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('cerrar')">
      <div class="modal">

        <!-- Header -->
        <div class="modal-header">
          <div class="modal-header-left">
            <span class="modal-title">Detalle Jornada</span>
            <span class="badge" :class="badgeClass">{{ estadoLabel }}</span>
          </div>
          <button class="modal-close" @click="$emit('cerrar')">
            <span class="material-icons" style="font-size:18px">close</span>
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">

          <!-- Sección: Jornada -->
          <div class="sec">
            <div class="sec-label">Jornada</div>
            <div class="fields-grid">
              <div class="field">
                <span class="field-label">Usuario</span>
                <span class="field-val">{{ jornada.Nombre_Usuario || jornada.usuario }}</span>
              </div>
              <div class="field">
                <span class="field-label">Fecha</span>
                <span class="field-val">{{ fmtFecha(jornada.fecha) }}</span>
              </div>
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
              <div class="field">
                <span class="field-label">T. Total</span>
                <span class="field-val">{{ formatMins(jornada.tiempo_total_min) }}</span>
              </div>
              <div class="field">
                <span class="field-label">T. Pausas</span>
                <span class="field-val td-pausa">{{ formatMins(jornada.tiempo_pausa_min) }}</span>
              </div>
              <div class="field">
                <span class="field-label">T. Laborado</span>
                <span class="field-val td-laborado">{{ formatMins(jornada.tiempo_laborado_min) }}</span>
              </div>
            </div>

            <!-- Observaciones -->
            <div class="field field-full" style="margin-top:8px">
              <span class="field-label">Observaciones</span>
              <span v-if="!editando" class="field-val">{{ jornada.observaciones || '—' }}</span>
              <textarea v-else v-model="editObservaciones" class="field-textarea" rows="2" placeholder="Sin observaciones" />
            </div>
          </div>

          <!-- Sección: Pausas -->
          <div class="sec">
            <div class="sec-label">Pausas ({{ pausas.length }})</div>
            <div v-if="!pausas.length" class="empty-pausas">Sin pausas registradas</div>
            <table v-else class="pausas-table">
              <thead>
                <tr>
                  <th class="pth">Tipo</th>
                  <th class="pth">Inicio</th>
                  <th class="pth">Fin</th>
                  <th class="pth">Duración</th>
                  <th class="pth">Observaciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in pausas" :key="p.id" class="ptr">
                  <td class="ptd">{{ p.tipos_nombre || '—' }}</td>
                  <td class="ptd ptd-mono">{{ fmtHora(p.hora_inicio) }}</td>
                  <td class="ptd ptd-mono">{{ fmtHora(p.hora_fin) || '—' }}</td>
                  <td class="ptd ptd-mono">{{ durPausa(p) }}</td>
                  <td class="ptd">{{ p.observaciones || '—' }}</td>
                </tr>
              </tbody>
            </table>
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
import { ref, computed } from 'vue'
import { api } from 'src/services/api'

const props = defineProps({
  jornada: { type: Object, required: true },
  esAdmin: { type: Boolean, default: false },
})
const emit = defineEmits(['cerrar', 'actualizada'])

// Pausas desde la jornada cargada en equipo (viene con pausas incluidas si el endpoint las trae)
// Si no vienen, mostramos vacío
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

// Edición
const editando          = ref(false)
const editHoraInicio    = ref('')
const editHoraFin       = ref('')
const editObservaciones = ref('')
const guardando         = ref(false)
const reabriendo        = ref(false)
const error             = ref('')

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

function fmtFecha(val) {
  if (!val) return '—'
  // fecha puede llegar como '2026-03-26' o '2026-03-26T05:00:00.000Z'
  const s = String(val).slice(0, 10) // tomar solo YYYY-MM-DD
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
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
  width: 100%; max-width: 640px;
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
.modal-header-left { display: flex; align-items: center; gap: 10px; }
.modal-title       { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.modal-close {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  border: none; background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: background 80ms, color 80ms;
}
.modal-close:hover { background: var(--bg-card-hover); color: var(--text-primary); }

.modal-body { overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 20px; }

.sec       { display: flex; flex-direction: column; gap: 10px; }
.sec-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--text-tertiary);
}

.fields-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}
.field      { display: flex; flex-direction: column; gap: 3px; }
.field-full { grid-column: 1 / -1; }
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
  resize: vertical; min-height: 52px;
}
.field-textarea:focus { outline: none; border-color: var(--accent); }

/* Tabla pausas */
.empty-pausas { font-size: 12px; color: var(--text-tertiary); font-style: italic; }
.pausas-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.pth {
  text-align: left; padding: 4px 8px; height: 28px;
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-tertiary); border-bottom: 1px solid var(--border-default);
}
.ptd { padding: 0 8px; height: 32px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); }
.ptd-mono { font-variant-numeric: tabular-nums; }
.ptr:last-child .ptd { border-bottom: none; }

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
  .fields-grid { grid-template-columns: 1fr 1fr; }
  .modal { max-height: 95vh; }
}
</style>
