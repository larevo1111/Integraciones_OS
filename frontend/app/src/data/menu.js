/**
 * Datos del menú — cargados desde sys_menu en Hostinger (Ori_Sil_2)
 * Estructura: categorías raíz con sus hijos
 */
export const MENU = [
  {
    uid: 'terceros', titulo: 'Terceros', icono: 'Users', color: '#60a5fa',
    hijos: [
      { uid: 'terceros_clientes',    titulo: 'Clientes',       icono: 'UserCheck',  ruta: '/terceros/clientes' },
      { uid: 'terceros_proveedores', titulo: 'Proveedores',    icono: 'Truck',      ruta: '/terceros/proveedores' },
      { uid: 'terceros_empleados',   titulo: 'Empleados',      icono: 'Briefcase',  ruta: '/terceros/empleados' },
    ]
  },
  {
    uid: 'ventas', titulo: 'Ventas', icono: 'TrendingUp', color: '#4ade80',
    hijos: [
      { uid: 'ventas_resumen_fac',  titulo: 'Resumen Facturación',        icono: 'BarChart2',   ruta: '/ventas/resumen-facturacion' },
      { uid: 'ventas_resumen_rem',  titulo: 'Resumen Remisiones',         icono: 'BarChart',    ruta: '/ventas/resumen-remisiones' },
      { uid: 'ventas_consignacion', titulo: 'Mercancía en consignación',  icono: 'PackageCheck',ruta: '/ventas/consignacion' },
      { uid: 'ventas_pedidos',      titulo: 'Pedidos pendientes',         icono: 'Clock',       ruta: '/ventas/pedidos-pendientes' },
      { uid: 'ventas_facturas',     titulo: 'Facturas',                   icono: 'FileText',    ruta: '/ventas/facturas' },
      { uid: 'ventas_remisiones',   titulo: 'Remisiones',                 icono: 'FileOutput',  ruta: '/ventas/remisiones' },
      { uid: 'ventas_cotizaciones', titulo: 'Cotizaciones',               icono: 'FilePlus',    ruta: '/ventas/cotizaciones' },
    ]
  },
  {
    uid: 'tareas', titulo: 'Tareas', icono: 'CheckSquare', color: '#f59e0b',
    hijos: [
      { uid: 'tareas_registrar', titulo: 'Registrar tarea', icono: 'PlusCircle',   ruta: '/tareas/nueva' },
      { uid: 'tareas_semana',    titulo: 'Esta semana',     icono: 'CalendarDays', ruta: '/tareas?filtro=semana' },
      { uid: 'tareas_hoy',       titulo: 'Hoy',             icono: 'Sun',          ruta: '/tareas?filtro=hoy' },
      { uid: 'tareas_manana',    titulo: 'Mañana',          icono: 'Sunrise',      ruta: '/tareas?filtro=manana' },
      { uid: 'tareas_ayer',      titulo: 'Ayer',            icono: 'ChevronLeft',  ruta: '/tareas?filtro=ayer' },
      { uid: 'tareas_mias',      titulo: 'Todas las mías',  icono: 'User',         ruta: '/tareas?filtro=mias' },
      { uid: 'tareas_equipo',    titulo: 'Todo el equipo',  icono: 'Users',        ruta: '/tareas?filtro=equipo' },
    ]
  },
  {
    uid: 'crm', titulo: 'CRM', icono: 'Target', color: '#a78bfa',
    hijos: [
      { uid: 'crm_oportunidades', titulo: 'Oportunidades', icono: 'Zap',           ruta: '/crm/oportunidades' },
      { uid: 'crm_tareas',        titulo: 'Tareas CRM',    icono: 'ClipboardList', ruta: '/crm/tareas' },
      { uid: 'crm_notas',         titulo: 'Notas',         icono: 'StickyNote',    ruta: '/crm/notas' },
    ]
  },
  {
    uid: 'produccion', titulo: 'Producción', icono: 'Factory', color: '#fb923c',
    hijos: [
      { uid: 'prod_resumen', titulo: 'Resumen producción',   icono: 'BarChart2',    ruta: '/produccion/resumen' },
      { uid: 'prod_ordenes', titulo: 'Órdenes de producción',icono: 'ClipboardList',ruta: '/produccion/ordenes' },
    ]
  },
  {
    uid: 'compras', titulo: 'Compras', icono: 'ShoppingCart', color: '#34d399',
    hijos: [
      { uid: 'compras_resumen_fac', titulo: 'Resumen facturas compras',   icono: 'BarChart2',  ruta: '/compras/resumen-facturas' },
      { uid: 'compras_resumen_rem', titulo: 'Resumen remisiones compra',  icono: 'BarChart',   ruta: '/compras/resumen-remisiones' },
      { uid: 'compras_ordenes',     titulo: 'Órdenes de compra',          icono: 'ShoppingBag',ruta: '/compras/ordenes' },
      { uid: 'compras_remisiones',  titulo: 'Remisiones de compra',       icono: 'FileOutput', ruta: '/compras/remisiones' },
      { uid: 'compras_facturas',    titulo: 'Facturas de compra',         icono: 'FileText',   ruta: '/compras/facturas' },
    ]
  },
  {
    uid: 'herramientas', titulo: 'Herramientas', icono: 'Wrench', color: '#94a3b8',
    hijos: [
      { uid: 'herr_metabase', titulo: 'Análisis de datos',   icono: 'PieChart', ruta: '/herramientas/metabase' },
      { uid: 'herr_ia',       titulo: 'Hablar con agente IA',icono: 'Bot',      ruta: '/herramientas/ia' },
    ]
  },
]
