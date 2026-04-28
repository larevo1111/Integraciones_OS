import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router"
import { ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

const fmt = (n) => Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })

export function InconsistenciaDetallePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try { setR(await api.get(`/api/inventario/inconsistencias/${id}`)) }
    catch { setR(null) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { cargar() }, [cargar])

  if (loading) return <div className="p-5 text-muted-foreground">Cargando…</div>
  if (!r) return <div className="p-5 text-red-500">Análisis no encontrado</div>

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1100px] mx-auto">
      <Button variant="ghost" size="sm" onClick={() => navigate('/inconsistencias')} className="mb-3">
        <ChevronLeft className="h-4 w-4" /> Volver
      </Button>

      <div className="mb-5">
        <h1 className="text-[16px] sm:text-[18px] font-semibold">{r.nombre}</h1>
        <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-0.5">
          cod <span className="font-mono">{r.id_effi}</span> · {r.bodega} · {r.fecha}
        </p>
        <div className="flex gap-2 mt-2">
          <Badge variant="outline">Stock antes: {fmt(r.stock_antes)}</Badge>
          <Badge variant="outline">{r.ajustes?.length || 0} ajustes</Badge>
        </div>
      </div>

      <div className="mb-5">
        <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Problema</h2>
        <div className="text-[13px] whitespace-pre-wrap">{r.problema}</div>
      </div>

      <div className="mb-5">
        <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Causa raíz</h2>
        <div className="text-[13px] whitespace-pre-wrap">{r.causa_raiz || '—'}</div>
      </div>

      {r.ajustes?.length > 0 && (
        <div className="mb-5">
          <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Ajustes aplicados</h2>
          <div className="border border-border rounded-md overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-2 py-1.5 text-left">Fecha</th>
                  <th className="px-2 py-1.5 text-center">Tipo</th>
                  <th className="px-2 py-1.5 text-right">Cantidad</th>
                  <th className="px-2 py-1.5 text-left">OP Effi</th>
                  <th className="px-2 py-1.5 text-left">Motivo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {r.ajustes.map(a => (
                  <tr key={a.id}>
                    <td className="px-2 py-1.5 font-mono">{a.fecha}</td>
                    <td className="px-2 py-1.5 text-center"><Badge variant={a.tipo === 'ingreso' ? 'programado' : 'solicitado'}>{a.tipo}</Badge></td>
                    <td className="px-2 py-1.5 text-right font-mono">{fmt(a.cantidad)}</td>
                    <td className="px-2 py-1.5 font-mono">{a.op_ajuste_effi || '—'}</td>
                    <td className="px-2 py-1.5 text-[11px]">{a.motivo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {r.contenido_md && (
        <div className="mb-5">
          <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Análisis detallado</h2>
          <pre className="bg-muted/30 border border-border rounded p-3 text-[11px] font-mono whitespace-pre-wrap overflow-x-auto">{r.contenido_md}</pre>
        </div>
      )}
    </div>
  )
}
