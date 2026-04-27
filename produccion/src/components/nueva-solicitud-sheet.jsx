import { useEffect, useState } from "react"
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
  const [modo, setModo] = useState("producto")  // "producto" | "grupo"

  // Modo producto
  const [cod, setCod] = useState("")
  const [cantidad, setCantidad] = useState("")
  const [filtroTipo, setFiltroTipo] = useState("")

  // Común
  const [observaciones, setObservaciones] = useState("")
  const [fechaProgramada, setFechaProgramada] = useState("")
  const [guardando, setGuardando] = useState(false)

  // Modo grupo
  const [grupos, setGrupos] = useState([])
  const [grupoSel, setGrupoSel] = useState("")
  const [cantidadesGrupo, setCantidadesGrupo] = useState({})  // {cod: cantidadStr}

  const articulo = articulos.find(a => a.value === cod)
  const articulosFiltrados = filtroTipo ? articulos.filter(a => a.tipo === filtroTipo) : articulos
  const presentacionesGrupo = grupoSel
    ? articulos.filter(a => a.grupo_producto === grupoSel)
    : []

  useEffect(() => {
    if (open && grupos.length === 0) {
      api.get('/api/articulos/grupos').then(setGrupos).catch(() => {})
    }
  }, [open, grupos.length])

  const reset = () => {
    setCod(""); setCantidad(""); setObservaciones(""); setFechaProgramada(""); setFiltroTipo("")
    setGrupoSel(""); setCantidadesGrupo({}); setModo("producto")
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      if (modo === "producto") {
        if (!cod || !cantidad || parseFloat(cantidad) <= 0) return
        await api.post('/api/solicitudes', {
          cod_articulo: cod, nombre_articulo: articulo.label, tipo_articulo: articulo.tipo,
          cantidad: parseFloat(cantidad),
          observaciones: observaciones || null, fecha_programada: fechaProgramada || null,
          solicitado_por: 'Jenifer',
        })
      } else {
        // Modo grupo: crear N solicitudes (1 por presentación con cantidad > 0)
        const items = presentacionesGrupo
          .map(p => ({ cod: p.value, label: p.label, tipo: p.tipo, qty: parseFloat(cantidadesGrupo[p.value] || 0) }))
          .filter(it => it.qty > 0)
        if (items.length === 0) return
        for (const it of items) {
          await api.post('/api/solicitudes', {
            cod_articulo: it.cod, nombre_articulo: it.label, tipo_articulo: it.tipo,
            cantidad: it.qty,
            observaciones: observaciones || null, fecha_programada: fechaProgramada || null,
            solicitado_por: 'Jenifer',
          })
        }
      }
      reset()
      onOpenChange(false)
      onCreated?.()
    } catch (e) {
      alert('Error: ' + e.message)
    } finally {
      setGuardando(false)
    }
  }

  const totalGrupo = Object.values(cantidadesGrupo).filter(v => parseFloat(v) > 0).length
  const puedeGuardar = modo === "producto"
    ? (cod && cantidad && parseFloat(cantidad) > 0)
    : (grupoSel && totalGrupo > 0)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col sm:!max-w-[36rem]">
        <SheetHeader>
          <SheetTitle>Nueva solicitud de producción</SheetTitle>
          <SheetDescription>Programa qué se necesita producir</SheetDescription>
        </SheetHeader>

        <div className="space-y-4 flex-1 overflow-y-auto">
          {/* Toggle modo */}
          <div className="flex gap-1 p-1 bg-muted/40 rounded-md">
            <button
              onClick={() => setModo("producto")}
              className={`flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                modo === "producto" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Por producto
            </button>
            <button
              onClick={() => setModo("grupo")}
              className={`flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                modo === "grupo" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Por grupo
            </button>
          </div>

          {modo === "producto" && (
            <>
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
                  value={cod} onChange={setCod} options={articulosFiltrados}
                  placeholder="Buscar y seleccionar producto..."
                  searchPlaceholder="Escribir nombre o código..."
                />
                {articulo && <p className="text-xs text-muted-foreground pt-1">{articulo.subtitle}</p>}
              </div>

              <div className="space-y-1.5">
                <Label>Cantidad</Label>
                <Input type="number" step="0.01" value={cantidad}
                  onChange={e => setCantidad(e.target.value)} placeholder="Ej: 50" />
              </div>
            </>
          )}

          {modo === "grupo" && (
            <>
              <div className="space-y-1.5">
                <Label>Grupo de producto</Label>
                <Combobox
                  value={grupoSel}
                  onChange={setGrupoSel}
                  options={grupos.map(g => ({ value: g.grupo, label: `${g.grupo} (${g.n_presentaciones} presentaciones)` }))}
                  placeholder="Seleccionar grupo..."
                  searchPlaceholder="Escribir nombre del grupo..."
                />
              </div>

              {grupoSel && presentacionesGrupo.length > 0 && (
                <div className="space-y-1.5">
                  <Label>Presentaciones — escribí cantidad para cada una</Label>
                  <div className="border border-border rounded-md divide-y divide-border max-h-[40vh] overflow-y-auto">
                    {presentacionesGrupo.map(p => (
                      <div key={p.value} className="flex items-center gap-2 px-3 py-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-[13px] truncate">{p.label}</div>
                          <div className="text-[11px] text-muted-foreground font-mono">{p.value}</div>
                        </div>
                        <Input
                          type="number" step="0.01" inputMode="decimal"
                          value={cantidadesGrupo[p.value] || ''}
                          onChange={e => setCantidadesGrupo({...cantidadesGrupo, [p.value]: e.target.value})}
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
          )}

          <div className="space-y-1.5">
            <Label>Fecha programada (opcional)</Label>
            <Input type="date" value={fechaProgramada} onChange={e => setFechaProgramada(e.target.value)} />
          </div>

          <div className="space-y-1.5">
            <Label>Observaciones</Label>
            <textarea
              value={observaciones} onChange={e => setObservaciones(e.target.value)} rows={3}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring placeholder:text-muted-foreground resize-none"
              placeholder="Notas, especificaciones, urgencias..."
            />
          </div>
        </div>

        <SheetFooter>
          <SheetClose asChild>
            <Button variant="ghost">Cancelar</Button>
          </SheetClose>
          <Button onClick={guardar} disabled={!puedeGuardar || guardando}>
            {guardando ? 'Guardando...' : (modo === "grupo" && totalGrupo > 1 ? `Crear ${totalGrupo} solicitudes` : 'Crear solicitud')}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
