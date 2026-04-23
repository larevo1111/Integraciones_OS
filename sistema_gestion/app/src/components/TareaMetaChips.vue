<template>
  <div class="form-chips">
    <!-- Estado (opcional, solo en edit) -->
    <q-chip
      v-if="showEstado"
      clickable dense
      icon="radio_button_unchecked"
      class="tf-chip"
      :class="{ 'tf-chip-filled': estadoSeleccionado }"
      :style="estadoSeleccionado ? { background: estadoSeleccionado.color + '22', borderColor: estadoSeleccionado.color, color: estadoSeleccionado.color } : {}"
    >
      <span class="cat-dot" :style="{ background: estadoSeleccionado?.color || '#6b7280', marginRight: '5px' }"></span>
      <span>{{ estadoSeleccionado?.label || 'Estado' }}</span>
      <q-menu class="tf-menu" anchor="top middle" self="bottom middle" :offset="[0, 6]">
        <q-list dense style="min-width:160px">
          <q-item
            v-for="e in ESTADOS"
            :key="e.key"
            clickable v-close-popup
            :active="estado === e.key"
            @click="$emit('update:estado', e.key)"
          >
            <q-item-section avatar><span class="cat-dot" :style="{ background: e.color }"></span></q-item-section>
            <q-item-section>{{ e.label }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-chip>

    <!-- Categoría -->
    <q-chip
      clickable dense
      icon="sell"
      class="tf-chip"
      :class="{ 'tf-chip-filled': categoriaSeleccionada }"
      :style="categoriaSeleccionada ? { background: hexAlpha(categoriaSeleccionada.color, 0.15), borderColor: categoriaSeleccionada.color, color: categoriaSeleccionada.color } : {}"
    >
      <span v-if="categoriaSeleccionada" class="cat-dot" :style="{ background: categoriaSeleccionada.color, marginRight: '5px' }"></span>
      <span>{{ categoriaSeleccionada ? categoriaSeleccionada.nombre.replace(/_/g, ' ') : 'Categoría' }}</span>
      <span v-if="iaLoading" class="material-icons spin-ico">autorenew</span>
      <q-menu class="tf-menu" anchor="top middle" self="bottom middle" :offset="[0, 6]">
        <q-list dense style="min-width:220px;max-height:300px;overflow-y:auto">
          <q-item
            v-for="c in categorias"
            :key="c.id"
            clickable v-close-popup
            :active="categoriaId === c.id"
            @click="$emit('update:categoriaId', c.id)"
          >
            <q-item-section avatar><span class="cat-dot" :style="{ background: c.color }"></span></q-item-section>
            <q-item-section>{{ c.nombre.replace(/_/g, ' ') }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-chip>

    <!-- Prioridad -->
    <q-chip
      clickable dense
      icon="flag"
      class="tf-chip"
      :class="{ 'tf-chip-filled': prioridad && prioridad !== 'Media' }"
      :style="prioridadStyle"
    >
      <span>{{ prioridad || 'Prioridad' }}</span>
      <q-menu class="tf-menu" anchor="top middle" self="bottom middle" :offset="[0, 6]">
        <q-list dense style="min-width:140px">
          <q-item
            v-for="p in ['Urgente','Alta','Media','Baja']"
            :key="p"
            clickable v-close-popup
            :active="prioridad === p"
            @click="$emit('update:prioridad', p)"
          >
            <q-item-section avatar><q-icon name="flag" :style="{ color: _COLORES_PRIO[p] }" /></q-item-section>
            <q-item-section>{{ p }}</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-chip>

    <!-- Etiquetas -->
    <EtiquetasSelector
      :model-value="etiquetas"
      :etiquetas="etiquetasDisponibles"
      class="tf-inline-selector"
      @update:model-value="v => $emit('update:etiquetas', v)"
      @etiqueta-creada="e => $emit('etiqueta-creada', e)"
      @etiqueta-actualizada="e => $emit('etiqueta-actualizada', e)"
      @etiqueta-eliminada="id => $emit('etiqueta-eliminada', id)"
    />

    <!-- Fecha -->
    <q-chip
      :clickable="!fechaReadonly" dense
      icon="event"
      class="tf-chip"
      :class="{ 'tf-chip-filled': fechaLimite }"
    >
      <span>{{ fechaLimite ? fechaLabel : 'Fecha' }}</span>
      <q-menu v-if="!fechaReadonly" class="tf-menu" anchor="top middle" self="bottom middle" :offset="[0, 6]">
        <q-date
          :model-value="fechaLimite ? String(fechaLimite).slice(0,10) : ''"
          mask="YYYY-MM-DD"
          today-btn
          minimal
          @update:model-value="val => $emit('update:fechaLimite', val || '')"
        />
        <div v-if="fechaLimite" class="row justify-end q-pa-xs">
          <q-btn flat dense size="sm" label="Quitar" v-close-popup @click="$emit('update:fechaLimite', '')" />
        </div>
      </q-menu>
    </q-chip>

    <!-- Responsables -->
    <ResponsablesSelector
      :single="false"
      :model-value="responsables"
      :usuarios="usuarios"
      class="tf-inline-selector"
      @update:model-value="v => $emit('update:responsables', v)"
    />

    <!-- Proyecto -->
    <ProyectoSelector
      :model-value="proyectoId"
      :proyectos="proyectos"
      empty-label="Proyecto"
      class="tf-inline-selector"
      @update:model-value="v => $emit('update:proyectoId', v)"
      @crear-item="tipo => $emit('crear-item', tipo)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EtiquetasSelector    from './EtiquetasSelector.vue'
import ResponsablesSelector from './ResponsablesSelector.vue'
import ProyectoSelector     from './ProyectoSelector.vue'

const props = defineProps({
  // Valores
  estado:       { type: String, default: null },
  categoriaId:  { type: Number, default: null },
  prioridad:    { type: String, default: 'Media' },
  etiquetas:    { type: Array,  default: () => [] },
  fechaLimite:  { type: String, default: '' },
  responsables: { type: Array,  default: () => [] },
  proyectoId:   { type: Number, default: null },

  // Opciones (listas)
  categorias:           { type: Array, default: () => [] },
  etiquetasDisponibles: { type: Array, default: () => [] },
  usuarios:             { type: Array, default: () => [] },
  proyectos:            { type: Array, default: () => [] },

  // Flags
  showEstado:    { type: Boolean, default: false },
  iaLoading:     { type: Boolean, default: false },
  fechaReadonly: { type: Boolean, default: false }
})

defineEmits([
  'update:estado',
  'update:categoriaId',
  'update:prioridad',
  'update:etiquetas',
  'update:fechaLimite',
  'update:responsables',
  'update:proyectoId',
  'crear-item',
  'etiqueta-creada',
  'etiqueta-actualizada',
  'etiqueta-eliminada'
])

const ESTADOS = [
  { key: 'Pendiente',   label: 'Pendiente',   color: '#6b7280' },
  { key: 'En Progreso', label: 'En Progreso', color: '#3b82f6' },
  { key: 'Completada',  label: 'Completada',  color: '#22c55e' },
  { key: 'Cancelada',   label: 'Cancelada',   color: '#ef4444' }
]

const _COLORES_PRIO = { 'Urgente': '#ef4444', 'Alta': '#f59e0b', 'Media': '#6b7280', 'Baja': '#374151' }

const estadoSeleccionado    = computed(() => ESTADOS.find(e => e.key === props.estado) || null)
const categoriaSeleccionada = computed(() => props.categorias.find(c => c.id === props.categoriaId) || null)

const prioridadStyle = computed(() => {
  const p = props.prioridad
  if (!p || p === 'Media') return {}
  const c = _COLORES_PRIO[p]
  return c ? { borderColor: c, color: c } : {}
})

const fechaLabel = computed(() => {
  if (!props.fechaLimite) return ''
  const iso = String(props.fechaLimite).slice(0, 10)
  const [y, m, d] = iso.split('-')
  const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  return `${d} ${meses[+m - 1]}`
})

function hexAlpha(hex, a) {
  if (!hex) return null
  const h = hex.replace('#', '')
  if (h.length !== 6) return null
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg); } }
.spin-ico {
  font-size: 12px;
  color: var(--accent);
  animation: spin 1s linear infinite;
  margin-left: 4px;
}

.form-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 4px 0;
}
.form-chips :deep(.tf-inline-selector) {
  display: inline-flex;
  align-items: center;
}
.tf-chip {
  background: transparent !important;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary) !important;
  font-size: 12px;
  min-height: 26px;
  padding: 0 10px;
}
.tf-chip:hover {
  background: var(--bg-row-hover) !important;
  border-color: var(--border-default);
  color: var(--text-primary) !important;
}
.tf-chip.tf-chip-filled {
  background: var(--bg-row-hover) !important;
  color: var(--text-primary) !important;
  font-weight: 500;
}
.tf-chip :deep(.q-icon) { font-size: 18px !important; opacity: 1 !important; color: currentColor !important; }
.tf-chip :deep(.q-chip__icon--left) { font-size: 18px !important; margin-right: 4px; color: currentColor !important; }

.cat-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
