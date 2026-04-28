/**
 * InventariosLayoutPage — Clon 1:1 del App.vue del módulo inventario.
 * Estructura: aside (lista fechas) + contenido (header + toolbar + tabs + vista).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router"
import "@/styles/inventario.css"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"
import { NuevoInventarioModal } from "@/components/inventario/nuevo-inventario-modal"
import { TablaConteo } from "@/components/inventario/tabla-conteo"
import { ConfirmModal } from "@/components/inventario/confirm-modal"
import { NotaModal } from "@/components/inventario/nota-modal"
import { FotoVerModal } from "@/components/inventario/foto-ver-modal"
import { AsignarModal } from "@/components/inventario/asignar-modal"
import { AgregarModal } from "@/components/inventario/agregar-modal"
import { VistaGestion } from "@/components/inventario/vista-gestion"
import { VistaCostos } from "@/components/inventario/vista-costos"
import { VistaResumen } from "@/components/inventario/vista-resumen"

const FILTROS_BASE = [
  { key: 'todos',     label: 'Todos' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'contado',   label: 'Contados' },
  { key: 'diferencia',label: 'Diferencias' },
]

const PERMISO_DEFAULT = {
  cerrar_conteo: true, reabrir_conteo: true, cerrar_inventario: true,
  nuevo_inventario: true, reiniciar_inventario: true, eliminar_inventario: true,
  asignar_articulo: true, ver_gestion: true,
}

export function InventariosLayoutPage() {
  const navigate = useNavigate()
  const { fecha: fechaParam } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()

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
  // Modales aside
  const [modalAbierto, setModalAbierto] = useState(null)  // 'cerrar-conteo' | 'reabrir-conteo' | 'cerrar-inv' | 'reiniciar' | 'eliminar' | null
  // Modales por fila
  const [accionFila, setAccionFila] = useState({ tipo: null, articulo: null })  // tipo: 'nota' | 'ver-foto' | 'asignar' | null
  const fotoInputRef = useRef(null)
  const articuloFotoRef = useRef(null)  // qué artículo recibirá la foto pendiente
  const [mostrarAgregar, setMostrarAgregar] = useState(false)

  // Reloj — formato Vue: "Mié 22 Abr 2026 · 17:11:21"
  const [horaActual, setHoraActual] = useState('')
  useEffect(() => {
    const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    const upd = () => {
      const d = new Date()
      const h = String(d.getHours()).padStart(2, '0')
      const m = String(d.getMinutes()).padStart(2, '0')
      const s = String(d.getSeconds()).padStart(2, '0')
      setHoraActual(`${dias[d.getDay()]} ${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()} · ${h}:${m}:${s}`)
    }
    upd()
    const t = setInterval(upd, 1000)
    return () => clearInterval(t)
  }, [])

  // Aside abierto/cerrado (panelAbierto del Vue)
  const [panelAbierto, setPanelAbierto] = useState(true)

  // Sync Effi state — refresh completo (artículos + OPs)
  const [syncEstado, setSyncEstado] = useState('idle')
  const [syncMensaje, setSyncMensaje] = useState('')
  const lanzarSync = async () => {
    if (syncEstado !== 'idle') return
    setSyncEstado('ejecutando'); setSyncMensaje('Iniciando…')
    try {
      await api.post('/api/refresh-effi', {})
      const poll = setInterval(async () => {
        try {
          const s = await api.get('/api/refresh-effi/estado')
          setSyncEstado(s.estado || 'idle')
          setSyncMensaje(s.mensaje || '')
          if (s.estado === 'ok' || s.estado === 'error' || s.estado === 'idle') {
            clearInterval(poll)
            setTimeout(() => { setSyncEstado('idle'); setSyncMensaje('') }, 4000)
            cargarArticulos()
          }
        } catch (_) { clearInterval(poll); setSyncEstado('idle') }
      }, 2500)
    } catch (e) {
      alert('Error sync: ' + e.message); setSyncEstado('idle')
    }
  }

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

  // Abrir modal automáticamente si viene ?accion=... (desde el sidebar)
  useEffect(() => {
    const accion = searchParams.get('accion')
    if (!accion || !fecha) return
    const validas = ['cerrar-conteo', 'reabrir-conteo', 'cerrar-inv', 'reiniciar', 'eliminar']
    if (validas.includes(accion)) setModalAbierto(accion)
    // limpiar el query param para no reabrir al refrescar
    const next = new URLSearchParams(searchParams)
    next.delete('accion')
    setSearchParams(next, { replace: true })
  }, [searchParams, fecha, setSearchParams])

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

  const MESES_CORTOS = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  const fmtFechaCorta = (yyyymmdd) => {
    if (!yyyymmdd) return ''
    const [y, m, d] = yyyymmdd.split('-')
    return `${parseInt(d, 10)} ${MESES_CORTOS[parseInt(m, 10) - 1]} ${y}`
  }

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

  const recargarTodo = async () => {
    if (!fecha) return
    try {
      const ec = await api.get(`/api/inventario/estado-cierre?fecha=${fecha}`)
      setEstadoCierre(ec)
    } catch (_) {}
    await cargarArticulos()
  }

  const ejecutarAccion = async (accion) => {
    const usuario = auth.usuario?.email || ''
    const endpoints = {
      'cerrar-conteo':   '/api/inventario/cerrar-conteo',
      'reabrir-conteo':  '/api/inventario/reabrir-conteo',
      'cerrar-inv':      '/api/inventario/cerrar-inventario',
      'reiniciar':       '/api/inventario/reiniciar',
      'eliminar':        '/api/inventario/eliminar',
    }
    try {
      await api.post(endpoints[accion], { fecha_inventario: fecha, usuario })
      setModalAbierto(null)
      if (accion === 'eliminar') {
        // Recargar lista de fechas y cambiar a otra
        const data = await api.get('/api/inventario/fechas')
        setFechas(data)
        if (data.length) cambiarFecha(data[0].fecha_inventario)
        else { setArticulos([]); setResumen({}) }
      } else {
        await recargarTodo()
      }
    } catch (e) {
      alert('Error: ' + (e.message || 'No se pudo ejecutar la acción'))
    }
  }

  const fechaDisplay = useMemo(() => {
    if (!fecha) return ''
    const [y, m, d] = fecha.split('-')
    return `${d}/${m}/${y}`
  }, [fecha])

  return (
    <div className="inv-app inv-react-root inv-no-panel">
      {/* CONTENT */}
      <div className="inv-content">
        {/* HEADER */}
        <div className="inv-header">
          <div className="inv-header-left">
            <div className="inv-avatar">{(auth.usuario?.nombre || '?').charAt(0).toUpperCase()}</div>
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
            {/* Acciones del inventario activo (antes vivían en el aside) */}
            {fecha && puede('nuevo_inventario') && (
              <button className={`inv-header-action ${calculandoTeorico ? 'inv-panel-action-spin' : ''}`}
                      disabled={calculandoTeorico || estadoCierre.inventario_cerrado}
                      onClick={calcularTeorico}
                      title={estadoTeorico?.calculado ? `Recalcular teórico (${estadoTeorico.calculado_en || ''})` : 'Calcular inventario teórico'}>
                <span className={`material-icons ${calculandoTeorico ? 'spin' : ''}`} style={{ fontSize: 16 }}>analytics</span>
              </button>
            )}
            {fecha && puede('cerrar_conteo') && !estadoCierre.conteo_cerrado && (
              <button className="inv-header-action" onClick={() => setModalAbierto('cerrar-conteo')} title="Cerrar conteo físico">
                <span className="material-icons" style={{ fontSize: 16 }}>lock</span>
              </button>
            )}
            {fecha && puede('reabrir_conteo') && estadoCierre.conteo_cerrado && !estadoCierre.inventario_cerrado && (
              <button className="inv-header-action" onClick={() => setModalAbierto('reabrir-conteo')} title="Reabrir conteo físico">
                <span className="material-icons" style={{ fontSize: 16 }}>lock_open</span>
              </button>
            )}
            {fecha && puede('cerrar_inventario') && estadoCierre.conteo_cerrado && !estadoCierre.inventario_cerrado && (
              <button className="inv-header-action inv-header-action-warn" onClick={() => setModalAbierto('cerrar-inv')} title="Cerrar inventario completo">
                <span className="material-icons" style={{ fontSize: 16 }}>verified</span>
              </button>
            )}
            {fecha && puede('reiniciar_inventario') && !estadoCierre.conteo_cerrado && (
              <button className="inv-header-action inv-header-action-danger" onClick={() => setModalAbierto('reiniciar')} title="Reiniciar conteos">
                <span className="material-icons" style={{ fontSize: 16 }}>restart_alt</span>
              </button>
            )}
            {fecha && puede('eliminar_inventario') && !estadoCierre.inventario_cerrado && (
              <button className="inv-header-action inv-header-action-danger" onClick={() => setModalAbierto('eliminar')} title="Eliminar inventario">
                <span className="material-icons" style={{ fontSize: 16 }}>delete_outline</span>
              </button>
            )}
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
          <button
            className={`inv-btn-sync ${syncEstado === 'ejecutando' || syncEstado === 'iniciando' ? 'syncing' : ''}`}
            disabled={syncEstado === 'ejecutando' || syncEstado === 'iniciando'}
            onClick={lanzarSync}
            title="Actualizar artículos + OPs desde Effi"
          >
            <span className={`material-icons ${syncEstado === 'ejecutando' || syncEstado === 'iniciando' ? 'spin' : ''}`} style={{ fontSize: 16 }}>sync</span>
            <span>{syncEstado === 'ejecutando' ? (syncMensaje || 'Sincronizando…') : syncEstado === 'ok' ? '✓ Listo' : syncEstado === 'error' ? '✗ Error' : 'Sync Effi'}</span>
          </button>
          <button className="inv-btn-scan" title="Escanear código de barras (próximamente)">
            <span className="material-icons" style={{ fontSize: 16 }}>qr_code_scanner</span>
            Escanear
          </button>
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
            <button className={`inv-tab ${vistaActiva === 'resumen' ? 'active' : ''}`} onClick={() => setVistaActiva('resumen')}>
              <span className="material-icons" style={{ fontSize: 15 }}>pie_chart</span> Resumen
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
              onAccionFila={(tipo, articulo) => {
                if (tipo === 'foto') {
                  articuloFotoRef.current = articulo
                  fotoInputRef.current?.click()
                } else {
                  setAccionFila({ tipo, articulo })
                }
              }}
            />
          </>
        )}

        {vistaActiva === 'gestion' && <VistaGestion fecha={fecha} />}

        {vistaActiva === 'costos' && <VistaCostos fecha={fecha} />}

        {vistaActiva === 'resumen' && <VistaResumen fecha={fecha} />}
      </div>

      {/* MODALES */}
      <NuevoInventarioModal
        open={mostrarNuevoInv}
        onOpenChange={setMostrarNuevoInv}
        onCreated={(nueva) => { cargarFechas(); if (nueva) cambiarFecha(nueva) }}
      />

      <ConfirmModal
        open={modalAbierto === 'cerrar-conteo'}
        onClose={() => setModalAbierto(null)}
        onConfirm={() => ejecutarAccion('cerrar-conteo')}
        titulo="Cerrar conteo físico"
        icono="lock"
        variante="default"
        mensaje="Una vez cerrado el conteo no se podrán modificar los conteos físicos."
        mensajeSecundario="Podés reabrir el conteo después si fuera necesario."
        textoConfirmar="Cerrar conteo"
      />

      <ConfirmModal
        open={modalAbierto === 'reabrir-conteo'}
        onClose={() => setModalAbierto(null)}
        onConfirm={() => ejecutarAccion('reabrir-conteo')}
        titulo="Reabrir conteo físico"
        icono="lock_open"
        variante="default"
        mensaje="Se permitirá editar conteos físicos nuevamente."
        textoConfirmar="Reabrir conteo"
      />

      <ConfirmModal
        open={modalAbierto === 'cerrar-inv'}
        onClose={() => setModalAbierto(null)}
        onConfirm={() => ejecutarAccion('cerrar-inv')}
        titulo="Cerrar inventario completo"
        icono="verified"
        variante="warn"
        mensaje="Esta acción es irreversible: el inventario quedará cerrado definitivamente."
        mensajeSecundario="Ya no se podrá modificar ningún dato: ni conteos, ni gestión de inconsistencias, ni resoluciones, ni ajustes. Solo se podrá ver el informe final."
        textoConfirmar="Cerrar inventario completo"
      />

      <ConfirmModal
        open={modalAbierto === 'reiniciar'}
        onClose={() => setModalAbierto(null)}
        onConfirm={() => ejecutarAccion('reiniciar')}
        titulo="Reiniciar conteos"
        icono="restart_alt"
        variante="danger"
        mensaje={`Se borrarán TODOS los conteos del inventario ${fechaDisplay}. Las notas y fotos también se perderán. Esta acción es irreversible.`}
        mensajeSecundario="Para confirmar, escribí REINICIAR en el campo de abajo."
        requiredText="REINICIAR"
        textoConfirmar="Reiniciar conteos"
      />

      <ConfirmModal
        open={modalAbierto === 'eliminar'}
        onClose={() => setModalAbierto(null)}
        onConfirm={() => ejecutarAccion('eliminar')}
        titulo="Eliminar inventario"
        icono="delete_forever"
        variante="danger"
        mensaje={`Se eliminarán TODOS los registros del inventario ${fechaDisplay}, incluyendo conteos, notas y fotos. Esta acción es irreversible.`}
        textoConfirmar="Eliminar inventario"
      />

      {/* MODALES POR FILA */}
      <NotaModal
        open={accionFila.tipo === 'nota'}
        articulo={accionFila.articulo}
        onClose={() => setAccionFila({ tipo: null, articulo: null })}
        onSaved={() => cargarArticulos()}
      />

      <FotoVerModal
        open={accionFila.tipo === 'ver-foto'}
        articulo={accionFila.articulo}
        onClose={() => setAccionFila({ tipo: null, articulo: null })}
      />

      <AsignarModal
        open={accionFila.tipo === 'asignar'}
        articulo={accionFila.articulo}
        onClose={() => setAccionFila({ tipo: null, articulo: null })}
        onAsignado={() => cargarArticulos()}
      />

      <AgregarModal
        open={mostrarAgregar}
        fecha={fecha}
        bodega={bodegaActiva}
        onClose={() => setMostrarAgregar(false)}
        onChange={() => { cargarArticulos(); api.get(`/api/inventario/bodegas/todas?fecha=${fecha}`).then(setBodegas) }}
      />

      {/* FAB agregar artículo (solo si conteo abierto) */}
      {!estadoCierre.conteo_cerrado && !estadoCierre.inventario_cerrado && (
        <button className="inv-fab" onClick={() => setMostrarAgregar(true)} title="Agregar artículo">
          <span className="material-icons">add</span>
        </button>
      )}

      {/* INPUT OCULTO PARA TOMAR FOTO (cámara móvil) */}
      <input
        ref={fotoInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={async (e) => {
          const file = e.target.files?.[0]
          const art = articuloFotoRef.current
          if (!file || !art) return
          try {
            const fd = new FormData()
            fd.append('file', file)
            fd.append('usuario', auth.usuario?.email || '')
            const resp = await fetch(`/api/inventario/articulos/${art.id}/foto`, {
              method: 'POST',
              headers: { Authorization: 'Bearer ' + (localStorage.getItem('produccion_jwt') || '') },
              body: fd,
            })
            if (!resp.ok) throw new Error('upload fallido (' + resp.status + ')')
            await cargarArticulos()
          } catch (err) {
            alert('Error subiendo foto: ' + err.message)
          } finally {
            articuloFotoRef.current = null
            e.target.value = ''
          }
        }}
      />
    </div>
  )
}
