<template>
  <div class="page-root">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Conexiones BD</h1>
        <p class="page-subtitle">Fuentes de datos externas — el schema se inyecta al LLM por tema</p>
      </div>
      <button class="btn btn-primary" @click="abrirNueva">+ Nueva conexión</button>
    </div>

    <!-- Lista de conexiones -->
    <div class="conexiones-grid">
      <div v-for="c in conexiones" :key="c.id" class="conexion-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-nombre">{{ c.nombre }}</div>
            <div class="card-meta">
              <span class="badge badge-tipo">{{ c.tipo }}</span>
              <span class="card-host">{{ c.host }}:{{ c.puerto }} / {{ c.base_datos }}</span>
            </div>
          </div>
          <div class="card-estado" :class="estadoClase(c.id)">
            {{ estadoTexto(c.id) }}
          </div>
        </div>
        <div v-if="c.notas" class="card-notas">{{ c.notas }}</div>
        <div v-if="c.ultima_sync" class="card-sync">
          Última sync: {{ fmtFecha(c.ultima_sync) }}
        </div>
        <div class="card-actions">
          <button class="btn btn-secondary" @click="probarConexion(c)" :disabled="testeando[c.id]">
            {{ testeando[c.id] ? 'Probando...' : 'Probar conexión' }}
          </button>
          <button class="btn btn-secondary" @click="abrirEditar(c)">Editar</button>
          <button class="btn btn-danger" @click="eliminar(c)">Eliminar</button>
        </div>
        <div v-if="resultadoTest[c.id]" class="test-result" :class="resultadoTest[c.id].ok ? 'test-ok' : 'test-err'">
          {{ resultadoTest[c.id].mensaje }}
          <div v-if="resultadoTest[c.id].tablas_disponibles?.length" class="test-tablas">
            {{ resultadoTest[c.id].tablas_disponibles.length }} tablas disponibles
          </div>
        </div>
      </div>

      <div v-if="!conexiones.length && !cargando" class="empty-state">
        <p>No hay conexiones configuradas.</p>
        <button class="btn btn-primary" @click="abrirNueva">Crear primera conexión</button>
      </div>
    </div>

    <!-- Modal crear/editar -->
    <div v-if="modal.abierto" class="modal-overlay" @click.self="cerrarModal">
      <div class="modal-panel">
        <div class="modal-header">
          <h2 class="modal-title">{{ modal.editando ? 'Editar conexión' : 'Nueva conexión' }}</h2>
          <button class="btn-close" @click="cerrarModal">✕</button>
        </div>

        <div class="form-body">
          <div class="form-row">
            <div class="input-group">
              <label>Nombre *</label>
              <input v-model="form.nombre" placeholder="ej: Ventas Hostinger" class="input" />
            </div>
            <div class="input-group">
              <label>Tipo BD</label>
              <select v-model="form.tipo" class="input">
                <option value="mariadb">MariaDB</option>
                <option value="mysql">MySQL</option>
                <option value="postgresql">PostgreSQL</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="input-group flex-3">
              <label>Host *</label>
              <input v-model="form.host" placeholder="109.106.250.195" class="input" />
            </div>
            <div class="input-group flex-1">
              <label>Puerto</label>
              <input v-model.number="form.puerto" type="number" placeholder="3306" class="input" />
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <label>Base de datos *</label>
              <input v-model="form.base_datos" placeholder="nombre_base_datos" class="input" />
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <label>Usuario *</label>
              <input v-model="form.usuario" placeholder="usuario_readonly" class="input" />
            </div>
            <div class="input-group">
              <label>Password</label>
              <input v-model="form.password" type="password" placeholder="••••••••" class="input" autocomplete="new-password" />
            </div>
          </div>

          <div class="input-group">
            <label>Notas (opcional)</label>
            <textarea v-model="form.notas" class="input textarea" rows="2"
              placeholder="ej: BD de ventas. Solo lectura. Tablas resumen_ventas_*"></textarea>
          </div>
        </div>

        <div v-if="modal.error" class="form-error">{{ modal.error }}</div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="cerrarModal">Cancelar</button>
          <button class="btn btn-primary" @click="guardar" :disabled="modal.guardando">
            {{ modal.guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from 'src/services/api'

const conexiones   = ref([])
const cargando     = ref(false)
const testeando    = ref({})
const resultadoTest = ref({})

const modal = ref({ abierto: false, editando: null, error: '', guardando: false })
const form  = ref(formVacio())

function formVacio() {
  return { nombre: '', tipo: 'mariadb', host: '', puerto: 3306,
           base_datos: '', usuario: '', password: '', notas: '' }
}

onMounted(cargar)

async function cargar() {
  cargando.value = true
  try {
    const data = await api('/api/ia/conexiones')
    conexiones.value = Array.isArray(data) ? data : []
  } finally {
    cargando.value = false
  }
}

async function probarConexion(c) {
  testeando.value[c.id] = true
  resultadoTest.value[c.id] = null
  try {
    const r = await api(`/api/ia/conexiones/${c.id}/test`, { method: 'POST' })
    resultadoTest.value[c.id] = r
  } catch (e) {
    resultadoTest.value[c.id] = { ok: false, mensaje: e.message }
  } finally {
    testeando.value[c.id] = false
  }
}

function estadoClase(id) {
  const r = resultadoTest.value[id]
  if (!r) return ''
  return r.ok ? 'estado-ok' : 'estado-err'
}
function estadoTexto(id) {
  const r = resultadoTest.value[id]
  if (!r) return ''
  return r.ok ? '✓ Conectado' : '✗ Error'
}

function abrirNueva() {
  form.value = formVacio()
  modal.value = { abierto: true, editando: null, error: '', guardando: false }
}
function abrirEditar(c) {
  form.value = { nombre: c.nombre, tipo: c.tipo, host: c.host, puerto: c.puerto,
                 base_datos: c.base_datos, usuario: c.usuario, password: '', notas: c.notas || '' }
  modal.value = { abierto: true, editando: c.id, error: '', guardando: false }
}
function cerrarModal() {
  modal.value.abierto = false
}

async function guardar() {
  if (!form.value.nombre || !form.value.host || !form.value.usuario || !form.value.base_datos) {
    modal.value.error = 'nombre, host, usuario y base de datos son obligatorios'
    return
  }
  modal.value.guardando = true
  modal.value.error = ''
  try {
    const body = { ...form.value }
    if (modal.value.editando) {
      await api(`/api/ia/conexiones/${modal.value.editando}`, { method: 'PUT', body: JSON.stringify(body) })
    } else {
      await api('/api/ia/conexiones', { method: 'POST', body: JSON.stringify(body) })
    }
    cerrarModal()
    await cargar()
  } catch (e) {
    modal.value.error = e.message
  } finally {
    modal.value.guardando = false
  }
}

async function eliminar(c) {
  if (!confirm(`¿Eliminar la conexión "${c.nombre}"?`)) return
  try {
    await api(`/api/ia/conexiones/${c.id}`, { method: 'DELETE' })
    await cargar()
  } catch (e) {
    alert(e.message)
  }
}

function fmtFecha(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<style scoped>
.page-root { padding: 32px; max-width: 900px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 28px;
}
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin: 0; }

.conexiones-grid { display: flex; flex-direction: column; gap: 12px; }

.conexion-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.card-nombre { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.card-meta { display: flex; align-items: center; gap: 8px; }
.card-host { font-size: 12px; color: var(--text-tertiary); font-family: monospace; }
.card-notas { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
.card-sync { font-size: 11px; color: var(--text-tertiary); margin-bottom: 10px; }
.card-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.badge-tipo {
  font-size: 11px; font-weight: 500; padding: 2px 8px;
  border-radius: 4px; background: var(--bg-surface);
  color: var(--text-secondary); border: 1px solid var(--border-default);
  text-transform: uppercase; letter-spacing: 0.04em;
}

.card-estado { font-size: 12px; font-weight: 500; }
.estado-ok { color: #4ade80; }
.estado-err { color: #f87171; }

.test-result {
  margin-top: 10px; padding: 8px 12px; border-radius: 6px;
  font-size: 12px; font-weight: 500;
}
.test-ok  { background: rgba(74,222,128,0.1); color: #4ade80; }
.test-err { background: rgba(248,113,113,0.1); color: #f87171; }
.test-tablas { font-weight: 400; margin-top: 2px; opacity: 0.8; }

.empty-state {
  text-align: center; padding: 48px; color: var(--text-tertiary);
  background: var(--bg-card); border: 1px dashed var(--border-default); border-radius: var(--radius-lg);
}
.empty-state p { margin-bottom: 16px; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-panel {
  background: var(--bg-modal); border: 1px solid var(--border-default);
  border-radius: var(--radius-xl); width: 540px; max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px 0;
}
.modal-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0; }
.btn-close {
  background: none; border: none; color: var(--text-tertiary);
  cursor: pointer; font-size: 16px; padding: 4px;
}
.btn-close:hover { color: var(--text-primary); }
.form-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; gap: 12px; }
.input-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.input-group label { font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.flex-3 { flex: 3; }
.flex-1 { flex: 1; }
.input {
  background: var(--bg-input); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 8px 10px;
  font-size: 13px; color: var(--text-primary); outline: none;
  transition: border-color 120ms;
}
.input:focus { border-color: var(--border-focus); }
.textarea { resize: vertical; font-family: inherit; }
select.input { cursor: pointer; }
.form-error {
  margin: 0 24px; padding: 10px 12px; background: rgba(248,113,113,0.1);
  border: 1px solid rgba(248,113,113,0.3); border-radius: 6px;
  font-size: 12px; color: #f87171;
}
.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 16px 24px; border-top: 1px solid var(--border-default);
}

/* Botones */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: var(--radius-md);
  font-size: 13px; font-weight: 500; cursor: pointer;
  border: 1px solid transparent; transition: opacity 120ms;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary  { background: #5e6ad2; color: #fff; border-color: #5e6ad2; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-secondary {
  background: var(--bg-surface); color: var(--text-primary);
  border-color: var(--border-default);
}
.btn-secondary:hover:not(:disabled) { background: var(--bg-card-hover); }
.btn-danger { background: rgba(248,113,113,0.1); color: #f87171; border-color: rgba(248,113,113,0.3); }
.btn-danger:hover:not(:disabled) { background: rgba(248,113,113,0.2); }
</style>
