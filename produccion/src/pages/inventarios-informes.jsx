import { useCallback, useEffect, useState } from "react"
import { FileText, Download, Loader2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function InventariosInformesPage() {
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState('')
  const [generando, setGenerando] = useState(null)  // 'informe' | 'analisis' | null
  const [error, setError] = useState(null)

  const cargarFechas = useCallback(async () => {
    const data = await api.get('/api/inventario/fechas')
    setFechas(data)
    if (data.length && !fecha) setFecha(data[0].fecha_inventario)
  }, [fecha])

  useEffect(() => { cargarFechas() }, [cargarFechas])

  const descargar = async (tipo) => {
    if (!fecha) return
    setGenerando(tipo); setError(null)
    try {
      const url = `/api/inventario/${tipo}?fecha=${fecha}`
      const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${auth.token}` } })
      if (!resp.ok) {
        const t = await resp.text()
        throw new Error(t || `HTTP ${resp.status}`)
      }
      const blob = await resp.blob()
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${tipo === 'informe' ? 'informe_inventario' : 'analisis_ia'}_${fecha}.pdf`
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (e) { setError(e.message) }
    finally { setGenerando(null) }
  }

  return (
    <div className="p-5 max-w-2xl mx-auto">
      <div className="mb-5">
        <h1 className="text-[16px] font-semibold flex items-center gap-2"><FileText className="h-4 w-4" /> Informes</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">Descargá los PDFs oficiales del inventario</p>
      </div>

      <div className="space-y-4">
        <div className="rounded-lg border border-border bg-card p-5">
          <label className="text-[12px] font-medium text-muted-foreground">Fecha del inventario</label>
          <select value={fecha} onChange={e => setFecha(e.target.value)}
            className="mt-1 w-full h-10 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {fechas.map(f => <option key={f.fecha_inventario} value={f.fecha_inventario}>{f.fecha_inventario} · {f.contados || 0}/{f.inventariables || 0} contados</option>)}
          </select>
        </div>

        {/* Informe técnico */}
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="text-[14px] font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4" /> Informe técnico
              </div>
              <p className="text-[12px] text-muted-foreground mt-1">
                Detalle completo del inventario: diferencias por grupo, bodegas, valor teórico vs físico, impacto económico.
              </p>
            </div>
            <Button onClick={() => descargar('informe')} disabled={generando !== null || !fecha}>
              {generando === 'informe'
                ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generando…</>
                : <><Download className="h-3.5 w-3.5" /> Descargar</>
              }
            </Button>
          </div>
        </div>

        {/* Análisis IA */}
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="text-[14px] font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4" /> Análisis IA ejecutivo
              </div>
              <p className="text-[12px] text-muted-foreground mt-1">
                Reporte ejecutivo generado por IA: problemas sistémicos, causas raíz, recomendaciones operativas.
              </p>
            </div>
            <Button onClick={() => descargar('analisis-ia')} disabled={generando !== null || !fecha}>
              {generando === 'analisis-ia'
                ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generando…</>
                : <><Download className="h-3.5 w-3.5" /> Descargar</>
              }
            </Button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">{error}</div>
        )}

        <div className="flex items-start gap-2 p-3 rounded bg-muted/30 border border-border text-[11px] text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
          <div>Los PDFs se generan on-the-fly desde la BD VPS. El análisis IA tarda ~30s, el informe técnico ~5s.</div>
        </div>
      </div>
    </div>
  )
}
