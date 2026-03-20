<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Esquemas BD</h1>
      <p class="page-subtitle">DDL de tablas por tema — el LLM lo usa para generar SQL correcto</p>
    </div>

    <div class="page-content">

      <!-- Tabs de temas -->
      <div class="temas-bar">
        <button
          v-for="tema in temas"
          :key="tema.id"
          class="tema-btn"
          :class="{ active: temaActivo?.id === tema.id }"
          @click="seleccionarTema(tema)"
        >
          {{ tema.nombre }}
          <span v-if="esquema?.ddl_auto" class="tema-badge">DDL</span>
        </button>
      </div>

      <!-- Contenido del tema seleccionado -->
      <div v-if="temaActivo" class="esquema-wrap">

        <!-- Header -->
        <div class="tabla-header" style="margin-bottom:12px">
          <span class="tabla-titulo">
            {{ temaActivo.nombre }}
            <span v-if="esquema?.ultima_sync" class="text-muted" style="font-size:12px;font-weight:400">
              — sync {{ formatFecha(esquema.ultima_sync) }}
            </span>
          </span>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary" @click="guardarNotas" :disabled="guardando">
              {{ guardando ? 'Guardando...' : 'Guardar notas' }}
            </button>
            <button class="btn btn-primary" @click="sincronizar" :disabled="sincronizando">
              <RefreshCwIcon :size="13" />
              {{ sincronizando ? 'Sincronizando...' : 'Sincronizar DDL' }}
            </button>
          </div>
        </div>

        <!-- Tablas incluidas -->
        <div class="input-group">
          <label class="input-label">Tablas incluidas en este tema (una por línea)</label>
          <textarea
            class="input-field"
            v-model="tablasTexto"
            rows="5"
            style="font-family:monospace;font-size:12px;resize:vertical"
            placeholder="resumen_ventas_facturas_mes&#10;zeffi_clientes&#10;..."
          />
          <div style="font-size:11px;color:var(--text-tertiary);margin-top:3px">
            El LLM solo verá el DDL de estas tablas al responder preguntas del tema "{{ temaActivo.nombre }}"
          </div>
        </div>

        <!-- Notas manuales -->
        <div class="input-group" style="margin-top:12px">
          <label class="input-label">Notas manuales (instrucciones adicionales al LLM sobre el esquema)</label>
          <textarea
            class="input-field"
            v-model="notasTexto"
            rows="5"
            style="font-size:13px;resize:vertical;line-height:1.6"
            placeholder="ej. El campo pdte_de_cobro es TEXT, no numérico — castear con CAST(REPLACE(...))"
          />
        </div>

        <!-- DDL autogenerado -->
        <div class="input-group" style="margin-top:12px">
          <label class="input-label">
            DDL autogenerado
            <span class="badge badge-neutral" style="margin-left:6px">solo lectura</span>
          </label>
          <div v-if="!esquema?.ddl_auto" class="empty-state" style="padding:20px;text-align:center;border:1px solid var(--border-subtle);border-radius:var(--radius-md)">
            <p style="color:var(--text-tertiary);font-size:13px">Sin DDL — presiona "Sincronizar DDL" para generarlo desde la BD</p>
          </div>
          <textarea
            v-else
            class="input-field"
            :value="esquema.ddl_auto"
            rows="16"
            readonly
            style="font-family:monospace;font-size:11px;resize:vertical;background:var(--bg-card);color:var(--text-secondary)"
          />
        </div>

      </div>

      <div v-else class="empty-state" style="margin-top:24px">
        <p>Selecciona un tema para ver su esquema</p>
      </div>

      <!-- Info box -->
      <div class="card" style="max-width:700px;margin-top:16px;background:var(--color-info-bg);border-color:rgba(37,99,235,0.15)">
        <div style="display:flex;gap:10px;align-items:flex-start">
          <DatabaseIcon :size="16" style="color:var(--color-info);margin-top:2px;flex-shrink:0" />
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--color-info);margin-bottom:4px">Cómo funcionan los esquemas</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
              Cuando el usuario pregunta algo de análisis de datos, el LLM recibe el DDL de las tablas del tema activo.
              Si no hay tema activo, recibe el DDL completo de todas las tablas.
              <strong>Sincronizar DDL</strong> lee la estructura real de la BD de Hostinger y la guarda aquí.
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { apiFetch } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import { DatabaseIcon, RefreshCwIcon } from 'lucide-vue-next'

const temas      = ref([])
const temaActivo = ref(null)
const esquema    = ref(null)
const tablasTexto = ref('')
const notasTexto  = ref('')
const cargando   = ref(false)
const guardando  = ref(false)
const sincronizando = ref(false)

async function cargarTemas() {
  try {
    const res = await apiFetch('/api/ia/rag/temas')
    temas.value = await res.json()
    if (temas.value.length && !temaActivo.value) seleccionarTema(temas.value[0])
  } catch { temas.value = [] }
}

async function seleccionarTema(tema) {
  temaActivo.value = tema
  esquema.value = null
  tablasTexto.value = ''
  notasTexto.value = ''
  cargando.value = true
  try {
    const res = await apiFetch(`/api/ia/esquemas/${tema.id}`)
    if (res.ok) {
      const data = await res.json()
      esquema.value = data
      const tablas = data.tablas_incluidas
        ? (typeof data.tablas_incluidas === 'string' ? JSON.parse(data.tablas_incluidas) : data.tablas_incluidas)
        : []
      tablasTexto.value = tablas.join('\n')
      notasTexto.value = data.notas_manuales || ''
    }
  } catch { }
  cargando.value = false
}

async function guardarNotas() {
  if (!temaActivo.value) return
  guardando.value = true
  try {
    const tablas = tablasTexto.value.split('\n').map(s => s.trim()).filter(Boolean)
    await apiFetch(`/api/ia/esquemas/${temaActivo.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tablas_incluidas: tablas, notas_manuales: notasTexto.value })
    })
    await seleccionarTema(temaActivo.value)
  } catch (e) { alert('Error: ' + e.message) }
  guardando.value = false
}

async function sincronizar() {
  if (!temaActivo.value) return
  sincronizando.value = true
  try {
    const res = await apiFetch(`/api/ia/esquemas/${temaActivo.value.id}/sync`, { method: 'POST' })
    const data = await res.json()
    if (data.ok === false) throw new Error(data.error || 'Error al sincronizar')
    await seleccionarTema(temaActivo.value)
  } catch (e) { alert('Error al sincronizar: ' + e.message) }
  sincronizando.value = false
}

function formatFecha(f) {
  if (!f) return ''
  const d = new Date(f)
  return d.toLocaleDateString('es-CO', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => cargarTemas())
onMounted(cargarTemas)
</script>

<style scoped>
.temas-bar {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.tema-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 70ms, color 70ms, border-color 70ms;
}
.tema-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.tema-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}
.tema-badge {
  background: rgba(255,255,255,0.25);
  border-radius: 10px;
  padding: 1px 5px;
  font-size: 10px;
  font-weight: 600;
}
.tema-btn:not(.active) .tema-badge {
  background: var(--accent-muted);
  color: var(--accent);
}
.esquema-wrap { max-width: 800px; }
</style>
