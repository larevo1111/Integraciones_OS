import { useCallback, useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router"
import { ChevronLeft, CheckCircle2, AlertCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { RecetaForm } from "@/components/receta-form"

/**
 * Página de detalle de receta (/recetas/:cod).
 * Wrapper sobre <RecetaForm> que agrega el header de navegación + acciones de estado (Validar / Borrador).
 */
export function RecetaDetallePage() {
  const { cod } = useParams()
  const navigate = useNavigate()
  const [r, setR] = useState(null)
  const [saving, setSaving] = useState(false)

  // Cargar metadata de la receta para el header (nombre, estado, badges).
  // El RecetaForm carga sus propios datos internos.
  const cargarHeader = useCallback(async () => {
    try {
      const data = await api.get(`/api/recetas/${cod}`)
      setR(data)
    } catch { setR(null) }
  }, [cod])
  useEffect(() => { cargarHeader() }, [cargarHeader])

  const patch = async (body) => {
    setSaving(true)
    try { await api.patch(`/api/recetas/${cod}`, body); await cargarHeader() }
    finally { setSaving(false) }
  }
  const validar = () => patch({ estado: 'validada' })
  const devolverBorrador = () => patch({ estado: 'borrador' })

  return (
    <div className="px-3 py-4 sm:p-5 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/recetas')}>
          <ChevronLeft className="h-4 w-4" /> Volver
        </Button>
      </div>

      {r && (
        <div className="mb-5">
          <h1 className="text-[16px] sm:text-[18px] font-semibold">{r.nombre}</h1>
          <p className="text-[11px] sm:text-[12px] text-muted-foreground mt-0.5">
            cod <span className="font-mono">{r.cod_articulo}</span> · <span className="capitalize">{r.familia}</span> · <span className="font-mono">{r.patron}</span>
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <Badge variant={r.estado === 'validada' ? 'programado' : 'solicitado'}>{r.estado}</Badge>
            <Badge variant="outline">{r.confianza}</Badge>
            <Badge variant="outline">{r.n_ops_analizadas} OPs</Badge>
            <div className="flex gap-2 sm:ml-auto">
              {r.estado !== 'validada' && (
                <Button size="sm" variant="outline" onClick={validar} disabled={saving}>
                  <CheckCircle2 className="h-4 w-4" /> Validar
                </Button>
              )}
              {r.estado === 'validada' && (
                <Button variant="outline" size="sm" onClick={devolverBorrador} disabled={saving}>
                  <AlertCircle className="h-4 w-4" /> Borrador
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      <RecetaForm cod={cod} />
    </div>
  )
}
