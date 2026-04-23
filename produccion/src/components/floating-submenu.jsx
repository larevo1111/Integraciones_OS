/**
 * FloatingSubmenu — panel flotante al lado del sidebar principal.
 * Estilo: HubSpot / Linear command bar.
 *
 * Se cierra:
 *  - al clicar fuera
 *  - al presionar ESC
 *  - al navegar a otra ruta (el padre debe manejar onClose)
 */
import { useEffect, useRef, useState } from "react"
import { NavLink } from "react-router"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * groups: array de
 *   { title?: string, items: [{ to, label, onClick, icon, rightSlot }] }
 * Cada grupo se renderiza con separador superior.
 */
export function FloatingSubmenu({
  open, onClose, groups = [],
  anchorRef,
  title = null,
}) {
  const panelRef = useRef(null)

  // Cerrar al clicar fuera
  useEffect(() => {
    if (!open) return
    const onDocClick = (e) => {
      if (!panelRef.current) return
      if (panelRef.current.contains(e.target)) return
      if (anchorRef?.current?.contains(e.target)) return
      onClose?.()
    }
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose, anchorRef])

  // Calcular posición izquierda = borde derecho del sidebar (anchorRef → aside)
  const [leftPos, setLeftPos] = useState(224)
  useEffect(() => {
    if (!open) return
    const calc = () => {
      const aside = anchorRef?.current?.closest('aside')
      if (aside) setLeftPos(aside.getBoundingClientRect().right)
    }
    calc()
    window.addEventListener('resize', calc)
    return () => window.removeEventListener('resize', calc)
  }, [open, anchorRef])

  if (!open) return null

  return (
    <div
      ref={panelRef}
      className="floating-submenu"
      role="menu"
      style={{ left: leftPos }}
    >
      {title && <div className="floating-submenu-title">{title}</div>}
      {groups.map((g, gi) => (
        <div key={gi} className={cn("floating-submenu-group", gi > 0 && "with-separator")}>
          {g.title && <div className="floating-submenu-group-title">{g.title}</div>}
          {g.items.map((item, ii) => (
            <FloatingItem key={ii} {...item} />
          ))}
        </div>
      ))}
    </div>
  )
}

function FloatingItem({ to, label, onClick, icon: Icon, rightSlot, active, monospace }) {
  const content = (isActive) => (
    <>
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />}
      <span className={cn("truncate flex-1", monospace && "floating-submenu-mono")}>{label}</span>
      {rightSlot !== undefined ? rightSlot : <ChevronRight className="h-3 w-3 shrink-0 floating-submenu-chev" strokeWidth={1.75} />}
    </>
  )
  if (to) {
    return (
      <NavLink to={to} onClick={onClick}
               className={({ isActive }) => cn("floating-submenu-item", (active ?? isActive) && "active")}>
        {({ isActive }) => content(active ?? isActive)}
      </NavLink>
    )
  }
  return (
    <button className={cn("floating-submenu-item", active && "active")} onClick={onClick}>
      {content(!!active)}
    </button>
  )
}
