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
    if (to.path === '/login' && token) return '/tareas'
  })

  return Router
})
