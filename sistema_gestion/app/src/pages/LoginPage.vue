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
        <div v-if="cargando" class="google-btn-loading">
          <span class="material-icons spin" style="font-size:18px">refresh</span>
          <span>Verificando...</span>
        </div>
        <!-- GSI renderiza el botón aquí -->
        <div id="google-signin-btn" :style="cargando ? 'display:none' : ''"></div>

        <p v-if="error" class="login-error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { googleSdkLoaded } from 'vue3-google-login'
import { useAuthStore } from 'src/stores/authStore'

const router    = useRouter()
const auth      = useAuthStore()
const cargando  = ref(false)
const error     = ref('')
const empresas  = ref([])
const seleccionando = ref(null)

onMounted(() => {
  googleSdkLoaded((google) => {
    google.accounts.id.initialize({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      callback: onGoogleCallback,
      ux_mode: 'popup'
    })
    google.accounts.id.renderButton(
      document.getElementById('google-signin-btn'),
      { theme: 'filled_black', size: 'large', width: 280, text: 'continue_with', locale: 'es' }
    )
  })
})

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
.google-btn-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  height: 44px; color: var(--text-tertiary); font-size: 14px;
}
#google-signin-btn { display: flex; justify-content: center; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
