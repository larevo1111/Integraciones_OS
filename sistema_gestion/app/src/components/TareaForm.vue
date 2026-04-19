<template>
  <q-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :position="isMobile ? 'bottom' : 'standard'"
    :maximized="false"
    transition-show="jump-up"
    transition-hide="jump-down"
  >
    <q-card class="tf-card">
      <!-- Header -->
      <div class="tf-header">
        <span class="tf-header-title">{{ editar ? 'Editar tarea' : 'Nueva tarea' }}</span>
        <q-space />
        <q-btn flat dense round icon="close" size="sm" v-close-popup />
      </div>

      <q-form @submit.prevent="guardar" class="tf-form">
        <!-- Título -->
        <q-input
          ref="tituloRef"
          v-model="form.titulo"
          autofocus
          borderless
          dense
          placeholder="¿Qué hay que hacer?"
          class="tf-titulo"
          input-class="tf-titulo-input"
          @blur="tfSugerirSiNecesario"
        />

        <!-- Descripción -->
        <q-input
          v-model="form.descripcion"
          type="textarea"
          borderless
          dense
          autogrow
          placeholder="Descripción (opcional)"
          class="tf-descripcion"
          input-class="tf-descripcion-input"
        />

        <!-- Chips fila -->
        <div class="tf-chips">
          <!-- Categoría -->
          <MetaChip
            :icon="categoriaSeleccionada ? null : 'label_outline'"
            label="Categoría"
            :value="form.categoria_id"
            :value-label="categoriaSeleccionada?.nombre?.replace(/_/g, ' ')"
            :value-bg="categoriaSeleccionada ? hexAlpha(categoriaSeleccionada.color, 0.15) : null"
            :value-color="categoriaSeleccionada?.color"
          >
            <q-list dense style="min-width: 220px; max-height: 280px; overflow-y: auto">
              <q-item-label header class="tf-menu-title">
                Categoría
                <q-spinner v-if="iaLoading" size="14px" color="primary" class="q-ml-xs" />
              </q-item-label>
              <q-item
                v-for="c in categorias"
                :key="c.id"
                clickable v-close-popup
                :active="form.categoria_id === c.id"
                @click="form.categoria_id = c.id; tfChipClickCount++"
              >
                <q-item-section avatar>
                  <span class="cat-dot" :style="{ background: c.color }"></span>
                </q-item-section>
                <q-item-section>{{ c.nombre.replace(/_/g, ' ') }}</q-item-section>
              </q-item>
            </q-list>
          </MetaChip>

          <!-- Prioridad -->
          <MetaChip
            icon="flag"
            label="Prioridad"
            :value="form.prioridad !== 'Media' ? form.prioridad : null"
            :value-label="form.prioridad"
            :value-bg="prioridadBg"
            :value-color="prioridadColor"
          >
            <q-list dense style="min-width: 160px; max-height: 240px; overflow-y: auto">
              <q-item-label header class="tf-menu-title">Prioridad</q-item-label>
              <q-item
                v-for="p in ['Urgente', 'Alta', 'Media', 'Baja']"
                :key="p"
                clickable v-close-popup
                :active="form.prioridad === p"
                @click="form.prioridad = p"
              >
                <q-item-section avatar>
                  <q-icon name="flag" :color="_COLORES_PRIO_NAME[p] || 'grey'" />
                </q-item-section>
                <q-item-section>{{ p }}</q-item-section>
              </q-item>
            </q-list>
          </MetaChip>

          <!-- Fecha -->
          <MetaChip
            icon="event"
            label="Fecha"
            :value="form.fecha_limite"
            :value-label="fechaLabel"
          >
            <template #default="{ close }">
              <q-date
                :model-value="form.fecha_limite"
                mask="YYYY-MM-DD"
                today-btn
                minimal
                @update:model-value="val => { form.fecha_limite = val; close() }"
              />
              <div v-if="form.fecha_limite" class="row justify-center q-pa-sm">
                <q-btn flat dense size="sm" label="Quitar fecha" @click="form.fecha_limite = ''; close()" />
              </div>
            </template>
          </MetaChip>

          <!-- Responsable -->
          <MetaChip
            icon="person_outline"
            label="Responsable"
            :value="form.responsable"
            :value-label="responsableLabel"
          >
            <q-list dense style="min-width: 200px; max-height: 260px; overflow-y: auto">
              <q-item-label header class="tf-menu-title">Responsable</q-item-label>
              <q-item
                v-for="u in usuarios"
                :key="u.email"
                clickable v-close-popup
                :active="form.responsable === u.email"
                @click="form.responsable = u.email"
              >
                <q-item-section>{{ u.nombre }}</q-item-section>
              </q-item>
            </q-list>
          </MetaChip>

          <!-- Proyecto -->
          <MetaChip
            icon="folder_outline"
            label="Proyecto"
            :value="form.proyecto_id"
            :value-label="proyectoSeleccionado?.nombre"
            :value-bg="proyectoSeleccionado ? hexAlpha(proyectoSeleccionado.color || '#888', 0.15) : null"
          >
            <template #default="{ close }">
              <q-list dense style="min-width: 220px; max-height: 320px; overflow-y: auto">
                <q-item-label header class="tf-menu-title">Proyecto</q-item-label>
                <q-item clickable v-close-popup :active="!form.proyecto_id" @click="form.proyecto_id = null">
                  <q-item-section class="text-grey">Sin proyecto</q-item-section>
                </q-item>
                <q-item
                  v-for="p in proyectos"
                  :key="p.id"
                  clickable v-close-popup
                  :active="form.proyecto_id === p.id"
                  @click="form.proyecto_id = p.id"
                >
                  <q-item-section avatar>
                    <span class="cat-dot" :style="{ background: p.color || '#888' }"></span>
                  </q-item-section>
                  <q-item-section>{{ p.nombre }}</q-item-section>
                </q-item>
              </q-list>
            </template>
          </MetaChip>

          <!-- Etiquetas -->
          <MetaChip
            icon="local_offer"
            label="Etiquetas"
            :value="form.etiquetas.length ? form.etiquetas : null"
            :value-label="etiquetasLabel"
          >
            <q-list dense style="min-width: 220px; max-height: 320px; overflow-y: auto">
              <q-item-label header class="tf-menu-title">Etiquetas</q-item-label>
              <q-item
                v-for="e in etiquetas"
                :key="e.id"
                clickable
                @click="toggleEtiqueta(e.id)"
              >
                <q-item-section avatar>
                  <q-checkbox :model-value="form.etiquetas.includes(e.id)" dense />
                </q-item-section>
                <q-item-section avatar>
                  <span class="cat-dot" :style="{ background: e.color || '#888' }"></span>
                </q-item-section>
                <q-item-section>{{ e.nombre }}</q-item-section>
              </q-item>
              <q-item v-if="!etiquetas.length">
                <q-item-section class="text-grey">Sin etiquetas</q-item-section>
              </q-item>
            </q-list>
          </MetaChip>

          <!-- OP / Remisión / Pedido (dinámico según categoría) -->
          <MetaChip
            v-if="categoriaSeleccionada?.es_produccion"
            icon="description"
            label="OP Effi"
            :value="form.id_op"
            :value-label="form.id_op ? `OP ${form.id_op}` : null"
          >
            <div class="q-pa-sm" style="min-width: 280px">
              <OpSelector v-model="form.id_op" />
            </div>
          </MetaChip>

          <MetaChip
            v-if="categoriaSeleccionada?.es_empaque"
            icon="inventory_2"
            label="Remisión"
            :value="form.id_remision"
            :value-label="form.id_remision ? `Rem ${form.id_remision}` : null"
          >
            <div class="q-pa-sm" style="min-width: 280px">
              <RemisionSelector v-model="form.id_remision" />
            </div>
          </MetaChip>

          <MetaChip
            v-if="categoriaSeleccionada?.es_empaque"
            icon="shopping_cart"
            label="Pedido"
            :value="form.id_pedido"
            :value-label="form.id_pedido ? `Ped ${form.id_pedido}` : null"
          >
            <div class="q-pa-sm" style="min-width: 280px">
              <PedidoSelector v-model="form.id_pedido" />
            </div>
          </MetaChip>
        </div>

        <!-- Footer -->
        <div class="tf-footer">
          <q-btn flat dense label="Cancelar" v-close-popup class="tf-btn-cancel" />
          <q-btn
            type="submit"
            color="primary"
            unelevated
            dense
            :loading="guardando"
            :disable="!form.titulo || !form.categoria_id"
            :label="editar ? 'Guardar' : 'Crear tarea'"
          />
        </div>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/services/api'
import { crearTarea, sugerirCategoria } from 'src/composables/useTareas'
import { useAuthStore } from 'src/stores/authStore'
import MetaChip          from 'src/components/base/MetaChip.vue'
import OpSelector        from 'src/components/OpSelector.vue'
import RemisionSelector  from 'src/components/RemisionSelector.vue'
import PedidoSelector    from 'src/components/PedidoSelector.vue'

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

const $q        = useQuasar()
const auth      = useAuthStore()
const guardando = ref(false)
const tituloRef = ref(null)
const isMobile  = computed(() => $q.screen.lt.md)

const form = ref({
  titulo: '', descripcion: '', categoria_id: null, proyecto_id: null,
  prioridad: 'Media', responsable: auth.usuario?.email || '',
  fecha_limite: '', id_op: '', id_remision: '', id_pedido: '', etiquetas: []
})

const iaLoading      = ref(false)
let tfChipClickCount = 0

const _COLORES_PRIO = {
  'Urgente': { bg: 'rgba(239, 68, 68, 0.15)',  fg: '#EF4444' },
  'Alta':    { bg: 'rgba(249, 115, 22, 0.15)', fg: '#F97316' },
  'Media':   { bg: null, fg: null },
  'Baja':    { bg: 'rgba(148, 163, 184, 0.15)', fg: '#64748B' }
}
const _COLORES_PRIO_NAME = {
  'Urgente': 'red-5', 'Alta': 'orange-5', 'Media': 'grey-5', 'Baja': 'grey-4'
}

const prioridadBg    = computed(() => _COLORES_PRIO[form.value.prioridad]?.bg)
const prioridadColor = computed(() => _COLORES_PRIO[form.value.prioridad]?.fg)

const editar = computed(() => !!props.tareaEditar)
const categoriaSeleccionada = computed(() => props.categorias.find(c => c.id === form.value.categoria_id))
const proyectoSeleccionado  = computed(() => props.proyectos.find(p => p.id === form.value.proyecto_id))

const fechaLabel = computed(() => {
  if (!form.value.fecha_limite) return null
  const [y, m, d] = form.value.fecha_limite.split('-')
  const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
  return `${d} ${meses[+m - 1]}`
})

const responsableLabel = computed(() => {
  if (!form.value.responsable) return null
  const u = props.usuarios.find(x => x.email === form.value.responsable)
  return u?.nombre || form.value.responsable.split('@')[0]
})

const etiquetasLabel = computed(() => {
  const ids = form.value.etiquetas
  if (!ids.length) return null
  if (ids.length === 1) {
    return props.etiquetas.find(e => e.id === ids[0])?.nombre || '1 etiq'
  }
  return `${ids.length} etiquetas`
})

function toggleEtiqueta(id) {
  const idx = form.value.etiquetas.indexOf(id)
  if (idx === -1) form.value.etiquetas.push(id)
  else form.value.etiquetas.splice(idx, 1)
}

function hexAlpha(hex, a) {
  if (!hex) return null
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}

async function tfSugerirSiNecesario() {
  if (editar.value || !form.value.titulo || form.value.titulo.length < 4) return
  if (form.value.categoria_id) return
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
  if (form.value.categoria_id || tfChipClickCount > 0) return  // respeta elección manual
  tfDebounce = setTimeout(tfSugerirSiNecesario, 1000)
})

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
      id_remision:  props.tareaEditar.id_remision || '',
      id_pedido:    props.tareaEditar.id_pedido || '',
      etiquetas:    (props.tareaEditar.etiquetas || []).map(e => e.id)
    }
  } else {
    const d = props.defaults || {}
    form.value = {
      titulo: '', descripcion: '',
      categoria_id: d.categoria_id || null,
      proyecto_id: d.proyecto_id || null,
      prioridad: d.prioridad || 'Media',
      responsable: d.responsable || auth.usuario?.email || '',
      fecha_limite: d.fecha_limite || '',
      id_op: d.id_op || '', id_remision: d.id_remision || '', id_pedido: d.id_pedido || '',
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
      if (!form.value.categoria_id) await tfSugerirSiNecesario()
      if (!form.value.categoria_id) {
        const varios = props.categorias.find(c => c.nombre === 'Varios')
        if (varios) form.value.categoria_id = varios.id
      }
      if (!form.value.categoria_id) return
      tarea = await crearTarea(form.value)
    }
    emit('guardada', tarea)
    emit('update:modelValue', false)
  } catch (e) { console.error(e) } finally { guardando.value = false }
}
</script>

<style scoped>
.tf-card {
  width: 540px;
  max-width: 96vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-modal);
  border: 1px solid var(--border-default);
}
.q-dialog--bottom .tf-card,
.tf-card.q-dialog__inner--bottom {
  width: 100%;
  max-width: 100%;
  border-radius: 16px 16px 0 0;
  max-height: 92dvh;
}

.tf-header {
  display: flex; align-items: center;
  padding: 10px 12px 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.tf-header-title {
  font-size: 12px; font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tf-form {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
}

.tf-titulo {
  padding: 12px 16px 4px;
}
.tf-titulo :deep(.tf-titulo-input) {
  font-size: 18px !important;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.3;
}

.tf-descripcion {
  padding: 0 16px 8px;
}
.tf-descripcion :deep(.tf-descripcion-input) {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
  min-height: 40px;
}

.tf-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px 16px;
  border-top: 1px solid var(--border-subtle);
}

.tf-menu-title {
  font-size: 10px !important;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-tertiary) !important;
  letter-spacing: 0.05em;
  padding: 8px 12px 4px !important;
}

.cat-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.tf-footer {
  display: flex; gap: 8px; justify-content: flex-end;
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.tf-btn-cancel { color: var(--text-secondary); }
</style>
