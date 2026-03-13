<template>
  <div class="app-shell">
    <AppSidebar :usuario="authStore.usuario" @logout="logout" />
    <div class="main-area">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import AppSidebar from 'src/components/AppSidebar.vue'
import { useAuthStore } from 'src/stores/authStore'

const router    = useRouter()
const authStore = useAuthStore()

function logout() {
  authStore.cerrarSesion()
  router.push('/login')
}
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
