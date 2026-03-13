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
      { path: 'ventas/resumen-facturacion',                      component: () => import('pages/ventas/ResumenFacturacionPage.vue') },
      { path: 'ventas/detalle-mes/:mes',                         component: () => import('pages/ventas/DetalleFacturacionMesPage.vue') },
      { path: 'ventas/detalle-cliente/:mes/:id_cliente',         component: () => import('pages/ventas/DetalleClienteMesPage.vue') },
      { path: 'ventas/detalle-canal/:mes/:canal',                component: () => import('pages/ventas/DetalleCanalMesPage.vue') },
      { path: 'ventas/detalle-producto/:mes/:cod_articulo',      component: () => import('pages/ventas/DetalleProductoMesPage.vue') },
      { path: 'ventas/detalle-factura/:id_interno/:id_numeracion', component: () => import('pages/ventas/DetalleFacturaPage.vue') },
      { path: 'ventas/resumen-remisiones',  component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/cartera/:id_cliente',           component: () => import('pages/ventas/DetalleCarteraClientePage.vue') },
      { path: 'ventas/consignacion',                  component: () => import('pages/ventas/ConsignacionPage.vue') },
      { path: 'ventas/consignacion-cliente/:id_cliente', component: () => import('pages/ventas/ConsignacionClientePage.vue') },
      { path: 'ventas/consignacion-orden/:id_orden',  component: () => import('pages/ventas/DetalleConsignacionPage.vue') },
      { path: 'ventas/pedidos-pendientes',  component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/facturas',            component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/remisiones',          component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/cotizaciones',        component: () => import('pages/PlaceholderPage.vue') },
      { path: 'ventas/cartera',            component: () => import('pages/ventas/CarteraPage.vue') },

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
