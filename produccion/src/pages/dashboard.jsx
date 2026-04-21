import { useEffect, useState } from "react"
import { Link } from "react-router"
import { ClipboardList, Factory, CheckCircle2, Clock, ArrowRight } from "lucide-react"
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
    { label: 'En producción', value: stats.en_produccion || 0, icon: Factory, color: 'text-violet-400' },
    { label: 'Producidas', value: (stats.producido || 0) + (stats.validado || 0), icon: CheckCircle2, color: 'text-emerald-400' },
  ]

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="mb-5">
        <h1 className="text-[16px] font-semibold">Vista general</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">Resumen de solicitudes de producción</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
        {kpis.map(k => {
          const Icon = k.icon
          return (
            <div key={k.label} className="rounded-md border border-border bg-card p-3.5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-muted-foreground">{k.label}</span>
                <Icon className={cn("h-3.5 w-3.5", k.color)} strokeWidth={2} />
              </div>
              <div className="text-[22px] font-semibold tabular-nums tracking-tight">{loading ? '—' : k.value}</div>
            </div>
          )
        })}
      </div>

      <Link
        to="/solicitudes"
        className="group rounded-md border border-border bg-card p-4 flex items-center justify-between hover:bg-accent/50 transition-colors cursor-pointer"
      >
        <div>
          <h2 className="text-[13px] font-medium mb-0.5">Ver solicitudes</h2>
          <p className="text-[12px] text-muted-foreground">
            Crea solicitudes, asigna fechas y haz seguimiento hasta validación.
          </p>
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" strokeWidth={2} />
      </Link>
    </div>
  )
}
