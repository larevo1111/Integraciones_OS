import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

/**
 * NuevoInventarioModal — clon del modal Vue (líneas 65-117 de App.vue).
 * Mantiene mismas clases CSS para que se vea idéntico.
 */
export function NuevoInventarioModal({ open, onOpenChange, onCreated }) {
  const hoy = new Date().toISOString().slice(0, 10)
  const [nuevaFecha, setNuevaFecha] = useState(hoy)
  const [tipo, setTipo] = useState('completo')
  const [cantidadParcial, setCantidadParcial] = useState(15)
  const [sugeridos, setSugeridos] = useState([])
  const [sugiriendo, setSugiriendo] = useState(false)
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open) {
      setTipo('completo'); setSugeridos([]); setError(null); setNuevaFecha(hoy)
    }
  }, [open])

  if (!open) return null

  const sugerirArticulos = async () => {
    setSugiriendo(true); setError(null)
    try {
      const data = await api.get(`/api/inventario/sugerir-articulos?cantidad=${cantidadParcial}`)
      setSugeridos(data.map(s => ({ ...s, seleccionado: true })))
    } catch (e) { setError(e.message); setSugeridos([]) }
    finally { setSugiriendo(false) }
  }

  const crearInventario = async () => {
    if (!nuevaFecha) return
    setCreando(true); setError(null)
    try {
      const body = {
        fecha_inventario: nuevaFecha,
        usuario: auth.usuario?.email || '',
        tipo,
      }
      if (tipo === 'parcial') body.articulos = sugeridos.filter(s => s.seleccionado).map(s => s.id_effi)
      await api.post('/api/inventario/nuevo', body)
      onCreated?.(nuevaFecha)
      onOpenChange(false)
    } catch (e) { setError(e.message) }
    finally { setCreando(false) }
  }

  const nSel = sugeridos.filter(s => s.seleccionado).length
  const sizeClass = (tipo === 'parcial' && sugeridos.length) ? 'inv-modal-lg' : 'inv-modal-sm'

  return (
    <div className="inv-overlay" onClick={(e) => { if (e.target === e.currentTarget) onOpenChange(false) }}>
      <div className={`inv-modal ${sizeClass}`}>
        <div className="inv-modal-header">
          <span>Nuevo inventario</span>
          <button className="action-btn" onClick={() => onOpenChange(false)}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-body">
          <label className="inv-form-label">Fecha de corte</label>
          <input value={nuevaFecha} onChange={e => setNuevaFecha(e.target.value)} type="date" className="inv-form-input" />

          <label className="inv-form-label" style={{ marginTop: 12 }}>Tipo de inventario</label>
          <div className="inv-tipo-toggle">
            <button className={`inv-tipo-btn ${tipo === 'completo' ? 'active' : ''}`} onClick={() => { setTipo('completo'); setSugeridos([]) }}>
              <span className="material-icons" style={{ fontSize: 16 }}>select_all</span> Completo
            </button>
            <button className={`inv-tipo-btn ${tipo === 'parcial' ? 'active' : ''}`} onClick={() => setTipo('parcial')}>
              <span className="material-icons" style={{ fontSize: 16 }}>checklist</span> Parcial
            </button>
          </div>

          {tipo === 'completo' && (
            <p className="inv-form-hint">Se generarán todos los artículos inventariables con el stock a esta fecha.</p>
          )}

          {tipo === 'parcial' && (
            <>
              <div className="inv-parcial-config">
                <label className="inv-form-label">Cantidad de artículos</label>
                <div className="inv-parcial-row">
                  <input value={cantidadParcial} onChange={e => setCantidadParcial(+e.target.value)}
                         type="number" min="5" max="50" className="inv-form-input" style={{ width: 80 }} />
                  <button className="inv-btn-secondary" disabled={sugiriendo} onClick={sugerirArticulos}>
                    <span className={`material-icons ${sugiriendo ? 'spin' : ''}`} style={{ fontSize: 14 }}>auto_awesome</span>
                    {sugiriendo ? 'Cargando...' : 'Sugerir artículos'}
                  </button>
                </div>
              </div>

              {sugeridos.length > 0 && (
                <div className="inv-sugeridos">
                  <div className="inv-sugeridos-header">
                    <span className="inv-form-label" style={{ margin: 0 }}>{nSel} seleccionados de {sugeridos.length}</span>
                    <button className="inv-link-btn" onClick={() => setSugeridos(s => s.map(x => ({ ...x, seleccionado: true })))}>Todos</button>
                    <button className="inv-link-btn" onClick={() => setSugeridos(s => s.map(x => ({ ...x, seleccionado: false })))}>Ninguno</button>
                  </div>
                  <div className="inv-sugeridos-list">
                    {sugeridos.map((s, i) => (
                      <label key={i} className={`inv-sugerido-item ${s.seleccionado ? 'checked' : ''}`}>
                        <input type="checkbox" checked={s.seleccionado}
                               onChange={e => setSugeridos(prev => prev.map((x, idx) => idx === i ? { ...x, seleccionado: e.target.checked } : x))} />
                        <span className="inv-sug-cod">{s.id_effi}</span>
                        <span className="inv-sug-nombre">{s.nombre}</span>
                        <span className="inv-sug-grupo">{s.grupo}</span>
                        <span className="inv-sug-razon">{s.razon}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {error && <div style={{ color: 'var(--color-error)', fontSize: 12, marginTop: 8 }}>{error}</div>}

          <button className="inv-btn-primary" style={{ marginTop: 12 }}
                  disabled={!nuevaFecha || creando || (tipo === 'parcial' && nSel === 0)}
                  onClick={crearInventario}>
            {creando ? 'Creando...' : tipo === 'completo' ? 'Crear inventario completo' : `Crear inventario parcial (${nSel} art.)`}
          </button>
        </div>
      </div>
    </div>
  )
}
