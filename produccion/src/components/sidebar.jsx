/**
 * Sidebar — 2 niveles visibles + panel flotante lateral para sub-sub-items.
 *  - N1: items principales (Vista general, Solicitudes, ...)
 *  - N2: sub-items con sangría (cuando un N1 es expandible)
 *  - N3: NO viven en el sidebar. Al hacer click en un N2 con "hasFloating"
 *        se abre <FloatingSubmenu /> a la derecha del sidebar (HubSpot-style).
 *
 * El item "Inventarios" (N2) abre un FloatingSubmenu con las fechas
 * de inventario + acción "+ Nuevo inventario".
 */
import { useEffect, useRef, useState, forwardRef } from "react"
import { NavLink, useLocation, useNavigate } from "react-router"
import {
  ClipboardList, LayoutDashboard, Calendar, BookOpen, Settings,
  ChevronsLeft, ChevronsRight, Sun, Moon, ChevronRight, LogOut,
  Package, Boxes, Plus, Calendar as CalIcon,
  Lock, LockOpen, ShieldCheck, RotateCcw, Trash2, RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/lib/theme"
import { auth } from "@/lib/auth"
import { api } from "@/lib/api"
import { FloatingSubmenu } from "./floating-submenu"

const KEY_OPEN = 'sidebar_open_groups'
const KEY_COLLAPSED = 'sidebar_collapsed'

const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
const fmtFechaCorta = (yyyymmdd) => {
  if (!yyyymmdd) return ''
  const [y, m, d] = yyyymmdd.split('-')
  return `${parseInt(d, 10)} ${MESES[parseInt(m, 10) - 1]} ${y}`
}

export function Sidebar({ mobileOpen = false, onCloseMobile }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(KEY_COLLAPSED) === '1')
  const [openGroups, setOpenGroups] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY_OPEN) || '{"Inventarios":true}') }
    catch { return { Inventarios: true } }
  })
  const { theme, toggle } = useTheme()
  const [fechas, setFechas] = useState([])

  // Panel flotante (N3)
  const [floatingOpen, setFloatingOpen] = useState(false)
  const inventariosN2Ref = useRef(null)

  useEffect(() => { localStorage.setItem(KEY_COLLAPSED, collapsed ? '1' : '0') }, [collapsed])
  useEffect(() => { localStorage.setItem(KEY_OPEN, JSON.stringify(openGroups)) }, [openGroups])

  // Cargar fechas
  useEffect(() => {
    api.get('/api/inventario/fechas')
      .then(d => setFechas(Array.isArray(d) ? d : []))
      .catch(() => setFechas([]))
  }, [location.pathname])

  // Cerrar floating cuando la ruta cambia a algo no-inventarios
  useEffect(() => {
    if (!location.pathname.startsWith('/inventarios')) setFloatingOpen(false)
  }, [location.pathname])

  const toggleGroup = (key) => {
    if (collapsed) { setCollapsed(false); setOpenGroups(g => ({ ...g, [key]: true })); return }
    setOpenGroups(g => ({ ...g, [key]: !g[key] }))
  }

  const isInventariosActive = location.pathname.startsWith('/inventarios') || location.pathname === '/catalogo'
  const currentFecha = (location.pathname.match(/\/inventarios\/(\d{4}-\d{2}-\d{2})/) || [])[1]

  const handleClickInventariosN2 = () => {
    setFloatingOpen(v => !v)
  }

  return (
    <>
      <aside
        className={cn(
          "flex flex-col transition-[width,transform] duration-200 shrink-0 border-r",
          collapsed ? "w-12" : "w-56",
          // Móvil: overlay fijo, oculto por defecto
          "max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:w-56 max-md:shadow-xl",
          mobileOpen ? "max-md:translate-x-0" : "max-md:-translate-x-full"
        )}
        style={{ background: 'var(--sb-bg)', borderColor: 'var(--border)' }}
      >
        {/* Logo */}
        <div className="h-14 flex items-center px-3 gap-2.5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="w-7 h-7 rounded-md flex items-center justify-center font-semibold text-[11px] shrink-0"
               style={{ background: 'var(--accent)', color: '#000' }}>
            OS
          </div>
          {!collapsed && <span className="text-[13.5px] font-semibold truncate tracking-tight" style={{ color: 'var(--text)' }}>Producción</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <NavItemN1 to="/" end icon={LayoutDashboard} label="Vista general" collapsed={collapsed} onClick={onCloseMobile} />
          <NavItemN1 to="/solicitudes" icon={ClipboardList} label="Solicitudes" collapsed={collapsed} onClick={onCloseMobile} />
          <NavItemN1 to="/calendario"  icon={Calendar}      label="Calendario"  collapsed={collapsed} onClick={onCloseMobile} />
          <NavItemN1 to="/recetas"     icon={BookOpen}      label="Recetas"     collapsed={collapsed} onClick={onCloseMobile} />

          {/* N1 — Inventarios (expandible con N2) */}
          <GroupHeader
            icon={Package}
            label="Inventarios"
            isOpen={openGroups['Inventarios'] && !collapsed}
            onToggle={() => toggleGroup('Inventarios')}
            collapsed={collapsed}
            isActive={isInventariosActive}
          />
          {openGroups['Inventarios'] && !collapsed && (
            <div className="space-y-px">
              <NavItemN2 to="/catalogo" label="Catálogo" onClick={onCloseMobile} />
              {/* N2 con panel flotante: Inventarios */}
              <NavItemN2Floating
                ref={inventariosN2Ref}
                label="Inventarios"
                isActive={location.pathname.startsWith('/inventarios')}
                isFloatingOpen={floatingOpen}
                onClick={handleClickInventariosN2}
              />
            </div>
          )}

          <NavItemN1 to="/config" icon={Settings} label="Configuración" collapsed={collapsed} onClick={onCloseMobile} />
        </nav>

        {/* Footer */}
        <div className="px-1.5 pb-2 space-y-px border-t pt-2" style={{ borderColor: 'var(--border)' }}>
          {auth.usuario && (
            <div className={cn("flex items-center gap-2 px-2 py-1.5 rounded-md", collapsed && "justify-center")}
                 title={collapsed ? auth.usuario.nombre : undefined}>
              {auth.usuario.foto
                ? <img src={auth.usuario.foto} alt="" className="h-5 w-5 rounded-full shrink-0" />
                : <div className="h-5 w-5 rounded-full text-[10px] flex items-center justify-center shrink-0"
                       style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
                    {auth.usuario.nombre?.[0]?.toUpperCase() || '?'}
                  </div>}
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] truncate" style={{ color: 'var(--text)' }}>{auth.usuario.nombre}</div>
                  <div className="text-[10px] truncate" style={{ color: 'var(--text-tertiary)' }}>Nivel {auth.usuario.nivel}</div>
                </div>
              )}
              {!collapsed && (
                <button
                  onClick={() => { auth.logout(); window.location.reload() }}
                  className="hover:text-[var(--error)] cursor-pointer transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                  title="Cerrar sesión"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
          <FooterBtn icon={theme === 'dark' ? Sun : Moon} label={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'} onClick={toggle} collapsed={collapsed} />
          <FooterBtn icon={collapsed ? ChevronsRight : ChevronsLeft} label="Colapsar" onClick={() => setCollapsed(c => !c)} collapsed={collapsed} />
          {!collapsed && (
            <div className="px-2 pt-1 text-[10px] tabular-nums" style={{ color: 'var(--text-tertiary)' }}>
              v{typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '?'}
            </div>
          )}
        </div>
      </aside>

      {/* Panel flotante para N3: fechas de inventario */}
      <FloatingSubmenu
        open={floatingOpen}
        onClose={() => setFloatingOpen(false)}
        anchorRef={inventariosN2Ref}
        title="Inventarios"
        groups={[
          {
            title: 'Por fecha',
            items: fechas.map(f => ({
              to: `/inventarios/${f.fecha_inventario}`,
              label: fmtFechaCorta(f.fecha_inventario),
              icon: CalIcon,
              monospace: true,
              active: currentFecha === f.fecha_inventario,
              onClick: () => setFloatingOpen(false),
              actionsMenu: [
                { label: 'Calcular teórico',  icon: RefreshCw,    onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=calcular-teorico`) } },
                { label: 'Cerrar conteo',     icon: Lock,         onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=cerrar-conteo`) } },
                { label: 'Reabrir conteo',    icon: LockOpen,     onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=reabrir-conteo`) } },
                { label: 'Cerrar inventario', icon: ShieldCheck,  onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=cerrar-inv`) }, variant: 'warn' },
                { label: 'Reiniciar conteos', icon: RotateCcw,    onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=reiniciar`) }, variant: 'danger' },
                { label: 'Eliminar inventario', icon: Trash2,     onClick: () => { setFloatingOpen(false); navigate(`/inventarios/${f.fecha_inventario}?accion=eliminar`) }, variant: 'danger' },
              ],
            })),
          },
          {
            items: [
              {
                onClick: () => { setFloatingOpen(false); navigate('/inventarios/nuevo') },
                label: 'Nuevo inventario',
                icon: Plus,
                rightSlot: null,
              },
            ],
          },
        ]}
      />
    </>
  )
}

// ── Subcomponentes ──

function NavItemN1({ to, end, icon: Icon, label, collapsed, onClick }) {
  return (
    <NavLink
      to={to} end={end}
      onClick={onClick}
      className={cn("group flex items-center gap-2.5 h-7 rounded-md text-[13px] transition-colors cursor-pointer",
        collapsed && "justify-center")}
      style={({ isActive }) => ({
        paddingLeft: collapsed ? 0 : 8, paddingRight: 8,
        color: isActive ? 'var(--text)' : 'var(--text-secondary)',
        background: isActive ? 'var(--accent-muted)' : 'transparent',
        fontWeight: isActive ? 500 : 400,
      })}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  )
}

function GroupHeader({ icon: Icon, label, isOpen, onToggle, collapsed, isActive }) {
  return (
    <button
      onClick={onToggle}
      className={cn("w-full flex items-center gap-2.5 h-7 rounded-md text-[13px] transition-colors cursor-pointer",
        collapsed && "justify-center")}
      style={{
        paddingLeft: collapsed ? 0 : 8, paddingRight: 8,
        color: isActive ? 'var(--text)' : 'var(--text-secondary)',
        background: isActive && !isOpen ? 'var(--accent-muted)' : 'transparent',
        fontWeight: isActive ? 500 : 400,
      }}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
      {!collapsed && (
        <>
          <span className="truncate flex-1 text-left">{label}</span>
          <ChevronRight className={cn("h-3 w-3 shrink-0 transition-transform duration-150", isOpen && "rotate-90")} />
        </>
      )}
    </button>
  )
}

function NavItemN2({ to, label, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className="flex items-center h-6 rounded-md text-[12px] transition-colors cursor-pointer"
      style={({ isActive }) => ({
        paddingLeft: 24, paddingRight: 8,
        color: isActive ? 'var(--text)' : 'var(--text-secondary)',
        background: isActive ? 'var(--accent-muted)' : 'transparent',
        fontWeight: isActive ? 500 : 400,
      })}
    >
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

// N2 que abre panel flotante al clicar (HubSpot-like con chevron ">")
const NavItemN2Floating = forwardRef(function NavItemN2Floating({ label, isActive, isFloatingOpen, onClick }, ref) {
  return (
    <button
      ref={ref}
      onClick={onClick}
      className="w-full flex items-center h-6 rounded-md text-[12px] transition-colors cursor-pointer"
      style={{
        paddingLeft: 24, paddingRight: 8,
        color: isActive || isFloatingOpen ? 'var(--text)' : 'var(--text-secondary)',
        background: (isActive && !isFloatingOpen) ? 'var(--accent-muted)' : (isFloatingOpen ? 'var(--bg-hover)' : 'transparent'),
        fontWeight: isActive ? 500 : 400,
      }}
    >
      <span className="truncate flex-1 text-left">{label}</span>
      <ChevronRight className="h-3 w-3 shrink-0" strokeWidth={1.75} />
    </button>
  )
})

function FooterBtn({ icon: Icon, label, onClick, collapsed }) {
  return (
    <button
      onClick={onClick}
      className={cn("w-full flex items-center gap-2.5 h-7 rounded-md text-[12px] transition-colors cursor-pointer",
        collapsed && "justify-center")}
      style={{ paddingLeft: collapsed ? 0 : 8, paddingRight: 8, color: 'var(--text-secondary)' }}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  )
}
