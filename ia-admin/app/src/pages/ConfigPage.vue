<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Configuración</h1>
      <p class="page-subtitle">Parámetros globales del servicio — límites, seguridad y comportamiento</p>
    </div>

    <div class="page-content">

      <!-- Sección Seguridad de tokens -->
      <div class="config-section">
        <div class="section-header">
          <ShieldIcon :size="14" class="section-icon" />
          <span class="section-title">Seguridad de tokens</span>
          <span class="section-desc">Protegen contra gastos accidentales y abusos</span>
        </div>
        <div class="config-table">
          <ConfigRow
            v-for="clave in ORDEN_SEGURIDAD"
            :key="clave"
            :row="byKey[clave]"
            :editando="editando === clave"
            :guardando="guardando === clave"
            @edit="iniciarEdicion(clave)"
            @save="guardar(clave, $event)"
            @cancel="editando = null"
          />
        </div>
      </div>

      <!-- Sección Rate limiting por usuario -->
      <div class="config-section">
        <div class="section-header">
          <ZapIcon :size="14" class="section-icon" />
          <span class="section-title">Rate limiting por usuario</span>
          <span class="section-desc">Máximo de solicitudes permitidas por usuario según ventana de tiempo</span>
        </div>
        <div class="config-table">
          <ConfigRow
            v-for="clave in ORDEN_RATE"
            :key="clave"
            :row="byKey[clave]"
            :editando="editando === clave"
            :guardando="guardando === clave"
            @edit="iniciarEdicion(clave)"
            @save="guardar(clave, $event)"
            @cancel="editando = null"
          />
        </div>
      </div>

      <!-- Sección Circuit breaker -->
      <div class="config-section">
        <div class="section-header">
          <AlertTriangleIcon :size="14" class="section-icon" />
          <span class="section-title">Circuit breaker</span>
          <span class="section-desc">Suspensión automática de un agente si acumula errores consecutivos</span>
        </div>
        <div class="config-table">
          <ConfigRow
            v-for="clave in ORDEN_CIRCUIT"
            :key="clave"
            :row="byKey[clave]"
            :editando="editando === clave"
            :guardando="guardando === clave"
            @edit="iniciarEdicion(clave)"
            @save="guardar(clave, $event)"
            @cancel="editando = null"
          />
        </div>
      </div>

    </div>

    <!-- Toast -->
    <div v-if="toast.visible" class="toast" :class="toast.tipo">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ShieldIcon, ZapIcon, AlertTriangleIcon } from 'lucide-vue-next'
import ConfigRow from 'components/ConfigRow.vue'
import { useAuthStore } from 'stores/authStore'

const auth = useAuthStore()

const ORDEN_SEGURIDAD = ['limite_costo_dia_usd']
const ORDEN_RATE      = ['rate_usuario_rps', 'rate_usuario_rp10s', 'rate_usuario_rpm']
const ORDEN_CIRCUIT   = ['circuit_breaker_errores', 'circuit_breaker_ventana_min']

const LABELS = {
  limite_costo_dia_usd:       { label: 'Límite de costo diario',         unidad: 'USD',      info: 'Si el gasto total del día supera este valor, todas las llamadas a agentes de pago se bloquean. Reinicia a medianoche. Pon 0 para desactivar.' },
  rate_usuario_rps:           { label: 'Máx. solicitudes por segundo',   unidad: 'req/s',    info: 'Máximo de solicitudes que un mismo usuario puede enviar por segundo desde cualquier canal (Telegram, ERP, API).' },
  rate_usuario_rp10s:         { label: 'Máx. solicitudes en 10 segundos',unidad: 'req/10s',  info: 'Máximo acumulado en una ventana deslizante de 10 segundos por usuario.' },
  rate_usuario_rpm:           { label: 'Máx. solicitudes por minuto',    unidad: 'req/min',  info: 'Máximo acumulado en una ventana deslizante de 60 segundos por usuario.' },
  circuit_breaker_errores:    { label: 'Errores para activar el corte',  unidad: 'errores',  info: 'Si un agente acumula este número de errores dentro de la ventana de tiempo, se suspende automáticamente.' },
  circuit_breaker_ventana_min:{ label: 'Ventana del circuit breaker',    unidad: 'minutos',  info: 'Ventana de tiempo en la que se cuentan los errores para activar el circuit breaker.' },
}

const config   = ref([])
const editando = ref(null)
const guardando= ref(null)
const toast    = ref({ visible: false, msg: '', tipo: 'ok' })

const byKey = computed(() => {
  const m = {}
  for (const row of config.value) {
    m[row.clave] = { ...row, ...LABELS[row.clave] }
  }
  return m
})

async function cargar() {
  const r = await fetch('/api/ia/config', { headers: { Authorization: `Bearer ${auth.token}` } })
  const d = await r.json()
  if (d.ok) config.value = d.config
}

function iniciarEdicion(clave) {
  editando.value = clave
}

async function guardar(clave, nuevoValor) {
  guardando.value = clave
  try {
    const r = await fetch(`/api/ia/config/${clave}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${auth.token}` },
      body: JSON.stringify({ valor: nuevoValor }),
    })
    const d = await r.json()
    if (d.ok) {
      const idx = config.value.findIndex(c => c.clave === clave)
      if (idx >= 0) config.value[idx].valor = nuevoValor
      mostrarToast('Guardado', 'ok')
    } else {
      mostrarToast(d.error || 'Error al guardar', 'error')
    }
  } catch {
    mostrarToast('Error de conexión', 'error')
  } finally {
    guardando.value = null
    editando.value  = null
  }
}

function mostrarToast(msg, tipo = 'ok') {
  toast.value = { visible: true, msg, tipo }
  setTimeout(() => { toast.value.visible = false }, 2500)
}

onMounted(cargar)
</script>

<style scoped>
.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-card);
}

.section-icon { opacity: 0.6; color: var(--accent); flex-shrink: 0; }

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 4px;
}

.config-table { padding: 4px 0; }

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  z-index: 9999;
  animation: fadeIn 150ms ease;
}
.toast.ok    { background: var(--color-success-bg); color: var(--color-success); border: 1px solid var(--color-success); }
.toast.error { background: var(--color-error-bg);   color: var(--color-error);   border: 1px solid var(--color-error); }

@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
</style>
