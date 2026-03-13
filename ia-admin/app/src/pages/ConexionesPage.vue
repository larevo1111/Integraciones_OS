<template>
  <div class="page-root">

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Conexiones BD</h1>
        <p class="page-subtitle">Fuentes de datos externas — el schema se inyecta al LLM por tema</p>
      </div>
      <div class="header-actions">
        <!-- Botón ayuda estilo Linear -->
        <button class="btn-help" @click="ayudaAbierta = !ayudaAbierta" :class="{ active: ayudaAbierta }" title="Ayuda">
          <span>?</span>
        </button>
        <button class="btn btn-primary" @click="abrirNueva">+ Nueva conexión</button>
      </div>
    </div>

    <!-- Panel ayuda colapsable -->
    <transition name="ayuda-slide">
      <div v-if="ayudaAbierta" class="ayuda-panel">
        <p><strong>¿Qué es una Conexión BD?</strong><br>
        Es la fuente de datos que la IA usa para responder preguntas con datos reales. Cada área (Comercial, Finanzas, etc.) puede tener su propio conjunto de tablas.</p>
        <p style="margin-top:10px"><strong>Cómo conectar paso a paso:</strong></p>
        <ol class="ayuda-lista">
          <li>Clic en <strong>"+ Nueva conexión"</strong></li>
          <li>Completa host, puerto, base de datos, usuario y contraseña</li>
          <li>Clic en <strong>"Probar conexión"</strong> — debe pasar antes de poder guardar</li>
          <li>Una vez guardada, ve a <strong>Contextos → Schema BD</strong> y selecciona las tablas del área</li>
        </ol>
        <p style="margin-top:10px"><strong>🔒 Seguridad:</strong> aunque el usuario de BD tenga permisos de escritura, el sistema bloquea cualquier modificación en dos capas independientes: validación de sintaxis SQL y modo READ ONLY de sesión.</p>
        <p style="margin-top:8px"><strong>⚠️ Recomendación:</strong> usa siempre un usuario con GRANT SELECT únicamente.</p>
      </div>
    </transition>

    <!-- Lista de conexiones -->
    <div class="conexiones-grid">
      <div v-for="c in conexiones" :key="c.id" class="conexion-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-nombre">{{ c.nombre }}</div>
            <div class="card-meta">
              <span class="badge-tipo">{{ c.tipo }}</span>
              <span class="card-host">{{ c.host }}:{{ c.puerto }} / {{ c.base_datos }}</span>
            </div>
          </div>
          <div v-if="resultadoTest[c.id]" class="card-estado" :class="resultadoTest[c.id].ok ? 'estado-ok' : 'estado-err'">
            {{ resultadoTest[c.id].ok ? '✓ OK' : '✗ Error' }}
          </div>
        </div>
        <div v-if="c.notas" class="card-notas">{{ c.notas }}</div>
        <div class="card-actions">
          <button class="btn btn-secondary" @click="probarConexionGuardada(c)" :disabled="testeando[c.id]">
            {{ testeando[c.id] ? 'Probando...' : 'Probar' }}
          </button>
          <button class="btn btn-secondary" @click="abrirEditar(c)">Editar</button>
          <button class="btn btn-danger" @click="eliminar(c)">Eliminar</button>
        </div>
        <div v-if="resultadoTest[c.id]" class="test-result" :class="resultadoTest[c.id].ok ? 'test-ok' : 'test-err'">
          {{ resultadoTest[c.id].mensaje }}
          <span v-if="resultadoTest[c.id].tablas_disponibles?.length" class="test-tablas">
            — {{ resultadoTest[c.id].tablas_disponibles.length }} tablas
          </span>
        </div>
      </div>

      <div v-if="!conexiones.length && !cargando" class="empty-state">
        <p>No hay conexiones configuradas.</p>
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
              <input v-model="form.nombre" placeholder="ej: Ventas Hostinger" class="input" @input="resetTest" />
            </div>
            <div class="input-group">
              <label>Tipo BD</label>
              <select v-model="form.tipo" class="input" @change="resetTest">
                <option value="mariadb">MariaDB</option>
                <option value="mysql">MySQL</option>
                <option value="postgresql">PostgreSQL</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="input-group flex-3">
              <label>Host *</label>
              <input v-model="form.host" placeholder="109.106.250.195" class="input" @input="resetTest" />
            </div>
            <div class="input-group flex-1">
              <label>Puerto</label>
              <input v-model.number="form.puerto" type="number" placeholder="3306" class="input" @input="resetTest" />
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <label>Base de datos *</label>
              <input v-model="form.base_datos" placeholder="nombre_base_datos" class="input" @input="resetTest" />
            </div>
          </div>

          <div class="form-row">
            <div class="input-group">
              <label>Usuario *</label>
              <input v-model="form.usuario" placeholder="usuario_readonly" class="input" @input="resetTest" />
            </div>
            <div class="input-group">
              <label>Password</label>
              <input v-model="form.password" type="password" placeholder="••••••••" class="input" autocomplete="new-password" @input="resetTest" />
            </div>
          </div>

          <div class="input-group">
            <label>Notas (opcional)</label>
            <textarea v-model="form.notas" class="input textarea" rows="2"
              placeholder="ej: BD de ventas. Solo lectura. Tablas resumen_ventas_*"></textarea>
          </div>

          <!-- Test de conexión -->
          <div class="test-section">
            <button class="btn btn-secondary" @click="probarEnModal" :disabled="modal.testeando || !formCompleto">
              {{ modal.testeando ? 'Probando conexión...' : '⚡ Probar conexión' }}
            </button>
            <div v-if="modal.testResult" class="test-result-inline" :class="modal.testResult.ok ? 'test-ok' : 'test-err'">
              {{ modal.testResult.ok ? '✓' : '✗' }} {{ modal.testResult.mensaje }}
              <span v-if="modal.testResult.tablas_disponibles?.length" class="test-tablas">
                — {{ modal.testResult.tablas_disponibles.length }} tablas
              </span>
            </div>
            <div v-else-if="!modal.editando" class="test-hint">
              La conexión debe probarse antes de guardar
            </div>
          </div>
        </div>

        <div v-if="modal.error" class="form-error">{{ modal.error }}</div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="cerrarModal">Cancelar</button>
          <button class="btn btn-primary" @click="guardar"
            :disabled="modal.guardando || (!modal.editando && !modal.testResult?.ok)"
            :title="!modal.testResult?.ok && !modal.editando ? 'Primero prueba la conexión' : ''">
            {{ modal.guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from 'src/services/api'

const conexiones    = ref([])
const cargando      = ref(false)
const testeando     = ref({})
const resultadoTest = ref({})
const ayudaAbierta  = ref(false)

const modal = ref({
  abierto: false, editando: null, error: '',
  guardando: false, testeando: false, testResult: null
})
const form = ref(formVacio())

function formVacio() {
  return { nombre: '', tipo: 'mariadb', host: '', puerto: 3306,
           base_datos: '', usuario: '', password: '', notas: '' }
}

const formCompleto = computed(() =>
  form.value.host && form.value.usuario && form.value.base_datos
)

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

// Test conexión guardada (desde la card)
async function probarConexionGuardada(c) {
  testeando.value = { ...testeando.value, [c.id]: true }
  resultadoTest.value = { ...resultadoTest.value, [c.id]: null }
  try {
    const r = await api(`/api/ia/conexiones/${c.id}/test`, { method: 'POST' })
    resultadoTest.value = { ...resultadoTest.value, [c.id]: r }
  } catch (e) {
    resultadoTest.value = { ...resultadoTest.value, [c.id]: { ok: false, mensaje: e.message } }
  } finally {
    testeando.value = { ...testeando.value, [c.id]: false }
  }
}

// Test con parámetros crudos (desde el modal)
async function probarEnModal() {
  modal.value.testeando = true
  modal.value.testResult = null
  modal.value.error = ''
  try {
    const r = await api('/api/ia/conexiones/test-params', {
      method: 'POST',
      body: JSON.stringify({
        tipo: form.value.tipo, host: form.value.host,
        puerto: form.value.puerto, usuario: form.value.usuario,
        password: form.value.password, base_datos: form.value.base_datos
      })
    })
    modal.value.testResult = r
  } catch (e) {
    modal.value.testResult = { ok: false, mensaje: e.message }
  } finally {
    modal.value.testeando = false
  }
}

function resetTest() {
  modal.value.testResult = null
}

function abrirNueva() {
  form.value = formVacio()
  modal.value = { abierto: true, editando: null, error: '', guardando: false, testeando: false, testResult: null }
}
function abrirEditar(c) {
  form.value = { nombre: c.nombre, tipo: c.tipo, host: c.host, puerto: c.puerto,
                 base_datos: c.base_datos, usuario: c.usuario, password: '', notas: c.notas || '' }
  // Al editar el test no es obligatorio (la conexión ya existe)
  modal.value = { abierto: true, editando: c.id, error: '', guardando: false, testeando: false, testResult: { ok: true } }
}
function cerrarModal() { modal.value.abierto = false }

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
  } catch (e) { alert(e.message) }
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
  margin-bottom: 20px;
}
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin: 0; }
.header-actions { display: flex; align-items: center; gap: 8px; }

/* Botón ayuda estilo Linear — icono sutil, circular */
.btn-help {
  width: 26px; height: 26px; border-radius: 50%;
  background: none; border: 1px solid var(--border-default);
  color: var(--text-tertiary); font-size: 12px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: border-color 120ms, color 120ms, background 120ms;
  flex-shrink: 0;
}
.btn-help:hover, .btn-help.active {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--bg-surface);
}

/* Panel ayuda */
.ayuda-panel {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-left: 3px solid #5e6ad2; border-radius: var(--radius-lg);
  padding: 16px 20px; font-size: 13px; color: var(--text-secondary);
  line-height: 1.65; margin-bottom: 20px;
}
.ayuda-slide-enter-active, .ayuda-slide-leave-active { transition: all 180ms ease; overflow: hidden; }
.ayuda-slide-enter-from, .ayuda-slide-leave-to { opacity: 0; max-height: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; }
.ayuda-slide-enter-to, .ayuda-slide-leave-from { opacity: 1; max-height: 600px; margin-bottom: 20px; }
.ayuda-lista { padding-left: 18px; margin: 6px 0 0; }
.ayuda-lista li { margin-bottom: 5px; }

/* Cards */
.conexiones-grid { display: flex; flex-direction: column; gap: 12px; }
.conexion-card {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: var(--radius-lg); padding: 16px;
}
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.card-nombre { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
.card-meta { display: flex; align-items: center; gap: 8px; }
.card-host { font-size: 12px; color: var(--text-tertiary); font-family: monospace; }
.card-notas { font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; }
.card-actions { display: flex; gap: 8px; }
.card-estado { font-size: 12px; font-weight: 600; }
.estado-ok { color: #4ade80; }
.estado-err { color: #f87171; }

.badge-tipo {
  font-size: 11px; padding: 2px 7px; border-radius: 4px;
  background: var(--bg-surface); color: var(--text-tertiary);
  border: 1px solid var(--border-default); text-transform: uppercase; letter-spacing: 0.04em;
}

.test-result {
  margin-top: 10px; padding: 7px 12px; border-radius: 6px; font-size: 12px;
}
.test-ok  { background: rgba(74,222,128,0.1); color: #4ade80; }
.test-err { background: rgba(248,113,113,0.1); color: #f87171; }
.test-tablas { opacity: 0.75; }

.empty-state {
  text-align: center; padding: 48px; color: var(--text-tertiary);
  background: var(--bg-card); border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg); font-size: 13px;
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-panel {
  background: var(--bg-modal); border: 1px solid var(--border-default);
  border-radius: var(--radius-xl); width: 540px; max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4); max-height: 90vh; overflow-y: auto;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px 0;
}
.modal-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0; }
.btn-close { background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 16px; padding: 4px; }
.btn-close:hover { color: var(--text-primary); }
.form-body { padding: 18px 24px; display: flex; flex-direction: column; gap: 14px; }
.form-row { display: flex; gap: 12px; }
.input-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.input-group label { font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.flex-3 { flex: 3; } .flex-1 { flex: 1; }
.input {
  background: var(--bg-input); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); padding: 8px 10px;
  font-size: 13px; color: var(--text-primary); outline: none; transition: border-color 120ms;
}
.input:focus { border-color: var(--border-focus); }
.textarea { resize: vertical; font-family: inherit; }
select.input { cursor: pointer; }

/* Sección test dentro del modal */
.test-section {
  display: flex; flex-direction: column; gap: 8px;
  padding: 12px; background: var(--bg-surface);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
}
.test-result-inline { font-size: 12px; font-weight: 500; padding: 6px 10px; border-radius: 6px; }
.test-hint { font-size: 12px; color: var(--text-tertiary); }

.form-error {
  margin: 0 24px; padding: 10px 12px; background: rgba(248,113,113,0.1);
  border: 1px solid rgba(248,113,113,0.3); border-radius: 6px;
  font-size: 12px; color: #f87171;
}
.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 14px 24px; border-top: 1px solid var(--border-default);
}

/* Botones */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: var(--radius-md);
  font-size: 13px; font-weight: 500; cursor: pointer;
  border: 1px solid transparent; transition: opacity 120ms;
}
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-primary { background: #5e6ad2; color: #fff; border-color: #5e6ad2; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-secondary { background: var(--bg-surface); color: var(--text-primary); border-color: var(--border-default); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-card-hover); }
.btn-danger { background: rgba(248,113,113,0.1); color: #f87171; border-color: rgba(248,113,113,0.3); }
.btn-danger:hover:not(:disabled) { background: rgba(248,113,113,0.2); }
</style>
