<template>
  <div
    class="tarea-item"
    :class="{ selected: seleccionada, completada: esCompletada, 'is-subtarea': !!tarea.parent_id }"
    @click="$emit('click', tarea)"
  >
    <!-- Columna izquierda: estado + (badge 0/N + ↳) debajo -->
    <div class="estado-col">
      <EstadoBadge :estado="tarea.estado" @click="$emit('cambiar-estado', tarea)" />

      <!-- Tarea padre CON subtareas: badge 0/N + botón ↳ -->
      <div
        v-if="tarea.subtareas_total > 0 && !tarea.parent_id"
        class="sub-controls"
      >
        <button
          class="subtareas-badge"
          :class="{ expandida: expandida }"
          @click.stop="$emit('toggle-subtareas', tarea)"
          :title="expandida ? 'Contraer subtareas' : 'Expandir subtareas'"
        >
          <span class="material-icons" style="font-size:8px">{{ expandida ? 'expand_more' : 'chevron_right' }}</span>
          {{ tarea.subtareas_completadas }}/{{ tarea.subtareas_total }}
        </button>
        <button
          v-if="!esCompletada"
          class="btn-add-sub"
          title="Agregar subtarea"
          @click.stop="$emit('agregar-subtarea', tarea)"
        >
          <span class="material-icons" style="font-size:10px">subdirectory_arrow_right</span>
        </button>
      </div>

      <!-- Tarea padre SIN subtareas aún: solo ↳ sutil on hover -->
      <button
        v-else-if="!tarea.parent_id && !esCompletada"
        class="btn-add-sub-solo"
        title="Agregar subtarea"
        @click.stop="$emit('agregar-subtarea', tarea)"
      >
        <span class="material-icons" style="font-size:10px">subdirectory_arrow_right</span>
      </button>
    </div>

    <div class="cat-dot" :style="{ background: tarea.categoria_color }" />
    <input
      v-if="editandoTitulo"
      ref="inputTituloRef"
      class="tarea-titulo-input"
      v-model="tituloEditando"
      @blur="confirmarEdicion"
      @keydown.enter.prevent="confirmarEdicion"
      @keydown.escape.prevent="cancelarEdicion"
      @click.stop
    />
    <span
      v-else
      class="tarea-titulo"
      :class="{ 'titulo-editable': !compacto }"
      @click.stop="activarEdicion"
    >{{ tarea.titulo }}</span>

    <div class="tarea-meta">
      <!-- Cronómetro activo (corriendo en tiempo real) -->
      <span v-if="tarea.cronometro_activo" class="cronometro-activo">
        <span class="cronometro-dot" />
        {{ tiempoCronometro }}
      </span>

      <!-- Chip categoría: dot coloreado + nombre, fondo tinted -->
      <span
        v-if="tarea.categoria_nombre"
        class="meta-chip"
        :style="{ background: hexAlpha(tarea.categoria_color, 0.12), color: tarea.categoria_color }"
        :title="tarea.categoria_nombre"
      >
        <span class="meta-chip-dot" :style="{ background: tarea.categoria_color }" />
        {{ catNombreCorto }}
      </span>

      <!-- Bandera prioridad (2do elemento, solo Urgente/Alta/Media visibles; Baja omitida) -->
      <span
        v-if="colorPrioridad"
        class="meta-flag"
        :title="tarea.prioridad"
        :style="{ color: colorPrioridad }"
      ><span class="material-icons" style="font-size:11px">flag</span></span>

      <!-- Chip duración real -->
      <span
        v-if="tarea.tiempo_real_min > 0 && !tarea.cronometro_activo"
        class="meta-chip meta-chip-dur"
        title="Tiempo real"
      >{{ duracionDisplay }}</span>

      <!-- Chip fecha -->
      <span
        v-if="fechaDisplay"
        class="meta-chip meta-chip-fecha"
        :class="clasesFecha"
      >{{ fechaDisplay }}</span>

      <!-- Chip proyecto -->
      <span
        v-if="tarea.proyecto_nombre"
        class="meta-chip"
        :style="{ background: hexAlpha(tarea.proyecto_color, 0.10), color: 'var(--text-tertiary)' }"
        :title="tarea.proyecto_nombre"
      >
        <span class="meta-chip-dot" :style="{ background: tarea.proyecto_color || '#888' }" />
        {{ proyNombreCorto }}
      </span>

      <!-- Badge responsable (solo vista Equipo) -->
      <span
        v-if="mostrarResponsable && responsableIniciales"
        class="meta-chip meta-chip-responsable"
        :title="tarea.responsable_nombre || tarea.responsable"
      >{{ responsableIniciales }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import EstadoBadge from './EstadoBadge.vue'

const props = defineProps({
  tarea:              { type: Object, required: true },
  seleccionada:       { type: Boolean, default: false },
  usuarioActual:      { type: String, default: '' },
  expandida:          { type: Boolean, default: false },
  mostrarResponsable: { type: Boolean, default: false },
  compacto:           { type: Boolean, default: false }   // modo móvil: chips y fecha cortos
})

const responsableIniciales = computed(() => {
  if (!props.tarea.responsable) return null
  const nombre = props.tarea.responsable_nombre || ''
  if (nombre) {
    // Primer nombre, 3 primeras letras en mayúscula
    return nombre.split(' ')[0].slice(0, 3).toUpperCase()
  }
  // Fallback: parte antes del @ en el email
  return props.tarea.responsable.split('@')[0].slice(0, 3).toUpperCase()
})
const emit = defineEmits(['click', 'cambiar-estado', 'agregar-subtarea', 'toggle-subtareas', 'editar-titulo'])

// ── Edición inline del título (solo desktop) ──────────────────
const editandoTitulo  = ref(false)
const tituloEditando  = ref('')
const inputTituloRef  = ref(null)

function activarEdicion(e) {
  if (props.compacto) return          // móvil: no editar inline
  e.stopPropagation()
  tituloEditando.value  = props.tarea.titulo
  editandoTitulo.value  = true
  nextTick(() => {
    const el = inputTituloRef.value
    if (!el) return
    el.focus()
    el.setSelectionRange(el.value.length, el.value.length)
  })
  emit('click', props.tarea)          // también abrir panel
}

function confirmarEdicion() {
  const nuevo = tituloEditando.value.trim()
  editandoTitulo.value = false
  if (nuevo && nuevo !== props.tarea.titulo) {
    emit('editar-titulo', { tarea: props.tarea, titulo: nuevo })
  }
}

function cancelarEdicion() {
  editandoTitulo.value = false
}

const esCompletada = computed(() => ['Completada','Cancelada'].includes(props.tarea.estado))

const _COLORES_PRIO = { Urgente: '#ef4444', Alta: '#f59e0b', Media: '#6b7280' }
const colorPrioridad = computed(() => _COLORES_PRIO[props.tarea.prioridad] || null)

function hexAlpha(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(136,136,136,${alpha})`
  const r = parseInt(hex.slice(1,3), 16)
  const g = parseInt(hex.slice(3,5), 16)
  const b = parseInt(hex.slice(5,7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

const catNombreCorto = computed(() => {
  const n = (props.tarea.categoria_nombre || '').replace(/_/g, ' ')
  const max = props.compacto ? 4 : 14
  return n.length > max ? n.slice(0, max) : n
})
const proyNombreCorto = computed(() => {
  const n = props.tarea.proyecto_nombre || ''
  const max = props.compacto ? 4 : 14
  return n.length > max ? n.slice(0, max) : n
})

function isoFecha(f) {
  if (!f) return null
  const s = typeof f === 'string' ? f : f.toISOString()
  return s.slice(0, 10)
}

const fechaDisplay = computed(() => {
  const iso = isoFecha(props.tarea.fecha_limite)
  if (!iso) return ''
  const d      = new Date(iso + 'T00:00:00')
  const hoy    = new Date(); hoy.setHours(0,0,0,0)
  const manana = new Date(hoy); manana.setDate(hoy.getDate()+1)
  const ayer   = new Date(hoy); ayer.setDate(hoy.getDate()-1)
  if (d.getTime() === hoy.getTime())    return 'Hoy'
  if (d.getTime() === manana.getTime()) return props.compacto ? 'Mañ' : 'Mañana'
  if (d.getTime() === ayer.getTime())   return props.compacto ? 'Ayr' : 'Ayer'
  // Para fechas específicas: "5 jun" en desktop, "5j" sería raro, dejamos igual
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
})

const clasesFecha = computed(() => {
  const iso = isoFecha(props.tarea.fecha_limite)
  if (!iso) return ''
  const d   = new Date(iso + 'T00:00:00')
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  if (d < hoy) return 'vencida'
  if (d.getTime() === hoy.getTime()) return 'hoy'
  return ''
})

const duracionDisplay = computed(() => {
  const min = props.tarea.tiempo_real_min || 0
  if (!min) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
})

const tiempoCronometro = ref('00:00')
let interval = null

// Parsear cronometro_inicio como Colombia UTC-5 (mysql2 timezone:'local' guarda en hora Colombia)
function parseInicio(str) {
  if (!str) return null
  if (str.includes('Z') || str.includes('+') || str.includes('-', 10)) return new Date(str)
  return new Date(str.replace(' ', 'T') + '-05:00')
}

function calcularTiempo() {
  if (!props.tarea.cronometro_activo || !props.tarea.cronometro_inicio) return
  const ini   = parseInicio(props.tarea.cronometro_inicio)
  if (!ini) return
  const base  = (props.tarea.tiempo_real_min || 0) * 60
  const extra = Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
  const total = base + extra
  const m = Math.floor(total / 60)
  const s = total % 60
  tiempoCronometro.value = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

function iniciarInterval() {
  if (interval) clearInterval(interval)
  calcularTiempo()
  interval = setInterval(calcularTiempo, 1000)
}
function detenerInterval() {
  if (interval) { clearInterval(interval); interval = null }
  tiempoCronometro.value = '00:00'
}

onMounted(() => {
  if (props.tarea.cronometro_activo) iniciarInterval()
})

// Reaccionar a cambios de cronometro_activo después del mount
watch(() => props.tarea.cronometro_activo, (val) => {
  if (val) iniciarInterval()
  else     detenerInterval()
})

onUnmounted(() => { if (interval) clearInterval(interval) })
</script>

<style scoped>
/* Columna izquierda fija en 14px (= ancho del círculo) — evita que el badge corra el contenido */
.estado-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 14px;
  position: relative;
}

/* Badge 0/N + botón ↳ — flotante debajo del círculo, no afecta altura de fila */
.sub-controls {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

/* Badge expandir subtareas — sin chip, solo texto sutil */
.subtareas-badge {
  display: inline-flex; align-items: center; gap: 1px;
  padding: 0 2px; height: 12px;
  border: none; border-radius: 0; background: transparent;
  font-size: 8px; color: var(--text-tertiary);
  cursor: pointer; flex-shrink: 0;
  transition: color 80ms;
  white-space: nowrap; line-height: 1;
}
.subtareas-badge:hover, .subtareas-badge.expandida {
  color: var(--accent);
}

/* Botón ↳ junto al badge (para tareas padre con subtareas) */
.btn-add-sub {
  display: flex; align-items: center; justify-content: center;
  width: 13px; height: 12px; flex-shrink: 0;
  background: transparent; border: none;
  color: var(--text-tertiary); cursor: pointer;
  opacity: 0.3; transition: opacity 100ms, color 100ms;
  padding: 0;
}
.tarea-item:hover .btn-add-sub { opacity: 0.7; }
.btn-add-sub:hover { color: var(--accent) !important; opacity: 1 !important; }

/* Botón ↳ solo (para tareas padre sin subtareas aún) — más sutil */
.btn-add-sub-solo {
  display: flex; align-items: center; justify-content: center;
  width: 14px; height: 12px; flex-shrink: 0;
  background: transparent; border: none;
  color: var(--text-tertiary); cursor: pointer;
  opacity: 0; transition: opacity 100ms, color 100ms;
  padding: 0;
}
.tarea-item:hover .btn-add-sub-solo { opacity: 0.45; }
.btn-add-sub-solo:hover { color: var(--accent) !important; opacity: 1 !important; }

/* Mobile: hacer los botones de subtarea siempre mínimamente visibles (sin hover) */
@media (max-width: 768px) {
  .btn-add-sub       { opacity: 0.45; }
  .btn-add-sub-solo  { opacity: 0.25; }
}

/* Título editable en desktop */
.titulo-editable { cursor: text; }

/* Input inline de edición de título */
.tarea-titulo-input {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--accent);
  outline: none;
  font-size: 13px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  padding: 0 0 1px;
  min-width: 0;
  line-height: inherit;
}

/* Subtarea: indentación */
.is-subtarea { padding-left: 28px !important; }
.is-subtarea .tarea-titulo { font-size: 11px; color: var(--text-secondary); }
</style>
