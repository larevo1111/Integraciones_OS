<template>
  <div style="display:flex;height:100%;overflow:hidden">

    <!-- Lista principal -->
    <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0">

      <!-- Header de proyecto activo (breadcrumb) -->
      <div v-if="proyectoFiltro" class="proyecto-header-bar">
        <a class="proyecto-back-link" @click="router.replace(props.soloMias ? '/tareas' : '/equipo')">
          <span class="material-icons" style="font-size:15px">arrow_back</span>
          {{ props.soloMias ? 'Mis Tareas' : 'Equipo' }}
        </a>
        <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">chevron_right</span>
        <span class="proyecto-dot-hdr" :style="{ background: proyectoFiltro.color || '#607D8B' }"></span>
        <span class="proyecto-header-nombre">{{ proyectoFiltro.nombre }}</span>
      </div>

      <!-- Barra de filtros -->
      <div class="filtros-bar-wrap">
        <div class="filtros-bar">
          <button
            v-for="f in FILTROS"
            :key="f.key"
            class="chip"
            :class="{ active: filtroActivo === f.key }"
            :ref="f.key === 'personalizado' ? (el) => btnPersonalizadoRef = el : undefined"
            @click="onFiltroClick(f.key)"
          >
            {{ f.label }}
            <span v-if="f.key === 'hoy' && conteoHoy" class="chip-count">{{ conteoHoy }}</span>
            <span v-if="f.key === 'personalizado' && filtroPersonalizadoCount" class="chip-count">{{ filtroPersonalizadoCount }}</span>
          </button>

          <!-- Agrupar por -->
          <div style="position:relative;margin-left:auto;flex-shrink:0" ref="btnAgruparWrap">
            <button class="chip chip-agrupar" @click="toggleMenuAgrupar" ref="btnAgruparRef">
              <span class="material-icons" style="font-size:13px">sort</span>
              {{ AGRUPACIONES.find(a => a.key === agruparPor)?.label }}
              <span class="material-icons" style="font-size:13px">expand_more</span>
            </button>
            <Teleport to="body">
              <div v-if="menuAgrupar" class="dropdown-backdrop" @click="menuAgrupar=false" />
              <div v-if="menuAgrupar" class="dropdown-menu-teleport" :style="dropdownAgruparStyle" @mouseleave="menuAgrupar=false">
                <div
                  v-for="ag in AGRUPACIONES"
                  :key="ag.key"
                  class="dropdown-item-teleport"
                  :class="{ active: agruparPor === ag.key }"
                  @click="agruparPor = ag.key; menuAgrupar = false"
                >
                  <span class="material-icons" style="font-size:14px">{{ agruparPor === ag.key ? 'radio_button_checked' : 'radio_button_unchecked' }}</span>
                  {{ ag.label }}
                </div>
              </div>
            </Teleport>
          </div>
        </div>
      </div>

      <!-- Calendario inline -->
      <div v-if="filtroActivo === 'calendario'" class="cal-inline">
        <div class="cal-nav-row">
          <button class="cal-nav-btn" @click="calMesAnt"><span class="material-icons">chevron_left</span></button>
          <span class="cal-mes-label">{{ calMesLabel }}</span>
          <button class="cal-nav-btn" @click="calMesSig"><span class="material-icons">chevron_right</span></button>
          <button v-if="calMesOffset !== 0" class="cal-hoy-btn" @click="calIrHoy">Hoy</button>
        </div>
        <div class="cal-grid">
          <div v-for="d in calDiasSemana" :key="d" class="cal-dow">{{ d }}</div>
          <div
            v-for="(c, i) in calCeldas" :key="i"
            class="cal-cell"
            :class="{ 'cal-otro': c.otro, 'cal-hoy': c.iso === hoyISO(), 'cal-sel': c.iso === calFechaSel, 'cal-tiene': calConteos[c.iso] }"
            @click="calSelDia(c.iso)"
          >
            <span class="cal-num">{{ c.dia }}</span>
            <span v-if="calConteos[c.iso]" class="cal-dot" />
          </div>
        </div>
        <div class="cal-dia-info">
          <span class="cal-dia-label">{{ calDiaLabel }}</span>
          <span class="cal-dia-count">{{ tareas.length }} tarea{{ tareas.length !== 1 ? 's' : '' }}</span>
        </div>
      </div>

      <!-- QuickAdd (desktop y mobile) -->
      <div class="quickadd-wrap">
        <form class="quickadd-row" :class="{ activo: qaActivo }" @submit.prevent="qaAgregar">
          <span class="material-icons quickadd-plus">add</span>
          <input
            ref="qaInputRef"
            class="quickadd-input"
            v-model="qaTitulo"
            placeholder="Agregar una tarea..."
            @focus="qaActivo = true"
            @keydown.escape="qaCancelar"
          />
          <template v-if="qaActivo">
            <button type="button" class="btn btn-ghost btn-sm" @click="qaCancelar">Cancelar</button>
            <button type="submit" class="btn btn-primary btn-sm" :disabled="!qaTitulo || qaGuardando">
              {{ qaGuardando ? '...' : 'Agregar' }}
            </button>
          </template>
        </form>

        <!-- Categorías chips + OP -->
        <div v-if="qaActivo" class="quickadd-cats">
          <button
            v-for="c in categorias"
            :key="c.id"
            class="cat-chip"
            :class="{ selected: qaCatId === c.id }"
            @click="qaCatId = c.id"
          >
            <span class="cat-dot" :style="{ background: c.color }"></span>
            {{ c.nombre.replace(/_/g, ' ') }}
          </button>
        </div>
        <!-- Proyecto + etiquetas + OP -->
        <div v-if="qaActivo" class="quickadd-extra">
          <ProyectoSelector
            v-model="qaProyectoId"
            :proyectos="proyectos"
            @crear-item="tipo => abrirPanelItem(tipo)"
          />
          <EtiquetasSelector
            v-model="qaEtiquetas"
            :etiquetas="etiquetas"
            @etiqueta-creada="e => etiquetas.push(e)"
            @etiqueta-actualizada="e => { const i = etiquetas.findIndex(x => x.id === e.id); if (i !== -1) etiquetas[i] = e }"
            @etiqueta-eliminada="id => { const i = etiquetas.findIndex(x => x.id === id); if (i !== -1) etiquetas.splice(i, 1) }"
          />
        </div>
        <div v-if="qaActivo && qaCatEsProduccion" class="quickadd-op">
          <OpSelector v-model="qaOp" style="max-width:360px" />
        </div>
        <div v-if="qaActivo && qaCatEsEmpaque" class="quickadd-op">
          <div style="display:flex;flex-direction:column;gap:6px;max-width:360px">
            <RemisionSelector v-model="qaRemision" />
            <PedidoSelector   v-model="qaPedido" />
          </div>
        </div>
      </div>

      <!-- Lista de tareas -->
      <div class="page-body lista-tareas" v-if="!cargando">
        <div v-if="!grupos.length && !completadasFiltradas.length" class="empty-state">
          <span class="material-icons" style="font-size:32px">check_circle_outline</span>
          <p>No hay tareas con estos filtros</p>
        </div>

        <template v-for="grupo in grupos" :key="grupo.key">
          <div class="grupo-header">
            <div class="grupo-color-bar" :style="{ background: grupo.color }" />
            <span class="grupo-nombre">{{ grupo.nombre }}</span>
            <span class="grupo-count">{{ grupo.tareas.length }}</span>
          </div>
          <template v-for="t in grupo.tareas" :key="t.id">
            <TareaItem
              :tarea="t"
              :seleccionada="tareaSeleccionada?.id === t.id"
              :seleccionada-multi="seleccionMultiIds.includes(t.id)"
              :usuario-actual="auth.usuario?.email"
              :expandida="!!subtareasExpandidas[t.id]"
              :mostrar-responsable="!props.soloMias"
              :compacto="isMobile"
              @click="seleccionar"
              @cambiar-estado="cambiarEstado"
              @agregar-subtarea="iniciarSubtarea"
              @toggle-subtareas="toggleSubtareas"
              @editar-titulo="editarTituloInline"
              @seleccionar-multi="onSeleccionarMulti"
            />
            <!-- Subtareas expandidas -->
            <template v-if="subtareasExpandidas[t.id]">
              <TareaItem
                v-for="sub in subtareasData[t.id] || []"
                :key="sub.id"
                :tarea="sub"
                :seleccionada="tareaSeleccionada?.id === sub.id"
                :seleccionada-multi="seleccionMultiIds.includes(sub.id)"
                :usuario-actual="auth.usuario?.email"
                :mostrar-responsable="!props.soloMias"
                :compacto="isMobile"
                @click="seleccionar"
                @cambiar-estado="cambiarEstado"
                @editar-titulo="editarTituloInline"
                @seleccionar-multi="onSeleccionarMulti"
              />
              <!-- Inline quickadd para nueva subtarea -->
              <form v-if="qaSubtareaParentId === t.id" class="subtarea-quickadd" @click.stop @submit.prevent="guardarSubtarea(t)">
                <span class="material-icons" style="font-size:13px;color:var(--text-tertiary)">subdirectory_arrow_right</span>
                <input
                  ref="qaSubInputRef"
                  v-model="qaSubTitulo"
                  class="subtarea-input"
                  placeholder="Nueva subtarea..."
                  @keydown.escape="cancelarSubtarea"
                />
                <button type="submit" class="btn-sub-ok" :disabled="!qaSubTitulo.trim()" title="Agregar">
                  <span class="material-icons" style="font-size:13px">check</span>
                </button>
                <button type="button" class="btn-sub-cancel" @click="cancelarSubtarea" title="Cancelar">
                  <span class="material-icons" style="font-size:13px">close</span>
                </button>
              </form>
            </template>
          </template>
        </template>

        <!-- Completadas al fondo (colapsables) -->
        <template v-if="completadasFiltradas.length">
          <div class="completadas-header" @click="mostrarCompletadas = !mostrarCompletadas">
            <span class="material-icons" style="font-size:16px">{{ mostrarCompletadas ? 'expand_more' : 'chevron_right' }}</span>
            Completadas ({{ completadasFiltradas.length }})
          </div>
          <template v-if="mostrarCompletadas">
            <TareaItem
              v-for="t in completadasFiltradas"
              :key="t.id"
              :tarea="t"
              :seleccionada="tareaSeleccionada?.id === t.id"
              :seleccionada-multi="seleccionMultiIds.includes(t.id)"
              :usuario-actual="auth.usuario?.email"
              :mostrar-responsable="!props.soloMias"
              :compacto="isMobile"
              @click="seleccionar"
              @cambiar-estado="cambiarEstado"
              @editar-titulo="editarTituloInline"
              @seleccionar-multi="onSeleccionarMulti"
            />
          </template>
        </template>
      </div>

      <div v-else class="empty-state"><span class="material-icons spin">refresh</span></div>

      <!-- FAB mobile (oculto durante multi-selección) -->
      <button v-if="!seleccionMultiIds.length" class="fab d-mobile-only" @click="mostrarForm = true">
        <span class="material-icons">add</span>
      </button>
    </div>

    <!-- Panel lateral derecho (desktop) -->
    <Transition name="panel">
      <TareaPanel
        v-if="tareaSeleccionada"
        :tarea="tareaSeleccionada"
        :usuarios="usuarios"
        :categorias="categorias"
        :proyectos="proyectos"
        :etiquetas="etiquetas"
        @cerrar="tareaSeleccionada = null"
        @actualizada="onTareaActualizada"
        @eliminar="eliminar"
        @crear-item="tipo => abrirPanelItem(tipo)"
        @abrir-padre="abrirPadre"
        class="d-desktop-only"
      />
    </Transition>

    <!-- Bottom sheet detalle de tarea (mobile) -->
    <Teleport to="body">
      <Transition name="bsheet">
        <div v-if="tareaSeleccionada && isMobile" class="bsheet-overlay" @click.self="tareaSeleccionada = null">
          <div
            class="bsheet-panel"
            :class="{ 'bsheet-full': bsheetEstado === 'full' }"
            :style="bsheetPanelDragStyle"
          >
            <!-- Handle arrastrable -->
            <div
              class="bsheet-handle-area"
              @touchstart="bsheetTouchStart"
              @touchmove.prevent="bsheetTouchMove"
              @touchend="bsheetTouchEnd"
              @touchcancel="bsheetTouchEnd"
            >
              <div class="bsheet-handle"></div>
              <button
                v-if="bsheetEstado === 'full'"
                class="bsheet-close-btn"
                @click.stop="tareaSeleccionada = null"
              >
                <span class="material-icons" style="font-size:20px">close</span>
              </button>
            </div>
            <TareaPanel
              :tarea="tareaSeleccionada"
              :usuarios="usuarios"
              :categorias="categorias"
              :proyectos="proyectos"
              :etiquetas="etiquetas"
              @cerrar="tareaSeleccionada = null"
              @actualizada="onTareaActualizada"
              @eliminar="eliminar"
              @crear-item="tipo => abrirPanelItem(tipo)"
              @abrir-padre="abrirPadre"
            />
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Popup filtro personalizado -->
    <FiltroPersonalizado
      v-if="mostrarFiltroPopup"
      :categorias="categorias"
      :etiquetas="etiquetas"
      :proyectos="proyectos"
      :usuarios="usuarios"
      :anchor-el="btnPersonalizadoRef"
      :valor="filtroPersonalizado || {}"
      @aplicar="onAplicarFiltro"
      @cerrar="onCerrarFiltroPopup"
    />

    <!-- Bottom sheet / modal nueva tarea (mobile) -->
    <TareaForm
      v-model="mostrarForm"
      :categorias="categorias"
      :proyectos="proyectos"
      :etiquetas="etiquetas"
      :usuarios="usuarios"
      @guardada="onTareaGuardada"
    />

    <!-- Barra flotante multi-selección -->
    <Teleport to="body">
      <Transition name="multi-bar">
        <div v-if="seleccionMultiIds.length" class="multi-bar">
          <!-- Fila 1: close + count -->
          <div class="multi-bar-row1">
            <button class="multi-bar-close" @click="seleccionMultiIds = []" title="Cancelar selección">
              <span class="material-icons" style="font-size:15px">close</span>
            </button>
            <span class="multi-bar-count">{{ seleccionMultiIds.length }} seleccionada{{ seleccionMultiIds.length !== 1 ? 's' : '' }}</span>
            <div class="multi-bar-divider d-desktop-divider" />
          </div>

          <!-- Fila 2 (mobile) / misma línea (desktop): acciones -->
          <div class="multi-bar-actions">
            <!-- Fecha -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuFecha }" @click="cerrarMenusMulti('fecha')">
                <span class="material-icons" style="font-size:14px">event</span>
              </button>
              <div v-if="multiMenuFecha" class="multi-bar-menu">
                <div class="multi-menu-item" @click="aplicarFechaMulti(isoRelativo(0))">Hoy</div>
                <div class="multi-menu-item" @click="aplicarFechaMulti(isoRelativo(1))">Mañana</div>
                <div class="multi-menu-item" @click="aplicarFechaMulti(isoRelativo(2))">Pasado mañana</div>
                <div class="multi-menu-sep" />
                <input type="date" class="multi-date-input" @change="aplicarFechaMulti($event.target.value)" />
                <div class="multi-menu-item" @click="aplicarFechaMulti(null)">Sin fecha</div>
              </div>
            </div>

            <!-- Estado -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuEstado }" @click="cerrarMenusMulti('estado')">
                <span class="material-icons" style="font-size:14px">swap_horiz</span> Estado
              </button>
              <div v-if="multiMenuEstado" class="multi-bar-menu">
                <div v-for="e in ['Pendiente','En Progreso','Completada','Cancelada']" :key="e" class="multi-menu-item" @click="aplicarEstadoMulti(e)">{{ e }}</div>
              </div>
            </div>

            <!-- Categoría -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuCategoria }" @click="cerrarMenusMulti('categoria')">
                <span class="material-icons" style="font-size:14px">label</span> Cat.
              </button>
              <div v-if="multiMenuCategoria" class="multi-bar-menu multi-bar-menu-scroll">
                <div v-for="c in categorias" :key="c.id" class="multi-menu-item multi-menu-item-dot" @click="aplicarCategoriaMulti(c.id)">
                  <span class="multi-dot" :style="{ background: c.color }" />
                  {{ c.nombre.replace(/_/g, ' ') }}
                </div>
              </div>
            </div>

            <!-- Proyecto -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuProyecto }" @click="cerrarMenusMulti('proyecto')">
                <span class="material-icons" style="font-size:14px">folder</span> Proy.
              </button>
              <div v-if="multiMenuProyecto" class="multi-bar-menu multi-bar-menu-scroll">
                <div v-for="p in proyectos" :key="p.id" class="multi-menu-item multi-menu-item-dot" @click="aplicarProyectoMulti(p.id)">
                  <span class="multi-dot" :style="{ background: p.color || '#607D8B' }" />
                  {{ p.nombre }}
                </div>
                <div class="multi-menu-sep" />
                <div class="multi-menu-item" @click="aplicarProyectoMulti(null)">Sin proyecto</div>
              </div>
            </div>

            <!-- Etiquetas -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuEtiqueta }" @click="cerrarMenusMulti('etiqueta')">
                <span class="material-icons" style="font-size:14px">sell</span>
                <span class="d-desktop-only">Etiq.</span>
              </button>
              <div v-if="multiMenuEtiqueta" class="multi-bar-menu multi-bar-menu-scroll">
                <div v-for="e in etiquetas" :key="e.id" class="multi-menu-item multi-menu-item-dot" @click="aplicarEtiquetaMulti(e.id)">
                  <span class="multi-dot" :style="{ background: e.color || '#607D8B' }" />
                  {{ e.nombre }}
                </div>
                <div class="multi-menu-sep" />
                <form class="multi-menu-nueva-etiq" @submit.prevent="crearEtiquetaDesdeMulti">
                  <input v-model="nuevaEtiquetaMulti" placeholder="Nueva etiqueta..." class="multi-menu-nueva-input" />
                  <button type="submit" class="multi-menu-nueva-btn" :disabled="!nuevaEtiquetaMulti.trim()">
                    <span class="material-icons" style="font-size:14px">add</span>
                  </button>
                </form>
                <div class="multi-menu-sep" />
                <div class="multi-menu-item" @click="quitarEtiquetasMulti">Quitar todas</div>
              </div>
            </div>

            <!-- Responsable -->
            <div style="position:relative">
              <button class="multi-bar-btn" :class="{ 'multi-bar-btn-active': multiMenuResponsable }" @click="cerrarMenusMulti('responsable')">
                <span class="material-icons" style="font-size:14px">person</span>
              </button>
              <div v-if="multiMenuResponsable" class="multi-bar-menu multi-bar-menu-scroll">
                <div v-for="u in usuarios" :key="u.email" class="multi-menu-item" @click="aplicarResponsableMulti(u.email)">
                  {{ u.nombre || u.email.split('@')[0] }}
                </div>
              </div>
            </div>

            <div class="multi-bar-divider" />

            <!-- Eliminar -->
            <button class="multi-bar-btn multi-bar-btn-danger" @click="eliminarMulti">
              <span class="material-icons" style="font-size:14px">delete</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Mini-modal: tiempo al completar tarea -->
    <Teleport to="body">
      <Transition name="tiempo-modal">
        <div v-if="tiempoModal" class="tiempo-modal-overlay" @click.self="cancelarTiempoModal">
          <div class="tiempo-modal-card">
            <p class="tiempo-modal-titulo">¿Cuánto tiempo tomó?</p>
            <p class="tiempo-modal-subtitulo">{{ tiempoModal.tarea.titulo }}</p>
            <div class="tiempo-modal-input-row">
              <input
                ref="tiempoInputRef"
                v-model="tiempoInput"
                type="number"
                min="1"
                max="9999"
                placeholder="min"
                class="tiempo-modal-input"
                @keyup.enter="confirmarTiempoModal"
                @keyup.escape="cancelarTiempoModal"
              />
              <span class="tiempo-modal-unidad">minutos</span>
            </div>
            <div class="tiempo-modal-acciones">
              <button class="tiempo-modal-btn-omitir" @click="cancelarTiempoModal">Cancelar</button>
              <button
                class="tiempo-modal-btn-ok"
                :disabled="tiempoInput === ''"
                @click="confirmarTiempoModal"
              >Confirmar</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch, nextTick, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from 'src/services/api'
import { useAuthStore } from 'src/stores/authStore'

const props = defineProps({
  soloMias: { type: Boolean, default: true }
})
import TareaItem            from 'src/components/TareaItem.vue'
import TareaPanel           from 'src/components/TareaPanel.vue'
import TareaForm            from 'src/components/TareaForm.vue'
import OpSelector           from 'src/components/OpSelector.vue'
import RemisionSelector     from 'src/components/RemisionSelector.vue'
import PedidoSelector       from 'src/components/PedidoSelector.vue'
import ProyectoSelector     from 'src/components/ProyectoSelector.vue'
import EtiquetasSelector    from 'src/components/EtiquetasSelector.vue'
import FiltroPersonalizado  from 'src/components/FiltroPersonalizado.vue'

const auth  = useAuthStore()
const route  = useRoute()
const router = useRouter()
const abrirPanelItem = inject('abrirPanelItem', () => {})

// Detección mobile (≤768px) — controla bottom sheet vs panel lateral
const isMobile = ref(typeof window !== 'undefined' && window.innerWidth <= 768)
function onResize() { isMobile.value = window.innerWidth <= 768 }

// ─── BOTTOM SHEET DRAG ───
const bsheetEstado    = ref('half')  // 'half' | 'full'
const bsheetDragY     = ref(0)
const bsheetDragging  = ref(false)
let   _bsTouchStartY  = 0
let   _bsEstadoInicio = 'half'

const bsheetPanelDragStyle = computed(() =>
  bsheetDragging.value && bsheetDragY.value !== 0
    ? { transform: `translateY(${bsheetDragY.value}px)`, transition: 'none' }
    : {}
)

function bsheetTouchStart(e) {
  _bsTouchStartY  = e.touches[0].clientY
  _bsEstadoInicio = bsheetEstado.value
  bsheetDragging.value = true
  bsheetDragY.value = 0
}
function bsheetTouchMove(e) {
  if (!bsheetDragging.value) return
  const delta = e.touches[0].clientY - _bsTouchStartY
  if (_bsEstadoInicio === 'half') {
    // hacia arriba (negativo) = expandir, hacia abajo (positivo) = cerrar
    bsheetDragY.value = Math.max(-window.innerHeight * 0.46, Math.min(delta, window.innerHeight))
  } else {
    // en full: solo se puede bajar
    bsheetDragY.value = Math.max(0, delta)
  }
}
function bsheetTouchEnd() {
  const delta = bsheetDragY.value
  bsheetDragging.value = false
  bsheetDragY.value = 0
  if (_bsEstadoInicio === 'half') {
    if (delta < -80)  bsheetEstado.value = 'full'
    else if (delta > 120) tareaSeleccionada.value = null
    // else: vuelve a half (sin cambio)
  } else {
    if (delta > 100) bsheetEstado.value = 'half'
    // else: vuelve a full (sin cambio)
  }
}

// Estado principal
const tareas            = ref([])
const completadas       = ref([])
const categorias        = ref([])
const proyectos         = ref([])
const etiquetas         = ref([])
const usuarios          = ref([])
const cargando          = ref(true)
const tareaSeleccionada = ref(null)
const mostrarForm       = ref(false)
const mostrarCompletadas = ref(false)

// Multi-selección
const seleccionMultiIds = ref([])   // array de IDs seleccionados
const multiMenuFecha     = ref(false)
const multiMenuEstado    = ref(false)
const multiMenuCategoria = ref(false)
const multiMenuProyecto  = ref(false)
const multiMenuEtiqueta    = ref(false)
const multiMenuResponsable = ref(false)
const nuevaEtiquetaMulti   = ref('')

function cerrarMenusMulti(abrir) {
  const yaAbierto = abrir === 'fecha' && multiMenuFecha.value
    || abrir === 'estado' && multiMenuEstado.value
    || abrir === 'categoria' && multiMenuCategoria.value
    || abrir === 'proyecto' && multiMenuProyecto.value
    || abrir === 'etiqueta' && multiMenuEtiqueta.value
    || abrir === 'responsable' && multiMenuResponsable.value
  multiMenuFecha.value       = !yaAbierto && abrir === 'fecha'
  multiMenuEstado.value      = !yaAbierto && abrir === 'estado'
  multiMenuCategoria.value   = !yaAbierto && abrir === 'categoria'
  multiMenuProyecto.value    = !yaAbierto && abrir === 'proyecto'
  multiMenuEtiqueta.value    = !yaAbierto && abrir === 'etiqueta'
  multiMenuResponsable.value = !yaAbierto && abrir === 'responsable'
}

function isoRelativo(dias) {
  const d = new Date()
  d.setDate(d.getDate() + dias)
  return _localISO(d)
}
const menuAgrupar            = ref(false)
const btnAgruparRef          = ref(null)
const dropdownAgruparStyle   = ref({})
const filtroActivo      = ref('hoy')
const agruparPor        = ref(localStorage.getItem('gestion_agrupar') || 'categoria')

function toggleMenuAgrupar() {
  if (!menuAgrupar.value) {
    const rect = btnAgruparRef.value?.getBoundingClientRect()
    if (rect) {
      dropdownAgruparStyle.value = {
        position: 'fixed',
        top:  `${rect.bottom + 4}px`,
        right: `${window.innerWidth - rect.right}px`,
        zIndex: 9999
      }
    }
  }
  menuAgrupar.value = !menuAgrupar.value
}

// Filtro por proyecto (desde query param)
const proyectoFiltroId = computed(() => route.query.proyecto_id ? Number(route.query.proyecto_id) : null)
const proyectoFiltro   = computed(() => proyectos.value.find(p => p.id === proyectoFiltroId.value) || null)

// Subtareas
const subtareasExpandidas = ref({})   // { [tareaId]: true }
const subtareasData       = ref({})   // { [tareaId]: [subtarea, ...] }
const qaSubtareaParentId  = ref(null)
const qaSubTitulo         = ref('')
const qaSubInputRef       = ref(null)

async function toggleSubtareas(tarea) {
  const id = tarea.id
  if (subtareasExpandidas.value[id]) {
    subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: false }
    return
  }
  // Cargar subtareas si no están en caché
  if (!subtareasData.value[id]) {
    try {
      const data = await api(`/api/gestion/tareas/${id}/subtareas`)
      subtareasData.value = { ...subtareasData.value, [id]: data.subtareas || [] }
    } catch (e) { console.error(e); return }
  }
  subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: true }
}

async function iniciarSubtarea(tarea) {
  const id = tarea.id
  // Expandir primero si no está expandido
  if (!subtareasExpandidas.value[id]) {
    if (!subtareasData.value[id]) {
      try {
        const data = await api(`/api/gestion/tareas/${id}/subtareas`)
        subtareasData.value = { ...subtareasData.value, [id]: data.subtareas || [] }
      } catch {}
    }
    subtareasExpandidas.value = { ...subtareasExpandidas.value, [id]: true }
  }
  qaSubtareaParentId.value = id
  qaSubTitulo.value = ''
  await nextTick()
  const el = Array.isArray(qaSubInputRef.value) ? qaSubInputRef.value[0] : qaSubInputRef.value
  el?.focus()
}

function cancelarSubtarea() {
  qaSubtareaParentId.value = null
  qaSubTitulo.value = ''
}

async function guardarSubtarea(padre) {
  const titulo = qaSubTitulo.value.trim()
  if (!titulo) return
  qaSubTitulo.value = ''
  try {
    const data = await api('/api/gestion/tareas', {
      method: 'POST',
      body: JSON.stringify({
        titulo,
        categoria_id: padre.categoria_id,
        proyecto_id:  padre.proyecto_id || null,
        parent_id:    padre.id
      })
    })
    const subs = subtareasData.value[padre.id] || []
    subtareasData.value = { ...subtareasData.value, [padre.id]: [...subs, data.tarea] }
    const idx = tareas.value.findIndex(t => t.id === padre.id)
    if (idx !== -1) {
      tareas.value[idx] = { ...tareas.value[idx], subtareas_total: (tareas.value[idx].subtareas_total || 0) + 1 }
    }
    await nextTick()
    const el = Array.isArray(qaSubInputRef.value) ? qaSubInputRef.value[0] : qaSubInputRef.value
    el?.focus()
  } catch (e) { console.error(e) }
}

// QuickAdd desktop
const qaActivo      = ref(false)
const qaTitulo      = ref('')
const qaCatId       = ref(null)
const qaOp          = ref('')
const qaRemision    = ref('')
const qaPedido      = ref('')
const qaProyectoId  = ref(null)
const qaGuardando   = ref(false)
const qaInputRef    = ref(null)
const qaEtiquetas   = ref([])

const qaCatEsProduccion = computed(() =>
  categorias.value.find(c => c.id === qaCatId.value)?.es_produccion
)
const qaCatEsEmpaque = computed(() =>
  categorias.value.find(c => c.id === qaCatId.value)?.es_empaque
)

function qaCancelar() {
  qaActivo.value    = false
  qaTitulo.value    = ''
  qaOp.value        = ''
  qaRemision.value  = ''
  qaPedido.value    = ''
  qaProyectoId.value = null
  qaEtiquetas.value  = []
}

async function qaAgregar() {
  if (!qaTitulo.value || qaGuardando.value) return
  qaGuardando.value = true
  try {
    const body = {
      titulo:       qaTitulo.value,
      categoria_id: qaCatId.value || categorias.value.find(c => c.nombre === 'Varios')?.id || categorias.value[0]?.id,
      proyecto_id:  qaProyectoId.value ?? proyectoFiltroId.value ?? null,
      id_op:        qaOp.value      || null,
      id_remision:  qaRemision.value || null,
      id_pedido:    qaPedido.value   || null,
      etiquetas:    qaEtiquetas.value,
      fecha_limite: filtroActivo.value === 'hoy'    ? hoyISO() :
                    filtroActivo.value === 'manana'  ? mananaISO() : null
    }
    const data = await api('/api/gestion/tareas', { method: 'POST', body: JSON.stringify(body) })
    onTareaGuardada(data.tarea)
    qaTitulo.value     = ''
    qaOp.value         = ''
    qaRemision.value   = ''
    qaPedido.value     = ''
    qaProyectoId.value = null
    qaEtiquetas.value  = []
    qaActivo.value     = false
  } catch (e) { console.error(e) } finally { qaGuardando.value = false }
}

const FILTROS = [
  { key: 'hoy',          label: 'Hoy' },
  { key: 'manana',       label: 'Mañana' },
  { key: 'ayer',         label: 'Ayer' },
  { key: 'semana',       label: 'Esta semana' },
  { key: 'todas',        label: 'Todas' },
  { key: 'personalizado', label: 'Personalizado' },
  { key: 'calendario',   label: 'Calendario' }
]

// Filtro personalizado
const filtroPersonalizado   = ref(null)   // null = sin filtro activo
const mostrarFiltroPopup    = ref(false)
const btnPersonalizadoRef   = ref(null)

const filtroPersonalizadoCount = computed(() => {
  if (!filtroPersonalizado.value) return 0
  const f = filtroPersonalizado.value
  return [
    f.fecha_desde, f.fecha_hasta,
    ...(f.prioridades || []),
    ...(f.categorias  || []),
    ...(f.etiquetas   || []),
    f.proyecto_id
  ].filter(Boolean).length
})

function onFiltroClick(key) {
  if (key === 'personalizado') {
    mostrarFiltroPopup.value = !mostrarFiltroPopup.value
    filtroActivo.value = 'personalizado'
  } else {
    filtroActivo.value = key
    mostrarFiltroPopup.value = false
  }
}

function onAplicarFiltro(filtros) {
  filtroPersonalizado.value = filtros
  mostrarFiltroPopup.value  = false
  cargarTareas()
}

function onCerrarFiltroPopup() {
  mostrarFiltroPopup.value = false
  if (!filtroPersonalizado.value) filtroActivo.value = 'hoy'
}
const AGRUPACIONES = computed(() => {
  const base = [
    { key: 'categoria',   label: 'Categoría' },
    { key: 'prioridad',   label: 'Prioridad' },
    { key: 'fecha',       label: 'Fecha' },
    { key: 'proyecto',    label: 'Proyecto' }
  ]
  if (!props.soloMias) base.push({ key: 'responsable', label: 'Responsable' })
  return base
})

const conteoHoy = computed(() => tareas.value.filter(t => t.fecha_limite === hoyISO()).length)

// Usar fecha local (no UTC) para evitar desfase en noches Colombia (UTC-5)
function _localISO(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
function hoyISO()    { return _localISO(new Date()) }
function mananaISO() { const d = new Date(); d.setDate(d.getDate()+1); return _localISO(d) }

// ─── COMPLETADAS FILTRADAS (mismo filtro que pendientes) ───
function _finRealISO(t) {
  if (!t.fecha_fin_real) return null
  const s = String(t.fecha_fin_real)
  // Si viene con T (ISO): parsear como Date y extraer fecha local Colombia
  if (s.includes('T')) {
    const d = new Date(s)
    return _localISO(d)
  }
  // Si viene como "2026-04-01 18:00:23": tomar los primeros 10 chars
  return s.slice(0, 10)
}
function _coincideFecha(t, iso) {
  return t.fecha_limite === iso || _finRealISO(t) === iso
}
function _coincideRango(t, desde, hasta) {
  const fl = t.fecha_limite
  const fr = _finRealISO(t)
  return (fl && fl >= desde && fl <= hasta) || (fr && fr >= desde && fr <= hasta)
}
const completadasFiltradas = computed(() => {
  const all = completadas.value
  if (!all.length) return []
  const f = filtroActivo.value

  if (f === 'todas' || proyectoFiltroId.value) return all

  if (f === 'hoy')    return all.filter(t => _coincideFecha(t, hoyISO()))
  if (f === 'manana') return all.filter(t => _coincideFecha(t, mananaISO()))
  if (f === 'ayer')   return all.filter(t => _coincideFecha(t, isoRelativo(-1)))

  if (f === 'semana') {
    const hoy = new Date()
    const dow = hoy.getDay() || 7
    const lunes = new Date(hoy); lunes.setDate(hoy.getDate() - dow + 1)
    const domingo = new Date(lunes); domingo.setDate(lunes.getDate() + 6)
    return all.filter(t => _coincideRango(t, _localISO(lunes), _localISO(domingo)))
  }
  if (f === 'calendario') return all.filter(t => _coincideFecha(t, calFechaSel.value))

  if (f === 'personalizado' && filtroPersonalizado.value) {
    const fp = filtroPersonalizado.value
    return all.filter(t => {
      if (fp.fecha_desde || fp.fecha_hasta) {
        const fl = t.fecha_limite, fr = _finRealISO(t)
        const enRangoFl = fl && (!fp.fecha_desde || fl >= fp.fecha_desde) && (!fp.fecha_hasta || fl <= fp.fecha_hasta)
        const enRangoFr = fr && (!fp.fecha_desde || fr >= fp.fecha_desde) && (!fp.fecha_hasta || fr <= fp.fecha_hasta)
        if (!enRangoFl && !enRangoFr) return false
      }
      if (fp.categorias?.length && !fp.categorias.includes(t.categoria_id)) return false
      return true
    })
  }
  return all
})

// ─── CALENDARIO ───
const calMesOffset = ref(0)
const calFechaSel  = ref(hoyISO())
const calDiasSemana = ['L','M','M','J','V','S','D']

const calMesLabel = computed(() => {
  const d = _calMesBase()
  const s = d.toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })
  return s.charAt(0).toUpperCase() + s.slice(1)
})
function _calMesBase() {
  const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + calMesOffset.value); return d
}
const calCeldas = computed(() => {
  const b = _calMesBase(), año = b.getFullYear(), mes = b.getMonth()
  let sd = new Date(año, mes, 1).getDay(); sd = sd === 0 ? 6 : sd - 1
  const ultDia = new Date(año, mes + 1, 0).getDate()
  const prevUlt = new Date(año, mes, 0).getDate()
  const r = []
  for (let i = sd - 1; i >= 0; i--) { const d = new Date(año, mes - 1, prevUlt - i); r.push({ dia: prevUlt - i, iso: _localISO(d), otro: true }) }
  for (let d = 1; d <= ultDia; d++) { r.push({ dia: d, iso: _localISO(new Date(año, mes, d)), otro: false }) }
  const rest = 42 - r.length
  for (let d = 1; d <= rest; d++) { r.push({ dia: d, iso: _localISO(new Date(año, mes + 1, d)), otro: true }) }
  return r
})
const calConteos = computed(() => {
  const m = {}
  for (const t of tareas.value) { if (t.fecha_limite) m[t.fecha_limite] = (m[t.fecha_limite] || 0) + 1 }
  return m
})
const calDiaLabel = computed(() => {
  const [y, m, d] = calFechaSel.value.split('-').map(Number)
  const f = new Date(y, m - 1, d)
  const s = f.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })
  return s.charAt(0).toUpperCase() + s.slice(1)
})
function calMesAnt() { calMesOffset.value-- }
function calMesSig() { calMesOffset.value++ }
function calIrHoy() { calMesOffset.value = 0; calFechaSel.value = hoyISO() }
function calSelDia(iso) { calFechaSel.value = iso; cargarTareas() }

watch(tareaSeleccionada, (v, old) => { if (v && (!old || v.id !== old.id)) bsheetEstado.value = 'half' })
watch(agruparPor, val => localStorage.setItem('gestion_agrupar', val))
watch(filtroActivo, () => cargarTareas())
watch(calMesOffset, () => { if (filtroActivo.value === 'calendario') cargarTareas() })
watch(() => route.query.proyecto_id, () => cargarTareas())
watch(() => props.soloMias, (val) => {
  if (val && agruparPor.value === 'responsable') agruparPor.value = 'categoria'
  cargarTareas()
})

const ORDEN_PRIORIDAD    = ['Urgente','Alta','Media','Baja']
const COLORES_PRIORIDAD  = { Urgente: '#ef4444', Alta: '#f59e0b', Media: '#6b7280', Baja: '#374151' }
const PRIORIDAD_IDX      = { Urgente: 0, Alta: 1, Media: 2, Baja: 3 }

// Comparadores atómicos
const cmpPrioridad  = (a, b) => (PRIORIDAD_IDX[a.prioridad] ?? 2) - (PRIORIDAD_IDX[b.prioridad] ?? 2)
const cmpFecha      = (a, b) => (a.fecha_limite || '9999-12-31').localeCompare(b.fecha_limite || '9999-12-31')
const cmpCategoria  = (a, b) => (a.categoria_nombre || '').localeCompare(b.categoria_nombre || '')
const cmpProyecto   = (a, b) => (a.proyecto_nombre || 'zzz').localeCompare(b.proyecto_nombre || 'zzz')
const cmpResponsable = (a, b) => (a.responsable_nombre || a.responsable || '').localeCompare(b.responsable_nombre || b.responsable || '')

function sortWithin(lista, ...cmps) {
  return [...lista].sort((a, b) => {
    for (const fn of cmps) {
      const r = fn(a, b)
      if (r !== 0) return r
    }
    return 0
  })
}

// Orden secundario según agrupación activa y vista
function ordenSecundario(lista) {
  if (!props.soloMias) {
    // Vista Equipo
    switch (agruparPor.value) {
      case 'responsable': return sortWithin(lista, cmpCategoria, cmpProyecto)
      case 'categoria':   return sortWithin(lista, cmpResponsable, cmpProyecto)
      case 'proyecto':    return sortWithin(lista, cmpResponsable, cmpCategoria)
      case 'prioridad':   return sortWithin(lista, cmpResponsable, cmpCategoria)
      case 'fecha':       return sortWithin(lista, cmpResponsable, cmpCategoria)
    }
  } else {
    // Vista Mis Tareas
    switch (agruparPor.value) {
      case 'categoria': return sortWithin(lista, cmpPrioridad, cmpFecha)
      case 'prioridad': return sortWithin(lista, cmpFecha, cmpCategoria)
      case 'fecha':     return sortWithin(lista, cmpPrioridad, cmpCategoria)
      case 'proyecto':  return sortWithin(lista, cmpPrioridad, cmpFecha)
    }
  }
  return lista
}

const grupos = computed(() => {
  if (!tareas.value.length) return []
  if (agruparPor.value === 'categoria') {
    const map = {}
    tareas.value.forEach(t => {
      const k = t.categoria_id
      if (!map[k]) map[k] = { key: k, nombre: t.categoria_nombre, color: t.categoria_color, tareas: [] }
      map[k].tareas.push(t)
    })
    return Object.values(map).map(g => ({ ...g, tareas: ordenSecundario(g.tareas) }))
  }
  if (agruparPor.value === 'prioridad') {
    const map = {}
    tareas.value.forEach(t => {
      const p = t.prioridad || 'Media'
      if (!map[p]) map[p] = { key: p, nombre: p, color: COLORES_PRIORIDAD[p], tareas: [] }
      map[p].tareas.push(t)
    })
    return ORDEN_PRIORIDAD.filter(p => map[p]).map(p => ({ ...map[p], tareas: ordenSecundario(map[p].tareas) }))
  }
  if (agruparPor.value === 'fecha') {
    const map = {}
    tareas.value.forEach(t => {
      const f = t.fecha_limite || 'Sin fecha'
      if (!map[f]) map[f] = { key: f, nombre: formatGrupoFecha(f), color: '#6b7280', tareas: [] }
      map[f].tareas.push(t)
    })
    return Object.values(map)
      .sort((a, b) => {
        if (a.key === 'Sin fecha') return 1
        if (b.key === 'Sin fecha') return -1
        return a.key.localeCompare(b.key)
      })
      .map(g => ({ ...g, tareas: ordenSecundario(g.tareas) }))
  }
  if (agruparPor.value === 'proyecto') {
    const map = {}
    tareas.value.forEach(t => {
      const k = t.proyecto_id || 'sin-proyecto'
      if (!map[k]) map[k] = { key: k, nombre: t.proyecto_nombre || 'Sin proyecto', color: t.proyecto_color || '#607D8B', tareas: [] }
      map[k].tareas.push(t)
    })
    const sinProy = map['sin-proyecto']
    const conProy = Object.values(map).filter(g => g.key !== 'sin-proyecto').sort((a, b) => a.nombre.localeCompare(b.nombre))
    const all = sinProy ? [...conProy, sinProy] : conProy
    return all.map(g => ({ ...g, tareas: ordenSecundario(g.tareas) }))
  }
  if (agruparPor.value === 'responsable') {
    const map = {}
    tareas.value.forEach(t => {
      const k = t.responsable || 'sin-asignar'
      const nombre = t.responsable_nombre || t.responsable || 'Sin asignar'
      if (!map[k]) map[k] = { key: k, nombre, color: '#607D8B', tareas: [] }
      map[k].tareas.push(t)
    })
    const sinAsig = map['sin-asignar']
    const conAsig = Object.values(map).filter(g => g.key !== 'sin-asignar').sort((a, b) => a.nombre.localeCompare(b.nombre))
    const all = sinAsig ? [...conAsig, sinAsig] : conAsig
    return all.map(g => ({ ...g, tareas: ordenSecundario(g.tareas) }))
  }
  return []
})

function formatGrupoFecha(iso) {
  if (iso === 'Sin fecha') return 'Sin fecha'
  const d = new Date(iso + 'T00:00:00')
  const hoy = new Date(); hoy.setHours(0,0,0,0)
  if (d.getTime() === hoy.getTime()) return 'Hoy'
  if (d.getTime() === hoy.getTime() + 86400000) return 'Mañana'
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })
}

async function cargarTareas() {
  cargando.value = true
  try {
    const params = new URLSearchParams()
    // Siempre enviar fecha local del cliente para evitar desfase de zona horaria con servidor Hostinger
    params.set('fecha_hoy', hoyISO())
    if (props.soloMias) params.set('solo_mias', '1')
    if (proyectoFiltroId.value) {
      params.set('proyecto_id', proyectoFiltroId.value)
    } else if (filtroActivo.value === 'personalizado' && filtroPersonalizado.value) {
      const f = filtroPersonalizado.value
      if (f.fecha_desde)              params.set('fecha_desde',  f.fecha_desde)
      if (f.fecha_hasta)              params.set('fecha_hasta',  f.fecha_hasta)
      if (f.prioridades?.length)      params.set('prioridades',  f.prioridades.join(','))
      if (f.categorias?.length)       params.set('categorias',   f.categorias.join(','))
      if (f.etiquetas?.length)        params.set('etiquetas',    f.etiquetas.join(','))
      if (f.proyecto_id)              params.set('proyecto_id',  f.proyecto_id)
      if (f.responsables?.length)     params.set('responsables', f.responsables.join(','))
      if (f.id_op)                    params.set('id_op',        f.id_op)
    } else if (filtroActivo.value === 'calendario') {
      params.set('fecha_desde', calFechaSel.value)
      params.set('fecha_hasta', calFechaSel.value)
    } else if (filtroActivo.value !== 'todas' && filtroActivo.value !== 'personalizado') {
      params.set('filtro', filtroActivo.value)
    }
    const completadasParams = new URLSearchParams()
    if (props.soloMias) completadasParams.set('solo_mias', '1')
    if (proyectoFiltroId.value) completadasParams.set('proyecto_id', proyectoFiltroId.value)
    const completadasUrl = `/api/gestion/tareas/completadas?${completadasParams}`
    const [dataTareas, dataCompletadas] = await Promise.all([
      api(`/api/gestion/tareas?${params}`),
      api(completadasUrl)
    ])
    tareas.value      = dataTareas.tareas || []
    completadas.value = dataCompletadas.tareas || []
  } catch (e) { console.error(e) } finally { cargando.value = false }
}

async function cargarCatalogos() {
  const [resCat, resUsr, resProy, resEtq] = await Promise.allSettled([
    api('/api/gestion/categorias'),
    api('/api/gestion/usuarios'),
    api('/api/gestion/proyectos'),
    api('/api/gestion/etiquetas')
  ])
  if (resCat.status  === 'fulfilled') categorias.value = resCat.value.categorias   || []
  if (resUsr.status  === 'fulfilled') usuarios.value   = resUsr.value.usuarios     || []
  if (resProy.status === 'fulfilled') {
    const estadosFinales = ['Completado','Archivado','Resuelta','Cerrada','Cumplido','Cancelado','Aprobada','Descartada']
    proyectos.value = (resProy.value.proyectos || []).filter(p => !estadosFinales.includes(p.estado))
  }
  if (resEtq.status  === 'fulfilled') etiquetas.value  = resEtq.value.etiquetas    || []
}

function seleccionar(tarea) {
  // En modo multi: click normal también toglea
  if (seleccionMultiIds.value.length > 0) { onSeleccionarMulti(tarea); return }
  tareaSeleccionada.value = tareaSeleccionada.value?.id === tarea.id ? null : tarea
}

function onSeleccionarMulti(tarea) {
  const idx = seleccionMultiIds.value.indexOf(tarea.id)
  if (idx === -1) {
    // Si es la primera selección y hay panel abierto → incluir esa tarea también
    if (seleccionMultiIds.value.length === 0 && tareaSeleccionada.value && tareaSeleccionada.value.id !== tarea.id) {
      seleccionMultiIds.value.push(tareaSeleccionada.value.id)
    }
    seleccionMultiIds.value.push(tarea.id)
    tareaSeleccionada.value = null
  } else {
    seleccionMultiIds.value.splice(idx, 1)
  }
}

async function _bulkPut(ids, body) {
  await Promise.all(ids.map(id =>
    api(`/api/gestion/tareas/${id}`, { method: 'PUT', body: JSON.stringify(body) }).catch(console.error)
  ))
}

async function _postBulk(ids) {
  // Si la tarea abierta estaba en el set, cerrar panel
  if (tareaSeleccionada.value && ids.includes(tareaSeleccionada.value.id)) tareaSeleccionada.value = null
  seleccionMultiIds.value = []
  await cargarTareas()   // recarga con el filtro actual → vistas siempre correctas
}

async function aplicarFechaMulti(fecha) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  await _bulkPut(ids, { fecha_limite: fecha || null })
  await _postBulk(ids)
}

async function aplicarEstadoMulti(estado) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  await _bulkPut(ids, { estado })
  await _postBulk(ids)
}

async function aplicarCategoriaMulti(categoriaId) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  await _bulkPut(ids, { categoria_id: categoriaId })
  await _postBulk(ids)
}

async function aplicarProyectoMulti(proyectoId) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  await _bulkPut(ids, { proyecto_id: proyectoId })
  await _postBulk(ids)
}

async function crearEtiquetaDesdeMulti() {
  const nombre = nuevaEtiquetaMulti.value.trim()
  if (!nombre) return
  try {
    const data = await api('/api/gestion/etiquetas', {
      method: 'POST', body: JSON.stringify({ nombre })
    })
    etiquetas.value.push(data.etiqueta)
    nuevaEtiquetaMulti.value = ''
    await aplicarEtiquetaMulti(data.etiqueta.id)
  } catch (e) {
    console.error(e)
  }
}

async function aplicarEtiquetaMulti(etiquetaId) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  const allTareas = [...tareas.value, ...completadas.value]
  await Promise.all(ids.map(id => {
    const t = allTareas.find(x => x.id === id)
    const actuales = (t?.etiquetas || []).map(e => e.id)
    if (actuales.includes(etiquetaId)) return Promise.resolve()
    return api(`/api/gestion/tareas/${id}`, {
      method: 'PUT', body: JSON.stringify({ etiquetas: [...actuales, etiquetaId] })
    }).catch(console.error)
  }))
  await _postBulk(ids)
}

async function quitarEtiquetasMulti() {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  await _bulkPut(ids, { etiquetas: [] })
  await _postBulk(ids)
}

async function aplicarResponsableMulti(email) {
  cerrarMenusMulti(null)
  const ids = [...seleccionMultiIds.value]
  const allTareas = [...tareas.value, ...completadas.value]
  await Promise.all(ids.map(id => {
    const t = allTareas.find(x => x.id === id)
    const actuales = t?.responsables || (t?.responsable ? [t.responsable] : [])
    if (actuales.includes(email)) return Promise.resolve()
    return api(`/api/gestion/tareas/${id}`, {
      method: 'PUT', body: JSON.stringify({ responsables: [...actuales, email] })
    }).catch(console.error)
  }))
  await _postBulk(ids)
}

async function eliminarMulti() {
  const n = seleccionMultiIds.value.length
  if (!confirm(`¿Eliminar ${n} tarea${n !== 1 ? 's' : ''}?`)) return
  const ids = [...seleccionMultiIds.value]
  await Promise.all(ids.map(id =>
    api(`/api/gestion/tareas/${id}`, { method: 'DELETE' }).catch(console.error)
  ))
  await _postBulk(ids)
}

function onKeyDown(e) {
  if (e.key === 'Escape' && seleccionMultiIds.value.length > 0) {
    seleccionMultiIds.value = []
    cerrarMenusMulti(null)
  }
}

function onDocumentClick(e) {
  if (!seleccionMultiIds.value.length) return
  // Limpiar si el click no fue sobre una tarea ni sobre la barra flotante
  if (!e.target.closest('.tarea-item') && !e.target.closest('.multi-bar')) {
    seleccionMultiIds.value = []
    cerrarMenusMulti(null)
  }
}

// ─── MINI-MODAL TIEMPO AL COMPLETAR ───────────────────────────
const tiempoModal     = ref(null)   // { tarea } cuando está abierto
const tiempoInput     = ref('')     // minutos ingresados por el usuario
const tiempoInputRef  = ref(null)   // ref para hacer focus

function _parseColombia(str) {
  if (!str) return null
  if (str.includes('Z') || str.includes('+') || str.includes('-', 10)) return new Date(str)
  return new Date(str.replace(' ', 'T') + '-05:00')
}

function _minutosActuales(tarea) {
  let min = tarea.tiempo_real_min || 0
  if (tarea.cronometro_activo && tarea.cronometro_inicio) {
    const ini = _parseColombia(tarea.cronometro_inicio)
    if (ini) min += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 60000))
  }
  return min
}

async function cambiarEstado(tarea) {
  // Ciclo del check: Pendiente→EnProgreso→Completada→Pendiente
  // Cancelada: el check no la reactiva (se gestiona desde el panel de estado)
  const CICLO = { 'Pendiente': 'En Progreso', 'En Progreso': 'Completada', 'Completada': 'Pendiente' }
  const nextEstado = CICLO[tarea.estado] || 'Pendiente'
  // Al completar: abrir mini-modal con tiempo actual pre-llenado
  if (nextEstado === 'Completada') {
    tiempoModal.value = { tarea }
    tiempoInput.value = _minutosActuales(tarea) || ''
    nextTick(() => { tiempoInputRef.value?.focus(); tiempoInputRef.value?.select() })
    return
  }
  // Al revertir Completada→Pendiente, resetear tiempo_real_min acumulado
  const tiempoReset = (tarea.estado === 'Completada' && nextEstado === 'Pendiente') ? 0 : null
  await _aplicarEstado(tarea, nextEstado, tiempoReset)
  // Auto-iniciar cronómetro al poner En Progreso (si panel no está abierto con esta tarea)
  if (nextEstado === 'En Progreso' && !tarea.cronometro_activo && tareaSeleccionada.value?.id !== tarea.id) {
    try {
      const data = await api(`/api/gestion/tareas/${tarea.id}/iniciar`, { method: 'POST' })
      if (data?.tiempo?.inicio) {
        const idx = tareas.value.findIndex(t => t.id === tarea.id)
        if (idx !== -1) tareas.value[idx] = { ...tareas.value[idx], cronometro_activo: 1, cronometro_inicio: data.tiempo.inicio }
      }
    } catch (e) { console.error(e) }
  }
}

async function _aplicarEstado(tarea, estado, tiempo_real_min) {
  const body = { estado }
  if (tiempo_real_min != null) body.tiempo_real_min = tiempo_real_min
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}`, { method: 'PUT', body: JSON.stringify(body) })
    onTareaActualizada(data.tarea)
  } catch (e) { console.error(e) }
}

async function confirmarTiempoModal() {
  const { tarea } = tiempoModal.value
  const min = parseInt(tiempoInput.value) || null
  tiempoModal.value = null
  await _aplicarEstado(tarea, 'Completada', min)
}

function omitirTiempoModal() {
  const { tarea } = tiempoModal.value
  tiempoModal.value = null
  _aplicarEstado(tarea, 'Completada', null)
}

function cancelarTiempoModal() {
  tiempoModal.value = null
}

function onTareaActualizada(t) {
  // Si es subtarea → actualizar en subtareasData, no en tareas principales
  if (t.parent_id) {
    const subs = subtareasData.value[t.parent_id]
    if (subs) {
      subtareasData.value = {
        ...subtareasData.value,
        [t.parent_id]: subs.map(s => s.id === t.id ? t : s)
      }
    }
    if (tareaSeleccionada.value?.id === t.id) tareaSeleccionada.value = t
    return
  }
  // Tarea principal
  const esCompletada = ['Completada','Cancelada'].includes(t.estado)
  tareas.value      = tareas.value.filter(x => x.id !== t.id)
  completadas.value = completadas.value.filter(x => x.id !== t.id)
  if (esCompletada) completadas.value.unshift(t)
  else              tareas.value.push(t)
  if (tareaSeleccionada.value?.id === t.id) tareaSeleccionada.value = t
}

async function abrirPadre(parentId) {
  // Buscar en lista local primero
  let padre = tareas.value.find(t => t.id === parentId) || completadas.value.find(t => t.id === parentId)
  if (!padre) {
    try {
      const data = await api(`/api/gestion/tareas/${parentId}`)
      padre = data.tarea
    } catch { return }
  }
  tareaSeleccionada.value = padre
}

function onTareaGuardada(tarea) {
  tareas.value.push(tarea)
}

async function editarTituloInline({ tarea, titulo }) {
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}`, { method: 'PUT', body: JSON.stringify({ titulo }) })
    onTareaActualizada(data.tarea)
  } catch (e) { console.error(e) }
}

async function eliminar(tarea) {
  if (!confirm(`¿Eliminar "${tarea.titulo}"?`)) return
  try {
    await api(`/api/gestion/tareas/${tarea.id}`, { method: 'DELETE' })
    tareas.value = tareas.value.filter(t => t.id !== tarea.id)
    if (tareaSeleccionada.value?.id === tarea.id) tareaSeleccionada.value = null
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeyDown)
  document.addEventListener('click', onDocumentClick, true)
  await Promise.all([cargarTareas(), cargarCatalogos()])
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('click', onDocumentClick, true)
})
</script>

<style scoped>
.d-desktop-only { }
.d-mobile-only  { display: none; }
@media (max-width: 768px) {
  .d-desktop-only { display: none !important; }
  .d-mobile-only  { display: flex; }
  /* QuickAdd en mobile: padding ajustado */
  .quickadd-wrap { padding: 0 12px 8px; }
  /* Chips de categoría: scroll horizontal en lugar de wrap */
  .quickadd-cats {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-left: 0;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .quickadd-cats::-webkit-scrollbar { display: none; }
  /* Extra (proyecto + etiquetas) en móvil */
  .quickadd-extra { padding-left: 0; }
  /* Selectores OP/Remisión/Pedido: ancho completo sin padding excesivo */
  .quickadd-op { padding-left: 0; }
  .quickadd-op > div { max-width: 100% !important; }
}

/* QuickAdd */
.quickadd-wrap {
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 16px 10px;
}
/* OP row */
.quickadd-op {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 0 26px;
}

/* Panel */
.panel-enter-active, .panel-leave-active { transition: transform 200ms ease-out, opacity 200ms; }
.panel-enter-from, .panel-leave-to { transform: translateX(20px); opacity: 0; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Chip filtro proyecto activo */
/* Header de proyecto activo */
.proyecto-header-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 12px; flex-shrink: 0;
}
.proyecto-back-link {
  display: inline-flex; align-items: center; gap: 3px;
  color: var(--text-tertiary); text-decoration: none;
  transition: color 80ms;
}
.proyecto-back-link:hover { color: var(--text-primary); }
.proyecto-dot-hdr {
  width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
}
.proyecto-header-nombre {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
}

/* ─── SUBTAREAS ─── */
.subtarea-quickadd {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 16px 4px 40px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}
.subtarea-input {
  flex: 1; background: transparent; border: none; outline: none;
  font-size: 13px; color: var(--text-primary);
  font-family: var(--font-sans);
}
.subtarea-input::placeholder { color: var(--text-tertiary); }
.btn-sub-ok, .btn-sub-cancel {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; flex-shrink: 0;
  background: transparent; border: none; border-radius: var(--radius-sm);
  color: var(--text-tertiary); cursor: pointer;
  transition: color 80ms, background 80ms;
}
.btn-sub-ok:hover { color: var(--accent); }
.btn-sub-ok:disabled { opacity: 0.3; cursor: default; }
.btn-sub-cancel:hover { color: var(--color-error); background: var(--color-error-bg); }
.subtarea-add-row {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 16px 6px 42px;
  font-size: 11px; color: var(--text-tertiary);
  cursor: pointer; transition: color 80ms;
}
.subtarea-add-row:hover { color: var(--accent); }

/* ── Barra flotante multi-selección ── */
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
.multi-bar-row1 {
  display: contents;
}
.multi-bar-actions {
  display: contents;
}
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
.multi-bar-close:hover { background: var(--bg-hover); color: var(--text-secondary); }
.multi-bar-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px;
  border: none; border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px; cursor: pointer;
  transition: background 80ms, color 80ms;
}
.multi-bar-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.multi-bar-btn-active { background: var(--bg-hover); color: var(--text-primary); }
.multi-bar-btn-danger:hover { color: #ef4444; }

/* Mobile: multi-bar en 2 filas */
@media (max-width: 768px) {
  .multi-bar {
    flex-wrap: wrap;
    justify-content: center;
    max-width: calc(100vw - 32px);
    bottom: 16px;
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
.multi-menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }
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
.multi-menu-nueva-btn:hover:not(:disabled) { background: var(--bg-hover); color: var(--accent); }
.multi-menu-nueva-btn:disabled { opacity: 0.3; cursor: default; }
.multi-bar-menu-scroll { max-height: 200px; overflow-y: auto; }

/* Animación entrada/salida */
.multi-bar-enter-active, .multi-bar-leave-active { transition: all 180ms ease; }
.multi-bar-enter-from, .multi-bar-leave-to { opacity: 0; transform: translateX(-50%) translateY(8px); }

/* ─── CALENDARIO INLINE ─── */
.cal-inline { flex-shrink: 0; padding: 0 12px 4px; border-bottom: 1px solid var(--border-subtle); }
.cal-nav-row { display: flex; align-items: center; gap: 6px; padding: 6px 4px 4px; }
.cal-mes-label { font-size: 14px; font-weight: 600; color: var(--text-primary); min-width: 130px; text-align: center; }
.cal-nav-btn {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: var(--radius-sm);
  background: transparent; border: none; color: var(--text-secondary); cursor: pointer;
}
.cal-nav-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.cal-hoy-btn {
  margin-left: auto; padding: 2px 8px; height: 22px;
  border-radius: var(--radius-sm); border: 1px solid var(--border-default);
  background: transparent; color: var(--text-secondary); font-size: 11px; cursor: pointer;
}
.cal-hoy-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
.cal-dow { text-align: center; font-size: 10px; font-weight: 600; color: var(--text-tertiary); padding: 3px 0; }
.cal-cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 32px; border-radius: var(--radius-sm); cursor: pointer; position: relative;
  transition: background 80ms;
}
.cal-cell:hover { background: var(--bg-row-hover); }
.cal-num { font-size: 12px; color: var(--text-primary); line-height: 1; }
.cal-otro .cal-num { color: var(--text-tertiary); opacity: 0.4; }
.cal-hoy .cal-num {
  background: var(--accent); color: #000; font-weight: 600;
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.cal-sel { background: var(--bg-row-selected); }
.cal-sel .cal-num { color: var(--accent); font-weight: 600; }
.cal-hoy.cal-sel .cal-num { color: #000; }
.cal-dot { position: absolute; bottom: 2px; width: 4px; height: 4px; border-radius: 50%; background: var(--accent); }
.cal-dia-info { display: flex; align-items: center; gap: 8px; padding: 6px 4px 2px; }
.cal-dia-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cal-dia-count { font-size: 11px; color: var(--text-tertiary); }
</style>
