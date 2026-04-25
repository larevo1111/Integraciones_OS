import { useState, useCallback, useEffect } from "react"
import { useLocation } from "react-router"
import { Menu } from "lucide-react"
import { Sidebar } from "./sidebar"

export function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // Cerrar sidebar móvil al navegar
  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  const closeMobile = useCallback(() => setMobileOpen(false), [])

  return (
    <div className="h-[100dvh] flex bg-background text-foreground overflow-hidden">
      {/* Backdrop móvil */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={closeMobile}
        />
      )}

      <Sidebar mobileOpen={mobileOpen} onCloseMobile={closeMobile} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header móvil */}
        <div className="flex items-center h-12 px-3 gap-3 border-b border-border shrink-0 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-accent cursor-pointer"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-[13px] font-semibold truncate">Producción OS</span>
        </div>

        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
