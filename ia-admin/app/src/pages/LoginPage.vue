<template>
  <div class="login-shell">
    <div class="login-card">

      <!-- Logo -->
      <div class="login-logo">
        <div class="login-logo-icon">IA</div>
        <div class="login-logo-text">Origen Silvestre</div>
        <div class="login-logo-sub">Panel de Administración · IA</div>
      </div>

      <!-- Botón Google -->
      <div v-if="!cargando" class="login-google-wrap">
        <GoogleLogin :callback="handleCallback" :buttonConfig="{
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          width: 300,
          locale: 'es'
        }" />
      </div>

      <!-- Cargando -->
      <div v-else class="login-loading">
        <div class="loading-dots"><div /><div /><div /></div>
        <span>Verificando identidad...</span>
      </div>

      <!-- Error -->
      <div v-if="error" class="login-error">
        {{ error }}
      </div>

      <div class="login-footer">🔒 Acceso restringido · Solo usuarios autorizados</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { GoogleLogin } from 'vue3-google-login'
import { useAuthStore } from 'src/stores/authStore'

const router    = useRouter()
const authStore = useAuthStore()
const cargando  = ref(false)
const error     = ref('')

async function handleCallback(response) {
  if (!response?.credential) return
  cargando.value = true
  error.value    = ''
  try {
    await authStore.autenticarGoogle(response.credential)
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.login-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: var(--radius-2xl);
  padding: 40px 36px;
  width: 380px;
  max-width: 92vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  box-shadow: var(--shadow-lg);
}

.login-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.login-logo-icon {
  width: 52px; height: 52px;
  border-radius: var(--radius-xl);
  background: var(--accent);
  color: white;
  font-size: 16px;
  font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  letter-spacing: 0.02em;
  margin-bottom: 4px;
}

.login-logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.login-logo-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
}

.login-google-wrap {
  display: flex;
  justify-content: center;
}

.login-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 13px;
}

.login-error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid rgba(220,38,38,0.15);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 13px;
  text-align: center;
  width: 100%;
}

.login-footer {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* Loading dots */
.loading-dots { display: flex; gap: 5px; }
.loading-dots div {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: bounce 1.2s infinite;
}
.loading-dots div:nth-child(2) { animation-delay: 0.2s; }
.loading-dots div:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
