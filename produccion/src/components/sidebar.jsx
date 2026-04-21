import { useState } from "react"
import { NavLink } from "react-router"
import { ClipboardList, LayoutDashboard, Calendar, BookOpen, Settings, ChevronsLeft, ChevronsRight, Sun, Moon } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/lib/theme"

const navItems = [
  { to: "/", label: "Vista general", icon: LayoutDashboard },
  { to: "/solicitudes", label: "Solicitudes", icon: ClipboardList },
  { to: "/calendario", label: "Calendario", icon: Calendar },
  { to: "/recetas", label: "Recetas", icon: BookOpen },
  { to: "/config", label: "Configuración", icon: Settings },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { theme, toggle } = useTheme()

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
      <nav className="flex-1 px-1.5 space-y-0.5">
        {navItems.map(item => {
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

      {/* Footer: theme toggle + collapse */}
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
