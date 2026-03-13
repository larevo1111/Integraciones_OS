<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Contextos RAG</h1>
      <p class="page-subtitle">Base de conocimiento para los agentes de IA</p>
    </div>

    <div class="page-content">

      <!-- Selector de temas -->
      <div class="temas-bar">
        <button
          v-for="tema in temas"
          :key="tema.id"
          class="tema-btn"
          :class="{ active: temaActivo?.id === tema.id }"
          @click="seleccionarTema(tema)"
        >
          <span class="tema-slug">{{ tema.slug }}</span>
          <span class="tema-nombre">{{ tema.nombre }}</span>
          <span v-if="tema.total_documentos > 0" class="tema-badge">{{ tema.total_documentos }}</span>
        </button>
        <button class="tema-btn tema-nuevo-btn" @click="abrirModalTema">
          <PlusIcon :size="12" />
          Nuevo tema
        </button>
      </div>

      <!-- Tabla de documentos -->
      <div class="tabla-wrap" v-if="temaActivo">
        <div class="tabla-header">
          <span class="tabla-titulo">
            {{ temaActivo.nombre }}
            <span class="text-muted" style="font-weight:400;font-size:12px">
              — {{ documentos.length }} documento{{ documentos.length !== 1 ? 's' : '' }}
            </span>
          </span>
          <button class="btn btn-primary" @click="abrirNuevoDoc">
            <PlusIcon :size="13" /> Agregar Documento
          </button>
        </div>

        <div v-if="cargandoDocs" class="empty-state"><p>Cargando...</p></div>
        <div v-else-if="documentos.length === 0" class="empty-state">
          <p>No hay documentos en este tema — Agrega el primero</p>
        </div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Fragmentos</th>
              <th>Tokens est.</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="doc in documentos"
              :key="doc.id"
              :class="{ selected: docSeleccionado?.id === doc.id }"
              @click="abrirEditarDoc(doc)"
            >
              <td><strong>{{ doc.nombre }}</strong></td>
              <td><span class="badge badge-neutral">{{ doc.tipo }}</span></td>
              <td>{{ doc.fragmentos_total ?? 0 }}</td>
              <td>{{ formatNum(doc.tokens_estimados) }}</td>
              <td>
                <span v-if="doc.activo" class="badge badge-success">activo</span>
                <span v-else class="badge badge-neutral">inactivo</span>
              </td>
              <td>
                <button class="btn-icon" @click.stop="abrirEditarDoc(doc)" title="Ver/Editar">
                  <PencilIcon :size="13" />
                </button>
                <button class="btn-icon btn-icon-danger" @click.stop="confirmarEliminar(doc)" title="Eliminar">
                  <TrashIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Sección de búsqueda RAG -->
      <div class="tabla-wrap busqueda-section">
        <div class="tabla-header">
          <span class="tabla-titulo">Probar búsqueda RAG</span>
        </div>
        <div class="busqueda-form">
          <input
            class="input-field"
            v-model="preguntaPrueba"
            placeholder="Escribe una pregunta para ver qué fragmentos encontraría el sistema..."
            @keyup.enter="probarBusqueda"
            style="flex:1"
          />
          <select class="input-field" v-model="temaFiltroSearchId" style="width:200px;flex-shrink:0">
            <option :value="null">Todos los temas</option>
            <option v-for="t in temas" :key="t.id" :value="t.id">{{ t.nombre }}</option>
          </select>
          <button class="btn btn-primary" @click="probarBusqueda" :disabled="buscando || !preguntaPrueba.trim()">
            {{ buscando ? 'Buscando...' : 'Buscar' }}
          </button>
        </div>

        <div v-if="resultadosBusqueda.length > 0" class="busqueda-resultados">
          <div v-for="(frag, idx) in resultadosBusqueda" :key="idx" class="frag-card">
            <div class="frag-header">
              <span class="frag-doc">{{ frag.nombre_documento }}</span>
              <span class="badge badge-neutral">{{ frag.tema_slug }}</span>
              <div class="frag-score-bar">
                <div class="frag-score-fill" :style="{ width: Math.min(100, (frag.score || 0) * 100) + '%' }"></div>
              </div>
              <span class="frag-score-num">{{ (frag.score || 0).toFixed(3) }}</span>
            </div>
            <p class="frag-contenido">{{ frag.contenido?.slice(0, 300) }}{{ frag.contenido?.length > 300 ? '...' : '' }}</p>
          </div>
        </div>
        <div v-else-if="busquedaRealizada && !buscando" class="empty-state" style="padding:16px">
          <p>Sin resultados para esa pregunta</p>
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="panelAbierto" class="overlay" @click="cerrarPanel" />
    </transition>

    <!-- Panel lateral documento -->
    <transition name="panel">
      <div v-if="panelAbierto" class="side-panel">
        <div class="side-panel-header">
          <span class="side-panel-title">{{ docSeleccionado ? docSeleccionado.nombre : 'Nuevo Documento' }}</span>
          <button class="btn-icon" @click="cerrarPanel"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Nombre *</label>
            <input class="input-field" v-model="formDoc.nombre" placeholder="Ej: Política de precios 2026" />
          </div>
          <div class="input-group">
            <label class="input-label">Tipo *</label>
            <select class="input-field" v-model="formDoc.tipo">
              <option value="texto">Texto</option>
              <option value="manual">Manual</option>
              <option value="url">URL</option>
              <option value="pdf">PDF</option>
            </select>
          </div>
          <div class="input-group">
            <label class="input-label">Contenido *</label>
            <textarea
              class="input-field"
              v-model="formDoc.contenido"
              placeholder="Pega aquí el texto completo del documento..."
              style="min-height:200px;resize:vertical;font-family:inherit"
            ></textarea>
            <div class="tokens-hint" v-if="formDoc.contenido">
              ~{{ tokensEstimados.toLocaleString() }} tokens estimados · ~{{ fragmentosEstimados }} fragmento{{ fragmentosEstimados !== 1 ? 's' : '' }}
            </div>
          </div>

          <div v-if="docSeleccionado && docSeleccionado.fragmentos_total > 0" class="frag-info">
            <span>Fragmentos indexados: <strong>{{ docSeleccionado.fragmentos_total }}</strong></span>
            <span class="text-muted">· {{ formatFecha(docSeleccionado.created_at) }}</span>
            <button class="btn btn-secondary" style="margin-left:auto" @click="reindexar" :disabled="guardando">
              Re-indexar
            </button>
          </div>

          <div class="input-group" style="display:flex;align-items:center;gap:10px">
            <label class="toggle">
              <input type="checkbox" v-model="formDoc.activo" />
              <div class="toggle-track"></div>
              <div class="toggle-thumb"></div>
            </label>
            <span class="input-label" style="margin:0">Activo</span>
          </div>
        </div>
        <div class="side-panel-footer">
          <button v-if="docSeleccionado" class="btn btn-danger" @click="eliminarDocPanel">Eliminar</button>
          <button class="btn btn-secondary" @click="cerrarPanel">Cancelar</button>
          <button class="btn btn-primary" @click="guardarDoc" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </transition>

    <!-- Modal nuevo tema -->
    <transition name="overlay">
      <div v-if="modalTema" class="modal-overlay" @click.self="cerrarModalTema">
        <div class="modal-box">
          <div class="modal-header">
            <span class="side-panel-title">Nuevo Tema</span>
            <button class="btn-icon" @click="cerrarModalTema"><XIcon :size="15" /></button>
          </div>
          <div class="modal-body">
            <div class="input-group">
              <label class="input-label">Slug * <span class="text-muted">(solo minúsculas, guiones y números)</span></label>
              <input class="input-field" v-model="formTema.slug" placeholder="recursos-humanos" />
            </div>
            <div class="input-group">
              <label class="input-label">Nombre *</label>
              <input class="input-field" v-model="formTema.nombre" placeholder="Recursos Humanos" />
            </div>
            <div class="input-group">
              <label class="input-label">Descripción</label>
              <textarea class="input-field" v-model="formTema.descripcion" placeholder="Descripción del área de conocimiento..." style="min-height:80px;resize:vertical"></textarea>
            </div>
            <div class="input-group">
              <label class="input-label">System Prompt</label>
              <textarea class="input-field" v-model="formTema.system_prompt" placeholder="Instrucciones base para el LLM en este tema..." style="min-height:80px;resize:vertical"></textarea>
            </div>
            <div class="input-group">
              <label class="input-label">Agente preferido</label>
              <select class="input-field" v-model="formTema.agente_preferido">
                <option value="">Sin preferencia</option>
                <option v-for="ag in agentes" :key="ag.slug" :value="ag.slug">{{ ag.nombre }}</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="cerrarModalTema">Cancelar</button>
            <button class="btn btn-primary" @click="crearTema" :disabled="creandoTema">
              {{ creandoTema ? 'Creando...' : 'Crear Tema' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { apiFetch, api } from 'src/services/api'
import { ref, computed, onMounted } from 'vue'
import { PlusIcon, PencilIcon, XIcon, TrashIcon } from 'lucide-vue-next'

// ── Estado ────────────────────────────────────────────────────────
const temas        = ref([])
const temaActivo   = ref(null)
const documentos   = ref([])
const agentes      = ref([])
const panelAbierto = ref(false)
const modalTema    = ref(false)
const docSeleccionado = ref(null)
const cargandoDocs = ref(false)
const guardando    = ref(false)
const creandoTema  = ref(false)

const formDoc = ref({ nombre: '', tipo: 'texto', contenido: '', activo: true })
const formTema = ref({ slug: '', nombre: '', descripcion: '', system_prompt: '', agente_preferido: '' })

const preguntaPrueba     = ref('')
const temaFiltroSearchId = ref(null)
const buscando           = ref(false)
const busquedaRealizada  = ref(false)
const resultadosBusqueda = ref([])

// ── Computed ──────────────────────────────────────────────────────
const tokensEstimados = computed(() => {
  const palabras = formDoc.value.contenido.split(/\s+/).filter(w => w).length
  return Math.round(palabras * 1.33)
})
const fragmentosEstimados = computed(() =>
  Math.ceil(formDoc.value.contenido.split(/\s+/).filter(w => w).length / 500) || 0
)

// ── Utilidades ────────────────────────────────────────────────────
function formatNum(n) {
  if (!n) return '0'
  return Number(n).toLocaleString('es-CO')
}
function formatFecha(f) {
  if (!f) return ''
  return new Date(f).toLocaleDateString('es-CO')
}

// ── Temas ─────────────────────────────────────────────────────────
async function cargarTemas() {
  try {
    const res  = await apiFetch('/api/ia/rag/temas?empresa=ori_sil_2')
    const data = await res.json()
    temas.value = data.temas || []
    if (!temaActivo.value && temas.value.length) {
      temaActivo.value = temas.value[0]
      cargarDocumentos()
    }
  } catch (e) { console.error('Error cargando temas', e) }
}

async function seleccionarTema(tema) {
  temaActivo.value = tema
  cargarDocumentos()
}

// ── Documentos ────────────────────────────────────────────────────
async function cargarDocumentos() {
  if (!temaActivo.value) return
  cargandoDocs.value = true
  try {
    const res  = await apiFetch(`/api/ia/rag/temas/${temaActivo.value.id}/documentos`)
    const data = await res.json()
    documentos.value = data.documentos || []
  } catch (e) { documentos.value = [] }
  cargandoDocs.value = false
}

function abrirNuevoDoc() {
  docSeleccionado.value = null
  formDoc.value = { nombre: '', tipo: 'texto', contenido: '', activo: true }
  panelAbierto.value = true
}

async function abrirEditarDoc(doc) {
  docSeleccionado.value = doc
  formDoc.value = { nombre: doc.nombre, tipo: doc.tipo, contenido: '', activo: !!doc.activo }
  panelAbierto.value = true
  // Cargar contenido completo
  try {
    const res  = await apiFetch(`/api/ia/rag/documentos/${doc.id}`)
    const data = await res.json()
    formDoc.value.contenido = data.documento?.contenido_original || ''
  } catch (e) {}
}

function cerrarPanel() {
  panelAbierto.value = false
  docSeleccionado.value = null
  formDoc.value = { nombre: '', tipo: 'texto', contenido: '', activo: true }
}

async function guardarDoc() {
  if (!formDoc.value.nombre?.trim()) { alert('El nombre es requerido'); return }
  if (!formDoc.value.contenido?.trim()) { alert('El contenido es requerido'); return }
  guardando.value = true
  try {
    if (docSeleccionado.value) {
      const res = await apiFetch(`/api/ia/rag/documentos/${docSeleccionado.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(formDoc.value)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al guardar')
    } else {
      const res = await apiFetch(`/api/ia/rag/temas/${temaActivo.value.id}/documentos`, {
        method: 'POST',
        body: JSON.stringify(formDoc.value)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al crear')
      if (data.advertencia) console.warn(data.advertencia)
    }
    cerrarPanel()
    await cargarDocumentos()
    await cargarTemas()
  } catch (e) {
    alert('Error: ' + e.message)
  }
  guardando.value = false
}

async function reindexar() {
  if (!docSeleccionado.value || !formDoc.value.contenido?.trim()) return
  guardando.value = true
  try {
    const res = await apiFetch(`/api/ia/rag/documentos/${docSeleccionado.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ contenido: formDoc.value.contenido })
    })
    const data = await res.json()
    if (data.ok) {
      docSeleccionado.value.fragmentos_total = data.fragmentos_creados
      alert(`Re-indexado: ${data.fragmentos_creados} fragmentos`)
    }
  } catch (e) { alert('Error al re-indexar: ' + e.message) }
  guardando.value = false
}

async function confirmarEliminar(doc) {
  if (!confirm(`¿Eliminar documento "${doc.nombre}"? Esta acción eliminará también todos sus fragmentos.`)) return
  try {
    await apiFetch(`/api/ia/rag/documentos/${doc.id}`, { method: 'DELETE' })
    await cargarDocumentos()
    await cargarTemas()
  } catch (e) { alert('Error al eliminar') }
}

async function eliminarDocPanel() {
  if (!docSeleccionado.value) return
  if (!confirm(`¿Eliminar documento "${docSeleccionado.value.nombre}"?`)) return
  try {
    await apiFetch(`/api/ia/rag/documentos/${docSeleccionado.value.id}`, { method: 'DELETE' })
    cerrarPanel()
    await cargarDocumentos()
    await cargarTemas()
  } catch (e) { alert('Error al eliminar') }
}

// ── Nuevo tema ────────────────────────────────────────────────────
async function abrirModalTema() {
  formTema.value = { slug: '', nombre: '', descripcion: '', system_prompt: '', agente_preferido: '' }
  // Cargar agentes si aún no están
  if (agentes.value.length === 0) {
    try {
      const res  = await apiFetch('/api/ia/agentes-admin')
      agentes.value = await res.json()
    } catch (e) {}
  }
  modalTema.value = true
}

function cerrarModalTema() {
  modalTema.value = false
}

async function crearTema() {
  if (!formTema.value.slug?.trim() || !formTema.value.nombre?.trim()) {
    alert('Slug y nombre son requeridos')
    return
  }
  creandoTema.value = true
  try {
    const res = await apiFetch('/api/ia/rag/temas', {
      method: 'POST',
      body: JSON.stringify({ ...formTema.value, empresa: 'ori_sil_2' })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error al crear tema')
    cerrarModalTema()
    await cargarTemas()
    // Seleccionar el tema recién creado
    const nuevo = temas.value.find(t => t.slug === formTema.value.slug)
    if (nuevo) seleccionarTema(nuevo)
  } catch (e) {
    alert('Error: ' + e.message)
  }
  creandoTema.value = false
}

// ── Búsqueda RAG ─────────────────────────────────────────────────
async function probarBusqueda() {
  if (!preguntaPrueba.value.trim()) return
  buscando.value = true
  busquedaRealizada.value = true
  try {
    const body = { pregunta: preguntaPrueba.value, empresa: 'ori_sil_2' }
    if (temaFiltroSearchId.value) body.tema_id = temaFiltroSearchId.value
    const res  = await apiFetch('/api/ia/rag/buscar', {
      method: 'POST',
      body: JSON.stringify(body)
    })
    const data = await res.json()
    resultadosBusqueda.value = data.fragmentos || []
  } catch (e) {
    resultadosBusqueda.value = []
    console.error('Error en búsqueda', e)
  }
  buscando.value = false
}

onMounted(cargarTemas)
</script>

<style scoped>
/* ── Temas bar ── */
.temas-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 20px;
}

.tema-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  transition: all 70ms;
  font-family: inherit;
}
.tema-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
  border-color: var(--border-default);
}
.tema-btn.active {
  background: var(--accent-muted);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 500;
}
.tema-slug {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  opacity: 0.7;
}
.tema-nombre {
  font-size: 12px;
}
.tema-badge {
  background: var(--accent);
  color: white;
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
}
.tema-nuevo-btn {
  border-style: dashed;
  color: var(--text-tertiary);
}
.tema-nuevo-btn:hover {
  color: var(--color-success);
  border-color: var(--color-success);
}

/* ── Búsqueda ── */
.busqueda-section {
  margin-top: 24px;
}
.busqueda-form {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 0;
}

/* ── Resultados fragmentos ── */
.busqueda-resultados {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.frag-card {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}
.frag-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.frag-doc {
  font-weight: 500;
  font-size: 12px;
  color: var(--text-primary);
}
.frag-score-bar {
  flex: 1;
  height: 4px;
  background: var(--border-subtle);
  border-radius: 2px;
  min-width: 60px;
}
.frag-score-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  min-width: 4px;
}
.frag-score-num {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}
.frag-contenido {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
}

/* ── Fragmentos info ── */
.frag-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-card-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

/* ── Tokens hint ── */
.tokens-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

/* ── Botón ícono danger ── */
.btn-icon-danger {
  color: var(--color-error);
}
.btn-icon-danger:hover {
  background: var(--color-error-bg);
}

/* ── Modal tema ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  width: 480px;
  max-width: calc(100vw - 40px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-shrink: 0;
}

.text-muted {
  color: var(--text-tertiary);
}
</style>
