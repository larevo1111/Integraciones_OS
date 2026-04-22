import { useCallback, useEffect, useState } from "react"
import { MessageSquare, Plus, Trash2, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const TIPOS = [
  { value: "observacion", label: "Observación" },
  { value: "alerta",      label: "Alerta" },
  { value: "accion",      label: "Acción" },
  { value: "problema",    label: "Problema" },
]

export function InventariosObservacionesPage() {
  const [rows, setRows] = useState([])
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)

  const cargarFechas = useCallback(async () => {
    const data = await api.get('/api/inventario/fechas')
    setFechas(data)
    if (data.length && !fecha) setFecha(data[0].fecha_inventario)
  }, [fecha])

  const cargar = useCallback(async (f) => {
    if (!f) return
    setLoading(true)
    try {
      const data = await api.get(`/api/inventario/observaciones?fecha=${f}`)
      setRows(data)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargarFechas() }, [cargarFechas])
  useEffect(() => { cargar(fecha) }, [fecha, cargar])

  const eliminar = async (row) => {
    if (!confirm('¿Eliminar esta observación?')) return
    try {
      await api.del(`/api/inventario/observaciones/${row.id}`)
      await cargar(fecha)
    } catch (e) { alert('Error: ' + e.message) }
  }

  const columns = [
    { key: 'tipo',        label: 'Tipo',     visible: true, nowrap: true, options: TIPOS },
    { key: 'descripcion', label: 'Descripción', visible: true },
    { key: 'detalle',     label: 'Detalle',  visible: true },
    { key: 'registrado_por', label: 'Por',   visible: true, nowrap: true },
    { key: 'created_at',  label: 'Fecha',    visible: true, nowrap: true },
    { key: 'acciones',    label: '',         visible: true, nowrap: true },
  ]

  const renderCell = (row, col) => {
    if (col.key === 'tipo') {
      const label = TIPOS.find(t => t.value === row.tipo)?.label || row.tipo
      return <Badge variant={row.tipo === 'alerta' || row.tipo === 'problema' ? 'en_produccion' : 'solicitado'}>{label}</Badge>
    }
    if (col.key === 'created_at' && row.created_at) {
      return <span className="text-muted-foreground text-[11px]">{row.created_at.slice(0, 16)}</span>
    }
    if (col.key === 'acciones') {
      return (
        <button onClick={(e) => { e.stopPropagation(); eliminar(row) }}
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive cursor-pointer transition-opacity">
          <Trash2 className="h-4 w-4" />
        </button>
      )
    }
    return null
  }

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2"><MessageSquare className="h-4 w-4" /> Observaciones</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">Notas, alertas y acciones registradas durante el inventario</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={fecha} onChange={e => setFecha(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {fechas.map(f => <option key={f.fecha_inventario} value={f.fecha_inventario}>{f.fecha_inventario}</option>)}
          </select>
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="h-3.5 w-3.5" strokeWidth={2.25} /> Nueva
          </Button>
        </div>
      </div>

      <OsDataTable rows={rows} columns={columns} loading={loading} title="Observaciones" renderCell={renderCell} />

      <NuevaObservacionModal open={modalOpen} onOpenChange={setModalOpen} fecha={fecha} onCreated={() => cargar(fecha)} />
    </div>
  )
}


function NuevaObservacionModal({ open, onOpenChange, fecha, onCreated }) {
  const [tipo, setTipo] = useState('observacion')
  const [descripcion, setDescripcion] = useState('')
  const [detalle, setDetalle] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open) { setTipo('observacion'); setDescripcion(''); setDetalle(''); setError(null) }
  }, [open])

  const guardar = async () => {
    setGuardando(true); setError(null)
    try {
      await api.post('/api/inventario/observaciones', {
        fecha_inventario: fecha, tipo, descripcion, detalle: detalle || null,
        usuario: auth.usuario?.email || '',
      })
      onCreated?.()
      onOpenChange(false)
    } catch (e) { setError(e.message) }
    finally { setGuardando(false) }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => onOpenChange(false)}>
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h2 className="text-[14px] font-semibold">Nueva observación · {fecha}</h2>
          <button onClick={() => onOpenChange(false)} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-[12px] font-medium text-muted-foreground">Tipo</label>
            <div className="mt-1 flex gap-2 flex-wrap">
              {TIPOS.map(t => (
                <button key={t.value} onClick={() => setTipo(t.value)}
                  className={`h-8 px-3 rounded-md text-[12px] border transition-colors ${tipo === t.value ? 'bg-primary text-primary-foreground border-primary' : 'bg-transparent border-input hover:bg-accent'}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-[12px] font-medium text-muted-foreground">Descripción *</label>
            <input value={descripcion} onChange={e => setDescripcion(e.target.value)} placeholder="Ej: Bodega sin iluminación"
              className="mt-1 w-full h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>

          <div>
            <label className="text-[12px] font-medium text-muted-foreground">Detalle (opcional)</label>
            <textarea value={detalle} onChange={e => setDetalle(e.target.value)} rows={4} placeholder="Información adicional, acciones a tomar..."
              className="mt-1 w-full px-3 py-2 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-y" />
          </div>

          {error && <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">{error}</div>}
        </div>

        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={guardando}>Cancelar</Button>
          <Button onClick={guardar} disabled={!descripcion.trim() || guardando}>
            {guardando ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Guardando…</> : 'Guardar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
