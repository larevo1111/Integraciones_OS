import { useEffect, useState } from "react"
import { X, AlertTriangle, Loader2, CheckCircle2, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Combobox } from "@/components/ui/combobox"
import { api } from "@/lib/api"

/**
 * Diálogo Programar OP — preview editable.
 * - Suma recetas de todas las solicitudes (puede haber varias recetas distintas en una OP)
 * - 3 tablas editables (productos, materiales, otros costos) — cada celda + agregar/quitar filas
 * - Totales se recalculan en vivo
 */
export function ProgramarGrupoDialog({ open, onOpenChange, solicitudes, articulos, onCreated }) {
  const [compat, setCompat] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState(null)
  const [tiposCosto, setTiposCosto] = useState([])

  useEffect(() => {
    if (!open || solicitudes.length === 0) return
    setLoading(true); setError(null); setCompat(null); setPreview(null)
    const cods = solicitudes.map(s => s.cod_articulo)
    Promise.all([
      api.post('/api/produccion/compatibilidad', { cods }),
      api.post('/api/produccion/preview-op', {
        items: solicitudes.map(s => ({ cod: s.cod_articulo, cantidad: parseFloat(s.cantidad) || 0 }))
      }).catch(e => { setError('Preview: ' + e.message); return null })
    ])
      .then(([c, p]) => { setCompat(c); setPreview(p) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
    if (tiposCosto.length === 0) {
      api.get('/api/produccion/tipos-costo').then(setTiposCosto).catch(() => {})
    }
  }, [open, solicitudes, tiposCosto.length])

  const recalc = (mats, prods, costos) => {
    const cm = mats.reduce((s, m) => s + (parseFloat(m.cantidad) || 0) * (parseFloat(m.costo) || 0), 0)
    const co = costos.reduce((s, c) => s + (parseFloat(c.cantidad) || 0) * (parseFloat(c.costo) || 0), 0)
    const v = prods.reduce((s, p) => s + (parseFloat(p.cantidad) || 0) * (parseFloat(p.precio) || 0), 0)
    return { costo_materiales: +cm.toFixed(2), costo_otros: +co.toFixed(2), costo_total: +(cm + co).toFixed(2), venta_total: +v.toFixed(2), beneficio: +(v - cm - co).toFixed(2) }
  }
  const updateAll = (m, p, c) => setPreview({...preview, materiales: m, productos: p, otros_costos: c, totales: recalc(m, p, c)})

  const setMat  = (i, k, v) => { const m = [...preview.materiales];   m[i] = {...m[i], [k]: v}; updateAll(m, preview.productos, preview.otros_costos) }
  const setProd = (i, k, v) => { const p = [...preview.productos];    p[i] = {...p[i], [k]: v}; updateAll(preview.materiales, p, preview.otros_costos) }
  const setCost = (i, k, v) => { const c = [...preview.otros_costos]; c[i] = {...c[i], [k]: v}; updateAll(preview.materiales, preview.productos, c) }

  // Cambio de artículo en una fila: actualiza cod + nombre + costo (materiales) o precio (productos)
  const cambiarMatArticulo = (i, nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    const m = [...preview.materiales]
    m[i] = { ...m[i], cod: nuevoCod, nombre: a.nombre, costo: a.costo_manual || 0 }
    updateAll(m, preview.productos, preview.otros_costos)
  }
  const cambiarProdArticulo = (i, nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    const p = [...preview.productos]
    // Para productos no hay precio en /api/articulos, dejamos el actual; si nuevo, queda 0
    p[i] = { ...p[i], cod: nuevoCod, nombre: a.nombre }
    updateAll(preview.materiales, p, preview.otros_costos)
  }

  const removeMat  = i => updateAll(preview.materiales.filter((_, j) => j !== i), preview.productos, preview.otros_costos)
  const removeProd = i => updateAll(preview.materiales, preview.productos.filter((_, j) => j !== i), preview.otros_costos)
  const removeCost = i => updateAll(preview.materiales, preview.productos, preview.otros_costos.filter((_, j) => j !== i))

  const addMat = (cod) => {
    const a = articulos.find(x => x.value === cod)
    if (!a) return
    const m = [...preview.materiales, { cod, nombre: a.label.replace(/^\d+ — /, ''), cantidad: 1, costo: 0 }]
    updateAll(m, preview.productos, preview.otros_costos)
  }
  const addProd = (cod) => {
    const a = articulos.find(x => x.value === cod)
    if (!a) return
    const p = [...preview.productos, { cod, nombre: a.label.replace(/^\d+ — /, ''), cantidad: 1, precio: 0 }]
    updateAll(preview.materiales, p, preview.otros_costos)
  }
  const addCost = (tipoIdStr) => {
    const t = tiposCosto.find(x => String(x.tipo_costo_id) === String(tipoIdStr))
    if (!t) return
    const c = [...preview.otros_costos, {
      tipo_costo_id: parseInt(t.tipo_costo_id),
      nombre: t.nombre,
      cantidad: 1,
      costo: t.tipo_costo_id == 13 ? 7000 : 0,
    }]
    updateAll(preview.materiales, preview.productos, c)
  }

  const crear = async () => {
    setCreando(true); setError(null)
    try {
      const r = await api.post('/api/produccion/crear-op-effi', {
        solicitudes_ids: solicitudes.map(s => s.id),
        materiales: preview.materiales,
        productos: preview.productos,
        otros_costos: preview.otros_costos,
      })
      onCreated?.(r)
      onOpenChange(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setCreando(false)
    }
  }

  if (!open) return null

  const fmt = (n) => (Math.round(n)).toLocaleString('es-CO')
  const opts = (articulos || []).map(a => ({ value: a.value, label: a.label, nombre: a.nombre }))
  const optsCosto = tiposCosto.map(t => ({ value: String(t.tipo_costo_id), label: `${t.tipo_costo_id} — ${t.nombre}`, nombre: t.nombre }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-2 sm:p-4" onClick={() => onOpenChange(false)}>
      <div
        className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-5xl max-h-[95vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-border shrink-0">
          <h2 className="text-[14px] font-semibold">
            Programar {solicitudes.length} solicitud{solicitudes.length === 1 ? '' : 'es'} en una OP
          </h2>
          <button onClick={() => onOpenChange(false)} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-3 sm:p-5 space-y-4 overflow-auto flex-1">
          {loading && (
            <div className="flex items-center gap-2 p-3 rounded bg-muted/30">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-[13px] text-muted-foreground">Cargando preview de OP…</span>
            </div>
          )}

          {preview && (
            <>
              {/* Productos */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="text-[12px] font-semibold text-muted-foreground">PRODUCTOS A PRODUCIR</div>
                  <Combobox value="" onChange={addProd} options={opts} placeholder="Agregar producto" searchPlaceholder="Buscar producto..." variant="link" />
                </div>
                <div className="border border-border rounded-md overflow-x-auto">
                  <table className="w-full text-[12px]">
                    <thead className="bg-muted/30 text-[12px]">
                      <tr><th className="px-2 py-1.5 text-left">Cód</th><th className="px-2 py-1.5 text-left">Producto</th><th className="px-2 py-1.5 text-right">Cant</th><th className="px-2 py-1.5 text-right">Precio</th><th className="px-2 py-1.5 text-right">Subtotal</th><th className="w-8"></th></tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {preview.productos.map((p, i) => (
                        <tr key={i}>
                          <td className="px-2 py-1 font-mono text-[12px]">{p.cod}</td>
                          <td className="px-2 py-1 min-w-[480px]">
                            <Combobox value={p.cod} onChange={(c) => cambiarProdArticulo(i, c)} options={opts}
                              placeholder={p.nombre || 'Seleccionar…'} searchPlaceholder="Buscar producto..."
                              triggerClassName="!text-[10px] h-7" />
                          </td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-20 ml-auto" value={p.cantidad} onChange={e => setProd(i, 'cantidad', e.target.value)} /></td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-24 ml-auto" value={p.precio} onChange={e => setProd(i, 'precio', e.target.value)} /></td>
                          <td className="px-2 py-1 text-right font-mono">{fmt((parseFloat(p.cantidad)||0) * (parseFloat(p.precio)||0))}</td>
                          <td className="px-1 py-1"><button onClick={() => removeProd(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Materiales */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="text-[12px] font-semibold text-muted-foreground">MATERIALES</div>
                  <Combobox value="" onChange={addMat} options={opts} placeholder="Agregar material" searchPlaceholder="Buscar material..." variant="link" />
                </div>
                <div className="border border-border rounded-md overflow-x-auto">
                  <table className="w-full text-[12px]">
                    <thead className="bg-muted/30 text-[12px]">
                      <tr><th className="px-2 py-1.5 text-left">Cód</th><th className="px-2 py-1.5 text-left">Material</th><th className="px-2 py-1.5 text-right">Cant</th><th className="px-2 py-1.5 text-right">Costo</th><th className="px-2 py-1.5 text-right">Subtotal</th><th className="w-8"></th></tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {preview.materiales.map((m, i) => (
                        <tr key={i}>
                          <td className="px-2 py-1 font-mono text-[12px]">{m.cod}</td>
                          <td className="px-2 py-1 min-w-[504px]">
                            <Combobox value={m.cod} onChange={(c) => cambiarMatArticulo(i, c)} options={opts}
                              placeholder={m.nombre || 'Seleccionar…'} searchPlaceholder="Buscar material..."
                              triggerClassName="!text-[10px] h-7" />
                          </td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-20 ml-auto" value={m.cantidad} onChange={e => setMat(i, 'cantidad', e.target.value)} /></td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-24 ml-auto" value={m.costo} onChange={e => setMat(i, 'costo', e.target.value)} /></td>
                          <td className="px-2 py-1 text-right font-mono">{fmt((parseFloat(m.cantidad)||0) * (parseFloat(m.costo)||0))}</td>
                          <td className="px-1 py-1"><button onClick={() => removeMat(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Otros costos */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="text-[12px] font-semibold text-muted-foreground">OTROS COSTOS</div>
                  <Combobox value="" onChange={addCost} options={optsCosto} placeholder="Agregar costo" searchPlaceholder="Buscar tipo de costo..." variant="link" />
                </div>
                <div className="border border-border rounded-md overflow-x-auto">
                  <table className="w-full text-[12px]">
                    <thead className="bg-muted/30 text-[12px]">
                      <tr><th className="px-2 py-1.5 text-left">Tipo</th><th className="px-2 py-1.5 text-right">Horas</th><th className="px-2 py-1.5 text-right">$/Hora</th><th className="px-2 py-1.5 text-right">Subtotal</th><th className="w-8"></th></tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {preview.otros_costos.map((c, i) => (
                        <tr key={i}>
                          <td className="px-2 py-1 min-w-[504px]">
                            <Combobox value={String(c.tipo_costo_id || '')} onChange={(v) => {
                              const t = tiposCosto.find(x => String(x.tipo_costo_id) === v); if (!t) return
                              const arr = [...preview.otros_costos]
                              arr[i] = { ...arr[i], tipo_costo_id: parseInt(t.tipo_costo_id), nombre: t.nombre }
                              updateAll(preview.materiales, preview.productos, arr)
                            }} options={optsCosto} placeholder={c.nombre || 'Seleccionar tipo…'} searchPlaceholder="Buscar tipo..."
                            triggerClassName="!text-[10px] h-7" />
                          </td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-20 ml-auto" value={c.cantidad} onChange={e => setCost(i, 'cantidad', e.target.value)} /></td>
                          <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-24 ml-auto" value={c.costo} onChange={e => setCost(i, 'costo', e.target.value)} /></td>
                          <td className="px-2 py-1 text-right font-mono">{fmt((parseFloat(c.cantidad)||0) * (parseFloat(c.costo)||0))}</td>
                          <td className="px-1 py-1"><button onClick={() => removeCost(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Totales */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-border">
                <div className="text-center">
                  <div className="text-[12px] text-muted-foreground uppercase">Costo total</div>
                  <div className="font-semibold text-[14px]">${fmt(preview.totales.costo_total)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[12px] text-muted-foreground uppercase">Venta total</div>
                  <div className="font-semibold text-[14px]">${fmt(preview.totales.venta_total)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[12px] text-muted-foreground uppercase">Beneficio</div>
                  <div className={`font-semibold text-[14px] ${preview.totales.beneficio > 0 ? 'text-emerald-500' : 'text-destructive'}`}>${fmt(preview.totales.beneficio)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[12px] text-muted-foreground uppercase">Margen</div>
                  <div className="font-semibold text-[14px]">{preview.totales.venta_total > 0 ? Math.round(preview.totales.beneficio * 100 / preview.totales.venta_total) : 0}%</div>
                </div>
              </div>
            </>
          )}

          {error && (
            <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[13px] text-destructive">{error}</div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-4 sm:px-5 py-3 border-t border-border shrink-0">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={creando}>Cancelar</Button>
          <Button onClick={crear} disabled={creando || !preview}>
            {creando ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Creando OP en Effi (~60s)…</> : <><CheckCircle2 className="h-3.5 w-3.5" /> Crear OP</>}
          </Button>
        </div>
      </div>
    </div>
  )
}
