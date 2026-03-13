<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Agentes</h1>
      <p class="page-subtitle">Modelos de IA configurados — keys, límites y estado</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ agentes.length }} agentes</span>
          <button class="btn btn-primary" @click="abrirNuevo">
            <PlusIcon :size="13" /> Nuevo agente
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Slug</th>
              <th>Nombre</th>
              <th>Proveedor</th>
              <th>Modelo</th>
              <th>RPD</th>
              <th>RPM</th>
              <th>API Key</th>
              <th>Activo</th>
              <th>Orden</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="ag in agentes"
              :key="ag.slug"
              :class="{ selected: seleccionado?.slug === ag.slug }"
              @click="seleccionar(ag)"
            >
              <td class="mono">{{ ag.slug }}</td>
              <td><strong>{{ ag.nombre }}</strong></td>
              <td>
                <span class="badge badge-neutral">{{ ag.proveedor }}</span>
              </td>
              <td class="mono">{{ ag.modelo_id }}</td>
              <td>{{ ag.rate_limit_rpd ?? '∞' }}</td>
              <td>{{ ag.rate_limit_rpm ?? '∞' }}</td>
              <td>
                <span v-if="ag.tiene_key" class="badge badge-success">configurada</span>
                <span v-else class="badge badge-error">falta key</span>
              </td>
              <td>
                <label class="toggle" @click.stop>
                  <input type="checkbox" :checked="ag.activo" @change="toggleActivo(ag)" />
                  <div class="toggle-track"></div>
                  <div class="toggle-thumb"></div>
                </label>
              </td>
              <td>{{ ag.orden }}</td>
              <td>
                <button class="btn-icon" @click.stop="seleccionar(ag)" title="Editar">
                  <PencilIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
          <span class="side-panel-title">{{ esNuevo ? 'Nuevo agente' : seleccionado.nombre }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Slug *</label>
            <input class="input-field" v-model="form.slug" placeholder="gemini-pro" :readonly="!esNuevo" />
          </div>
          <div class="input-group">
            <label class="input-label">Nombre *</label>
            <input class="input-field" v-model="form.nombre" placeholder="Gemini 2.5 Pro" />
          </div>
          <div class="input-group">
            <label class="input-label">Proveedor</label>
            <select class="input-field" v-model="form.proveedor">
              <option>google</option>
              <option>anthropic</option>
              <option>groq</option>
              <option>deepseek</option>
              <option>openai</option>
            </select>
          </div>
          <div class="input-group">
            <label class="input-label">Modelo ID *</label>
            <input class="input-field" v-model="form.modelo_id" placeholder="gemini-2.5-pro" />
          </div>
          <div class="divider" />
          <div class="input-group">
            <label class="input-label">API Key</label>
            <div style="display:flex;gap:6px">
              <input
                class="input-field"
                :type="mostrarKey ? 'text' : 'password'"
                v-model="form.api_key"
                placeholder="Dejar vacío para no cambiar"
                style="flex:1"
              />
              <button class="btn-icon" @click="mostrarKey = !mostrarKey" :title="mostrarKey ? 'Ocultar' : 'Mostrar'">
                <EyeIcon v-if="!mostrarKey" :size="13" />
                <EyeOffIcon v-else :size="13" />
              </button>
            </div>
            <div v-if="!esNuevo" style="font-size:11px;color:var(--text-tertiary);margin-top:4px">
              Estado actual: <strong :style="{ color: seleccionado.tiene_key ? 'var(--color-success)' : 'var(--color-error)' }">
                {{ seleccionado.tiene_key ? 'configurada' : 'no configurada' }}
              </strong>
            </div>
          </div>
          <div class="divider" />
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="input-group">
              <label class="input-label">Límite RPD</label>
              <input class="input-field" type="number" v-model.number="form.rate_limit_rpd" placeholder="1000" />
            </div>
            <div class="input-group">
              <label class="input-label">Límite RPM</label>
              <input class="input-field" type="number" v-model.number="form.rate_limit_rpm" placeholder="60" />
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="input-group">
              <label class="input-label">Costo input (USD/1K tokens)</label>
              <input class="input-field" type="number" step="0.0001" v-model.number="form.costo_input_1k" placeholder="0.00125" />
            </div>
            <div class="input-group">
              <label class="input-label">Costo output (USD/1K tokens)</label>
              <input class="input-field" type="number" step="0.0001" v-model.number="form.costo_output_1k" placeholder="0.005" />
            </div>
          </div>
          <div class="input-group">
            <label class="input-label">Orden de fallback</label>
            <input class="input-field" type="number" v-model.number="form.orden" placeholder="1" />
          </div>
          <div class="input-group">
            <label class="input-label">Capacidades (JSON array)</label>
            <input class="input-field" v-model="form.capacidades" placeholder='["texto","sql"]' />
          </div>
          <div class="input-group" style="display:flex;align-items:center;gap:10px">
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
import { PlusIcon, PencilIcon, XIcon, EyeIcon, EyeOffIcon } from 'lucide-vue-next'

const agentes = ref([])
const cargando = ref(true)
const seleccionado = ref(null)
const esNuevo = ref(false)
const form = ref({})
const guardando = ref(false)
const mostrarKey = ref(false)

async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/ia/agentes-admin')
    agentes.value = await res.json()
  } catch (e) { agentes.value = [] }
  cargando.value = false
}

function seleccionar(ag) {
  esNuevo.value = false
  seleccionado.value = ag
  mostrarKey.value = false
  form.value = {
    slug: ag.slug,
    nombre: ag.nombre,
    proveedor: ag.proveedor,
    modelo_id: ag.modelo_id,
    api_key: '',
    rate_limit_rpd: ag.rate_limit_rpd,
    rate_limit_rpm: ag.rate_limit_rpm,
    costo_input_1k: ag.costo_input_1k,
    costo_output_1k: ag.costo_output_1k,
    capacidades: ag.capacidades,
    orden: ag.orden,
    activo: !!ag.activo
  }
}

function abrirNuevo() {
  esNuevo.value = true
  seleccionado.value = { slug: '', nombre: '', tiene_key: false }
  mostrarKey.value = true
  form.value = {
    slug: '', nombre: '', proveedor: 'google', modelo_id: '',
    api_key: '', rate_limit_rpd: null, rate_limit_rpm: null,
    costo_input_1k: 0, costo_output_1k: 0,
    capacidades: '["texto"]', orden: 99, activo: true
  }
}

function cerrar() {
  seleccionado.value = null
  form.value = {}
}

async function toggleActivo(ag) {
  try {
    await apiFetch(`/api/ia/agentes-admin/${ag.slug}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activo: !ag.activo })
    })
    ag.activo = !ag.activo
  } catch (e) { alert('Error al cambiar estado') }
}

async function guardar() {
  guardando.value = true
  try {
    const url = esNuevo.value ? '/api/ia/agentes-admin' : `/api/ia/agentes-admin/${form.value.slug}`
    const method = esNuevo.value ? 'POST' : 'PUT'
    const res = await apiFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    if (!res.ok) throw new Error(await res.text())
    cerrar()
    await cargar()
  } catch (e) {
    alert('Error: ' + e.message)
  }
  guardando.value = false
}

async function eliminar() {
  if (!confirm(`¿Eliminar agente "${seleccionado.value.slug}"?`)) return
  try {
    await apiFetch(`/api/ia/agentes-admin/${seleccionado.value.slug}`, { method: 'DELETE' })
    cerrar()
    await cargar()
  } catch (e) { alert('Error al eliminar') }
}

onMounted(cargar)
</script>
