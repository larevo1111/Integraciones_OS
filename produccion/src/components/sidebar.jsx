import { useState } from "react"
import { NavLink } from "react-router"
import { ClipboardList, LayoutDashboard, Calendar, BookOpen, Settings, ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/", label: "Vista general", icon: LayoutDashboard },
  { to: "/solicitudes", label: "Solicitudes", icon: ClipboardList },
  { to: "/calendario", label: "Calendario", icon: Calendar },
  { to: "/recetas", label: "Recetas", icon: BookOpen },
  { to: "/config", label: "Configuración", icon: Settings },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        "bg-sidebar border-r border-border flex flex-col transition-[width] duration-200 shrink-0",
        collapsed ? "w-14" : "w-56"
      )}
      style={{ background: 'var(--color-sidebar)' }}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border gap-2 shrink-0">
        <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center text-primary-foreground font-bold text-sm shrink-0">
          OS
        </div>
        {!collapsed && <span className="font-semibold text-sm truncate">Producción</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2">
        {navItems.map(item => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-2.5 h-9 rounded-md text-sm transition-colors cursor-pointer",
                isActive
                  ? "bg-accent text-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
                collapsed && "justify-center"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Toggle */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="h-9 mx-2 mb-2 rounded-md flex items-center justify-center text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer"
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>
    </aside>
  )
}
