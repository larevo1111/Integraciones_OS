<template>
  <div class="gestion-layout">

    <!-- SIDEBAR (desktop) -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="sidebar-logo-icon">G</div>
        <span class="sidebar-logo-name">OS Gestión</span>
        <span
          class="material-icons sidebar-collapse-btn"
          style="font-size:18px;margin-left:auto"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >chevron_left</span>
      </div>

      <!-- Nav -->
      <nav class="sidebar-nav">
        <!-- ═══ MIS TAREAS (acordeón) ═══ -->
        <div class="sidebar-section">
          <div class="nav-item nav-item-acordeon" :class="{ active: ruta === '/tareas' && !$route.query.proyecto_id }">
            <span class="nav-item-toggle material-icons" @click.stop="toggleAcordeon('bloque-mis')">{{ acordeonAbierto['bloque-mis'] ? 'expand_more' : 'chevron_right' }}</span>
            <RouterLink to="/tareas" class="nav-item-link-grow">
              <span class="nav-item-icon material-icons">check_circle_outline</span>
              <span class="nav-item-label">Mis Tareas</span>
            </RouterLink>
          </div>
        </div>

        <template v-if="acordeonAbierto['bloque-mis']">
        <div v-for="sec in SECCIONES_SIDEBAR" :key="'mis-'+sec.tipo" class="sidebar-section sidebar-section-indented">
          <div class="sidebar-acordeon-header" @click="toggleAcordeon('mis-'+sec.tipo)">
            <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['mis-'+sec.tipo] ? 'expand_more' : 'chevron_right' }}</span>
            <span style="flex:1">{{ sec.label }}</span>
            <span v-if="misItemsPorTipo(sec.tipo).length" class="acordeon-count">{{ misItemsPorTipo(sec.tipo).length }}</span>
            <button class="btn-icon-tiny" :title="`Nuevo ${sec.singular}`" @click.stop="abrirPanel(sec.tipo)">
              <span class="material-icons" style="font-size:14px">add</span>
            </button>
          </div>
          <template v-if="acordeonAbierto['mis-'+sec.tipo]">
            <div
              v-for="p in misItemsPorTipo(sec.tipo)"
              :key="p.id"
              class="nav-item-proyecto-wrap"
              @mouseenter="proyectoHover = p.id"
              @mouseleave="proyectoHover = null"
            >
              <RouterLink
                :to="{ path: '/tareas', query: { proyecto_id: p.id } }"
                class="nav-item nav-item-proyecto"
                :class="{ active: ruta === '/tareas' && String($route.query.proyecto_id) === String(p.id) }"
              >
                <span class="nav-item-icon">
                  <span class="proyecto-dot-sm" :style="{ background: p.color || '#607D8B' }"></span>
                </span>
                <span class="nav-item-label">{{ p.nombre }}</span>
                <span v-if="p.tareas_pendientes && proyectoHover !== p.id" class="nav-item-count">{{ p.tareas_pendientes }}</span>
                <template v-if="proyectoHover === p.id">
                  <button class="btn-proyecto-check" title="Completar" @click.prevent.stop="completarItem(p)">
                    <span class="material-icons" style="font-size:15px">check_circle_outline</span>
                  </button>
                  <button class="btn-proyecto-menu" @click.prevent.stop="abrirMenuProyecto($event, p)">
                    <span class="material-icons" style="font-size:16px">more_vert</span>
                  </button>
                </template>
              </RouterLink>
            </div>
            <div v-if="!misItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty-hint">
              Sin {{ sec.label.toLowerCase() }}
            </div>
          </template>
        </div>

        <!-- Etiquetas -->
        <div class="sidebar-section sidebar-section-indented">
          <div class="sidebar-acordeon-header" @click="toggleAcordeon('mis-etiquetas')">
            <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['mis-etiquetas'] ? 'expand_more' : 'chevron_right' }}</span>
            <span style="flex:1">Etiquetas</span>
            <span v-if="misEtiquetasCount" class="acordeon-count">{{ misEtiquetasCount }}</span>
          </div>
          <template v-if="acordeonAbierto['mis-etiquetas']">
            <div
              v-for="e in etiquetasGlobal"
              v-show="e.mis_tareas_total"
              :key="e.id"
              class="nav-item-proyecto-wrap"
              @mouseenter="etiquetaHover = e.id"
              @mouseleave="etiquetaHover = null"
            >
              <RouterLink
                :to="{ path: '/tareas', query: { etiqueta_id: e.id } }"
                class="nav-item nav-item-proyecto"
                :class="{ active: ruta === '/tareas' && String($route.query.etiqueta_id) === String(e.id) }"
              >
                <span class="nav-item-icon">
                  <span class="proyecto-dot-sm" :style="{ background: e.color || '#888' }"></span>
                </span>
                <div v-if="etiquetaEditandoId === e.id" class="etiqueta-edit-row" @click.prevent.stop>
                  <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                  <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                    <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" ref="etiquetaInputRef" />
                  </form>
                  <button class="etiqueta-edit-btn etiqueta-edit-ok" @click.prevent.stop="guardarEtiquetaEdit(e)" title="Guardar">
                    <span class="material-icons" style="font-size:15px">check</span>
                  </button>
                  <button class="etiqueta-edit-btn etiqueta-edit-cancel" @click.prevent.stop="etiquetaEditandoId = null" title="Cancelar">
                    <span class="material-icons" style="font-size:15px">close</span>
                  </button>
                </div>
                <template v-else>
                  <span class="nav-item-label">{{ e.nombre }}</span>
                  <span v-if="e.mis_tareas_pendientes && etiquetaHover !== e.id" class="nav-item-count">{{ e.mis_tareas_pendientes }}</span>
                  <button v-if="etiquetaHover === e.id" class="btn-proyecto-menu" @click.prevent.stop="abrirMenuEtiqueta($event, e)">
                    <span class="material-icons" style="font-size:16px">more_vert</span>
                  </button>
                </template>
              </RouterLink>
            </div>
            <div v-if="!etiquetasGlobal.length" class="sidebar-empty-hint">Sin etiquetas</div>
          </template>
        </div>
        </template>

        <!-- ═══ SEPARADOR ═══ -->
        <div class="sidebar-separator" />

        <!-- ═══ EQUIPO (acordeón) ═══ -->
        <div class="sidebar-section">
          <div class="nav-item nav-item-acordeon" :class="{ active: ruta === '/equipo' }">
            <span class="nav-item-toggle material-icons" @click.stop="toggleAcordeon('bloque-eq')">{{ acordeonAbierto['bloque-eq'] ? 'expand_more' : 'chevron_right' }}</span>
            <RouterLink to="/equipo" class="nav-item-link-grow">
              <span class="nav-item-icon material-icons">group</span>
              <span class="nav-item-label">Equipo</span>
            </RouterLink>
          </div>
        </div>

        <template v-if="acordeonAbierto['bloque-eq']">
        <div v-for="sec in SECCIONES_SIDEBAR" :key="'eq-'+sec.tipo" class="sidebar-section sidebar-section-indented">
          <div class="sidebar-acordeon-header" @click="toggleAcordeon('eq-'+sec.tipo)">
            <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['eq-'+sec.tipo] ? 'expand_more' : 'chevron_right' }}</span>
            <span style="flex:1">{{ sec.label }}</span>
            <span v-if="equipoItemsPorTipo(sec.tipo).length" class="acordeon-count">{{ equipoItemsPorTipo(sec.tipo).length }}</span>
            <button class="btn-icon-tiny" :title="`Nuevo ${sec.singular}`" @click.stop="abrirPanel(sec.tipo)">
              <span class="material-icons" style="font-size:14px">add</span>
            </button>
          </div>
          <template v-if="acordeonAbierto['eq-'+sec.tipo]">
            <div
              v-for="p in equipoItemsPorTipo(sec.tipo)"
              :key="p.id"
              class="nav-item-proyecto-wrap"
              @mouseenter="proyectoHover = p.id"
              @mouseleave="proyectoHover = null"
            >
              <RouterLink
                :to="{ path: '/equipo', query: { proyecto_id: p.id } }"
                class="nav-item nav-item-proyecto"
                :class="{ active: ruta === '/equipo' && String($route.query.proyecto_id) === String(p.id) }"
              >
                <span class="nav-item-icon">
                  <span class="proyecto-dot-sm" :style="{ background: p.color || '#607D8B' }"></span>
                </span>
                <span class="nav-item-label">{{ p.nombre }}</span>
                <span v-if="p.tareas_pendientes && proyectoHover !== p.id" class="nav-item-count">{{ p.tareas_pendientes }}</span>
                <template v-if="proyectoHover === p.id">
                  <button class="btn-proyecto-check" title="Completar" @click.prevent.stop="completarItem(p)">
                    <span class="material-icons" style="font-size:15px">check_circle_outline</span>
                  </button>
                  <button class="btn-proyecto-menu" @click.prevent.stop="abrirMenuProyecto($event, p)">
                    <span class="material-icons" style="font-size:16px">more_vert</span>
                  </button>
                </template>
              </RouterLink>
            </div>
            <div v-if="!equipoItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty-hint">
              Sin {{ sec.label.toLowerCase() }}
            </div>
          </template>
        </div>

        <!-- Etiquetas (equipo) -->
        <div class="sidebar-section sidebar-section-indented">
          <div class="sidebar-acordeon-header" @click="toggleAcordeon('eq-etiquetas')">
            <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['eq-etiquetas'] ? 'expand_more' : 'chevron_right' }}</span>
            <span style="flex:1">Etiquetas</span>
            <span v-if="eqEtiquetasCount" class="acordeon-count">{{ eqEtiquetasCount }}</span>
          </div>
          <template v-if="acordeonAbierto['eq-etiquetas']">
            <div
              v-for="e in etiquetasGlobal"
              v-show="e.tareas_total"
              :key="e.id"
              class="nav-item-proyecto-wrap"
              @mouseenter="etiquetaHover = e.id"
              @mouseleave="etiquetaHover = null"
            >
              <RouterLink
                :to="{ path: '/equipo', query: { etiqueta_id: e.id } }"
                class="nav-item nav-item-proyecto"
                :class="{ active: ruta === '/equipo' && String($route.query.etiqueta_id) === String(e.id) }"
              >
                <span class="nav-item-icon">
                  <span class="proyecto-dot-sm" :style="{ background: e.color || '#888' }"></span>
                </span>
                <div v-if="etiquetaEditandoId === e.id" class="etiqueta-edit-row" @click.prevent.stop>
                  <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                  <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                    <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" ref="etiquetaInputRef" />
                  </form>
                  <button class="etiqueta-edit-btn etiqueta-edit-ok" @click.prevent.stop="guardarEtiquetaEdit(e)" title="Guardar">
                    <span class="material-icons" style="font-size:15px">check</span>
                  </button>
                  <button class="etiqueta-edit-btn etiqueta-edit-cancel" @click.prevent.stop="etiquetaEditandoId = null" title="Cancelar">
                    <span class="material-icons" style="font-size:15px">close</span>
                  </button>
                </div>
                <template v-else>
                  <span class="nav-item-label">{{ e.nombre }}</span>
                  <span v-if="e.tareas_pendientes && etiquetaHover !== e.id" class="nav-item-count">{{ e.tareas_pendientes }}</span>
                  <button v-if="etiquetaHover === e.id" class="btn-proyecto-menu" @click.prevent.stop="abrirMenuEtiqueta($event, e)">
                    <span class="material-icons" style="font-size:16px">more_vert</span>
                  </button>
                </template>
              </RouterLink>
            </div>
            <div v-if="!etiquetasGlobal.length" class="sidebar-empty-hint">Sin etiquetas</div>
          </template>
        </div>

        <!-- Completados -->
        <div v-if="proyectosCompletados.length" class="completados-wrap" style="padding:0 8px">
          <div class="completados-header" @click="mostrarCompletados = !mostrarCompletados">
            <span class="material-icons" style="font-size:14px">{{ mostrarCompletados ? 'expand_more' : 'chevron_right' }}</span>
            Completados ({{ proyectosCompletados.length }})
          </div>
          <template v-if="mostrarCompletados">
            <div
              v-for="p in proyectosCompletados"
              :key="p.id"
              class="nav-item nav-item-proyecto nav-item-completado"
            >
              <span class="nav-item-icon">
                <span class="proyecto-dot-sm" :style="{ background: p.color || '#607D8B', opacity: 0.5 }"></span>
              </span>
              <span class="nav-item-label nav-item-label-completado">{{ p.nombre }}</span>
            </div>
          </template>
        </div>
        </template>

        <!-- ═══ SEPARADOR ═══ -->
        <div class="sidebar-separator" />

        <!-- ═══ JORNADAS ═══ -->
        <div class="sidebar-section">
          <RouterLink to="/jornadas" class="nav-item" :class="{ active: ruta === '/jornadas' }">
            <span class="nav-item-icon material-icons">schedule</span>
            <span class="nav-item-label">Jornadas</span>
          </RouterLink>
        </div>

        <!-- Tablas -->
        <div class="sidebar-section">
          <div class="sidebar-section-label">Tablas</div>
          <RouterLink to="/proyectos-tabla" class="nav-item" :class="{ active: ruta === '/proyectos-tabla' }">
            <span class="nav-item-icon material-icons">folder_open</span>
            <span class="nav-item-label">Proyectos</span>
          </RouterLink>
          <RouterLink to="/dificultades" class="nav-item" :class="{ active: ruta === '/dificultades' }">
            <span class="nav-item-icon material-icons">warning_amber</span>
            <span class="nav-item-label">Dificultades</span>
          </RouterLink>
          <RouterLink to="/compromisos" class="nav-item" :class="{ active: ruta === '/compromisos' }">
            <span class="nav-item-icon material-icons">task_alt</span>
            <span class="nav-item-label">Compromisos</span>
          </RouterLink>
          <RouterLink to="/ideas" class="nav-item" :class="{ active: ruta === '/ideas' }">
            <span class="nav-item-icon material-icons">lightbulb_outline</span>
            <span class="nav-item-label">Ideas</span>
          </RouterLink>
        </div>
      </nav>

      <!-- Footer usuario -->
      <div class="sidebar-footer">
        <!-- Toggle tema -->
        <div class="nav-item" style="margin-bottom:4px" @click="toggleTema">
          <span class="nav-item-icon material-icons">{{ auth.tema === 'dark' ? 'light_mode' : 'dark_mode' }}</span>
          <span class="nav-item-label">{{ auth.tema === 'dark' ? 'Modo claro' : 'Modo oscuro' }}</span>
        </div>
        <!-- Usuario -->
        <div class="sidebar-user" @click="menuUsuario = !menuUsuario">
          <img :src="auth.usuario?.foto || ''" :alt="auth.usuario?.nombre" class="sidebar-user-foto" @error="e => e.target.style.display='none'" />
          <div class="sidebar-user-info">
            <div class="sidebar-user-name">{{ auth.usuario?.nombre }} <span style="font-size:9px;color:var(--text-tertiary);font-weight:400">{{ APP_VERSION }}</span></div>
            <div class="sidebar-user-empresa">{{ auth.empresa_activa?.siglas || auth.empresa_activa?.uid }}</div>
          </div>
        </div>
        <!-- Menú usuario -->
        <div v-if="menuUsuario" class="usuario-menu">
          <div class="usuario-menu-item" @click="cerrarSesion">
            <span class="material-icons" style="font-size:16px">logout</span>
            Cerrar sesión
          </div>
        </div>
      </div>
    </aside>

    <!-- MAIN -->
    <div class="main-content">
      <!-- Header jornada — arriba de todo -->
      <JornadaHeader />

      <!-- Topbar mobile -->
      <div class="topbar">
        <button class="btn-icon d-mobile-only" @click="drawerOpen = true">
          <span class="material-icons">menu</span>
        </button>
        <span class="topbar-title">{{ tituloRuta }}</span>
        <slot name="topbar-actions" />
      </div>

      <!-- Contenido de la página -->
      <div class="page-body" ref="pageBodyRef"
        @touchstart.passive="onPullStart"
        @touchmove.passive="onPullMove"
        @touchend="onPullEnd"
      >
        <!-- Indicador pull-to-refresh -->
        <div class="ptr-indicator" :class="{ visible: pullY > 0, refreshing: pullRefreshing }" :style="{ height: Math.min(pullY, 60) + 'px' }">
          <span v-if="pullRefreshing" class="material-icons ptr-spin">refresh</span>
          <span v-else class="material-icons" :style="{ transform: `rotate(${Math.min(pullY / 60, 1) * 180}deg)` }">arrow_downward</span>
        </div>
        <router-view :key="refreshKey" />
      </div>
    </div>

    <!-- Panel lateral crear/editar -->
    <ProyectoPanel
      v-if="panelVisible"
      :item="panelItem"
      :tipo="panelTipo"
      :categorias="categorias"
      :usuarios="usuarios"
      :etiquetas="etiquetasGlobal"
      @cerrar="panelVisible = false"
      @guardado="onItemGuardado"
      @eliminado="onItemEliminado"
    />

    <!-- Menú contextual ⋮ -->
    <Teleport to="body">
      <div v-if="menuProyecto.visible" class="proyecto-ctx-menu" :style="menuProyecto.style" @click.stop>
        <div class="ctx-item" @click="editarItem(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">edit</span>
          Editar
        </div>
        <div class="ctx-item" @click="verTabla(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">table_chart</span>
          Ver tabla
        </div>
        <div class="ctx-item ctx-item-warn" @click="archivarProyecto(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">archive</span>
          Archivar
        </div>
        <div class="ctx-item ctx-item-danger" @click="eliminarProyecto(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">delete_outline</span>
          Eliminar
        </div>
      </div>
      <!-- Menú contextual etiqueta -->
      <div v-if="menuEtiqueta.visible" class="ctx-backdrop" @click="menuEtiqueta.visible = false" />
      <div v-if="menuEtiqueta.visible" class="proyecto-ctx-menu" :style="menuEtiqueta.style" @click.stop>
        <div class="ctx-item" @click="editarEtiqueta">
          <span class="material-icons" style="font-size:15px">edit</span>
          Editar nombre
        </div>
        <div class="ctx-item ctx-item-danger" @click="eliminarEtiqueta">
          <span class="material-icons" style="font-size:15px">delete_outline</span>
          Eliminar
        </div>
      </div>
    </Teleport>

    <!-- DRAWER mobile -->
    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="drawerOpen" class="drawer-overlay" @click="drawerOpen = false">
          <aside class="drawer-panel" @click.stop>
            <div class="sidebar-logo" style="border-bottom:1px solid var(--border-subtle)">
              <div class="sidebar-logo-icon">G</div>
              <span class="sidebar-logo-name">OS Gestión</span>
              <button class="btn-icon" style="margin-left:auto" @click="drawerOpen = false">
                <span class="material-icons">close</span>
              </button>
            </div>
            <nav class="sidebar-nav" style="overflow-y:auto">
              <!-- ═══ MIS TAREAS (acordeón) ═══ -->
              <div class="nav-item nav-item-acordeon" :class="{ active: ruta === '/tareas' && !$route.query.proyecto_id }">
                <span class="nav-item-toggle material-icons" @click.stop="toggleAcordeon('bloque-mis')">{{ acordeonAbierto['bloque-mis'] ? 'expand_more' : 'chevron_right' }}</span>
                <RouterLink to="/tareas" class="nav-item-link-grow" @click="drawerOpen=false">
                  <span class="nav-item-icon material-icons">check_circle_outline</span>
                  <span class="nav-item-label">Mis Tareas</span>
                </RouterLink>
              </div>

              <template v-if="acordeonAbierto['bloque-mis']">
              <div v-for="sec in SECCIONES_SIDEBAR" :key="'dm-'+sec.tipo" class="sidebar-section sidebar-section-indented">
                <div class="sidebar-acordeon-header" @click="toggleAcordeon('mis-'+sec.tipo)">
                  <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['mis-'+sec.tipo] ? 'expand_more' : 'chevron_right' }}</span>
                  <span style="flex:1">{{ sec.label }}</span>
                  <span v-if="misItemsPorTipo(sec.tipo).length" class="acordeon-count">{{ misItemsPorTipo(sec.tipo).length }}</span>
                  <button class="btn-icon-tiny" @click.stop="drawerOpen=false; abrirPanel(sec.tipo)"><span class="material-icons" style="font-size:14px">add</span></button>
                </div>
                <template v-if="acordeonAbierto['mis-'+sec.tipo]">
                  <div v-for="p in misItemsPorTipo(sec.tipo)" :key="p.id" class="nav-item-proyecto-wrap">
                    <RouterLink :to="{ path: '/tareas', query: { proyecto_id: p.id } }" class="nav-item nav-item-proyecto" @click="drawerOpen=false">
                      <span class="nav-item-icon"><span class="proyecto-dot-sm" :style="{ background: p.color || '#607D8B' }"></span></span>
                      <span class="nav-item-label">{{ p.nombre }}</span>
                      <span v-if="p.tareas_pendientes" class="nav-item-count">{{ p.tareas_pendientes }}</span>
                      <button class="btn-proyecto-menu btn-mobile-always" @click.prevent.stop="abrirMenuProyecto($event, p)"><span class="material-icons" style="font-size:16px">more_vert</span></button>
                    </RouterLink>
                  </div>
                  <div v-if="!misItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty-hint">Sin {{ sec.label.toLowerCase() }}</div>
                </template>
              </div>

              <!-- Etiquetas (mis tareas — mobile) -->
              <div class="sidebar-section sidebar-section-indented">
                <div class="sidebar-acordeon-header" @click="toggleAcordeon('mis-etiquetas')">
                  <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['mis-etiquetas'] ? 'expand_more' : 'chevron_right' }}</span>
                  <span style="flex:1">Etiquetas</span>
                  <span v-if="misEtiquetasCount" class="acordeon-count">{{ misEtiquetasCount }}</span>
                </div>
                <template v-if="acordeonAbierto['mis-etiquetas']">
                  <div v-for="e in etiquetasGlobal" v-show="e.mis_tareas_total" :key="e.id" class="nav-item-proyecto-wrap">
                    <RouterLink :to="{ path: '/tareas', query: { etiqueta_id: e.id } }" class="nav-item nav-item-proyecto" @click="drawerOpen=false"
                      :class="{ active: ruta === '/tareas' && String($route.query.etiqueta_id) === String(e.id) }">
                      <span class="nav-item-icon"><span class="proyecto-dot-sm" :style="{ background: e.color || '#888' }"></span></span>
                      <div v-if="etiquetaEditandoId === e.id" class="etiqueta-edit-row" @click.prevent.stop>
                        <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                        <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                          <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" />
                        </form>
                        <button class="etiqueta-edit-btn etiqueta-edit-ok" @click.prevent.stop="guardarEtiquetaEdit(e)" title="Guardar">
                          <span class="material-icons" style="font-size:15px">check</span>
                        </button>
                        <button class="etiqueta-edit-btn etiqueta-edit-cancel" @click.prevent.stop="etiquetaEditandoId = null" title="Cancelar">
                          <span class="material-icons" style="font-size:15px">close</span>
                        </button>
                      </div>
                      <template v-else>
                        <span class="nav-item-label">{{ e.nombre }}</span>
                        <span v-if="e.mis_tareas_pendientes" class="nav-item-count">{{ e.mis_tareas_pendientes }}</span>
                        <button class="btn-proyecto-menu btn-mobile-always" @click.prevent.stop="abrirMenuEtiqueta($event, e)"><span class="material-icons" style="font-size:16px">more_vert</span></button>
                      </template>
                    </RouterLink>
                  </div>
                  <div v-if="!etiquetasGlobal.length" class="sidebar-empty-hint">Sin etiquetas</div>
                </template>
              </div>
              </template>

              <div class="sidebar-separator" />

              <!-- ═══ EQUIPO (acordeón) ═══ -->
              <div class="nav-item nav-item-acordeon" :class="{ active: ruta === '/equipo' }">
                <span class="nav-item-toggle material-icons" @click.stop="toggleAcordeon('bloque-eq')">{{ acordeonAbierto['bloque-eq'] ? 'expand_more' : 'chevron_right' }}</span>
                <RouterLink to="/equipo" class="nav-item-link-grow" @click="drawerOpen=false">
                  <span class="nav-item-icon material-icons">group</span>
                  <span class="nav-item-label">Equipo</span>
                </RouterLink>
              </div>

              <template v-if="acordeonAbierto['bloque-eq']">
              <div v-for="sec in SECCIONES_SIDEBAR" :key="'de-'+sec.tipo" class="sidebar-section sidebar-section-indented">
                <div class="sidebar-acordeon-header" @click="toggleAcordeon('eq-'+sec.tipo)">
                  <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['eq-'+sec.tipo] ? 'expand_more' : 'chevron_right' }}</span>
                  <span style="flex:1">{{ sec.label }}</span>
                  <span v-if="equipoItemsPorTipo(sec.tipo).length" class="acordeon-count">{{ equipoItemsPorTipo(sec.tipo).length }}</span>
                  <button class="btn-icon-tiny" @click.stop="drawerOpen=false; abrirPanel(sec.tipo)"><span class="material-icons" style="font-size:14px">add</span></button>
                </div>
                <template v-if="acordeonAbierto['eq-'+sec.tipo]">
                  <div v-for="p in equipoItemsPorTipo(sec.tipo)" :key="p.id" class="nav-item-proyecto-wrap">
                    <RouterLink :to="{ path: '/equipo', query: { proyecto_id: p.id } }" class="nav-item nav-item-proyecto" @click="drawerOpen=false">
                      <span class="nav-item-icon"><span class="proyecto-dot-sm" :style="{ background: p.color || '#607D8B' }"></span></span>
                      <span class="nav-item-label">{{ p.nombre }}</span>
                      <span v-if="p.tareas_pendientes" class="nav-item-count">{{ p.tareas_pendientes }}</span>
                      <button class="btn-proyecto-menu btn-mobile-always" @click.prevent.stop="abrirMenuProyecto($event, p)"><span class="material-icons" style="font-size:16px">more_vert</span></button>
                    </RouterLink>
                  </div>
                  <div v-if="!equipoItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty-hint">Sin {{ sec.label.toLowerCase() }}</div>
                </template>
              </div>

              <!-- Etiquetas (equipo — mobile) -->
              <div class="sidebar-section sidebar-section-indented">
                <div class="sidebar-acordeon-header" @click="toggleAcordeon('eq-etiquetas')">
                  <span class="material-icons" style="font-size:14px">{{ acordeonAbierto['eq-etiquetas'] ? 'expand_more' : 'chevron_right' }}</span>
                  <span style="flex:1">Etiquetas</span>
                  <span v-if="eqEtiquetasCount" class="acordeon-count">{{ eqEtiquetasCount }}</span>
                </div>
                <template v-if="acordeonAbierto['eq-etiquetas']">
                  <div v-for="e in etiquetasGlobal" v-show="e.tareas_total" :key="e.id" class="nav-item-proyecto-wrap">
                    <RouterLink :to="{ path: '/equipo', query: { etiqueta_id: e.id } }" class="nav-item nav-item-proyecto" @click="drawerOpen=false"
                      :class="{ active: ruta === '/equipo' && String($route.query.etiqueta_id) === String(e.id) }">
                      <span class="nav-item-icon"><span class="proyecto-dot-sm" :style="{ background: e.color || '#888' }"></span></span>
                      <div v-if="etiquetaEditandoId === e.id" class="etiqueta-edit-row" @click.prevent.stop>
                        <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                        <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                          <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" />
                        </form>
                        <button class="etiqueta-edit-btn etiqueta-edit-ok" @click.prevent.stop="guardarEtiquetaEdit(e)" title="Guardar">
                          <span class="material-icons" style="font-size:15px">check</span>
                        </button>
                        <button class="etiqueta-edit-btn etiqueta-edit-cancel" @click.prevent.stop="etiquetaEditandoId = null" title="Cancelar">
                          <span class="material-icons" style="font-size:15px">close</span>
                        </button>
                      </div>
                      <template v-else>
                        <span class="nav-item-label">{{ e.nombre }}</span>
                        <span v-if="e.tareas_pendientes" class="nav-item-count">{{ e.tareas_pendientes }}</span>
                        <button class="btn-proyecto-menu btn-mobile-always" @click.prevent.stop="abrirMenuEtiqueta($event, e)"><span class="material-icons" style="font-size:16px">more_vert</span></button>
                      </template>
                    </RouterLink>
                  </div>
                  <div v-if="!etiquetasGlobal.length" class="sidebar-empty-hint">Sin etiquetas</div>
                </template>
              </div>
              </template>

              <div class="sidebar-separator" />

              <!-- ═══ JORNADAS ═══ -->
              <RouterLink to="/jornadas" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">schedule</span><span class="nav-item-label">Jornadas</span></RouterLink>

              <!-- Links tablas -->
              <div class="sidebar-section">
                <div class="sidebar-section-label">Tablas</div>
                <RouterLink to="/proyectos-tabla" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">folder_open</span><span class="nav-item-label">Proyectos</span></RouterLink>
                <RouterLink to="/dificultades" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">warning_amber</span><span class="nav-item-label">Dificultades</span></RouterLink>
                <RouterLink to="/compromisos" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">task_alt</span><span class="nav-item-label">Compromisos</span></RouterLink>
                <RouterLink to="/ideas" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">lightbulb_outline</span><span class="nav-item-label">Ideas</span></RouterLink>
              </div>

              <!-- Footer usuario (móvil) -->
              <div style="margin-top:auto; padding:12px 8px; border-top:1px solid var(--border-subtle)">
                <div class="nav-item" style="margin-bottom:4px" @click="toggleTema; drawerOpen=false">
                  <span class="nav-item-icon material-icons">{{ auth.tema === 'dark' ? 'light_mode' : 'dark_mode' }}</span>
                  <span class="nav-item-label">{{ auth.tema === 'dark' ? 'Modo claro' : 'Modo oscuro' }}</span>
                </div>
                <div class="nav-item" @click="cerrarSesion">
                  <span class="nav-item-icon material-icons">logout</span>
                  <span class="nav-item-label">Cerrar sesión</span>
                  <span style="font-size:9px;color:var(--text-tertiary);margin-left:auto">{{ APP_VERSION }}</span>
                </div>
              </div>
            </nav>
          </aside>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, reactive, computed, provide, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/authStore'
import { api } from 'src/services/api'
import { hoyLocal } from 'src/services/fecha'
import ProyectoPanel from 'src/components/ProyectoPanel.vue'
import JornadaHeader from 'src/components/JornadaHeader.vue'

const APP_VERSION = 'v2.3.3'

// ─── Pull-to-refresh ───
const pageBodyRef    = ref(null)
const refreshKey     = ref(0)
const pullY          = ref(0)
const pullRefreshing = ref(false)
let pullStartY       = 0
let pulling          = false

function onPullStart(e) {
  if (e.target.closest('.drag-handle') || pageBodyRef.value?.scrollTop > 0) return
  pullStartY = e.touches[0].clientY
  pulling = true
}
function onPullMove(e) {
  if (!pulling || pageBodyRef.value?.scrollTop > 0) { pulling = false; pullY.value = 0; return }
  const diff = e.touches[0].clientY - pullStartY
  if (diff > 0) pullY.value = diff * 0.21
  else { pulling = false; pullY.value = 0 }
}
function onPullEnd() {
  if (!pulling) return
  pulling = false
  if (pullY.value >= 78) {
    pullRefreshing.value = true
    pullY.value = 50
    setTimeout(() => {
      refreshKey.value++
      cargarProyectos()
      pullRefreshing.value = false
      pullY.value = 0
    }, 400)
  } else {
    pullY.value = 0
  }
}
const auth             = useAuthStore()
const router           = useRouter()
const route            = useRoute()
const sidebarCollapsed = ref(false)
const drawerOpen       = ref(false)
const menuUsuario      = ref(false)

// ── Secciones del sidebar ──
const SECCIONES_SIDEBAR = [
  { tipo: 'proyecto',    label: 'Proyectos',    singular: 'proyecto',    icon: 'folder_open' },
  { tipo: 'dificultad',  label: 'Dificultades', singular: 'dificultad',  icon: 'warning_amber' },
  { tipo: 'compromiso',  label: 'Compromisos',  singular: 'compromiso',  icon: 'task_alt' },
  { tipo: 'idea',        label: 'Ideas',        singular: 'idea',        icon: 'lightbulb_outline' },
]
const ESTADOS_COMPLETADO = { proyecto: 'Completado', dificultad: 'Resuelta', compromiso: 'Cumplido', idea: 'Aprobada' }
const RUTAS_TABLA = { proyecto: '/proyectos-tabla', dificultad: '/dificultades', compromiso: '/compromisos', idea: '/ideas' }

// Items en sidebar (todos los tipos activos juntos)
const todosItems          = ref([])
const proyectosCompletados = ref([])
const mostrarCompletados  = ref(false)
const cargandoProyectos   = ref(false)
const proyectoHover       = ref(null)
const etiquetaHover       = ref(null)
const menuEtiqueta        = ref({ visible: false, etiqueta: null, style: {} })

// Panel lateral
const panelVisible = ref(false)
const panelItem    = ref(null)
const panelTipo    = ref('proyecto')

// Datos compartidos para el panel
const categorias     = ref([])
const usuarios       = ref([])
const etiquetasGlobal = ref([])

// Menú contextual ⋮
const menuProyecto = ref({ visible: false, proyecto: null, style: {} })

function itemsPorTipo(tipo) {
  return todosItems.value.filter(p => p.tipo === tipo)
}

const miEmail = computed(() => auth.usuario?.email || '')

function misItemsPorTipo(tipo) {
  return todosItems.value.filter(p => p.tipo === tipo && (p.responsables || []).includes(miEmail.value))
}
function equipoItemsPorTipo(tipo) {
  return todosItems.value.filter(p => p.tipo === tipo)
}
// Acordeones individuales: 'mis-proyecto', 'mis-dificultad', 'eq-proyecto', etc.
const acordeonAbierto = reactive({})
function toggleAcordeon(key) { acordeonAbierto[key] = !acordeonAbierto[key] }

// Alias para compatibilidad template (completados no filtran por tipo)
const proyectos = todosItems // renombrado internamente

async function cargarProyectos() {
  cargandoProyectos.value = true
  try {
    const [activos, resueltos] = await Promise.all([
      api('/api/gestion/proyectos'),
      Promise.resolve({ proyectos: [] }) // completados se cargan aparte si hay
    ])
    const all = activos.proyectos || []
    // Separar activos de completados/resueltos/cumplidos/aprobados
    const estadosCompletados = Object.values(ESTADOS_COMPLETADO)
    todosItems.value          = all.filter(p => !estadosCompletados.includes(p.estado) && p.estado !== 'Archivado' && p.estado !== 'Cerrada' && p.estado !== 'Cancelado' && p.estado !== 'Descartada')
    proyectosCompletados.value = all.filter(p => estadosCompletados.includes(p.estado))
  } catch {} finally { cargandoProyectos.value = false }
}

async function cargarDatosPanel() {
  try {
    const [cats, usrs, etqs] = await Promise.all([
      api('/api/gestion/categorias'),
      api('/api/gestion/usuarios'),
      api('/api/gestion/etiquetas'),
    ])
    categorias.value     = cats.categorias || cats || []
    usuarios.value       = usrs.usuarios   || usrs || []
    etiquetasGlobal.value = etqs.etiquetas  || etqs || []
  } catch {}
}

function abrirPanel(tipo, item = null) {
  panelTipo.value = tipo
  panelItem.value = item
  panelVisible.value = true
  if (!categorias.value.length) cargarDatosPanel()
}

provide('abrirPanelItem', abrirPanel)
provide('recargarSidebar', cargarProyectos)

function onItemGuardado(p) {
  if (p._accion === 'creado') {
    todosItems.value.push(p)
    panelVisible.value = false
    // Abrir el acordeón correspondiente para que se vea el item nuevo
    const bloque = (p.responsables || []).includes(miEmail.value) ? 'bloque-mis' : 'bloque-eq'
    acordeonAbierto[bloque] = true
    acordeonAbierto[(bloque === 'bloque-mis' ? 'mis-' : 'eq-') + (p.tipo || 'proyecto')] = true
  } else {
    const idx = todosItems.value.findIndex(x => x.id === p.id)
    if (idx !== -1) todosItems.value[idx] = { ...todosItems.value[idx], ...p }
  }
}

function onItemEliminado(p) {
  todosItems.value = todosItems.value.filter(x => x.id !== p.id)
  if (String(route.query.proyecto_id) === String(p.id)) router.push('/tareas')
}

function abrirMenuProyecto(event, proyecto) {
  const rect = event.currentTarget.getBoundingClientRect()
  menuProyecto.value = {
    visible: true,
    proyecto,
    style: {
      position: 'fixed',
      top: `${rect.bottom + 4}px`,
      left: `${rect.left}px`,
      zIndex: 9999
    }
  }
  setTimeout(() => document.addEventListener('click', cerrarMenuProyecto, { once: true }), 0)
}

function cerrarMenuProyecto() {
  menuProyecto.value.visible = false
}

function editarItem(p) {
  cerrarMenuProyecto()
  abrirPanel(p.tipo || 'proyecto', p)
}

function verTabla(p) {
  cerrarMenuProyecto()
  const ruta = RUTAS_TABLA[p.tipo || 'proyecto'] || '/proyectos-tabla'
  router.push(ruta)
}

async function completarItem(p) {
  cerrarMenuProyecto()
  const hoy = hoyLocal()
  const estadoFinal = ESTADOS_COMPLETADO[p.tipo || 'proyecto']
  try {
    await api(`/api/gestion/proyectos/${p.id}`, {
      method: 'PUT',
      body: JSON.stringify({ estado: estadoFinal, fecha_finalizacion_real: hoy })
    })
    todosItems.value = todosItems.value.filter(x => x.id !== p.id)
    proyectosCompletados.value.unshift({ ...p, estado: estadoFinal, fecha_finalizacion_real: hoy })
    if (String(route.query.proyecto_id) === String(p.id)) router.replace('/tareas')
  } catch (e) { console.error(e) }
}

async function archivarProyecto(p) {
  cerrarMenuProyecto()
  try {
    await api(`/api/gestion/proyectos/${p.id}`, {
      method: 'PUT',
      body: JSON.stringify({ estado: 'Archivado' })
    })
    todosItems.value = todosItems.value.filter(x => x.id !== p.id)
    if (String(route.query.proyecto_id) === String(p.id)) router.replace('/tareas')
  } catch (e) { console.error(e) }
}

async function eliminarProyecto(p) {
  cerrarMenuProyecto()
  if (!confirm(`¿Eliminar "${p.nombre}"? Las tareas quedarán sin asignar.`)) return
  try {
    await api(`/api/gestion/proyectos/${p.id}`, { method: 'DELETE' })
    todosItems.value = todosItems.value.filter(x => x.id !== p.id)
    if (String(route.query.proyecto_id) === String(p.id)) router.replace('/tareas')
  } catch (e) { console.error(e) }
}

// ── Menú contextual etiquetas ──
function abrirMenuEtiqueta(event, etiqueta) {
  const rect = event.currentTarget.getBoundingClientRect()
  menuEtiqueta.value = {
    visible: true,
    etiqueta,
    style: { position: 'fixed', top: `${rect.bottom + 4}px`, left: `${rect.left}px`, zIndex: 9999 }
  }
}

const etiquetaEditandoId = ref(null)
const etiquetaEditColor  = ref(null)

function editarEtiqueta() {
  const e = menuEtiqueta.value.etiqueta
  menuEtiqueta.value.visible = false
  etiquetaEditandoId.value = e.id
  etiquetaEditColor.value = null
  nextTick(() => {
    const input = document.querySelector('.etiqueta-edit-input')
    if (input) { input.focus(); input.select() }
  })
}

async function guardarEtiquetaEdit(e) {
  const input = document.querySelector('.etiqueta-edit-input')
  const nombre = (input?.value || '').trim()
  const color = etiquetaEditColor.value
  etiquetaEditandoId.value = null
  const body = {}
  if (nombre && nombre !== e.nombre) body.nombre = nombre
  if (color && color !== e.color) body.color = color
  if (!Object.keys(body).length) return
  try {
    const data = await api(`/api/gestion/etiquetas/${e.id}`, { method: 'PUT', body: JSON.stringify(body) })
    const idx = etiquetasGlobal.value.findIndex(x => x.id === e.id)
    if (idx !== -1) etiquetasGlobal.value[idx] = { ...etiquetasGlobal.value[idx], ...body }
  } catch (err) { console.error(err) }
}

async function eliminarEtiqueta() {
  const e = menuEtiqueta.value.etiqueta
  menuEtiqueta.value.visible = false
  if (!confirm(`¿Eliminar etiqueta "${e.nombre}"? Se quitará de todas las tareas.`)) return
  try {
    await api(`/api/gestion/etiquetas/${e.id}`, { method: 'DELETE' })
    etiquetasGlobal.value = etiquetasGlobal.value.filter(x => x.id !== e.id)
    if (String(route.query.etiqueta_id) === String(e.id)) router.replace(route.path)
  } catch (err) { console.error(err) }
}

const ruta = computed(() => route.path)

const TITULOS = {
  '/tareas':          'Mis Tareas',
  '/equipo':          'Equipo',
  '/jornadas':        'Jornadas',
}
const tituloRuta = computed(() => {
  for (const [path, titulo] of Object.entries(TITULOS)) {
    if (ruta.value.startsWith(path)) return titulo
  }
  return ''
})

function toggleTema() {
  auth.cambiarTema(auth.tema === 'dark' ? 'light' : 'dark')
}

function cerrarSesion() {
  auth.cerrarSesion()
  router.push('/login')
}

onMounted(() => {
  if (auth.token) {
    cargarProyectos()
    cargarEtiquetas()
  }
})

async function cargarEtiquetas() {
  try {
    const data = await api('/api/gestion/etiquetas')
    etiquetasGlobal.value = data.etiquetas || []
  } catch {}
}
const misEtiquetasCount = computed(() => etiquetasGlobal.value.filter(e => e.mis_tareas_total).length)
const eqEtiquetasCount  = computed(() => etiquetasGlobal.value.filter(e => e.tareas_total).length)
</script>

<style scoped>
.d-mobile-only { display: none; }
@media (max-width: 768px) {
  .d-mobile-only { display: flex; }
  .sidebar { display: none; }
}

/* Proyectos sidebar */
.btn-icon-tiny {
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 4px;
  background: transparent; border: none; cursor: pointer;
  color: var(--text-tertiary); transition: background 80ms, color 80ms;
}
.btn-icon-tiny:hover { background: var(--bg-row-hover); color: var(--text-primary); }

.nav-item-proyecto { position: relative; }
.nav-item-count {
  margin-left: auto; font-size: 11px;
  color: var(--text-tertiary);
  min-width: 16px; text-align: right;
}
.proyecto-dot-sm {
  width: 6px; height: 6px; border-radius: 50%; display: inline-block;
}
.sidebar-empty-hint {
  padding: 4px 16px 6px;
  font-size: 11px; color: var(--text-tertiary); font-style: italic;
}

/* Proyecto nav item con hover */
.nav-item-proyecto-wrap { position: relative; }

/* Botón ⋮ dentro del nav-item */
.btn-proyecto-check {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: var(--radius-sm);
  background: transparent; border: none; cursor: pointer;
  color: var(--text-tertiary); margin-left: auto; flex-shrink: 0;
  transition: background 80ms, color 80ms;
}
.btn-proyecto-check:hover { color: var(--accent); background: var(--accent-muted); }

.btn-proyecto-menu {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: var(--radius-sm);
  background: transparent; border: none; cursor: pointer;
  color: var(--text-tertiary); flex-shrink: 0;
  transition: background 80ms, color 80ms;
}
.btn-proyecto-menu:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.btn-mobile-always { opacity: 0.5; }
.btn-mobile-always:active { opacity: 1; background: var(--bg-row-hover); }

/* Separador entre bloques */
.sidebar-separator {
  height: 1px;
  background: var(--border-subtle);
  margin: 8px 12px;
}

/* Acordeón de sección equipo */
.sidebar-acordeon-header {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 12px; font-size: 11px;
  color: var(--text-tertiary); cursor: pointer;
  border-radius: var(--radius-sm); transition: color 80ms;
  user-select: none; margin: 2px 0;
}
.sidebar-acordeon-header:hover { color: var(--text-secondary); }

/* Acordeón principal (Mis Tareas / Equipo) */
.nav-item-acordeon {
  display: flex; align-items: center; gap: 0;
  padding: 0 4px 0 4px;
}
.nav-item-toggle {
  font-size: 16px; cursor: pointer; flex-shrink: 0;
  color: var(--text-tertiary); padding: 4px;
  border-radius: var(--radius-sm);
  transition: color 80ms, background 80ms;
}
.nav-item-toggle:hover { color: var(--text-primary); background: var(--bg-row-hover); }
.nav-item-link-grow {
  display: flex; align-items: center; gap: 10px;
  flex: 1; min-width: 0;
  text-decoration: none; color: inherit;
}
.acordeon-count {
  font-size: 10px; color: var(--text-tertiary);
  min-width: 14px; text-align: right; margin-right: 4px;
}

/* Acordeón completados */
.completados-wrap { margin-top: 4px; }
.completados-header {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px; font-size: 11px;
  color: var(--text-tertiary); cursor: pointer;
  border-radius: var(--radius-sm); transition: color 80ms;
  user-select: none;
}
.completados-header:hover { color: var(--text-secondary); }
.nav-item-completado { opacity: 0.55; pointer-events: none; }
.nav-item-label-completado { text-decoration: line-through; }

/* Menú contextual ⋮ */
.proyecto-ctx-menu {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 150px;
  overflow: hidden;
}
.ctx-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 13px; color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.ctx-item:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.ctx-item-success:hover { color: var(--accent); }
.ctx-item-warn:hover { color: var(--color-warning); }
.ctx-item-danger:hover { color: var(--color-error); }
.ctx-backdrop { position: fixed; inset: 0; z-index: 9998; }
.etiqueta-edit-row {
  display: flex; align-items: center; gap: 4px; flex: 1; min-width: 0;
}
.etiqueta-edit-input {
  width: 100%; background: var(--bg-input); border: 1px solid var(--accent);
  border-radius: var(--radius-sm); color: var(--text-primary);
  font-size: 12px; padding: 2px 6px; height: 22px;
  font-family: var(--font-sans); outline: none;
}
.etiqueta-edit-color {
  width: 20px; height: 20px; padding: 0; border: 1px solid var(--border-default);
  border-radius: 50%; cursor: pointer; background: none; flex-shrink: 0;
  -webkit-appearance: none; appearance: none;
}
.etiqueta-edit-color::-webkit-color-swatch-wrapper { padding: 0; }
.etiqueta-edit-color::-webkit-color-swatch { border: none; border-radius: 50%; }
.etiqueta-edit-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border: none; border-radius: var(--radius-sm);
  background: transparent; cursor: pointer; flex-shrink: 0; padding: 0;
}
.etiqueta-edit-ok { color: var(--accent); }
.etiqueta-edit-ok:hover { background: var(--accent-muted); }
.etiqueta-edit-cancel { color: var(--text-tertiary); }
.etiqueta-edit-cancel:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Menú usuario */
.usuario-menu {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  margin: 4px 0;
  overflow: hidden;
}
.usuario-menu-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms;
}
.usuario-menu-item:hover { background: var(--bg-row-hover); color: var(--color-error); }
</style>
