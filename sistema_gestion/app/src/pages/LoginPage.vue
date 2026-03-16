<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">G</div>
      <h1 class="login-title">OS Gestión</h1>
      <p class="login-subtitle">Gestión de tareas y conocimiento del equipo</p>

      <!-- Selector de empresa (si hay múltiples) -->
      <div v-if="empresas.length" class="empresa-selector">
        <p class="input-label" style="text-align:left;margin-bottom:10px">Selecciona tu empresa:</p>
        <button
          v-for="emp in empresas"
          :key="emp.uid"
          class="empresa-btn"
          :class="{ loading: seleccionando === emp.uid }"
          @click="seleccionar(emp.uid)"
        >
          <span class="empresa-siglas">{{ emp.siglas || emp.uid }}</span>
          <span class="empresa-nombre">{{ emp.nombre }}</span>
          <span v-if="seleccionando === emp.uid" class="material-icons spin" style="font-size:16px;color:var(--text-tertiary)">refresh</span>
        </button>
      </div>

      <!-- Botón Google -->
      <div v-else>
        <GoogleLogin :callback="onGoogleCallback" :auto-login="false">
          <template #default="{ login }">
            <button class="google-btn" :disabled="cargando" @click="login">
              <svg v-if="!cargando" width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span v-if="cargando" class="material-icons spin" style="font-size:18px">refresh</span>
              <span>{{ cargando ? 'Verificando...' : 'Continuar con Google' }}</span>
            </button>
          </template>
        </GoogleLogin>

        <p v-if="error" class="login-error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { GoogleLogin } from 'vue3-google-login'
import { useAuthStore } from 'src/stores/authStore'

const router    = useRouter()
const auth      = useAuthStore()
const cargando  = ref(false)
const error     = ref('')
const empresas  = ref([])
const seleccionando = ref(null)

async function onGoogleCallback(response) {
  cargando.value = true
  error.value    = ''
  try {
    const data = await auth.autenticarGoogle(response.credential)
    if (data.tipo === 'final') {
      router.push('/tareas')
    } else {
      empresas.value = data.empresas
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function seleccionar(uid) {
  seleccionando.value = uid
  try {
    await auth.seleccionarEmpresa(uid)
    router.push('/tareas')
  } catch (e) {
    error.value = e.message
    seleccionando.value = null
  }
}
</script>

<style scoped>
.empresa-selector { text-align: left; }
.empresa-btn {
  width: 100%;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  background: var(--bg-input);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 80ms, background 80ms;
  color: var(--text-primary);
  font-family: var(--font-sans);
}
.empresa-btn:hover { border-color: var(--border-focus); background: var(--bg-card-hover); }
.empresa-siglas {
  font-size: 11px; font-weight: 700;
  background: var(--accent-muted); color: var(--accent);
  padding: 2px 6px; border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.empresa-nombre { flex: 1; font-size: 13px; font-weight: 500; text-align: left; }
.login-error { color: var(--color-error); font-size: 12px; margin-top: 12px; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
