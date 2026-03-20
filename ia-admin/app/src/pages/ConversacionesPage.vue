<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Conversaciones</h1>
      <p class="page-subtitle">Historial de sesiones activas — resumen, mensajes recientes y caché SQL por usuario</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ conversaciones.length }} sesiones activas</span>
          <button class="btn btn-secondary" @click="cargar">
            <RefreshCwIcon :size="13" /> Actualizar
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Canal</th>
              <th>Resumen</th>
              <th>Mensajes</th>
              <th>Caché SQL</th>
              <th>Última actividad</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="conversaciones.length === 0">
              <td colspan="7" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin sesiones</td>
            </tr>
            <tr
              v-for="c in conversaciones"
              :key="c.id"
              :class="{ selected: seleccionado?.id === c.id }"
              @click="verDetalle(c)"
              style="cursor:pointer"
            >
              <td>
                <div style="font-weight:500">{{ c.nombre_usuario || c.usuario_id }}</div>
                <div v-if="c.nombre_usuario" style="font-size:11px;color:var(--text-tertiary)">{{ c.usuario_id }}</div>
              </td>
              <td>
                <span class="badge" :class="canalBadge(c.canal)">{{ c.canal }}</span>
              </td>
              <td>
                <span v-if="c.largo_resumen" class="badge badge-neutral">{{ c.largo_resumen }} car.</span>
                <span v-else style="color:var(--text-tertiary);font-size:12px">—</span>
              </td>
              <td>
                <span v-if="c.n_mensajes" class="badge badge-neutral">{{ c.n_mensajes }}</span>
                <span v-else style="color:var(--text-tertiary);font-size:12px">0</span>
              </td>
              <td>
                <span v-if="c.tiene_cache_sql" class="badge badge-success">Sí</span>
                <span v-else style="color:var(--text-tertiary);font-size:12px">—</span>
              </td>
              <td style="font-size:12px;color:var(--text-tertiary);white-space:nowrap">
                {{ formatFecha(c.updated_at) }}
              </td>
              <td>
                <button class="btn-icon" @click.stop="verDetalle(c)" title="Ver detalle">
                  <EyeIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Info box -->
      <div class="card" style="max-width:700px;margin-top:16px;background:var(--color-info-bg);border-color:rgba(37,99,235,0.15)">
        <div style="display:flex;gap:10px;align-items:flex-start">
          <MessageSquareIcon :size="16" style="color:var(--color-info);margin-top:2px;flex-shrink:0" />
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--color-info);margin-bottom:4px">Memoria de conversación</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
              Cada sesión tiene un <strong>resumen comprimido</strong> (hasta 600 palabras) de toda la conversación,
              los <strong>últimos 5 mensajes</strong> exactos, y una <strong>caché SQL</strong> con el resultado de la última consulta.
              Limpiar el resumen reinicia la memoria del bot con ese usuario.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="seleccionado" class="overlay" @click="cerrar" />
    </transition>

    <!-- Panel lateral de detalle -->
    <transition name="panel">
      <div v-if="seleccionado" class="side-panel" style="width:500px">
        <div class="side-panel-header">
          <span class="side-panel-title">
            {{ detalle?.nombre_usuario || detalle?.usuario_id || '...' }}
            <span class="badge" :class="canalBadge(detalle?.canal)" style="margin-left:6px;font-size:11px">{{ detalle?.canal }}</span>
          </span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body" v-if="detalle">

          <!-- Acciones rápidas -->
          <div style="display:flex;gap:8px;margin-bottom:16px">
            <button class="btn btn-secondary" style="font-size:12px" @click="limpiarResumen" :disabled="accion !== null">
              <Trash2Icon :size="12" /> Limpiar resumen
            </button>
            <button class="btn btn-secondary" style="font-size:12px" @click="limpiarCache" :disabled="accion !== null">
              <Trash2Icon :size="12" /> Limpiar caché SQL
            </button>
            <button class="btn btn-danger" style="font-size:12px" @click="eliminarConversacion" :disabled="accion !== null">
              <Trash2Icon :size="12" /> Eliminar sesión
            </button>
          </div>

          <!-- Resumen -->
          <div class="detalle-seccion">
            <div class="detalle-seccion-titulo">
              Resumen de conversación
              <span v-if="detalle.resumen" class="badge badge-neutral" style="margin-left:6px">
                {{ contarPalabras(detalle.resumen) }} palabras
              </span>
            </div>
            <div v-if="detalle.resumen" class="detalle-texto">{{ detalle.resumen }}</div>
            <div v-else class="detalle-vacio">Sin resumen</div>
          </div>

          <!-- Mensajes recientes -->
          <div class="detalle-seccion" style="margin-top:16px">
            <div class="detalle-seccion-titulo">
              Mensajes recientes
              <span class="badge badge-neutral" style="margin-left:6px">{{ detalle.mensajes_recientes?.length || 0 }}</span>
            </div>
            <div v-if="detalle.mensajes_recientes?.length">
              <div
                v-for="(msg, i) in detalle.mensajes_recientes"
                :key="i"
                class="mensaje-item"
                :class="msg.role === 'user' ? 'mensaje-user' : 'mensaje-bot'"
              >
                <div class="mensaje-rol">{{ msg.role === 'user' ? 'Usuario' : 'Bot' }}</div>
                <div class="mensaje-texto">{{ msg.content?.substring(0, 300) }}{{ msg.content?.length > 300 ? '...' : '' }}</div>
              </div>
            </div>
            <div v-else class="detalle-vacio">Sin mensajes recientes</div>
          </div>

          <!-- Caché SQL -->
          <div class="detalle-seccion" style="margin-top:16px">
            <div class="detalle-seccion-titulo">Caché SQL</div>
            <div v-if="detalle.metadata?.cache_sql">
              <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px">
                <strong>Pregunta:</strong> {{ detalle.metadata.cache_sql.pregunta }}
              </div>
              <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px">
                <strong>Columnas:</strong> {{ detalle.metadata.cache_sql.columnas?.join(', ') || '—' }}
              </div>
              <div style="font-size:12px;color:var(--text-secondary)">
                <strong>Filas:</strong> {{ detalle.metadata.cache_sql.n_filas || 0 }}
              </div>
            </div>
            <div v-else class="detalle-vacio">Sin caché SQL</div>
          </div>

        </div>
        <div class="side-panel-body" v-else style="display:flex;align-items:center;justify-content:center;color:var(--text-tertiary)">
          Cargando...
        </div>
        <div class="side-panel-footer">
          <button class="btn btn-secondary" @click="cerrar">Cerrar</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { apiFetch } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import { RefreshCwIcon, EyeIcon, XIcon, Trash2Icon, MessageSquareIcon } from 'lucide-vue-next'

const conversaciones = ref([])
const cargando       = ref(true)
const seleccionado   = ref(null)
const detalle        = ref(null)
const accion         = ref(null)

async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/ia/conversaciones')
    conversaciones.value = await res.json()
  } catch { conversaciones.value = [] }
  cargando.value = false
}

async function verDetalle(c) {
  seleccionado.value = c
  detalle.value = null
  try {
    const res = await apiFetch(`/api/ia/conversaciones/${c.id}`)
    detalle.value = await res.json()
  } catch { detalle.value = c }
}

function cerrar() { seleccionado.value = null; detalle.value = null; accion.value = null }

async function limpiarResumen() {
  if (!confirm('¿Limpiar resumen y mensajes recientes de esta sesión?')) return
  accion.value = 'resumen'
  try {
    await apiFetch(`/api/ia/conversaciones/${seleccionado.value.id}/resumen`, { method: 'DELETE' })
    await verDetalle(seleccionado.value)
    await cargar()
  } catch { alert('Error') }
  accion.value = null
}

async function limpiarCache() {
  if (!confirm('¿Limpiar la caché SQL de esta sesión?')) return
  accion.value = 'cache'
  try {
    await apiFetch(`/api/ia/conversaciones/${seleccionado.value.id}/cache`, { method: 'DELETE' })
    await verDetalle(seleccionado.value)
    await cargar()
  } catch { alert('Error') }
  accion.value = null
}

async function eliminarConversacion() {
  if (!confirm('¿Eliminar completamente esta sesión? El bot olvidará todo el historial con este usuario.')) return
  accion.value = 'eliminar'
  try {
    await apiFetch(`/api/ia/conversaciones/${seleccionado.value.id}`, { method: 'DELETE' })
    cerrar()
    await cargar()
  } catch { alert('Error') }
  accion.value = null
}

function canalBadge(canal) {
  if (canal === 'telegram') return 'badge-info'
  if (canal === 'api') return 'badge-neutral'
  if (canal === 'erp') return 'badge-success'
  return 'badge-neutral'
}

function contarPalabras(texto) {
  return texto?.trim().split(/\s+/).filter(Boolean).length || 0
}

function formatFecha(f) {
  if (!f) return '—'
  const d = new Date(f)
  return d.toLocaleDateString('es-CO', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => cargar())
onMounted(cargar)
</script>

<style scoped>
.detalle-seccion { }
.detalle-seccion-titulo {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}
.detalle-texto {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  max-height: 180px;
  overflow-y: auto;
}
.detalle-vacio {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}
.mensaje-item {
  border-radius: var(--radius-md);
  padding: 8px 10px;
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.5;
}
.mensaje-user {
  background: var(--accent-muted);
  border-left: 2px solid var(--accent);
}
.mensaje-bot {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
}
.mensaje-rol {
  font-weight: 600;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  margin-bottom: 3px;
}
.mensaje-texto { color: var(--text-secondary); }
.badge-info {
  background: rgba(37,99,235,0.1);
  color: var(--color-info);
}
</style>
