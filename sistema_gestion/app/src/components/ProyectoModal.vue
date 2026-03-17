<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="proyecto-modal-overlay" @click.self="cerrar">
        <div class="proyecto-modal">
          <!-- Header -->
          <div class="proyecto-modal-header">
            <span class="proyecto-color-preview" :style="{ background: form.color }"></span>
            <span class="proyecto-modal-title">{{ proyectoEditar ? 'Editar proyecto' : 'Nuevo proyecto' }}</span>
            <button class="btn-icon" @click="cerrar">
              <span class="material-icons" style="font-size:18px">close</span>
            </button>
          </div>

          <!-- Body -->
          <div class="proyecto-modal-body">
            <!-- Paleta de colores -->
            <div class="campo-label">Color</div>
            <div class="color-paleta">
              <button
                v-for="c in COLORES"
                :key="c"
                class="color-dot"
                :class="{ selected: form.color === c }"
                :style="{ background: c }"
                @click="form.color = c"
              />
            </div>

            <!-- Nombre -->
            <div class="campo-label" style="margin-top:16px">
              Nombre <span style="color:var(--color-error)">*</span>
            </div>
            <input
              ref="inputNombre"
              v-model="form.nombre"
              class="input-field"
              placeholder="Ej: Rediseño web, Lanzamiento Q2..."
              maxlength="80"
              @keydown.enter.prevent="guardar"
              @keydown.escape="cerrar"
            />

            <!-- Descripción -->
            <div class="campo-label" style="margin-top:16px">Descripción <span class="opcional">(opcional)</span></div>
            <textarea
              v-model="form.descripcion"
              class="input-field"
              rows="2"
              placeholder="¿De qué trata este proyecto?"
              style="resize:vertical;min-height:56px"
            />
          </div>

          <!-- Footer -->
          <div class="proyecto-modal-footer">
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

const COLORES = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#00C853', '#14b8a6', '#3b82f6', '#8b5cf6',
  '#ec4899', '#607D8B'
]

const props = defineProps({
  modelValue:    { type: Boolean, default: false },
  proyectoEditar: { type: Object, default: null }
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const inputNombre = ref(null)
const guardando   = ref(false)
const form = ref({ nombre: '', descripcion: '', color: '#00C853' })

watch(() => props.modelValue, (val) => {
  if (val) {
    if (props.proyectoEditar) {
      form.value = {
        nombre:      props.proyectoEditar.nombre || '',
        descripcion: props.proyectoEditar.descripcion || '',
        color:       props.proyectoEditar.color || '#00C853'
      }
    } else {
      form.value = { nombre: '', descripcion: '', color: '#00C853' }
    }
    nextTick(() => inputNombre.value?.focus())
  }
})

function cerrar() {
  emit('update:modelValue', false)
}

async function guardar() {
  if (!form.value.nombre.trim() || guardando.value) return
  guardando.value = true
  try {
    let data
    if (props.proyectoEditar) {
      data = await api(`/api/gestion/proyectos/${props.proyectoEditar.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          nombre:      form.value.nombre.trim(),
          descripcion: form.value.descripcion.trim(),
          color:       form.value.color
        })
      })
      emit('guardado', { ...data.proyecto, _accion: 'editado' })
    } else {
      data = await api('/api/gestion/proyectos', {
        method: 'POST',
        body: JSON.stringify({
          nombre:      form.value.nombre.trim(),
          descripcion: form.value.descripcion.trim(),
          color:       form.value.color
        })
      })
      emit('guardado', { ...data.proyecto, _accion: 'creado' })
    }
    cerrar()
  } catch (e) { console.error(e) } finally { guardando.value = false }
}
</script>

<style scoped>
.proyecto-modal-overlay {
  position: fixed; inset: 0;
  background: var(--bg-overlay);
  z-index: 500;
  display: flex; align-items: center; justify-content: center;
}

.proyecto-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  width: 380px;
  max-width: 94vw;
  display: flex; flex-direction: column;
  overflow: hidden;
}

.proyecto-modal-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 16px 14px;
  border-bottom: 1px solid var(--border-subtle);
}
.proyecto-color-preview {
  width: 14px; height: 14px;
  border-radius: 50%; flex-shrink: 0;
  transition: background 150ms;
}
.proyecto-modal-title {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  flex: 1;
}

.proyecto-modal-body {
  padding: 18px 16px 12px;
}

.campo-label {
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.opcional { font-weight: 400; text-transform: none; letter-spacing: 0; }

/* Paleta de colores */
.color-paleta {
  display: flex; gap: 8px; flex-wrap: wrap;
}
.color-dot {
  width: 22px; height: 22px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 100ms, border-color 100ms;
  outline: none;
}
.color-dot:hover { transform: scale(1.15); }
.color-dot.selected {
  border-color: var(--text-primary);
  transform: scale(1.2);
  box-shadow: 0 0 0 1px var(--bg-card);
}

.proyecto-modal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px 14px;
  border-top: 1px solid var(--border-subtle);
}

/* Transición */
.modal-enter-active, .modal-leave-active {
  transition: opacity 150ms;
}
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .proyecto-modal,
.modal-leave-active .proyecto-modal {
  transition: transform 150ms, opacity 150ms;
}
.modal-enter-from .proyecto-modal,
.modal-leave-to .proyecto-modal {
  transform: scale(0.97); opacity: 0;
}
</style>
