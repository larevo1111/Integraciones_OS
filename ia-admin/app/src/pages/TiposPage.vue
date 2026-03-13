<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Tipos de consulta</h1>
      <p class="page-subtitle">Reglas de enrutamiento — qué agente usar según el tipo de pregunta</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ tipos.length }} tipos configurados</span>
          <button class="btn btn-primary" @click="abrirNuevo">
            <PlusIcon :size="13" /> Nuevo tipo
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Descripción</th>
              <th>Agente preferido</th>
              <th>Necesita BD</th>
              <th>Necesita imágenes</th>
              <th>Max tokens resp.</th>
              <th>Activo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="t in tipos"
              :key="t.tipo"
              :class="{ selected: seleccionado?.tipo === t.tipo }"
              @click="seleccionar(t)"
            >
              <td class="mono">{{ t.tipo }}</td>
              <td style="color:var(--text-secondary);max-width:260px;overflow:hidden;text-overflow:ellipsis">{{ t.descripcion }}</td>
              <td>
                <span class="badge badge-info">{{ t.agente_preferido }}</span>
              </td>
              <td>
                <span v-if="t.requiere_bd" class="badge badge-success">Sí</span>
                <span v-else class="badge badge-neutral">No</span>
              </td>
              <td>
                <span v-if="t.puede_generar_imagen" class="badge badge-success">Sí</span>
                <span v-else class="badge badge-neutral">No</span>
              </td>
              <td>{{ t.max_tokens_respuesta ?? '—' }}</td>
              <td>
                <label class="toggle" @click.stop>
                  <input type="checkbox" :checked="t.activo" @change="toggleActivo(t)" />
                  <div class="toggle-track"></div>
                  <div class="toggle-thumb"></div>
                </label>
              </td>
              <td>
                <button class="btn-icon" @click.stop="seleccionar(t)">
                  <PencilIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Info sobre el flujo de enrutamiento -->
      <div class="card" style="margin-top:16px">
        <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-tertiary);margin-bottom:10px">
          Flujo de enrutamiento
        </div>
        <div style="font-size:13px;color:var(--text-secondary);line-height:1.7">
          1. El <strong>router</strong> (gemma-router / groq-llama) recibe la pregunta y determina el tipo de consulta.<br>
          2. Se busca el tipo en esta tabla → se obtiene <code style="font-family:var(--font-mono);background:var(--bg-row-hover);padding:1px 5px;border-radius:3px">agente_preferido</code>.<br>
          3. Si ese agente no está activo o no tiene key → se usa el siguiente por <code style="font-family:var(--font-mono);background:var(--bg-row-hover);padding:1px 5px;border-radius:3px">orden</code> en la tabla de agentes.<br>
          4. La respuesta se formatea y se registra en logs.
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="seleccionado" class="overlay" @click="cerrar" />
    </transition>

    <!-- Panel lateral -->
    <transition name="panel">
      <div v-if="seleccionado" class="side-panel">
        <div class="side-panel-header">
          <span class="side-panel-title">{{ esNuevo ? 'Nuevo tipo' : seleccionado.tipo }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Tipo (slug) *</label>
            <input class="input-field" v-model="form.tipo" placeholder="analisis_datos" :readonly="!esNuevo" />
          </div>
          <div class="input-group">
            <label class="input-label">Descripción</label>
            <input class="input-field" v-model="form.descripcion" placeholder="Preguntas con SQL sobre datos de ventas" />
          </div>
          <div class="input-group">
            <label class="input-label">Agente preferido *</label>
            <select class="input-field" v-model="form.agente_preferido">
              <option v-for="ag in slugsAgentes" :key="ag" :value="ag">{{ ag }}</option>
            </select>
          </div>
          <div class="divider" />
          <div class="input-group">
            <label class="input-label">Prompt de sistema</label>
            <textarea class="input-field" v-model="form.system_prompt" rows="5" placeholder="Eres un analista..." />
          </div>
          <div class="divider" />
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="input-group">
              <label class="input-label">Requiere BD</label>
              <label class="toggle" style="margin-top:6px">
                <input type="checkbox" v-model="form.requiere_bd" />
                <div class="toggle-track"></div>
                <div class="toggle-thumb"></div>
              </label>
            </div>
            <div class="input-group">
              <label class="input-label">Puede generar imagen</label>
              <label class="toggle" style="margin-top:6px">
                <input type="checkbox" v-model="form.puede_generar_imagen" />
                <div class="toggle-track"></div>
                <div class="toggle-thumb"></div>
              </label>
            </div>
          </div>
          <div class="input-group">
            <label class="input-label">Max tokens respuesta</label>
            <input class="input-field" type="number" v-model.number="form.max_tokens_respuesta" placeholder="2048" />
          </div>
          <div class="input-group" style="display:flex;align-items:center;gap:10px;margin-top:4px">
            <label class="toggle">
              <input type="checkbox" v-model="form.activo" />
              <div class="toggle-track"></div>
              <div class="toggle-thumb"></div>
            </label>
            <span class="input-label" style="margin:0">Activo</span>
          </div>
        </div>
        <div class="side-panel-footer">
          <button v-if="!esNuevo" class="btn btn-danger" @click="eliminar">Eliminar</button>
          <button class="btn btn-secondary" @click="cerrar">Cancelar</button>
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { apiFetch } from 'src/services/api'
import { ref, onMounted } from 'vue'
import { PlusIcon, PencilIcon, XIcon } from 'lucide-vue-next'

const tipos = ref([])
const cargando = ref(true)
const seleccionado = ref(null)
const esNuevo = ref(false)
const form = ref({})
const guardando = ref(false)
const slugsAgentes = ref([])

async function cargar() {
  cargando.value = true
  try {
    const [rt, ra] = await Promise.all([
      apiFetch('/api/ia/tipos-admin').then(r => r.json()),
      apiFetch('/api/ia/agentes-admin').then(r => r.json())
    ])
    tipos.value = rt
    slugsAgentes.value = ra.map(a => a.slug)
  } catch (e) { tipos.value = [] }
  cargando.value = false
}

function seleccionar(t) {
  esNuevo.value = false
  seleccionado.value = t
  form.value = { ...t, activo: !!t.activo, requiere_bd: !!t.requiere_bd, puede_generar_imagen: !!t.puede_generar_imagen }
}

function abrirNuevo() {
  esNuevo.value = true
  seleccionado.value = { tipo: '' }
  form.value = {
    tipo: '', descripcion: '', agente_preferido: slugsAgentes.value[0] ?? '',
    system_prompt: '', requiere_bd: false, puede_generar_imagen: false,
    max_tokens_respuesta: 2048, activo: true
  }
}

function cerrar() { seleccionado.value = null; form.value = {} }

async function toggleActivo(t) {
  try {
    await apiFetch(`/api/ia/tipos-admin/${t.tipo}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activo: !t.activo })
    })
    t.activo = !t.activo
  } catch (e) { alert('Error') }
}

async function guardar() {
  guardando.value = true
  try {
    const url = esNuevo.value ? '/api/ia/tipos-admin' : `/api/ia/tipos-admin/${form.value.tipo}`
    const method = esNuevo.value ? 'POST' : 'PUT'
    const res = await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    if (!res.ok) throw new Error(await res.text())
    cerrar(); await cargar()
  } catch (e) { alert('Error: ' + e.message) }
  guardando.value = false
}

async function eliminar() {
  if (!confirm(`¿Eliminar tipo "${seleccionado.value.tipo}"?`)) return
  try {
    await apiFetch(`/api/ia/tipos-admin/${seleccionado.value.tipo}`, { method: 'DELETE' })
    cerrar(); await cargar()
  } catch (e) { alert('Error') }
}

onMounted(cargar)
</script>
