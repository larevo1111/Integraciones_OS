/**
 * VistaCostos — Tab "Costos" del inventario.
 * Refactor: usa OsDataTable (mismo objeto que solicitudes) — scroll, sort, filtros, export incluidos.
 */
import { useEffect, useState, useMemo } from "react"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const fmtNum = (n) => n == null ? '—' : (Math.round(n * 100) / 100).toLocaleString('es-CO')
const fmtMoney = (n) => n == null ? '$0' : '$' + Math.round(n).toLocaleString('es-CO')

export function VistaCostos({ fecha }) {
  const [rows, setRows] = useState([])
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!fecha) return
    setCargando(true)
    api.get(`/api/inventario/costos?fecha=${fecha}`)
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(e => { console.error(e); setRows([]) })
      .finally(() => setCargando(false))
  }, [fecha])

  const totales = useMemo(() => rows.reduce((acc, r) => ({
    val_teorico: acc.val_teorico + (Number(r.valor_teorico) || 0),
    val_fisico:  acc.val_fisico  + (Number(r.valor_fisico)  || 0),
    impacto:     acc.impacto     + (Number(r.impacto)       || 0),
  }), { val_teorico: 0, val_fisico: 0, impacto: 0 }), [rows])

  const columns = [
    { key: 'id_effi',       label: 'Cód',           visible: true, nowrap: true },
    { key: 'nombre',        label: 'Artículo',      visible: true },
    { key: 'categoria',     label: 'Categoría',     visible: true, nowrap: true },
    { key: 'grupo',         label: 'Tipo',          visible: true, nowrap: true },
    { key: 'costo_manual',  label: 'Costo Unit.',   visible: true, numeric: true, nowrap: true },
    { key: 'teorico',       label: 'Cant. Teórica', visible: true, numeric: true, nowrap: true },
    { key: 'fisico',        label: 'Cant. Física',  visible: true, numeric: true, nowrap: true },
    { key: 'diferencia',    label: 'Diferencia',    visible: true, numeric: true, nowrap: true },
    { key: 'valor_teorico', label: 'Val. Teórico',  visible: true, numeric: true, nowrap: true },
    { key: 'valor_fisico',  label: 'Val. Físico',   visible: true, numeric: true, nowrap: true },
    { key: 'impacto',       label: 'Impacto $',     visible: true, numeric: true, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (['costo_manual', 'valor_teorico', 'valor_fisico'].includes(col.key)) return fmtMoney(value)
    if (col.key === 'impacto') {
      const v = Number(value) || 0
      return <span className={v < 0 ? 'text-destructive font-semibold' : 'text-emerald-500 font-semibold'}>{fmtMoney(v)}</span>
    }
    if (col.key === 'diferencia') {
      const v = Number(value)
      if (isNaN(v)) return '—'
      const sign = v > 0 ? '+' : ''
      return <span className="font-semibold">{sign}{fmtNum(v)}</span>
    }
    if (['teorico', 'fisico'].includes(col.key)) return fmtNum(value)
    if (col.key === 'grupo') return value ? <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{value}</span> : '—'
    if (col.key === 'categoria') return value || '—'
    return value
  }

  if (!fecha) return null

  return (
    <div className="px-3 py-3 sm:px-5 sm:py-4">
      {/* Totales arriba */}
      <div className="flex flex-wrap gap-3 mb-3 text-[12px]">
        <div className="px-3 py-1.5 rounded bg-muted/40">
          <span className="text-muted-foreground">Val. Teórico: </span>
          <span className="font-semibold">{fmtMoney(totales.val_teorico)}</span>
        </div>
        <div className="px-3 py-1.5 rounded bg-muted/40">
          <span className="text-muted-foreground">Val. Físico: </span>
          <span className="font-semibold">{fmtMoney(totales.val_fisico)}</span>
        </div>
        <div className={`px-3 py-1.5 rounded ${totales.impacto < 0 ? 'bg-destructive/10' : 'bg-emerald-500/10'}`}>
          <span className="text-muted-foreground">Impacto: </span>
          <span className={`font-semibold ${totales.impacto < 0 ? 'text-destructive' : 'text-emerald-500'}`}>{fmtMoney(totales.impacto)}</span>
        </div>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={cargando}
        title="Valorización"
        renderCell={renderCell}
      />
    </div>
  )
}
