import { useEffect, useState, useMemo } from "react"
import { Plus, Trash2, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { NuevaSolicitudSheet } from "@/components/nueva-solicitud-sheet"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

const ESTADOS = [
  { value: "solicitado", label: "Solicitado" },
  { value: "programado", label: "Programado" },
  { value: "en_produccion", label: "En producción" },
  { value: "producido", label: "Producido" },
  { value: "validado", label: "Validado" },
  { value: "cancelado", label: "Cancelado" },
]

export function SolicitudesPage() {
  const [solicitudes, setSolicitudes] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroEstado, setFiltroEstado] = useState(null)
  const [busqueda, setBusqueda] = useState("")
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [articulos, setArticulos] = useState([])

  const cargar = async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/solicitudes?_end=500')
      setSolicitudes(data)
    } finally {
      setLoading(false)
    }
  }

  const cargarArticulos = async () => {
    const data = await api.get('/api/articulos')
    setArticulos(data.map(a => ({
      value: a.cod,
      label: a.nombre,
      subtitle: `Stock: ${a.stock}${a.unidad ? ' ' + a.unidad : ''}`,
      badge: a.tipo,
      tipo: a.tipo,
    })))
  }

  useEffect(() => { cargar(); cargarArticulos() }, [])

  const filtradas = useMemo(() => {
    let data = solicitudes
    if (filtroEstado) data = data.filter(s => s.estado === filtroEstado)
    if (busqueda.trim()) {
      const q = busqueda.toLowerCase()
      data = data.filter(s =>
        s.nombre_articulo.toLowerCase().includes(q) ||
        String(s.cod_articulo).includes(q)
      )
    }
    return data
  }, [solicitudes, filtroEstado, busqueda])

  const conteos = useMemo(() => {
    const c = { solicitado: 0, programado: 0, en_produccion: 0, producido: 0, validado: 0, cancelado: 0 }
    solicitudes.forEach(s => { if (c[s.estado] !== undefined) c[s.estado]++ })
    return c
  }, [solicitudes])

  const actualizar = async (id, cambios) => {
    try {
      await api.patch(`/api/solicitudes/${id}`, cambios)
      await cargar()
    } catch (e) {
      alert('Error: ' + e.message)
    }
  }

  const eliminar = async (id) => {
    if (!confirm('¿Eliminar esta solicitud?')) return
    await api.del(`/api/solicitudes/${id}`)
    await cargar()
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Solicitudes de Producción</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Programa qué producir y seguimiento hasta validación
          </p>
        </div>
        <Button onClick={() => setDrawerOpen(true)} className="cursor-pointer">
          <Plus className="h-4 w-4" />
          Nueva solicitud
        </Button>
      </div>

      {/* Filtros tipo pills */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setFiltroEstado(null)}
          className={cn(
            "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors cursor-pointer",
            !filtroEstado ? "bg-foreground text-background border-foreground" : "border-border text-muted-foreground hover:text-foreground"
          )}
        >
          Todas <span className="ml-1 opacity-60">{solicitudes.length}</span>
        </button>
        {ESTADOS.map(e => (
          <button
            key={e.value}
            onClick={() => setFiltroEstado(filtroEstado === e.value ? null : e.value)}
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-medium border transition-colors cursor-pointer",
              filtroEstado === e.value
                ? "bg-foreground text-background border-foreground"
                : "border-border text-muted-foreground hover:text-foreground"
            )}
          >
            {e.label} <span className="ml-1 opacity-60">{conteos[e.value] || 0}</span>
          </button>
        ))}

        <div className="flex-1" />

        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            placeholder="Buscar producto..."
            className="pl-9 w-64"
          />
        </div>
      </div>

      {/* Tabla */}
      <div className="rounded-lg border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-20">Cód</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5">Producto</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-20">Tipo</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-right px-4 py-2.5 w-28">Cantidad</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-40">Estado</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-32">Programada</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-28">Solicitante</th>
                <th className="text-xs font-semibold uppercase text-muted-foreground text-left px-4 py-2.5 w-24">OP Effi</th>
                <th className="px-4 py-2.5 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="9" className="text-center py-12 text-muted-foreground">Cargando...</td></tr>
              ) : filtradas.length === 0 ? (
                <tr><td colSpan="9" className="text-center py-12 text-muted-foreground">Sin solicitudes</td></tr>
              ) : filtradas.map(s => (
                <SolicitudRow
                  key={s.id}
                  solicitud={s}
                  articulos={articulos}
                  onUpdate={(cambios) => actualizar(s.id, cambios)}
                  onDelete={() => eliminar(s.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <NuevaSolicitudSheet
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        articulos={articulos}
        onCreated={cargar}
      />
    </div>
  )
}

function SolicitudRow({ solicitud, articulos, onUpdate, onDelete }) {
  const [editingCant, setEditingCant] = useState(false)
  const [cantValue, setCantValue] = useState(solicitud.cantidad)
  const editable = solicitud.estado === 'solicitado'

  const saveCant = () => {
    const n = parseFloat(cantValue)
    if (isNaN(n) || n <= 0) { setCantValue(solicitud.cantidad); setEditingCant(false); return }
    if (n !== solicitud.cantidad) onUpdate({ cantidad: n })
    setEditingCant(false)
  }

  return (
    <tr className="border-b border-border hover:bg-accent/30 transition-colors group">
      <td className="px-4 py-2.5 text-sm text-muted-foreground">{solicitud.cod_articulo}</td>
      <td className="px-4 py-2.5 text-sm">
        {editable ? (
          <select
            value={solicitud.cod_articulo}
            onChange={e => {
              const art = articulos.find(a => a.value === e.target.value)
              if (art) onUpdate({ cod_articulo: art.value, nombre_articulo: art.label, tipo_articulo: art.tipo })
            }}
            className="bg-transparent w-full cursor-pointer hover:bg-accent/50 px-1 -mx-1 rounded outline-none"
          >
            <option value={solicitud.cod_articulo}>{solicitud.nombre_articulo}</option>
            {articulos.map(a => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        ) : solicitud.nombre_articulo}
      </td>
      <td className="px-4 py-2.5 text-xs">
        <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{solicitud.tipo_articulo || '—'}</span>
      </td>
      <td className="px-4 py-2.5 text-sm text-right font-mono">
        {editable && editingCant ? (
          <input
            type="number"
            step="0.01"
            autoFocus
            value={cantValue}
            onChange={e => setCantValue(e.target.value)}
            onBlur={saveCant}
            onKeyDown={e => { if (e.key === 'Enter') saveCant(); if (e.key === 'Escape') { setCantValue(solicitud.cantidad); setEditingCant(false) } }}
            className="w-24 bg-transparent border border-primary rounded px-2 py-0.5 text-right outline-none"
          />
        ) : (
          <span
            onClick={() => editable && setEditingCant(true)}
            className={cn(editable && "cursor-pointer hover:bg-accent/50 px-2 py-0.5 -mx-2 rounded")}
          >
            {solicitud.cantidad}
          </span>
        )}
      </td>
      <td className="px-4 py-2.5">
        <Select value={solicitud.estado} onValueChange={v => onUpdate({ estado: v })}>
          <SelectTrigger className="h-7 text-xs w-full border-0 bg-transparent hover:bg-accent/50 shadow-none px-2 gap-1.5 cursor-pointer">
            <Badge variant={solicitud.estado}>{ESTADOS.find(e => e.value === solicitud.estado)?.label}</Badge>
          </SelectTrigger>
          <SelectContent>
            {ESTADOS.map(e => <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </td>
      <td className="px-4 py-2.5 text-sm text-muted-foreground">
        <input
          type="date"
          value={solicitud.fecha_programada || ''}
          onChange={e => onUpdate({ fecha_programada: e.target.value || null })}
          className="bg-transparent outline-none cursor-pointer hover:bg-accent/50 rounded px-1 -mx-1"
        />
      </td>
      <td className="px-4 py-2.5 text-sm text-muted-foreground">{solicitud.solicitado_por}</td>
      <td className="px-4 py-2.5 text-sm text-muted-foreground">
        {solicitud.op_effi ? (
          <span className="font-mono">#{solicitud.op_effi}</span>
        ) : (
          <span className="opacity-40">—</span>
        )}
      </td>
      <td className="px-4 py-2.5">
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive cursor-pointer transition-opacity"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </td>
    </tr>
  )
}
