/**
 * AsignarModal — vincula un artículo "No Matriculado" del inventario con uno
 * existente del catálogo Effi.
 * GET  /api/inventario/articulos/buscar?q=...
 * POST /api/inventario/articulos/asignar
 */
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function AsignarModal({ open, articulo, onClose, onAsignado }) {
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState([])
  const [seleccionado, setSeleccionado] = useState(null)
  const [buscando, setBuscando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)

  useEffect(() => {
    if (!open) {
      setBusqueda(''); setResultados([]); setSeleccionado(null)
    }
  }, [open])

  // Búsqueda con debounce 300ms
  useEffect(() => {
    if (!open || !busqueda.trim()) { setResultados([]); return }
    const t = setTimeout(async () => {
      setBuscando(true)
      try {
        const data = await api.get(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busqueda)}`)
        setResultados(Array.isArray(data) ? data : [])
      } catch (e) { console.error(e); setResultados([]) }
      finally { setBuscando(false) }
    }, 300)
    return () => clearTimeout(t)
  }, [busqueda, open])

  if (!open || !articulo) return null

  const unidadesCoinciden = !seleccionado || (articulo.unidad || 'UND') === (seleccionado.unidad || 'UND')

  const confirmar = async () => {
    if (!seleccionado) return
    setConfirmando(true)
    try {
      await api.post('/api/inventario/articulos/asignar', {
        conteo_id: articulo.id,
        id_effi_nuevo: seleccionado.id,
        nombre_effi: seleccionado.nombre,
        categoria_effi: seleccionado.categoria || '',
        cod_barras: seleccionado.cod_barras || '',
        usuario: auth.usuario?.email || '',
      })
      onAsignado && onAsignado()
      onClose()
    } catch (e) {
      alert('Error al asignar: ' + (e.message || ''))
    } finally { setConfirmando(false) }
  }

  return (
    <div className="inv-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="inv-modal" style={{ maxWidth: 640 }}>
        <div className="inv-modal-header">
          <span className="material-icons" style={{ fontSize: 18, color: 'var(--accent)' }}>link</span>
          <span>Asignar artículo a Effi</span>
          <button className="action-btn" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-body">
          {/* Origen NM */}
          <div className="asignar-origen">
            <div className="asignar-label">Artículo No Matriculado</div>
            <div className="asignar-nombre">{articulo.nombre}</div>
            <span className="asignar-unidad-tag">{articulo.unidad || 'UND'}</span>
          </div>

          <div className="asignar-flecha">
            <span className="material-icons" style={{ fontSize: 20 }}>arrow_downward</span>
          </div>

          {!seleccionado && (
            <>
              <input
                value={busqueda}
                onChange={e => setBusqueda(e.target.value)}
                className="inv-modal-search"
                type="text"
                placeholder="Buscar artículo en Effi por nombre o código..."
                autoFocus
              />
              {buscando && <div style={{ padding: 8, fontSize: 11, color: 'var(--text-tertiary)' }}>Buscando...</div>}
              <div className="inv-modal-results">
                {resultados.map(r => (
                  <div key={r.id} className="inv-modal-result-item" onClick={() => setSeleccionado(r)}>
                    <div>
                      <span className="inv-modal-result-name">{r.nombre}</span>
                      <span className="inv-modal-result-meta">ID: {r.id} · {r.categoria || '—'} · {r.unidad || 'UND'}</span>
                    </div>
                  </div>
                ))}
                {!buscando && busqueda && !resultados.length && (
                  <div style={{ padding: 12, fontSize: 11, color: 'var(--text-tertiary)' }}>Sin resultados</div>
                )}
              </div>
            </>
          )}

          {seleccionado && (
            <div className="asignar-destino">
              <div className="asignar-label">Artículo Effi seleccionado</div>
              <div className="asignar-nombre">{seleccionado.nombre}</div>
              <div className="asignar-meta">ID: {seleccionado.id} · Cat: {seleccionado.categoria || '—'}</div>

              <div className={`asignar-comparacion ${unidadesCoinciden ? 'asignar-match' : 'asignar-mismatch'}`}>
                <span>{articulo.unidad || 'UND'}</span>
                <span className="material-icons" style={{ fontSize: 14 }}>arrow_forward</span>
                <span>{seleccionado.unidad || 'UND'}</span>
                <span className="asignar-comparacion-msg">
                  {unidadesCoinciden ? 'Unidades coinciden' : '¡Unidades diferentes!'}
                </span>
              </div>

              <div className="alerta-btns" style={{ marginTop: 12 }}>
                <button className="inv-btn-secondary" onClick={() => { setSeleccionado(null); setBusqueda('') }}>
                  Cambiar
                </button>
                <button className="inv-btn-primary" disabled={confirmando} onClick={confirmar}>
                  {confirmando ? 'Asignando…' : 'Confirmar asignación'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
