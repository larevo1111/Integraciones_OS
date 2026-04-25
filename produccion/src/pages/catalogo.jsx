/**
 * CatalogoPage — único agregado nuevo. Tabla con TODOS los productos del catálogo
 * con su stock actual. Usa OsDataTable estándar.
 */
import { useCallback, useEffect, useState } from "react"
import { BookOpen } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const TIPOS = [
  { value: "PT",  label: "Producto Terminado" },
  { value: "PP",  label: "Producto en Proceso" },
  { value: "MP",  label: "Materia Prima" },
  { value: "INS", label: "Insumos" },
  { value: "DS",  label: "Desarrollo" },
]

export function CatalogoPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/articulos')
      setRows(data.map((a, i) => ({ ...a, id: a.cod || i })))
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const columns = [
    { key: 'cod',    label: 'Cód',     visible: true, nowrap: true },
    { key: 'nombre', label: 'Producto', visible: true },
    { key: 'tipo',   label: 'Tipo',    visible: true, options: TIPOS, nowrap: true },
    { key: 'unidad', label: 'Unidad',  visible: true, nowrap: true },
    { key: 'stock',  label: 'Stock',   visible: true, numeric: true, nowrap: true },
  ]

  const renderCell = (row, col) => {
    if (col.key === 'tipo') {
      if (!row.tipo) return <span className="text-muted-foreground/40">—</span>
      return <Badge variant={row.tipo === 'PT' ? 'solicitado' : 'programado'}>{row.tipo}</Badge>
    }
    if (col.key === 'stock') {
      const v = parseFloat(row.stock || 0)
      const cls = v <= 0 ? 'text-muted-foreground' : v < 5 ? 'text-amber-500' : ''
      return <span className={`font-mono tabular-nums ${cls}`}>{Number(v).toLocaleString('es-CO')}</span>
    }
    if (col.key === 'unidad') {
      return row.unidad ? <span className="text-muted-foreground font-mono text-[11px]">{row.unidad}</span> : <span className="text-muted-foreground/40">—</span>
    }
    return null
  }

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2"><BookOpen className="h-4 w-4" /> Catálogo</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Productos vigentes con su stock actual en bodega principal
          </p>
        </div>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title="Catálogo"
        renderCell={renderCell}
      />
    </div>
  )
}
