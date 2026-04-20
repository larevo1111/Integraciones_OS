<template>
  <q-layout view="lHh LpR lFf">

    <!-- ═══ SIDEBAR / DRAWER ═══ -->
    <q-drawer
      v-model="drawerOpen"
      side="left"
      :mini="isMini"
      :width="240"
      :mini-width="56"
      :breakpoint="768"
      show-if-above
      bordered
      class="sidebar-drawer"
      :class="{ 'mini-mode': miniState && !isMobile }"
    >
      <!-- Logo header -->
      <div class="sidebar-logo">
        <img src="/logo-os.png" class="sidebar-logo-img" alt="OS" />
        <span v-if="!isMini" class="sidebar-logo-name">OS Gesti&oacute;n</span>
        <q-btn
          flat dense round
          :icon="miniState ? 'chevron_right' : 'chevron_left'"
          size="xs"
          class="sidebar-toggle-btn gt-sm"
          :class="{ 'q-ml-auto': !isMini }"
          @click="miniState = !miniState"
        />
        <q-btn
          flat dense round icon="close" size="sm"
          class="q-ml-auto lt-md"
          @click="drawerOpen = false"
        />
      </div>

      <!-- Nav content -->
      <div class="sidebar-scroll">
        <q-list dense>

          <!-- ═══ MIS TAREAS (acordeón) ═══ -->
          <template v-if="!isMini">
            <q-expansion-item
              v-model="acordeonAbierto['bloque-mis']"
              icon="check_circle_outline"
              label="Mis Tareas"
              header-class="sidebar-item"
              :header-style="ruta === '/tareas' && !$route.query.proyecto_id ? 'background: var(--bg-row-selected)' : ''"
              dense
            >
              <template #header>
                <q-item-section avatar class="sidebar-item-icon">
                  <q-icon name="check_circle_outline" />
                </q-item-section>
                <q-item-section class="sidebar-item-label cursor-pointer" @click.stop="$router.push('/tareas'); drawerOpen = false">
                  Mis Tareas
                </q-item-section>
              </template>

              <!-- Subitems Mis Tareas -->
              <div v-for="sec in SECCIONES_SIDEBAR" :key="'mis-'+sec.tipo" class="sidebar-sub-section">
                <div class="sidebar-sub-header" @click="toggleAcordeon('mis-'+sec.tipo)">
                  <q-icon :name="acordeonAbierto['mis-'+sec.tipo] ? 'expand_more' : 'chevron_right'" size="14px" />
                  <span class="q-ml-xs" style="flex:1">{{ sec.label }}</span>
                  <span v-if="misItemsPorTipo(sec.tipo).length" class="sidebar-count">{{ misItemsPorTipo(sec.tipo).length }}</span>
                  <q-btn flat dense round size="xs" icon="add" class="sidebar-add-btn" @click.stop="abrirPanel(sec.tipo)" />
                </div>
                <template v-if="acordeonAbierto['mis-'+sec.tipo]">
                  <q-item
                    v-for="p in misItemsPorTipo(sec.tipo)" :key="p.id"
                    clickable dense
                    class="sidebar-project-item"
                    :class="{ active: ruta === '/tareas' && String($route.query.proyecto_id) === String(p.id) }"
                    :to="{ path: '/tareas', query: { proyecto_id: p.id } }"
                    @click="drawerOpen = false"
                    @mouseenter="proyectoHover = p.id"
                    @mouseleave="proyectoHover = null"
                  >
                    <q-item-section avatar class="sidebar-item-icon">
                      <span class="proyecto-dot" :style="{ background: p.color || '#607D8B' }" />
                    </q-item-section>
                    <q-item-section class="sidebar-item-label">{{ p.nombre }}</q-item-section>
                    <q-item-section side v-if="p.tareas_pendientes && proyectoHover !== p.id">
                      <span class="sidebar-count">{{ p.tareas_pendientes }}</span>
                    </q-item-section>
                    <q-item-section side v-if="proyectoHover === p.id" class="sidebar-hover-actions">
                      <div class="row no-wrap items-center">
                        <q-btn flat dense round size="xs" icon="check_circle_outline" @click.prevent.stop="completarItem(p)" />
                        <q-btn flat dense round size="xs" icon="more_vert" @click.prevent.stop="abrirMenuProyecto($event, p)" />
                      </div>
                    </q-item-section>
                  </q-item>
                  <div v-if="!misItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty">
                    Sin {{ sec.label.toLowerCase() }}
                  </div>
                </template>
              </div>

              <!-- Etiquetas (mis tareas) -->
              <div class="sidebar-sub-section">
                <div class="sidebar-sub-header" @click="toggleAcordeon('mis-etiquetas')">
                  <q-icon :name="acordeonAbierto['mis-etiquetas'] ? 'expand_more' : 'chevron_right'" size="14px" />
                  <span class="q-ml-xs" style="flex:1">Etiquetas</span>
                  <span v-if="misEtiquetasCount" class="sidebar-count">{{ misEtiquetasCount }}</span>
                </div>
                <template v-if="acordeonAbierto['mis-etiquetas']">
                  <q-item
                    v-for="e in etiquetasGlobal" :key="e.id"
                    v-show="e.mis_tareas_total"
                    clickable dense
                    class="sidebar-project-item"
                    :class="{ active: ruta === '/tareas' && String($route.query.etiqueta_id) === String(e.id) }"
                    :to="{ path: '/tareas', query: { etiqueta_id: e.id } }"
                    @click="drawerOpen = false"
                    @mouseenter="etiquetaHover = e.id"
                    @mouseleave="etiquetaHover = null"
                  >
                    <q-item-section avatar class="sidebar-item-icon">
                      <span class="proyecto-dot" :style="{ background: e.color || '#888' }" />
                    </q-item-section>
                    <!-- Edición inline -->
                    <q-item-section v-if="etiquetaEditandoId === e.id" class="sidebar-item-label" @click.prevent.stop>
                      <div class="etiqueta-edit-row">
                        <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                        <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                          <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" ref="etiquetaInputRef" />
                        </form>
                        <q-btn flat dense round size="xs" icon="check" color="positive" @click.prevent.stop="guardarEtiquetaEdit(e)" />
                        <q-btn flat dense round size="xs" icon="close" @click.prevent.stop="etiquetaEditandoId = null" />
                      </div>
                    </q-item-section>
                    <template v-else>
                      <q-item-section class="sidebar-item-label">{{ e.nombre }}</q-item-section>
                      <q-item-section side v-if="e.mis_tareas_pendientes && etiquetaHover !== e.id">
                        <span class="sidebar-count">{{ e.mis_tareas_pendientes }}</span>
                      </q-item-section>
                      <q-item-section side v-if="etiquetaHover === e.id">
                        <q-btn flat dense round size="xs" icon="more_vert" @click.prevent.stop="abrirMenuEtiqueta($event, e)" />
                      </q-item-section>
                    </template>
                  </q-item>
                  <div v-if="!etiquetasGlobal.length" class="sidebar-empty">Sin etiquetas</div>
                </template>
              </div>
            </q-expansion-item>
          </template>

          <!-- Mini mode: Mis Tareas (click navega, hover abre popover) -->
          <template v-if="isMini">
            <q-item
              clickable dense
              class="sidebar-item sidebar-item-mini"
              :class="{ active: ruta === '/tareas' && !$route.query.proyecto_id }"
              to="/tareas"
              @mouseenter="showHover('mis')"
              @mouseleave="hideHover('mis')"
            >
              <q-item-section avatar class="sidebar-item-icon"><q-icon name="check_circle_outline" /></q-item-section>
              <q-menu
                v-model="hoverMenus.mis"
                no-parent-event
                anchor="center right" self="center left"
                :offset="[8, 0]"
                class="sidebar-popover"
                @mouseenter="showHover('mis')"
                @mouseleave="hideHover('mis')"
              >
                <q-list dense style="min-width: 220px">
                  <q-item-label header class="sidebar-popover-title">Mis Tareas</q-item-label>
                  <template v-for="sec in SECCIONES_SIDEBAR" :key="'mini-mis-'+sec.tipo">
                    <q-item
                      v-for="p in misItemsPorTipo(sec.tipo)" :key="p.id"
                      clickable dense v-close-popup
                      :to="{ path: '/tareas', query: { proyecto_id: p.id } }"
                    >
                      <q-item-section avatar style="min-width:20px"><span class="proyecto-dot" :style="{ background: p.color || '#607D8B' }" /></q-item-section>
                      <q-item-section>{{ p.nombre }}</q-item-section>
                      <q-item-section side v-if="p.tareas_pendientes"><span class="sidebar-count">{{ p.tareas_pendientes }}</span></q-item-section>
                    </q-item>
                  </template>
                  <q-separator v-if="etiquetasGlobal.filter(e => e.mis_tareas_total).length" />
                  <q-item
                    v-for="e in etiquetasGlobal.filter(e => e.mis_tareas_total)" :key="e.id"
                    clickable dense v-close-popup
                    :to="{ path: '/tareas', query: { etiqueta_id: e.id } }"
                  >
                    <q-item-section avatar style="min-width:20px"><span class="proyecto-dot" :style="{ background: e.color || '#888' }" /></q-item-section>
                    <q-item-section>{{ e.nombre }}</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </q-item>
          </template>

          <!-- ═══ SEPARADOR ═══ -->
          <q-separator class="q-my-xs q-mx-md" />

          <!-- ═══ EQUIPO (acordeón) ═══ -->
          <template v-if="!isMini">
            <q-expansion-item
              v-model="acordeonAbierto['bloque-eq']"
              icon="group"
              label="Equipo"
              header-class="sidebar-item"
              :header-style="ruta === '/equipo' ? 'background: var(--bg-row-selected)' : ''"
              dense
            >
              <template #header>
                <q-item-section avatar class="sidebar-item-icon">
                  <q-icon name="group" />
                </q-item-section>
                <q-item-section class="sidebar-item-label cursor-pointer" @click.stop="$router.push('/equipo'); drawerOpen = false">
                  Equipo
                </q-item-section>
              </template>

              <!-- Subitems Equipo -->
              <div v-for="sec in SECCIONES_SIDEBAR" :key="'eq-'+sec.tipo" class="sidebar-sub-section">
                <div class="sidebar-sub-header" @click="toggleAcordeon('eq-'+sec.tipo)">
                  <q-icon :name="acordeonAbierto['eq-'+sec.tipo] ? 'expand_more' : 'chevron_right'" size="14px" />
                  <span class="q-ml-xs" style="flex:1">{{ sec.label }}</span>
                  <span v-if="equipoItemsPorTipo(sec.tipo).length" class="sidebar-count">{{ equipoItemsPorTipo(sec.tipo).length }}</span>
                  <q-btn flat dense round size="xs" icon="add" class="sidebar-add-btn" @click.stop="abrirPanel(sec.tipo)" />
                </div>
                <template v-if="acordeonAbierto['eq-'+sec.tipo]">
                  <q-item
                    v-for="p in equipoItemsPorTipo(sec.tipo)" :key="p.id"
                    clickable dense
                    class="sidebar-project-item"
                    :class="{ active: ruta === '/equipo' && String($route.query.proyecto_id) === String(p.id) }"
                    :to="{ path: '/equipo', query: { proyecto_id: p.id } }"
                    @click="drawerOpen = false"
                    @mouseenter="proyectoHover = p.id"
                    @mouseleave="proyectoHover = null"
                  >
                    <q-item-section avatar class="sidebar-item-icon">
                      <span class="proyecto-dot" :style="{ background: p.color || '#607D8B' }" />
                    </q-item-section>
                    <q-item-section class="sidebar-item-label">{{ p.nombre }}</q-item-section>
                    <q-item-section side v-if="p.tareas_pendientes && proyectoHover !== p.id">
                      <span class="sidebar-count">{{ p.tareas_pendientes }}</span>
                    </q-item-section>
                    <q-item-section side v-if="proyectoHover === p.id" class="sidebar-hover-actions">
                      <div class="row no-wrap items-center">
                        <q-btn flat dense round size="xs" icon="check_circle_outline" @click.prevent.stop="completarItem(p)" />
                        <q-btn flat dense round size="xs" icon="more_vert" @click.prevent.stop="abrirMenuProyecto($event, p)" />
                      </div>
                    </q-item-section>
                  </q-item>
                  <div v-if="!equipoItemsPorTipo(sec.tipo).length && !cargandoProyectos" class="sidebar-empty">
                    Sin {{ sec.label.toLowerCase() }}
                  </div>
                </template>
              </div>

              <!-- Etiquetas (equipo) -->
              <div class="sidebar-sub-section">
                <div class="sidebar-sub-header" @click="toggleAcordeon('eq-etiquetas')">
                  <q-icon :name="acordeonAbierto['eq-etiquetas'] ? 'expand_more' : 'chevron_right'" size="14px" />
                  <span class="q-ml-xs" style="flex:1">Etiquetas</span>
                  <span v-if="eqEtiquetasCount" class="sidebar-count">{{ eqEtiquetasCount }}</span>
                </div>
                <template v-if="acordeonAbierto['eq-etiquetas']">
                  <q-item
                    v-for="e in etiquetasGlobal" :key="e.id"
                    v-show="e.tareas_total"
                    clickable dense
                    class="sidebar-project-item"
                    :class="{ active: ruta === '/equipo' && String($route.query.etiqueta_id) === String(e.id) }"
                    :to="{ path: '/equipo', query: { etiqueta_id: e.id } }"
                    @click="drawerOpen = false"
                    @mouseenter="etiquetaHover = e.id"
                    @mouseleave="etiquetaHover = null"
                  >
                    <q-item-section avatar class="sidebar-item-icon">
                      <span class="proyecto-dot" :style="{ background: e.color || '#888' }" />
                    </q-item-section>
                    <q-item-section v-if="etiquetaEditandoId === e.id" class="sidebar-item-label" @click.prevent.stop>
                      <div class="etiqueta-edit-row">
                        <input type="color" class="etiqueta-edit-color" :value="e.color || '#888888'" @input="etiquetaEditColor = $event.target.value" />
                        <form @submit.prevent="guardarEtiquetaEdit(e)" style="flex:1;min-width:0">
                          <input class="etiqueta-edit-input" :value="e.nombre" @keydown.escape="etiquetaEditandoId = null" ref="etiquetaInputRef" />
                        </form>
                        <q-btn flat dense round size="xs" icon="check" color="positive" @click.prevent.stop="guardarEtiquetaEdit(e)" />
                        <q-btn flat dense round size="xs" icon="close" @click.prevent.stop="etiquetaEditandoId = null" />
                      </div>
                    </q-item-section>
                    <template v-else>
                      <q-item-section class="sidebar-item-label">{{ e.nombre }}</q-item-section>
                      <q-item-section side v-if="e.tareas_pendientes && etiquetaHover !== e.id">
                        <span class="sidebar-count">{{ e.tareas_pendientes }}</span>
                      </q-item-section>
                      <q-item-section side v-if="etiquetaHover === e.id">
                        <q-btn flat dense round size="xs" icon="more_vert" @click.prevent.stop="abrirMenuEtiqueta($event, e)" />
                      </q-item-section>
                    </template>
                  </q-item>
                  <div v-if="!etiquetasGlobal.length" class="sidebar-empty">Sin etiquetas</div>
                </template>
              </div>

              <!-- Completados -->
              <div v-if="proyectosCompletados.length" class="sidebar-sub-section">
                <div class="sidebar-sub-header" @click="mostrarCompletados = !mostrarCompletados">
                  <q-icon :name="mostrarCompletados ? 'expand_more' : 'chevron_right'" size="14px" />
                  <span class="q-ml-xs">Completados ({{ proyectosCompletados.length }})</span>
                </div>
                <template v-if="mostrarCompletados">
                  <q-item v-for="p in proyectosCompletados" :key="p.id" dense class="sidebar-project-item" style="opacity:0.45;pointer-events:none">
                    <q-item-section avatar class="sidebar-item-icon">
                      <span class="proyecto-dot" :style="{ background: p.color || '#607D8B' }" />
                    </q-item-section>
                    <q-item-section class="sidebar-item-label" style="text-decoration:line-through">{{ p.nombre }}</q-item-section>
                  </q-item>
                </template>
              </div>
            </q-expansion-item>
          </template>

          <!-- Mini mode: Equipo (click navega, hover abre popover) -->
          <template v-if="isMini">
            <q-item
              clickable dense
              class="sidebar-item sidebar-item-mini"
              :class="{ active: ruta === '/equipo' }"
              to="/equipo"
              @mouseenter="showHover('eq')"
              @mouseleave="hideHover('eq')"
            >
              <q-item-section avatar class="sidebar-item-icon"><q-icon name="group" /></q-item-section>
              <q-menu
                v-model="hoverMenus.eq"
                no-parent-event
                anchor="center right" self="center left"
                :offset="[8, 0]"
                class="sidebar-popover"
                @mouseenter="showHover('eq')"
                @mouseleave="hideHover('eq')"
              >
                <q-list dense style="min-width: 220px">
                  <q-item-label header class="sidebar-popover-title">Equipo</q-item-label>
                  <template v-for="sec in SECCIONES_SIDEBAR" :key="'mini-eq-'+sec.tipo">
                    <q-item
                      v-for="p in equipoItemsPorTipo(sec.tipo)" :key="p.id"
                      clickable dense v-close-popup
                      :to="{ path: '/equipo', query: { proyecto_id: p.id } }"
                    >
                      <q-item-section avatar style="min-width:20px"><span class="proyecto-dot" :style="{ background: p.color || '#607D8B' }" /></q-item-section>
                      <q-item-section>{{ p.nombre }}</q-item-section>
                      <q-item-section side v-if="p.tareas_pendientes"><span class="sidebar-count">{{ p.tareas_pendientes }}</span></q-item-section>
                    </q-item>
                  </template>
                </q-list>
              </q-menu>
            </q-item>
          </template>

          <!-- ═══ SEPARADOR ═══ -->
          <q-separator class="q-my-xs q-mx-md" />

          <!-- ═══ JORNADAS ═══ -->
          <q-item clickable dense class="sidebar-item" :class="{ active: ruta === '/jornadas' }" :to="'/jornadas'" @click="drawerOpen = false">
            <q-item-section avatar class="sidebar-item-icon"><q-icon name="schedule" /></q-item-section>
            <q-item-section v-if="!isMini" class="sidebar-item-label">Jornadas</q-item-section>
            <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">Jornadas</q-tooltip>
          </q-item>

          <!-- ═══ TABLAS ═══ -->
          <q-item-label v-if="!isMini" header class="sidebar-section-lbl">Tablas</q-item-label>

          <q-item clickable dense class="sidebar-item" :class="{ active: ruta === '/proyectos-tabla' }" to="/proyectos-tabla" @click="drawerOpen = false">
            <q-item-section avatar class="sidebar-item-icon"><q-icon name="folder_open" /></q-item-section>
            <q-item-section v-if="!isMini" class="sidebar-item-label">Proyectos</q-item-section>
            <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">Proyectos</q-tooltip>
          </q-item>

          <q-item clickable dense class="sidebar-item" :class="{ active: ruta === '/dificultades' }" to="/dificultades" @click="drawerOpen = false">
            <q-item-section avatar class="sidebar-item-icon"><q-icon name="warning_amber" /></q-item-section>
            <q-item-section v-if="!isMini" class="sidebar-item-label">Dificultades</q-item-section>
            <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">Dificultades</q-tooltip>
          </q-item>

          <q-item clickable dense class="sidebar-item" :class="{ active: ruta === '/compromisos' }" to="/compromisos" @click="drawerOpen = false">
            <q-item-section avatar class="sidebar-item-icon"><q-icon name="task_alt" /></q-item-section>
            <q-item-section v-if="!isMini" class="sidebar-item-label">Compromisos</q-item-section>
            <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">Compromisos</q-tooltip>
          </q-item>

          <q-item clickable dense class="sidebar-item" :class="{ active: ruta === '/ideas' }" to="/ideas" @click="drawerOpen = false">
            <q-item-section avatar class="sidebar-item-icon"><q-icon name="lightbulb_outline" /></q-item-section>
            <q-item-section v-if="!isMini" class="sidebar-item-label">Ideas</q-item-section>
            <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">Ideas</q-tooltip>
          </q-item>

        </q-list>
      </div>

      <!-- Footer sidebar -->
      <div class="sidebar-footer">
        <q-separator />
        <q-item clickable dense class="sidebar-item q-mt-xs" @click="toggleTema">
          <q-item-section avatar class="sidebar-item-icon">
            <q-icon :name="auth.tema === 'dark' ? 'light_mode' : 'dark_mode'" />
          </q-item-section>
          <q-item-section v-if="!isMini" class="sidebar-item-label">
            {{ auth.tema === 'dark' ? 'Modo claro' : 'Modo oscuro' }}
          </q-item-section>
          <q-tooltip v-if="isMini" anchor="center right" self="center left" :offset="[8, 0]">
            {{ auth.tema === 'dark' ? 'Modo claro' : 'Modo oscuro' }}
          </q-tooltip>
        </q-item>

        <q-item v-if="!isMini" dense class="sidebar-user" clickable @click="menuUsuario = !menuUsuario">
          <q-item-section avatar class="sidebar-item-icon">
            <q-avatar size="24px">
              <img :src="auth.usuario?.foto || ''" @error="e => e.target.style.display='none'" />
            </q-avatar>
          </q-item-section>
          <q-item-section class="sidebar-item-label">
            <div class="sidebar-user-name">{{ auth.usuario?.nombre }} <span class="sidebar-version">{{ APP_VERSION }}</span></div>
            <div class="sidebar-user-empresa">{{ auth.empresa_activa?.siglas || auth.empresa_activa?.uid }}</div>
          </q-item-section>
        </q-item>

        <!-- Menú usuario -->
        <div v-if="menuUsuario && !isMini" class="usuario-menu">
          <q-item clickable dense @click="cerrarSesion">
            <q-item-section avatar style="min-width:28px"><q-icon name="logout" size="16px" /></q-item-section>
            <q-item-section>Cerrar sesi&oacute;n</q-item-section>
          </q-item>
        </div>
      </div>
    </q-drawer>

    <!-- ═══ PAGE CONTAINER ═══ -->
    <q-page-container>
      <q-page class="main-page">
        <!-- Jornada header — siempre visible -->
        <JornadaHeader />

        <!-- Topbar — siempre visible -->
        <div class="topbar">
          <q-btn flat dense round icon="menu" class="lt-md" @click="drawerOpen = !drawerOpen" />
          <span class="topbar-title">{{ tituloRuta }}</span>
          <div v-if="esPaginaTareas" class="quick-search" :class="{ expanded: qsExpanded }">
            <q-btn flat dense round size="xs" icon="search" @click="qsExpanded = !qsExpanded; $nextTick(() => qsExpanded && $refs.qsInput?.focus())" />
            <input
              v-show="qsExpanded"
              ref="qsInput"
              v-model="qsQuery"
              class="qs-input"
              placeholder="Buscar tarea..."
              @keydown.escape="qsExpanded = false; qsQuery = ''"
            />
            <q-btn v-if="qsExpanded && qsQuery" flat dense round size="xs" icon="close" @click="qsQuery = ''; $refs.qsInput?.focus()" />
          </div>
        </div>

        <!-- Contenido con pull-to-refresh -->
        <div class="page-body" ref="pageBodyRef"
          @touchstart.passive="onPullStart"
          @touchmove.passive="onPullMove"
          @touchend="onPullEnd"
        >
          <div class="ptr-indicator" :class="{ visible: pullY > 0, refreshing: pullRefreshing }" :style="{ height: Math.min(pullY, 60) + 'px' }">
            <span v-if="pullRefreshing" class="material-icons ptr-spin">refresh</span>
            <span v-else class="material-icons" :style="{ transform: `rotate(${Math.min(pullY / 60, 1) * 180}deg)` }">arrow_downward</span>
          </div>
          <router-view :key="refreshKey" />
        </div>
      </q-page>
    </q-page-container>

    <!-- ═══ FOOTER — Bottom tab bar (mobile only via CSS lt-md) ═══ -->
    <q-footer bordered class="bottom-tab-bar lt-md">
      <RouterLink to="/tareas" class="btab" :class="{ active: ruta.startsWith('/tareas') }">
        <span class="material-icons">check_circle_outline</span>
        <span class="btab-label">Tareas</span>
      </RouterLink>
      <RouterLink to="/equipo" class="btab" :class="{ active: ruta.startsWith('/equipo') }">
        <span class="material-icons">group</span>
        <span class="btab-label">Equipo</span>
      </RouterLink>
      <RouterLink to="/jornadas" class="btab" :class="{ active: ruta.startsWith('/jornadas') }">
        <span class="material-icons">schedule</span>
        <span class="btab-label">Jornadas</span>
      </RouterLink>
      <RouterLink to="/proyectos-tabla" class="btab" :class="{ active: ruta.startsWith('/proyectos') }">
        <span class="material-icons">folder_open</span>
        <span class="btab-label">Proyectos</span>
      </RouterLink>
      <button class="btab" @click="drawerOpen = true">
        <span class="material-icons">menu</span>
        <span class="btab-label">M&aacute;s</span>
      </button>
    </q-footer>

    <!-- ═══ Panel lateral crear/editar ═══ -->
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

    <!-- ═══ Men&uacute; contextual ⋮ ═══ -->
    <Teleport to="body">
      <div v-if="menuProyecto.visible" class="proyecto-ctx-menu" :style="menuProyecto.style" @click.stop>
        <div class="ctx-item" @click="editarItem(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">edit</span> Editar
        </div>
        <div class="ctx-item" @click="verTabla(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">table_chart</span> Ver tabla
        </div>
        <div class="ctx-item ctx-item-warn" @click="archivarProyecto(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">archive</span> Archivar
        </div>
        <div class="ctx-item ctx-item-danger" @click="eliminarProyecto(menuProyecto.proyecto)">
          <span class="material-icons" style="font-size:15px">delete_outline</span> Eliminar
        </div>
      </div>
      <div v-if="menuEtiqueta.visible" class="ctx-backdrop" @click="menuEtiqueta.visible = false" />
      <div v-if="menuEtiqueta.visible" class="proyecto-ctx-menu" :style="menuEtiqueta.style" @click.stop>
        <div class="ctx-item" @click="editarEtiqueta">
          <span class="material-icons" style="font-size:15px">edit</span> Editar nombre
        </div>
        <div class="ctx-item ctx-item-danger" @click="eliminarEtiqueta">
          <span class="material-icons" style="font-size:15px">delete_outline</span> Eliminar
        </div>
      </div>
    </Teleport>

  </q-layout>
</template>

<script setup>
import { ref, reactive, computed, provide, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/authStore'
import { api } from 'src/services/api'
import { hoyLocal } from 'src/services/fecha'
import ProyectoPanel from 'src/components/ProyectoPanel.vue'
import JornadaHeader from 'src/components/JornadaHeader.vue'

const APP_VERSION = 'v2.7.19'
const $q = useQuasar()

// ─── Layout state ───
const drawerOpen       = ref(false)
const miniState        = ref(false)
const isMobile         = computed(() => $q.screen.lt.md)
const isMini           = computed(() => miniState.value && !isMobile.value)

// ─── Hover menus (mini-mode popover tipo Kommo) ───
const hoverMenus = reactive({ mis: false, eq: false })
const hoverTimers = {}
function showHover(key) {
  clearTimeout(hoverTimers[key])
  hoverMenus[key] = true
}
function hideHover(key) {
  hoverTimers[key] = setTimeout(() => { hoverMenus[key] = false }, 180)
}

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

const todosItems          = ref([])
const proyectosCompletados = ref([])
const mostrarCompletados  = ref(false)
const cargandoProyectos   = ref(false)
const proyectoHover       = ref(null)
const etiquetaHover       = ref(null)
const menuEtiqueta        = ref({ visible: false, etiqueta: null, style: {} })

const panelVisible = ref(false)
const panelItem    = ref(null)
const panelTipo    = ref('proyecto')

const categorias     = ref([])
const usuarios       = ref([])
const etiquetasGlobal = ref([])
const menuProyecto = ref({ visible: false, proyecto: null, style: {} })

const miEmail = computed(() => auth.usuario?.email || '')

function misItemsPorTipo(tipo) {
  return todosItems.value.filter(p => p.tipo === tipo && (p.responsables || []).includes(miEmail.value))
}
function equipoItemsPorTipo(tipo) {
  return todosItems.value.filter(p => p.tipo === tipo)
}

const acordeonAbierto = reactive({})
function toggleAcordeon(key) { acordeonAbierto[key] = !acordeonAbierto[key] }

async function cargarProyectos() {
  cargandoProyectos.value = true
  try {
    const activos = await api('/api/gestion/proyectos')
    const all = activos.proyectos || []
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

// Notificación a páginas (TareasPage/EquipoPage) cuando se crea/edita un item desde el panel
const ultimoItemGuardado = ref(null)
provide('ultimoItemGuardado', ultimoItemGuardado)

function onItemGuardado(p) {
  if (p._accion === 'creado') {
    todosItems.value.push(p)
    panelVisible.value = false
    const bloque = (p.responsables || []).includes(miEmail.value) ? 'bloque-mis' : 'bloque-eq'
    acordeonAbierto[bloque] = true
    acordeonAbierto[(bloque === 'bloque-mis' ? 'mis-' : 'eq-') + (p.tipo || 'proyecto')] = true
  } else {
    const idx = todosItems.value.findIndex(x => x.id === p.id)
    if (idx !== -1) todosItems.value[idx] = { ...todosItems.value[idx], ...p }
  }
  ultimoItemGuardado.value = { ...p, _ts: Date.now() }
}

function onItemEliminado(p) {
  todosItems.value = todosItems.value.filter(x => x.id !== p.id)
  if (String(route.query.proyecto_id) === String(p.id)) router.push('/tareas')
}

function abrirMenuProyecto(event, proyecto) {
  const rect = event.currentTarget.getBoundingClientRect()
  menuProyecto.value = {
    visible: true, proyecto,
    style: { position: 'fixed', top: `${rect.bottom + 4}px`, left: `${rect.left}px`, zIndex: 9999 }
  }
  setTimeout(() => document.addEventListener('click', cerrarMenuProyecto, { once: true }), 0)
}

function cerrarMenuProyecto() { menuProyecto.value.visible = false }

function editarItem(p) {
  cerrarMenuProyecto()
  abrirPanel(p.tipo || 'proyecto', p)
}
function verTabla(p) {
  cerrarMenuProyecto()
  router.push(RUTAS_TABLA[p.tipo || 'proyecto'] || '/proyectos-tabla')
}

async function completarItem(p) {
  cerrarMenuProyecto()
  const hoy = hoyLocal()
  const estadoFinal = ESTADOS_COMPLETADO[p.tipo || 'proyecto']
  try {
    await api(`/api/gestion/proyectos/${p.id}`, {
      method: 'PUT', body: JSON.stringify({ estado: estadoFinal, fecha_finalizacion_real: hoy })
    })
    todosItems.value = todosItems.value.filter(x => x.id !== p.id)
    proyectosCompletados.value.unshift({ ...p, estado: estadoFinal, fecha_finalizacion_real: hoy })
    if (String(route.query.proyecto_id) === String(p.id)) router.replace('/tareas')
  } catch (e) { console.error(e) }
}

async function archivarProyecto(p) {
  cerrarMenuProyecto()
  try {
    await api(`/api/gestion/proyectos/${p.id}`, { method: 'PUT', body: JSON.stringify({ estado: 'Archivado' }) })
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
    visible: true, etiqueta,
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
    await api(`/api/gestion/etiquetas/${e.id}`, { method: 'PUT', body: JSON.stringify(body) })
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

// Búsqueda rápida
const qsExpanded = ref(false)
const qsQuery    = ref('')
const esPaginaTareas = computed(() => ruta.value.startsWith('/tareas') || ruta.value.startsWith('/equipo'))
provide('qsQuery', qsQuery)
watch(ruta, () => { qsQuery.value = ''; qsExpanded.value = false })

const TITULOS = { '/tareas': 'Mis Tareas', '/equipo': 'Equipo', '/jornadas': 'Jornadas' }
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
/* ─── Sidebar drawer overrides ─── */
.sidebar-drawer {
  background: var(--bg-sidebar) !important;
}
.sidebar-drawer :deep(.q-drawer__content) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Scroll area */
.sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
}

/* Logo */
.sidebar-logo {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 8px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.sidebar-logo-img {
  width: 28px; height: 28px;
  border-radius: var(--radius-full);
  flex-shrink: 0; object-fit: cover;
}
/* En modo mini (56px), ocultar el logo-img y centrar el toggle btn */
.mini-mode .sidebar-logo {
  padding: 0;
  justify-content: center;
}
.mini-mode .sidebar-logo-img { display: none; }
.sidebar-logo-name {
  font-size: 12px; font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}
.sidebar-toggle-btn {
  color: var(--text-tertiary);
}
.sidebar-toggle-btn:hover { color: var(--text-primary); }

/* Nav items — Linear style */
.sidebar-item {
  min-height: 32px !important;
  padding: 0 8px !important;
  margin: 1px 4px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  transition: background 80ms, color 80ms;
}
.sidebar-item:hover { background: var(--bg-row-hover); color: var(--text-primary) !important; }
.sidebar-item.active,
.sidebar-item.q-router-link--active,
.sidebar-item.q-router-link--exact-active {
  background: var(--bg-row-selected);
  color: var(--text-primary) !important;
  font-weight: 500;
}

.sidebar-item-mini { justify-content: center; }

.sidebar-item-icon {
  min-width: 28px !important;
  max-width: 28px;
}
.sidebar-item-icon .q-icon { font-size: 16px; opacity: 0.55; }
.sidebar-item:hover .sidebar-item-icon .q-icon,
.sidebar-item.active .sidebar-item-icon .q-icon { opacity: 0.9; }

.sidebar-item-label {
  font-size: 13px;
}

/* Section label */
.sidebar-section-lbl {
  font-size: 10px !important;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary) !important;
  padding: 12px 16px 2px !important;
  min-height: 24px !important;
}

/* Sub-sections (inside expansion items) */
.sidebar-sub-section { padding-left: 20px; }
.sidebar-sub-header {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 12px; font-size: 12px; font-weight: 500;
  color: var(--text-secondary); cursor: pointer;
  border-radius: 4px; transition: color 80ms;
  user-select: none;
}
.sidebar-sub-header:hover { color: var(--text-primary); }
.sidebar-add-btn {
  color: var(--text-tertiary) !important;
  opacity: 0;
  transition: opacity 80ms;
}
.sidebar-sub-header:hover .sidebar-add-btn { opacity: 1; }

/* Project items (sub-level dentro de acordeones) */
.sidebar-project-item {
  min-height: 26px !important;
  padding: 2px 8px 2px 16px !important;
  margin: 0 4px;
  border-radius: 4px;
  font-size: 12px !important;
  color: var(--text-secondary) !important;
}
.sidebar-project-item :deep(.q-item__section--main),
.sidebar-project-item .q-item__section--main {
  font-size: 12px !important;
  color: var(--text-secondary);
}
.sidebar-project-item:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary) !important;
}
.sidebar-project-item.active,
.sidebar-project-item.q-router-link--active,
.sidebar-project-item.q-router-link--exact-active {
  background: var(--bg-row-selected);
  color: var(--text-primary) !important;
  font-weight: 500;
}
.sidebar-project-item.q-router-link--active :deep(.q-item__section--main),
.sidebar-project-item.q-router-link--exact-active :deep(.q-item__section--main) {
  color: var(--text-primary);
}

/* Count badge */
.sidebar-count {
  font-size: 10px;
  color: var(--text-tertiary);
  min-width: 14px; text-align: right;
}

/* Proyecto dot */
.proyecto-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  display: inline-block;
}

/* Hover actions */
.sidebar-hover-actions .q-btn { color: var(--text-tertiary); }
.sidebar-hover-actions .q-btn:hover { color: var(--text-primary); }

/* Empty hint */
.sidebar-empty {
  padding: 2px 16px 4px;
  font-size: 11px; color: var(--text-tertiary); font-style: italic;
}

/* Footer */
.sidebar-footer {
  flex-shrink: 0;
  padding: 0 4px 8px;
}
.sidebar-user { padding: 4px 8px !important; }
.sidebar-user-name {
  font-size: 11px; font-weight: 600; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sidebar-version { font-size: 9px; color: var(--text-tertiary); font-weight: 400; }
.sidebar-user-empresa { font-size: 10px; color: var(--text-tertiary); }

/* User menu */
.usuario-menu {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  margin: 4px;
  overflow: hidden;
}

/* Popover en mini mode → movido a app.scss porque QMenu se teletransporta al body */

/* Expansion item overrides */
.sidebar-drawer :deep(.q-expansion-item__container > .q-item) {
  min-height: 32px;
  padding: 0 8px;
  margin: 1px 4px;
  border-radius: 6px;
}
.sidebar-drawer :deep(.q-expansion-item__content) {
  padding: 0;
}

/* ─── Topbar ─── */
.topbar {
  height: 44px;
  display: flex; align-items: center;
  padding: 0 16px; gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  background: var(--bg-app);
}
.topbar-title {
  font-size: 12px; font-weight: 600;
  color: var(--text-primary); flex: 1;
}
.mobile-header {
  background: var(--bg-app) !important;
  color: var(--text-primary);
}

/* ─── Quick search ─── */
.quick-search { display: flex; align-items: center; margin-left: auto; }
.qs-input {
  background: transparent; border: none;
  border-bottom: 1px solid var(--border-default);
  color: var(--text-primary); font-size: 13px;
  padding: 2px 4px; width: 160px;
  font-family: inherit; outline: none;
}
.qs-input:focus { border-bottom-color: var(--accent); }
@media (max-width: 768px) { .qs-input { width: 120px; } }

/* ─── Main page ─── */
.main-page {
  display: flex; flex-direction: column;
  min-height: 100%;
  padding: 0 !important;
}
.page-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ─── Pull to refresh ─── */
.ptr-indicator {
  display: flex; align-items: center; justify-content: center;
  height: 0; overflow: hidden;
  color: var(--text-tertiary);
  transition: height 150ms ease;
}
.ptr-indicator.visible { transition: none; }
.ptr-indicator .material-icons { font-size: 20px; transition: transform 150ms; }
.ptr-spin { animation: ptr-spin 600ms linear infinite; }
@keyframes ptr-spin { to { transform: rotate(360deg); } }

/* ─── Bottom tab bar ─── */
.bottom-tab-bar {
  display: flex;
  background: var(--bg-surface) !important;
  padding: 4px 0 env(safe-area-inset-bottom, 0);
}
.btab {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 1px; padding: 6px 0;
  font-size: 9px; font-weight: 500;
  color: var(--text-tertiary);
  text-decoration: none;
  cursor: pointer;
  background: none; border: none;
  font-family: inherit;
  transition: color 80ms;
}
.btab .material-icons { font-size: 20px; }
.btab-label { white-space: nowrap; }
.btab.active { color: var(--accent); }
.btab:hover { color: var(--text-primary); }

/* ─── Menú contextual ─── */
.proyecto-ctx-menu {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 150px; overflow: hidden;
}
.ctx-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer; transition: background 60ms;
}
.ctx-item:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.ctx-item-warn:hover { color: var(--color-warning); }
.ctx-item-danger:hover { color: var(--color-error); }
.ctx-backdrop { position: fixed; inset: 0; z-index: 9998; }

/* ─── Etiqueta edit inline ─── */
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
</style>
