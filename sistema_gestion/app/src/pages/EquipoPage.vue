<template>
  <div class="page-wrap">
    <div class="page-content">
      <GestionTable
        title="Jornadas"
        :rows="jornadasMapeadas"
        :columns="columnas"
        :loading="cargando"
        @row-click="abrirDetalle"
      >
        <template #toolbar>
          <!-- Preset Hoy -->
          <button class="toolbar-btn" :class="{ 'toolbar-btn-active': esHoy }" @click.stop="setHoy">Hoy</button>
          <!-- Desde / Hasta -->
          <div class="date-wrap">
            <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">calendar_today</span>
            <input type="date" v-model="desde" class="date-input" @change="cargarEquipo" />
          </div>
          <span style="color:var(--text-tertiary);font-size:12px">—</span>
          <div class="date-wrap">
            <input type="date" v-model="hasta" class="date-input" @change="cargarEquipo" />
          </div>
        </template>

        <!-- Cell renderers personalizados -->
        <template #cell-usuario="{ row }">
          <div class="cell-usuario">
            <span class="u-nombre">{{ primerNombre(row.Nombre_Usuario) || row.usuario }}</span>
            <span class="u-email">{{ row.usuario }}</span>
          </div>
        </template>
        <template #cell-fecha="{ row }">
          <span class="td-mono">{{ row.fecha }}</span>
        </template>
        <template #cell-hora_inicio="{ row }">
          <span class="td-mono">{{ formatHora(row.hora_inicio) }}</span>
        </template>
        <template #cell-hora_fin="{ row }">
          <span class="td-mono">{{ formatHora(row.hora_fin) }}</span>
        </template>
        <template #cell-tiempo_total_min="{ row }">
          <span class="td-mono">{{ formatMins(row.tiempo_total_min) }}</span>
        </template>
        <template #cell-tiempo_pausa_min="{ row }">
          <span class="td-mono td-pausa">{{ formatMins(row.tiempo_pausa_min) }}</span>
        </template>
        <template #cell-tiempo_laborado_min="{ row }">
          <span class="td-mono td-laborado">{{ formatMins(row.tiempo_laborado_min) }}</span>
        </template>
        <template #cell-estado="{ row }">
          <span class="badge" :class="badgeClass(row)">{{ estadoLabel(row) }}</span>
        </template>
      </GestionTable>
    </div>

    <!-- Popup de detalle -->
    <JornadaDetallePopup
      v-if="jornadaSel"
      :jornada="jornadaSel"
      :es-admin="esAdmin"
      @cerrar="jornadaSel = null"
      @actualizada="onJornadaActualizada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { useJornadaStore } from 'src/stores/jornadaStore'
import { api } from 'src/services/api'
import GestionTable from 'src/components/GestionTable.vue'
import JornadaDetallePopup from 'src/components/JornadaDetallePopup.vue'

const auth         = useAuthStore()
const jornadaStore = useJornadaStore()

const hoy   = new Date().toISOString().slice(0, 10)
const desde = ref(hoy)
const hasta = ref(hoy)

const jornadas  = ref([])
const cargando  = ref(false)
const jornadaSel = ref(null)

const esAdmin = computed(() => (auth.usuario?.nivel || 1) >= 7)
const esHoy   = computed(() => desde.value === hoy && hasta.value === hoy)

const columnas = [
  { key: 'usuario',            label: 'Usuario',     visible: true  },
  { key: 'fecha',              label: 'Fecha',       visible: false },
  { key: 'hora_inicio',        label: 'Inicio',      visible: true  },
  { key: 'hora_fin',           label: 'Fin',         visible: true  },
  { key: 'tiempo_total_min',   label: 'T. Total',    visible: true  },
  { key: 'tiempo_pausa_min',   label: 'T. Pausas',   visible: true  },
  { key: 'tiempo_laborado_min',label: 'T. Laborado', visible: true  },
  { key: 'estado',             label: 'Estado',      visible: true  },
  { key: 'num_pausas',         label: 'Pausas',      visible: false },
]

// Jornadas con campo "usuario" como nombre para filtro por columna
const jornadasMapeadas = computed(() => jornadas.value.map(j => ({
  ...j,
  _nombre_display: j.Nombre_Usuario ? primerNombre(j.Nombre_Usuario) : j.usuario,
})))

onMounted(cargarEquipo)

function setHoy() {
  desde.value = hoy
  hasta.value = hoy
  cargarEquipo()
}

async function cargarEquipo() {
  cargando.value = true
  try {
    const data = await api(`/api/gestion/jornadas/equipo?desde=${desde.value}&hasta=${hasta.value}`)
    jornadas.value = data.jornadas || []
  } finally {
    cargando.value = false
  }
}

function abrirDetalle(jornada) {
  jornadaSel.value = jornada
}

async function onJornadaActualizada() {
  await cargarEquipo()
  if (jornadaSel.value?.usuario === auth.usuario?.email) {
    await jornadaStore.cargarHoy()
  }
  jornadaSel.value = null
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
  if (!m) return '0m'
  const h = Math.floor(m / 60), r = m % 60
  return h > 0 ? `${h}h${r > 0 ? ' ' + r + 'm' : ''}` : `${m}m`
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
.page-wrap    { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-app); }
.page-content { padding: 20px 24px; }

/* Toolbar extras */
.toolbar-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans); white-space: nowrap;
  transition: background 80ms, color 80ms;
}
.toolbar-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.toolbar-btn-active { background: var(--accent-muted) !important; border-color: var(--accent-border) !important; color: var(--accent) !important; }
.date-wrap {
  display: inline-flex; align-items: center; gap: 5px;
  height: 28px; padding: 0 10px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: transparent;
}
.date-input {
  background: transparent; border: none; color: var(--text-secondary);
  font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit;
}
.date-input:focus { outline: none; }

/* Cell renderers */
.cell-usuario { display: flex; flex-direction: column; gap: 1px; line-height: 1.2; }
.u-nombre     { font-weight: 500; color: var(--text-primary); }
.u-email      { font-size: 11px; color: var(--text-tertiary); }
.td-mono      { font-variant-numeric: tabular-nums; }
.td-pausa     { color: var(--color-warning); font-weight: 500; }
.td-laborado  { color: var(--accent); font-weight: 500; }
.badge {
  display: inline-block; font-size: 11px; padding: 2px 8px;
  border-radius: var(--radius-full); font-weight: 500; white-space: nowrap;
}
.badge-green { background: rgba(0,200,83,0.12); color: var(--accent); }
.badge-blue  { background: rgba(99,179,237,0.12); color: #63B3ED; }
.badge-gray  { background: rgba(160,160,160,0.08); color: var(--text-tertiary); }

@media (max-width: 768px) {
  .page-content { padding: 12px 16px; }
  .u-email { display: none; }
}
</style>
