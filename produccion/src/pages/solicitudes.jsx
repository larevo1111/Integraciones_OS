import { useEffect, useState, useCallback } from "react"
import { Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { NuevaSolicitudSheet } from "@/components/nueva-solicitud-sheet"
import { api } from "@/lib/api"

const ESTADOS = [
  { value: "solicitado", label: "Solicitado" },
  { value: "programado", label: "Programado" },
  { value: "en_produccion", label: "En producción" },
  { value: "producido", label: "Producido" },
  { value: "validado", label: "Validado" },
  { value: "cancelado", label: "Cancelado" },
]

const ESTADO_LABEL = Object.fromEntries(ESTADOS.map(e => [e.value, e.label]))

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
  const [drawerOpen, setDrawerOpen] = useState(false)
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

  const actualizar = async (id, cambios) => {
    try {
      await api.patch(`/api/solicitudes/${id}`, cambios)
      await cargar()
    } catch (e) { alert('Error: ' + e.message) }
  }

  const eliminar = async (id) => {
    if (!confirm('¿Eliminar esta solicitud?')) return
    await api.del(`/api/solicitudes/${id}`)
    await cargar()
  }

  const columns = [
    { key: 'id', label: 'ID', visible: true, nowrap: true, numeric: true },
    { key: 'cod_articulo', label: 'Cód', visible: true, nowrap: true },
    { key: 'nombre_articulo', label: 'Producto', visible: true },
    { key: 'tipo_articulo', label: 'Tipo', visible: true, options: TIPOS },
    { key: 'cantidad', label: 'Cantidad', visible: true, numeric: true, nowrap: true },
    { key: 'estado', label: 'Estado', visible: true, options: ESTADOS },
    { key: 'fecha_programada', label: 'Programada', visible: true, nowrap: true },
    { key: 'solicitado_por', label: 'Solicitante', visible: true, nowrap: true },
    { key: 'op_effi', label: 'OP Effi', visible: true, nowrap: true },
    { key: 'observaciones', label: 'Observaciones', visible: false },
    { key: 'fecha_solicitud', label: 'Fecha solicitud', visible: false, nowrap: true },
    { key: 'acciones', label: '', visible: true, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (col.key === 'estado') {
      return (
        <select
          value={value}
          onClick={e => e.stopPropagation()}
          onChange={e => actualizar(row.id, { estado: e.target.value })}
          className="bg-transparent outline-none cursor-pointer"
        >
          {ESTADOS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
        </select>
      )
    }
    if (col.key === 'tipo_articulo') {
      return value ? <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{value}</span> : '—'
    }
    if (col.key === 'cantidad') {
      const editable = row.estado === 'solicitado'
      return <EditableNumber value={value} editable={editable} onSave={v => actualizar(row.id, { cantidad: v })} />
    }
    if (col.key === 'fecha_programada') {
      return (
        <input
          type="date"
          value={value || ''}
          onClick={e => e.stopPropagation()}
          onChange={e => actualizar(row.id, { fecha_programada: e.target.value || null })}
          className="bg-transparent outline-none cursor-pointer hover:bg-accent/50 rounded px-1 -mx-1 text-sm text-muted-foreground"
        />
      )
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
    return null // default
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
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

      <OsDataTable
        rows={solicitudes}
        columns={columns}
        loading={loading}
        title="Solicitudes"
        renderCell={renderCell}
      />

      <NuevaSolicitudSheet
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        articulos={articulos}
        onCreated={cargar}
      />
    </div>
  )
}

function EditableNumber({ value, editable, onSave }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value)
  useEffect(() => { setVal(value) }, [value])

  const save = () => {
    // Aceptar punto o coma como separador decimal
    const normalizado = String(val).replace(',', '.')
    const n = parseFloat(normalizado)
    if (isNaN(n) || n <= 0) { setVal(value); setEditing(false); return }
    if (n !== value) onSave(n)
    setEditing(false)
  }

  if (editable && editing) {
    return (
      <input
        type="text"
        inputMode="decimal"
        autoFocus
        value={val}
        onClick={e => e.stopPropagation()}
        onChange={e => {
          // Permitir solo dígitos, punto y coma
          const v = e.target.value.replace(/[^0-9.,]/g, '')
          setVal(v)
        }}
        onBlur={save}
        onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { setVal(value); setEditing(false) } }}
        className="w-20 bg-transparent border border-primary rounded px-2 py-0.5 text-right outline-none font-mono text-sm"
      />
    )
  }
  return (
    <span
      onClick={e => { if (editable) { e.stopPropagation(); setEditing(true) } }}
      className={editable ? "cursor-pointer hover:bg-accent/50 px-2 py-0.5 -mx-2 rounded font-mono" : "font-mono"}
    >{value}</span>
  )
}
