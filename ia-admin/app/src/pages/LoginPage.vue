<template>
  <div class="login-shell">
    <div class="login-card">

      <!-- Logo -->
      <div class="login-logo">
        <div class="login-logo-icon">IA</div>
        <div class="login-logo-text">Origen Silvestre</div>
        <div class="login-logo-sub">Panel de Administración · IA</div>
      </div>

      <!-- PASO 1: Botón Google -->
      <div v-if="paso === 1 && !cargando" class="login-google-wrap">
        <GoogleLogin :callback="handleCallback" :buttonConfig="{
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          width: 300,
          locale: 'es'
        }" />
      </div>

      <!-- PASO 2: Selección de empresa (múltiples empresas) -->
      <div v-if="paso === 2 && !cargando" class="empresa-selector">
        <p class="empresa-selector-hint">Selecciona la empresa con la que deseas acceder:</p>
        <div class="empresa-grid">
          <button
            v-for="emp in empresasDisponibles"
            :key="emp.uid"
            class="empresa-card"
            @click="seleccionarEmpresa(emp.uid)"
          >
            <div class="empresa-badge">{{ emp.siglas }}</div>
            <div class="empresa-info">
              <span class="empresa-nombre">{{ emp.nombre }}</span>
              <span class="empresa-rol">{{ emp.rol }}</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Cargando -->
      <div v-if="cargando" class="login-loading">
        <div class="loading-dots"><div /><div /><div /></div>
        <span>{{ mensajeCarga }}</span>
      </div>

      <!-- Error -->
      <div v-if="error" class="login-error">
        {{ error }}
      </div>

      <div class="login-footer">Acceso restringido · Solo usuarios autorizados</div>
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
const paso      = ref(1)
const mensajeCarga       = ref('Verificando identidad...')
const empresasDisponibles = ref([])

async function handleCallback(response) {
  if (!response?.credential) return
  cargando.value = true
  error.value    = ''
  mensajeCarga.value = 'Verificando identidad...'
  try {
    const data = await authStore.autenticarGoogle(response.credential)

    if (data.tipo === 'final') {
      // Empresa única o ya seleccionada — ir al dashboard
      router.push('/')
    } else if (data.tipo === 'temporal') {
      // Múltiples empresas — mostrar selector
      empresasDisponibles.value = data.empresas || []
      paso.value = 2
    }
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

async function seleccionarEmpresa(empresaUid) {
  cargando.value = true
  error.value    = ''
  mensajeCarga.value = 'Ingresando...'
  try {
    await authStore.seleccionarEmpresa(empresaUid)
    router.push('/')
  } catch (e) {
    error.value = e.message
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

/* Selector de empresa */
.empresa-selector {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empresa-selector-hint {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  margin: 0;
}

.empresa-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empresa-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background: transparent;
  cursor: pointer;
  transition: background 70ms, border-color 70ms;
  text-align: left;
  width: 100%;
}

.empresa-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--accent);
}

.empresa-badge {
  width: 36px; height: 36px;
  border-radius: var(--radius-md);
  background: var(--accent-muted);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.empresa-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.empresa-nombre {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.empresa-rol {
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: capitalize;
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
