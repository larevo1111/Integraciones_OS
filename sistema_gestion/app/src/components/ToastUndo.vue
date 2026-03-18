<template>
  <Teleport to="body">
    <Transition name="toast-slide">
      <div v-if="visible" class="toast-undo">
        <span class="toast-msg">{{ mensaje }}</span>
        <div class="toast-actions">
          <button class="toast-btn-undo" @click="deshacer">Deshacer</button>
          <button class="toast-btn-close" @click="cerrar">
            <span class="material-icons" style="font-size:14px">close</span>
          </button>
        </div>
        <!-- Barra de progreso -->
        <div class="toast-progress" :style="{ width: progreso + '%' }" />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'

const DURACION = 15000  // 15 segundos

const visible  = ref(false)
const mensaje  = ref('')
const progreso = ref(100)

let onUndo     = null
let timer      = null
let progTimer  = null

function mostrar(msg, undoFn) {
  // Si hay uno activo, cerrarlo primero
  limpiar()

  mensaje.value  = msg
  progreso.value = 100
  visible.value  = true
  onUndo         = undoFn

  // Barra de progreso decremental
  const inicio = Date.now()
  progTimer = setInterval(() => {
    const elapsed = Date.now() - inicio
    progreso.value = Math.max(0, 100 - (elapsed / DURACION) * 100)
  }, 100)

  timer = setTimeout(() => cerrar(), DURACION)
}

function deshacer() {
  if (onUndo) onUndo()
  cerrar()
}

function cerrar() {
  visible.value = false
  limpiar()
}

function limpiar() {
  clearTimeout(timer)
  clearInterval(progTimer)
  timer = null
  progTimer = null
  onUndo = null
}

onUnmounted(() => limpiar())

defineExpose({ mostrar })
</script>

<style scoped>
.toast-undo {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  min-width: 280px;
  max-width: 420px;
  background: var(--bg-elevated, #1e1e1e);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  overflow: hidden;
}

.toast-msg {
  flex: 1;
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.toast-btn-undo {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-muted);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm);
  padding: 3px 10px;
  cursor: pointer;
  transition: background 80ms;
  font-family: var(--font-sans);
}
.toast-btn-undo:hover { background: var(--accent-border); }

.toast-btn-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  padding: 2px;
}
.toast-btn-close:hover { color: var(--text-primary); }

/* Barra de progreso */
.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--accent);
  transition: width 100ms linear;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

/* Transición entrada/salida */
.toast-slide-enter-active { transition: opacity 180ms, transform 180ms; }
.toast-slide-leave-active { transition: opacity 150ms, transform 150ms; }
.toast-slide-enter-from   { opacity: 0; transform: translateX(-50%) translateY(12px); }
.toast-slide-leave-to     { opacity: 0; transform: translateX(-50%) translateY(12px); }
</style>
