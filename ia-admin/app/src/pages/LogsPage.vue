<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Logs</h1>
      <p class="page-subtitle">Historial completo de llamadas al servicio de IA</p>
    </div>

    <div class="page-content">
      <!-- Filtros -->
      <div class="filtros-wrap">
        <select class="input-field" v-model="filtros.agente" style="width:160px" @change="cargar">
          <option value="">Todos los agentes</option>
          <option v-for="s in slugsAgentes" :key="s" :value="s">{{ s }}</option>
        </select>
        <select class="input-field" v-model="filtros.tipo" style="width:160px" @change="cargar">
          <option value="">Todos los tipos</option>
          <option v-for="t in tiposList" :key="t" :value="t">{{ t }}</option>
        </select>
        <input class="input-field" v-model="filtros.usuario" placeholder="Usuario..." style="width:140px" @keyup.enter="cargar" />
        <input class="input-field" type="date" v-model="filtros.fecha_desde" style="width:150px" @change="cargar" />
        <input class="input-field" type="date" v-model="filtros.fecha_hasta" style="width:150px" @change="cargar" />
        <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-secondary);cursor:pointer">
          <input type="checkbox" v-model="filtros.solo_errores" @change="cargar" style="accent-color:var(--color-error)" />
          Solo errores
        </label>
        <button class="btn btn-secondary" @click="cargar">
          <SearchIcon :size="13" /> Buscar
        </button>
        <span style="font-size:12px;color:var(--text-tertiary);margin-left:auto">{{ total }} registros</span>
      </div>

      <!-- Tabla -->
      <div class="tabla-wrap">
        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Fecha/Hora</th>
              <th>Usuario</th>
              <th>Canal</th>
              <th>Agente</th>
              <th>Tipo</th>
              <th>Tokens</th>
              <th>Costo</th>
              <th>ms</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="log in logs"
              :key="log.id"
              :class="{ selected: seleccionado?.id === log.id }"
              @click="seleccionar(log)"
            >
              <td class="mono" style="color:var(--text-tertiary)">{{ log.id }}</td>
              <td class="mono" style="font-size:12px">{{ fechaCorta(log.created_at) }}</td>
              <td>{{ log.usuario_id }}</td>
              <td><span class="badge badge-neutral">{{ log.canal }}</span></td>
              <td>{{ log.agente_slug }}</td>
              <td>{{ log.tipo_consulta }}</td>
              <td>{{ log.tokens_total ?? '—' }}</td>
              <td class="mono" style="font-size:12px">{{ log.costo_usd ? '$' + Number(log.costo_usd).toFixed(5) : '—' }}</td>
              <td>{{ log.latencia_ms ?? '—' }}</td>
              <td>
                <span v-if="!log.error_mensaje" class="badge badge-success">OK</span>
                <span v-else class="badge badge-error">Error</span>
              </td>
            </tr>
            <tr v-if="!logs.length">
              <td colspan="10" style="text-align:center;color:var(--text-tertiary);padding:40px">Sin registros</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div v-if="total > limit" class="paginacion">
        <button class="btn btn-secondary" :disabled="offset === 0" @click="paginaAnterior">← Anterior</button>
        <span style="font-size:13px;color:var(--text-secondary)">
          {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} de {{ total }}
        </span>
        <button class="btn btn-secondary" :disabled="offset + limit >= total" @click="paginaSiguiente">Siguiente →</button>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="seleccionado" class="overlay" @click="cerrar" />
    </transition>

    <!-- Panel detalle del log -->
    <transition name="panel">
      <div v-if="seleccionado" class="side-panel" style="width:500px">
        <div class="side-panel-header">
          <span class="side-panel-title">Log #{{ seleccionado.id }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="log-meta-grid">
            <div class="log-meta-item"><span class="log-meta-label">Fecha</span><span>{{ fechaCompleta(seleccionado.created_at) }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Usuario</span><span>{{ seleccionado.usuario_id }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Canal</span><span>{{ seleccionado.canal }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Agente</span><span>{{ seleccionado.agente_slug }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Tipo</span><span>{{ seleccionado.tipo_consulta }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Tokens entrada</span><span>{{ seleccionado.tokens_in ?? '—' }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Tokens salida</span><span>{{ seleccionado.tokens_out ?? '—' }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Costo</span><span>${{ seleccionado.costo_usd?.toFixed(5) ?? '0.00000' }}</span></div>
            <div class="log-meta-item"><span class="log-meta-label">Latencia</span><span>{{ seleccionado.latencia_ms }}ms</span></div>
          </div>

          <div v-if="seleccionado.error_mensaje" class="error-box">
            <div class="error-label">Error</div>
            <pre class="log-pre error-pre">{{ seleccionado.error_mensaje }}</pre>
          </div>

          <div class="divider" />

          <div v-if="seleccionado.pregunta_usuario">
            <div class="log-section-label">Pregunta</div>
            <pre class="log-pre">{{ seleccionado.pregunta_usuario }}</pre>
          </div>

          <div v-if="seleccionado.sql_generado">
            <div class="log-section-label">SQL generado</div>
            <pre class="log-pre mono">{{ seleccionado.sql_generado }}</pre>
          </div>

          <div v-if="seleccionado.respuesta_texto">
            <div class="log-section-label">Respuesta</div>
            <pre class="log-pre">{{ seleccionado.respuesta_texto }}</pre>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { apiFetch } from 'src/services/api'
import { ref, onMounted } from 'vue'
import { SearchIcon, XIcon } from 'lucide-vue-next'

const logs = ref([])
const cargando = ref(true)
const seleccionado = ref(null)
const total = ref(0)
const limit = 50
const offset = ref(0)
const slugsAgentes = ref([])
const tiposList = ref([])
const filtros = ref({
  agente: '', tipo: '', usuario: '', fecha_desde: '', fecha_hasta: '', solo_errores: false
})

async function cargar() {
  cargando.value = true
  try {
    const params = new URLSearchParams({ limit, offset: offset.value })
    if (filtros.value.agente) params.set('agente', filtros.value.agente)
    if (filtros.value.tipo) params.set('tipo', filtros.value.tipo)
    if (filtros.value.usuario) params.set('usuario', filtros.value.usuario)
    if (filtros.value.fecha_desde) params.set('fecha_desde', filtros.value.fecha_desde)
    if (filtros.value.fecha_hasta) params.set('fecha_hasta', filtros.value.fecha_hasta)
    if (filtros.value.solo_errores) params.set('solo_errores', '1')
    const res = await apiFetch(`/api/ia/logs?${params}`)
    const data = await res.json()
    logs.value = Array.isArray(data) ? data : (data.rows ?? [])
    total.value = data.total ?? logs.value.length
  } catch (e) { logs.value = [] }
  cargando.value = false
}

async function cargarFiltros() {
  try {
    const [ra, rt] = await Promise.all([
      apiFetch('/api/ia/agentes-admin').then(r => r.json()),
      apiFetch('/api/ia/tipos-admin').then(r => r.json())
    ])
    slugsAgentes.value = ra.map(a => a.slug)
    tiposList.value = rt.map(t => t.tipo)
  } catch (e) {}
}

function seleccionar(log) { seleccionado.value = log }
function cerrar() { seleccionado.value = null }

function paginaAnterior() { offset.value = Math.max(0, offset.value - limit); cargar() }
function paginaSiguiente() { offset.value = offset.value + limit; cargar() }

function fechaCorta(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-CO', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
function fechaCompleta(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'medium' })
}

onMounted(() => { cargarFiltros(); cargar() })
</script>

<style scoped>
.filtros-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.paginacion {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}
.log-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
}
.log-meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
  color: var(--text-primary);
}
.log-meta-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
}
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
  color: var(--text-primary);
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
}
.error-box {
  background: var(--color-error-bg);
  border: 1px solid rgba(220,38,38,0.2);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 8px;
}
.error-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-error);
  margin-bottom: 4px;
}
.error-pre {
  background: transparent;
  border: none;
  padding: 0;
  color: var(--color-error);
  font-size: 12px;
  max-height: 100px;
}
</style>
