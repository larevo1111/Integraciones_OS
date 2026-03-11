<template>
  <div class="sidebar">

    <!-- Header: Logo + Workspace -->
    <div class="sidebar-header">
      <div class="workspace-switcher">
        <div class="ws-logo">OS</div>
        <span class="ws-name">Origen Silvestre</span>
      </div>
      <div class="sidebar-header-actions">
        <button class="btn-icon" title="Buscar">
          <SearchIcon :size="15" />
        </button>
        <button class="btn-icon" title="Nueva tarea" @click="$router.push('/tareas/nueva')">
          <PlusIcon :size="15" />
        </button>
      </div>
    </div>

    <!-- Nav principal -->
    <nav class="sidebar-nav">

      <!-- Items fijos superiores -->
      <div class="nav-section">
        <router-link to="/dashboard" class="nav-item" active-class="active">
          <LayoutDashboardIcon :size="15" class="nav-icon" />
          <span>Dashboard</span>
        </router-link>
      </div>

      <div class="nav-divider" />

      <!-- Módulos con submenús -->
      <div
        v-for="modulo in menu"
        :key="modulo.uid"
        class="nav-module"
      >
        <!-- Cabecera del módulo -->
        <button
          class="nav-module-header"
          :class="{ expanded: expandidos.includes(modulo.uid) }"
          @click="toggleModulo(modulo.uid)"
        >
          <div class="nav-module-left">
            <span class="nav-module-dot" :style="{ background: modulo.color }" />
            <span class="nav-module-titulo">{{ modulo.titulo }}</span>
          </div>
          <ChevronRightIcon :size="13" class="nav-chevron" />
        </button>

        <!-- Submenús -->
        <transition name="submenu">
          <div v-if="expandidos.includes(modulo.uid)" class="nav-sub-list">
            <router-link
              v-for="item in modulo.hijos"
              :key="item.uid"
              :to="item.ruta"
              class="nav-sub-item"
              active-class="active"
            >
              <span class="nav-sub-dot" />
              <span>{{ item.titulo }}</span>
            </router-link>
          </div>
        </transition>
      </div>

      <div class="nav-divider" />

      <!-- Herramientas fijas abajo -->
      <div class="nav-section">
        <router-link to="/herramientas/metabase" class="nav-item" active-class="active">
          <PieChartIcon :size="15" class="nav-icon" />
          <span>Análisis de datos</span>
        </router-link>
        <router-link to="/herramientas/ia" class="nav-item" active-class="active">
          <BotIcon :size="15" class="nav-icon" />
          <span>Agente IA</span>
        </router-link>
      </div>
    </nav>

    <!-- Footer: perfil -->
    <div class="sidebar-footer">
      <button class="nav-item" style="width:100%">
        <div class="avatar-sm">S</div>
        <span>Santiago</span>
        <SettingsIcon :size="13" class="nav-icon" style="margin-left:auto;opacity:0.4" />
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { MENU } from 'src/data/menu.js'
import {
  SearchIcon, PlusIcon, LayoutDashboardIcon, ChevronRightIcon,
  PieChartIcon, BotIcon, SettingsIcon
} from 'lucide-vue-next'

const menu = MENU

// Expandir el primer módulo por defecto
const expandidos = ref([MENU[0].uid])

function toggleModulo(uid) {
  const idx = expandidos.value.indexOf(uid)
  if (idx === -1) expandidos.value.push(uid)
  else expandidos.value.splice(idx, 1)
}
</script>

<style scoped>
/* ─── SIDEBAR CONTENEDOR ────────────────────────────── */
.sidebar {
  width: 232px;
  height: 100vh;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

/* ─── HEADER ────────────────────────────────────────── */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.workspace-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--radius-md);
  padding: 4px 6px;
  margin: -4px -6px;
  cursor: pointer;
  transition: background 80ms;
}
.workspace-switcher:hover { background: rgba(255,255,255,0.05); }

.ws-logo {
  width: 22px; height: 22px;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.ws-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.sidebar-header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

/* ─── NAV ───────────────────────────────────────────── */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.nav-section {
  padding: 0 6px;
}

.nav-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 4px 12px;
}

/* Item base (dashboard, herramientas fijas) */
.nav-item {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 8px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  cursor: pointer;
  text-decoration: none;
  border: none;
  background: transparent;
  width: 100%;
  transition: background 70ms, color 70ms;
  user-select: none;
}
.nav-item:hover, .nav-item.active {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}
.nav-item.active { font-weight: 500; }
.nav-icon { opacity: 0.55; flex-shrink: 0; }
.nav-item:hover .nav-icon, .nav-item.active .nav-icon { opacity: 0.9; }

/* ─── MÓDULOS ───────────────────────────────────────── */
.nav-module { padding: 0 6px; }

.nav-module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 28px;
  padding: 0 8px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 70ms;
}
.nav-module-header:hover { background: rgba(255,255,255,0.04); }

.nav-module-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-module-dot {
  width: 7px; height: 7px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.nav-module-titulo {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-tertiary);
  user-select: none;
}
.nav-module-header:hover .nav-module-titulo,
.nav-module-header.expanded .nav-module-titulo {
  color: var(--text-secondary);
}

.nav-chevron {
  color: var(--text-tertiary);
  opacity: 0.6;
  transition: transform 150ms ease-out;
  flex-shrink: 0;
}
.nav-module-header.expanded .nav-chevron {
  transform: rotate(90deg);
}

/* ─── SUBMENÚS ──────────────────────────────────────── */
.nav-sub-list {
  padding: 2px 0 4px 0;
}

.nav-sub-item {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 30px;
  padding: 0 8px 0 22px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: background 70ms, color 70ms;
}
.nav-sub-item:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}
.nav-sub-item.active {
  background: rgba(255,255,255,0.07);
  color: var(--text-primary);
  font-weight: 500;
}

.nav-sub-dot {
  width: 4px; height: 4px;
  border-radius: var(--radius-full);
  background: var(--text-tertiary);
  flex-shrink: 0;
  transition: background 70ms;
}
.nav-sub-item:hover .nav-sub-dot,
.nav-sub-item.active .nav-sub-dot {
  background: var(--text-secondary);
}

/* ─── FOOTER ────────────────────────────────────────── */
.sidebar-footer {
  padding: 6px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* Avatar pequeño para el perfil */
.avatar-sm {
  width: 22px; height: 22px;
  border-radius: var(--radius-full);
  background: var(--accent-muted);
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

/* ─── BOTÓN ÍCONO ───────────────────────────────────── */
.btn-icon {
  width: 28px; height: 28px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 70ms, color 70ms;
}
.btn-icon:hover {
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
}

/* ─── TRANSICIÓN SUBMENÚS ───────────────────────────── */
.submenu-enter-active,
.submenu-leave-active {
  transition: opacity 120ms ease-out, transform 120ms ease-out;
}
.submenu-enter-from,
.submenu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
