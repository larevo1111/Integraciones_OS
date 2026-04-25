/**
 * RecetaDetallePage — muestra la receta completa de un producto y permite
 * editar estado + confianza + notas.
 */
import { useCallback, useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router"
import { ChevronLeft, CheckCircle2, AlertCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

function Money({ v }) {
  const n = Number(v || 0)
  return <span className="font-mono tabular-nums">${n.toLocaleString('es-CO', { maximumFractionDigits: 2 })}</span>
}

function Num({ v, decimals = 4 }) {
  const n = Number(v || 0)
  return <span className="font-mono tabular-nums">{n.toLocaleString('es-CO', { maximumFractionDigits: decimals })}</span>
}

export function RecetaDetallePage() {
  const { cod } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notas, setNotas] = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`/api/recetas/${cod}`)
      setR(data)
      setNotas(data.notas_analisis || '')
    } catch { setR(null) }
    finally { setLoading(false) }
  }, [cod])

  useEffect(() => { cargar() }, [cargar])

  const patch = async (body) => {
    setSaving(true)
    try {
      await api.patch(`/api/recetas/${cod}`, body)
      await cargar()
    } finally { setSaving(false) }
  }

  const validar = () => patch({ estado: 'validada' })
  const devolverBorrador = () => patch({ estado: 'borrador' })
  const guardarNotas = () => patch({ notas_analisis: notas })

  if (loading) return <div className="p-5 text-muted-foreground">Cargando receta {cod}…</div>
  if (!r) return <div className="p-5 text-red-500">Receta no encontrada para cod={cod}</div>

  const principal = r.productos?.find(p => p.es_principal) || null
  const coProds = r.productos?.filter(p => !p.es_principal) || []

  // costos totales estimados (para 1 lote)
  const costoMateriales = (r.materiales || []).reduce(
    (s, m) => s + Number(m.cantidad_por_lote || 0) * Number(m.costo_unit_snapshot || 0), 0)
  const costoProd = (r.costos || []).reduce(
    (s, c) => s + Number(c.cantidad_por_lote || 0) * Number(c.costo_unit || 0), 0)
  const ventaTotal = principal ? Number(principal.cantidad_por_lote) * Number(principal.precio_min_venta_snapshot) : 0
  const beneficio = ventaTotal - costoMateriales - costoProd
  const margenPct = ventaTotal ? (beneficio / ventaTotal * 100) : 0

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/recetas')}>
          <ChevronLeft className="h-4 w-4" /> Volver
        </Button>
      </div>

      <div className="mb-5">
        <h1 className="text-[16px] sm:text-[18px] font-semibold">{r.nombre}</h1>
        <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-0.5">
          cod <span className="font-mono">{r.cod_articulo}</span> · <span className="capitalize">{r.familia}</span> · <span className="font-mono">{r.patron}</span>
          {r.cantidad_lote_std ? <> · <span className="font-mono">{r.cantidad_lote_std} {r.unidad_producto}</span></> : null}
        </p>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <Badge variant={r.estado === 'validada' ? 'programado' : 'solicitado'}>{r.estado}</Badge>
          <Badge variant="outline">{r.confianza}</Badge>
          <Badge variant="outline">{r.n_ops_analizadas} OPs</Badge>
          <div className="flex gap-2 sm:ml-auto">
            {r.estado !== 'validada' && (
              <Button size="sm" onClick={validar} disabled={saving}>
                <CheckCircle2 className="h-4 w-4" /> Validar
              </Button>
            )}
            {r.estado === 'validada' && (
              <Button variant="outline" size="sm" onClick={devolverBorrador} disabled={saving}>
                <AlertCircle className="h-4 w-4" /> Borrador
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Resumen económico */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
        <Card label="Costo materiales"><Money v={costoMateriales} /></Card>
        <Card label="Costo producción"><Money v={costoProd} /></Card>
        <Card label="Venta total"><Money v={ventaTotal} /></Card>
        <Card label="Beneficio"><span className={beneficio > 0 ? 'text-emerald-600' : 'text-red-500'}><Money v={beneficio} /> ({margenPct.toFixed(1)}%)</span></Card>
      </div>

      {/* Materiales */}
      <Seccion titulo="Materiales">
        <div className="overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0">
        <table className="w-full text-[12px] min-w-[500px]">
          <thead className="text-muted-foreground border-b border-border">
            <tr><th className="text-left py-1.5">Cód</th><th className="text-left">Nombre</th><th className="text-right">Cantidad</th><th className="text-right">Costo unit</th><th className="text-right">Subtotal</th><th className="text-right">N OPs</th></tr>
          </thead>
          <tbody>
            {(r.materiales || []).map(m => (
              <tr key={m.id} className="border-b border-border/40">
                <td className="py-1.5 font-mono">{m.cod_material}</td>
                <td>{m.nombre}</td>
                <td className="text-right"><Num v={m.cantidad_por_lote} /></td>
                <td className="text-right"><Money v={m.costo_unit_snapshot} /></td>
                <td className="text-right"><Money v={Number(m.cantidad_por_lote) * Number(m.costo_unit_snapshot)} /></td>
                <td className="text-right">{m.n_ops_aparece}</td>
              </tr>
            ))}
            {(r.materiales || []).length === 0 && (
              <tr><td colSpan={6} className="py-2 text-center text-muted-foreground italic">Sin materiales definidos</td></tr>
            )}
          </tbody>
        </table>
        </div>
      </Seccion>

      {/* Productos */}
      <Seccion titulo="Productos">
        <div className="overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0">
        <table className="w-full text-[12px] min-w-[500px]">
          <thead className="text-muted-foreground border-b border-border">
            <tr><th className="text-left py-1.5">Cód</th><th className="text-left">Nombre</th><th className="text-right">Cantidad</th><th className="text-right">Precio min venta</th><th className="text-right">Subtotal</th></tr>
          </thead>
          <tbody>
            {(r.productos || []).map(p => (
              <tr key={p.id} className={`border-b border-border/40 ${p.es_principal ? 'font-medium' : ''}`}>
                <td className="py-1.5 font-mono">{p.es_principal && '★ '}{p.cod_articulo}</td>
                <td>{p.nombre}</td>
                <td className="text-right"><Num v={p.cantidad_por_lote} /></td>
                <td className="text-right"><Money v={p.precio_min_venta_snapshot} /></td>
                <td className="text-right"><Money v={Number(p.cantidad_por_lote) * Number(p.precio_min_venta_snapshot)} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Seccion>

      {/* Costos de producción */}
      {r.costos?.length > 0 && (
        <Seccion titulo="Costos de producción">
          <div className="overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0">
          <table className="w-full text-[12px] min-w-[400px]">
            <thead className="text-muted-foreground border-b border-border">
              <tr><th className="text-left py-1.5">Nombre</th><th className="text-right">Cantidad</th><th className="text-right">Costo unit</th><th className="text-right">Subtotal</th></tr>
            </thead>
            <tbody>
              {r.costos.map(c => (
                <tr key={c.id} className="border-b border-border/40">
                  <td className="py-1.5">{c.nombre}</td>
                  <td className="text-right"><Num v={c.cantidad_por_lote} decimals={2} /></td>
                  <td className="text-right"><Money v={c.costo_unit} /></td>
                  <td className="text-right"><Money v={Number(c.cantidad_por_lote) * Number(c.costo_unit)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Seccion>
      )}

      {/* Notas / análisis */}
      <Seccion titulo="Razonamiento / análisis">
        <textarea
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          className="w-full min-h-[120px] bg-background border border-border rounded p-2 text-[12px] font-mono"
        />
        <div className="flex items-center justify-between mt-2">
          <div className="text-[11px] text-muted-foreground">
            {r.ops_referencia ? <>OPs ref: <span className="font-mono">{r.ops_referencia}</span></> : null}
          </div>
          <Button size="sm" variant="outline" onClick={guardarNotas} disabled={saving || notas === (r.notas_analisis || '')}>
            Guardar notas
          </Button>
        </div>
      </Seccion>
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

function Seccion({ titulo, children }) {
  return (
    <div className="mb-5">
      <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">{titulo}</h2>
      {children}
    </div>
  )
}
