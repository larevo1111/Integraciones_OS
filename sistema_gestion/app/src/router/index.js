import { route } from 'quasar/wrappers'
import { createRouter, createWebHashHistory } from 'vue-router'
import routes from './routes'

export default route(function () {
  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createWebHashHistory()
  })

  Router.beforeEach((to) => {
    const token = localStorage.getItem('gestion_jwt')
    if (to.meta.requiresAuth && !token) return '/login'
    if (to.path === '/login' && token) {
      // Solo redirigir si el token es FINAL (no temporal)
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.tipo === 'final') return '/tareas'
        // Token temporal: borrarlo y quedarse en login
        localStorage.removeItem('gestion_jwt')
        localStorage.removeItem('gestion_usuario')
        localStorage.removeItem('gestion_empresa')
      } catch { localStorage.removeItem('gestion_jwt') }
    }
  })

  return Router
})
