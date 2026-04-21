import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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

  useEffect(() => {
    if (solicitud) {
      setCod(solicitud.cod_articulo || "")
      setCantidad(String(solicitud.cantidad || ""))
      setObservaciones(solicitud.observaciones || "")
      setFechaNecesidad(solicitud.fecha_necesidad || "")
      setFechaProgramada(solicitud.fecha_programada || "")
      setOpEffi(solicitud.op_effi || "")
      setEstado(solicitud.estado || "solicitado")
      setFiltroTipo("")
    } else {
      setCod(""); setCantidad(""); setObservaciones("")
      setFechaNecesidad(""); setFechaProgramada(""); setOpEffi("")
      setEstado("solicitado"); setFiltroTipo("")
    }
  }, [solicitud, open])

  const articulo = articulos.find(a => a.value === cod)
  const articulosFiltrados = filtroTipo ? articulos.filter(a => a.tipo === filtroTipo) : articulos

  const guardar = async () => {
    const cantNum = parseFloat(String(cantidad).replace(',', '.'))
    if (!cod || isNaN(cantNum) || cantNum <= 0) return
    setGuardando(true)
    try {
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

  const puedeGuardar = cod && cantidad && parseFloat(String(cantidad).replace(',', '.')) > 0

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle>{esNueva ? 'Nueva solicitud' : `Solicitud #${solicitud.id}`}</SheetTitle>
            {!esNueva && <Badge variant={solicitud.estado}>{ESTADOS.find(e => e.value === solicitud.estado)?.label}</Badge>}
          </div>
          <SheetDescription>{esNueva ? 'Programa qué se necesita producir' : 'Editar solicitud'}</SheetDescription>
        </SheetHeader>

        <div className="space-y-4 flex-1 overflow-y-auto pr-1 -mr-1">
          {editableProducto ? (
            <>
              <div className="space-y-1.5">
                <Label>Tipo de artículo</Label>
                <div className="flex gap-1.5 flex-wrap">
                  {TIPOS_FILTRO.map(t => (
                    <button
                      key={t.value}
                      onClick={() => setFiltroTipo(t.value)}
                      className={`px-2.5 py-1 rounded-full text-xs border transition-colors cursor-pointer ${
                        filtroTipo === t.value
                          ? 'bg-foreground text-background border-foreground'
                          : 'border-border text-muted-foreground hover:text-foreground'
                      }`}
                    >{t.label}</button>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Producto</Label>
                <Combobox
                  value={cod}
                  onChange={setCod}
                  options={articulosFiltrados}
                  placeholder="Buscar y seleccionar..."
                  searchPlaceholder="Escribir nombre o código..."
                />
                {articulo && <p className="text-xs text-muted-foreground pt-1">{articulo.subtitle}</p>}
              </div>
            </>
          ) : (
            <div className="space-y-1.5">
              <Label>Producto</Label>
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
                <div>{solicitud?.nombre_articulo}</div>
                <div className="text-xs text-muted-foreground mt-0.5">Cód {solicitud?.cod_articulo} · {solicitud?.tipo_articulo || '—'}</div>
              </div>
              <p className="text-[11px] text-muted-foreground">No editable — la solicitud ya no está en estado "Solicitado"</p>
            </div>
          )}

          <div className="space-y-1.5">
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

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Necesidad</Label>
              <Input
                type="date"
                value={fechaNecesidad}
                onChange={e => setFechaNecesidad(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">Para cuándo lo necesita</p>
            </div>
            <div className="space-y-1.5">
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
              <div className="space-y-1.5">
                <Label>Estado</Label>
                <select
                  value={estado}
                  onChange={e => setEstado(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm cursor-pointer outline-none focus:ring-1 focus:ring-ring"
                >
                  {ESTADOS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>OP Effi (opcional)</Label>
                <Input
                  value={opEffi}
                  onChange={e => setOpEffi(e.target.value)}
                  placeholder="Ej: 2163"
                />
              </div>
            </>
          )}

          <div className="space-y-1.5">
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
            {guardando ? 'Guardando...' : esNueva ? 'Crear solicitud' : 'Guardar cambios'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
