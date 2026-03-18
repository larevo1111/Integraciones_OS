<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Lógica de Negocio</h1>
      <p class="page-subtitle">Fragmentos RAG que la IA usa como contexto de negocio en cada consulta</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ fragmentos.length }} fragmentos</span>
          <button class="btn btn-primary" @click="abrirNuevo">
            <PlusIcon :size="13" /> Nuevo fragmento
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Concepto</th>
              <th>Keywords</th>
              <th>Palabras</th>
              <th>Siempre presente</th>
              <th>Activo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="f in fragmentos"
              :key="f.id"
              :class="{ selected: seleccionado?.id === f.id }"
              @click="seleccionar(f)"
            >
              <td><strong>{{ f.concepto }}</strong></td>
              <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--text-tertiary)">
                {{ f.keywords || '—' }}
              </td>
              <td>
                <span class="badge badge-neutral">{{ f.palabras ?? 0 }} pal.</span>
              </td>
              <td>
                <span v-if="f.siempre_presente" class="badge badge-success">Siempre</span>
                <span v-else style="font-size:12px;color:var(--text-tertiary)">Por keyword</span>
              </td>
              <td>
                <label class="toggle" @click.stop>
                  <input type="checkbox" :checked="f.activo" @change="toggleActivo(f)" />
                  <div class="toggle-track"></div>
                  <div class="toggle-thumb"></div>
                </label>
              </td>
              <td>
                <button class="btn-icon" @click.stop="seleccionar(f)" title="Editar">
                  <PencilIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Info box -->
      <div class="card" style="max-width:700px;margin-top:16px;background:var(--color-info-bg);border-color:rgba(37,99,235,0.15)">
        <div style="display:flex;gap:10px;align-items:flex-start">
          <BookOpenIcon :size="16" style="color:var(--color-info);margin-top:2px;flex-shrink:0" />
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--color-info);margin-bottom:4px">Cómo funciona el RAG</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
              Los fragmentos marcados como <strong>Siempre presente</strong> se inyectan en cada consulta.
              Los demás se incluyen solo cuando la pregunta contiene sus <strong>keywords</strong>.
              El recuento de palabras se actualiza automáticamente al guardar.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="seleccionado" class="overlay" @click="cerrar" />
    </transition>

    <!-- Panel lateral -->
    <transition name="panel">
      <div v-if="seleccionado" class="side-panel" style="width:440px">
        <div class="side-panel-header">
          <span class="side-panel-title">{{ esNuevo ? 'Nuevo fragmento' : seleccionado.concepto }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Concepto *</label>
            <input class="input-field" v-model="form.concepto" placeholder="ej. Política de devoluciones" />
          </div>
          <div class="input-group">
            <label class="input-label">Keywords (separadas por coma)</label>
            <input class="input-field" v-model="form.keywords" placeholder="devoluci, nota crédito, NC" />
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:3px">La IA activa este fragmento cuando la pregunta contiene alguna de estas palabras</div>
          </div>
          <div class="input-group">
            <label class="input-label">Explicación / contenido *</label>
            <textarea
              class="input-field"
              v-model="form.explicacion"
              rows="12"
              style="resize:vertical;font-size:13px;line-height:1.6;font-family:inherit"
              placeholder="Describe aquí la lógica de negocio..."
            />
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:3px">
              {{ form.explicacion ? contarPalabras(form.explicacion) + ' palabras aprox.' : '0 palabras' }}
            </div>
          </div>
          <div style="display:flex;gap:20px;margin-top:4px">
            <div class="input-group" style="display:flex;align-items:center;gap:10px;margin-bottom:0">
              <label class="toggle">
                <input type="checkbox" v-model="form.siempre_presente" />
                <div class="toggle-track"></div>
                <div class="toggle-thumb"></div>
              </label>
              <span class="input-label" style="margin:0">Siempre presente</span>
            </div>
            <div class="input-group" style="display:flex;align-items:center;gap:10px;margin-bottom:0">
              <label class="toggle">
                <input type="checkbox" v-model="form.activo" />
                <div class="toggle-track"></div>
                <div class="toggle-thumb"></div>
              </label>
              <span class="input-label" style="margin:0">Activo</span>
            </div>
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
import { useAuthStore } from 'src/stores/authStore'
import { ref, onMounted, watch } from 'vue'
import { PlusIcon, PencilIcon, XIcon, BookOpenIcon } from 'lucide-vue-next'

const fragmentos = ref([])
const cargando = ref(true)
const seleccionado = ref(null)
const esNuevo = ref(false)
const form = ref({})
const guardando = ref(false)

async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/ia/logica-negocio')
    fragmentos.value = await res.json()
  } catch (e) { fragmentos.value = [] }
  cargando.value = false
}

function seleccionar(f) {
  esNuevo.value = false
  seleccionado.value = f
  form.value = { ...f, siempre_presente: !!f.siempre_presente, activo: !!f.activo }
}

function abrirNuevo() {
  esNuevo.value = true
  seleccionado.value = { concepto: '' }
  form.value = { concepto: '', keywords: '', explicacion: '', siempre_presente: false, activo: true }
}

function cerrar() { seleccionado.value = null; form.value = {} }

function contarPalabras(texto) {
  return texto.trim().split(/\s+/).filter(Boolean).length
}

async function toggleActivo(f) {
  try {
    await apiFetch(`/api/ia/logica-negocio/${f.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activo: f.activo ? 0 : 1 })
    })
    f.activo = !f.activo
  } catch (e) { alert('Error') }
}

async function guardar() {
  if (!form.value.concepto || !form.value.explicacion) {
    alert('Concepto y Explicación son obligatorios')
    return
  }
  guardando.value = true
  try {
    const url = esNuevo.value ? '/api/ia/logica-negocio' : `/api/ia/logica-negocio/${form.value.id}`
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
  if (!confirm(`¿Eliminar fragmento "${seleccionado.value.concepto}"?`)) return
  try {
    await apiFetch(`/api/ia/logica-negocio/${seleccionado.value.id}`, { method: 'DELETE' })
    cerrar(); await cargar()
  } catch (e) { alert('Error') }
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => { cargar() })

onMounted(cargar)
</script>
