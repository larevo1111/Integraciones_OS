<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Playground</h1>
      <p class="page-subtitle">Prueba el servicio de IA directamente — consultas en tiempo real</p>
    </div>

    <div class="page-content playground-layout">
      <!-- Panel izquierdo: entrada -->
      <div class="panel-input">
        <div class="card" style="height:100%;display:flex;flex-direction:column;gap:14px">
          <div>
            <label class="input-label">Pregunta</label>
            <textarea
              class="input-field"
              v-model="pregunta"
              rows="6"
              placeholder="¿Cuánto vendimos este mes? / Redacta un email / Genera imagen de un árbol..."
              @keydown.ctrl.enter="enviar"
            />
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:4px">Ctrl+Enter para enviar</div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label class="input-label">Agente</label>
              <select class="input-field" v-model="agenteSeleccionado">
                <option value="">Auto (router decide)</option>
                <option v-for="ag in agentes" :key="ag.slug" :value="ag.slug">
                  {{ ag.slug }} {{ !ag.activo || !ag.tiene_key ? '⚠️' : '' }}
                </option>
              </select>
            </div>
            <div>
              <label class="input-label">Tipo de consulta</label>
              <select class="input-field" v-model="tipoSeleccionado">
                <option value="">Auto</option>
                <option v-for="t in tipos" :key="t.tipo" :value="t.tipo">{{ t.tipo }}</option>
              </select>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label class="input-label">Usuario ID</label>
              <input class="input-field" v-model="usuarioId" placeholder="santi" />
            </div>
            <div>
              <label class="input-label">Canal</label>
              <input class="input-field" v-model="canal" placeholder="playground" />
            </div>
          </div>

          <button
            class="btn btn-primary"
            style="width:100%;height:38px;font-size:14px"
            @click="enviar"
            :disabled="enviando || !pregunta.trim()"
          >
            <span v-if="enviando">Procesando...</span>
            <span v-else>Enviar consulta →</span>
          </button>

          <!-- Historial de esta sesión -->
          <div v-if="historial.length" style="border-top:1px solid var(--border-subtle);padding-top:12px">
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-tertiary);margin-bottom:8px">
              Historial de sesión
            </div>
            <div class="historial-list">
              <div
                v-for="(h, i) in historial"
                :key="i"
                class="historial-item"
                :class="{ active: historialActivo === i }"
                @click="verHistorial(i)"
              >
                <span class="historial-num">{{ i + 1 }}</span>
                <span class="historial-texto">{{ h.pregunta.substring(0, 60) }}{{ h.pregunta.length > 60 ? '...' : '' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel derecho: respuesta -->
      <div class="panel-output">
        <div class="card" style="height:100%;display:flex;flex-direction:column;gap:0">
          <!-- Sin respuesta -->
          <div v-if="!respuesta && !enviando" class="empty-state" style="flex:1">
            <BotIcon :size="28" style="opacity:0.15" />
            <p>La respuesta aparecerá aquí</p>
            <span>Escribe una pregunta y presiona Enviar</span>
          </div>

          <!-- Cargando -->
          <div v-else-if="enviando" class="empty-state" style="flex:1">
            <div class="loading-dots">
              <div /><div /><div />
            </div>
            <p>Procesando con {{ agenteSeleccionado || 'router' }}...</p>
          </div>

          <!-- Respuesta -->
          <template v-else>
            <!-- Meta -->
            <div class="respuesta-meta">
              <div class="meta-chips">
                <span class="badge badge-info">{{ respuesta.agente_usado }}</span>
                <span class="badge badge-neutral">{{ respuesta.tipo_detectado }}</span>
                <span v-if="respuesta.latencia_ms" class="badge badge-neutral">{{ respuesta.latencia_ms }}ms</span>
                <span v-if="respuesta.tokens_total" class="badge badge-neutral">{{ respuesta.tokens_total }} tokens</span>
                <span v-if="respuesta.costo_usd" class="badge badge-neutral">${{ respuesta.costo_usd.toFixed(5) }}</span>
              </div>
              <button class="btn-icon" @click="limpiar" title="Nueva consulta"><XIcon :size="13" /></button>
            </div>

            <!-- Error -->
            <div v-if="respuesta.error" class="error-box" style="margin:16px">
              <div class="error-label">Error</div>
              <pre class="log-pre error-pre">{{ respuesta.error }}</pre>
            </div>

            <!-- SQL generado -->
            <div v-if="respuesta.sql_generado" style="padding:0 16px">
              <div class="log-section-label">SQL generado</div>
              <pre class="log-pre mono">{{ respuesta.sql_generado }}</pre>
            </div>

            <!-- Imagen -->
            <div v-if="respuesta.imagen_b64" style="padding:0 16px">
              <div class="log-section-label">Imagen generada</div>
              <img :src="`data:${respuesta.imagen_mime};base64,${respuesta.imagen_b64}`" style="max-width:100%;border-radius:var(--radius-lg);margin-top:6px" />
            </div>

            <!-- Texto de respuesta -->
            <div v-if="respuesta.respuesta" style="padding:0 16px 16px;flex:1;overflow-y:auto">
              <div class="log-section-label">Respuesta</div>
              <div class="respuesta-texto">{{ respuesta.respuesta }}</div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { BotIcon, XIcon } from 'lucide-vue-next'

const pregunta = ref('')
const agenteSeleccionado = ref('')
const tipoSeleccionado = ref('')
const usuarioId = ref('santi')
const canal = ref('playground')
const enviando = ref(false)
const respuesta = ref(null)
const historial = ref([])
const historialActivo = ref(null)
const agentes = ref([])
const tipos = ref([])

async function cargarOpciones() {
  try {
    const [ra, rt] = await Promise.all([
      fetch('/api/ia/agentes-admin').then(r => r.json()),
      fetch('/api/ia/tipos-admin').then(r => r.json())
    ])
    agentes.value = ra
    tipos.value = rt
  } catch (e) {}
}

async function enviar() {
  if (!pregunta.value.trim() || enviando.value) return
  enviando.value = true
  respuesta.value = null

  const body = {
    pregunta: pregunta.value.trim(),
    usuario_id: usuarioId.value || 'playground',
    canal: canal.value || 'playground'
  }
  if (agenteSeleccionado.value) body.agente = agenteSeleccionado.value
  if (tipoSeleccionado.value) body.tipo = tipoSeleccionado.value

  try {
    const res = await fetch('http://localhost:5100/ia/consultar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    respuesta.value = data
    historial.value.unshift({ pregunta: pregunta.value, respuesta: data })
    historialActivo.value = null
  } catch (e) {
    respuesta.value = { error: e.message }
  }
  enviando.value = false
}

function verHistorial(i) {
  historialActivo.value = i
  respuesta.value = historial.value[i].respuesta
  pregunta.value = historial.value[i].pregunta
}

function limpiar() {
  respuesta.value = null
  pregunta.value = ''
  historialActivo.value = null
}

onMounted(cargarOpciones)
</script>

<style scoped>
.playground-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 16px;
  height: calc(100vh - 100px);
}
.panel-input, .panel-output { height: 100%; overflow: hidden; }

.respuesta-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.meta-chips { display: flex; gap: 6px; flex-wrap: wrap; }

.respuesta-texto {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  margin-top: 8px;
}

.historial-list { display: flex; flex-direction: column; gap: 2px; }
.historial-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 70ms;
}
.historial-item:hover, .historial-item.active { background: var(--bg-row-hover); }
.historial-num {
  width: 18px; height: 18px;
  border-radius: var(--radius-full);
  background: var(--border-default);
  font-size: 10px;
  font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.historial-texto { font-size: 12px; color: var(--text-secondary); }

.log-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  margin: 14px 0 6px;
}
.log-pre {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--bg-row-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}
.error-box {
  background: var(--color-error-bg);
  border: 1px solid rgba(220,38,38,0.2);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.error-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--color-error); margin-bottom: 4px; }
.error-pre { background: transparent; border: none; padding: 0; color: var(--color-error); font-family: var(--font-mono); font-size: 12px; margin: 0; }

/* Loading dots */
.loading-dots { display: flex; gap: 5px; margin-bottom: 8px; }
.loading-dots div {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: bounce 1.2s infinite;
}
.loading-dots div:nth-child(2) { animation-delay: 0.2s; }
.loading-dots div:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
