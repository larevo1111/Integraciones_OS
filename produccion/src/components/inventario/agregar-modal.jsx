/**
 * AgregarModal — agregar artículo al inventario actual.
 * 3 tabs:
 *  - buscar: busca en catálogo Effi y agrega
 *  - excluidos: muestra artículos excluidos del inventario, los reactiva
 *  - manual: crea un "No Matriculado" con nombre/cantidad/unidad/costo/foto
 *
 * Endpoints:
 *  - GET  /api/inventario/articulos/buscar?q=
 *  - POST /api/inventario/articulos/agregar  (catálogo)
 *  - GET  /api/inventario/excluidos?fecha=
 *  - PUT  /api/inventario/articulos/{id}/reactivar
 *  - POST /api/inventario/articulos/no-matriculado  (FormData)
 */
import { useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const UNIDADES = ['UND', 'KG', 'GRS', 'LT', 'ML']

export function AgregarModal({ open, fecha, bodega, onClose, onChange }) {
  const [tab, setTab] = useState('buscar')
  // tab buscar
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  // tab excluidos
  const [excluidos, setExcluidos] = useState([])
  const [busquedaExc, setBusquedaExc] = useState('')
  // tab manual
  const [mNombre, setMNombre] = useState('')
  const [mCantidad, setMCantidad] = useState('')
  const [mUnidad, setMUnidad] = useState('UND')
  const [mCosto, setMCosto] = useState('')
  const [mNotas, setMNotas] = useState('')
  const [mFoto, setMFoto] = useState(null)
  const manualFotoInput = useRef(null)

  // Reset al abrir
  useEffect(() => {
    if (!open) return
    setTab('buscar'); setBusqueda(''); setResultados([])
    setBusquedaExc(''); setExcluidos([])
    setMNombre(''); setMCantidad(''); setMUnidad('UND'); setMCosto(''); setMNotas(''); setMFoto(null)
  }, [open])

  // Búsqueda con debounce 300ms
  useEffect(() => {
    if (!open || tab !== 'buscar' || busqueda.length < 2) { setResultados([]); return }
    const t = setTimeout(async () => {
      setBuscando(true)
      try {
        const data = await api.get(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busqueda)}`)
        setResultados(Array.isArray(data) ? data : [])
      } catch (e) { console.error(e); setResultados([]) }
      finally { setBuscando(false) }
    }, 300)
    return () => clearTimeout(t)
  }, [busqueda, open, tab])

  // Cargar excluidos al abrir tab
  useEffect(() => {
    if (!open || tab !== 'excluidos' || !fecha) return
    api.get(`/api/inventario/excluidos?fecha=${fecha}`).then(d => setExcluidos(d || [])).catch(console.error)
  }, [open, tab, fecha])

  if (!open) return null

  const excluidosFiltrados = busquedaExc
    ? excluidos.filter(e => (e.nombre || '').toLowerCase().includes(busquedaExc.toLowerCase()))
    : excluidos

  const agregarDeCatalogo = async (art) => {
    try {
      await api.post('/api/inventario/articulos/agregar', {
        fecha_inventario: fecha,
        bodega: bodega || 'Principal',
        id_effi: art.id,
        contado_por: auth.usuario?.email || '',
      })
      onChange && onChange()
      onClose()
    } catch (e) { alert('Error: ' + (e.message || '')) }
  }

  const reactivar = async (art) => {
    try {
      await api.put(`/api/inventario/articulos/${art.id}/reactivar`, { usuario: auth.usuario?.email || '' })
      setExcluidos(prev => prev.filter(x => x.id !== art.id))
      onChange && onChange()
    } catch (e) { alert('Error: ' + (e.message || '')) }
  }

  const agregarManual = async () => {
    if (!mNombre || !mCantidad || !mUnidad) return
    const cant = parseFloat(String(mCantidad).replace(',', '.'))
    if (isNaN(cant)) return alert('Cantidad inválida')

    const fd = new FormData()
    fd.append('fecha_inventario', fecha)
    fd.append('bodega', bodega || 'Principal')
    fd.append('nombre', mNombre)
    fd.append('unidad', mUnidad)
    fd.append('cantidad', String(cant))
    fd.append('costo', mCosto || '0')
    fd.append('notas', mNotas || '')
    fd.append('usuario', auth.usuario?.email || '')
    if (mFoto) fd.append('foto', mFoto)

    try {
      const resp = await fetch('/api/inventario/articulos/no-matriculado', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + (localStorage.getItem('produccion_jwt') || '') },
        body: fd,
      })
      if (!resp.ok) throw new Error('upload fallido (' + resp.status + ')')
      onChange && onChange()
      onClose()
    } catch (e) { alert('Error: ' + e.message) }
  }

  const tabBtn = (key, label, onClick) => (
    <button className={`inv-modal-tab ${tab === key ? 'active' : ''}`}
            onClick={onClick || (() => setTab(key))}>
      {label}
    </button>
  )

  return (
    <div className="inv-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`inv-modal ${tab === 'manual' ? 'inv-modal-expanded' : ''}`} style={{ maxWidth: 640 }}>
        <div className="inv-modal-header">
          <span className="material-icons" style={{ fontSize: 18, color: 'var(--accent)' }}>add</span>
          <span>Agregar artículo al inventario</span>
          <button className="action-btn" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        <div className="inv-modal-tabs">
          {tabBtn('buscar', 'Buscar')}
          {tabBtn('excluidos', 'Excluidos')}
          {tabBtn('manual', 'No matriculado')}
        </div>
        <div className="inv-modal-body">
          {tab === 'buscar' && (
            <>
              <input value={busqueda} onChange={e => setBusqueda(e.target.value)}
                     className="inv-modal-search" type="text" autoFocus
                     placeholder="Buscar artículo por nombre o código..." />
              {buscando && <div style={{ padding: 8, fontSize: 11, color: 'var(--text-tertiary)' }}>Buscando…</div>}
              <div className="inv-modal-results">
                {resultados.map(r => (
                  <div key={r.id} className="inv-modal-result-item" onClick={() => agregarDeCatalogo(r)}>
                    <div>
                      <span className="inv-modal-result-name">{r.nombre}</span>
                      <span className="inv-modal-result-meta">ID: {r.id} · {r.categoria || '—'} · {r.unidad || 'UND'}</span>
                    </div>
                  </div>
                ))}
                {busqueda && !buscando && !resultados.length && (
                  <div className="inv-modal-empty">Sin resultados</div>
                )}
              </div>
            </>
          )}

          {tab === 'excluidos' && (
            <>
              <input value={busquedaExc} onChange={e => setBusquedaExc(e.target.value)}
                     className="inv-modal-search" type="text" placeholder="Filtrar excluidos..." />
              <div className="inv-modal-results">
                {excluidosFiltrados.map(e => (
                  <div key={e.id} className="inv-modal-result-item" onClick={() => reactivar(e)}>
                    <div>
                      <span className="inv-modal-result-name">{e.nombre}</span>
                      <span className="inv-modal-result-meta">ID: {e.id_effi} · {e.categoria || '—'}</span>
                    </div>
                  </div>
                ))}
                {!excluidosFiltrados.length && (
                  <div className="inv-modal-empty">
                    {busquedaExc ? 'Sin resultados' : 'No hay artículos excluidos'}
                  </div>
                )}
              </div>
            </>
          )}

          {tab === 'manual' && (
            <>
              <div className="inv-form-group">
                <label className="inv-form-label">Nombre del artículo *</label>
                <input value={mNombre} onChange={e => setMNombre(e.target.value)}
                       className="inv-form-input" type="text"
                       placeholder="Ej: Producto nuevo sin código" />
              </div>
              <div className="inv-form-row">
                <div className="inv-form-group inv-form-half">
                  <label className="inv-form-label">Cantidad *</label>
                  <input value={mCantidad} onChange={e => setMCantidad(e.target.value)}
                         className="inv-form-input" type="text" inputMode="decimal" placeholder="0" />
                </div>
                <div className="inv-form-group inv-form-half">
                  <label className="inv-form-label">Unidad *</label>
                  <select value={mUnidad} onChange={e => setMUnidad(e.target.value)} className="inv-form-input">
                    {UNIDADES.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
              </div>
              <div className="inv-form-group">
                <label className="inv-form-label">Costo unitario</label>
                <input value={mCosto} onChange={e => setMCosto(e.target.value)}
                       className="inv-form-input" type="text" inputMode="decimal" placeholder="Opcional" />
              </div>
              <div className="inv-form-group">
                <label className="inv-form-label">Observaciones</label>
                <textarea value={mNotas} onChange={e => setMNotas(e.target.value)}
                          className="inv-nota-textarea" rows={2}
                          placeholder="Por qué no está matriculado, dónde se encontró..." />
              </div>
              <div className="inv-form-group">
                <label className="inv-form-label">Foto</label>
                <button className="inv-btn-outline" onClick={() => manualFotoInput.current?.click()}>
                  <span className="material-icons" style={{ fontSize: 14 }}>photo_camera</span>
                  {' '}{mFoto?.name || 'Tomar foto'}
                </button>
                <input ref={manualFotoInput} type="file" accept="image/*" capture="environment"
                       style={{ display: 'none' }}
                       onChange={e => setMFoto(e.target.files?.[0] || null)} />
              </div>
              <button className="inv-btn-primary"
                      disabled={!mNombre || !mCantidad || !mUnidad}
                      onClick={agregarManual}>
                Agregar artículo
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
