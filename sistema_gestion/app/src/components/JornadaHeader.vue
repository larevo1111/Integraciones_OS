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
          <span class="material-icons" style="font-size:16px">play_arrow</span>
          <span class="jh-btn-label">Iniciar Jornada</span>
        </button>
      </div>
    </template>

    <!-- Estado 2: Trabajando -->
    <template v-else-if="store.estado === 2">
      <div class="jh-left">
        <span class="jh-dot jh-dot-green"></span>
        <span class="jh-hora">{{ horaInicio }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-timer">{{ timerFormateado }}</span>
      </div>
      <div class="jh-right">
        <button class="jh-btn jh-btn-pausa" @click="abrirPausa">
          <span class="material-icons" style="font-size:16px">pause</span>
          <span class="jh-btn-label">Pausa</span>
        </button>
        <button class="jh-btn jh-btn-fin" ref="btnFin" @click="confirmarFinalizar">
          <span class="material-icons" style="font-size:16px">stop</span>
          <span class="jh-btn-label">Fin Jornada</span>
        </button>
      </div>
    </template>

    <!-- Estado 3: En pausa -->
    <template v-else-if="store.estado === 3">
      <div class="jh-left">
        <span class="jh-dot jh-dot-yellow"></span>
        <span class="jh-hora">{{ horaInicio }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-timer jh-timer-pausa">{{ timerFormateado }}</span>
        <span class="jh-pausa-tipo">{{ store.pausaActiva?.tipos_nombre || 'Pausa' }}</span>
      </div>
      <div class="jh-right">
        <button class="jh-btn jh-btn-reanudar" @click="reanudarPausa">
          <span class="material-icons" style="font-size:16px">play_arrow</span>
          <span class="jh-btn-label">Reanudar</span>
        </button>
      </div>
    </template>

    <!-- Estado 0: Jornada finalizada -->
    <template v-else-if="store.estado === 0">
      <div class="jh-left">
        <span class="jh-fecha">{{ fechaHoy }}</span>
        <span class="jh-sep">&middot;</span>
        <span class="jh-hora">{{ horaInicio }} — {{ horaFin }}</span>
        <span class="jh-completada">Jornada completada</span>
      </div>
    </template>

    <!-- Popover confirmación -->
    <JornadaPopover
      v-if="popover.visible"
      :titulo="popover.titulo"
      :hora="popover.hora"
      :anchor-el="popover.anchorEl"
      @confirmar="popover.onConfirmar"
      @cancelar="popover.visible = false"
    />

    <!-- Dialog pausa -->
    <PausaDialog
      v-model="dialogPausa"
      :tipos="store.tiposPausa"
      @confirmar="onPausaConfirmada"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { useJornadaStore } from 'src/stores/jornadaStore'
import JornadaPopover from './JornadaPopover.vue'
import PausaDialog from './PausaDialog.vue'

const auth = useAuthStore()
const store = useJornadaStore()

const btnIniciar = ref(null)
const btnFin = ref(null)
const dialogPausa = ref(false)

const popover = reactive({
  visible: false,
  titulo: '',
  hora: '',
  anchorEl: null,
  onConfirmar: () => {}
})

const nombreUsuario = computed(() => {
  const n = auth.usuario?.nombre || ''
  return n.split(' ')[0] // solo primer nombre
})

const fechaHoy = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })
})

const horaInicio = computed(() => {
  if (!store.jornada?.hora_inicio) return ''
  return new Date(store.jornada.hora_inicio).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
})

const horaFin = computed(() => {
  if (!store.jornada?.hora_fin) return ''
  return new Date(store.jornada.hora_fin).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
})

const timerFormateado = computed(() => {
  const s = store.timerSegundos
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
})

function horaActual() {
  return new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function confirmarIniciar() {
  popover.titulo = 'Iniciar Jornada'
  popover.hora = horaActual()
  popover.anchorEl = btnIniciar.value
  popover.onConfirmar = async () => {
    popover.visible = false
    await store.iniciarJornada()
  }
  popover.visible = true
}

function confirmarFinalizar() {
  popover.titulo = 'Finalizar Jornada'
  popover.hora = horaActual()
  popover.anchorEl = btnFin.value
  popover.onConfirmar = async () => {
    popover.visible = false
    await store.finalizarJornada()
  }
  popover.visible = true
}

function abrirPausa() {
  dialogPausa.value = true
}

async function onPausaConfirmada({ tipos, observaciones }) {
  await store.iniciarPausa(tipos, observaciones)
}

async function reanudarPausa() {
  if (store.pausaActiva) {
    await store.reanudar(store.pausaActiva.id)
  }
}

onMounted(async () => {
  if (auth.estaAutenticado) {
    await Promise.allSettled([
      store.cargarHoy(),
      store.cargarTiposPausa()
    ])
  }
})
</script>

<style scoped>
.jornada-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  min-height: 40px;
  gap: 12px;
  position: relative;
}

.jh-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 0;
  flex-wrap: wrap;
}

.jh-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.jh-fecha { font-weight: 500; color: var(--text-primary); text-transform: capitalize; }
.jh-nombre { color: var(--text-tertiary); }
.jh-sep { color: var(--text-tertiary); font-size: 11px; }
.jh-hora { font-variant-numeric: tabular-nums; color: var(--text-primary); font-weight: 500; }

.jh-timer {
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-weight: 600;
}
.jh-timer-pausa { color: var(--color-warning, #FFB300); }

.jh-pausa-tipo {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: rgba(255, 179, 0, 0.12);
  color: var(--color-warning, #FFB300);
  white-space: nowrap;
}

.jh-completada {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--accent-muted);
  color: var(--accent);
  white-space: nowrap;
}

/* Punto pulsante */
.jh-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.jh-dot-green {
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(0, 200, 83, 0.5);
  animation: pulse-green 2s infinite;
}
.jh-dot-yellow {
  background: var(--color-warning, #FFB300);
  box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.5);
  animation: pulse-yellow 2s infinite;
}

@keyframes pulse-green {
  0% { box-shadow: 0 0 0 0 rgba(0, 200, 83, 0.5); }
  70% { box-shadow: 0 0 0 6px rgba(0, 200, 83, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 200, 83, 0); }
}
@keyframes pulse-yellow {
  0% { box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.5); }
  70% { box-shadow: 0 0 0 6px rgba(255, 179, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 179, 0, 0); }
}

/* Botones */
.jh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 80ms, color 80ms, border-color 80ms;
  white-space: nowrap;
}
.jh-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }

.jh-btn-iniciar {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.jh-btn-iniciar:hover { background: var(--accent-hover); border-color: var(--accent-hover); color: #fff; }

.jh-btn-reanudar {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.jh-btn-reanudar:hover { background: var(--accent-hover); border-color: var(--accent-hover); color: #fff; }

.jh-btn-fin { border-color: var(--color-error, #ef5350); color: var(--color-error, #ef5350); }
.jh-btn-fin:hover { background: rgba(239, 83, 80, 0.1); }

/* Mobile */
@media (max-width: 768px) {
  .jornada-header { padding: 6px 12px; }
  .jh-btn-label { display: none; }
  .jh-btn { padding: 6px 8px; }
  .jh-nombre { display: none; }
}
</style>
