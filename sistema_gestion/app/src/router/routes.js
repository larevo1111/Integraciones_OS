const routes = [
  { path: '/login', component: () => import('pages/LoginPage.vue') },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '',        redirect: '/tareas' },
      { path: 'tareas',  component: () => import('pages/TareasPage.vue') },
      { path: 'equipo',  component: () => import('pages/EquipoPage.vue') },
      { path: 'dificultades',  component: () => import('pages/DificultadesPage.vue') },
      { path: 'dificultades/:id', component: () => import('pages/DetalleDificultadPage.vue') },
      { path: 'ideas',   component: () => import('pages/IdeasPage.vue') },
      { path: 'ideas/:id', component: () => import('pages/DetalleIdeaPage.vue') },
      { path: 'pendientes', component: () => import('pages/PendientesPage.vue') },
      { path: 'pendientes/:id', component: () => import('pages/DetallePendientePage.vue') },
      { path: 'informes', component: () => import('pages/InformesPage.vue') },
      { path: 'informes/:id', component: () => import('pages/DetalleInformePage.vue') }
    ]
  },
  { path: '/:catchAll(.*)*', redirect: '/tareas' }
]
export default routes
