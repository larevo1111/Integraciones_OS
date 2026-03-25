<template>
  <div class="page-wrap">
    <div class="page-content">

      <!-- Tabla card -->
      <div class="os-table-wrapper">

        <!-- Toolbar -->
        <div class="table-toolbar">
          <div class="toolbar-left">
            <span class="table-title">Jornadas del equipo</span>
            <span v-if="!cargando" class="row-count">{{ jornadas.length }}</span>
          </div>
          <div class="toolbar-right">
            <div class="date-wrap">
              <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">calendar_today</span>
              <input type="date" v-model="fechaFiltro" class="date-input" @change="cargarEquipo" />
            </div>
          </div>
        </div>

        <!-- Tabla -->
        <div class="table-scroll">
          <table class="os-table">
            <thead>
              <tr>
                <th class="th">Usuario</th>
                <th class="th th-center">Inicio</th>
                <th class="th th-center">Fin</th>
                <th class="th th-right">T. Total</th>
                <th class="th th-right">T. Pausas</th>
                <th class="th th-right">T. Laborado</th>
                <th class="th">Estado</th>
                <th v-if="esAdmin" class="th th-center" style="width:40px"></th>
              </tr>
            </thead>
            <tbody>
              <!-- Skeleton -->
              <template v-if="cargando">
                <tr v-for="n in 4" :key="n" class="skeleton-row">
                  <td v-for="c in (esAdmin ? 8 : 7)" :key="c" class="td">
                    <div class="skeleton-cell" />
                  </td>
                </tr>
              </template>
              <!-- Datos -->
              <template v-else>
                <tr v-if="!jornadas.length">
                  <td :colspan="esAdmin ? 8 : 7" class="td-empty">Sin registros para esta fecha</td>
                </tr>
                <tr v-for="j in jornadas" :key="j.id || j.usuario" class="data-row">
                  <td class="td">
                    <div class="cell-usuario">
                      <span class="u-nombre">{{ primerNombre(j.Nombre_Usuario) || j.usuario }}</span>
                      <span class="u-email">{{ j.usuario }}</span>
                    </div>
                  </td>
                  <td class="td td-center td-mono">{{ formatHora(j.hora_inicio) }}</td>
                  <td class="td td-center td-mono">{{ formatHora(j.hora_fin) }}</td>
                  <td class="td td-right td-mono">{{ formatMins(j.tiempo_total_min) }}</td>
                  <td class="td td-right td-mono td-pausa">{{ formatMins(j.tiempo_pausa_min) }}</td>
                  <td class="td td-right td-mono td-laborado">{{ formatMins(j.tiempo_laborado_min) }}</td>
                  <td class="td">
                    <span class="badge" :class="badgeClass(j)">{{ estadoLabel(j) }}</span>
                  </td>
                  <td v-if="esAdmin" class="td td-center">
                    <button v-if="j.hora_fin" class="btn-reabrir" title="Reabrir jornada" @click="reabrir(j)">
                      <span class="material-icons" style="font-size:13px">lock_open</span>
                    </button>
                  </td>
                </tr>
              </template>
            </tbody>
            <!-- Totales -->
            <tfoot v-if="jornadas.length > 1">
              <tr class="tfoot-row">
                <td class="td tf-label" colspan="3">Totales</td>
                <td class="td td-right td-mono tf-val">{{ formatMins(totales.total) }}</td>
                <td class="td td-right td-mono td-pausa tf-val">{{ formatMins(totales.pausa) }}</td>
                <td class="td td-right td-mono td-laborado tf-val">{{ formatMins(totales.laborado) }}</td>
                <td class="td" :colspan="esAdmin ? 2 : 1"></td>
              </tr>
            </tfoot>
          </table>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { useJornadaStore } from 'src/stores/jornadaStore'
import { api } from 'src/services/api'

const auth         = useAuthStore()
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
    if (j.usuario === auth.usuario?.email) await jornadaStore.cargarHoy()
  } catch (e) { console.error('Error reabriendo jornada:', e) }
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
  return h > 0 ? `${h}h${rm > 0 ? ' ' + rm + 'm' : ''}` : `${m}m`
}

function estadoLabel(j) {
  if (!j.hora_inicio) return 'Sin jornada'
  if (j.hora_fin)     return 'Finalizada'
  return 'Activa'
}

function badgeClass(j) {
  if (!j.hora_inicio) return 'badge-gray'
  if (j.hora_fin)     return 'badge-blue'
  return 'badge-green'
}
</script>

<style scoped>
/* ── Layout ── */
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
.page-content { padding: 20px 24px; }

/* ── Card ── */
.os-table-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  position: relative;
}

/* ── Toolbar ── */
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-toolbar, var(--bg-card));
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.toolbar-left  { display: flex; align-items: center; gap: 8px; }
.table-title   { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.row-count {
  font-size: 11px; font-weight: 500;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.06);
  padding: 1px 7px; border-radius: var(--radius-full);
}
.toolbar-right { display: flex; align-items: center; gap: 4px; }
.date-wrap {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: transparent;
}
.date-input {
  background: transparent; border: none;
  color: var(--text-secondary);
  font-size: 12px; font-weight: 500;
  cursor: pointer; font-family: inherit;
}
.date-input:focus { outline: none; }

/* ── Tabla ── */
.table-scroll { overflow-x: auto; }
.os-table     { width: 100%; border-collapse: collapse; font-size: 13px; }

.th {
  text-align: left; padding: 0 12px;
  height: 36px;
  font-size: 11px; font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  white-space: nowrap;
  position: sticky; top: 0; z-index: 5;
  user-select: none;
}
.th-center { text-align: center; }
.th-right  { text-align: right; }

.td {
  padding: 0 12px;
  height: 36px;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.04));
  color: var(--text-secondary);
  vertical-align: middle;
  white-space: nowrap;
}
.td-center { text-align: center; }
.td-right  { text-align: right; }
.td-mono   { font-variant-numeric: tabular-nums; }
.td-pausa    { color: var(--color-warning, #FFB300); font-weight: 500; }
.td-laborado { color: var(--accent); font-weight: 500; }

.data-row { cursor: default; transition: background 60ms; }
.data-row:hover .td { background: var(--bg-row-hover); }

/* Columna usuario */
.cell-usuario { display: flex; flex-direction: column; gap: 1px; line-height: 1.2; }
.u-nombre     { font-weight: 500; color: var(--text-primary); }
.u-email      { font-size: 11px; color: var(--text-tertiary); }

/* Badges */
.badge {
  display: inline-block; font-size: 11px; padding: 2px 8px;
  border-radius: var(--radius-full); font-weight: 500; white-space: nowrap;
}
.badge-green { background: rgba(0,200,83,0.12); color: var(--accent); }
.badge-blue  { background: rgba(99,179,237,0.12); color: #63B3ED; }
.badge-gray  { background: rgba(160,160,160,0.08); color: var(--text-tertiary); }

/* Botón reabrir */
.btn-reabrir {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: background 80ms, color 80ms, border-color 80ms;
}
.btn-reabrir:hover {
  background: var(--bg-row-hover); border-color: var(--border-default); color: var(--text-primary);
}

/* Skeleton */
.skeleton-row .td { border-bottom: 1px solid var(--border-subtle); }
.skeleton-cell {
  height: 14px; border-radius: 4px;
  background: var(--border-subtle, rgba(255,255,255,0.06));
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0%,100% { opacity: 0.4; }
  50%      { opacity: 0.9; }
}

/* Empty */
.td-empty {
  height: 80px; text-align: center;
  color: var(--text-tertiary); font-size: 13px;
  border-bottom: none;
}

/* Totales */
.tfoot-row .td {
  border-top: 1px solid var(--border-default);
  border-bottom: none;
  background: var(--bg-card);
  font-weight: 600;
}
.tf-label {
  color: var(--text-tertiary); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.tf-val { color: var(--text-secondary); }

/* Mobile */
@media (max-width: 768px) {
  .page-content { padding: 12px 16px; }
  .u-email { display: none; }
}
</style>
