/**
 * Sidebar — 3 niveles tipo Linear/HubSpot:
 *  - N1: items principales (Vista general, Solicitudes, ...)
 *  - N2: sub-items con sangría (cuando un N1 es expandible)
 *  - N3: items dinámicos con más sangría (las fechas de inventarios)
 *
 * El item "Inventarios" expandido muestra dos N2: "Catálogo" y "Inventarios"
 * (este último también expandible para ver las fechas).
 */
import { useEffect, useState } from "react"
import { NavLink, useLocation } from "react-router"
import {
  ClipboardList, LayoutDashboard, Calendar, BookOpen, Settings,
  ChevronsLeft, ChevronsRight, Sun, Moon, ChevronRight, LogOut,
  Package, Boxes, Plus,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/lib/theme"
import { auth } from "@/lib/auth"
import { api } from "@/lib/api"

const KEY_OPEN = 'sidebar_open_groups'
const KEY_COLLAPSED = 'sidebar_collapsed'

const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
const fmtFechaCorta = (yyyymmdd) => {
  if (!yyyymmdd) return ''
  const [y, m, d] = yyyymmdd.split('-')
  return `${parseInt(d, 10)} ${MESES[parseInt(m, 10) - 1]} ${y}`
}

export function Sidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(KEY_COLLAPSED) === '1')
  const [openGroups, setOpenGroups] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY_OPEN) || '{"Inventarios":true,"InvFechas":true}') }
    catch { return { Inventarios: true, InvFechas: true } }
  })
  const { theme, toggle } = useTheme()
  const [fechas, setFechas] = useState([])

  useEffect(() => { localStorage.setItem(KEY_COLLAPSED, collapsed ? '1' : '0') }, [collapsed])
  useEffect(() => { localStorage.setItem(KEY_OPEN, JSON.stringify(openGroups)) }, [openGroups])

  // Cargar fechas de inventarios (refresh cuando navegamos dentro)
  useEffect(() => {
    api.get('/api/inventario/fechas')
      .then(d => setFechas(Array.isArray(d) ? d : []))
      .catch(() => setFechas([]))
  }, [location.pathname])

  const toggleGroup = (key) => {
    if (collapsed) { setCollapsed(false); setOpenGroups(g => ({ ...g, [key]: true })); return }
    setOpenGroups(g => ({ ...g, [key]: !g[key] }))
  }

  const isInventariosActive = location.pathname.startsWith('/inventarios') || location.pathname === '/catalogo'

  return (
    <aside
      className={cn(
        "flex flex-col transition-[width] duration-200 shrink-0 border-r",
        collapsed ? "w-12" : "w-56"
      )}
      style={{ background: 'var(--sb-bg)', borderColor: 'var(--border)' }}
    >
      {/* Logo */}
      <div className="h-12 flex items-center px-3 gap-2 shrink-0">
        <div className="w-6 h-6 rounded bg-[var(--accent)] flex items-center justify-center text-black font-semibold text-[11px] shrink-0">
          OS
        </div>
        {!collapsed && <span className="text-[13px] font-medium truncate" style={{ color: 'var(--text)' }}>Producción</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-1.5 space-y-px overflow-y-auto">
        {/* N1 — Vista general */}
        <NavItemN1 to="/" end icon={LayoutDashboard} label="Vista general" collapsed={collapsed} />
        <NavItemN1 to="/solicitudes" icon={ClipboardList} label="Solicitudes" collapsed={collapsed} />
        <NavItemN1 to="/calendario"  icon={Calendar}      label="Calendario"  collapsed={collapsed} />
        <NavItemN1 to="/recetas"     icon={BookOpen}      label="Recetas"     collapsed={collapsed} />

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
            {/* N2 — Catálogo */}
            <NavItemN2 to="/catalogo" label="Catálogo" />

            {/* N2 — Inventarios (expandible a N3 fechas) */}
            <GroupHeaderN2
              label="Inventarios"
              isOpen={openGroups['InvFechas']}
              onToggle={() => toggleGroup('InvFechas')}
              isActive={location.pathname.startsWith('/inventarios')}
            />
            {openGroups['InvFechas'] && (
              <div className="space-y-px">
                {fechas.map(f => (
                  <NavItemN3 key={f.fecha_inventario} to={`/inventarios/${f.fecha_inventario}`} label={fmtFechaCorta(f.fecha_inventario)} />
                ))}
                {!fechas.length && (
                  <div className="text-[10px] py-1 italic" style={{ color: 'var(--text-tertiary)', paddingLeft: 38 }}>
                    Sin inventarios
                  </div>
                )}
                <NavLink
                  to="/inventarios/nuevo"
                  className="flex items-center gap-1.5 h-6 rounded-md text-[11px] transition-colors cursor-pointer"
                  style={{ paddingLeft: 38, paddingRight: 8, color: 'var(--text-tertiary)' }}
                >
                  <Plus className="h-3 w-3 shrink-0" strokeWidth={1.75} />
                  <span>Nuevo inventario</span>
                </NavLink>
              </div>
            )}
          </div>
        )}

        {/* N1 — Configuración */}
        <NavItemN1 to="/config" icon={Settings} label="Configuración" collapsed={collapsed} />
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
      </div>
    </aside>
  )
}

// ── Subcomponentes ──

function NavItemN1({ to, end, icon: Icon, label, collapsed }) {
  return (
    <NavLink
      to={to} end={end}
      className={({ isActive }) => cn(
        "group flex items-center gap-2.5 h-7 rounded-md text-[13px] transition-colors cursor-pointer",
        collapsed && "justify-center"
      )}
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
      className={cn(
        "w-full flex items-center gap-2.5 h-7 rounded-md text-[13px] transition-colors cursor-pointer",
        collapsed && "justify-center"
      )}
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

function NavItemN2({ to, label }) {
  return (
    <NavLink
      to={to}
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

function GroupHeaderN2({ label, isOpen, onToggle, isActive }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center h-6 rounded-md text-[12px] transition-colors cursor-pointer"
      style={{
        paddingLeft: 24, paddingRight: 8,
        color: isActive ? 'var(--text)' : 'var(--text-secondary)',
        background: isActive && !isOpen ? 'var(--accent-muted)' : 'transparent',
        fontWeight: isActive ? 500 : 400,
      }}
    >
      <span className="truncate flex-1 text-left">{label}</span>
      <ChevronRight className={cn("h-3 w-3 shrink-0 transition-transform duration-150", isOpen && "rotate-90")} />
    </button>
  )
}

function NavItemN3({ to, label }) {
  return (
    <NavLink
      to={to}
      className="flex items-center h-6 rounded-md text-[11px] transition-colors cursor-pointer"
      style={({ isActive }) => ({
        paddingLeft: 38, paddingRight: 8,
        color: isActive ? 'var(--accent)' : 'var(--text-tertiary)',
        background: isActive ? 'var(--accent-muted)' : 'transparent',
        fontFamily: "var(--font-mono, 'Fragment Mono', 'JetBrains Mono', monospace)",
      })}
    >
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

function FooterBtn({ icon: Icon, label, onClick, collapsed }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2.5 h-7 rounded-md text-[12px] transition-colors cursor-pointer",
        collapsed && "justify-center"
      )}
      style={{
        paddingLeft: collapsed ? 0 : 8, paddingRight: 8,
        color: 'var(--text-secondary)',
      }}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  )
}
