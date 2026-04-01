const routes = [
  { path: '/login', component: () => import('pages/LoginPage.vue') },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '',               redirect: '/tareas' },
      { path: 'tareas',         component: () => import('pages/TareasPage.vue') },
      { path: 'equipo',         component: () => import('pages/TareasPage.vue'), props: { soloMias: false } },
      { path: 'jornadas',       component: () => import('pages/EquipoPage.vue') },
      { path: 'proyectos-tabla', component: () => import('pages/ItemsTablePage.vue'), props: { tipo: 'proyecto' } },
      { path: 'dificultades',   component: () => import('pages/ItemsTablePage.vue'), props: { tipo: 'dificultad' } },
      { path: 'compromisos',    component: () => import('pages/ItemsTablePage.vue'), props: { tipo: 'compromiso' } },
      { path: 'ideas',          component: () => import('pages/ItemsTablePage.vue'), props: { tipo: 'idea' } },
    ]
  },
  { path: '/:catchAll(.*)*', redirect: '/tareas' }
]
export default routes
