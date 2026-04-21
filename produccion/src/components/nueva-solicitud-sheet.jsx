import { useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter, SheetClose } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Combobox } from "@/components/ui/combobox"
import { api } from "@/lib/api"

const TIPOS = [
  { value: "", label: "Todos los tipos" },
  { value: "PT", label: "Producto Terminado" },
  { value: "PP", label: "Producto en Proceso" },
  { value: "MP", label: "Materia Prima" },
  { value: "INS", label: "Insumos" },
]

export function NuevaSolicitudSheet({ open, onOpenChange, articulos, onCreated }) {
  const [cod, setCod] = useState("")
  const [cantidad, setCantidad] = useState("")
  const [observaciones, setObservaciones] = useState("")
  const [fechaProgramada, setFechaProgramada] = useState("")
  const [filtroTipo, setFiltroTipo] = useState("")
  const [guardando, setGuardando] = useState(false)

  const articulo = articulos.find(a => a.value === cod)

  const articulosFiltrados = filtroTipo
    ? articulos.filter(a => a.tipo === filtroTipo)
    : articulos

  const reset = () => {
    setCod(""); setCantidad(""); setObservaciones(""); setFechaProgramada(""); setFiltroTipo("")
  }

  const guardar = async () => {
    if (!cod || !cantidad || parseFloat(cantidad) <= 0) return
    setGuardando(true)
    try {
      await api.post('/api/solicitudes', {
        cod_articulo: cod,
        nombre_articulo: articulo.label,
        tipo_articulo: articulo.tipo,
        cantidad: parseFloat(cantidad),
        observaciones: observaciones || null,
        fecha_programada: fechaProgramada || null,
        solicitado_por: 'Jenifer', // TODO: usuario real
      })
      reset()
      onOpenChange(false)
      onCreated?.()
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col">
        <SheetHeader>
          <SheetTitle>Nueva solicitud de producción</SheetTitle>
          <SheetDescription>Programa qué se necesita producir</SheetDescription>
        </SheetHeader>

        <div className="space-y-4 flex-1 overflow-y-auto">
          <div className="space-y-1.5">
            <Label>Tipo de artículo</Label>
            <div className="flex gap-1.5 flex-wrap">
              {TIPOS.map(t => (
                <button
                  key={t.value}
                  onClick={() => setFiltroTipo(t.value)}
                  className={`px-2.5 py-1 rounded-full text-xs border transition-colors cursor-pointer ${
                    filtroTipo === t.value
                      ? 'bg-foreground text-background border-foreground'
                      : 'border-border text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Producto</Label>
            <Combobox
              value={cod}
              onChange={setCod}
              options={articulosFiltrados}
              placeholder="Buscar y seleccionar producto..."
              searchPlaceholder="Escribir nombre o código..."
            />
            {articulo && (
              <p className="text-xs text-muted-foreground pt-1">
                {articulo.subtitle}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Cantidad</Label>
            <Input
              type="number"
              step="0.01"
              value={cantidad}
              onChange={e => setCantidad(e.target.value)}
              placeholder="Ej: 50"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Fecha programada (opcional)</Label>
            <Input
              type="date"
              value={fechaProgramada}
              onChange={e => setFechaProgramada(e.target.value)}
            />
          </div>

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
        </div>

        <SheetFooter>
          <SheetClose asChild>
            <Button variant="ghost">Cancelar</Button>
          </SheetClose>
          <Button
            onClick={guardar}
            disabled={!cod || !cantidad || parseFloat(cantidad) <= 0 || guardando}
          >
            {guardando ? 'Guardando...' : 'Crear solicitud'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
