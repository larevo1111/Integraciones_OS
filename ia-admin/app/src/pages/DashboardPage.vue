<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-subtitle">Hola, {{ usuario?.nombre ?? 'Admin' }} — consumo en tiempo real del servicio de IA</p>
    </div>

    <div class="page-content">
      <!-- KPIs hoy -->
      <div class="section-label">Hoy</div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Llamadas hoy</div>
          <div class="kpi-value">{{ consumo?.totales?.llamadas ?? '—' }}</div>
          <div class="kpi-meta">{{ consumo?.por_agente?.length ?? 0 }} agentes activos</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Tokens hoy</div>
          <div class="kpi-value">{{ fmt(consumo?.totales?.tokens_total) }}</div>
          <div class="kpi-meta">In + Out</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Costo hoy</div>
          <div class="kpi-value">${{ consumo?.totales?.costo_usd?.toFixed(4) ?? '0.0000' }}</div>
          <div class="kpi-meta">USD</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Errores hoy</div>
          <div class="kpi-value" :style="{ color: (consumo?.totales?.errores ?? 0) > 0 ? 'var(--color-error)' : 'inherit' }">
            {{ consumo?.totales?.errores ?? 0 }}
          </div>
          <div class="kpi-meta">llamadas fallidas</div>
        </div>
      </div>

      <!-- KPIs del mes -->
      <div class="section-label" style="margin-top:24px">Este mes</div>
      <div class="kpi-grid">
        <div class="kpi-card kpi-highlight">
          <div class="kpi-label">Costo del mes</div>
          <div class="kpi-value">${{ costoMes.toFixed(4) }}</div>
          <div class="kpi-meta">USD acumulado</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Llamadas del mes</div>
          <div class="kpi-value">{{ fmt(llamadasMes) }}</div>
          <div class="kpi-meta">total de llamadas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Tokens del mes</div>
          <div class="kpi-value">{{ fmt(tokensMes) }}</div>
          <div class="kpi-meta">acumulados</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Ciclo de facturación</div>
          <div class="kpi-value" style="font-size:18px">{{ cicloPeriodo }}</div>
          <div class="kpi-meta">{{ diasRestantes }} días restantes</div>
        </div>
      </div>

      <!-- Alertas -->
      <div v-if="consumo?.alertas?.length" class="alertas-wrap">
        <div v-for="a in consumo.alertas" :key="a.agente" class="alerta-item" :class="`alerta-${a.nivel}`">
          <AlertTriangleIcon :size="14" />
          <span><strong>{{ a.agente }}</strong>: {{ a.mensaje }}</span>
        </div>
      </div>

      <!-- Consumo por agente hoy -->
      <div class="tabla-wrap" style="margin-bottom:20px">
        <div class="tabla-header">
          <span class="tabla-titulo">Consumo por agente — hoy</span>
          <button class="btn-icon" title="Actualizar" @click="cargar">
            <RefreshCwIcon :size="13" :class="{ 'spin': cargando }" />
          </button>
        </div>
        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Agente</th>
              <th>Modelo</th>
              <th>Llamadas</th>
              <th>% Límite RPD</th>
              <th>Tokens</th>
              <th>Costo</th>
              <th>Latencia prom.</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ag in consumo?.por_agente" :key="ag.agente_slug">
              <td><strong>{{ ag.agente_slug }}</strong></td>
              <td class="mono">{{ ag.modelo_id }}</td>
              <td>{{ ag.llamadas }} / {{ ag.limite_rpd_diario ?? '∞' }}</td>
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="progress-bar-wrap" style="width:80px">
                    <div class="progress-bar-fill" :style="{ width: `${Math.min(Number(ag.pct_limite_hoy)||0,100)}%`, background: colorBarra(ag.estado) }" />
                  </div>
                  <span :style="{ color: colorTexto(ag.estado), fontSize:'12px', fontWeight:500 }">
                    {{ ag.pct_limite_hoy != null ? Number(ag.pct_limite_hoy).toFixed(1)+'%' : '—' }}
                  </span>
                </div>
              </td>
              <td>{{ fmt(ag.tokens_total) }}</td>
              <td>${{ ag.costo_usd ? Number(ag.costo_usd).toFixed(4) : '0.0000' }}</td>
              <td>{{ ag.latencia_prom_ms ? ag.latencia_prom_ms+'ms' : '—' }}</td>
              <td><span class="badge" :class="badgeEstado(ag.estado)">{{ ag.estado }}</span></td>
            </tr>
            <tr v-if="!consumo?.por_agente?.length">
              <td colspan="8" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin datos hoy</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Histórico 30 días -->
      <div class="tabla-wrap" style="margin-bottom:20px">
        <div class="tabla-header">
          <span class="tabla-titulo">Histórico — últimos 30 días por agente</span>
        </div>
        <table class="os-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Agente</th>
              <th>Llamadas</th>
              <th>Tokens</th>
              <th>Costo USD</th>
              <th>Latencia prom.</th>
              <th>Errores</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in historico" :key="`${r.fecha}-${r.agente_slug}`">
              <td class="mono">{{ fechaCorta(r.fecha) }}</td>
              <td>{{ r.agente_slug }}</td>
              <td>{{ r.llamadas }}</td>
              <td>{{ fmt(r.tokens_total) }}</td>
              <td>${{ Number(r.costo_usd).toFixed(4) }}</td>
              <td>{{ r.latencia_prom_ms ? r.latencia_prom_ms+'ms' : '—' }}</td>
              <td :style="{ color: r.errores > 0 ? 'var(--color-error)' : 'inherit' }">{{ r.errores }}</td>
            </tr>
            <tr v-if="!historico.length">
              <td colspan="7" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin datos históricos</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Últimas llamadas -->
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">Últimas 20 llamadas</span>
        </div>
        <table class="os-table">
          <thead>
            <tr>
              <th>Hora</th>
              <th>Usuario</th>
              <th>Canal</th>
              <th>Agente</th>
              <th>Tipo</th>
              <th>Tokens</th>
              <th>ms</th>
              <th>Ok</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td class="mono">{{ horaCorta(log.created_at) }}</td>
              <td>{{ log.usuario_id }}</td>
              <td>{{ log.canal }}</td>
              <td>{{ log.agente_slug }}</td>
              <td>{{ log.tipo_consulta }}</td>
              <td>{{ log.tokens_total ?? '—' }}</td>
              <td>{{ log.latencia_ms ?? '—' }}</td>
              <td>
                <span v-if="!log.error_mensaje" style="color:var(--color-success)">✓</span>
                <span v-else style="color:var(--color-error)" :title="log.error_mensaje">✗</span>
              </td>
            </tr>
            <tr v-if="!logs.length && !cargandoLogs">
              <td colspan="8" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin llamadas registradas</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/authStore'
import { api } from 'src/services/api'
import { RefreshCwIcon, AlertTriangleIcon } from 'lucide-vue-next'

const authStore = useAuthStore()
const usuario = authStore.usuario

const consumo   = ref(null)
const historico = ref([])
const logs      = ref([])
const cargando  = ref(true)
const cargandoLogs = ref(true)

// ─── Costo / llamadas / tokens del mes actual ──────────────────────
// fecha del historico llega como "Fri, 13 Mar 2026 00:00:00 GMT" — normalizar
function fechaMes(f) {
  if (!f) return ''
  return new Date(f).toISOString().slice(0, 7) // "2026-03"
}
const costoMes = computed(() => {
  if (!historico.value.length) return 0
  const mesActual = new Date().toISOString().slice(0, 7)
  return historico.value
    .filter(r => fechaMes(r.fecha) === mesActual)
    .reduce((acc, r) => acc + Number(r.costo_usd || 0), 0)
})
const llamadasMes = computed(() => {
  const mesActual = new Date().toISOString().slice(0, 7)
  return historico.value
    .filter(r => fechaMes(r.fecha) === mesActual)
    .reduce((acc, r) => acc + (r.llamadas || 0), 0)
})
const tokensMes = computed(() => {
  const mesActual = new Date().toISOString().slice(0, 7)
  return historico.value
    .filter(r => fechaMes(r.fecha) === mesActual)
    .reduce((acc, r) => acc + (r.tokens_total || 0), 0)
})

// ─── Ciclo de facturación: del 1 al último día del mes ────────────
const cicloPeriodo = computed(() => {
  const hoy = new Date()
  const y = hoy.getFullYear(), m = hoy.getMonth()
  const fin = new Date(y, m + 1, 0) // último día del mes
  const opts = { day: 'numeric', month: 'short' }
  return `1–${fin.getDate()} ${fin.toLocaleString('es-CO', { month: 'short' })} ${y}`
})
const diasRestantes = computed(() => {
  const hoy = new Date()
  const fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 1)
  return Math.ceil((fin - hoy) / (1000 * 60 * 60 * 24))
})

async function cargar() {
  cargando.value = true
  try { consumo.value = await api('/api/ia/consumo') } catch { consumo.value = null }
  try {
    const res = await api('/api/ia/consumo/historico')
    historico.value = (res.registros || []).sort((a, b) => b.fecha > a.fecha ? 1 : -1)
  } catch { historico.value = [] }
  cargando.value = false
}

async function cargarLogs() {
  cargandoLogs.value = true
  try { logs.value = (await api('/api/ia/logs?limit=20')).rows } catch { logs.value = [] }
  cargandoLogs.value = false
}

onMounted(() => {
  cargar()
  cargarLogs()
})

function fmt(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString('es-CO')
}
function horaCorta(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
function fechaCorta(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}
function colorBarra(estado) {
  if (estado === 'critico') return 'var(--color-error)'
  if (estado === 'advertencia') return 'var(--color-warning)'
  return 'var(--color-success)'
}
function colorTexto(estado) {
  if (estado === 'critico') return 'var(--color-error)'
  if (estado === 'advertencia') return 'var(--color-warning)'
  return 'var(--text-secondary)'
}
function badgeEstado(estado) {
  if (estado === 'critico') return 'badge-error'
  if (estado === 'advertencia') return 'badge-warning'
  if (estado === 'ilimitado') return 'badge-info'
  return 'badge-success'
}
</script>

<style scoped>
.section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.kpi-highlight {
  border-color: var(--color-accent);
}
.alertas-wrap { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; margin-top: 16px; }
.alerta-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
}
.alerta-critico  { background: var(--color-error-bg);   color: var(--color-error); }
.alerta-advertencia { background: var(--color-warning-bg); color: var(--color-warning); }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.8s linear infinite; }
</style>
