<template>
  <Teleport to="body">
    <Transition :name="isMobile ? 'sheet' : 'modal'">
      <div v-if="modelValue" class="form-overlay" @click.self="$emit('update:modelValue', false)">

        <!-- Contenedor: modal en desktop, bottom sheet en mobile -->
        <div class="form-container" :class="isMobile ? 'is-sheet' : 'is-modal'">

          <!-- Handle (solo mobile) -->
          <div v-if="isMobile" class="sheet-handle"></div>

          <!-- Header -->
          <div class="form-header">
            <span class="panel-header-tipo">{{ editar ? 'Editar tarea' : 'Nueva tarea' }}</span>
            <div class="panel-header-actions">
              <button class="btn-icon" title="Guardar" :disabled="!form.titulo || !form.categoria_id || guardando" @click="guardar">
                <span class="material-icons" style="font-size:18px;color:var(--accent)">check</span>
              </button>
              <button type="button" class="btn-icon" title="Cerrar" @click="$emit('update:modelValue', false)">
                <span class="material-icons" style="font-size:18px">close</span>
              </button>
            </div>
          </div>

          <!-- Body -->
          <div class="form-body">
            <!-- Título -->
            <input
              ref="tituloRef"
              class="input-field titulo-input"
              v-model="form.titulo"
              placeholder="¿Qué hay que hacer?"
              @blur="tfSugerirSiNecesario"
            />

            <!-- Categorías como chips -->
            <div class="form-section-label">
              Categoría
              <span v-if="iaLoading" class="material-icons" style="font-size:12px;color:var(--accent);animation:spin 1s linear infinite;margin-left:4px">autorenew</span>
            </div>
            <div class="cats-grid">
              <button
                type="button"
                v-for="c in categorias"
                :key="c.id"
                class="cat-chip"
                :class="{ selected: form.categoria_id === c.id }"
                @click="form.categoria_id = c.id; tfChipClickCount++"
              >
                <span class="cat-dot" :style="{ background: c.color }"></span>
                {{ c.nombre.replace(/_/g, ' ') }}
              </button>
            </div>

            <!-- OP Effi (solo si categoría es producción) -->
            <div v-if="categoriaSeleccionada?.es_produccion" class="input-group">
              <label class="input-label">OP Effi</label>
              <OpSelector v-model="form.id_op" />
            </div>

            <!-- Proyecto + Etiquetas -->
            <div class="form-row-2">
              <div class="input-group">
                <label class="input-label">Proyecto</label>
                <ProyectoSelector v-model="form.proyecto_id" :proyectos="proyectos" />
              </div>
              <div class="input-group">
                <label class="input-label">Etiquetas</label>
                <EtiquetasSelector v-model="form.etiquetas" :etiquetas="etiquetas" />
              </div>
            </div>

            <!-- Fila fecha + responsable + prioridad -->
            <div class="form-row-3">
              <div class="input-group">
                <label class="input-label">¿Para cuándo?</label>
                <input type="date" class="input-field" v-model="form.fecha_limite" />
              </div>
              <div class="input-group">
                <label class="input-label">Responsable</label>
                <select class="input-field select-field" v-model="form.responsable">
                  <option v-for="u in usuarios" :key="u.email" :value="u.email">{{ u.nombre }}</option>
                </select>
              </div>
              <div class="input-group">
                <label class="input-label">Prioridad</label>
                <select class="input-field select-field" v-model="form.prioridad">
                  <option>Baja</option><option>Media</option><option>Alta</option><option>Urgente</option>
                </select>
              </div>
            </div>

            <!-- Descripción -->
            <div class="input-group">
              <label class="input-label">Descripción (opcional)</label>
              <textarea class="input-field" v-model="form.descripcion" rows="3" placeholder="Contexto, pasos, notas..." />
            </div>
          </div>

          <!-- Footer con botones -->
          <div class="form-footer">
            <button type="button" class="form-btn-cancel" @click="$emit('update:modelValue', false)">Cancelar</button>
            <button class="form-btn-crear" :disabled="!form.titulo || !form.categoria_id || guardando" @click="guardar">
              {{ guardando ? 'Guardando...' : (editar ? 'Guardar tarea' : 'Crear tarea') }}
            </button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { api } from 'src/services/api'
import { crearTarea, sugerirCategoria } from 'src/composables/useTareas'
import { useAuthStore } from 'src/stores/authStore'
import OpSelector        from 'src/components/OpSelector.vue'
import ProyectoSelector  from 'src/components/ProyectoSelector.vue'
import EtiquetasSelector from 'src/components/EtiquetasSelector.vue'

const props = defineProps({
  modelValue:  Boolean,
  tareaEditar: { type: Object, default: null },
  categorias:  { type: Array, default: () => [] },
  proyectos:   { type: Array, default: () => [] },
  etiquetas:   { type: Array, default: () => [] },
  usuarios:    { type: Array, default: () => [] },
  defaults:    { type: Object, default: () => ({}) }
})
const emit = defineEmits(['update:modelValue', 'guardada'])

const auth      = useAuthStore()
const guardando = ref(false)
const tituloRef = ref(null)
const isMobile  = computed(() => window.innerWidth <= 768)

const form = ref({
  titulo: '', descripcion: '', categoria_id: null, proyecto_id: null,
  prioridad: 'Media', responsable: auth.usuario?.email || '',
  fecha_limite: '', id_op: '', etiquetas: []
})

const iaLoading   = ref(false)
let tfChipClickCount = 0

async function tfSugerirSiNecesario() {
  if (editar.value || !form.value.titulo || form.value.titulo.length < 4) return
  if (form.value.categoria_id) return  // ya tiene categoría
  const clicksBefore = tfChipClickCount
  iaLoading.value = true
  const sug = await sugerirCategoria(form.value.titulo)
  iaLoading.value = false
  if (sug?.categoria_id && tfChipClickCount === clicksBefore) form.value.categoria_id = sug.categoria_id
}

let tfDebounce = null
watch(() => form.value.titulo, (val) => {
  if (tfDebounce) clearTimeout(tfDebounce)
  if (!val || val.length < 4 || editar.value) return
  form.value.categoria_id = null  // título cambió → resetear categoría
  tfDebounce = setTimeout(tfSugerirSiNecesario, 1000)
})

const editar = computed(() => !!props.tareaEditar)
const categoriaSeleccionada = computed(() => props.categorias.find(c => c.id === form.value.categoria_id))

watch(() => props.modelValue, async (val) => {
  if (!val) return
  if (props.tareaEditar) {
    form.value = {
      titulo:       props.tareaEditar.titulo || '',
      descripcion:  props.tareaEditar.descripcion || '',
      categoria_id: props.tareaEditar.categoria_id,
      proyecto_id:  props.tareaEditar.proyecto_id || null,
      prioridad:    props.tareaEditar.prioridad || 'Media',
      responsable:  props.tareaEditar.responsable || auth.usuario?.email || '',
      fecha_limite: props.tareaEditar.fecha_limite || '',
      id_op:        props.tareaEditar.id_op || '',
      etiquetas:    (props.tareaEditar.etiquetas || []).map(e => e.id)
    }
  } else {
    const d = props.defaults || {}
    form.value = {
      titulo: '', descripcion: '',
      categoria_id: d.categoria_id || props.categorias[0]?.id || null,
      proyecto_id: d.proyecto_id || null,
      prioridad: d.prioridad || 'Media',
      responsable: d.responsable || auth.usuario?.email || '',
      fecha_limite: d.fecha_limite || '',
      id_op: d.id_op || '',
      etiquetas: d.etiquetas || []
    }
  }
  await nextTick()
  tituloRef.value?.focus()
})

async function guardar() {
  if (!form.value.titulo || guardando.value) return
  guardando.value = true
  try {
    let tarea
    if (editar.value) {
      const data = await api(`/api/gestion/tareas/${props.tareaEditar.id}`, { method: 'PUT', body: JSON.stringify(form.value) })
      tarea = data.tarea
    } else {
      // Sugerencia IA si no eligió categoría
      if (!form.value.categoria_id) await tfSugerirSiNecesario()
      if (!form.value.categoria_id) return // categoría requerida
      tarea = await crearTarea(form.value)
    }
    emit('guardada', tarea)
    emit('update:modelValue', false)
  } catch (e) { console.error(e) } finally { guardando.value = false }
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg); } }
/* Overlay */
.form-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Contenedor común */
.form-container {
  background: var(--bg-modal);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Desktop: modal centrado */
.is-modal {
  width: 540px;
  max-width: 96vw;
  max-height: 90vh;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

/* Mobile: bottom sheet */
.is-sheet {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  border-radius: 16px 16px 0 0;
  max-height: 92dvh;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* Handle bar (mobile) */
.sheet-handle {
  width: 36px; height: 4px;
  background: var(--border-strong);
  border-radius: 2px;
  margin: 10px auto 2px;
}

.form-header {
  display: flex; align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.form-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.titulo-input {
  font-size: 15px;
  font-weight: 500;
  padding: 10px 12px;
}

/* Categorías grid */
.form-section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.cats-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.cat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 80ms;
  font-family: var(--font-sans);
}
.cat-chip:hover { border-color: var(--border-default); color: var(--text-primary); }
.cat-chip.selected {
  background: var(--bg-row-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
  font-weight: 500;
}
.cat-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Filas */
.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  align-items: start;
}
.form-row-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}
@media (max-width: 768px) {
  .form-row-2 { grid-template-columns: 1fr; }
  .form-row-3 { grid-template-columns: 1fr 1fr; }
}

/* Footer */
.form-footer {
  display: flex; gap: 8px; justify-content: flex-end;
  padding: 12px 16px; border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.form-btn-cancel {
  height: 32px; padding: 0 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border-default); background: transparent;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-sans);
}
.form-btn-cancel:hover { background: var(--bg-card-hover); }
.form-btn-crear {
  height: 32px; padding: 0 16px; border-radius: var(--radius-md);
  border: none; background: #fff; color: #111;
  font-size: 12px; font-weight: 600; cursor: pointer;
  font-family: var(--font-sans);
}
.form-btn-crear:disabled { opacity: 0.4; cursor: default; }
.form-btn-crear:hover:not(:disabled) { background: var(--bg-card-hover); }

/* Transiciones */
.modal-enter-active, .modal-leave-active { transition: opacity 150ms; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .form-container, .modal-leave-active .form-container { transition: transform 150ms, opacity 150ms; }
.modal-enter-from .form-container, .modal-leave-to .form-container { transform: scale(0.97); opacity: 0; }

.sheet-enter-active, .sheet-leave-active { transition: opacity 200ms; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
.sheet-enter-active .is-sheet, .sheet-leave-active .is-sheet { transition: transform 250ms cubic-bezier(0.32,0.72,0,1); }
.sheet-enter-from .is-sheet, .sheet-leave-to .is-sheet { transform: translateY(100%); }
</style>
