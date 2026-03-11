<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="main-area">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import AppSidebar from 'src/components/AppSidebar.vue'
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-app);
}

.main-area {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-app);
}
</style>
