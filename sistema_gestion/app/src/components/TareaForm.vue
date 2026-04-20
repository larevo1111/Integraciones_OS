<template>
  <Teleport to="body">
    <Transition :name="isMobile ? 'sheet' : 'modal'">
      <div v-if="modelValue" class="form-overlay" @click.self="$emit('update:modelValue', false)">

        <!-- Contenedor: modal en desktop, bottom sheet en mobile -->
        <div
          class="form-container"
          :class="isMobile ? 'is-sheet' : 'is-modal'"
          :style="isMobile && sheetDragY > 0 ? { transform: `translateY(${sheetDragY}px)`, transition: 'none' } : {}"
        >

          <!-- Handle draggable (solo mobile) -->
          <div
            v-if="isMobile"
            class="sheet-handle-wrap"
            @touchstart.passive="onDragStart"
            @touchmove.passive="onDragMove"
            @touchend="onDragEnd"
          >
            <div class="sheet-handle"></div>
          </div>

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

          <!-- Body (form wrapper: Enter en cualquier input dispara guardar; textarea no) -->
          <form class="form-body" @submit.prevent="guardar">
            <!-- Título -->
            <input
              ref="tituloRef"
              class="input-field titulo-input"
              v-model="form.titulo"
              placeholder="¿Qué hay que hacer?"
              @blur="tfSugerirSiNecesario"
            />

            <!-- OP Effi (solo si categoría es producción) -->
            <div v-if="categoriaSeleccionada?.es_produccion" class="input-group">
              <label class="input-label">OP Effi</label>
              <OpSelector v-model="form.id_op" />
            </div>

            <!-- Remisión + Pedido (solo si categoría es empaque) -->
            <div v-if="categoriaSeleccionada?.es_empaque" class="input-group">
              <label class="input-label">Remisión</label>
              <RemisionSelector v-model="form.id_remision" />
            </div>
            <div v-if="categoriaSeleccionada?.es_empaque" class="input-group">
              <label class="input-label">Pedido</label>
              <PedidoSelector v-model="form.id_pedido" />
            </div>

            <!-- Fila de chips compartida -->
            <TareaMetaChips
              :categoria-id="form.categoria_id"
              :prioridad="form.prioridad"
              :etiquetas="form.etiquetas"
              :fecha-limite="form.fecha_limite"
              :responsables="form.responsables"
              :proyecto-id="form.proyecto_id"
              :categorias="categorias"
              :etiquetas-disponibles="etiquetas"
              :usuarios="usuarios"
              :proyectos="proyectos"
              :ia-loading="iaLoading"
              @update:categoria-id="val => { form.categoria_id = val; tfChipClickCount++ }"
              @update:prioridad="val => form.prioridad = val"
              @update:etiquetas="val => form.etiquetas = val"
              @update:fecha-limite="val => form.fecha_limite = val"
              @update:responsables="val => form.responsables = val"
              @update:proyecto-id="val => form.proyecto_id = val"
              @crear-item="tipo => abrirPanelItem(tipo)"
            />

            <!-- Descripción -->
            <div class="input-group">
              <label class="input-label">Descripción (opcional)</label>
              <textarea class="input-field" v-model="form.descripcion" rows="3" placeholder="Contexto, pasos, notas..." />
            </div>
          </form>

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
import { ref, computed, watch, nextTick, inject } from 'vue'
import { api } from 'src/services/api'
import { crearTarea, sugerirCategoria } from 'src/composables/useTareas'
import { useAuthStore } from 'src/stores/authStore'
import OpSelector           from 'src/components/OpSelector.vue'
import RemisionSelector     from 'src/components/RemisionSelector.vue'
import PedidoSelector       from 'src/components/PedidoSelector.vue'
import TareaMetaChips       from 'src/components/TareaMetaChips.vue'

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
const abrirPanelItem = inject('abrirPanelItem', () => {})
const ultimoItemGuardado = inject('ultimoItemGuardado', ref(null))

// Auto-seleccionar proyecto recién creado desde el popover "+ Nuevo proyecto"
watch(ultimoItemGuardado, (p) => {
  if (!p || !props.modelValue) return
  if (p._accion === 'creado' && (p.tipo === 'proyecto' || !p.tipo)) {
    form.value.proyecto_id = p.id
  }
})
const guardando = ref(false)
const tituloRef = ref(null)
const isMobile  = computed(() => window.innerWidth <= 768)

// Drag-to-dismiss del bottom sheet en mobile
const sheetDragY = ref(0)
let sheetDragStartY = 0
function onDragStart(ev) {
  sheetDragStartY = ev.touches[0].clientY
}
function onDragMove(ev) {
  const dy = ev.touches[0].clientY - sheetDragStartY
  sheetDragY.value = Math.max(0, dy)
}
function onDragEnd() {
  // Si arrastró más de 120px → cerrar
  if (sheetDragY.value > 120) {
    sheetDragY.value = 0
    emit('update:modelValue', false)
  } else {
    sheetDragY.value = 0
  }
}

const form = ref({
  titulo: '', descripcion: '', categoria_id: null, proyecto_id: null,
  prioridad: 'Media',
  responsables: auth.usuario?.email ? [auth.usuario.email] : [],
  fecha_limite: '', id_op: '', id_remision: '', id_pedido: '', etiquetas: []
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
    const existingResp = props.tareaEditar.responsables
      || (props.tareaEditar.responsable ? [props.tareaEditar.responsable] : [])
    form.value = {
      titulo:       props.tareaEditar.titulo || '',
      descripcion:  props.tareaEditar.descripcion || '',
      categoria_id: props.tareaEditar.categoria_id,
      proyecto_id:  props.tareaEditar.proyecto_id || null,
      prioridad:    props.tareaEditar.prioridad || 'Media',
      responsables: existingResp,
      fecha_limite: props.tareaEditar.fecha_limite || '',
      id_op:        props.tareaEditar.id_op || '',
      id_remision:  props.tareaEditar.id_remision || '',
      id_pedido:    props.tareaEditar.id_pedido || '',
      etiquetas:    (props.tareaEditar.etiquetas || []).map(e => e.id)
    }
  } else {
    const d = props.defaults || {}
    const defaultResp = auth.usuario?.email ? [auth.usuario.email] : []
    form.value = {
      titulo: '', descripcion: '',
      categoria_id: d.categoria_id || props.categorias[0]?.id || null,
      proyecto_id: d.proyecto_id || null,
      prioridad: d.prioridad || 'Media',
      responsables: d.responsables || defaultResp,
      fecha_limite: d.fecha_limite || '',
      id_op: d.id_op || '',
      id_remision: d.id_remision || '',
      id_pedido: d.id_pedido || '',
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
    const body = {
      ...form.value,
      responsable: form.value.responsables[0] || auth.usuario?.email || ''
    }
    if (editar.value) {
      const data = await api(`/api/gestion/tareas/${props.tareaEditar.id}`, { method: 'PUT', body: JSON.stringify(body) })
      tarea = data.tarea
    } else {
      // Sugerencia IA si no eligió categoría
      if (!form.value.categoria_id) await tfSugerirSiNecesario()
      if (!form.value.categoria_id) return // categoría requerida
      tarea = await crearTarea(body)
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

/* Handle bar (mobile) — área touch amplia para arrastrar */
.sheet-handle-wrap {
  padding: 8px 0 4px;
  cursor: grab;
  touch-action: none;
  display: flex;
  justify-content: center;
}
.sheet-handle-wrap:active { cursor: grabbing; }
.sheet-handle {
  width: 40px; height: 4px;
  background: var(--border-strong);
  border-radius: 2px;
}

/* Transición suave al soltar el drag */
.is-sheet { transition: transform 200ms ease; }

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
