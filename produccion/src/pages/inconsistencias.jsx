import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const ESTADOS = [
  { value: 'abierto',     label: 'Abierto' },
  { value: 'en_revision', label: 'En revisión' },
  { value: 'resuelto',    label: 'Resuelto' },
  { value: 'descartado',  label: 'Descartado' },
]

const TIPOS = [
  { value: 'stock_negativo',     label: 'Stock negativo' },
  { value: 'descuadre_conteo',   label: 'Descuadre conteo' },
  { value: 'articulo_eliminado', label: 'Artículo eliminado' },
  { value: 'duplicado',          label: 'Duplicado' },
  { value: 'otro',               label: 'Otro' },
]

const ESTADO_VARIANT = {
  abierto: 'solicitado', en_revision: 'solicitado',
  resuelto: 'programado', descartado: 'destructive',
}

const fmt = (n) => Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })
const money = (n) => `$${Math.round(Number(n) || 0).toLocaleString('es-CO')}`

export function InconsistenciasPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/inventario/inconsistencias?limit=500')
      setRows(Array.isArray(data) ? data : [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const columns = [
    { key: 'id',                   label: 'ID',           visible: true,  nowrap: true, numeric: true },
    { key: 'fecha_analisis',       label: 'Análisis',     visible: true,  nowrap: true },
    { key: 'fecha_inventario',     label: 'Inventario',   visible: false, nowrap: true },
    { key: 'id_effi',              label: 'Cód',          visible: true,  nowrap: true },
    { key: 'nombre',               label: 'Producto',     visible: true },
    { key: 'bodega',               label: 'Bodega',       visible: true },
    { key: 'tipo_inconsistencia',  label: 'Tipo',         visible: true,  options: TIPOS, nowrap: true },
    { key: 'estado',               label: 'Estado',       visible: true,  options: ESTADOS, nowrap: true },
    { key: 'stock_antes',          label: 'Stock antes',  visible: true,  numeric: true, nowrap: true },
    { key: 'inventario_teorico',   label: 'Teórico',      visible: false, numeric: true, nowrap: true },
    { key: 'inventario_fisico',    label: 'Físico',       visible: false, numeric: true, nowrap: true },
    { key: 'costo_unitario',       label: 'Costo unit',   visible: false, numeric: true, nowrap: true },
    { key: 'costo_total_impacto',  label: 'Impacto $',    visible: true,  numeric: true, nowrap: true },
    { key: 'n_ajustes',            label: 'Ajustes',      visible: true,  numeric: true, nowrap: true },
    { key: 'causa_raiz',           label: 'Causa',        visible: false },
    { key: 'creado_por',           label: 'Creado por',   visible: false, nowrap: true },
    { key: 'created_at',           label: 'Created',      visible: false, nowrap: true },
  ]

  const renderCell = (row, col, value) => {
    if (col.key === 'estado') {
      const lbl = ESTADOS.find(e => e.value === value)?.label || value
      return <Badge variant={ESTADO_VARIANT[value] || 'outline'}>{lbl}</Badge>
    }
    if (col.key === 'tipo_inconsistencia') {
      const lbl = TIPOS.find(t => t.value === value)?.label || value
      return <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{lbl}</span>
    }
    if (col.key === 'stock_antes' || col.key === 'inventario_teorico' || col.key === 'inventario_fisico') {
      if (value == null || value === '') return <span className="text-muted-foreground/40">—</span>
      const n = Number(value)
      return <span className={`font-mono ${n < 0 ? 'text-red-500' : ''}`}>{fmt(n)}</span>
    }
    if (col.key === 'costo_unitario' || col.key === 'costo_total_impacto') {
      return value ? <span className="font-mono">{money(value)}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'n_ajustes') {
      return <Badge variant="outline">{value || 0}</Badge>
    }
    if (col.key === 'causa_raiz') {
      const txt = (value || '').replace(/^- /, '').split('\n')[0]
      return <span className="text-[11px] truncate" title={value}>{txt}</span>
    }
    if (col.key === 'fecha_inventario' && !value) {
      return <span className="text-muted-foreground/40">—</span>
    }
    return null
  }

  return (
    <div className="px-3 pt-4 pb-6 sm:px-10 sm:pt-10 sm:pb-8 max-w-[1400px] mx-auto">
      <div className="mb-4">
        <h1 className="text-[16px] sm:text-[18px] font-semibold tracking-tight">Análisis de inconsistencias</h1>
        <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-1 hidden sm:block">
          Histórico de descuadres detectados, su diagnóstico, ajustes asociados e impacto monetario
        </p>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title="Inconsistencias"
        onRowClick={(row) => navigate(`/inconsistencias/${row.id}`)}
        renderCell={renderCell}
      />
    </div>
  )
}
