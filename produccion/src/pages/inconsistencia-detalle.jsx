import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router"
import { ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

const fmt = (n) => Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })
const money = (n) => `$${Math.round(Number(n) || 0).toLocaleString('es-CO')}`

const ESTADOS = [
  { value: 'abierto',     label: 'Abierto' },
  { value: 'en_revision', label: 'En revisión' },
  { value: 'resuelto',    label: 'Resuelto' },
  { value: 'descartado',  label: 'Descartado' },
]

const ESTADO_VARIANT = {
  abierto: 'solicitado', en_revision: 'solicitado',
  resuelto: 'programado', descartado: 'destructive',
  pendiente: 'solicitado', aplicado: 'programado',
  fallido: 'destructive',  revertido: 'outline',
}

export function InconsistenciaDetallePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try { setR(await api.get(`/api/inventario/inconsistencias/${id}`)) }
    catch { setR(null) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { cargar() }, [cargar])

  const cambiarEstado = async (nuevoEstado) => {
    setSaving(true)
    try {
      await api.patch(`/api/inventario/inconsistencias/${id}/estado`, { estado: nuevoEstado })
      await cargar()
    } finally { setSaving(false) }
  }

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
          cod <span className="font-mono">{r.id_effi}</span> · {r.bodega} · análisis {r.fecha_analisis}
          {r.fecha_inventario && <> · inventario {r.fecha_inventario}</>}
        </p>
        <div className="flex flex-wrap gap-2 mt-2 items-center">
          <Badge variant={ESTADO_VARIANT[r.estado] || 'outline'}>{ESTADOS.find(e => e.value === r.estado)?.label || r.estado}</Badge>
          <Badge variant="outline">{r.tipo_inconsistencia}</Badge>
          <Badge variant="outline">{r.ajustes?.length || 0} ajuste{r.ajustes?.length === 1 ? '' : 's'}</Badge>
          <div className="flex gap-1 ml-auto">
            {ESTADOS.filter(e => e.value !== r.estado).map(e => (
              <Button key={e.value} variant="outline" size="sm" disabled={saving} onClick={() => cambiarEstado(e.value)}>
                → {e.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Snapshot inventario + impacto */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
        <Card label="Stock antes"><span className={Number(r.stock_antes) < 0 ? 'text-red-500 font-mono' : 'font-mono'}>{fmt(r.stock_antes)}</span></Card>
        <Card label="Inv. teórico">{r.inventario_teorico != null ? <span className="font-mono">{fmt(r.inventario_teorico)}</span> : '—'}</Card>
        <Card label="Inv. físico">{r.inventario_fisico != null ? <span className="font-mono">{fmt(r.inventario_fisico)}</span> : '—'}</Card>
        <Card label="Impacto $">{r.costo_total_impacto ? <span className="font-mono">{money(r.costo_total_impacto)}</span> : '—'}</Card>
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
          <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Ajustes asociados</h2>
          <div className="border border-border rounded-md overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-2 py-1.5 text-left">Aplicado</th>
                  <th className="px-2 py-1.5 text-center">Estado</th>
                  <th className="px-2 py-1.5 text-center">Tipo</th>
                  <th className="px-2 py-1.5 text-right">Cantidad</th>
                  <th className="px-2 py-1.5 text-right">Costo unit</th>
                  <th className="px-2 py-1.5 text-right">Costo total</th>
                  <th className="px-2 py-1.5 text-left">OP Effi</th>
                  <th className="px-2 py-1.5 text-left">Motivo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {r.ajustes.map(a => (
                  <tr key={a.id}>
                    <td className="px-2 py-1.5 font-mono">{a.fecha_ajuste || '—'}</td>
                    <td className="px-2 py-1.5 text-center"><Badge variant={ESTADO_VARIANT[a.estado] || 'outline'}>{a.estado}</Badge></td>
                    <td className="px-2 py-1.5 text-center"><span className={`text-[11px] ${a.tipo === 'ingreso' ? 'text-emerald-500' : 'text-red-500'}`}>{a.tipo}</span></td>
                    <td className="px-2 py-1.5 text-right font-mono">{fmt(a.cantidad)}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{a.costo_unitario ? money(a.costo_unitario) : '—'}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{a.costo_total ? money(a.costo_total) : '—'}</td>
                    <td className="px-2 py-1.5 font-mono">{a.op_ajuste_effi ? `#${a.op_ajuste_effi}` : '—'}</td>
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
          <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Análisis detallado (.md)</h2>
          <pre className="bg-muted/30 border border-border rounded p-3 text-[11px] font-mono whitespace-pre-wrap overflow-x-auto">{r.contenido_md}</pre>
        </div>
      )}
    </div>
  )
}

function Card({ label, children }) {
  return (
    <div className="border border-border rounded px-3 py-2">
      <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</div>
      <div className="text-[13px] mt-0.5">{children}</div>
    </div>
  )
}
