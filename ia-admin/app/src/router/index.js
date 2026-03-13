import { route } from 'quasar/wrappers'
import { createRouter, createMemoryHistory, createWebHistory, createWebHashHistory } from 'vue-router'
import routes from './routes'

export default route(function () {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : (process.env.VUE_ROUTER_MODE === 'history' ? createWebHistory : createWebHashHistory)

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(process.env.VUE_ROUTER_BASE)
  })

  Router.beforeEach((to) => {
    let token = localStorage.getItem('ia_jwt')

    // Si hay token, verificar que no esté expirado (client-side decode)
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          // Expirado — limpiar localStorage y tratar como sin sesión
          localStorage.removeItem('ia_jwt')
          localStorage.removeItem('ia_usuario')
          localStorage.removeItem('ia_empresa')
          token = null
        }
      } catch {
        // Token malformado — limpiar
        localStorage.removeItem('ia_jwt')
        localStorage.removeItem('ia_usuario')
        localStorage.removeItem('ia_empresa')
        token = null
      }
    }

    if (to.meta.requiresAuth && !token) return '/login'
    if (to.path === '/login' && token) return '/dashboard'
  })

  return Router
})
