import { useCallback, useEffect, useState } from "react"
import { Sparkles, Loader2, Download, FileText, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function InventariosAnalisisIAPage() {
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState('')
  const [generando, setGenerando] = useState(false)
  const [error, setError] = useState(null)
  const [pdfUrl, setPdfUrl] = useState(null)

  const cargarFechas = useCallback(async () => {
    const data = await api.get('/api/inventario/fechas')
    setFechas(data)
    if (data.length && !fecha) setFecha(data[0].fecha_inventario)
  }, [fecha])

  useEffect(() => { cargarFechas() }, [cargarFechas])

  const generar = async () => {
    if (!fecha) return
    setGenerando(true); setError(null); setPdfUrl(null)
    try {
      // El endpoint retorna el PDF directamente (stream)
      const url = `/api/inventario/analisis-ia?fecha=${fecha}`
      const resp = await fetch(url, {
        headers: { 'Authorization': `Bearer ${auth.token}` }
      })
      if (!resp.ok) {
        const t = await resp.text()
        throw new Error(t || `HTTP ${resp.status}`)
      }
      const blob = await resp.blob()
      setPdfUrl(URL.createObjectURL(blob))
    } catch (e) { setError(e.message) }
    finally { setGenerando(false) }
  }

  return (
    <div className="p-5 max-w-4xl mx-auto">
      <div className="mb-5">
        <h1 className="text-[16px] font-semibold flex items-center gap-2"><Sparkles className="h-4 w-4" /> Análisis IA</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">
          Reporte ejecutivo del inventario generado por el ia_service local (gratis, sin API externa)
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 space-y-4">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex-1 min-w-[180px]">
            <label className="text-[12px] font-medium text-muted-foreground">Fecha del inventario</label>
            <select value={fecha} onChange={e => { setFecha(e.target.value); setPdfUrl(null) }}
              className="mt-1 w-full h-10 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
              {fechas.map(f => <option key={f.fecha_inventario} value={f.fecha_inventario}>{f.fecha_inventario} · {f.con_diferencia || 0} dif.</option>)}
            </select>
          </div>
          <Button onClick={generar} disabled={generando || !fecha}>
            {generando
              ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generando…</>
              : <><Sparkles className="h-3.5 w-3.5" /> Generar análisis</>
            }
          </Button>
        </div>

        {error && (
          <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">{error}</div>
        )}

        <div className="flex items-start gap-2 p-3 rounded bg-muted/30 border border-border text-[11px] text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
          <div>
            El análisis usa <span className="font-mono">ia_service :5100</span> y genera un PDF con resumen ejecutivo,
            problemas sistémicos, causas raíz y recomendaciones. Tarda ~30 segundos.
          </div>
        </div>
      </div>

      {/* Preview PDF */}
      {pdfUrl && (
        <div className="mt-6 rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="text-[13px] font-medium flex items-center gap-2">
              <FileText className="h-4 w-4" /> Análisis IA {fecha}
            </div>
            <a href={pdfUrl} download={`analisis_ia_${fecha}.pdf`}
               className="text-[12px] text-primary hover:underline flex items-center gap-1">
              <Download className="h-3.5 w-3.5" /> Descargar PDF
            </a>
          </div>
          <iframe src={pdfUrl} className="w-full h-[70vh]" title="Análisis IA" />
        </div>
      )}
    </div>
  )
}
