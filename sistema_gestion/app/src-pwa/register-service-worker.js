import { register } from 'register-service-worker'

register(process.env.SERVICE_WORKER_FILE, {
  ready (/* registration */) {
    // SW activo y listo
  },

  registered (registration) {
    // Verificar actualizaciones cada 5 minutos
    setInterval(() => { registration.update() }, 5 * 60 * 1000)
  },

  cached (/* registration */) {
    // Contenido cacheado para uso offline
  },

  updatefound (/* registration */) {
    console.log('[SW] Nueva versión descargando...')
  },

  updated (registration) {
    // Nueva versión disponible — recargar automáticamente
    console.log('[SW] Nueva versión lista — recargando...')
    if (registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
    window.location.reload()
  },

  offline () {
    // Sin conexión
  },

  error (err) {
    console.error('[SW] Error:', err)
  }
})
