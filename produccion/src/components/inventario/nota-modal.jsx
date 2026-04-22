/**
 * NotaModal — editar/agregar nota a un artículo del inventario.
 * PUT /api/inventario/articulos/{id}/nota
 */
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function NotaModal({ open, articulo, onClose, onSaved }) {
  const [texto, setTexto] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    if (open && articulo) setTexto(articulo.notas || '')
  }, [open, articulo])

  if (!open || !articulo) return null

  const guardar = async () => {
    setGuardando(true)
    try {
      await api.put(`/api/inventario/articulos/${articulo.id}/nota`, {
        notas: texto, usuario: auth.usuario?.email || '',
      })
      onSaved && onSaved(texto)
      onClose()
    } catch (e) {
      alert('Error al guardar la nota: ' + (e.message || ''))
    } finally { setGuardando(false) }
  }

  return (
    <div className="inv-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="inv-modal inv-modal-sm">
        <div className="inv-modal-header">
          <span className="material-icons" style={{ fontSize: 18, color: 'var(--accent)' }}>edit_note</span>
          <span>{articulo.notas ? 'Editar nota' : 'Agregar nota'}</span>
          <button className="action-btn" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-body">
          <p className="alerta-mensaje" style={{ color: 'var(--text-tertiary)', fontSize: 11, marginBottom: 8 }}>
            {articulo.id_effi} — {articulo.nombre}
          </p>
          <textarea
            value={texto}
            onChange={e => setTexto(e.target.value)}
            placeholder="Escribir nota..."
            rows={4}
            className="inv-form-input"
            style={{ width: '100%', resize: 'vertical', minHeight: 80 }}
          />
          <div className="alerta-btns">
            <button className="alerta-btn-confirmar" onClick={onClose}>Cancelar</button>
            <button className="inv-btn-primary" disabled={guardando} onClick={guardar}>
              {guardando ? 'Guardando…' : 'Guardar nota'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
