import { useCallback, useEffect, useRef, useState } from "react"
import { RefreshCw, Loader2, CheckCircle2, XCircle, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

const ESTADOS_EN_CURSO = ['iniciando', 'exportando', 'importando', 'sincronizando']

const ESTADOS_UI = {
  idle:          { icon: RefreshCw,      color: 'text-muted-foreground', label: 'Inactivo' },
  iniciando:     { icon: Loader2,        color: 'text-primary',          label: 'Iniciando…',   spin: true },
  exportando:    { icon: Loader2,        color: 'text-primary',          label: 'Exportando Effi…', spin: true },
  importando:    { icon: Loader2,        color: 'text-primary',          label: 'Importando a BD…', spin: true },
  sincronizando: { icon: Loader2,        color: 'text-primary',          label: 'Sincronizando catálogo…', spin: true },
  completado:    { icon: CheckCircle2,   color: 'text-emerald-500',      label: 'Completado' },
  error:         { icon: XCircle,        color: 'text-destructive',      label: 'Error' },
}

export function InventariosSyncEffiPage() {
  const [estado, setEstado] = useState({ estado: 'idle', mensaje: '', timestamp: null })
  const [lanzando, setLanzando] = useState(false)
  const poll = useRef(null)

  const cargarEstado = useCallback(async () => {
    try {
      const data = await api.get('/api/inventario/sync-effi/estado')
      setEstado(data)
      // Mientras esté en curso, polling cada 3s
      if (ESTADOS_EN_CURSO.includes(data.estado)) {
        poll.current = setTimeout(cargarEstado, 3000)
      }
    } catch (e) { console.error(e) }
  }, [])

  useEffect(() => {
    cargarEstado()
    return () => { if (poll.current) clearTimeout(poll.current) }
  }, [cargarEstado])

  const lanzar = async () => {
    if (ESTADOS_EN_CURSO.includes(estado.estado)) return
    setLanzando(true)
    try {
      await api.post('/api/inventario/sync-effi', {})
      await cargarEstado()
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setLanzando(false)
    }
  }

  const ui = ESTADOS_UI[estado.estado] || ESTADOS_UI.idle
  const Icon = ui.icon
  const enCurso = ESTADOS_EN_CURSO.includes(estado.estado)

  return (
    <div className="p-5 max-w-2xl mx-auto">
      <div className="mb-5">
        <h1 className="text-[16px] font-semibold flex items-center gap-2"><RefreshCw className="h-4 w-4" /> Sync Effi</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">
          Sincroniza catálogo de artículos desde Effi a la BD local (exporta Excel → importa → calcula grupo/unidad)
        </p>
      </div>

      {/* Card estado */}
      <div className="rounded-lg border border-border bg-card p-6 space-y-4">
        <div className="flex items-center gap-3">
          <Icon className={`h-8 w-8 ${ui.color} ${ui.spin ? 'animate-spin' : ''}`} strokeWidth={1.75} />
          <div className="flex-1">
            <div className="text-[14px] font-medium">{ui.label}</div>
            {estado.mensaje && <div className="text-[12px] text-muted-foreground mt-0.5">{estado.mensaje}</div>}
            {estado.timestamp && (
              <div className="text-[11px] text-muted-foreground/70 mt-0.5">
                Iniciado: {String(estado.timestamp).slice(0, 19).replace('T', ' ')}
              </div>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-border">
          <Button
            onClick={lanzar}
            disabled={enCurso || lanzando}
            className="w-full"
          >
            {lanzando || enCurso
              ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> {enCurso ? 'Sincronización en curso…' : 'Lanzando…'}</>
              : <><RefreshCw className="h-3.5 w-3.5" /> Sincronizar ahora</>
            }
          </Button>
        </div>

        <div className="flex items-start gap-2 p-3 rounded bg-muted/30 border border-border text-[11px] text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-foreground mb-0.5">Qué hace esto</div>
            <div>1) Abre Effi con Playwright y descarga el Excel de inventario</div>
            <div>2) Importa a <span className="font-mono">effi_data.zeffi_inventario</span></div>
            <div>3) Calcula <span className="font-mono">grupo</span> (PT/PP/MP/INS/DS) y <span className="font-mono">unidad</span> (kg/gr/und) de cada artículo</div>
            <div className="mt-1">Duración típica: 1-2 minutos. Ejecutarlo durante inventario es seguro.</div>
          </div>
        </div>
      </div>
    </div>
  )
}
