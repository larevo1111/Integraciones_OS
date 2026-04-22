/**
 * InventariosLayoutPage — Clon 1:1 del App.vue del módulo inventario.
 * Estructura: aside (lista fechas) + contenido (header + toolbar + tabs + vista).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router"
import "@/styles/inventario.css"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"
import { NuevoInventarioModal } from "@/components/inventario/nuevo-inventario-modal"
import { TablaConteo } from "@/components/inventario/tabla-conteo"

const FILTROS_BASE = [
  { key: 'todos',     label: 'Todos' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'contado',   label: 'Contados' },
  { key: 'diferencia',label: 'Con dif.' },
]

const PERMISO_DEFAULT = {
  cerrar_conteo: true, reabrir_conteo: true, cerrar_inventario: true,
  nuevo_inventario: true, reiniciar_inventario: true, eliminar_inventario: true,
  asignar_articulo: true, ver_gestion: true,
}

export function InventariosLayoutPage() {
  const navigate = useNavigate()
  const { fecha: fechaParam } = useParams()

  // Estado base
  const [fechas, setFechas] = useState([])
  const [fecha, setFecha] = useState(fechaParam || '')
  const [bodegas, setBodegas] = useState([])
  const [bodegaActiva, setBodegaActiva] = useState('Principal')
  const [articulos, setArticulos] = useState([])
  const [resumen, setResumen] = useState({})
  const [busqueda, setBusqueda] = useState('')
  const [filtroActivo, setFiltroActivo] = useState('todos')
  const [cargando, setCargando] = useState(false)
  const [vistaActiva, setVistaActiva] = useState('conteo')
  const [estadoCierre, setEstadoCierre] = useState({ conteo_cerrado: false, inventario_cerrado: false })
  const [mostrarNuevoInv, setMostrarNuevoInv] = useState(false)
  const [calculandoTeorico, setCalculandoTeorico] = useState(false)
  const [estadoTeorico, setEstadoTeorico] = useState(null)

  // Reloj
  const [horaActual, setHoraActual] = useState('')
  useEffect(() => {
    const t = setInterval(() => {
      const d = new Date()
      setHoraActual(d.toTimeString().slice(0, 8))
    }, 1000)
    return () => clearInterval(t)
  }, [])

  const puede = (accion) => PERMISO_DEFAULT[accion] !== false  // TODO: integrar con políticas

  // Cargar fechas
  const cargarFechas = useCallback(async () => {
    try {
      const data = await api.get('/api/inventario/fechas')
      setFechas(data)
      // Si no hay fecha seleccionada, usar la primera
      if (!fecha && data.length) {
        const f = fechaParam || data[0].fecha_inventario
        setFecha(f)
        if (!fechaParam) navigate(`/inventarios/${f}`, { replace: true })
      }
    } catch (e) { console.error(e) }
  }, [fecha, fechaParam, navigate])

  useEffect(() => { cargarFechas() }, [cargarFechas])
  useEffect(() => { if (fechaParam) setFecha(fechaParam) }, [fechaParam])

  // Cargar bodegas + estado cierre cuando cambia fecha
  useEffect(() => {
    if (!fecha) return
    api.get(`/api/inventario/bodegas/todas?fecha=${fecha}`).then(setBodegas).catch(console.error)
    api.get(`/api/inventario/estado-cierre?fecha=${fecha}`).then(setEstadoCierre).catch(console.error)
    api.get(`/api/inventario/teorico/estado?fecha=${fecha}`).then(setEstadoTeorico).catch(() => setEstadoTeorico(null))
  }, [fecha])

  // Cargar artículos cuando cambian fecha + bodega + filtro
  const cargarArticulos = useCallback(async () => {
    if (!fecha) return
    setCargando(true)
    try {
      const params = new URLSearchParams({ fecha })
      if (bodegaActiva) params.set('bodega', bodegaActiva)
      if (filtroActivo && filtroActivo !== 'todos') params.set('filtro', filtroActivo)
      if (busqueda.trim()) params.set('busqueda', busqueda.trim())
      const data = await api.get(`/api/inventario/articulos?${params}`)
      setArticulos(Array.isArray(data) ? data : [])
      // Resumen
      const res = await api.get(`/api/inventario/resumen?fecha=${fecha}` + (bodegaActiva ? `&bodega=${bodegaActiva}` : ''))
      setResumen(res)
    } catch (e) {
      console.error(e); setArticulos([])
    } finally { setCargando(false) }
  }, [fecha, bodegaActiva, filtroActivo, busqueda])

  useEffect(() => { cargarArticulos() }, [cargarArticulos])

  // Bodegas con stock vs sin stock
  const bodegasConStock = useMemo(() => bodegas.filter(b => b.total > 0), [bodegas])
  const bodegasSinStock = useMemo(() => bodegas.filter(b => b.total === 0), [bodegas])

  // Filtros con count
  const filtros = useMemo(() => FILTROS_BASE.map(f => ({
    ...f,
    count: f.key === 'todos' ? (resumen.total || 0)
         : f.key === 'pendiente' ? (resumen.pendientes || 0)
         : f.key === 'contado' ? (resumen.contados || 0)
         : f.key === 'diferencia' ? (resumen.con_diferencia || 0)
         : 0
  })), [resumen])

  // Progress bar
  const pctOk = resumen.total ? Math.round(((resumen.contados - (resumen.con_diferencia || 0)) / resumen.total) * 100) : 0
  const pctDiff = resumen.total ? Math.round(((resumen.con_diferencia || 0) / resumen.total) * 100) : 0

  const cambiarFecha = (nueva) => navigate(`/inventarios/${nueva}`)

  const calcularTeorico = async () => {
    if (calculandoTeorico) return
    setCalculandoTeorico(true)
    try {
      await api.post('/api/inventario/calcular-teorico', { fecha, usuario: auth.usuario?.email || '' })
      const e = await api.get(`/api/inventario/teorico/estado?fecha=${fecha}`)
      setEstadoTeorico(e)
      await cargarArticulos()
    } catch (e) { alert('Error: ' + e.message) }
    finally { setCalculandoTeorico(false) }
  }

  const fechaDisplay = useMemo(() => {
    if (!fecha) return ''
    const [y, m, d] = fecha.split('-')
    return `${d}/${m}/${y}`
  }, [fecha])

  return (
    <div className="inv-app panel-open inv-react-root">
      {/* SIDE PANEL */}
      <aside className="inv-panel open">
        <div className="inv-panel-header">
          <span className="inv-panel-title">Inventarios</span>
          {puede('nuevo_inventario') && (
            <button className="inv-panel-add" onClick={() => setMostrarNuevoInv(true)} title="Nuevo inventario">
              <span className="material-icons" style={{ fontSize: 14 }}>add</span>
            </button>
          )}
        </div>
        <div className="inv-panel-list">
          {fechas.map(f => (
            <div key={f.fecha_inventario} className={`inv-panel-item ${fecha === f.fecha_inventario ? 'active' : ''}`}>
              <div className="inv-panel-item-main" onClick={() => cambiarFecha(f.fecha_inventario)}>
                <div className="inv-panel-item-fecha">{f.fecha_inventario}</div>
                <div className="inv-panel-item-stats">
                  <span>{f.inventariables} artículos</span>
                  <span className="inv-panel-item-pct">{f.contados}/{f.inventariables}</span>
                </div>
              </div>
              {fecha === f.fecha_inventario && (
                <div className="inv-panel-item-actions" style={{ display: 'flex', gap: 4, padding: '6px 4px 0', flexWrap: 'wrap' }}>
                  {puede('nuevo_inventario') && (
                    <button className={`inv-panel-action ${calculandoTeorico ? 'inv-panel-action-spin' : ''}`}
                            disabled={calculandoTeorico || estadoCierre.inventario_cerrado}
                            onClick={(e) => { e.stopPropagation(); calcularTeorico() }}
                            title="Calcular inventario teórico">
                      <span className={`material-icons ${calculandoTeorico ? 'spin' : ''}`} style={{ fontSize: 13 }}>analytics</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
          {!fechas.length && <div className="inv-panel-empty">Sin inventarios</div>}
        </div>
      </aside>

      {/* CONTENT */}
      <div className="inv-content">
        {/* HEADER */}
        <div className="inv-header">
          <div className="inv-header-left">
            <div className="inv-avatar">{auth.usuario?.nombre?.slice(0, 2).toUpperCase() || '?'}</div>
            <div className="inv-user-info">
              <span className="inv-user-name">{auth.usuario?.nombre}</span>
              <span className="inv-title">
                Inventario {fechaDisplay}
                {estadoCierre.inventario_cerrado && (
                  <span className="cierre-badge cierre-badge-full" style={{ marginLeft: 8 }} title="Inventario cerrado completamente">
                    <span className="material-icons" style={{ fontSize: 11 }}>verified</span> CERRADO
                  </span>
                )}
                {!estadoCierre.inventario_cerrado && estadoCierre.conteo_cerrado && (
                  <span className="cierre-badge cierre-badge-conteo" style={{ marginLeft: 8 }} title="Conteo físico cerrado">
                    <span className="material-icons" style={{ fontSize: 11 }}>lock</span> CONTEO CERRADO
                  </span>
                )}
              </span>
            </div>
          </div>
          <div className="inv-header-right">
            <div className="inv-clock">{horaActual}</div>
            <div className="inv-progress-wrap">
              <div className="inv-progress-track">
                <div className="inv-progress-ok" style={{ width: pctOk + '%' }} />
                <div className="inv-progress-diff" style={{ width: pctDiff + '%' }} />
              </div>
              <span className="inv-progress-text">{resumen.contados || 0} / {resumen.total || 0}</span>
            </div>
          </div>
        </div>

        {/* TOOLBAR */}
        <div className="inv-toolbar">
          <div className="inv-search-box">
            <span className="material-icons inv-search-icon">search</span>
            <input
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              className="inv-search-input"
              type="text"
              placeholder="Buscar por nombre o código..."
            />
          </div>
        </div>

        {/* TABS */}
        {puede('ver_gestion') && (
          <div className="inv-tabs">
            <button className={`inv-tab ${vistaActiva === 'conteo' ? 'active' : ''}`} onClick={() => setVistaActiva('conteo')}>
              <span className="material-icons" style={{ fontSize: 15 }}>inventory_2</span> Conteo
            </button>
            <button className={`inv-tab ${vistaActiva === 'gestion' ? 'active' : ''}`} onClick={() => setVistaActiva('gestion')}>
              <span className="material-icons" style={{ fontSize: 15 }}>analytics</span> Gestión
            </button>
            <button className={`inv-tab ${vistaActiva === 'costos' ? 'active' : ''}`} onClick={() => setVistaActiva('costos')}>
              <span className="material-icons" style={{ fontSize: 15 }}>attach_money</span> Costos
            </button>
          </div>
        )}

        {/* VISTA: CONTEO */}
        {vistaActiva === 'conteo' && (
          <>
            {/* FILTROS + BODEGAS */}
            <div className="inv-filters-row">
              {filtros.map(f => (
                <button key={f.key} className={`inv-pill ${filtroActivo === f.key ? 'active' : ''}`} onClick={() => setFiltroActivo(f.key)}>
                  {f.label}<span className="inv-pill-count">{f.count}</span>
                </button>
              ))}
              <span className="inv-separator" />
              <span className="inv-bodegas-label">Bodegas</span>
              <button className={`inv-pill inv-pill-bodega ${bodegaActiva === null ? 'active' : ''}`} onClick={() => setBodegaActiva(null)}>
                Todas
              </button>
              {bodegasConStock.map(b => (
                <button
                  key={b.bodega}
                  className={`inv-pill inv-pill-bodega ${bodegaActiva === b.bodega ? 'active' : ''}`}
                  onClick={() => setBodegaActiva(b.bodega)}
                >
                  {b.bodega}<span className="inv-pill-count">{b.total}</span>
                </button>
              ))}
            </div>

            {/* TABLA CONTEO */}
            <TablaConteo
              articulos={articulos}
              cargando={cargando}
              fecha={fecha}
              bodegaActiva={bodegaActiva}
              conteoBloqueado={estadoCierre.conteo_cerrado || estadoCierre.inventario_cerrado}
              onChange={cargarArticulos}
            />
          </>
        )}

        {vistaActiva === 'gestion' && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
            Vista Gestión — pendiente de migrar
          </div>
        )}

        {vistaActiva === 'costos' && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
            Vista Costos — pendiente de migrar
          </div>
        )}
      </div>

      {/* MODALES */}
      <NuevoInventarioModal
        open={mostrarNuevoInv}
        onOpenChange={setMostrarNuevoInv}
        onCreated={(nueva) => { cargarFechas(); if (nueva) cambiarFecha(nueva) }}
      />
    </div>
  )
}
