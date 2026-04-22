import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, Check, RotateCcw, Loader2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const FILTROS_INC = [
  { value: "", label: "Todas" },
  { value: "incluidas", label: "Incluidas" },
  { value: "excluidas", label: "Excluidas" },
]
const FILTROS_SOSP = [
  { value: "", label: "Todas" },
  { value: "sospechosas", label: "Sospechosas" },
  { value: "normales", label: "Normales" },
]
const FILTROS_REV = [
  { value: "", label: "Todas" },
  { value: "pendientes", label: "Pendientes" },
  { value: "revisadas", label: "Revisadas" },
]

export function InventariosOpsRevisarPage() {
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState('')
  const [ops, setOps] = useState([])
  const [resumen, setResumen] = useState({})
  const [loading, setLoading] = useState(true)
  const [fInc, setFInc] = useState('')
  const [fSosp, setFSosp] = useState('')
  const [fRev, setFRev] = useState('')
  const [notaOp, setNotaOp] = useState(null)

  const cargarFechas = useCallback(async () => {
    const data = await api.get('/api/inventario/fechas')
    setFechas(data)
    if (data.length && !fecha) setFecha(data[0].fecha_inventario)
  }, [fecha])

  const cargar = useCallback(async (f) => {
    if (!f) return
    setLoading(true)
    try {
      const q = new URLSearchParams({ fecha: f })
      if (fInc) q.set('filtro_inclusion', fInc)
      if (fSosp) q.set('filtro_sospecha', fSosp)
      if (fRev) q.set('filtro_revision', fRev)
      const data = await api.get(`/api/inventario/ops-revisar?${q}`)
      setOps(data.ops || [])
      setResumen(data.resumen || {})
    } finally { setLoading(false) }
  }, [fInc, fSosp, fRev])

  useEffect(() => { cargarFechas() }, [cargarFechas])
  useEffect(() => { cargar(fecha) }, [fecha, cargar])

  const columns = [
    { key: 'id_op',            label: 'OP',       visible: true, nowrap: true },
    { key: 'fecha_creacion_op',label: 'Fecha OP', visible: true, nowrap: true },
    { key: 'descripcion',      label: 'Descripción', visible: true },
    { key: 'incluida_en_calculo', label: 'Incluida', visible: true, nowrap: true },
    { key: 'sospechosa',       label: 'Sospechosa', visible: true, nowrap: true },
    { key: 'revisada',         label: 'Revisada', visible: true, nowrap: true },
    { key: 'acciones',         label: '',         visible: true, nowrap: true },
  ]

  const toggleRevisada = async (row) => {
    try {
      if (row.revisada) {
        await api.patch(`/api/inventario/ops-revisar/${row.id}`, { revisada: false, usuario: auth.usuario?.email || '' })
      } else {
        setNotaOp(row)
      }
      await cargar(fecha)
    } catch (e) { alert('Error: ' + e.message) }
  }

  const renderCell = (row, col) => {
    if (col.key === 'incluida_en_calculo') return row.incluida_en_calculo ? <Badge variant="solicitado">Sí</Badge> : <Badge variant="cancelado">No</Badge>
    if (col.key === 'sospechosa')          return row.sospechosa ? <Badge variant="en_produccion">⚠</Badge> : <span className="text-muted-foreground/40">—</span>
    if (col.key === 'revisada')            return row.revisada ? <Badge variant="validado">✓</Badge> : <span className="text-muted-foreground/40">—</span>
    if (col.key === 'fecha_creacion_op' && row.fecha_creacion_op) {
      return <span className="text-[11px] text-muted-foreground">{String(row.fecha_creacion_op).slice(0,16)}</span>
    }
    if (col.key === 'acciones') {
      return (
        <button onClick={(e) => { e.stopPropagation(); toggleRevisada(row) }}
          className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity text-[11px] flex items-center gap-1 text-primary hover:text-primary/80">
          {row.revisada ? <><RotateCcw className="h-3.5 w-3.5" /> Desmarcar</> : <><Check className="h-3.5 w-3.5" /> Revisar</>}
        </button>
      )
    }
    return null
  }

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> OPs a revisar</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">OPs que afectan el inventario teórico y requieren auditoría</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={fecha} onChange={e => setFecha(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {fechas.map(f => <option key={f.fecha_inventario} value={f.fecha_inventario}>{f.fecha_inventario}</option>)}
          </select>
          <select value={fInc} onChange={e => setFInc(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {FILTROS_INC.map(f => <option key={f.value} value={f.value}>Inclusión: {f.label}</option>)}
          </select>
          <select value={fSosp} onChange={e => setFSosp(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {FILTROS_SOSP.map(f => <option key={f.value} value={f.value}>Sospecha: {f.label}</option>)}
          </select>
          <select value={fRev} onChange={e => setFRev(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {FILTROS_REV.map(f => <option key={f.value} value={f.value}>Revisión: {f.label}</option>)}
          </select>
        </div>
      </div>

      {/* Resumen */}
      {resumen.total !== undefined && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Kpi label="Total" value={resumen.total} />
          <Kpi label="Sospechosas" value={resumen.sospechosas} warn />
          <Kpi label="Revisadas" value={resumen.revisadas} ok />
          <Kpi label="Pendientes" value={(resumen.total || 0) - (resumen.revisadas || 0)} />
        </div>
      )}

      <OsDataTable rows={ops} columns={columns} loading={loading} title="OPs" renderCell={renderCell} />

      <NotaRevisionModal op={notaOp} onClose={() => setNotaOp(null)} onSaved={() => cargar(fecha)} />
    </div>
  )
}

function Kpi({ label, value, warn, ok }) {
  return (
    <div className="px-3 py-2 rounded-md border border-border bg-card">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className={`text-[18px] font-semibold tabular-nums ${warn ? 'text-amber-500' : ok ? 'text-emerald-500' : ''}`}>{value ?? 0}</div>
    </div>
  )
}

function NotaRevisionModal({ op, onClose, onSaved }) {
  const [nota, setNota] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => { if (op) setNota('') }, [op])

  if (!op) return null

  const guardar = async () => {
    setGuardando(true)
    try {
      await api.patch(`/api/inventario/ops-revisar/${op.id}`, {
        revisada: true, nota, usuario: auth.usuario?.email || '',
      })
      onSaved?.()
      onClose()
    } catch (e) { alert('Error: ' + e.message) }
    finally { setGuardando(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h2 className="text-[14px] font-semibold">Marcar OP {op.id_op} como revisada</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5">
          <label className="text-[12px] font-medium text-muted-foreground">Nota de revisión (opcional)</label>
          <textarea value={nota} onChange={e => setNota(e.target.value)} rows={3} placeholder="Ej: Verificado con planilla"
            className="mt-1 w-full px-3 py-2 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-y" />
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <Button variant="ghost" onClick={onClose} disabled={guardando}>Cancelar</Button>
          <Button onClick={guardar} disabled={guardando}>
            {guardando ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Guardando…</> : 'Confirmar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
