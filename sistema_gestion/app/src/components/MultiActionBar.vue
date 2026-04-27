<template>
  <Teleport to="body">
    <Transition name="multi-bar">
      <div v-if="count" class="multi-bar">
        <!-- Fila 1: close + count -->
        <div class="multi-bar-row1">
          <button class="multi-bar-close" @click="$emit('cerrar')" title="Cancelar selección">
            <span class="material-icons" style="font-size:15px">close</span>
          </button>
          <span class="multi-bar-count">{{ count }} seleccionada{{ count !== 1 ? 's' : '' }}</span>
          <div class="multi-bar-divider d-desktop-divider" />
        </div>

        <!-- Fila 2 (mobile) / misma línea (desktop): acciones -->
        <div class="multi-bar-actions">
          <!-- Fecha -->
          <div v-if="acciones.includes('fecha')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'fecha' }" @click="toggleMenu('fecha')">
              <span class="material-icons" style="font-size:14px">event</span>
            </button>
            <div v-if="abierto === 'fecha'" class="multi-bar-menu">
              <div class="multi-menu-item" @click="emitir('fecha', isoRel(0))">Hoy</div>
              <div class="multi-menu-item" @click="emitir('fecha', isoRel(1))">Mañana</div>
              <div class="multi-menu-item" @click="emitir('fecha', isoRel(2))">Pasado mañana</div>
              <div class="multi-menu-sep" />
              <input type="date" class="multi-date-input" @change="emitir('fecha', $event.target.value)" />
              <div class="multi-menu-item" @click="emitir('fecha', null)">Sin fecha</div>
            </div>
          </div>

          <!-- Estado -->
          <div v-if="acciones.includes('estado')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'estado' }" @click="toggleMenu('estado')">
              <span class="material-icons" style="font-size:14px">swap_horiz</span> Estado
            </button>
            <div v-if="abierto === 'estado'" class="multi-bar-menu">
              <div v-for="e in estadosFiltrados" :key="e" class="multi-menu-item" @click="emitir('estado', e)">{{ e }}</div>
            </div>
          </div>

          <!-- Prioridad -->
          <div v-if="acciones.includes('prioridad')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'prioridad' }" @click="toggleMenu('prioridad')">
              <span class="material-icons" style="font-size:14px">flag</span> Prio.
            </button>
            <div v-if="abierto === 'prioridad'" class="multi-bar-menu">
              <div v-for="p in ['Baja','Media','Alta','Urgente']" :key="p" class="multi-menu-item" @click="emitir('prioridad', p)">{{ p }}</div>
            </div>
          </div>

          <!-- Categoría -->
          <div v-if="acciones.includes('categoria')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'categoria' }" @click="toggleMenu('categoria')">
              <span class="material-icons" style="font-size:14px">label</span> Cat.
            </button>
            <div v-if="abierto === 'categoria'" class="multi-bar-menu multi-bar-menu-scroll">
              <div v-for="c in categorias" :key="c.id" class="multi-menu-item multi-menu-item-dot" @click="emitir('categoria', c.id)">
                <span class="multi-dot" :style="{ background: c.color }" />
                {{ c.nombre.replace(/_/g, ' ') }}
              </div>
            </div>
          </div>

          <!-- Proyecto -->
          <div v-if="acciones.includes('proyecto')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'proyecto' }" @click="toggleMenu('proyecto')">
              <span class="material-icons" style="font-size:14px">folder</span> Proy.
            </button>
            <div v-if="abierto === 'proyecto'" class="multi-bar-menu multi-bar-menu-scroll">
              <div v-for="p in proyectos" :key="p.id" class="multi-menu-item multi-menu-item-dot" @click="emitir('proyecto', p.id)">
                <span class="multi-dot" :style="{ background: p.color || '#607D8B' }" />
                {{ p.nombre }}
              </div>
              <div class="multi-menu-sep" />
              <div class="multi-menu-item" @click="emitir('proyecto', null)">Sin proyecto</div>
            </div>
          </div>

          <!-- Etiquetas -->
          <div v-if="acciones.includes('etiquetas')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'etiquetas' }" @click="toggleMenu('etiquetas')">
              <span class="material-icons" style="font-size:14px">sell</span>
              <span class="d-desktop-only">Etiq.</span>
            </button>
            <div v-if="abierto === 'etiquetas'" class="multi-bar-menu multi-bar-menu-scroll">
              <div v-for="e in etiquetas" :key="e.id" class="multi-menu-item multi-menu-item-dot" @click="emitir('etiqueta', e.id)">
                <span class="multi-dot" :style="{ background: e.color || '#607D8B' }" />
                {{ e.nombre }}
              </div>
              <div class="multi-menu-sep" />
              <form class="multi-menu-nueva-etiq" @submit.prevent="onNuevaEtiqueta">
                <input v-model="nuevaEtiqueta" placeholder="Nueva etiqueta..." class="multi-menu-nueva-input" />
                <button type="submit" class="multi-menu-nueva-btn" :disabled="!nuevaEtiqueta.trim()">
                  <span class="material-icons" style="font-size:14px">add</span>
                </button>
              </form>
              <div class="multi-menu-sep" />
              <div class="multi-menu-item" @click="emitir('quitar-etiquetas', null)">Quitar todas</div>
            </div>
          </div>

          <!-- Responsable -->
          <div v-if="acciones.includes('responsable')" style="position:relative">
            <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': abierto === 'responsable' }" @click="toggleMenu('responsable')">
              <span class="material-icons" style="font-size:14px">person</span>
            </button>
            <div v-if="abierto === 'responsable'" class="multi-bar-menu multi-bar-menu-scroll">
              <div v-for="u in usuarios" :key="u.email" class="multi-menu-item" @click="emitir('responsable', u.email)">
                {{ u.nombre || u.email.split('@')[0] }}
              </div>
            </div>
          </div>

          <div v-if="acciones.includes('eliminar')" class="multi-bar-divider" />

          <!-- Eliminar -->
          <button v-if="acciones.includes('eliminar')" class="multi-bar-btn multi-bar-btn-danger" @click="emitir('eliminar', null)">
            <span class="material-icons" style="font-size:14px">delete</span>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  count:      { type: Number, default: 0 },
  acciones:   { type: Array,  default: () => ['fecha','estado','categoria','proyecto','etiquetas','responsable','eliminar'] },
  estados:    { type: Array,  default: () => ['Pendiente','En Progreso','Cancelada'] },
  categorias: { type: Array,  default: () => [] },
  proyectos:  { type: Array,  default: () => [] },
  etiquetas:  { type: Array,  default: () => [] },
  usuarios:   { type: Array,  default: () => [] },
})

// Multiselect NUNCA permite Completada (exige modal individual)
const estadosFiltrados = computed(() =>
  props.estados.filter(e => e !== 'Completada')
)

const emit = defineEmits(['cerrar', 'aplicar', 'crear-etiqueta'])

const abierto = ref(null)
const nuevaEtiqueta = ref('')

function toggleMenu(menu) {
  abierto.value = abierto.value === menu ? null : menu
}

function emitir(tipo, valor) {
  abierto.value = null
  emit('aplicar', { tipo, valor })
}

function onNuevaEtiqueta() {
  const nombre = nuevaEtiqueta.value.trim()
  if (!nombre) return
  emit('crear-etiqueta', nombre)
  nuevaEtiqueta.value = ''
}

// Helper: ISO local +N días
function isoRel(dias) {
  const d = new Date()
  d.setDate(d.getDate() + dias)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
</script>

<style scoped>
.multi-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--bg-elevated, #1c1c1c);
  border: 1px solid var(--border-subtle, #333);
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.45);
  z-index: 500;
  white-space: nowrap;
  user-select: none;
}
.multi-bar-row1 { display: contents; }
.multi-bar-actions { display: contents; }
.multi-bar-count {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  padding: 0 4px;
}
.multi-bar-divider {
  width: 1px; height: 16px;
  background: var(--border-subtle);
  flex-shrink: 0;
  margin: 0 4px;
}
.multi-bar-close {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  border: none; border-radius: 50%;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 80ms;
  flex-shrink: 0;
}
.multi-bar-close:hover { background: var(--bg-card-hover); color: var(--text-secondary); }
.multi-bar-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px;
  border: none; border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px; cursor: pointer;
  transition: background 80ms, color 80ms;
}
.multi-bar-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.multi-bar-btn-active { background: var(--bg-card-hover); color: var(--text-primary); }
.multi-bar-btn-danger:hover { color: #ef4444; }

/* Mobile: multi-bar en 2 filas */
@media (max-width: 768px) {
  .multi-bar {
    flex-wrap: wrap;
    justify-content: center;
    max-width: calc(100vw - 32px);
    /* bottombar móvil ~53px de alto + safe-area; dejar 12px de margen */
    bottom: calc(65px + env(safe-area-inset-bottom, 0));
    padding: 6px 8px;
    gap: 2px;
  }
  .multi-bar-row1 {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    justify-content: center;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 2px;
  }
  .multi-bar-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-wrap: nowrap;
  }
  .d-desktop-divider { display: none; }
  .multi-bar-btn { padding: 4px 6px; font-size: 11px; }
}
.multi-bar-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-elevated, #1c1c1c);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.35);
  overflow: hidden;
  min-width: 140px;
  z-index: 10;
}
.multi-date-input {
  display: block;
  width: 100%;
  padding: 7px 10px;
  font-size: 12px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  cursor: pointer;
  box-sizing: border-box;
}
.multi-menu-item {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms;
}
.multi-menu-item:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.multi-menu-item-dot { display: flex; align-items: center; gap: 6px; }
.multi-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.multi-menu-sep { height: 1px; background: var(--border-subtle); margin: 3px 0; }
.multi-menu-nueva-etiq {
  display: flex; align-items: center; gap: 4px; padding: 4px 8px;
}
.multi-menu-nueva-input {
  flex: 1; min-width: 0; padding: 4px 8px; font-size: 12px;
  background: var(--bg-card, #222); border: 1px solid var(--border-subtle);
  border-radius: 5px; color: var(--text-primary); outline: none;
}
.multi-menu-nueva-input::placeholder { color: var(--text-tertiary); }
.multi-menu-nueva-input:focus { border-color: var(--accent); }
.multi-menu-nueva-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border: none; border-radius: 5px;
  background: transparent; color: var(--text-tertiary); cursor: pointer;
}
.multi-menu-nueva-btn:hover:not(:disabled) { background: var(--bg-card-hover); color: var(--accent); }
.multi-menu-nueva-btn:disabled { opacity: 0.3; cursor: default; }
.multi-bar-menu-scroll { max-height: 200px; overflow-y: auto; }

/* Animación entrada/salida */
.multi-bar-enter-active, .multi-bar-leave-active { transition: all 180ms ease; }
.multi-bar-enter-from, .multi-bar-leave-to { opacity: 0; transform: translateX(-50%) translateY(8px); }
</style>
