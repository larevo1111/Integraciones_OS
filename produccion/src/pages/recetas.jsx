/**
 * RecetasPage — lista del libro de recetas con pestañas Activas/Antiguas y búsqueda rápida.
 */
import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router"
import { BookOpen, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

const FAMILIAS = [
  { value: "coberturas",  label: "Coberturas" },
  { value: "tabletas",    label: "Tabletas" },
  { value: "propoleo",    label: "Propóleo" },
  { value: "polen",       label: "Polen" },
  { value: "mieles",      label: "Mieles" },
  { value: "cremas_mani", label: "Cremas Maní" },
  { value: "chocolates",  label: "Chocolates" },
  { value: "cacao_nibs",  label: "Cacao/Nibs" },
  { value: "infusiones",  label: "Infusiones" },
  { value: "otros",       label: "Otros" },
]

const ESTADOS = [
  { value: "borrador",  label: "Borrador" },
  { value: "validada",  label: "Validada" },
]

const CONFIANZAS = [
  { value: "alta",  label: "Alta" },
  { value: "media", label: "Media" },
  { value: "baja",  label: "Baja" },
]

const TABS = [
  { value: "activas",  label: "Activas 2026" },
  { value: "antiguas", label: "Antiguas" },
]

export function RecetasPage() {
  const [rows, setRows] = useState([])
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState("activas")
  const [search, setSearch] = useState("")
  const navigate = useNavigate()

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ tab })
      if (search.trim()) params.set('q_str', search.trim())
      const [recetas, resumen] = await Promise.all([
        api.get(`/api/recetas?${params}`),
        api.get('/api/recetas/stats/resumen'),
      ])
      setRows(recetas.map(r => ({ ...r })))
      setStats(resumen)
    } finally { setLoading(false) }
  }, [tab, search])

  useEffect(() => { cargar() }, [cargar])

  // Debounce de búsqueda: recargar 400ms después de dejar de escribir
  const [searchInput, setSearchInput] = useState("")
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  const columns = [
    { key: 'cod_articulo', label: 'Cód',       visible: true, nowrap: true },
    { key: 'nombre',       label: 'Producto',  visible: true },
    { key: 'familia',      label: 'Familia',   visible: true, options: FAMILIAS, nowrap: true },
    { key: 'patron',       label: 'Patrón',    visible: true, nowrap: true },
    { key: 'cantidad_lote_std', label: 'Lote', visible: true, numeric: true, nowrap: true },
    { key: 'n_materiales', label: 'Mat',       visible: true, numeric: true, nowrap: true },
    { key: 'n_ops_analizadas', label: 'OPs',   visible: true, numeric: true, nowrap: true },
    { key: 'confianza',    label: 'Conf',      visible: true, options: CONFIANZAS, nowrap: true },
    { key: 'estado',       label: 'Estado',    visible: true, options: ESTADOS, nowrap: true },
  ]

  const renderCell = (row, col) => {
    if (col.key === 'familia') {
      return <Badge variant="programado" className="text-[10px] px-1.5 py-0 h-4">{row.familia || '—'}</Badge>
    }
    if (col.key === 'patron') {
      const cls = row.patron === 'lote_fijo' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
      return <span className={`text-[10px] px-1.5 py-0 rounded ${cls}`}>{row.patron}</span>
    }
    if (col.key === 'cantidad_lote_std') {
      const v = row.cantidad_lote_std
      return v ? <span className="font-mono tabular-nums">{Number(v).toLocaleString('es-CO')}</span> : <span className="text-muted-foreground/40">—</span>
    }
    if (col.key === 'confianza') {
      const colors = { alta: 'text-emerald-600 dark:text-emerald-400', media: 'text-amber-500', baja: 'text-muted-foreground' }
      return <span className={colors[row.confianza] || ''}>{row.confianza}</span>
    }
    if (col.key === 'estado') {
      const variant = row.estado === 'validada' ? 'programado' : 'solicitado'
      return <Badge variant={variant}>{row.estado}</Badge>
    }
    return null
  }

  const onRowClick = (row) => navigate(`/recetas/${row.cod_articulo}`)

  const totalValidadas = stats.reduce((s, f) => s + (f.validadas || 0), 0)
  const totalRecetas = stats.reduce((s, f) => s + (f.total || 0), 0)

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2">
            <BookOpen className="h-4 w-4" /> Recetas
          </h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Libro maestro de recetas — {totalRecetas} productos, {totalValidadas} validadas
          </p>
        </div>
      </div>

      {/* Búsqueda + Pestañas */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar por nombre o código..."
            className="pl-8 h-8 text-[12px]"
          />
        </div>
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={cn(
                "h-8 px-3 rounded-md text-[12px] font-medium transition-colors cursor-pointer",
                tab === t.value
                  ? "bg-primary/10 text-primary border border-primary/30"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent border border-transparent"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Resumen por familia */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 mb-4 text-[11px]">
        {stats.map(s => (
          <div key={s.familia} className="border border-border rounded px-2 py-1.5">
            <div className="font-medium capitalize">{s.familia}</div>
            <div className="text-muted-foreground font-mono">
              {s.validadas}/{s.total}
            </div>
          </div>
        ))}
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title={tab === 'activas' ? 'Activas 2026' : 'Antiguas'}
        renderCell={renderCell}
        onRowClick={onRowClick}
        rowKey={(r) => r.cod_articulo}
      />
    </div>
  )
}
