<template>
  <div v-if="auth.estaAutenticado" class="jornada-header">

    <!-- Estado 1: Sin jornada -->
    <template v-if="store.estado === 1">
      <div class="jh-left">
        <span class="jh-fecha">{{ fechaHoy }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-nombre">{{ nombreUsuario }}</span>
      </div>
      <div class="jh-right">
        <button class="jh-btn jh-btn-iniciar" ref="btnIniciar" @click="confirmarIniciar">
          <span class="material-icons" style="font-size:15px">play_arrow</span>
          <span class="jh-btn-label">Iniciar Jornada</span>
        </button>
      </div>
    </template>

    <!-- Estado 2: Trabajando -->
    <template v-else-if="store.estado === 2">
      <div class="jh-left">
        <span class="jh-dot jh-dot-green"></span>
        <span class="jh-nombre">{{ nombreUsuario }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-hora">{{ horaInicio }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-timer">{{ timerFormateado }}</span>
      </div>
      <div class="jh-right">
        <button class="jh-btn jh-btn-ghost" title="Agregar pausa pasada" @click="abrirPausaRetroactiva">
          <span class="material-icons" style="font-size:15px">history</span>
          <span class="jh-btn-label">Pausa pasada</span>
        </button>
        <button class="jh-btn jh-btn-pausa" @click="abrirPausa">
          <span class="material-icons" style="font-size:15px">pause</span>
          <span class="jh-btn-label">Pausa</span>
        </button>
        <button class="jh-btn jh-btn-fin" ref="btnFin" @click="confirmarFinalizar">
          <span class="material-icons" style="font-size:15px">stop</span>
          <span class="jh-btn-label">Fin Jornada</span>
        </button>
      </div>
    </template>

    <!-- Estado 3: En pausa -->
    <template v-else-if="store.estado === 3">
      <div class="jh-left">
        <span class="jh-dot jh-dot-yellow"></span>
        <span class="jh-nombre">{{ nombreUsuario }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-hora">{{ horaInicio }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-pausa-tipo">{{ store.pausaActiva?.tipos_nombre || 'Pausa' }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-timer jh-timer-pausa">{{ timerFormateado }}</span>
      </div>
      <div class="jh-right">
        <button class="jh-btn jh-btn-reanudar" @click="reanudarPausa">
          <span class="material-icons" style="font-size:15px">play_arrow</span>
          <span class="jh-btn-label">Reanudar</span>
        </button>
      </div>
    </template>

    <!-- Estado 0: Jornada finalizada -->
    <template v-else-if="store.estado === 0">
      <div class="jh-left">
        <span class="jh-nombre">{{ nombreUsuario }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-hora">{{ horaInicio }} — {{ horaFin }}</span>
        <span class="jh-completada">Jornada completada</span>
        <span v-if="minutosParaReabrir > 0" class="jh-reabrir-hint">
          Puedes reabrir por {{ minutosParaReabrir }}m más
        </span>
      </div>
      <div class="jh-right">
        <button
          v-if="puedeReabrir"
          class="jh-btn jh-btn-ghost"
          @click="reabrir"
        >
          <span class="material-icons" style="font-size:15px">lock_open</span>
          <span class="jh-btn-label">Reabrir</span>
        </button>
        <button class="jh-btn jh-btn-ghost" title="Agregar pausa pasada" @click="abrirPausaRetroactiva">
          <span class="material-icons" style="font-size:15px">history</span>
          <span class="jh-btn-label">Pausa pasada</span>
        </button>
        <button
          class="jh-btn jh-btn-iniciar"
          :class="{ 'jh-btn-disabled': minutosParaNuevaJornada > 0 }"
          :title="minutosParaNuevaJornada > 0 ? `Disponible en ${labelEsperaJornada}` : 'Iniciar nueva jornada'"
          ref="btnIniciar"
          @click="minutosParaNuevaJornada === 0 && confirmarIniciar()"
        >
          <span class="material-icons" style="font-size:15px">play_arrow</span>
          <span class="jh-btn-label">{{ minutosParaNuevaJornada > 0 ? `en ${labelEsperaJornada}` : 'Nueva Jornada' }}</span>
        </button>
      </div>
    </template>

    <!-- Popover confirmación -->
    <JornadaPopover
      v-if="popover.visible"
      :titulo="popover.titulo"
      :fecha="fechaISO"
      :anchor-el="popover.anchorEl"
      @confirmar="popover.onConfirmar"
      @cancelar="popover.visible = false"
    />

    <!-- Dialog pausa normal -->
    <PausaDialog
      v-model="dialogPausa"
      :tipos="store.tiposPausa"
      :fecha="fechaISO"
      @confirmar="onPausaConfirmada"
    />

    <!-- Dialog pausa retroactiva -->
    <PausaDialog
      v-model="dialogPausaRetro"
      :tipos="store.tiposPausa"
      :fecha="fechaISO"
      :retroactiva="true"
      @confirmar="onPausaRetroConfirmada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { useJornadaStore } from 'src/stores/jornadaStore'
import JornadaPopover from './JornadaPopover.vue'
import PausaDialog from './PausaDialog.vue'

const auth  = useAuthStore()
const store = useJornadaStore()

const btnIniciar = ref(null)
const btnFin     = ref(null)
const dialogPausa     = ref(false)
const dialogPausaRetro = ref(false)

const popover = reactive({
  visible: false, titulo: '', anchorEl: null, onConfirmar: () => {}
})

// Tick reactivo — se actualiza cada segundo para el timer y cada 10s para el countdown
const ahora = ref(Date.now())
let tickInterval = null

onMounted(async () => {
  if (auth.estaAutenticado) {
    await Promise.allSettled([store.cargarHoy(), store.cargarTiposPausa()])
  }
  tickInterval = setInterval(() => { ahora.value = Date.now() }, 1000)
})
onUnmounted(() => { if (tickInterval) clearInterval(tickInterval) })

// ── Computed ─────────────────────────────────────────────────────────
const nombreUsuario = computed(() => {
  const n = auth.usuario?.nombre || ''
  return n.split(' ')[0]
})

const fechaISO = computed(() => new Date().toISOString().slice(0, 10))

const fechaHoy = computed(() => {
  return new Date().toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })
})

const horaInicio = computed(() => {
  if (!store.jornada?.hora_inicio) return ''
  return new Date(store.jornada.hora_inicio).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
})

const horaFin = computed(() => {
  if (!store.jornada?.hora_fin) return ''
  return new Date(store.jornada.hora_fin).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
})

// Timer: segundos laborados (total - pausas cerradas). Se calcula desde jornada directamente,
// sin depender de store.timerSegundos, para evitar el flash inicial de "0m".
const timerLaboradoSeg = computed(() => {
  if (!store.jornada?.hora_inicio) return 0
  const inicio = new Date(store.jornada.hora_inicio).getTime()
  let pausaMs = 0
  for (const p of (store.jornada.pausas || [])) {
    if (p.hora_fin) {
      pausaMs += new Date(p.hora_fin).getTime() - new Date(p.hora_inicio).getTime()
    }
  }
  return Math.max(0, Math.floor((ahora.value - inicio - pausaMs) / 1000))
})

// Timer de pausa activa (cuánto lleva en pausa)
const timerPausaSeg = computed(() => {
  const p = store.pausaActiva
  if (!p?.hora_inicio) return 0
  return Math.max(0, Math.floor((ahora.value - new Date(p.hora_inicio).getTime()) / 1000))
})

function fmtSeg(s) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

// Estado 2: muestra tiempo laborado | Estado 3: muestra tiempo DE la pausa actual
const timerFormateado = computed(() => {
  if (store.estado === 3) return fmtSeg(timerPausaSeg.value)
  return fmtSeg(timerLaboradoSeg.value)
})

const minutosParaReabrir = computed(() => {
  if (!store.jornada?.hora_fin_registro) return 0
  const ms = 60 * 60 * 1000 - (ahora.value - new Date(store.jornada.hora_fin_registro).getTime())
  return ms > 0 ? Math.ceil(ms / 60000) : 0
})

// Minutos restantes para poder abrir una nueva jornada (gap mínimo 6h)
const minutosParaNuevaJornada = computed(() => {
  if (!store.jornada?.hora_fin_registro) return 0
  const ms = 6 * 60 * 60 * 1000 - (ahora.value - new Date(store.jornada.hora_fin_registro).getTime())
  return ms > 0 ? Math.ceil(ms / 60000) : 0
})

const labelEsperaJornada = computed(() => {
  const min = minutosParaNuevaJornada.value
  if (!min) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
})

const puedeReabrir = computed(() => {
  if (store.estado !== 0) return false
  const esAdmin  = (auth.usuario?.nivel || 1) >= 7
  const esDueno  = store.jornada?.usuario === auth.usuario?.email
  return esAdmin || (esDueno && minutosParaReabrir.value > 0)
})

// ── Acciones ─────────────────────────────────────────────────────────
function confirmarIniciar() {
  popover.titulo = 'Iniciar Jornada'
  popover.anchorEl = btnIniciar.value
  popover.onConfirmar = async (horaISO) => {
    popover.visible = false
    await store.iniciarJornada(horaISO)
  }
  popover.visible = true
}

function confirmarFinalizar() {
  popover.titulo = 'Finalizar Jornada'
  popover.anchorEl = btnFin.value
  popover.onConfirmar = async (horaISO) => {
    popover.visible = false
    await store.finalizarJornada(horaISO)
  }
  popover.visible = true
}

function abrirPausa()           { dialogPausa.value = true }
function abrirPausaRetroactiva() { dialogPausaRetro.value = true }

async function onPausaConfirmada({ tipos, observaciones }) {
  await store.iniciarPausa(tipos, observaciones)
}

async function onPausaRetroConfirmada({ tipos, observaciones, hora_inicio, hora_fin }) {
  await store.iniciarPausa(tipos, observaciones, hora_inicio, hora_fin)
}

async function reanudarPausa() {
  if (store.pausaActiva) await store.reanudar(store.pausaActiva.id)
}

async function reabrir() {
  await store.reabrirJornada()
}
</script>

<style scoped>
.jornada-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  height: 40px;
  gap: 12px;
  position: relative;
  flex-shrink: 0;
}

.jh-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 0;
  overflow: hidden;
}

.jh-right {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.jh-fecha    { font-weight: 500; color: var(--text-secondary); text-transform: capitalize; }
.jh-nombre   { font-weight: 500; color: var(--text-primary); white-space: nowrap; }
.jh-sep      { color: var(--text-tertiary); font-size: 10px; }
.jh-hora     { font-variant-numeric: tabular-nums; color: var(--text-secondary); }

.jh-timer {
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-weight: 600;
}
.jh-timer-pausa { color: var(--color-warning, #FFB300); }

.jh-pausa-tipo {
  font-size: 11px; padding: 1px 8px;
  border-radius: var(--radius-full);
  background: rgba(255, 179, 0, 0.12);
  color: var(--color-warning, #FFB300);
  white-space: nowrap;
}
.jh-completada {
  font-size: 11px; padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--accent-muted);
  color: var(--accent);
  white-space: nowrap;
}
.jh-reabrir-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

/* Punto pulsante */
.jh-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.jh-dot-green {
  background: var(--accent);
  animation: pulse-green 2s infinite;
}
.jh-dot-yellow {
  background: var(--color-warning, #FFB300);
  animation: pulse-yellow 2s infinite;
}
@keyframes pulse-green {
  0%   { box-shadow: 0 0 0 0 rgba(0,200,83,0.5); }
  70%  { box-shadow: 0 0 0 6px rgba(0,200,83,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,200,83,0); }
}
@keyframes pulse-yellow {
  0%   { box-shadow: 0 0 0 0 rgba(255,179,0,0.5); }
  70%  { box-shadow: 0 0 0 6px rgba(255,179,0,0); }
  100% { box-shadow: 0 0 0 0 rgba(255,179,0,0); }
}

/* Botones */
.jh-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px; font-weight: 500;
  cursor: pointer;
  transition: background 80ms, color 80ms, border-color 80ms;
  white-space: nowrap;
}
.jh-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }

.jh-btn-iniciar, .jh-btn-reanudar {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.jh-btn-iniciar:hover, .jh-btn-reanudar:hover {
  background: var(--accent-hover); border-color: var(--accent-hover); color: #fff;
}
.jh-btn-iniciar.jh-btn-disabled {
  background: transparent; border-color: var(--border-default);
  color: var(--text-tertiary); cursor: default; opacity: 0.6;
}
.jh-btn-iniciar.jh-btn-disabled:hover { background: transparent; border-color: var(--border-default); color: var(--text-tertiary); }

.jh-btn-fin { border-color: var(--color-error, #ef5350); color: var(--color-error, #ef5350); }
.jh-btn-fin:hover { background: rgba(239,83,80,0.1); }

.jh-btn-ghost { border-color: transparent; color: var(--text-tertiary); }
.jh-btn-ghost:hover { border-color: var(--border-default); color: var(--text-secondary); background: var(--bg-row-hover); }

/* Mobile */
@media (max-width: 768px) {
  .jornada-header { padding: 0 10px; }
  .jh-btn-label   { display: none; }
  .jh-btn         { padding: 5px 7px; }
  .jh-reabrir-hint { display: none; }
}
</style>
