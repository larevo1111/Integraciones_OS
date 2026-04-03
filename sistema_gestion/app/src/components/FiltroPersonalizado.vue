<template>
  <Teleport to="body">
    <div class="fpop-overlay" @click.self="$emit('cerrar')" />
    <div class="fpop" :style="popStyle">
      <!-- Header -->
      <div class="fpop-header">
        <span class="fpop-title">Filtro personalizado</span>
        <button class="btn-icon" @click="$emit('cerrar')">
          <span class="material-icons" style="font-size:16px">close</span>
        </button>
      </div>

      <!-- Nombre -->
      <div class="fpop-section">
        <p class="fpop-label">Nombre</p>
        <input type="text" class="input-field fpop-date" v-model="local.nombre" placeholder="Buscar por nombre..." style="width:100%" />
      </div>

      <!-- Sección fechas -->
      <div class="fpop-section">
        <p class="fpop-label">Fechas</p>
        <div class="fpop-fechas">
          <div class="fpop-fecha-wrap">
            <span class="fpop-fecha-lbl">Desde</span>
            <input type="date" class="input-field fpop-date" v-model="local.fecha_desde" />
          </div>
          <div class="fpop-fecha-wrap">
            <span class="fpop-fecha-lbl">Hasta</span>
            <input type="date" class="input-field fpop-date" v-model="local.fecha_hasta" />
          </div>
        </div>
      </div>

      <!-- Prioridad multi-select -->
      <div class="fpop-section">
        <p class="fpop-label">Prioridad</p>
        <div class="fpop-chips">
          <button
            v-for="p in PRIORIDADES"
            :key="p.key"
            class="fpop-chip"
            :class="{ active: local.prioridades.includes(p.key) }"
            :style="local.prioridades.includes(p.key) ? { borderColor: p.color, color: p.color, background: p.color + '18' } : {}"
            @click="toggleArr(local.prioridades, p.key)"
          >
            <span class="fpop-dot" :style="{ background: p.color }" />
            {{ p.key }}
          </button>
        </div>
      </div>

      <!-- Categoría multi-select -->
      <div class="fpop-section" v-if="categorias.length">
        <p class="fpop-label">Categoría</p>
        <div class="fpop-chips">
          <button
            v-for="c in categorias"
            :key="c.id"
            class="fpop-chip"
            :class="{ active: local.categorias.includes(c.id) }"
            :style="local.categorias.includes(c.id) ? { borderColor: c.color, color: c.color, background: c.color + '18' } : {}"
            @click="toggleArr(local.categorias, c.id)"
          >
            <span class="fpop-dot" :style="{ background: c.color }" />
            {{ c.nombre.replace(/_/g,' ') }}
          </button>
        </div>
      </div>

      <!-- Etiquetas multi-select -->
      <div class="fpop-section" v-if="etiquetas.length">
        <p class="fpop-label">Etiquetas</p>
        <div class="fpop-chips">
          <button
            v-for="e in etiquetas"
            :key="e.id"
            class="fpop-chip"
            :class="{ active: local.etiquetas.includes(e.id) }"
            :style="local.etiquetas.includes(e.id) ? { borderColor: e.color || '#888', color: e.color || '#888', background: (e.color || '#888') + '18' } : {}"
            @click="toggleArr(local.etiquetas, e.id)"
          >
            {{ e.nombre }}
          </button>
        </div>
      </div>

      <!-- Proyecto (siempre visible) -->
      <div class="fpop-section">
        <p class="fpop-label">Proyecto</p>
        <div class="fpop-chips">
          <button
            class="fpop-chip"
            :class="{ active: local.sinProyecto }"
            @click="local.sinProyecto = !local.sinProyecto; if (local.sinProyecto) local.proyecto_id = null"
          >Sin proyecto</button>
          <button
            v-for="p in proyectos"
            :key="p.id"
            class="fpop-chip"
            :class="{ active: local.proyecto_id === p.id }"
            :style="local.proyecto_id === p.id ? { borderColor: p.color || '#888', color: p.color || '#888', background: (p.color || '#888') + '18' } : {}"
            @click="local.proyecto_id = local.proyecto_id === p.id ? null : p.id; local.sinProyecto = false"
          >
            <span class="fpop-dot" :style="{ background: p.color || '#888' }" />
            {{ p.nombre }}
          </button>
        </div>
      </div>

      <!-- Responsable multi-select -->
      <div class="fpop-section" v-if="usuarios.length">
        <p class="fpop-label">Responsable</p>
        <div class="fpop-chips">
          <button
            v-for="u in usuarios"
            :key="u.email"
            class="fpop-chip"
            :class="{ active: local.responsables.includes(u.email) }"
            :style="local.responsables.includes(u.email) ? { borderColor: 'var(--accent)', color: 'var(--accent)', background: 'var(--accent-muted)' } : {}"
            @click="toggleArr(local.responsables, u.email)"
          >
            {{ u.nombre_corto || u.nombre || u.email.split('@')[0] }}
          </button>
        </div>
      </div>

      <!-- OP Effi -->
      <div class="fpop-section">
        <p class="fpop-label">OP Effi</p>
        <OpSelector v-model="local.id_op" />
      </div>

      <!-- Pedido -->
      <div class="fpop-section">
        <p class="fpop-label">Pedido</p>
        <PedidoSelector v-model="local.id_pedido" />
      </div>

      <!-- Remisión -->
      <div class="fpop-section">
        <p class="fpop-label">Remisión</p>
        <RemisionSelector v-model="local.id_remision" />
      </div>

      <!-- Footer -->
      <div class="fpop-footer">
        <button class="btn btn-ghost btn-sm" @click="limpiar">Limpiar</button>
        <button class="btn btn-accent btn-sm" @click="aplicar">Aplicar</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import OpSelector from 'src/components/OpSelector.vue'
import RemisionSelector from 'src/components/RemisionSelector.vue'
import PedidoSelector from 'src/components/PedidoSelector.vue'

const props = defineProps({
  categorias: { type: Array, default: () => [] },
  etiquetas:  { type: Array, default: () => [] },
  proyectos:  { type: Array, default: () => [] },
  usuarios:   { type: Array, default: () => [] },
  anchorEl:   { type: Object, default: null },
  valor:      { type: Object, default: () => ({}) }
})
const emit = defineEmits(['aplicar', 'cerrar'])

const PRIORIDADES = [
  { key: 'Urgente', color: '#ef4444' },
  { key: 'Alta',    color: '#f59e0b' },
  { key: 'Media',   color: '#6b7280' },
  { key: 'Baja',    color: '#374151' }
]

const local = reactive({
  nombre:       props.valor.nombre        || '',
  fecha_desde:  props.valor.fecha_desde   || '',
  fecha_hasta:  props.valor.fecha_hasta   || '',
  prioridades:  [...(props.valor.prioridades   || [])],
  categorias:   [...(props.valor.categorias    || [])],
  etiquetas:    [...(props.valor.etiquetas     || [])],
  proyecto_id:  props.valor.proyecto_id   ?? null,
  sinProyecto:  props.valor.sinProyecto   || false,
  responsables: [...(props.valor.responsables  || [])],
  id_op:        props.valor.id_op         || '',
  id_pedido:    props.valor.id_pedido     || '',
  id_remision:  props.valor.id_remision   || ''
})

// Posición del popup debajo del botón ancla
const popStyle = ref({ top: '60px', right: '16px' })

onMounted(() => {
  if (props.anchorEl) {
    const rect = props.anchorEl.getBoundingClientRect()
    const isMobile = window.innerWidth <= 768
    if (isMobile) {
      popStyle.value = { bottom: '0', left: '0', right: '0', borderRadius: '12px 12px 0 0', top: 'auto' }
    } else {
      popStyle.value = {
        top:   (rect.bottom + window.scrollY + 6) + 'px',
        right: (window.innerWidth - rect.right) + 'px'
      }
    }
  }
})

function toggleArr(arr, val) {
  const i = arr.indexOf(val)
  if (i === -1) arr.push(val)
  else arr.splice(i, 1)
}

function limpiar() {
  local.nombre = ''
  local.fecha_desde = ''
  local.fecha_hasta = ''
  local.prioridades.splice(0)
  local.categorias.splice(0)
  local.etiquetas.splice(0)
  local.proyecto_id = null
  local.sinProyecto = false
  local.responsables.splice(0)
  local.id_op = ''
  local.id_pedido = ''
  local.id_remision = ''
  emit('aplicar', null)
}

function aplicar() {
  const f = {
    nombre:       local.nombre.trim() || null,
    fecha_desde:  local.fecha_desde  || null,
    fecha_hasta:  local.fecha_hasta  || null,
    prioridades:  [...local.prioridades],
    categorias:   [...local.categorias],
    etiquetas:    [...local.etiquetas],
    proyecto_id:  local.sinProyecto ? 'null' : (local.proyecto_id ?? null),
    sinProyecto:  local.sinProyecto,
    responsables: [...local.responsables],
    id_op:        (local.id_op || '').trim() || null,
    id_pedido:    (local.id_pedido || '').trim() || null,
    id_remision:  (local.id_remision || '').trim() || null
  }
  emit('aplicar', f)
}
</script>

<style scoped>
/* Overlay transparente para cerrar al click fuera */
.fpop-overlay {
  position: fixed; inset: 0; z-index: 299;
}

/* Panel */
.fpop {
  position: fixed;
  z-index: 300;
  width: 320px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--bg-elevated, var(--bg-card));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex; flex-direction: column;
}

@media (max-width: 768px) {
  .fpop {
    width: 100%;
    max-height: 75vh;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
  }
}

.fpop-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.fpop-title {
  font-size: 12px; font-weight: 600; color: var(--text-primary);
}

.fpop-section {
  padding: 10px 14px 4px;
}
.fpop-label {
  font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-tertiary);
  margin: 0 0 6px;
}

.fpop-fechas {
  display: flex; gap: 8px;
}
.fpop-fecha-wrap {
  flex: 1; display: flex; flex-direction: column; gap: 3px;
}
.fpop-fecha-lbl {
  font-size: 10px; color: var(--text-tertiary);
}
.fpop-date {
  height: 26px !important; font-size: 11px !important; padding: 0 6px !important;
}

.fpop-chips {
  display: flex; flex-wrap: wrap; gap: 5px;
}
.fpop-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; height: 22px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  background: transparent;
  font-size: 11px; color: var(--text-secondary);
  cursor: pointer; transition: all 80ms;
  white-space: nowrap;
  font-family: var(--font-sans);
}
.fpop-chip:hover { border-color: var(--border-strong); color: var(--text-primary); }
.fpop-chip.active { font-weight: 500; }
.fpop-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}

.fpop-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 6px;
  padding: 10px 14px 12px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
  margin-top: 4px;
}
</style>
