import { useCallback, useEffect, useState } from "react"
import { EyeOff, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function InventariosExcluidosPage() {
  const [rows, setRows] = useState([])
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState('')
  const [loading, setLoading] = useState(true)

  const cargarFechas = useCallback(async () => {
    const data = await api.get('/api/inventario/fechas')
    setFechas(data)
    if (data.length && !fecha) setFecha(data[0].fecha_inventario)
  }, [fecha])

  const cargarExcluidos = useCallback(async (f) => {
    if (!f) return
    setLoading(true)
    try {
      const data = await api.get(`/api/inventario/excluidos?fecha=${f}`)
      setRows(data.map(r => ({ ...r, id: r.id || r.id_effi })))
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargarFechas() }, [cargarFechas])
  useEffect(() => { cargarExcluidos(fecha) }, [fecha, cargarExcluidos])

  const columns = [
    { key: 'id_effi', label: 'Cód',       visible: true, nowrap: true },
    { key: 'nombre',  label: 'Artículo',  visible: true },
    { key: 'categoria', label: 'Categoría', visible: true, nowrap: true },
    { key: 'razon_exclusion', label: 'Razón de exclusión', visible: true },
    { key: 'acciones', label: '',         visible: true, nowrap: true },
  ]

  const reactivar = async (row) => {
    if (!confirm(`¿Reincluir "${row.nombre}" al inventario ${fecha}?`)) return
    try {
      await api.post('/api/inventario/articulos/agregar', {
        fecha, bodega: 'Principal',
        id_effi: row.id_effi,
        usuario: auth.usuario?.email || '',
      })
      await cargarExcluidos(fecha)
    } catch (e) { alert('Error: ' + e.message) }
  }

  const renderCell = (row, col) => {
    if (col.key === 'acciones') {
      return (
        <button onClick={(e) => { e.stopPropagation(); reactivar(row) }}
          className="opacity-0 group-hover:opacity-100 text-primary hover:text-primary/80 cursor-pointer transition-opacity text-[11px] flex items-center gap-1"
          title="Reincluir al inventario">
          <RotateCcw className="h-3.5 w-3.5" />
          Reincluir
        </button>
      )
    }
    if (col.key === 'razon_exclusion') {
      return <span className="text-muted-foreground">{row.razon_exclusion || '—'}</span>
    }
    return null
  }

  return (
    <div className="p-5 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <h1 className="text-[16px] font-semibold flex items-center gap-2"><EyeOff className="h-4 w-4" /> Excluidos</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Artículos excluidos del inventario por política de agrupación o tipo
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[12px] text-muted-foreground">Fecha:</label>
          <select value={fecha} onChange={e => setFecha(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-ring">
            {fechas.map(f => <option key={f.fecha_inventario} value={f.fecha_inventario}>{f.fecha_inventario}</option>)}
          </select>
        </div>
      </div>

      <OsDataTable
        rows={rows}
        columns={columns}
        loading={loading}
        title="Excluidos"
        renderCell={renderCell}
      />
    </div>
  )
}
