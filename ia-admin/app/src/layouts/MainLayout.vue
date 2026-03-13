<template>
  <div class="app-shell">
    <AppHeader
      :usuario="authStore.usuario"
      :empresa="authStore.empresa_activa"
      :total-empresas="totalEmpresas"
      @logout="logout"
      @cambiar-empresa="cambiarEmpresa"
    />
    <div class="app-body">
      <AppSidebar :usuario="authStore.usuario" @logout="logout" />
      <div class="main-area">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppSidebar from 'src/components/AppSidebar.vue'
import AppHeader  from 'src/components/AppHeader.vue'
import { useAuthStore } from 'src/stores/authStore'

const router    = useRouter()
const authStore = useAuthStore()

const totalEmpresas = ref(1)

onMounted(async () => {
  try {
    const token = localStorage.getItem('ia_jwt')
    if (!token) return
    const res = await fetch('/api/ia/mis-empresas', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      totalEmpresas.value = data.empresas?.length || 1
    }
  } catch (e) {
    // silencioso — no crítico
  }
})

function logout() {
  authStore.cerrarSesion()
  router.push('/login')
}

function cambiarEmpresa() {
  // Ir a login en paso 2 para re-seleccionar empresa
  authStore.cerrarSesion()
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-app);
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.main-area {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-app);
}
</style>
