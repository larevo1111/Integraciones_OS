import MainLayout from 'layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '',        redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('pages/DashboardPage.vue') },

      // Terceros
      { path: 'terceros/clientes',    component: () => import('pages/PlaceholderPage.vue') },
      { path: 'terceros/proveedores', component: () => import('pages/PlaceholderPage.vue') },
      { path: 'terceros/empleados',   component: () => import('pages/PlaceholderPage.vue') },

      // Ventas
      { path: 'ventas/resumen-facturacion',  component: () => import('pages/ventas/ResumenFacturacionPage.vue') },
      { path: 'ventas/detalle-mes/:mes',     component: () => import('pages/ventas/DetalleFacturacionMesPage.vue') },
      { path: 'ventas/resumen-remisiones',  component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/consignacion',        component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/pedidos-pendientes',  component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/facturas',            component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/remisiones',          component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/cotizaciones',        component: () => import('pages/PlaceholderPage.vue') },

      // Tareas
      { path: 'tareas',       component: () => import('pages/PlaceholderPage.vue') },
      { path: 'tareas/nueva', component: () => import('pages/PlaceholderPage.vue') },

      // CRM
      { path: 'crm/oportunidades', component: () => import('pages/PlaceholderPage.vue') },
      { path: 'crm/tareas',        component: () => import('pages/PlaceholderPage.vue') },
      { path: 'crm/notas',         component: () => import('pages/PlaceholderPage.vue') },

      // Producción
      { path: 'produccion/resumen', component: () => import('pages/PlaceholderPage.vue') },
      { path: 'produccion/ordenes', component: () => import('pages/PlaceholderPage.vue') },

      // Compras
      { path: 'compras/resumen-facturas',    component: () => import('pages/PlaceholderPage.vue') },
      { path: 'compras/resumen-remisiones',  component: () => import('pages/PlaceholderPage.vue') },
      { path: 'compras/ordenes',             component: () => import('pages/PlaceholderPage.vue') },
      { path: 'compras/remisiones',          component: () => import('pages/PlaceholderPage.vue') },
      { path: 'compras/facturas',            component: () => import('pages/PlaceholderPage.vue') },

      // Herramientas
      { path: 'herramientas/metabase', component: () => import('pages/PlaceholderPage.vue') },
      { path: 'herramientas/ia',       component: () => import('pages/PlaceholderPage.vue') },
    ]
  },
  { path: '/:catchAll(.*)*', component: () => import('pages/ErrorNotFound.vue') }
]

export default routes
