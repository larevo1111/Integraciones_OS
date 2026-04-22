import { useEffect, useState } from "react"
import { X, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

/**
 * Diálogo para programar varias solicitudes en una sola OP.
 * - Verifica compatibilidad (mismo granel) automáticamente
 * - Si compatibles, muestra botón "Crear grupo"
 * - Si no compatibles, muestra razón clara
 */
export function ProgramarGrupoDialog({ open, onOpenChange, solicitudes, onCreated }) {
  const [compat, setCompat] = useState(null)
  const [loading, setLoading] = useState(false)
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open || solicitudes.length === 0) return
    setLoading(true); setError(null); setCompat(null)
    const cods = solicitudes.map(s => s.cod_articulo)
    api.post('/api/produccion/compatibilidad', { cods })
      .then(setCompat)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [open, solicitudes])

  const crear = async () => {
    setCreando(true); setError(null)
    try {
      const grupo = await api.post('/api/produccion/grupos', {
        solicitudes_ids: solicitudes.map(s => s.id),
        creado_por: 'Jenifer',
      })
      onCreated?.(grupo)
      onOpenChange(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setCreando(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => onOpenChange(false)}>
      <div
        className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg max-h-[80vh] overflow-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h2 className="text-[14px] font-semibold">Programar {solicitudes.length} solicitudes en una OP</h2>
          <button onClick={() => onOpenChange(false)} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Lista de solicitudes seleccionadas */}
          <div className="space-y-1 text-[13px]">
            {solicitudes.map(s => (
              <div key={s.id} className="flex items-center gap-2">
                <span className="font-mono text-muted-foreground text-[11px]">#{s.id}</span>
                <span className="font-mono text-muted-foreground text-[11px]">{s.cod_articulo}</span>
                <span className="flex-1 truncate">{s.nombre_articulo}</span>
                <span className="font-mono">{s.cantidad}</span>
              </div>
            ))}
          </div>

          {/* Estado de compatibilidad */}
          {loading && (
            <div className="flex items-center gap-2 p-3 rounded bg-muted/30">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-[13px] text-muted-foreground">Verificando compatibilidad…</span>
            </div>
          )}

          {compat && compat.compatible && (
            <div className="flex items-start gap-2 p-3 rounded bg-emerald-500/10 border border-emerald-500/30">
              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
              <div className="text-[13px]">
                <div className="font-medium text-emerald-500">Productos compatibles</div>
                <div className="text-muted-foreground mt-0.5">
                  Comparten la materia prima granel: <span className="font-mono">cod {compat.mp_granel_comun}</span>
                  {compat.productos[0]?.mp_granel?.nombre && ` (${compat.productos[0].mp_granel.nombre})`}
                </div>
              </div>
            </div>
          )}

          {compat && !compat.compatible && (
            <div className="flex items-start gap-2 p-3 rounded bg-amber-500/10 border border-amber-500/30">
              <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
              <div className="text-[13px]">
                <div className="font-medium text-amber-500">No se pueden agrupar en una sola OP</div>
                <div className="text-muted-foreground mt-0.5">{compat.razon}</div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[13px] text-destructive">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={creando}>
            Cancelar
          </Button>
          <Button onClick={crear} disabled={!compat?.compatible || creando}>
            {creando ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Creando…</> : 'Crear grupo de OP'}
          </Button>
        </div>
      </div>
    </div>
  )
}
