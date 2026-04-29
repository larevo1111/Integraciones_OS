import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const ESTADOS = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'aplicado',  label: 'Aplicado' },
  { value: 'fallido',   label: 'Fallido' },
  { value: 'revertido', label: 'Revertido' },
]

const TIPOS = [
  { value: 'ingreso', label: 'Ingreso' },
  { value: 'egreso',  label: 'Egreso' },
]

const ESTADO_VARIANT = {
  pendiente: 'solicitado', aplicado: 'programado',
  fallido: 'destructive',  revertido: 'outline',
}

const fmt = (n) => Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })
const money = (n) => `$${Math.round(Number(n) || 0).toLocaleString('es-CO')}`

export function HistoricoAjustesPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/inventario/historico-ajustes?limit=500')
      setRows(Array.isArray(data) ? data : [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const columns = [
    { key: 'id',                label: 'ID',           visible: true,  nowrap: true, numeric: true },
    { key: 'fecha_ajuste',      label: 'Aplicado',     visible: true,  nowrap: true },
    { key: 'fecha_planificado', label: 'Planificado',  visible: false, nowrap: true },
    { key: 'id_effi',           label: 'Cód',          visible: true,  nowrap: true },
    { key: 'nombre',            label: 'Producto',     visible: true },
    { key: 'bodega',            label: 'Bodega',       visible: true },
    { key: 'tipo',              label: 'Tipo',         visible: true,  options: TIPOS, nowrap: true },
    { key: 'estado',            label: 'Estado',       visible: true,  options: ESTADOS, nowrap: true },
    { key: 'cantidad',          label: 'Cantidad',     visible: true,  numeric: true, nowrap: true },
    { key: 'costo_unitario',    label: 'Costo unit',   visible: false, numeric: true, nowrap: true },
    { key: 'costo_total',       label: 'Costo total',  visible: true,  numeric: true, nowrap: true },
    { key: 'stock_antes',       label: 'Stock antes',  visible: false, numeric: true, nowrap: true },
    { key: 'stock_despues',     label: 'Stock después', visible: false, numeric: true, nowrap: true },
    { key: 'op_ajuste_effi',    label: 'OP Effi',      visible: true,  nowrap: true },
    { key: 'analisis_id',       label: 'Análisis',     visible: true,  nowrap: true, numeric: true },
    { key: 'motivo',            label: 'Motivo',       visible: false },
    { key: 'error_msg',         label: 'Error',        visible: false },
    { key: 'ejecutado_por',     label: 'Ejecutado por', visible: false, nowrap: true },
    { key: 'created_at',        label: 'Created',      visible: false, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (col.key === 'estado') {
      const lbl = ESTADOS.find(e => e.value === value)?.label || value
      return <Badge variant={ESTADO_VARIANT[value] || 'outline'}>{lbl}</Badge>
    }
    if (col.key === 'tipo') {
      const lbl = TIPOS.find(t => t.value === value)?.label || value
      const cls = value === 'ingreso' ? 'text-emerald-500' : 'text-red-500'
      return <span className={`text-[11px] font-medium ${cls}`}>{lbl}</span>
    }
    if (col.key === 'cantidad' || col.key === 'stock_antes' || col.key === 'stock_despues') {
      if (value == null || value === '') return <span className="text-muted-foreground/40">—</span>
      return <span className="font-mono">{fmt(value)}</span>
    }
    if (col.key === 'costo_unitario' || col.key === 'costo_total') {
      return value ? <span className="font-mono">{money(value)}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'op_ajuste_effi') {
      return value ? <span className="font-mono text-muted-foreground">#{value}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'analisis_id') {
      if (!value) return <span className="text-muted-foreground/40">—</span>
      return (
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/inconsistencias/${value}`) }}
          className="text-primary hover:underline cursor-pointer font-mono text-[11px]"
        >#{value}</button>
      )
    }
    if (col.key === 'fecha_ajuste' || col.key === 'fecha_planificado') {
      return value || <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'motivo' || col.key === 'error_msg') {
      return value ? <span className="text-[11px] truncate" title={value}>{value}</span> : <span className="text-muted-foreground/40">—</span>
    }
    return null
  }

  return (
    <div className="px-3 pt-4 pb-6 sm:px-10 sm:pt-10 sm:pb-8 max-w-[1400px] mx-auto">
      <div className="mb-4">
        <h1 className="text-[16px] sm:text-[18px] font-semibold tracking-tight">Histórico de ajustes</h1>
        <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-1 hidden sm:block">
          Todos los ajustes de inventario aplicados (o pendientes) desde el sistema, con FK al análisis que los generó
        </p>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title="Ajustes"
        renderCell={renderCell}
      />
    </div>
  )
}
