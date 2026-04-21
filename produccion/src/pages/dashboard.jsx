import { useEffect, useState } from "react"
import { Link } from "react-router"
import { ClipboardList, Factory, CheckCircle2, Clock } from "lucide-react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

export function DashboardPage() {
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/solicitudes/stats/resumen')
      .then(setStats)
      .finally(() => setLoading(false))
  }, [])

  const kpis = [
    { label: 'Solicitadas', value: stats.solicitado || 0, icon: ClipboardList, color: 'text-blue-400' },
    { label: 'Programadas', value: stats.programado || 0, icon: Clock, color: 'text-amber-400' },
    { label: 'En producción', value: stats.en_produccion || 0, icon: Factory, color: 'text-purple-400' },
    { label: 'Producidas', value: (stats.producido || 0) + (stats.validado || 0), icon: CheckCircle2, color: 'text-emerald-400' },
  ]

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Vista general</h1>
        <p className="text-sm text-muted-foreground mt-1">Resumen de solicitudes de producción</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {kpis.map(k => {
          const Icon = k.icon
          return (
            <div key={k.label} className="rounded-lg border bg-card p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{k.label}</span>
                <Icon className={cn("h-4 w-4", k.color)} />
              </div>
              <div className="text-3xl font-semibold tabular-nums">{loading ? '—' : k.value}</div>
            </div>
          )
        })}
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="font-semibold mb-2">Empieza aquí</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Crea solicitudes de producción, asigna fechas y haz seguimiento hasta la validación.
        </p>
        <Link
          to="/solicitudes"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors cursor-pointer"
        >
          Ver solicitudes
        </Link>
      </div>
    </div>
  )
}
