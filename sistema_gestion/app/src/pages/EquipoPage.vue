<template>
  <div class="equipo-page">

    <!-- Header -->
    <div class="ep-header">
      <div class="ep-title">Equipo</div>
      <div class="ep-date-wrap">
        <span class="material-icons ep-date-icon">calendar_today</span>
        <input type="date" v-model="fechaFiltro" class="ep-date-input" @change="cargarEquipo" />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="ep-loading">
      <span class="material-icons ep-spin">refresh</span>
    </div>

    <!-- Table -->
    <div v-else class="ep-table-wrap">
      <table class="ep-table">
        <thead>
          <tr>
            <th class="ep-th">Usuario</th>
            <th class="ep-th ep-th-center">Inicio</th>
            <th class="ep-th ep-th-center">Fin</th>
            <th class="ep-th ep-th-right">T. Total</th>
            <th class="ep-th ep-th-right">T. Pausas</th>
            <th class="ep-th ep-th-right">T. Laborado</th>
            <th class="ep-th">Estado</th>
            <th v-if="esAdmin" class="ep-th ep-th-action"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!jornadas.length">
            <td :colspan="esAdmin ? 8 : 7" class="ep-empty">Sin registros para esta fecha</td>
          </tr>
          <tr v-for="j in jornadas" :key="j.id || j.usuario" class="ep-row">
            <td class="ep-td ep-td-usuario">
              <span class="ep-nombre">{{ primerNombre(j.Nombre_Usuario) || j.usuario }}</span>
              <span class="ep-email">{{ j.usuario }}</span>
            </td>
            <td class="ep-td ep-td-center ep-hora">{{ formatHora(j.hora_inicio) }}</td>
            <td class="ep-td ep-td-center ep-hora">{{ formatHora(j.hora_fin) }}</td>
            <td class="ep-td ep-td-right ep-mins">{{ formatMins(j.tiempo_total_min) }}</td>
            <td class="ep-td ep-td-right ep-mins ep-mins-pausa">{{ formatMins(j.tiempo_pausa_min) }}</td>
            <td class="ep-td ep-td-right ep-mins ep-mins-laborado">{{ formatMins(j.tiempo_laborado_min) }}</td>
            <td class="ep-td">
              <span class="ep-badge" :class="badgeClass(j)">{{ estadoLabel(j) }}</span>
            </td>
            <td v-if="esAdmin" class="ep-td ep-td-action">
              <button
                v-if="j.hora_fin"
                class="ep-btn-reabrir"
                title="Reabrir jornada"
                @click="reabrir(j)"
              >
                <span class="material-icons" style="font-size:14px">lock_open</span>
              </button>
            </td>
          </tr>
        </tbody>
        <tfoot v-if="jornadas.length > 1">
          <tr class="ep-tfoot-row">
            <td class="ep-td ep-tfoot-label" colspan="3">Totales</td>
            <td class="ep-td ep-td-right ep-mins ep-tfoot-val">{{ formatMins(totales.total) }}</td>
            <td class="ep-td ep-td-right ep-mins ep-mins-pausa ep-tfoot-val">{{ formatMins(totales.pausa) }}</td>
            <td class="ep-td ep-td-right ep-mins ep-mins-laborado ep-tfoot-val">{{ formatMins(totales.laborado) }}</td>
            <td class="ep-td" :colspan="esAdmin ? 2 : 1"></td>
          </tr>
        </tfoot>
      </table>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { useJornadaStore } from 'src/stores/jornadaStore'
import { api } from 'src/services/api'

const auth        = useAuthStore()
const jornadaStore = useJornadaStore()

const fechaFiltro = ref(new Date().toISOString().slice(0, 10))
const jornadas    = ref([])
const cargando    = ref(false)

const esAdmin = computed(() => (auth.usuario?.nivel || 1) >= 7)

const totales = computed(() => ({
  total:    jornadas.value.reduce((s, j) => s + (j.tiempo_total_min    || 0), 0),
  pausa:    jornadas.value.reduce((s, j) => s + (j.tiempo_pausa_min    || 0), 0),
  laborado: jornadas.value.reduce((s, j) => s + (j.tiempo_laborado_min || 0), 0),
}))

onMounted(cargarEquipo)

async function cargarEquipo() {
  cargando.value = true
  try {
    const data = await api(`/api/gestion/jornadas/equipo?fecha=${fechaFiltro.value}`)
    jornadas.value = data.jornadas || []
  } finally {
    cargando.value = false
  }
}

async function reabrir(j) {
  try {
    await api(`/api/gestion/jornadas/${j.id}/reabrir`, { method: 'PUT' })
    await cargarEquipo()
    if (j.usuario === auth.usuario?.email) {
      await jornadaStore.cargarHoy()
    }
  } catch (e) {
    console.error('Error reabriendo jornada:', e)
  }
}

function primerNombre(nombre) {
  if (!nombre) return ''
  return nombre.split(' ')[0]
}

function formatHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}

function formatMins(mins) {
  if (mins === null || mins === undefined) return '—'
  const m = Math.round(mins)
  if (m === 0) return '0m'
  const h  = Math.floor(m / 60)
  const rm = m % 60
  return h > 0 ? `${h}h ${rm > 0 ? rm + 'm' : ''}`.trim() : `${m}m`
}

function estadoLabel(j) {
  if (!j.hora_inicio) return 'Sin jornada'
  if (j.hora_fin)     return 'Finalizada'
  return 'Activa'
}

function badgeClass(j) {
  if (!j.hora_inicio) return 'ep-badge-gray'
  if (j.hora_fin)     return 'ep-badge-blue'
  return 'ep-badge-green'
}
</script>

<style scoped>
.equipo-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ── Header ─────────────────────────────────────────────── */
.ep-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px 12px;
  flex-shrink: 0;
}
.ep-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
.ep-date-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 5px 10px;
}
.ep-date-icon { font-size: 14px; color: var(--text-tertiary); }
.ep-date-input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.ep-date-input:focus { outline: none; }

/* ── Loading ─────────────────────────────────────────────── */
.ep-loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.ep-spin { animation: spin 1s linear infinite; color: var(--text-tertiary); font-size: 22px; }

/* ── Table wrapper ───────────────────────────────────────── */
.ep-table-wrap {
  flex: 1;
  overflow: auto;
  padding: 0 24px 24px;
}

/* ── Table ───────────────────────────────────────────────── */
.ep-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ep-th {
  padding: 7px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: var(--bg-surface, var(--bg-base));
  z-index: 2;
}
.ep-th-center { text-align: center; }
.ep-th-right  { text-align: right; }
.ep-th-action { width: 40px; }

.ep-td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.04));
  color: var(--text-secondary);
  vertical-align: middle;
}
.ep-td-center { text-align: center; }
.ep-td-right  { text-align: right; }
.ep-td-action { text-align: center; width: 40px; }

.ep-row:hover .ep-td { background: var(--bg-row-hover); }

/* ── Columns ─────────────────────────────────────────────── */
.ep-td-usuario {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.ep-nombre {
  font-weight: 500;
  color: var(--text-primary);
}
.ep-email {
  font-size: 11px;
  color: var(--text-tertiary);
}
.ep-hora {
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}
.ep-mins {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}
.ep-mins-pausa    { color: var(--color-warning, #FFB300); }
.ep-mins-laborado { color: var(--accent); }

/* ── Badges ──────────────────────────────────────────────── */
.ep-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 500;
  white-space: nowrap;
}
.ep-badge-green {
  background: rgba(0, 200, 83, 0.12);
  color: var(--accent);
}
.ep-badge-blue {
  background: rgba(99, 179, 237, 0.12);
  color: #63B3ED;
}
.ep-badge-gray {
  background: rgba(160, 160, 160, 0.08);
  color: var(--text-tertiary);
}

/* ── Reabrir button ──────────────────────────────────────── */
.ep-btn-reabrir {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px; height: 26px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background 80ms, color 80ms, border-color 80ms;
}
.ep-btn-reabrir:hover {
  background: var(--bg-row-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
}

/* ── Footer totals ───────────────────────────────────────── */
.ep-tfoot-row .ep-td {
  border-top: 1px solid var(--border-default);
  border-bottom: none;
  background: var(--bg-surface, var(--bg-base));
  font-weight: 600;
}
.ep-tfoot-label {
  color: var(--text-tertiary);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ep-tfoot-val { color: var(--text-secondary); }

/* ── Empty ───────────────────────────────────────────────── */
.ep-empty {
  padding: 40px 12px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  border-bottom: none;
}

/* ── Mobile ──────────────────────────────────────────────── */
@media (max-width: 768px) {
  .ep-header      { padding: 12px 16px 10px; }
  .ep-table-wrap  { padding: 0 16px 16px; }
  .ep-email       { display: none; }
  .ep-th-action, .ep-td-action { display: none; }
}
</style>
