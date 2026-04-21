import { useEffect, useState, useCallback } from "react"
import { Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { DetalleSolicitudSheet } from "@/components/detalle-solicitud-sheet"
import { api } from "@/lib/api"

const ESTADOS = [
  { value: "solicitado", label: "Solicitado" },
  { value: "programado", label: "Programado" },
  { value: "en_produccion", label: "En producción" },
  { value: "producido", label: "Producido" },
  { value: "validado", label: "Validado" },
  { value: "cancelado", label: "Cancelado" },
]

const TIPOS = [
  { value: "PT", label: "Producto Terminado" },
  { value: "PP", label: "Producto en Proceso" },
  { value: "MP", label: "Materia Prima" },
  { value: "INS", label: "Insumos" },
  { value: "DS", label: "Desarrollo" },
]

export function SolicitudesPage() {
  const [solicitudes, setSolicitudes] = useState([])
  const [loading, setLoading] = useState(true)
  const [detalleOpen, setDetalleOpen] = useState(false)
  const [solicitudSel, setSolicitudSel] = useState(null)
  const [articulos, setArticulos] = useState([])

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/solicitudes?_end=500')
      setSolicitudes(data)
    } finally {
      setLoading(false)
    }
  }, [])

  const cargarArticulos = useCallback(async () => {
    const data = await api.get('/api/articulos')
    setArticulos(data.map(a => ({
      value: a.cod,
      label: a.nombre,
      subtitle: `Stock: ${a.stock}${a.unidad ? ' ' + a.unidad : ''}`,
      badge: a.tipo,
      tipo: a.tipo,
    })))
  }, [])

  useEffect(() => { cargar(); cargarArticulos() }, [cargar, cargarArticulos])

  const eliminar = async (id) => {
    if (!confirm('¿Eliminar esta solicitud?')) return
    await api.del(`/api/solicitudes/${id}`)
    await cargar()
  }

  const abrirNueva = () => { setSolicitudSel(null); setDetalleOpen(true) }
  const abrirDetalle = (row) => { setSolicitudSel(row); setDetalleOpen(true) }

  const columns = [
    { key: 'id', label: 'ID', visible: true, nowrap: true, numeric: true },
    { key: 'cod_articulo', label: 'Cód', visible: true, nowrap: true },
    { key: 'nombre_articulo', label: 'Producto', visible: true },
    { key: 'tipo_articulo', label: 'Tipo', visible: true, options: TIPOS },
    { key: 'cantidad', label: 'Cantidad', visible: true, numeric: true, nowrap: true },
    { key: 'estado', label: 'Estado', visible: true, options: ESTADOS },
    { key: 'fecha_necesidad', label: 'Necesidad', visible: true, nowrap: true },
    { key: 'fecha_programada', label: 'Programada', visible: true, nowrap: true },
    { key: 'solicitado_por', label: 'Solicitante', visible: true, nowrap: true },
    { key: 'op_effi', label: 'OP Effi', visible: true, nowrap: true },
    { key: 'observaciones', label: 'Observaciones', visible: false },
    { key: 'fecha_solicitud', label: 'Fecha solicitud', visible: false, nowrap: true },
    { key: 'acciones', label: '', visible: true, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (col.key === 'estado') {
      const label = ESTADOS.find(e => e.value === value)?.label || value
      return <Badge variant={value}>{label}</Badge>
    }
    if (col.key === 'tipo_articulo') {
      return value ? <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{value}</span> : '—'
    }
    if (col.key === 'cantidad') {
      return <span className="font-mono">{value}</span>
    }
    if (col.key === 'fecha_necesidad' || col.key === 'fecha_programada') {
      return value ? (
        <span className="text-muted-foreground">{formatFecha(value)}</span>
      ) : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'fecha_solicitud') {
      return value ? value.slice(0, 16) : '—'
    }
    if (col.key === 'op_effi') {
      return value ? <span className="font-mono text-muted-foreground">#{value}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'acciones') {
      return (
        <button
          onClick={(e) => { e.stopPropagation(); eliminar(row.id) }}
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive cursor-pointer transition-opacity"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )
    }
    return null
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Solicitudes de Producción</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Click en una fila para ver o editar el detalle
          </p>
        </div>
        <Button onClick={abrirNueva} className="cursor-pointer">
          <Plus className="h-4 w-4" />
          Nueva solicitud
        </Button>
      </div>

      <OsDataTable
        rows={solicitudes}
        columns={columns}
        loading={loading}
        title="Solicitudes"
        onRowClick={abrirDetalle}
        renderCell={renderCell}
      />

      <DetalleSolicitudSheet
        open={detalleOpen}
        onOpenChange={setDetalleOpen}
        solicitud={solicitudSel}
        articulos={articulos}
        onSaved={cargar}
      />
    </div>
  )
}

function formatFecha(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  if (!d) return iso
  return `${d}/${m}/${y}`
}
