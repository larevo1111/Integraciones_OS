<template>
  <Teleport to="body">
    <Transition name="pmodal">
      <div v-if="modelValue" class="pmodal-overlay" @click.self="cerrar">
        <div class="pmodal">

          <!-- Header -->
          <div class="pmodal-header">
            <span class="pmodal-color-preview" :style="{ background: form.color }"></span>
            <span class="pmodal-title">{{ proyectoEditar ? 'Editar proyecto' : 'Nuevo proyecto' }}</span>
            <button class="btn-icon" @click="cerrar">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>

          <!-- Body -->
          <div class="pmodal-body">

            <!-- Paleta de colores -->
            <div class="pmodal-campo-label">Color</div>
            <div class="pmodal-color-paleta">
              <button
                v-for="c in COLORES"
                :key="c"
                class="pmodal-color-dot"
                :class="{ selected: form.color === c }"
                :style="{ background: c }"
                @click="form.color = c"
              />
            </div>

            <!-- Nombre -->
            <div class="pmodal-campo-label" style="margin-top:16px">
              Nombre <span style="color:var(--color-error)">*</span>
            </div>
            <input
              ref="inputNombre"
              v-model="form.nombre"
              class="input-field"
              placeholder="Ej: Rediseño web, Lanzamiento Q2..."
              maxlength="80"
              @keydown.escape="cerrar"
            />

            <!-- Descripción -->
            <div class="pmodal-campo-label" style="margin-top:14px">
              Descripción <span class="pmodal-opcional">(opcional)</span>
            </div>
            <textarea
              v-model="form.descripcion"
              class="input-field"
              rows="2"
              placeholder="¿De qué trata este proyecto?"
              style="resize:vertical;min-height:52px"
            />

            <!-- Responsables -->
            <div class="pmodal-campo-label" style="margin-top:14px">Responsables</div>
            <ResponsablesSelector
              :model-value="form.responsables"
              :usuarios="usuarios"
              @update:model-value="form.responsables = $event"
            />

            <!-- Etiquetas -->
            <div class="pmodal-campo-label" style="margin-top:14px">Etiquetas</div>
            <EtiquetasSelector
              :model-value="form.etiquetas"
              :etiquetas="etiquetasDisponibles"
              @update:model-value="form.etiquetas = $event"
              @etiqueta-creada="e => etiquetasDisponibles.push(e)"
            />

            <!-- Fecha estimada -->
            <div class="pmodal-campo-label" style="margin-top:14px">
              Fecha estimada de finalización <span class="pmodal-opcional">(opcional)</span>
            </div>
            <input
              type="date"
              v-model="form.fecha_estimada_fin"
              class="input-field"
              style="height:30px;font-size:12px"
            />

          </div>

          <!-- Footer -->
          <div class="pmodal-footer">
            <button class="btn btn-ghost btn-sm" @click="cerrar">Cancelar</button>
            <button
              class="btn btn-accent btn-sm"
              :disabled="!form.nombre.trim() || guardando"
              @click="guardar"
            >
              {{ guardando ? '...' : (proyectoEditar ? 'Guardar cambios' : 'Crear proyecto') }}
            </button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { api } from 'src/services/api'
import ResponsablesSelector from './ResponsablesSelector.vue'
import EtiquetasSelector    from './EtiquetasSelector.vue'

const COLORES = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#00C853', '#14b8a6', '#3b82f6', '#8b5cf6',
  '#ec4899', '#607D8B'
]

const props = defineProps({
  modelValue:     { type: Boolean, default: false },
  proyectoEditar: { type: Object,  default: null }
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const inputNombre          = ref(null)
const guardando            = ref(false)
const usuarios             = ref([])
const etiquetasDisponibles = ref([])

const form = ref({
  nombre:           '',
  descripcion:      '',
  color:            '#00C853',
  responsables:     [],
  etiquetas:        [],
  fecha_estimada_fin: ''
})

function resetForm(p = null) {
  form.value = {
    nombre:             p?.nombre            || '',
    descripcion:        p?.descripcion        || '',
    color:              p?.color              || '#00C853',
    responsables:       p?.responsables       || [],
    etiquetas:          (p?.etiquetas || []).map(e => e.id ?? e),
    fecha_estimada_fin: p?.fecha_estimada_fin ? p.fecha_estimada_fin.slice(0, 10) : ''
  }
}

async function cargarCatalogos() {
  try {
    const [uData, eData] = await Promise.allSettled([
      api('/api/gestion/usuarios'),
      api('/api/gestion/etiquetas')
    ])
    if (uData.status === 'fulfilled') usuarios.value = uData.value.usuarios || []
    if (eData.status === 'fulfilled') etiquetasDisponibles.value = eData.value.etiquetas || []
  } catch {}
}

watch(() => props.modelValue, (val) => {
  if (val) {
    resetForm(props.proyectoEditar)
    cargarCatalogos()
    nextTick(() => inputNombre.value?.focus())
  }
})

function cerrar() { emit('update:modelValue', false) }

async function guardar() {
  if (!form.value.nombre.trim() || guardando.value) return
  guardando.value = true
  try {
    const body = {
      nombre:             form.value.nombre.trim(),
      descripcion:        form.value.descripcion.trim() || null,
      color:              form.value.color,
      responsables:       form.value.responsables,
      etiquetas:          form.value.etiquetas,
      fecha_estimada_fin: form.value.fecha_estimada_fin || null
    }
    let data
    if (props.proyectoEditar) {
      data = await api(`/api/gestion/proyectos/${props.proyectoEditar.id}`, {
        method: 'PUT', body: JSON.stringify(body)
      })
      emit('guardado', { ...data.proyecto, _accion: 'editado' })
    } else {
      data = await api('/api/gestion/proyectos', {
        method: 'POST', body: JSON.stringify(body)
      })
      emit('guardado', { ...data.proyecto, _accion: 'creado' })
    }
    cerrar()
  } catch (e) { console.error(e) } finally { guardando.value = false }
}
</script>

<style scoped>
.pmodal-overlay {
  position: fixed; inset: 0;
  background: var(--bg-overlay);
  z-index: 500;
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}

.pmodal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  width: 420px;
  max-width: 100%;
  max-height: 90vh;
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* Header */
.pmodal-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 16px 14px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.pmodal-color-preview {
  width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
  transition: background 150ms;
}
.pmodal-title {
  font-size: 14px; font-weight: 600; color: var(--text-primary); flex: 1;
}

/* Body */
.pmodal-body {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.pmodal-campo-label {
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.pmodal-opcional { font-weight: 400; text-transform: none; letter-spacing: 0; }

/* Paleta colores */
.pmodal-color-paleta { display: flex; gap: 8px; flex-wrap: wrap; }
.pmodal-color-dot {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer; outline: none;
  transition: transform 100ms, border-color 100ms;
}
.pmodal-color-dot:hover { transform: scale(1.15); }
.pmodal-color-dot.selected {
  border-color: var(--text-primary);
  transform: scale(1.2);
  box-shadow: 0 0 0 1px var(--bg-card);
}

/* Footer */
.pmodal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* Transición */
.pmodal-enter-active, .pmodal-leave-active { transition: opacity 150ms; }
.pmodal-enter-from, .pmodal-leave-to { opacity: 0; }
.pmodal-enter-active .pmodal,
.pmodal-leave-active .pmodal {
  transition: transform 150ms, opacity 150ms;
}
.pmodal-enter-from .pmodal,
.pmodal-leave-to .pmodal {
  transform: scale(0.97); opacity: 0;
}
</style>
