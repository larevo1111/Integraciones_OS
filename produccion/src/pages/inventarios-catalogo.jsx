import { useCallback, useEffect, useState } from "react"
import { BookOpen, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"

const GRUPOS = [
  { value: "PT",  label: "Producto Terminado" },
  { value: "PP",  label: "Producto en Proceso" },
  { value: "MP",  label: "Materia Prima" },
  { value: "INS", label: "Insumos" },
  { value: "DS",  label: "Desarrollo" },
  { value: "NM",  label: "No Matriculado" },
  { value: "DES", label: "Desperdicio" },
]

export function InventariosCatalogoPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [busq, setBusq] = useState('')

  const cargar = useCallback(async () => {
    if (!busq || busq.length < 2) { setRows([]); setLoading(false); return }
    setLoading(true)
    try {
      const data = await api.get(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busq)}`)
      setRows(data.map((r, i) => ({ ...r, rowId: i })))
    } finally { setLoading(false) }
  }, [busq])

  useEffect(() => {
    const t = setTimeout(cargar, 250)
    return () => clearTimeout(t)
  }, [cargar])

  const columns = [
    { key: 'id',         label: 'Cód',       visible: true, nowrap: true },
    { key: 'cod_barras', label: 'Cód barras', visible: true, nowrap: true },
    { key: 'nombre',     label: 'Nombre',    visible: true },
    { key: 'categoria',  label: 'Categoría', visible: true, nowrap: true },
    { key: 'grupo',      label: 'Grupo',     visible: true, nowrap: true, options: GRUPOS },
    { key: 'unidad',     label: 'Unidad',    visible: true, nowrap: true },
  ]

  const renderCell = (row, col) => {
    if (col.key === 'grupo') {
      const label = GRUPOS.find(g => g.value === row.grupo)?.label || row.grupo
      return row.grupo
        ? <Badge variant={row.grupo === 'PT' ? 'solicitado' : row.grupo === 'NM' ? 'cancelado' : 'programado'}>{row.grupo}</Badge>
        : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'unidad') {
      return row.unidad ? <span className="text-muted-foreground font-mono text-[11px]">{row.unidad}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'cod_barras') {
      return row.cod_barras ? <span className="font-mono text-[11px] text-muted-foreground">{row.cod_barras}</span> : <span className="text-muted-foreground/40">—</span>
    }
    return null
  }

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2"><BookOpen className="h-4 w-4" /> Catálogo de artículos</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">Artículos sincronizados desde Effi con grupo y unidad precalculados</p>
        </div>
      </div>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          value={busq}
          onChange={e => setBusq(e.target.value)}
          placeholder="Buscar por nombre, código o código de barras (mínimo 2 caracteres)…"
          className="w-full h-10 pl-9 pr-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      {busq.length < 2 ? (
        <div className="rounded-lg border border-border bg-card py-16 text-center text-[13px] text-muted-foreground">
          Empezá a escribir para buscar en el catálogo de Effi (~500 artículos matriculados)
        </div>
      ) : (
        <OsDataTable rows={rows} columns={columns} loading={loading} title={`Resultados (${rows.length})`} renderCell={renderCell} rowIdKey="rowId" />
      )}
    </div>
  )
}
