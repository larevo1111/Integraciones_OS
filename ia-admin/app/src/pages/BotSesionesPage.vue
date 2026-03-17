<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Sesiones Bot</h1>
      <p class="page-subtitle">Usuarios del Bot Telegram — estado de autenticación y actividad</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ sesiones.length }} sesiones</span>
          <button class="btn btn-secondary" @click="cargar" :disabled="cargando" style="gap:5px">
            <RefreshCwIcon :size="13" :class="{ spin: cargando }" /> Actualizar
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Telegram ID</th>
              <th>Autorizado</th>
              <th>Nivel</th>
              <th>Agente</th>
              <th>Empresa</th>
              <th>Última actividad</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sesiones" :key="s.telegram_user_id">
              <td>
                <div style="display:flex;flex-direction:column;gap:1px">
                  <strong>{{ s.nombre || '—' }}</strong>
                  <span style="font-size:11px;color:var(--text-tertiary)">@{{ s.username || '?' }}</span>
                </div>
              </td>
              <td class="mono" style="font-size:12px">{{ s.telegram_user_id }}</td>
              <td>
                <span v-if="s.autorizado" class="badge badge-success">✓ Verificado</span>
                <span v-else class="badge badge-error">Sin verificar</span>
              </td>
              <td>
                <div class="nivel-pill" :class="`nivel-${s.nivel}`">
                  {{ s.nivel }} <span class="nivel-text">{{ nivelLabel(s.nivel) }}</span>
                </div>
              </td>
              <td>
                <span v-if="s.agente_preferido" class="badge badge-neutral">{{ s.agente_preferido }}</span>
                <span v-else style="font-size:12px;color:var(--text-tertiary)">default</span>
              </td>
              <td style="font-size:12px;color:var(--text-tertiary)">{{ s.empresa }}</td>
              <td class="mono" style="font-size:12px;color:var(--text-tertiary)">{{ fechaRelativa(s.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!cargando && sesiones.length === 0" class="empty-state">
          <p>No hay sesiones registradas</p>
        </div>
      </div>

      <!-- Stats cards -->
      <div v-if="!cargando && sesiones.length > 0" style="display:flex;gap:12px;max-width:700px;margin-top:16px;flex-wrap:wrap">
        <div class="stat-card">
          <div class="stat-value">{{ autorizados }}</div>
          <div class="stat-label">Autorizados</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ sinVerificar }}</div>
          <div class="stat-label">Sin verificar</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ activosHoy }}</div>
          <div class="stat-label">Activos hoy</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { apiFetch } from 'src/services/api'
import { ref, computed, onMounted } from 'vue'
import { RefreshCwIcon } from 'lucide-vue-next'

const sesiones = ref([])
const cargando = ref(true)

async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/ia/bot-sesiones')
    sesiones.value = await res.json()
  } catch (e) { sesiones.value = [] }
  cargando.value = false
}

const autorizados   = computed(() => sesiones.value.filter(s => s.autorizado).length)
const sinVerificar  = computed(() => sesiones.value.filter(s => !s.autorizado).length)
const activosHoy    = computed(() => {
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  return sesiones.value.filter(s => new Date(s.updated_at) >= hoy).length
})

function nivelLabel(n) {
  const labels = { 1: 'Básico', 2: 'Básico+', 3: 'Estándar', 4: 'Estándar+', 5: 'Avanzado', 6: 'Avanzado+', 7: 'Admin' }
  return labels[n] || n
}

function fechaRelativa(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  const diff = Date.now() - d.getTime()
  if (diff < 60000)     return 'ahora'
  if (diff < 3600000)   return `hace ${Math.floor(diff/60000)}m`
  if (diff < 86400000)  return `hace ${Math.floor(diff/3600000)}h`
  return d.toLocaleDateString('es-CO')
}

onMounted(cargar)
</script>

<style scoped>
.nivel-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
.nivel-pill.nivel-7 { background: rgba(94,106,210,0.12); color: #5e6ad2; }
.nivel-pill.nivel-5, .nivel-pill.nivel-6 { background: rgba(16,185,129,0.1); color: #059669; }
.nivel-pill.nivel-3, .nivel-pill.nivel-4 { background: rgba(245,158,11,0.1); color: #d97706; }
.nivel-text { font-weight: 400; }

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 12px 20px;
  min-width: 100px;
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
