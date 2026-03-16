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
        <div class="sidebar-section">
          <div class="sidebar-section-label">Tareas</div>
          <RouterLink to="/tareas" class="nav-item" :class="{ active: ruta === '/tareas' }">
            <span class="nav-item-icon material-icons">check_circle_outline</span>
            <span class="nav-item-label">Mis Tareas</span>
          </RouterLink>
          <RouterLink to="/equipo" class="nav-item" :class="{ active: ruta === '/equipo' }">
            <span class="nav-item-icon material-icons">group</span>
            <span class="nav-item-label">Equipo</span>
          </RouterLink>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Conocimiento</div>
          <RouterLink to="/dificultades" class="nav-item" :class="{ active: ruta.startsWith('/dificultades') }">
            <span class="nav-item-icon material-icons">warning_amber</span>
            <span class="nav-item-label">Dificultades</span>
          </RouterLink>
          <RouterLink to="/ideas" class="nav-item" :class="{ active: ruta.startsWith('/ideas') }">
            <span class="nav-item-icon material-icons">lightbulb_outline</span>
            <span class="nav-item-label">Ideas y Hechos</span>
          </RouterLink>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Compromisos</div>
          <RouterLink to="/pendientes" class="nav-item" :class="{ active: ruta.startsWith('/pendientes') }">
            <span class="nav-item-icon material-icons">task_alt</span>
            <span class="nav-item-label">Pendientes</span>
          </RouterLink>
          <RouterLink to="/informes" class="nav-item" :class="{ active: ruta.startsWith('/informes') }">
            <span class="nav-item-icon material-icons">bar_chart</span>
            <span class="nav-item-label">Informes</span>
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
            <div class="sidebar-user-name">{{ auth.usuario?.nombre }}</div>
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
      <!-- Topbar mobile -->
      <div class="topbar">
        <button class="btn-icon d-mobile-only" @click="drawerOpen = true">
          <span class="material-icons">menu</span>
        </button>
        <span class="topbar-title">{{ tituloRuta }}</span>
        <slot name="topbar-actions" />
      </div>

      <!-- Contenido de la página -->
      <div class="page-body">
        <router-view />
      </div>
    </div>

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
            <nav class="sidebar-nav">
              <RouterLink to="/tareas"       class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">check_circle_outline</span><span class="nav-item-label">Mis Tareas</span></RouterLink>
              <RouterLink to="/equipo"       class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">group</span><span class="nav-item-label">Equipo</span></RouterLink>
              <div class="sidebar-section-label" style="padding:12px 16px 2px">Conocimiento</div>
              <RouterLink to="/dificultades" class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">warning_amber</span><span class="nav-item-label">Dificultades</span></RouterLink>
              <RouterLink to="/ideas"        class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">lightbulb_outline</span><span class="nav-item-label">Ideas y Hechos</span></RouterLink>
              <div class="sidebar-section-label" style="padding:12px 16px 2px">Compromisos</div>
              <RouterLink to="/pendientes"   class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">task_alt</span><span class="nav-item-label">Pendientes</span></RouterLink>
              <RouterLink to="/informes"     class="nav-item" @click="drawerOpen=false"><span class="material-icons nav-item-icon">bar_chart</span><span class="nav-item-label">Informes</span></RouterLink>
            </nav>
          </aside>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/authStore'

const auth             = useAuthStore()
const router           = useRouter()
const route            = useRoute()
const sidebarCollapsed = ref(false)
const drawerOpen       = ref(false)
const menuUsuario      = ref(false)

const ruta = computed(() => route.path)

const TITULOS = {
  '/tareas':       'Mis Tareas',
  '/equipo':       'Equipo',
  '/dificultades': 'Dificultades',
  '/ideas':        'Ideas y Hechos',
  '/pendientes':   'Pendientes',
  '/informes':     'Informes'
}
const tituloRuta = computed(() => {
  for (const [path, titulo] of Object.entries(TITULOS)) {
    if (ruta.value.startsWith(path)) return titulo
  }
  return 'OS Gestión'
})

function toggleTema() {
  auth.cambiarTema(auth.tema === 'dark' ? 'light' : 'dark')
}

function cerrarSesion() {
  auth.cerrarSesion()
  router.push('/login')
}
</script>

<style scoped>
.d-mobile-only { display: none; }
@media (max-width: 768px) {
  .d-mobile-only { display: flex; }
  .sidebar { display: none; }
}

/* Drawer mobile */
.drawer-overlay {
  position: fixed; inset: 0;
  background: var(--bg-overlay);
  z-index: 300;
  display: flex;
}
.drawer-panel {
  width: 260px;
  height: 100%;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex; flex-direction: column;
  overflow-y: auto;
}
.drawer-enter-active, .drawer-leave-active { transition: opacity 150ms; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-active .drawer-panel, .drawer-leave-active .drawer-panel { transition: transform 150ms ease-out; }
.drawer-enter-from .drawer-panel, .drawer-leave-to .drawer-panel { transform: translateX(-100%); }

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
