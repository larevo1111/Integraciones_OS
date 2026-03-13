import MainLayout from 'layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue')
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '',           redirect: '/dashboard' },
      { path: 'dashboard',  component: () => import('pages/DashboardPage.vue') },
      { path: 'agentes',    component: () => import('pages/AgentesPage.vue') },
      { path: 'tipos',      component: () => import('pages/TiposPage.vue') },
      { path: 'logs',       component: () => import('pages/LogsPage.vue') },
      { path: 'playground', component: () => import('pages/PlaygroundPage.vue') },
      { path: 'usuarios',   component: () => import('pages/UsuariosPage.vue') },
      { path: 'contextos',  component: () => import('pages/ContextosPage.vue') },
    ]
  },
  { path: '/:catchAll(.*)*', redirect: '/dashboard' }
]

export default routes
