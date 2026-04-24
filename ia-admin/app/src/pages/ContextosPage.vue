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
          {{ tema.nombre }}
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

      <!-- Sección Schema BD -->
      <div class="tabla-wrap schema-section" v-if="temaActivo">
        <div class="tabla-header">
          <span class="tabla-titulo">Schema de BD
            <span class="text-muted" style="font-weight:400;font-size:12px">
              — se inyecta al LLM en consultas de datos
            </span>
          </span>
          <div style="display:flex;gap:8px;align-items:center">
            <span v-if="esquema?.ultima_sync" style="font-size:11px;color:var(--text-tertiary)">
              Sync: {{ fmtFecha(esquema.ultima_sync) }}
            </span>
            <button class="btn btn-secondary" @click="syncSchema" :disabled="sincronizando">
              {{ sincronizando ? 'Sincronizando...' : '↻ Sincronizar' }}
            </button>
            <button class="btn btn-secondary" @click="guardarSchema" :disabled="guardandoSchema">
              {{ guardandoSchema ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </div>

        <div style="padding:12px 16px 0">
          <AyudaPanel>
            <p><strong>¿Qué es el Schema BD de este tema?</strong><br>
            Define qué tablas de la base de datos puede ver la IA cuando alguien hace preguntas en este contexto. Solo las tablas seleccionadas se inyectan al modelo — así las respuestas son más precisas y el contexto más liviano.</p>
            <p style="margin-top:10px"><strong>Cómo configurarlo:</strong></p>
            <ol class="ayuda-lista">
              <li>Selecciona las <strong>tablas relevantes</strong> para esta área (ej: Comercial → tablas de ventas y clientes)</li>
              <li>Clic en <strong>"Sincronizar"</strong> — el sistema lee los campos y tipos de cada tabla directamente de la BD</li>
              <li>Agrega <strong>Notas de negocio</strong>: instrucciones que la IA debe saber para generar SQL correcto (ej: "precio_neto incluye IVA, usar precio_bruto - descuento")</li>
              <li>Clic en <strong>"Guardar"</strong></li>
            </ol>
            <p style="margin-top:10px"><strong>🔒 Seguridad:</strong> La IA solo puede hacer SELECT. El sistema bloquea cualquier escritura por dos capas independientes: validación de sintaxis SQL y modo READ ONLY de sesión en la BD.</p>
          </AyudaPanel>
        </div>

        <div v-if="cargandoSchema" style="padding:16px;color:var(--text-tertiary);font-size:13px">Cargando schema...</div>
        <div v-else class="schema-body">
          <!-- Tablas seleccionadas -->
          <div class="schema-field">
            <label class="schema-label">Tablas incluidas</label>
            <div class="tablas-chips" v-if="tablasDisponibles.length">
              <label v-for="t in tablasDisponibles" :key="t" class="chip-toggle">
                <input type="checkbox" :value="t" v-model="tablasSeleccionadas" />
                <span>{{ t }}</span>
              </label>
            </div>
            <div v-else style="font-size:12px;color:var(--text-tertiary)">
              Prueba la conexión primero para ver las tablas disponibles.
              <button class="btn-link" @click="cargarTablas">Cargar tablas</button>
            </div>
          </div>

          <!-- Schema auto -->
          <div class="schema-field" v-if="esquema?.ddl_auto">
            <label class="schema-label">Schema generado automáticamente <span class="text-muted">(solo lectura)</span></label>
            <pre class="schema-pre">{{ esquema.ddl_auto }}</pre>
          </div>

          <!-- Notas manuales -->
          <div class="schema-field">
            <label class="schema-label">Notas de negocio <span class="text-muted">(instrucciones adicionales para la IA)</span></label>
            <textarea class="input-field schema-textarea" v-model="notasSchema" rows="5"
              placeholder="ej: precio_neto_total INCLUYE IVA — usar precio_bruto_total - descuento_total&#10;id_cliente tiene prefijo tipo doc (CC 12345) — usar SUBSTRING_INDEX para JOIN"></textarea>
          </div>

          <div v-if="schemaMsg" class="schema-msg" :class="schemaMsgOk ? 'schema-ok' : 'schema-err'">{{ schemaMsg }}</div>
        </div>
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

          <!-- Zona de carga de archivo (solo en nuevo documento) -->
          <div v-if="!docSeleccionado" class="upload-section">
            <div
              class="upload-zone"
              :class="{ 'drag-over': dragging, 'upload-done': archivoSeleccionado }"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="onDrop"
              @click="$refs.inputArchivo.click()"
            >
              <input
                ref="inputArchivo"
                type="file"
                accept=".pdf,.doc,.docx,.xlsx,.xls,.xlsm,.csv,.txt,.md,.jpg,.jpeg,.png,.webp,.gif,.bmp"
                style="display:none"
                @change="onFileChange"
              />
              <template v-if="archivoSeleccionado">
                <FileTextIcon :size="20" />
                <span class="upload-filename">{{ archivoSeleccionado.name }}</span>
                <span class="upload-size text-muted">{{ formatBytes(archivoSeleccionado.size) }}</span>
                <button class="btn-link text-muted" style="font-size:11px" @click.stop="limpiarArchivo">Cambiar archivo</button>
              </template>
              <template v-else>
                <UploadIcon :size="20" />
                <span class="upload-hint">Arrastra un archivo o <strong>haz clic</strong> para seleccionar</span>
                <span class="upload-types">PDF · DOCX · XLSX · CSV · TXT · JPG · PNG · y más</span>
              </template>
            </div>
            <div class="upload-divider"><span>o escribe el contenido manualmente</span></div>
          </div>

          <div class="input-group">
            <label class="input-label">Nombre del documento *</label>
            <input class="input-field" v-model="formDoc.nombre" placeholder="Ej: Política de precios 2026" />
          </div>

          <!-- Contenido solo si NO hay archivo seleccionado (o editando existente) -->
          <div v-if="!archivoSeleccionado" class="input-group">
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

          <!-- Estado de procesamiento -->
          <div v-if="estadoUpload" class="upload-status" :class="uploadOk ? 'upload-status-ok' : 'upload-status-err'">
            {{ estadoUpload }}
          </div>

          <div v-if="docSeleccionado" class="input-group" style="display:flex;align-items:center;gap:10px">
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
            {{ guardando ? 'Procesando...' : (docSeleccionado ? 'Guardar' : (archivoSeleccionado ? 'Subir y procesar' : 'Guardar')) }}
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
import { localDatetime, fmtDatetime } from 'src/services/fecha'
import AyudaPanel from 'src/components/AyudaPanel.vue'
import { ref, computed, onMounted } from 'vue'
import { PlusIcon, PencilIcon, XIcon, TrashIcon, UploadIcon, FileTextIcon } from 'lucide-vue-next'

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

// Upload de archivos
const archivoSeleccionado = ref(null)
const dragging            = ref(false)
const estadoUpload        = ref('')
const uploadOk            = ref(true)
const inputArchivo        = ref(null)

const formDoc = ref({ nombre: '', tipo: 'texto', contenido: '', activo: true })
const formTema = ref({ slug: '', nombre: '', descripcion: '', system_prompt: '', agente_preferido: '' })

const preguntaPrueba     = ref('')
const temaFiltroSearchId = ref(null)
const buscando           = ref(false)
const busquedaRealizada  = ref(false)
const resultadosBusqueda = ref([])

// ── Schema BD ─────────────────────────────────────────────────────
const esquema            = ref(null)
const cargandoSchema     = ref(false)
const sincronizando      = ref(false)
const guardandoSchema    = ref(false)
const tablasDisponibles  = ref([])
const tablasSeleccionadas = ref([])
const notasSchema        = ref('')
const schemaMsg          = ref('')
const schemaMsgOk        = ref(true)

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
  cargarSchema()
}

// ── Schema BD ─────────────────────────────────────────────────────
async function cargarSchema() {
  if (!temaActivo.value) return
  cargandoSchema.value = true
  schemaMsg.value = ''
  try {
    const data = await api(`/api/ia/esquemas/${temaActivo.value.id}`)
    esquema.value = data
    tablasSeleccionadas.value = Array.isArray(data.tablas_incluidas) ? data.tablas_incluidas : []
    notasSchema.value = data.notas_manuales || ''
    if (data.conexion_id) cargarTablas(data.conexion_id)
  } catch (e) {
    esquema.value = null
  } finally {
    cargandoSchema.value = false
  }
}

async function cargarTablas(conexionId) {
  const id = conexionId || esquema.value?.conexion_id
  if (!id) return
  try {
    const data = await api(`/api/ia/conexiones/${id}/tablas`)
    tablasDisponibles.value = data.tablas || []
  } catch (e) { tablasDisponibles.value = [] }
}

async function syncSchema() {
  if (!temaActivo.value) return
  sincronizando.value = true
  schemaMsg.value = ''
  try {
    const data = await api(`/api/ia/esquemas/${temaActivo.value.id}/sync`, { method: 'POST' })
    schemaMsg.value = data.mensaje || 'Schema sincronizado'
    schemaMsgOk.value = data.ok !== false
    if (data.ok) { esquema.value = { ...esquema.value, ddl_auto: data.schema, ultima_sync: localDatetime() } }
  } catch (e) {
    schemaMsg.value = e.message; schemaMsgOk.value = false
  } finally { sincronizando.value = false }
}

async function guardarSchema() {
  if (!temaActivo.value) return
  guardandoSchema.value = true
  schemaMsg.value = ''
  try {
    await api(`/api/ia/esquemas/${temaActivo.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ tablas_incluidas: tablasSeleccionadas.value, notas_manuales: notasSchema.value })
    })
    schemaMsg.value = 'Guardado correctamente'
    schemaMsgOk.value = true
  } catch (e) {
    schemaMsg.value = e.message; schemaMsgOk.value = false
  } finally { guardandoSchema.value = false }
}

// Usa fmtDatetime del helper: siempre muestra hora Colombia sin depender de la
// zona del navegador (antes era inconsistente si el admin se abría desde fuera de CO).
const fmtFecha = fmtDatetime

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

// ── Manejo de archivos ────────────────────────────────────────────
function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) seleccionarArchivo(file)
}
function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) seleccionarArchivo(file)
}
function seleccionarArchivo(file) {
  archivoSeleccionado.value = file
  estadoUpload.value = ''
  // Autocompletar nombre si está vacío
  if (!formDoc.value.nombre) {
    formDoc.value.nombre = file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
  }
}
function limpiarArchivo() {
  archivoSeleccionado.value = null
  estadoUpload.value = ''
  if (inputArchivo.value) inputArchivo.value.value = ''
}
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function cerrarPanel() {
  panelAbierto.value = false
  docSeleccionado.value = null
  formDoc.value = { nombre: '', tipo: 'texto', contenido: '', activo: true }
  limpiarArchivo()
}

async function guardarDoc() {
  if (!formDoc.value.nombre?.trim()) { alert('El nombre es requerido'); return }
  guardando.value = true
  estadoUpload.value = ''
  try {
    if (docSeleccionado.value) {
      // Editar documento existente
      if (!formDoc.value.contenido?.trim()) { alert('El contenido es requerido'); guardando.value = false; return }
      const res = await apiFetch(`/api/ia/rag/documentos/${docSeleccionado.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(formDoc.value)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al guardar')
    } else if (archivoSeleccionado.value) {
      // Nuevo documento desde archivo
      estadoUpload.value = 'Extrayendo texto del archivo...'
      const fd = new FormData()
      fd.append('archivo', archivoSeleccionado.value)
      fd.append('nombre', formDoc.value.nombre.trim())
      const token = localStorage.getItem('ia_jwt') || ''
      const res = await fetch(`/api/ia/rag/temas/${temaActivo.value.id}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: fd
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al procesar archivo')
      estadoUpload.value = `✓ ${data.fragmentos_creados} fragmentos indexados`
      uploadOk.value = true
      await cargarDocumentos()
      await cargarTemas()
      limpiarArchivo()
      guardando.value = false
      return
    } else {
      // Nuevo documento desde texto
      if (!formDoc.value.contenido?.trim()) { alert('El contenido es requerido'); guardando.value = false; return }
      const res = await apiFetch(`/api/ia/rag/temas/${temaActivo.value.id}/documentos`, {
        method: 'POST',
        body: JSON.stringify(formDoc.value)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al crear')
    }
    cerrarPanel()
    await cargarDocumentos()
    await cargarTemas()
  } catch (e) {
    estadoUpload.value = '✗ Error: ' + e.message
    uploadOk.value = false
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
  gap: 4px;
  margin-bottom: 20px;
}

/* Estilo Linear.app — ver 90_tabs_pestanas.png */
.tema-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 400;
  font-family: inherit;
  transition: border-color 70ms, color 70ms, background 70ms;
  white-space: nowrap;
}
.tema-btn:hover {
  border-color: var(--border-default);
  color: var(--text-secondary);
}
.tema-btn.active {
  border-color: var(--border-default);
  color: var(--text-primary);
  background: var(--bg-surface);
  font-weight: 500;
}
.tema-badge {
  background: var(--accent);
  color: white;
  border-radius: 10px;
  padding: 0px 5px;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
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

/* ─── Upload de archivos ──────────────────────────────── */
.upload-section { display: flex; flex-direction: column; gap: 0; margin-bottom: 16px; }

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px 16px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 12px;
  transition: border-color 80ms, background 80ms;
}
.upload-zone:hover, .upload-zone.drag-over {
  border-color: var(--accent);
  background: var(--accent-muted);
  color: var(--accent);
}
.upload-zone.upload-done {
  border-style: solid;
  border-color: var(--color-success);
  background: transparent;
  color: var(--text-primary);
}
.upload-hint { font-size: 12px; color: var(--text-secondary); }
.upload-types { font-size: 10px; color: var(--text-tertiary); letter-spacing: 0.03em; }
.upload-filename { font-size: 13px; font-weight: 500; color: var(--text-primary); word-break: break-all; }
.upload-size { font-size: 11px; }

.upload-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0 4px;
  font-size: 11px;
  color: var(--text-tertiary);
}
.upload-divider::before, .upload-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}

.upload-status {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  margin-top: 8px;
}
.upload-status-ok  { background: var(--color-success-bg, #ecfdf5); color: var(--color-success); }
.upload-status-err { background: var(--color-error-bg);  color: var(--color-error); }

.btn-link {
  background: none; border: none; cursor: pointer; padding: 0;
  text-decoration: underline; font-family: inherit;
}

/* ── Schema BD ─────────────────────────────────────────── */
.schema-section { margin-top: 16px; }
.schema-body { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.schema-field { display: flex; flex-direction: column; gap: 8px; }
.schema-label { font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.schema-textarea {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px; line-height: 1.6; resize: vertical;
}
.schema-pre {
  background: var(--bg-surface); border: 1px solid var(--border-default);
  border-radius: 6px; padding: 12px; font-size: 11px;
  font-family: 'JetBrains Mono', monospace; color: var(--text-secondary);
  overflow-x: auto; max-height: 300px; overflow-y: auto;
  white-space: pre; line-height: 1.5; margin: 0;
}
.schema-msg {
  padding: 8px 12px; border-radius: 6px; font-size: 12px; font-weight: 500;
}
.schema-ok  { background: rgba(74,222,128,0.1); color: #4ade80; }
.schema-err { background: rgba(248,113,113,0.1); color: #f87171; }

/* Chips de selección de tablas */
.tablas-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip-toggle { display: flex; align-items: center; cursor: pointer; }
.chip-toggle input { display: none; }
.chip-toggle span {
  padding: 3px 10px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border-default); color: var(--text-secondary);
  background: var(--bg-surface); transition: all 120ms; font-family: monospace;
}
.chip-toggle input:checked + span {
  background: rgba(94,106,210,0.15); border-color: #5e6ad2;
  color: #5e6ad2; font-weight: 500;
}
.chip-toggle:hover span { border-color: var(--border-strong); }

.ayuda-lista { padding-left: 18px; margin: 6px 0 0; }
.ayuda-lista li { margin-bottom: 5px; }
</style>
