/**
 * FotoVerModal — lightbox para ver una foto subida de un artículo.
 * GET /api/inventario/fotos/{filename}
 */
export function FotoVerModal({ open, articulo, onClose }) {
  if (!open || !articulo?.foto) return null
  const src = `/api/inventario/fotos/${articulo.foto}`

  return (
    <div className="inv-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="inv-modal" style={{ maxWidth: 720 }}>
        <div className="inv-modal-header">
          <span className="material-icons" style={{ fontSize: 18, color: 'var(--accent)' }}>visibility</span>
          <span>Foto — {articulo.id_effi} · {articulo.nombre}</span>
          <button className="action-btn" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-body" style={{ display: 'flex', justifyContent: 'center' }}>
          <img src={src} alt={articulo.nombre} className="inv-foto-preview"
               style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 8 }} />
        </div>
      </div>
    </div>
  )
}
