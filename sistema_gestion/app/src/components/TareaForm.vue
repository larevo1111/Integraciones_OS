<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-overlay" @click.self="$emit('update:modelValue', false)">
        <div class="modal">
          <div class="modal-header">
            <span class="modal-title">{{ editar ? 'Editar tarea' : 'Nueva tarea' }}</span>
            <button class="btn-icon" @click="$emit('update:modelValue', false)"><span class="material-icons">close</span></button>
          </div>
          <div class="modal-body">
            <!-- Título -->
            <div class="input-group">
              <label class="input-label">Título *</label>
              <input class="input-field" v-model="form.titulo" placeholder="¿Qué hay que hacer?" autofocus />
            </div>

            <!-- Fila de selects -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="input-group">
                <label class="input-label">Categoría *</label>
                <select class="input-field select-field" v-model="form.categoria_id">
                  <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                </select>
              </div>
              <div class="input-group">
                <label class="input-label">Prioridad</label>
                <select class="input-field select-field" v-model="form.prioridad">
                  <option>Baja</option><option>Media</option><option>Alta</option><option>Urgente</option>
                </select>
              </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
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
            </div>

            <!-- OP Effi (solo si categoría es_produccion) -->
            <div v-if="categoriaSeleccionada?.es_produccion" class="input-group">
              <label class="input-label">OP Effi</label>
              <input class="input-field" v-model="form.id_op" placeholder="Número de OP" />
            </div>

            <!-- Descripción -->
            <div class="input-group">
              <label class="input-label">Descripción</label>
              <textarea class="input-field" v-model="form.descripcion" rows="4" placeholder="Contexto, pasos, notas..." />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="$emit('update:modelValue', false)">Cancelar</button>
            <button class="btn btn-primary" :disabled="!form.titulo || !form.categoria_id || guardando" @click="guardar">
              {{ guardando ? 'Guardando...' : (editar ? 'Guardar' : 'Crear tarea') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'

const props = defineProps({
  modelValue: Boolean,
  tareaEditar: { type: Object, default: null },
  categorias:  { type: Array, default: () => [] },
  usuarios:    { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue', 'guardada'])
const auth = useAuthStore()

const editar   = computed(() => !!props.tareaEditar)
const guardando = ref(false)

const form = ref({
  titulo: '', descripcion: '', categoria_id: null,
  prioridad: 'Media', responsable: auth.usuario?.email || '',
  fecha_limite: '', id_op: ''
})

const categoriaSeleccionada = computed(() =>
  props.categorias.find(c => c.id === form.value.categoria_id)
)

watch(() => props.modelValue, (val) => {
  if (val) {
    if (props.tareaEditar) {
      form.value = {
        titulo:       props.tareaEditar.titulo || '',
        descripcion:  props.tareaEditar.descripcion || '',
        categoria_id: props.tareaEditar.categoria_id,
        prioridad:    props.tareaEditar.prioridad || 'Media',
        responsable:  props.tareaEditar.responsable || auth.usuario?.email || '',
        fecha_limite: props.tareaEditar.fecha_limite || '',
        id_op:        props.tareaEditar.id_op || ''
      }
    } else {
      form.value = {
        titulo: '', descripcion: '',
        categoria_id: props.categorias[0]?.id || null,
        prioridad: 'Media',
        responsable: auth.usuario?.email || '',
        fecha_limite: '', id_op: ''
      }
    }
  }
})

async function guardar() {
  if (!form.value.titulo || !form.value.categoria_id) return
  guardando.value = true
  try {
    let data
    if (editar.value) {
      data = await api(`/api/gestion/tareas/${props.tareaEditar.id}`, { method: 'PUT', body: JSON.stringify(form.value) })
      emit('guardada', data.tarea)
    } else {
      data = await api('/api/gestion/tareas', { method: 'POST', body: JSON.stringify(form.value) })
      emit('guardada', data.tarea)
    }
    emit('update:modelValue', false)
  } catch (e) {
    console.error(e)
  } finally {
    guardando.value = false
  }
}
</script>
