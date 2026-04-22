import { useCallback, useEffect, useState } from "react"
import { Plus, Lock, Unlock, RotateCcw, Trash2, Loader2, X, CheckSquare, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const TIPO = [
  { value: "completo", label: "Completo" },
  { value: "parcial",  label: "Parcial"  },
]

export function InventariosListaPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/inventario/fechas')
      setRows(data.map((f, i) => ({ id: i + 1, ...f })))
    } catch (e) {
      console.error(e)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const columns = [
    { key: 'fecha_inventario', label: 'Fecha',          visible: true, nowrap: true },
    { key: 'total',            label: 'Total',          visible: true, numeric: true, nowrap: true },
    { key: 'inventariables',   label: 'Inventariables', visible: true, numeric: true, nowrap: true },
    { key: 'contados',         label: 'Contados',       visible: true, numeric: true, nowrap: true },
    { key: 'con_diferencia',   label: 'Con diferencia', visible: true, numeric: true, nowrap: true },
    { key: 'progreso',         label: 'Progreso',       visible: true, nowrap: true },
    { key: 'acciones',         label: '',               visible: true, nowrap: true },
  ]

  const renderCell = (row, col) => {
    if (col.key === 'progreso') {
      const total = row.inventariables || 0
      const done  = row.contados || 0
      const pct = total ? Math.round((done / total) * 100) : 0
      return (
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-24 rounded-full bg-muted overflow-hidden">
            <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-[11px] text-muted-foreground tabular-nums">{pct}%</span>
        </div>
      )
    }
    if (col.key === 'con_diferencia') {
      return row.con_diferencia > 0
        ? <Badge variant="programado">{row.con_diferencia}</Badge>
        : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'acciones') {
      return (
        <button
          onClick={(e) => { e.stopPropagation(); eliminar(row) }}
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive cursor-pointer transition-opacity"
          title="Eliminar inventario"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )
    }
    return null
  }

  const eliminar = async (row) => {
    if (!confirm(`¿Eliminar inventario ${row.fecha_inventario}?\n\nEsto borra TODOS los conteos de esa fecha.`)) return
    try {
      await api.post('/api/inventario/eliminar', { fecha: row.fecha_inventario, usuario: auth.usuario?.email })
      await cargar()
    } catch (e) { alert('Error: ' + e.message) }
  }

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[16px] font-semibold">Inventarios</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Lista de inventarios por fecha. Click en una fila para ir al conteo.
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <Plus className="h-3.5 w-3.5" strokeWidth={2.25} />
          Nuevo inventario
        </Button>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title="Inventarios"
        onRowClick={(row) => { window.location.href = `/inventarios/conteo?fecha=${row.fecha_inventario}` }}
        renderCell={renderCell}
      />

      <NuevoInventarioModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        onCreated={cargar}
      />
    </div>
  )
}


function NuevoInventarioModal({ open, onOpenChange, onCreated }) {
  const hoy = new Date().toISOString().slice(0,10)
  const [fecha, setFecha] = useState(hoy)
  const [tipo, setTipo] = useState('completo')
  const [cantidad, setCantidad] = useState(20)
  const [sugeridos, setSugeridos] = useState([])
  const [sugiriendo, setSugiriendo] = useState(false)
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open) {
      setTipo('completo'); setSugeridos([]); setError(null); setFecha(hoy)
    }
  }, [open])

  const sugerir = async () => {
    setSugiriendo(true); setError(null)
    try {
      const data = await api.get(`/api/inventario/sugerir-articulos?cantidad=${cantidad}`)
      setSugeridos(data.map(a => ({ ...a, seleccionado: true })))
    } catch (e) { setError(e.message) }
    finally { setSugiriendo(false) }
  }

  const crear = async () => {
    setCreando(true); setError(null)
    try {
      const body = {
        fecha_inventario: fecha,
        usuario: auth.usuario?.email || 'desconocido',
        tipo,
      }
      if (tipo === 'parcial') {
        body.articulos = sugeridos.filter(s => s.seleccionado).map(s => s.id_effi)
      }
      await api.post('/api/inventario/nuevo', body)
      onCreated?.()
      onOpenChange(false)
    } catch (e) {
      setError(e.message)
    } finally { setCreando(false) }
  }

  if (!open) return null
  const nSel = sugeridos.filter(s => s.seleccionado).length
  const puedeGuardar = fecha && !creando && (tipo === 'completo' || nSel > 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => onOpenChange(false)}>
      <div
        className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg max-h-[85vh] overflow-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h2 className="text-[14px] font-semibold">Nuevo inventario</h2>
          <button onClick={() => onOpenChange(false)} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-[12px] font-medium text-muted-foreground">Fecha de corte</label>
            <input type="date" value={fecha} onChange={e => setFecha(e.target.value)}
              className="mt-1 w-full h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>

          <div>
            <label className="text-[12px] font-medium text-muted-foreground">Tipo de inventario</label>
            <div className="mt-1 flex gap-2">
              {TIPO.map(t => (
                <button key={t.value} onClick={() => { setTipo(t.value); setSugeridos([]) }}
                  className={`flex-1 h-9 rounded-md text-[13px] border transition-colors ${tipo === t.value ? 'bg-primary text-primary-foreground border-primary' : 'bg-transparent border-input hover:bg-accent'}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {tipo === 'completo' && (
            <p className="text-[12px] text-muted-foreground">Se generarán todos los artículos inventariables con el stock a esta fecha.</p>
          )}

          {tipo === 'parcial' && (
            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <div>
                  <label className="text-[12px] font-medium text-muted-foreground">Cantidad de artículos</label>
                  <input type="number" min="5" max="50" value={cantidad} onChange={e => setCantidad(+e.target.value)}
                    className="mt-1 w-20 h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
                </div>
                <Button onClick={sugerir} disabled={sugiriendo} variant="outline">
                  {sugiriendo ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckSquare className="h-3.5 w-3.5" />}
                  {sugiriendo ? 'Cargando…' : 'Sugerir artículos'}
                </Button>
              </div>

              {sugeridos.length > 0 && (
                <div className="rounded-md border border-border">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-border text-[12px]">
                    <span>{nSel} seleccionados de {sugeridos.length}</span>
                    <div className="flex gap-3">
                      <button className="text-primary hover:underline" onClick={() => setSugeridos(s => s.map(x => ({ ...x, seleccionado: true })))}>Todos</button>
                      <button className="text-muted-foreground hover:text-foreground hover:underline" onClick={() => setSugeridos(s => s.map(x => ({ ...x, seleccionado: false })))}>Ninguno</button>
                    </div>
                  </div>
                  <div className="max-h-64 overflow-auto">
                    {sugeridos.map((s, i) => (
                      <label key={i} className={`flex items-center gap-2 px-3 py-1.5 text-[12px] cursor-pointer ${s.seleccionado ? 'bg-primary/5' : ''} hover:bg-accent/60`}>
                        <input type="checkbox" checked={s.seleccionado} onChange={e =>
                          setSugeridos(prev => prev.map((x, idx) => idx === i ? { ...x, seleccionado: e.target.checked } : x))
                        } className="accent-primary" />
                        <span className="font-mono text-muted-foreground w-12 shrink-0">{s.id_effi}</span>
                        <span className="flex-1 truncate">{s.nombre}</span>
                        {s.grupo && <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted shrink-0">{s.grupo}</span>}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {error && <div className="p-3 rounded bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">{error}</div>}
        </div>

        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={creando}>Cancelar</Button>
          <Button onClick={crear} disabled={!puedeGuardar}>
            {creando ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Creando…</> : tipo === 'completo' ? 'Crear inventario completo' : `Crear inventario parcial (${nSel} art.)`}
          </Button>
        </div>
      </div>
    </div>
  )
}
