<template>
  <div class="app-shell">
    <AppSidebar :usuario="usuario" />
    <div class="main-area">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppSidebar from 'src/components/AppSidebar.vue'

const usuario = ref({ nombre: 'Admin', email: '', rol: 'admin' })

onMounted(async () => {
  try {
    const res = await fetch('/api/ia/me')
    if (res.ok) usuario.value = await res.json()
  } catch (e) {
    // Sin auth (dev local) — usuario por defecto
  }
})
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
