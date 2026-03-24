<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Super Agente</h1>
      <p class="page-subtitle">Prompt del sistema y sesiones del agente conversacional</p>
    </div>

    <div class="page-content">
      <!-- Tabs -->
      <div class="tabs-bar">
        <button
          class="tab-btn"
          :class="{ active: tabActiva === 'prompt' }"
          @click="tabActiva = 'prompt'"
        >Prompt</button>
        <button
          class="tab-btn"
          :class="{ active: tabActiva === 'historial' }"
          @click="tabActiva = 'historial'; cargarSesiones()"
        >Historial</button>
      </div>

      <!-- Tab: Prompt -->
      <div v-if="tabActiva === 'prompt'">
        <div class="card" style="max-width:800px">
          <div class="input-group">
            <label class="input-label">Prompt de sistema</label>
            <textarea
              class="input-field"
              v-model="promptTexto"
              rows="14"
              style="resize:vertical;font-size:13px;line-height:1.6;font-family:inherit"
              placeholder="Eres un asistente de Origen Silvestre. Responde en español..."
            />
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;margin-top:12px;gap:12px">
            <div style="font-size:12px;color:var(--text-tertiary)">
              <span v-if="config">
                Última modificación: {{ formatFecha(config.updated_at) }} por {{ config.usuario_ult_mod || '—' }}
              </span>
              <span v-else>Sin configuración guardada aún</span>
            </div>
            <button class="btn btn-primary" @click="guardarPrompt" :disabled="guardando">
              {{ guardando ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Tab: Historial -->
      <div v-if="tabActiva === 'historial'">
        <div class="tabla-wrap">
          <div class="tabla-header">
            <span class="tabla-titulo">{{ sesiones.length }} sesiones</span>
          </div>

          <div v-if="cargandoSesiones" class="empty-state"><p>Cargando...</p></div>
          <div v-else-if="sesiones.length === 0" class="empty-state"><p>No hay sesiones registradas</p></div>
          <table v-else class="os-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Primera pregunta</th>
                <th>Mensajes</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in sesiones"
                :key="s.id"
                style="cursor:pointer"
                @click="abrirSesion(s)"
              >
                <td style="white-space:nowrap;font-size:12px;color:var(--text-secondary)">{{ formatFecha(s.updated_at) }}</td>
                <td>{{ s.usuario_nombre }}</td>
                <td style="color:var(--text-secondary);max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ s.primera_pregunta }}</td>
                <td><span class="badge badge-neutral">{{ s.n_mensajes }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Dialog: conversación completa -->
    <div v-if="sesionDetalle" class="overlay" @click="sesionDetalle = null" />
    <div v-if="sesionDetalle" class="side-panel" style="width:520px">
      <div class="side-panel-header">
        <span class="side-panel-title">Conversación — {{ sesionDetalle.usuario_nombre }}</span>
        <button class="btn-icon" @click="sesionDetalle = null"><XIcon :size="15" /></button>
      </div>
      <div class="side-panel-body" style="padding:0">
        <div v-if="cargandoDetalle" class="empty-state" style="padding:32px"><p>Cargando...</p></div>
        <div v-else class="chat-mensajes">
          <div
            v-for="(msg, i) in mensajesDetalle"
            :key="i"
            class="chat-msg"
            :class="msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'"
          >
            <div class="chat-msg-role">{{ msg.role === 'user' ? 'Usuario' : 'Super Agente' }}</div>
            <div class="chat-msg-content">{{ msg.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { apiFetch } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import { ref, onMounted, watch } from 'vue'
import { XIcon } from 'lucide-vue-next'

const tabActiva = ref('prompt')
const config = ref(null)
const promptTexto = ref('')
const guardando = ref(false)

const sesiones = ref([])
const cargandoSesiones = ref(false)
const sesionDetalle = ref(null)
const mensajesDetalle = ref([])
const cargandoDetalle = ref(false)

async function cargarConfig() {
  try {
    const res = await apiFetch('/api/ia/superagente/config')
    const data = await res.json()
    if (data.ok && data.config) {
      config.value = data.config
      promptTexto.value = data.config.prompt_sistema || ''
    }
  } catch (e) { /* silencioso */ }
}

async function guardarPrompt() {
  if (!promptTexto.value.trim()) {
    alert('El prompt no puede estar vacío')
    return
  }
  guardando.value = true
  try {
    const res = await apiFetch('/api/ia/superagente/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt_sistema: promptTexto.value })
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Error desconocido')
    await cargarConfig()
  } catch (e) { alert('Error al guardar: ' + e.message) }
  guardando.value = false
}

async function cargarSesiones() {
  if (sesiones.value.length > 0) return
  cargandoSesiones.value = true
  try {
    const res = await apiFetch('/api/ia/superagente/sesiones')
    const data = await res.json()
    sesiones.value = data.ok ? data.sesiones : []
  } catch (e) { sesiones.value = [] }
  cargandoSesiones.value = false
}

async function abrirSesion(s) {
  sesionDetalle.value = s
  mensajesDetalle.value = []
  cargandoDetalle.value = true
  try {
    const res = await apiFetch(`/api/ia/superagente/sesiones/${s.id}`)
    const data = await res.json()
    mensajesDetalle.value = data.ok ? data.sesion.mensajes : []
  } catch (e) { mensajesDetalle.value = [] }
  cargandoDetalle.value = false
}

function formatFecha(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => {
  config.value = null
  promptTexto.value = ''
  sesiones.value = []
  cargarConfig()
})

onMounted(cargarConfig)
</script>

<style scoped>
.tabs-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 0;
}

.tab-btn {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 70ms, border-color 70ms;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}

.chat-mensajes {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 12px 16px;
}

.chat-msg {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  max-width: 100%;
}

.chat-msg-user {
  background: var(--accent-muted);
  align-self: flex-end;
}

.chat-msg-assistant {
  background: var(--bg-row-hover);
  align-self: flex-start;
}

.chat-msg-role {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.chat-msg-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
