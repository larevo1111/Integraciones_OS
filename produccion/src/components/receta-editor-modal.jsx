import { X } from "lucide-react"
import { RecetaForm } from "./receta-form"

/**
 * Modal de edición rápida de receta. Reusa <RecetaForm> con la misma lógica de la página
 * de receta-detalle. Pensado para abrirse desde otros flujos (ej: preview de OP).
 *
 * Props:
 *  - cod: string (cod_articulo del producto principal)
 *  - open: bool
 *  - onOpenChange: (bool) => void
 *  - onSaved: () => void (opcional)
 */
export function RecetaEditorModal({ cod, open, onOpenChange, onSaved }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/60 p-2 sm:p-4 overflow-y-auto" onClick={() => onOpenChange(false)}>
      <div
        className="bg-background border border-border rounded-lg shadow-2xl w-full max-w-[1100px] my-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-3 border-b border-border sticky top-0 bg-background z-10 rounded-t-lg">
          <div>
            <div className="text-[14px] font-semibold">Modificar receta</div>
            <div className="text-[11px] text-muted-foreground">cod <span className="font-mono">{cod}</span></div>
          </div>
          <button onClick={() => onOpenChange(false)} className="text-muted-foreground hover:text-foreground p-1">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-3 sm:p-4">
          <RecetaForm
            cod={cod}
            hideNotas
            onSaved={() => { if (onSaved) onSaved() }}
          />
        </div>
      </div>
    </div>
  )
}
