<template>
  <div class="page-wrap">
    <div class="page-content">

      <!-- Barra de filtros (chips) -->
      <div class="filtros-bar-wrap">
        <div class="filtros-bar">
          <button
            v-for="f in FILTROS"
            :key="f.key"
            class="chip"
            :class="{ active: filtroActivo === f.key }"
            @click="onFiltroClick(f.key)"
          >{{ f.label }}</button>

        </div>
      </div>

      <GestionTable
        title="Jornadas"
        :rows="jornadasFiltradas"
        :columns="columnasComputed"
        :loading="cargando"
        @row-click="abrirDetalle"
      >
        <template #toolbar>
          <div class="date-wrap">
            <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">calendar_today</span>
            <input type="date" v-model="desde" class="date-input" @change="onFechaManual" />
          </div>
          <span style="color:var(--text-tertiary);font-size:12px">—</span>
          <div class="date-wrap">
            <input type="date" v-model="hasta" class="date-input" @change="onFechaManual" />
          </div>
        </template>

        <!-- Cell renderers personalizados -->
        <template #cell-_nombre="{ row }">
          <div class="cell-usuario">
            <span class="u-nombre">{{ row._nombre }}</span>
            <span class="u-email">{{ row.usuario }}</span>
          </div>
        </template>
        <template #cell-fecha="{ row }">
          <span class="td-mono">{{ fmtFecha(row.fecha) }}</span>
        </template>
        <template #cell-hora_inicio="{ row }">
          <span class="td-mono">{{ formatHora(row.hora_inicio) }}</span>
        </template>
        <template #cell-hora_fin="{ row }">
          <span class="td-mono">{{ formatHora(row.hora_fin) }}</span>
        </template>
        <template #cell-tiempo_total_usr="{ row }">
          <span class="td-mono">{{ formatMins(row.tiempo_total_usr) }}</span>
        </template>
        <template #cell-tiempo_pausa_usr="{ row }">
          <span class="td-mono td-pausa">{{ formatMins(row.tiempo_pausa_usr) }}</span>
        </template>
        <template #cell-tiempo_laborado_usr="{ row }">
          <span class="td-mono td-laborado">{{ formatMins(row.tiempo_laborado_usr) }}</span>
        </template>
        <template #cell-tiempo_total_sys="{ row }">
          <span class="td-mono">{{ formatMins(row.tiempo_total_sys) }}</span>
        </template>
        <template #cell-tiempo_pausa_sys="{ row }">
          <span class="td-mono td-pausa">{{ formatMins(row.tiempo_pausa_sys) }}</span>
        </template>
        <template #cell-tiempo_laborado_sys="{ row }">
          <span class="td-mono td-laborado">{{ formatMins(row.tiempo_laborado_sys) }}</span>
        </template>
        <template #cell-estado="{ row }">
          <span class="badge" :class="badgeClass(row)">{{ estadoLabel(row) }}</span>
        </template>
        <template #cell-tareas_count="{ row }">
          <span class="td-mono">{{ row.tareas_count || 0 }}</span>
        </template>
        <template #cell-dur_tareas_real="{ row }">
          <span class="td-mono">{{ formatMins(row.dur_tareas_real) }}</span>
        </template>
        <template #cell-dur_tareas_crono="{ row }">
          <span class="td-mono">{{ formatMins(row.dur_tareas_crono) }}</span>
        </template>
        <template #cell-dur_tareas_usuario="{ row }">
          <span class="td-mono">{{ formatMins(row.dur_tareas_usuario) }}</span>
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
import { hoyLocal, localISO } from 'src/services/fecha'
import GestionTable from 'src/components/GestionTable.vue'
import JornadaDetallePopup from 'src/components/JornadaDetallePopup.vue'

const auth         = useAuthStore()
const jornadaStore = useJornadaStore()

// ── Filtros de tiempo ────────────────────────────────────
const hoy = hoyLocal()
const desde = ref(hoy)
const hasta = ref(hoy)
const filtroActivo = ref('hoy')

const FILTROS = [
  { key: 'hoy',    label: 'Hoy' },
  { key: 'semana', label: 'Esta semana' },
  { key: 'mes',    label: 'Este mes' },
]

function calcRango(key) {
  const d = new Date()
  if (key === 'hoy') {
    return { d: hoy, h: hoy }
  } else if (key === 'semana') {
    const dow = d.getDay() === 0 ? 6 : d.getDay() - 1 // lunes=0
    const lun = new Date(d); lun.setDate(d.getDate() - dow)
    const dom = new Date(lun); dom.setDate(lun.getDate() + 6)
    return { d: localISO(lun), h: localISO(dom) }
  } else if (key === 'mes') {
    const primero = new Date(d.getFullYear(), d.getMonth(), 1)
    const ultimo  = new Date(d.getFullYear(), d.getMonth() + 1, 0)
    return { d: localISO(primero), h: localISO(ultimo) }
  }
  return { d: hoy, h: hoy }
}

function onFiltroClick(key) {
  filtroActivo.value = key
  const r = calcRango(key)
  desde.value = r.d
  hasta.value = r.h
  cargarEquipo()
}

function onFechaManual() {
  filtroActivo.value = null
  cargarEquipo()
}

// ── Datos ────────────────────────────────────────────────
const jornadas   = ref([])
const cargando   = ref(false)
const jornadaSel = ref(null)

const esAdmin = computed(() => (auth.usuario?.nivel || 1) >= 7)

const columnas = [
  { key: '_nombre',             label: 'Usuario',        visible: true,  filterType: 'select' },
  { key: 'fecha',              label: 'Fecha',          visible: false },
  { key: 'hora_inicio',        label: 'Inicio',         visible: true,  width: '120px' },
  { key: 'hora_fin',           label: 'Fin',            visible: true,  width: '120px' },
  { key: 'tiempo_total_usr',    label: 'T. Total (usr)',    visible: true  },
  { key: 'tiempo_pausa_usr',   label: 'T. Pausas (usr)',   visible: true  },
  { key: 'tiempo_laborado_usr',label: 'T. Laborado (usr)', visible: true  },
  { key: 'tiempo_total_sys',    label: 'T. Total (sys)',    visible: false },
  { key: 'tiempo_pausa_sys',   label: 'T. Pausas (sys)',   visible: false },
  { key: 'tiempo_laborado_sys',label: 'T. Laborado (sys)', visible: false },
  { key: 'estado',             label: 'Estado',          visible: true,  filterType: 'select' },
  { key: 'tareas_count',       label: 'Tareas',          visible: true  },
  { key: 'dur_tareas_real',    label: 'Dur. sistema',     visible: true,  hint: 'Duración Sistema: tiempo entre inicio y fin real de cada tarea (calculado automáticamente)' },
  { key: 'dur_tareas_crono',   label: 'Dur. cronómetro',  visible: false, hint: 'Duración Cronómetro: tiempo acumulado del cronómetro que cada persona activó manualmente' },
  { key: 'dur_tareas_usuario', label: 'Dur. usuario',     visible: false, hint: 'Duración Usuario: tiempo que la persona reportó manualmente al completar la tarea' },
  { key: 'num_pausas',         label: 'Pausas',          visible: false },
]

// Cuando el rango es > 1 día, mostrar columna fecha
const columnasComputed = computed(() => {
  const multi = desde.value !== hasta.value
  return columnas.map(c => c.key === 'fecha' ? { ...c, visible: multi } : c)
})

const jornadasFiltradas = computed(() => {
  return jornadas.value.map(j => ({
    ...j,
    _nombre: j.Nombre_Usuario ? primerNombre(j.Nombre_Usuario) : j.usuario,
  }))
})

onMounted(() => { cargarEquipo() })

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
function fmtFecha(val) {
  if (!val) return '—'
  const s = String(val).slice(0, 10)
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
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
.page-content { padding: 0; display: flex; flex-direction: column; }

/* Toolbar extras (date inputs dentro de GestionTable) */
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
  .u-email { display: none; }
}
</style>
