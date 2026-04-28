/**
 * VistaResumen — Tab "Resumen" del inventario.
 * Agrega los conteos por grupo (PT, PP, MP, INS, DS, NM, DES, SIN) y muestra impacto $.
 */
import { useEffect, useMemo, useState } from "react"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const fmtNum = (n) => n == null ? '—' : (Math.round(n * 100) / 100).toLocaleString('es-CO')
const fmtMoney = (n) => n == null ? '$0' : '$' + Math.round(n).toLocaleString('es-CO')

const GRUPO_LABEL = {
  MP:  'Materia Prima',
  INS: 'Insumos',
  PP:  'Producto en Proceso',
  PT:  'Producto Terminado',
  DS:  'Desarrollo',
  DES: 'Descontinuados',
  NM:  'No Matriculados',
  SIN: 'Sin clasificar',
}

export function VistaResumen({ fecha }) {
  const [rows, setRows] = useState([])
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!fecha) return
    setCargando(true)
    api.get(`/api/inventario/resumen-por-tipo?fecha=${fecha}`)
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(e => { console.error(e); setRows([]) })
      .finally(() => setCargando(false))
  }, [fecha])

  const totales = useMemo(() => rows.reduce((acc, r) => ({
    n_articulos: acc.n_articulos + (Number(r.n_articulos) || 0),
    val_teorico: acc.val_teorico + (Number(r.val_teorico) || 0),
    val_fisico:  acc.val_fisico  + (Number(r.val_fisico)  || 0),
    impacto:     acc.impacto     + (Number(r.impacto)     || 0),
  }), { n_articulos: 0, val_teorico: 0, val_fisico: 0, impacto: 0 }), [rows])

  const columns = [
    { key: 'grupo',            label: 'Tipo',          visible: true, nowrap: true },
    { key: 'n_articulos',      label: 'N° artículos',  visible: true, numeric: true, nowrap: true },
    { key: 'total_teorico',    label: 'Cant. Teórica', visible: true, numeric: true, nowrap: true },
    { key: 'total_fisico',     label: 'Cant. Física',  visible: true, numeric: true, nowrap: true },
    { key: 'total_diferencia', label: 'Diferencia',    visible: true, numeric: true, nowrap: true },
    { key: 'val_teorico',      label: 'Val. Teórico',  visible: true, numeric: true, nowrap: true },
    { key: 'val_fisico',       label: 'Val. Físico',   visible: true, numeric: true, nowrap: true },
    { key: 'impacto',          label: 'Impacto $',     visible: true, numeric: true, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (col.key === 'grupo') {
      const cod = value || 'SIN'
      const label = GRUPO_LABEL[cod] || cod
      return (
        <span className="inline-flex items-center gap-1.5">
          <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">{cod}</span>
          <span className="text-muted-foreground">{label}</span>
        </span>
      )
    }
    if (col.key === 'n_articulos') return fmtNum(value)
    if (['val_teorico', 'val_fisico'].includes(col.key)) return fmtMoney(value)
    if (col.key === 'impacto') {
      const v = Number(value) || 0
      return <span className={v < 0 ? 'text-destructive font-semibold' : 'text-emerald-500 font-semibold'}>{fmtMoney(v)}</span>
    }
    if (col.key === 'total_diferencia') {
      const v = Number(value)
      if (isNaN(v) || v === 0) return <span className="text-muted-foreground">0</span>
      const sign = v > 0 ? '+' : ''
      return <span className={`font-semibold ${v < 0 ? 'text-destructive' : 'text-emerald-500'}`}>{sign}{fmtNum(v)}</span>
    }
    if (['total_teorico', 'total_fisico'].includes(col.key)) return fmtNum(value)
    return value
  }

  if (!fecha) return null

  return (
    <div className="px-3 py-3 sm:px-5 sm:py-4">
      {/* Totales arriba — gran total impacto destacado */}
      <div className="flex flex-wrap gap-3 mb-3 text-[12px]">
        <div className="px-3 py-1.5 rounded bg-muted/40">
          <span className="text-muted-foreground">Artículos: </span>
          <span className="font-semibold">{fmtNum(totales.n_articulos)}</span>
        </div>
        <div className="px-3 py-1.5 rounded bg-muted/40">
          <span className="text-muted-foreground">Val. Teórico: </span>
          <span className="font-semibold">{fmtMoney(totales.val_teorico)}</span>
        </div>
        <div className="px-3 py-1.5 rounded bg-muted/40">
          <span className="text-muted-foreground">Val. Físico: </span>
          <span className="font-semibold">{fmtMoney(totales.val_fisico)}</span>
        </div>
        <div className={`px-3 py-1.5 rounded border ${totales.impacto < 0 ? 'bg-destructive/10 border-destructive/30' : 'bg-emerald-500/10 border-emerald-500/30'}`}>
          <span className="text-muted-foreground">Impacto Total: </span>
          <span className={`font-bold text-[13px] ${totales.impacto < 0 ? 'text-destructive' : 'text-emerald-500'}`}>{fmtMoney(totales.impacto)}</span>
        </div>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={cargando}
        title="Resumen por tipo"
        renderCell={renderCell}
      />
    </div>
  )
}
