import { cn } from "@/lib/utils"

export function Layout({ children }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="flex h-14 items-center px-4 gap-4">
          <span className="text-xl font-bold text-primary">OS</span>
          <span className="text-sm font-medium">Programación de Producción</span>
        </div>
      </header>
      <main className="p-4">
        {children}
      </main>
    </div>
  )
}
