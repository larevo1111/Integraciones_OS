<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-subtitle">Bienvenido, Santiago — Origen Silvestre</p>
    </div>

    <div class="placeholder-content">
      <div class="placeholder-icon">
        <LayoutDashboardIcon :size="32" />
      </div>
      <p>Dashboard en construcción</p>
      <span>Aquí irán los KPIs y resúmenes del negocio</span>
    </div>
  </div>
</template>

<script setup>
import { LayoutDashboardIcon } from 'lucide-vue-next'
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  gap: 10px;
  color: var(--text-tertiary);
}

.placeholder-icon {
  opacity: 0.25;
  margin-bottom: 4px;
}

.placeholder-content p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.placeholder-content span {
  font-size: 13px;
  color: var(--text-tertiary);
}
</style>
