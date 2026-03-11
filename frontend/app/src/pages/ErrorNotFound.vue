<template>
  <div class="not-found">
    <span class="code">404</span>
    <p>Página no encontrada</p>
    <router-link to="/dashboard" class="btn-back">Ir al Dashboard</router-link>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 12px;
  color: var(--text-secondary);
}
.code { font-size: 64px; font-weight: 700; color: var(--text-tertiary); line-height: 1; }
.btn-back {
  margin-top: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.06);
  color: var(--text-primary);
  text-decoration: none;
  font-size: 13px;
  border: 1px solid var(--border-strong);
}
.btn-back:hover { background: rgba(255,255,255,0.10); }
</style>
