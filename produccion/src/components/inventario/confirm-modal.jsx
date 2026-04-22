/**
 * ConfirmModal — modal genérico de confirmación.
 * Clon 1:1 de los modales del App.vue inventario (clases inv-overlay, inv-modal, etc.)
 *
 * Props:
 *  - open (bool): si está visible
 *  - onClose (fn): cerrar
 *  - onConfirm (fn): confirmar (se llama solo si confirmText === requiredText o no se pide)
 *  - titulo (string): texto del header
 *  - icono (string): material icon name (ej "lock", "verified", "delete_forever")
 *  - variante ('default' | 'warn' | 'danger'): estilo del header + botón
 *  - mensaje (string | node): texto principal
 *  - mensajeSecundario (string | node): texto chico debajo
 *  - textoConfirmar (string): label del botón de acción
 *  - requiredText (string | null): si se define, el usuario debe escribir este texto
 */
import { useState, useEffect } from "react"

export function ConfirmModal({
  open, onClose, onConfirm,
  titulo, icono = 'warning', variante = 'default',
  mensaje, mensajeSecundario,
  textoConfirmar = 'Confirmar', requiredText = null,
}) {
  const [inputTexto, setInputTexto] = useState('')

  useEffect(() => { if (!open) setInputTexto('') }, [open])

  if (!open) return null

  const headerClass = variante === 'warn'
    ? 'inv-modal-header inv-modal-header-warn'
    : variante === 'danger'
    ? 'inv-modal-header inv-modal-header-warn'
    : 'inv-modal-header'

  const iconColor = variante === 'warn' ? '#fbbf24'
    : variante === 'danger' ? 'var(--color-error)'
    : 'var(--accent)'

  const btnClass = variante === 'danger' ? 'inv-btn-danger'
    : variante === 'warn' ? 'inv-btn-primary'
    : 'inv-btn-primary'

  const btnStyle = variante === 'warn' ? { background: '#fbbf24' } : undefined

  const puedeConfirmar = !requiredText || inputTexto === requiredText

  const handleConfirm = () => {
    if (!puedeConfirmar) return
    onConfirm()
  }

  return (
    <div className="inv-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="inv-modal inv-modal-sm">
        <div className={headerClass}>
          <span className="material-icons" style={{ fontSize: 18, color: iconColor }}>{icono}</span>
          <span>{titulo}</span>
          <button className="action-btn" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-body">
          {mensaje && <p className="alerta-mensaje">{mensaje}</p>}
          {mensajeSecundario && (
            <p className="alerta-mensaje" style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>
              {mensajeSecundario}
            </p>
          )}
          {requiredText && (
            <input
              value={inputTexto}
              onChange={e => setInputTexto(e.target.value)}
              type="text"
              placeholder={`Escribir ${requiredText}`}
              className="inv-form-input"
              style={{ marginBottom: 10, textAlign: 'center', fontWeight: 600, letterSpacing: 2 }}
            />
          )}
          <div className="alerta-btns">
            <button className="alerta-btn-confirmar" onClick={onClose}>Cancelar</button>
            <button
              className={btnClass}
              style={btnStyle}
              disabled={!puedeConfirmar}
              onClick={handleConfirm}
            >
              {textoConfirmar}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
