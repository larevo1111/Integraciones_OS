import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

export function InconsistenciasPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/api/inventario/inconsistencias?limit=500')
      setRows(Array.isArray(data) ? data : [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const filtered = rows.filter(r => {
    if (!q.trim()) return true
    const text = `${r.id_effi} ${r.nombre} ${r.bodega} ${r.problema} ${r.causa_raiz}`.toLowerCase()
    return q.trim().toLowerCase().split(/\s+/).every(w => text.includes(w))
  })

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1400px] mx-auto">
      <div className="mb-4">
        <h1 className="text-[16px] sm:text-[18px] font-semibold">Análisis de inconsistencias</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">
          Histórico de análisis de stocks negativos / descuadres con su diagnóstico y ajustes asociados
        </p>
      </div>

      <Input value={q} onChange={e => setQ(e.target.value)}
             placeholder="Buscar por cod / bodega / causa…"
             className="mb-3 max-w-md" />

      {loading ? <div className="text-muted-foreground text-[12px]">Cargando…</div> : (
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead className="bg-muted/30">
              <tr>
                <th className="px-2 py-1.5 text-left">Fecha</th>
                <th className="px-2 py-1.5 text-left">Cód</th>
                <th className="px-2 py-1.5 text-left">Nombre</th>
                <th className="px-2 py-1.5 text-left">Bodega</th>
                <th className="px-2 py-1.5 text-right">Stock antes</th>
                <th className="px-2 py-1.5 text-left">Causa</th>
                <th className="px-2 py-1.5 text-center">Ajustes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map(r => (
                <tr key={r.id} className="hover:bg-muted/20 cursor-pointer"
                    onClick={() => navigate(`/inconsistencias/${r.id}`)}>
                  <td className="px-2 py-1.5 font-mono">{r.fecha}</td>
                  <td className="px-2 py-1.5 font-mono">{r.id_effi}</td>
                  <td className="px-2 py-1.5">{r.nombre}</td>
                  <td className="px-2 py-1.5">{r.bodega}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{Number(r.stock_antes || 0).toLocaleString('es-CO')}</td>
                  <td className="px-2 py-1.5 text-[11px] max-w-[400px] truncate" title={r.causa_raiz}>
                    {(r.causa_raiz || '').replace(/^- /, '').split('\n')[0]}
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <Badge variant="outline">{r.n_ajustes}</Badge>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="py-4 text-center text-muted-foreground italic">Sin análisis registrados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-3 text-[11px] text-muted-foreground">
        {filtered.length} de {rows.length} análisis
      </div>
    </div>
  )
}
