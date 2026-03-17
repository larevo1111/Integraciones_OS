<template>
  <div class="sidebar">

    <!-- Header: Logo + Workspace -->
    <div class="sidebar-header">
      <div class="workspace-switcher">
        <div class="ws-logo">IA</div>
        <span class="ws-name">IA Admin</span>
      </div>
    </div>

    <!-- Nav principal -->
    <nav class="sidebar-nav">
      <div class="nav-section">
        <router-link to="/dashboard" class="nav-item" active-class="active">
          <LayoutDashboardIcon :size="15" class="nav-icon" />
          <span>Dashboard</span>
        </router-link>
      </div>

      <div class="nav-divider" />

      <div class="nav-group-label">Configuración</div>

      <div class="nav-section">
        <router-link v-if="nivel >= 7" to="/agentes" class="nav-item" active-class="active">
          <BotIcon :size="15" class="nav-icon" />
          <span>Agentes</span>
        </router-link>
        <router-link v-if="nivel >= 7" to="/tipos" class="nav-item" active-class="active">
          <SettingsIcon :size="15" class="nav-icon" />
          <span>Tipos de consulta</span>
        </router-link>
        <router-link v-if="nivel >= 7" to="/usuarios" class="nav-item" active-class="active">
          <UsersIcon :size="15" class="nav-icon" />
          <span>Usuarios</span>
        </router-link>
        <router-link v-if="nivel >= 5" to="/contextos" class="nav-item" active-class="active">
          <DatabaseIcon :size="15" class="nav-icon" />
          <span>Contextos</span>
        </router-link>
        <router-link v-if="nivel >= 7" to="/conexiones" class="nav-item" active-class="active">
          <LinkIcon :size="15" class="nav-icon" />
          <span>Conexiones BD</span>
        </router-link>
        <router-link v-if="nivel >= 7" to="/logica-negocio" class="nav-item" active-class="active">
          <BookOpenIcon :size="15" class="nav-icon" />
          <span>Lógica de negocio</span>
        </router-link>
        <router-link v-if="nivel >= 7" to="/config" class="nav-item" active-class="active">
          <SlidersHorizontalIcon :size="15" class="nav-icon" />
          <span>Configuración</span>
        </router-link>
      </div>

      <div class="nav-divider" />

      <div class="nav-group-label">Monitoreo</div>

      <div class="nav-section">
        <router-link v-if="nivel >= 7" to="/bot-sesiones" class="nav-item" active-class="active">
          <MessageSquareIcon :size="15" class="nav-icon" />
          <span>Bot Telegram</span>
        </router-link>
        <router-link v-if="nivel >= 3" to="/logs" class="nav-item" active-class="active">
          <ScrollIcon :size="15" class="nav-icon" />
          <span>Logs</span>
        </router-link>
        <router-link to="/playground" class="nav-item" active-class="active">
          <PlayIcon :size="15" class="nav-icon" />
          <span>Playground</span>
        </router-link>
      </div>
    </nav>

    <!-- Footer: perfil + logout -->
    <div class="sidebar-footer">
      <div class="nav-item" style="cursor:default">
        <div class="avatar-sm">{{ inicial }}</div>
        <div class="user-info">
          <span class="user-name">{{ usuario?.nombre }}</span>
          <span class="user-rol">{{ usuario?.rol }}</span>
        </div>
      </div>
      <button class="nav-item logout-btn" @click="$emit('logout')" title="Cerrar sesión">
        <LogOutIcon :size="14" class="nav-icon" />
        <span>Cerrar sesión</span>
      </button>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  LayoutDashboardIcon, BotIcon, SettingsIcon, UsersIcon,
  ScrollIcon, PlayIcon, LogOutIcon, DatabaseIcon, LinkIcon,
  SlidersHorizontalIcon, BookOpenIcon, MessageSquareIcon
} from 'lucide-vue-next'
import { useAuthStore } from 'stores/authStore'

const emit = defineEmits(["logout"])
const props = defineProps({ usuario: { type: Object, default: () => ({ nombre: 'Admin', rol: 'admin' }) } })
const inicial = computed(() => props.usuario.nombre?.charAt(0).toUpperCase() || 'A')

const auth  = useAuthStore()
const nivel = computed(() => auth.nivel)
</script>

<style scoped>
.sidebar {
  width: 220px;
  height: 100%;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.workspace-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ws-logo {
  width: 22px; height: 22px;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: white;
  font-size: 9px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.ws-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.nav-section { padding: 0 6px; }

.nav-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: 4px 12px;
}

.nav-group-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-tertiary);
  padding: 8px 14px 4px;
  user-select: none;
}

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
  background: var(--bg-card-hover);
  color: var(--text-primary);
}
.nav-item.active { font-weight: 500; }
.nav-icon { opacity: 0.55; flex-shrink: 0; }
.nav-item:hover .nav-icon, .nav-item.active .nav-icon { opacity: 0.9; }

.sidebar-footer {
  padding: 6px;
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.user-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.user-rol  { font-size: 11px; color: var(--text-tertiary); text-transform: capitalize; }

.avatar-sm {
  width: 24px; height: 24px;
  border-radius: var(--radius-full);
  background: var(--accent-muted);
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.logout-btn {
  color: var(--text-tertiary);
  margin-top: 2px;
}
.logout-btn:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}
</style>
