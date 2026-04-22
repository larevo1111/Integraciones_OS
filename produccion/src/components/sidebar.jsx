import { useEffect, useState } from "react"
import { NavLink } from "react-router"
import {
  ClipboardList, LayoutDashboard, Calendar, BookOpen, Settings,
  ChevronsLeft, ChevronsRight, Sun, Moon, ChevronRight,
  Package, Boxes, EyeOff, MessageSquare, AlertTriangle,
  RefreshCw, Sparkles, FileText, Lock, ListChecks,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/lib/theme"

const navItems = [
  { to: "/", label: "Vista general", icon: LayoutDashboard },
  { to: "/solicitudes", label: "Solicitudes", icon: ClipboardList },
  { to: "/calendario", label: "Calendario", icon: Calendar },
  { to: "/recetas", label: "Recetas", icon: BookOpen },
  {
    label: "Inventarios", icon: Package,
    children: [
      { to: "/inventarios/conteo",        label: "Conteo físico",  icon: ListChecks },
      { to: "/inventarios/lista",         label: "Inventarios",    icon: Boxes },
      { to: "/inventarios/catalogo",      label: "Catálogo",       icon: BookOpen },
      { to: "/inventarios/excluidos",     label: "Excluidos",      icon: EyeOff },
      { to: "/inventarios/observaciones", label: "Observaciones",  icon: MessageSquare },
      { to: "/inventarios/ops-revisar",   label: "OPs a revisar",  icon: AlertTriangle },
      { to: "/inventarios/sync-effi",     label: "Sync Effi",      icon: RefreshCw },
      { to: "/inventarios/analisis-ia",   label: "Análisis IA",    icon: Sparkles },
      { to: "/inventarios/informes",      label: "Informes",       icon: FileText },
      { to: "/inventarios/politicas",     label: "Políticas",      icon: Lock },
    ],
  },
  { to: "/config", label: "Configuración", icon: Settings },
]

const KEY_OPEN = 'sidebar_open_groups'
const KEY_COLLAPSED = 'sidebar_collapsed'

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(KEY_COLLAPSED) === '1')
  const [openGroups, setOpenGroups] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY_OPEN) || '{}') }
    catch { return {} }
  })
  const { theme, toggle } = useTheme()

  useEffect(() => { localStorage.setItem(KEY_COLLAPSED, collapsed ? '1' : '0') }, [collapsed])
  useEffect(() => { localStorage.setItem(KEY_OPEN, JSON.stringify(openGroups)) }, [openGroups])

  const toggleGroup = (label) => {
    if (collapsed) { setCollapsed(false); setOpenGroups(g => ({ ...g, [label]: true })); return }
    setOpenGroups(g => ({ ...g, [label]: !g[label] }))
  }

  return (
    <aside
      className={cn(
        "flex flex-col transition-[width] duration-200 shrink-0 border-r border-border",
        collapsed ? "w-12" : "w-52"
      )}
      style={{ background: 'var(--color-sidebar)' }}
    >
      {/* Logo */}
      <div className="h-12 flex items-center px-3 gap-2 shrink-0">
        <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-primary-foreground font-semibold text-[11px] shrink-0">
          OS
        </div>
        {!collapsed && <span className="text-[13px] font-medium truncate">Producción</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-1.5 space-y-0.5 overflow-y-auto">
        {navItems.map((item, idx) => {
          if (item.children) {
            const isOpen = openGroups[item.label] && !collapsed
            const Icon = item.icon
            return (
              <div key={idx}>
                <button
                  onClick={() => toggleGroup(item.label)}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-2 h-7 rounded-md text-[13px] cursor-pointer transition-colors",
                    "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                    collapsed && "justify-center"
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
                  {!collapsed && (
                    <>
                      <span className="truncate flex-1 text-left">{item.label}</span>
                      <ChevronRight
                        className={cn("h-3 w-3 shrink-0 transition-transform duration-150", isOpen && "rotate-90")}
                      />
                    </>
                  )}
                </button>
                {isOpen && (
                  <div className="ml-3 mt-0.5 space-y-0.5 border-l border-border/50 pl-1.5">
                    {item.children.map(child => {
                      const ChildIcon = child.icon
                      return (
                        <NavLink
                          key={child.to}
                          to={child.to}
                          className={({ isActive }) => cn(
                            "flex items-center gap-2 px-2 h-6 rounded-md text-[12px] transition-colors cursor-pointer",
                            isActive
                              ? "bg-accent text-foreground"
                              : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                          )}
                        >
                          {ChildIcon && <ChildIcon className="h-3 w-3 shrink-0" strokeWidth={1.75} />}
                          <span className="truncate">{child.label}</span>
                        </NavLink>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          }
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => cn(
                "flex items-center gap-2.5 px-2 h-7 rounded-md text-[13px] transition-colors cursor-pointer",
                isActive
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                collapsed && "justify-center"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-1.5 pb-2 space-y-0.5">
        <button
          onClick={toggle}
          className={cn(
            "w-full flex items-center gap-2.5 px-2 h-7 rounded-md text-[13px] text-muted-foreground hover:bg-accent/60 hover:text-foreground cursor-pointer",
            collapsed && "justify-center"
          )}
          title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
        >
          {theme === 'dark'
            ? <Sun className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
            : <Moon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />}
          {!collapsed && <span className="truncate">{theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}</span>}
        </button>
        <button
          onClick={() => setCollapsed(c => !c)}
          className={cn(
            "w-full flex items-center gap-2.5 px-2 h-7 rounded-md text-muted-foreground hover:bg-accent/60 hover:text-foreground cursor-pointer",
            collapsed && "justify-center"
          )}
        >
          {collapsed
            ? <ChevronsRight className="h-3.5 w-3.5 shrink-0" />
            : <><ChevronsLeft className="h-3.5 w-3.5 shrink-0" /><span className="text-[13px]">Colapsar</span></>}
        </button>
      </div>
    </aside>
  )
}
