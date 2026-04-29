import { useCallback, useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router"
import { ChevronLeft, CheckCircle2, AlertCircle, Trash2, Save, RotateCcw } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Combobox } from "@/components/ui/combobox"
import { api } from "@/lib/api"

function Money({ v }) {
  const n = Number(v || 0)
  return <span className="font-mono tabular-nums">${n.toLocaleString('es-CO', { maximumFractionDigits: 2 })}</span>
}

const fmt = (n) => Math.round(Number(n) || 0).toLocaleString('es-CO')

export function RecetaDetallePage() {
  const { cod } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notas, setNotas] = useState('')
  const [obsOp, setObsOp] = useState('')
  const [articulos, setArticulos] = useState([])
  const [tiposCosto, setTiposCosto] = useState([])
  const [mats, setMats] = useState([])
  const [costos, setCostos] = useState([])
  const [prods, setProds] = useState([])
  const [puntos, setPuntos] = useState([])
  const [unidades, setUnidades] = useState([])
  const [dirty, setDirty] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`/api/recetas/${cod}`)
      setR(data)
      setNotas(data.notas_analisis || '')
      setObsOp(data.observaciones_op || '')
      setMats((data.materiales || []).map(m => ({
        cod_material: m.cod_material, nombre: m.nombre,
        cantidad_por_lote: m.cantidad_por_lote, costo_unit_snapshot: m.costo_unit_snapshot,
      })))
      setCostos((data.costos || []).map(c => ({
        tipo_costo_id: c.tipo_costo_id, nombre: c.nombre,
        cantidad_por_lote: c.cantidad_por_lote, costo_unit: c.costo_unit,
      })))
      setProds((data.productos || []).map(p => ({
        cod_articulo: p.cod_articulo, nombre: p.nombre, es_principal: !!p.es_principal,
        cantidad_por_lote: p.cantidad_por_lote, precio_min_venta_snapshot: p.precio_min_venta_snapshot,
      })))
      setPuntos((data.puntos_criticos || []).map(p => ({
        parametro: p.parametro || '', tipo: p.tipo || 'numerico',
        unidad: p.unidad || '', instrumento: p.instrumento || '',
        valor_min: p.valor_min, valor_max: p.valor_max,
        opciones_json: p.opciones_json || '', obligatorio: !!p.obligatorio, orden: p.orden || 0,
      })))
      setDirty(false)
    } catch { setR(null) }
    finally { setLoading(false) }
  }, [cod])

  useEffect(() => { cargar() }, [cargar])

  // Refrescar al terminar Sync Effi global
  useEffect(() => {
    const h = () => cargar()
    window.addEventListener('effi-synced', h)
    return () => window.removeEventListener('effi-synced', h)
  }, [cargar])

  useEffect(() => {
    api.get('/api/articulos').then(d => setArticulos(d.map(a => ({
      value: a.cod, label: `${a.cod} — ${a.nombre}`, nombre: a.nombre, costo_manual: a.costo_manual,
    })))).catch(() => {})
    api.get('/api/produccion/tipos-costo').then(setTiposCosto).catch(() => {})
    api.get('/api/produccion/unidades').then(setUnidades).catch(() => {})
  }, [])

  const opts = articulos
  const optsCosto = tiposCosto.map(t => ({ value: String(t.tipo_costo_id), label: `${t.tipo_costo_id} — ${t.nombre}`, nombre: t.nombre }))

  const setMat = (i, k, v) => { const a = [...mats]; a[i] = {...a[i], [k]: v}; setMats(a); setDirty(true) }
  const cambiarMat = (i, nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    const arr = [...mats]
    arr[i] = { ...arr[i], cod_material: nuevoCod, nombre: a.nombre, costo_unit_snapshot: a.costo_manual || 0 }
    setMats(arr); setDirty(true)
  }
  const removeMat = i => { setMats(mats.filter((_, j) => j !== i)); setDirty(true) }
  const addMat = (nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    setMats([...mats, { cod_material: nuevoCod, nombre: a.nombre, cantidad_por_lote: 1, costo_unit_snapshot: a.costo_manual || 0 }])
    setDirty(true)
  }

  const setProd = (i, k, v) => { const a = [...prods]; a[i] = {...a[i], [k]: v}; setProds(a); setDirty(true) }
  const cambiarProd = (i, nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    const arr = [...prods]
    arr[i] = { ...arr[i], cod_articulo: nuevoCod, nombre: a.nombre }
    setProds(arr); setDirty(true)
  }
  const removeProd = i => { setProds(prods.filter((_, j) => j !== i)); setDirty(true) }
  const addProd = (nuevoCod) => {
    const a = articulos.find(x => x.value === nuevoCod); if (!a) return
    setProds([...prods, { cod_articulo: nuevoCod, nombre: a.nombre, es_principal: false, cantidad_por_lote: 1, precio_min_venta_snapshot: 0 }])
    setDirty(true)
  }

  const setPunto = (i, k, v) => { const a = [...puntos]; a[i] = {...a[i], [k]: v}; setPuntos(a); setDirty(true) }
  const removePunto = i => { setPuntos(puntos.filter((_, j) => j !== i)); setDirty(true) }
  const addPunto = () => {
    setPuntos([...puntos, { parametro: '', tipo: 'numerico', unidad: '', instrumento: '',
      valor_min: null, valor_max: null, opciones_json: '', obligatorio: true, orden: puntos.length }])
    setDirty(true)
  }

  const setCost = (i, k, v) => { const a = [...costos]; a[i] = {...a[i], [k]: v}; setCostos(a); setDirty(true) }
  const cambiarCost = (i, nuevoTipoStr) => {
    const t = tiposCosto.find(x => String(x.tipo_costo_id) === nuevoTipoStr); if (!t) return
    const arr = [...costos]
    arr[i] = { ...arr[i], tipo_costo_id: parseInt(t.tipo_costo_id), nombre: t.nombre }
    setCostos(arr); setDirty(true)
  }
  const removeCost = i => { setCostos(costos.filter((_, j) => j !== i)); setDirty(true) }
  const addCost = (tipoStr) => {
    const t = tiposCosto.find(x => String(x.tipo_costo_id) === tipoStr); if (!t) return
    setCostos([...costos, { tipo_costo_id: parseInt(t.tipo_costo_id), nombre: t.nombre, cantidad_por_lote: 1, costo_unit: t.tipo_costo_id === 13 ? 7000 : 0 }])
    setDirty(true)
  }

  const guardarTodo = async () => {
    setSaving(true)
    try {
      await api.put(`/api/recetas/${cod}/full`, {
        materiales: mats.map(m => ({
          cod_material: String(m.cod_material), nombre: m.nombre,
          cantidad_por_lote: parseFloat(m.cantidad_por_lote) || 0,
          costo_unit_snapshot: parseFloat(m.costo_unit_snapshot) || 0,
        })),
        costos: costos.map(c => ({
          tipo_costo_id: parseInt(c.tipo_costo_id), nombre: c.nombre,
          cantidad_por_lote: parseFloat(c.cantidad_por_lote) || 0,
          costo_unit: parseFloat(c.costo_unit) || 0,
        })),
        productos: prods.map(p => ({
          cod_articulo: String(p.cod_articulo), nombre: p.nombre, es_principal: !!p.es_principal,
          cantidad_por_lote: parseFloat(p.cantidad_por_lote) || 0,
          precio_min_venta_snapshot: parseFloat(p.precio_min_venta_snapshot) || 0,
        })),
        puntos_criticos: puntos.filter(p => (p.parametro || '').trim()).map((p, i) => ({
          parametro: p.parametro.trim(),
          tipo: p.tipo || 'numerico',
          unidad: p.unidad || null,
          instrumento: p.instrumento || null,
          valor_min: p.valor_min === '' || p.valor_min == null ? null : parseFloat(p.valor_min),
          valor_max: p.valor_max === '' || p.valor_max == null ? null : parseFloat(p.valor_max),
          opciones_json: p.opciones_json || null,
          obligatorio: !!p.obligatorio,
          orden: p.orden || i,
        })),
      })
      await cargar()
    } finally { setSaving(false) }
  }

  const patch = async (body) => { setSaving(true); try { await api.patch(`/api/recetas/${cod}`, body); await cargar() } finally { setSaving(false) } }
  const validar = () => patch({ estado: 'validada' })
  const devolverBorrador = () => patch({ estado: 'borrador' })
  const guardarNotas = () => patch({ notas_analisis: notas })
  const guardarObsOp = () => patch({ observaciones_op: obsOp })

  if (loading) return <div className="p-5 text-muted-foreground">Cargando receta {cod}…</div>
  if (!r) return <div className="p-5 text-red-500">Receta no encontrada para cod={cod}</div>

  const principal = prods.find(p => p.es_principal) || null
  const costoMateriales = mats.reduce((s, m) => s + (parseFloat(m.cantidad_por_lote)||0) * (parseFloat(m.costo_unit_snapshot)||0), 0)
  const costoProd = costos.reduce((s, c) => s + (parseFloat(c.cantidad_por_lote)||0) * (parseFloat(c.costo_unit)||0), 0)
  const ventaTotal = principal ? (parseFloat(principal.cantidad_por_lote)||0) * (parseFloat(principal.precio_min_venta_snapshot)||0) : 0
  const beneficio = ventaTotal - costoMateriales - costoProd
  const margenPct = ventaTotal ? (beneficio / ventaTotal * 100) : 0

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/recetas')}>
          <ChevronLeft className="h-4 w-4" /> Volver
        </Button>
        {dirty && (
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={cargar} disabled={saving}>
              <RotateCcw className="h-4 w-4" /> Descartar
            </Button>
            <Button size="sm" onClick={guardarTodo} disabled={saving}>
              <Save className="h-4 w-4" /> {saving ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </div>
        )}
      </div>

      <div className="mb-5">
        <h1 className="text-[16px] sm:text-[18px] font-semibold">{r.nombre}</h1>
        <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-0.5">
          cod <span className="font-mono">{r.cod_articulo}</span> · <span className="capitalize">{r.familia}</span> · <span className="font-mono">{r.patron}</span>
        </p>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <Badge variant={r.estado === 'validada' ? 'programado' : 'solicitado'}>{r.estado}</Badge>
          <Badge variant="outline">{r.confianza}</Badge>
          <Badge variant="outline">{r.n_ops_analizadas} OPs</Badge>
          <div className="flex gap-2 sm:ml-auto">
            {r.estado !== 'validada' && (
              <Button size="sm" variant="outline" onClick={validar} disabled={saving}>
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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
        <Card label="Costo materiales"><Money v={costoMateriales} /></Card>
        <Card label="Costo producción"><Money v={costoProd} /></Card>
        <Card label="Venta total"><Money v={ventaTotal} /></Card>
        <Card label="Beneficio"><span className={beneficio > 0 ? 'text-emerald-600' : 'text-red-500'}><Money v={beneficio} /> ({margenPct.toFixed(1)}%)</span></Card>
      </div>

      {/* Materiales */}
      <Seccion titulo="Materiales" action={
        <Combobox value="" onChange={addMat} options={opts} placeholder="Agregar material" searchPlaceholder="Buscar material..." variant="link" />
      }>
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-2 py-1.5 text-left">Cód</th>
                <th className="px-2 py-1.5 text-left">Material</th>
                <th className="px-2 py-1.5 text-right">Cantidad</th>
                <th className="px-2 py-1.5 text-right">Costo unit</th>
                <th className="px-2 py-1.5 text-right">Subtotal</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {mats.map((m, i) => (
                <tr key={i}>
                  <td className="px-2 py-1 font-mono text-[12px]">{m.cod_material}</td>
                  <td className="px-2 py-1 max-w-[140px] sm:max-w-none md:min-w-[420px]">
                    <Combobox value={String(m.cod_material)} onChange={(c) => cambiarMat(i, c)} options={opts}
                      placeholder={m.nombre || 'Seleccionar…'} searchPlaceholder="Buscar material..."
                      triggerClassName="!text-[10px] h-7" />
                  </td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-14 sm:w-24 ml-auto" value={m.cantidad_por_lote} onChange={e => setMat(i, 'cantidad_por_lote', e.target.value)} /></td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-14 sm:w-24 ml-auto" value={m.costo_unit_snapshot} onChange={e => setMat(i, 'costo_unit_snapshot', e.target.value)} /></td>
                  <td className="px-2 py-1 text-right font-mono">${fmt((parseFloat(m.cantidad_por_lote)||0) * (parseFloat(m.costo_unit_snapshot)||0))}</td>
                  <td className="px-1 py-1"><button onClick={() => removeMat(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                </tr>
              ))}
              {mats.length === 0 && (
                <tr><td colSpan={6} className="py-2 text-center text-muted-foreground italic">Sin materiales</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Seccion>

      {/* Productos */}
      <Seccion titulo="Productos" action={
        <Combobox value="" onChange={addProd} options={opts} placeholder="Agregar producto" searchPlaceholder="Buscar producto..." variant="link" />
      }>
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-2 py-1.5 text-left">Cód</th>
                <th className="px-2 py-1.5 text-left">Producto</th>
                <th className="px-2 py-1.5 text-center">Principal</th>
                <th className="px-2 py-1.5 text-right">Cantidad</th>
                <th className="px-2 py-1.5 text-right">Precio venta</th>
                <th className="px-2 py-1.5 text-right">Subtotal</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {prods.map((p, i) => (
                <tr key={i}>
                  <td className="px-2 py-1 font-mono text-[12px]">{p.es_principal && '★ '}{p.cod_articulo}</td>
                  <td className="px-2 py-1 max-w-[140px] sm:max-w-none md:min-w-[420px]">
                    <Combobox value={String(p.cod_articulo)} onChange={(c) => cambiarProd(i, c)} options={opts}
                      placeholder={p.nombre || 'Seleccionar…'} searchPlaceholder="Buscar producto..."
                      triggerClassName="!text-[10px] h-7" />
                  </td>
                  <td className="px-2 py-1 text-center">
                    <input type="radio" checked={!!p.es_principal} onChange={() => {
                      setProds(prods.map((x, j) => ({ ...x, es_principal: i === j })))
                      setDirty(true)
                    }} className="accent-primary" />
                  </td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-14 sm:w-24 ml-auto" value={p.cantidad_por_lote} onChange={e => setProd(i, 'cantidad_por_lote', e.target.value)} /></td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-16 sm:w-28 ml-auto" value={p.precio_min_venta_snapshot} onChange={e => setProd(i, 'precio_min_venta_snapshot', e.target.value)} /></td>
                  <td className="px-2 py-1 text-right font-mono">${fmt((parseFloat(p.cantidad_por_lote)||0) * (parseFloat(p.precio_min_venta_snapshot)||0))}</td>
                  <td className="px-1 py-1"><button onClick={() => removeProd(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                </tr>
              ))}
              {prods.length === 0 && (
                <tr><td colSpan={7} className="py-2 text-center text-muted-foreground italic">Sin productos</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Seccion>

      {/* Costos de producción */}
      <Seccion titulo="Costos de producción" action={
        <Combobox value="" onChange={addCost} options={optsCosto} placeholder="Agregar costo" searchPlaceholder="Buscar tipo..." variant="link" />
      }>
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-2 py-1.5 text-left">Tipo</th>
                <th className="px-2 py-1.5 text-right">Cantidad</th>
                <th className="px-2 py-1.5 text-right">Costo unit</th>
                <th className="px-2 py-1.5 text-right">Subtotal</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {costos.map((c, i) => (
                <tr key={i}>
                  <td className="px-2 py-1 max-w-[140px] sm:max-w-none md:min-w-[420px]">
                    <Combobox value={String(c.tipo_costo_id)} onChange={(v) => cambiarCost(i, v)} options={optsCosto}
                      placeholder={c.nombre || 'Seleccionar…'} searchPlaceholder="Buscar tipo..."
                      triggerClassName="!text-[10px] h-7" />
                  </td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-14 sm:w-24 ml-auto" value={c.cantidad_por_lote} onChange={e => setCost(i, 'cantidad_por_lote', e.target.value)} /></td>
                  <td className="px-2 py-1"><Input className="h-7 text-right text-[12px] w-14 sm:w-24 ml-auto" value={c.costo_unit} onChange={e => setCost(i, 'costo_unit', e.target.value)} /></td>
                  <td className="px-2 py-1 text-right font-mono">${fmt((parseFloat(c.cantidad_por_lote)||0) * (parseFloat(c.costo_unit)||0))}</td>
                  <td className="px-1 py-1"><button onClick={() => removeCost(i)} className="text-muted-foreground hover:text-destructive p-1"><Trash2 className="h-3 w-3" /></button></td>
                </tr>
              ))}
              {costos.length === 0 && (
                <tr><td colSpan={5} className="py-2 text-center text-muted-foreground italic">Sin costos de producción</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Seccion>

      {/* Puntos críticos de control (configurables por producto) */}
      <Seccion titulo="Puntos críticos" action={
        <button onClick={addPunto} className="text-[12px] text-primary hover:underline cursor-pointer">+ Agregar</button>
      }>
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-2 py-1.5 text-left">Parámetro</th>
                <th className="px-2 py-1.5 text-left">Tipo</th>
                <th className="px-2 py-1.5 text-left">Unidad</th>
                <th className="px-2 py-1.5 text-left">Instrumento</th>
                <th className="px-2 py-1.5 text-right">Mín</th>
                <th className="px-2 py-1.5 text-right">Máx</th>
                <th className="px-2 py-1.5 text-left">Opciones (CSV)</th>
                <th className="px-2 py-1.5 text-center">Oblig.</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {puntos.map((p, i) => (
                <tr key={i}>
                  <td className="px-2 py-1">
                    <Input className="h-7 text-[12px]" placeholder="Ej: Temperatura templado"
                      value={p.parametro} onChange={e => setPunto(i, 'parametro', e.target.value)} />
                  </td>
                  <td className="px-2 py-1">
                    <select value={p.tipo} onChange={e => setPunto(i, 'tipo', e.target.value)}
                      className="h-7 text-[12px] bg-background border border-border rounded px-1">
                      <option value="numerico">Numérico</option>
                      <option value="booleano">Booleano</option>
                      <option value="texto">Texto</option>
                      <option value="seleccion">Selección</option>
                    </select>
                  </td>
                  <td className="px-2 py-1 min-w-[160px]">
                    {p.tipo === 'numerico' ? (
                      <Combobox value={p.unidad || ''} onChange={(v) => setPunto(i, 'unidad', v)}
                        options={unidades.map(u => ({ value: u.simbolo, label: `${u.simbolo} — ${u.nombre || u.categoria}` }))}
                        placeholder="—" searchPlaceholder="Buscar unidad..."
                        triggerClassName="!text-[11px] h-7 w-full" />
                    ) : <span className="text-muted-foreground/40 text-[11px]">—</span>}
                  </td>
                  <td className="px-2 py-1">
                    <Input className="h-7 text-[12px] w-32" placeholder="Termómetro, gramera..." list={`instr-${i}`}
                      value={p.instrumento || ''} onChange={e => setPunto(i, 'instrumento', e.target.value)} />
                    <datalist id={`instr-${i}`}>
                      <option value="Termómetro" />
                      <option value="Gramera" />
                      <option value="Cronómetro" />
                      <option value="Refractómetro" />
                      <option value="pH-metro" />
                      <option value="Higrómetro" />
                      <option value="Visual" />
                      <option value="Cuchillo (test templado)" />
                    </datalist>
                  </td>
                  <td className="px-2 py-1">
                    <Input className="h-7 text-right text-[12px] w-20 ml-auto" disabled={p.tipo !== 'numerico'}
                      value={p.valor_min ?? ''} onChange={e => setPunto(i, 'valor_min', e.target.value)} />
                  </td>
                  <td className="px-2 py-1">
                    <Input className="h-7 text-right text-[12px] w-20 ml-auto" disabled={p.tipo !== 'numerico'}
                      value={p.valor_max ?? ''} onChange={e => setPunto(i, 'valor_max', e.target.value)} />
                  </td>
                  <td className="px-2 py-1">
                    <Input className="h-7 text-[12px]" placeholder="Claro,Medio,Oscuro" disabled={p.tipo !== 'seleccion'}
                      value={p.opciones_json || ''} onChange={e => setPunto(i, 'opciones_json', e.target.value)} />
                  </td>
                  <td className="px-2 py-1 text-center">
                    <input type="checkbox" checked={!!p.obligatorio}
                      onChange={e => setPunto(i, 'obligatorio', e.target.checked)} className="accent-primary" />
                  </td>
                  <td className="px-1 py-1">
                    <button onClick={() => removePunto(i)} className="text-muted-foreground hover:text-destructive p-1">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </td>
                </tr>
              ))}
              {puntos.length === 0 && (
                <tr><td colSpan={9} className="py-2 text-center text-muted-foreground italic">
                  Sin puntos críticos. Agregá los parámetros que deben validarse al producir este producto (ej: temperatura, tiempo, pH).
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Seccion>

      {/* Observaciones para Effi (texto fijo que precarga el preview de OP) */}
      <Seccion titulo="Observaciones para Effi">
        <textarea
          value={obsOp}
          onChange={(e) => setObsOp(e.target.value)}
          placeholder="Texto que se inyecta en la observación de la OP en Effi cada vez que se programa este producto. Ej: Templar a 45°C, sellar al vacío"
          className="w-full min-h-[80px] bg-background border border-border rounded p-2 text-[12px]"
        />
        <div className="flex items-center justify-between mt-2">
          <div className="text-[11px] text-muted-foreground">Editable; el usuario puede ajustarlo en cada OP.</div>
          <Button size="sm" variant="outline" onClick={guardarObsOp} disabled={saving || obsOp === (r.observaciones_op || '')}>
            Guardar observaciones
          </Button>
        </div>
      </Seccion>

      {/* Notas */}
      <Seccion titulo="Razonamiento / análisis">
        <textarea
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          className="w-full min-h-[100px] bg-background border border-border rounded p-2 text-[12px] font-mono"
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

function Seccion({ titulo, action, children }) {
  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide">{titulo}</h2>
        {action}
      </div>
      {children}
    </div>
  )
}
