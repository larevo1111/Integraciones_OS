<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-subtitle">Hola, {{ usuario.nombre }} — consumo en tiempo real del servicio de IA</p>
    </div>

    <div class="page-content">
      <!-- KPIs hoy -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Llamadas hoy</div>
          <div class="kpi-value">{{ consumo?.totales?.llamadas_hoy ?? '—' }}</div>
          <div class="kpi-meta">{{ consumo?.totales?.agentes_activos ?? 0 }} agentes activos</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Tokens hoy</div>
          <div class="kpi-value">{{ fmt(consumo?.totales?.tokens_hoy) }}</div>
          <div class="kpi-meta">In + Out</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Costo hoy</div>
          <div class="kpi-value">${{ consumo?.totales?.costo_hoy_usd?.toFixed(4) ?? '0.0000' }}</div>
          <div class="kpi-meta">USD</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Errores hoy</div>
          <div class="kpi-value" :style="{ color: (consumo?.totales?.errores_hoy ?? 0) > 0 ? 'var(--color-error)' : 'inherit' }">
            {{ consumo?.totales?.errores_hoy ?? 0 }}
          </div>
          <div class="kpi-meta">llamadas fallidas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Costo del mes</div>
          <div class="kpi-value">${{ consumo?.totales?.costo_mes_usd?.toFixed(3) ?? '0.000' }}</div>
          <div class="kpi-meta">USD acumulado</div>
        </div>
      </div>

      <!-- Alertas -->
      <div v-if="consumo?.alertas?.length" class="alertas-wrap">
        <div v-for="a in consumo.alertas" :key="a.agente" class="alerta-item" :class="`alerta-${a.nivel}`">
          <AlertTriangleIcon :size="14" />
          <span><strong>{{ a.agente }}</strong>: {{ a.mensaje }}</span>
        </div>
      </div>

      <!-- Consumo por agente -->
      <div class="tabla-wrap" style="margin-bottom:20px">
        <div class="tabla-header">
          <span class="tabla-titulo">Consumo por agente — hoy</span>
          <button class="btn-icon" title="Actualizar" @click="cargarConsumo">
            <RefreshCwIcon :size="13" :class="{ 'spin': cargando }" />
          </button>
        </div>
        <div v-if="cargando" class="empty-state">
          <p>Cargando...</p>
        </div>
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
              <td>{{ ag.llamadas_hoy }} / {{ ag.rate_limit_rpd ?? '∞' }}</td>
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="progress-bar-wrap" style="width:80px">
                    <div class="progress-bar-fill" :style="{ width: `${Math.min(ag.pct_limite_hoy*100,100)}%`, background: colorBarra(ag.estado) }" />
                  </div>
                  <span :style="{ color: colorTexto(ag.estado), fontSize:'12px', fontWeight:500 }">
                    {{ ag.pct_limite_hoy != null ? (ag.pct_limite_hoy*100).toFixed(1)+'%' : '—' }}
                  </span>
                </div>
              </td>
              <td>{{ fmt(ag.tokens_hoy) }}</td>
              <td>${{ ag.costo_hoy_usd?.toFixed(4) ?? '0.0000' }}</td>
              <td>{{ ag.latencia_prom_ms ? ag.latencia_prom_ms+'ms' : '—' }}</td>
              <td><span class="badge" :class="badgeEstado(ag.estado)">{{ ag.estado }}</span></td>
            </tr>
            <tr v-if="!consumo?.por_agente?.length">
              <td colspan="8" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin datos hoy</td>
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
import { ref, onMounted, inject } from 'vue'
import { RefreshCwIcon, AlertTriangleIcon } from 'lucide-vue-next'

// usuario inyectado desde el layout (via provide/inject o prop route)
const usuario = inject('usuario', ref({ nombre: 'Admin', rol: 'admin' }))

const consumo = ref(null)
const logs = ref([])
const cargando = ref(true)
const cargandoLogs = ref(true)

async function cargarConsumo() {
  cargando.value = true
  try {
    const res = await fetch('/api/ia/consumo')
    consumo.value = await res.json()
  } catch (e) { consumo.value = null }
  cargando.value = false
}

async function cargarLogs() {
  cargandoLogs.value = true
  try {
    const res = await fetch('/api/ia/logs?limit=20')
    logs.value = await res.json()
  } catch (e) { logs.value = [] }
  cargandoLogs.value = false
}

onMounted(() => {
  cargarConsumo()
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
.alertas-wrap { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
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
