<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Ejemplos SQL</h1>
      <p class="page-subtitle">Pares pregunta → SQL que el LLM usa como referencia para generar consultas correctas</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap">
        <div class="tabla-header">
          <div style="display:flex;align-items:center;gap:12px">
            <span class="tabla-titulo">{{ ejemplos.length }} ejemplos</span>
            <input
              class="input-field"
              v-model="filtro"
              placeholder="Buscar..."
              style="width:200px;height:28px;font-size:12px;padding:0 8px"
            />
          </div>
          <button class="btn btn-primary" @click="abrirNuevo">
            <PlusIcon :size="13" /> Nuevo ejemplo
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Pregunta</th>
              <th>Tablas</th>
              <th>Usado</th>
              <th>Última vez</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="ejemplosFiltrados.length === 0">
              <td colspan="5" style="text-align:center;color:var(--text-tertiary);padding:24px">Sin resultados</td>
            </tr>
            <tr
              v-for="ej in ejemplosFiltrados"
              :key="ej.id"
              :class="{ selected: seleccionado?.id === ej.id }"
              @click="seleccionar(ej)"
            >
              <td style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                {{ ej.pregunta }}
              </td>
              <td style="font-size:11px;color:var(--text-tertiary);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                {{ ej.tablas_usadas || '—' }}
              </td>
              <td>
                <span class="badge badge-neutral">{{ ej.veces_usado ?? 0 }}×</span>
              </td>
              <td style="font-size:12px;color:var(--text-tertiary);white-space:nowrap">
                {{ ej.ultima_vez ? formatFecha(ej.ultima_vez) : '—' }}
              </td>
              <td>
                <button class="btn-icon" @click.stop="seleccionar(ej)" title="Editar">
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
          <CodeIcon :size="16" style="color:var(--color-info);margin-top:2px;flex-shrink:0" />
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--color-info);margin-bottom:4px">Cómo funcionan los ejemplos SQL</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
              Cuando el LLM va a generar un SQL, recibe los ejemplos más relevantes como referencia.
              Cuantos más ejemplos correctos existan, mejor será la calidad del SQL generado.
              El campo <strong>palabras_clave</strong> ayuda a seleccionar los ejemplos más relevantes para cada pregunta.
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
      <div v-if="seleccionado" class="side-panel" style="width:520px">
        <div class="side-panel-header">
          <span class="side-panel-title">{{ esNuevo ? 'Nuevo ejemplo SQL' : 'Editar ejemplo' }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Pregunta en lenguaje natural *</label>
            <textarea
              class="input-field"
              v-model="form.pregunta"
              rows="3"
              style="resize:vertical;font-size:13px"
              placeholder="ej. ¿Cuánto vendimos el mes pasado por canal?"
            />
          </div>
          <div class="input-group">
            <label class="input-label">SQL correcto *</label>
            <textarea
              class="input-field"
              v-model="form.sql_generado"
              rows="10"
              style="resize:vertical;font-family:monospace;font-size:12px;line-height:1.6"
              placeholder="SELECT ..."
            />
          </div>
          <div class="input-group">
            <label class="input-label">Tablas usadas (separadas por coma)</label>
            <input
              class="input-field"
              v-model="form.tablas_usadas"
              placeholder="zeffi_facturas_encabezados, zeffi_clientes"
            />
          </div>
          <div class="input-group">
            <label class="input-label">Palabras clave (para selección del ejemplo)</label>
            <input
              class="input-field"
              v-model="form.palabras_clave"
              placeholder="ventas, canal, mes, factura"
            />
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
import { ref, computed, onMounted, watch } from 'vue'
import { apiFetch } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'
import { PlusIcon, PencilIcon, XIcon, CodeIcon } from 'lucide-vue-next'

const ejemplos    = ref([])
const cargando    = ref(true)
const seleccionado = ref(null)
const esNuevo     = ref(false)
const form        = ref({})
const guardando   = ref(false)
const filtro      = ref('')

const ejemplosFiltrados = computed(() => {
  if (!filtro.value) return ejemplos.value
  const f = filtro.value.toLowerCase()
  return ejemplos.value.filter(e =>
    e.pregunta?.toLowerCase().includes(f) ||
    e.tablas_usadas?.toLowerCase().includes(f) ||
    e.palabras_clave?.toLowerCase().includes(f)
  )
})

async function cargar() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/ia/ejemplos-sql')
    ejemplos.value = await res.json()
  } catch { ejemplos.value = [] }
  cargando.value = false
}

function seleccionar(ej) {
  esNuevo.value = false
  seleccionado.value = ej
  form.value = { ...ej }
}

function abrirNuevo() {
  esNuevo.value = true
  seleccionado.value = { pregunta: '' }
  form.value = { pregunta: '', sql_generado: '', tablas_usadas: '', palabras_clave: '' }
}

function cerrar() { seleccionado.value = null; form.value = {} }

async function guardar() {
  if (!form.value.pregunta || !form.value.sql_generado) {
    alert('Pregunta y SQL son obligatorios')
    return
  }
  guardando.value = true
  try {
    const url = esNuevo.value ? '/api/ia/ejemplos-sql' : `/api/ia/ejemplos-sql/${form.value.id}`
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
  if (!confirm('¿Eliminar este ejemplo SQL?')) return
  try {
    await apiFetch(`/api/ia/ejemplos-sql/${seleccionado.value.id}`, { method: 'DELETE' })
    cerrar(); await cargar()
  } catch { alert('Error') }
}

function formatFecha(f) {
  const d = new Date(f)
  return d.toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'2-digit' })
}

const auth = useAuthStore()
watch(() => auth.empresa_activa?.uid, () => cargar())
onMounted(cargar)
</script>
