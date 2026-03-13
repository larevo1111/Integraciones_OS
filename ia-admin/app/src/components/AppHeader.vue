<template>
  <header class="app-header">
    <!-- Marca -->
    <div class="header-brand">
      <div class="header-logo">IA</div>
      <span class="header-title">IA Admin</span>
    </div>

    <!-- Empresa activa -->
    <div class="header-center" v-if="empresa">
      <span class="header-empresa-nombre">{{ empresa.nombre }}</span>
      <span class="header-empresa-badge">{{ empresa.siglas }}</span>
    </div>

    <!-- Acciones derechas -->
    <div class="header-actions">
      <span class="header-user">{{ usuario?.nombre }}</span>
      <button
        v-if="puedeCambiarEmpresa"
        class="header-btn"
        @click="$emit('cambiar-empresa')"
        title="Cambiar empresa"
      >
        <ArrowLeftRightIcon :size="14" />
        <span>Cambiar empresa</span>
      </button>
      <button class="header-btn header-btn-logout" @click="$emit('logout')" title="Cerrar sesión">
        <LogOutIcon :size="14" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { LogOutIcon, ArrowLeftRightIcon } from 'lucide-vue-next'

const props = defineProps({
  usuario:       { type: Object, default: null },
  empresa:       { type: Object, default: null },
  totalEmpresas: { type: Number, default: 1 }
})

defineEmits(['logout', 'cambiar-empresa'])

const puedeCambiarEmpresa = computed(() => props.totalEmpresas > 1)
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  gap: 12px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.header-logo {
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

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.header-empresa-nombre {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.header-empresa-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  background: var(--accent-muted);
  color: var(--accent);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
}

.header-user {
  font-size: 12px;
  color: var(--text-tertiary);
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: background 70ms, color 70ms;
}

.header-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.header-btn-logout {
  padding: 0 8px;
  border-color: transparent;
}

.header-btn-logout:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}
</style>
