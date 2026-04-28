import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { Combobox } from "@/components/ui/combobox"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

const TIPOS_FILTRO = [
  { value: "", label: "Todos" },
  { value: "PT", label: "Producto Terminado" },
  { value: "PP", label: "Producto en Proceso" },
  { value: "MP", label: "Materia Prima" },
  { value: "INS", label: "Insumos" },
]

const ESTADOS = [
  { value: "solicitado", label: "Solicitado" },
  { value: "programando", label: "Programando…" },
  { value: "programado", label: "Programado" },
  { value: "en_produccion", label: "En producción" },
  { value: "producido", label: "Producido" },
  { value: "validado", label: "Validado" },
  { value: "cancelado", label: "Cancelado" },
]

export function DetalleSolicitudSheet({ open, onOpenChange, solicitud, articulos, onSaved }) {
  const esNueva = !solicitud
  const editableProducto = esNueva || solicitud?.estado === 'solicitado'

  const [cod, setCod] = useState("")
  const [cantidad, setCantidad] = useState("")
  const [observaciones, setObservaciones] = useState("")
  const [fechaNecesidad, setFechaNecesidad] = useState("")
  const [fechaProgramada, setFechaProgramada] = useState("")
  const [opEffi, setOpEffi] = useState("")
  const [estado, setEstado] = useState("solicitado")
  const [filtroTipo, setFiltroTipo] = useState("")
  const [guardando, setGuardando] = useState(false)
  // Modo grupo (solo para esNueva)
  const [modo, setModo] = useState("producto")
  const [grupos, setGrupos] = useState([])
  const [grupoSel, setGrupoSel] = useState("")
  const [cantidadesGrupo, setCantidadesGrupo] = useState({})

  useEffect(() => {
    if (solicitud) {
      setCod(solicitud.cod_articulo || "")
      setCantidad(String(solicitud.cantidad || ""))
      setObservaciones(solicitud.observaciones || "")
      setFechaNecesidad(solicitud.fecha_necesidad || "")
      setFechaProgramada(solicitud.fecha_programada || "")
      setOpEffi(solicitud.op_effi || "")
      setEstado(solicitud.estado || "solicitado")
      setFiltroTipo(""); setModo("producto"); setGrupoSel(""); setCantidadesGrupo({})
    } else {
      setCod(""); setCantidad(""); setObservaciones("")
      setFechaNecesidad(""); setFechaProgramada(""); setOpEffi("")
      setEstado("solicitado"); setFiltroTipo("")
      setModo("producto"); setGrupoSel(""); setCantidadesGrupo({})
    }
  }, [solicitud, open])

  useEffect(() => {
    if (open && esNueva && grupos.length === 0) {
      api.get('/api/articulos/grupos').then(setGrupos).catch(() => {})
    }
  }, [open, esNueva, grupos.length])

  const articulo = articulos.find(a => a.value === cod)
  const articulosFiltrados = filtroTipo ? articulos.filter(a => a.tipo === filtroTipo) : articulos
  const presentacionesGrupo = grupoSel ? articulos.filter(a => a.grupo_producto === grupoSel) : []
  const totalGrupo = Object.values(cantidadesGrupo).filter(v => parseFloat(v) > 0).length

  const guardar = async () => {
    setGuardando(true)
    try {
      if (esNueva && modo === "grupo") {
        // Crear N solicitudes (una por presentación con cantidad > 0)
        const items = presentacionesGrupo
          .map(p => ({ cod: p.value, label: p.label, tipo: p.tipo, qty: parseFloat(cantidadesGrupo[p.value] || 0) }))
          .filter(it => it.qty > 0)
        if (items.length === 0) return
        for (const it of items) {
          await api.post('/api/solicitudes', {
            cod_articulo: it.cod, nombre_articulo: it.label, tipo_articulo: it.tipo,
            cantidad: it.qty,
            observaciones: observaciones || null,
            fecha_necesidad: fechaNecesidad || null,
            fecha_programada: fechaProgramada || null,
            solicitado_por: 'Jenifer',
          })
        }
        onOpenChange(false); onSaved?.(); return
      }
      const cantNum = parseFloat(String(cantidad).replace(',', '.'))
      if (!cod || isNaN(cantNum) || cantNum <= 0) return
      if (esNueva) {
        await api.post('/api/solicitudes', {
          cod_articulo: cod,
          nombre_articulo: articulo.label,
          tipo_articulo: articulo.tipo,
          cantidad: cantNum,
          observaciones: observaciones || null,
          fecha_necesidad: fechaNecesidad || null,
          fecha_programada: fechaProgramada || null,
          solicitado_por: 'Jenifer',
        })
      } else {
        const cambios = {
          cantidad: cantNum,
          observaciones: observaciones || null,
          fecha_necesidad: fechaNecesidad || null,
          fecha_programada: fechaProgramada || null,
          op_effi: opEffi || null,
          estado,
        }
        if (editableProducto && cod !== solicitud.cod_articulo) {
          cambios.cod_articulo = cod
          cambios.nombre_articulo = articulo.label
          cambios.tipo_articulo = articulo.tipo
        }
        await api.patch(`/api/solicitudes/${solicitud.id}`, cambios)
      }
      onOpenChange(false)
      onSaved?.()
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setGuardando(false)
    }
  }

  const puedeGuardar = (esNueva && modo === "grupo")
    ? (grupoSel && totalGrupo > 0)
    : (cod && cantidad && parseFloat(String(cantidad).replace(',', '.')) > 0)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col sm:!max-w-[680px]">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle>{esNueva ? 'Nueva solicitud' : `Solicitud #${solicitud.id}`}</SheetTitle>
            {!esNueva && <Badge variant={solicitud.estado}>{ESTADOS.find(e => e.value === solicitud.estado)?.label}</Badge>}
          </div>
          <SheetDescription>{esNueva ? 'Programa qué se necesita producir' : 'Editar solicitud'}</SheetDescription>
        </SheetHeader>

        <div className="space-y-4 flex-1 overflow-y-auto pr-1 -mr-1">
          {esNueva && (
            <div className="flex gap-1 p-1 bg-muted/40 rounded-md">
              <button
                onClick={() => setModo("producto")}
                className={cn(
                  "flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors",
                  modo === "producto" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
                )}
              >Por producto</button>
              <button
                onClick={() => setModo("grupo")}
                className={cn(
                  "flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors",
                  modo === "grupo" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
                )}
              >Por grupo</button>
            </div>
          )}

          {esNueva && modo === "grupo" ? (
            <>
              <div className="space-y-2">
                <Label>Grupo de producto</Label>
                <Combobox
                  value={grupoSel}
                  onChange={setGrupoSel}
                  options={grupos.map(g => ({ value: g.grupo, label: `${g.grupo} (${g.n_presentaciones})` }))}
                  placeholder="Seleccionar grupo..."
                  searchPlaceholder="Escribir nombre del grupo..."
                />
              </div>
              {grupoSel && presentacionesGrupo.length > 0 && (
                <div className="space-y-2">
                  <Label>Presentaciones — escribí cantidad para cada una</Label>
                  <div className="border border-border rounded-md divide-y divide-border max-h-[40vh] overflow-y-auto">
                    {presentacionesGrupo.map(p => (
                      <div key={p.value} className="flex items-center gap-2 px-3 py-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] truncate">{p.label}</div>
                          <div className="text-[11px] text-muted-foreground">{p.subtitle || '—'}</div>
                        </div>
                        <Input
                          type="text" inputMode="decimal"
                          value={cantidadesGrupo[p.value] || ''}
                          onChange={e => setCantidadesGrupo({...cantidadesGrupo, [p.value]: e.target.value.replace(/[^0-9.,]/g, '')})}
                          className="w-24 text-right"
                          placeholder="0"
                        />
                      </div>
                    ))}
                  </div>
                  {totalGrupo > 0 && (
                    <p className="text-xs text-muted-foreground pt-1">
                      Se crearán {totalGrupo} solicitud{totalGrupo === 1 ? '' : 'es'}
                    </p>
                  )}
                </div>
              )}
            </>
          ) : editableProducto ? (
            <>
              <div className="space-y-2">
                <Label>Tipo de artículo</Label>
                <div className="flex gap-2 flex-wrap">
                  {TIPOS_FILTRO.map(t => (
                    <button
                      key={t.value}
                      onClick={() => setFiltroTipo(t.value)}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-[12px] font-medium border transition-all cursor-pointer",
                        filtroTipo === t.value
                          ? 'bg-primary/10 text-primary border-primary/30'
                          : 'bg-background border-border text-muted-foreground hover:text-foreground hover:border-border/80'
                      )}
                    >{t.label}</button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Producto</Label>
                <Combobox
                  value={cod}
                  onChange={setCod}
                  options={articulosFiltrados}
                  placeholder="Buscar y seleccionar..."
                  searchPlaceholder="Escribir nombre o código..."
                  showCode
                  multiline
                  triggerClassName="!text-[11px]"
                />
                {articulo && <p className="text-xs text-muted-foreground pt-1">{articulo.subtitle}</p>}
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <Label>Producto</Label>
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
                <div>{solicitud?.nombre_articulo}</div>
                <div className="text-xs text-muted-foreground mt-0.5">Cód {solicitud?.cod_articulo} · {solicitud?.tipo_articulo || '—'}</div>
              </div>
              <p className="text-[11px] text-muted-foreground">No editable — la solicitud ya no está en estado "Solicitado"</p>
            </div>
          )}

          {!(esNueva && modo === "grupo") && (
            <div className="space-y-2">
              <Label>Cantidad</Label>
              <Input
                type="text"
                inputMode="decimal"
                value={cantidad}
                onChange={e => setCantidad(e.target.value.replace(/[^0-9.,]/g, ''))}
                placeholder="Ej: 50"
                disabled={!esNueva && solicitud?.estado !== 'solicitado'}
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Necesidad para</Label>
              <Input
                type="date"
                value={fechaNecesidad}
                onChange={e => setFechaNecesidad(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Fecha en que se necesita</p>
            </div>
            <div className="space-y-2">
              <Label>Programada</Label>
              <Input
                type="date"
                value={fechaProgramada}
                onChange={e => setFechaProgramada(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Cuándo se produce</p>
            </div>
          </div>

          {!esNueva && (
            <>
              <div className="space-y-2">
                <Label>Estado</Label>
                <select
                  value={estado}
                  onChange={e => setEstado(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-[13px] cursor-pointer outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  {ESTADOS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label>OP Effi (opcional)</Label>
                <Input
                  value={opEffi}
                  onChange={e => setOpEffi(e.target.value)}
                  placeholder="Ej: 2163"
                />
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label>Observaciones</Label>
            <textarea
              value={observaciones}
              onChange={e => setObservaciones(e.target.value)}
              rows={4}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring placeholder:text-muted-foreground resize-none"
              placeholder="Notas, especificaciones, urgencias..."
            />
          </div>

          {!esNueva && (
            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
              <div>Solicitada por <strong>{solicitud.solicitado_por}</strong></div>
              <div>El {solicitud.fecha_solicitud?.slice(0, 16)}</div>
            </div>
          )}
        </div>

        <SheetFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={guardar} disabled={!puedeGuardar || guardando}>
            {guardando ? 'Guardando...' : (esNueva && modo === "grupo" && totalGrupo > 1)
              ? `Crear ${totalGrupo} solicitudes`
              : esNueva ? 'Crear solicitud' : 'Guardar cambios'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
