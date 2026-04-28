/**
 * FloatingSubmenu — panel flotante al lado del sidebar principal.
 * Estilo: HubSpot / Linear command bar.
 *
 * Se cierra:
 *  - al clicar fuera
 *  - al presionar ESC
 *  - al navegar a otra ruta (el padre debe manejar onClose)
 *
 * Items soportan opcionalmente un menú de acciones (3 puntos verticales)
 * que abre un sub-popover con opciones rápidas.
 */
import { useEffect, useRef, useState } from "react"
import { NavLink } from "react-router"
import { ChevronRight, MoreVertical } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * groups: array de
 *   { title?: string, items: [{ to, label, onClick, icon, rightSlot, actionsMenu? }] }
 *
 * actionsMenu (opcional por item):
 *   [{ label, icon, onClick, variant?: 'default'|'warn'|'danger', disabled?: bool }]
 *   Si está presente, se renderiza un botón ⋮ a la derecha del item.
 *   Items con disabled:true se omiten (filtrar antes vs renderizar gris ya).
 */
export function FloatingSubmenu({
  open, onClose, groups = [],
  anchorRef,
  title = null,
}) {
  const panelRef = useRef(null)
  const [openActions, setOpenActions] = useState(null) // { groupIdx, itemIdx } | null

  // Cerrar al clicar fuera
  useEffect(() => {
    if (!open) return
    const onDocClick = (e) => {
      if (!panelRef.current) return
      if (panelRef.current.contains(e.target)) return
      if (anchorRef?.current?.contains(e.target)) return
      onClose?.()
    }
    const onKey = (e) => { if (e.key === 'Escape') { setOpenActions(null); onClose?.() } }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose, anchorRef])

  // Resetear actions al cerrar el panel
  useEffect(() => { if (!open) setOpenActions(null) }, [open])

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
            <FloatingItem
              key={ii}
              {...item}
              actionsOpen={openActions?.groupIdx === gi && openActions?.itemIdx === ii}
              onToggleActions={() => setOpenActions(prev =>
                prev?.groupIdx === gi && prev?.itemIdx === ii ? null : { groupIdx: gi, itemIdx: ii }
              )}
              onCloseActions={() => setOpenActions(null)}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

function FloatingItem({
  to, label, onClick, icon: Icon, rightSlot, active, monospace,
  actionsMenu, actionsOpen, onToggleActions, onCloseActions,
}) {
  const hasActions = Array.isArray(actionsMenu) && actionsMenu.length > 0

  const content = (isActive) => (
    <>
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />}
      <span className={cn("truncate flex-1", monospace && "floating-submenu-mono")}>{label}</span>
      {hasActions ? null
        : (rightSlot !== undefined ? rightSlot : <ChevronRight className="h-3 w-3 shrink-0 floating-submenu-chev" strokeWidth={1.75} />)}
    </>
  )

  // Botón ⋮ + sub-popover
  const actionsBtn = hasActions && (
    <span className="floating-submenu-actions-wrap">
      <button
        type="button"
        className={cn("floating-submenu-actions-btn", actionsOpen && "open")}
        title="Acciones"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleActions?.() }}
      >
        <MoreVertical className="h-3.5 w-3.5" strokeWidth={1.75} />
      </button>
      {actionsOpen && (
        <ActionsPopover actions={actionsMenu} onClose={onCloseActions} />
      )}
    </span>
  )

  if (to) {
    return (
      <div className="floating-submenu-row">
        <NavLink
          to={to} onClick={onClick}
          className={({ isActive }) => cn("floating-submenu-item", (active ?? isActive) && "active", hasActions && "with-actions")}
        >
          {({ isActive }) => content(active ?? isActive)}
        </NavLink>
        {actionsBtn}
      </div>
    )
  }
  return (
    <div className="floating-submenu-row">
      <button
        className={cn("floating-submenu-item", active && "active", hasActions && "with-actions")}
        onClick={onClick}
      >
        {content(!!active)}
      </button>
      {actionsBtn}
    </div>
  )
}

function ActionsPopover({ actions, onClose }) {
  const popRef = useRef(null)
  useEffect(() => {
    const onDocClick = (e) => {
      if (!popRef.current) return
      if (popRef.current.contains(e.target)) return
      // Cerrar también si se clickea fuera (incluyendo el ⋮ — el toggle ya maneja eso)
      onClose?.()
    }
    // setTimeout para no atrapar el click que abrió el popover
    const t = setTimeout(() => document.addEventListener('mousedown', onDocClick), 0)
    return () => { clearTimeout(t); document.removeEventListener('mousedown', onDocClick) }
  }, [onClose])

  return (
    <div ref={popRef} className="floating-submenu-actions-pop" role="menu">
      {actions.map((a, i) => (
        <button
          key={i}
          type="button"
          disabled={a.disabled}
          className={cn(
            "floating-submenu-actions-item",
            a.variant === 'warn' && "is-warn",
            a.variant === 'danger' && "is-danger",
          )}
          onClick={(e) => {
            e.stopPropagation()
            if (a.disabled) return
            onClose?.()
            a.onClick?.()
          }}
        >
          {a.icon && <a.icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />}
          <span className="truncate">{a.label}</span>
        </button>
      ))}
    </div>
  )
}
