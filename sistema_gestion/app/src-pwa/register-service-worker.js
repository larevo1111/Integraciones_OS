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

  updated (/* registration */) {
    // Nueva versión disponible — avisar al UI (banner) en lugar de auto-reload.
    // El usuario decide cuándo aplicar (botón "Actualizar" del banner o sidebar).
    console.log('[SW] Nueva versión lista — esperando confirmación del usuario')
    window.dispatchEvent(new CustomEvent('sw-updated'))
  },

  offline () {
    // Sin conexión
  },

  error (err) {
    console.error('[SW] Error:', err)
  }
})
