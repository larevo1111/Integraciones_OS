import { useEffect, useState, useCallback, useMemo } from "react"
import { Plus, Trash2, Layers, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { DetalleSolicitudSheet } from "@/components/detalle-solicitud-sheet"
import { ProgramarGrupoDialog } from "@/components/programar-grupo-dialog"
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
  const [selectedIds, setSelectedIds] = useState([])
  const [grupoDialogOpen, setGrupoDialogOpen] = useState(false)

  const seleccionadas = useMemo(
    () => solicitudes.filter(s => selectedIds.includes(s.id)),
    [solicitudes, selectedIds]
  )

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
      label: `${a.cod} — ${a.nombre}`,
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
    { key: 'fecha_necesidad', label: 'Necesidad para', visible: true, nowrap: true },
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
    <div className="px-3 pt-4 pb-6 sm:px-10 sm:pt-10 sm:pb-8 max-w-[1400px] mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 sm:mb-6 gap-3">
        <div>
          <h1 className="text-[16px] sm:text-[18px] font-semibold tracking-tight">Solicitudes de Producción</h1>
          <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-1 hidden sm:block">
            Selecciona varias para programarlas en una sola OP, o click en una fila para ver el detalle
          </p>
        </div>
        <Button onClick={abrirNueva} className="shrink-0 self-start sm:self-auto" size="sm">
          <Plus className="h-3.5 w-3.5" strokeWidth={2.25} />
          Nueva solicitud
        </Button>
      </div>

      {/* Barra de selección múltiple */}
      {selectedIds.length > 0 && (
        <div className="flex items-center justify-between gap-3 mb-3 px-3 py-2 rounded-lg bg-primary/10 border border-primary/30">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="font-medium">{selectedIds.length} solicitud{selectedIds.length === 1 ? '' : 'es'} seleccionada{selectedIds.length === 1 ? '' : 's'}</span>
            <button onClick={() => setSelectedIds([])} className="text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <Button onClick={() => setGrupoDialogOpen(true)} disabled={selectedIds.length < 2}>
            <Layers className="h-3.5 w-3.5" />
            Programar juntas
          </Button>
        </div>
      )}

      <OsDataTable
        rows={solicitudes}
        columns={columns}
        loading={loading}
        title="Solicitudes"
        onRowClick={abrirDetalle}
        renderCell={renderCell}
        selectable
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
      />

      <DetalleSolicitudSheet
        open={detalleOpen}
        onOpenChange={setDetalleOpen}
        solicitud={solicitudSel}
        articulos={articulos}
        onSaved={cargar}
      />

      <ProgramarGrupoDialog
        open={grupoDialogOpen}
        onOpenChange={setGrupoDialogOpen}
        solicitudes={seleccionadas}
        onCreated={async () => { setSelectedIds([]); await cargar() }}
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
