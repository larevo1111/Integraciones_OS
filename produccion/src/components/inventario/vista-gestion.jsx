/**
 * VistaGestion — Tab "Gestión" del inventario.
 * Sub-tabs: Dashboard (KPIs + filtros + observaciones + tabla artículos) + Auditoría OPs (placeholder).
 *
 * Endpoints:
 *  - GET  /api/inventario/gestion/dashboard?fecha=
 *  - POST /api/inventario/gestion/calcular  (si dashboard.vacio)
 *  - GET  /api/inventario/gestion?fecha=&severidad=&estado=&grupo=
 *  - POST /api/inventario/gestion/analizar  (lanza análisis async)
 *  - GET  /api/inventario/gestion/analisis-estado  (polling)
 *  - GET  /api/inventario/observaciones?fecha=
 *  - POST /api/inventario/observaciones
 *  - DELETE /api/inventario/observaciones/{id}
 *  - GET  /api/inventario/informes/inventario.pdf?fecha=
 *  - GET  /api/inventario/informes/analisis-ia.pdf?fecha=
 */
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const fmtMoney = (n) => {
  if (n == null || isNaN(n)) return '0'
  return Math.round(n).toLocaleString('es-CO')
}

const TIPOS_OBS = [
  { val: 'manual',           label: 'Nota' },
  { val: 'hallazgo',         label: 'Hallazgo' },
  { val: 'error_conteo',     label: 'Error conteo' },
  { val: 'correccion_costo', label: 'Corrección costo' },
]

export function VistaGestion({ fecha }) {
  const [subtab, setSubtab] = useState('dashboard')
  const [dash, setDash] = useState(null)
  const [articulos, setArticulos] = useState([])
  const [filtroSev, setFiltroSev] = useState(null)
  const [filtroEstado, setFiltroEstado] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [calculando, setCalculando] = useState(false)
  // Análisis IA
  const [analizando, setAnalizando] = useState(false)
  const [progAct, setProgAct] = useState({ progreso: 0, total: 0 })
  // Informes
  const [generandoInforme, setGenerandoInforme] = useState(false)
  const [generandoIA, setGenerandoIA] = useState(false)
  // Observaciones
  const [observaciones, setObservaciones] = useState([])
  const [obsExpanded, setObsExpanded] = useState(false)
  const [nuevaObsTipo, setNuevaObsTipo] = useState('manual')
  const [nuevaObsTexto, setNuevaObsTexto] = useState('')

  // Cargar dashboard al abrir
  const cargarDashboard = async () => {
    if (!fecha) return
    setCargando(true)
    try {
      let d = await api.get(`/api/inventario/gestion/dashboard?fecha=${fecha}`)
      if (d?.vacio) {
        setCalculando(true)
        await api.post('/api/inventario/gestion/calcular', { fecha_inventario: fecha, usuario: auth.usuario?.email || '' })
        d = await api.get(`/api/inventario/gestion/dashboard?fecha=${fecha}`)
        setCalculando(false)
      }
      setDash(d)
    } catch (e) { console.error(e) }
    finally { setCargando(false) }
  }

  const cargarArticulos = async () => {
    if (!fecha) return
    let url = `/api/inventario/gestion?fecha=${fecha}`
    if (filtroSev)    url += `&severidad=${filtroSev}`
    if (filtroEstado) url += `&estado=${filtroEstado}`
    try {
      const data = await api.get(url)
      setArticulos(Array.isArray(data) ? data : [])
    } catch (e) { console.error(e); setArticulos([]) }
  }

  const cargarObservaciones = async () => {
    if (!fecha) return
    try {
      const data = await api.get(`/api/inventario/observaciones?fecha=${fecha}`)
      setObservaciones(Array.isArray(data) ? data : [])
    } catch (e) { console.error(e); setObservaciones([]) }
  }

  useEffect(() => { cargarDashboard(); cargarObservaciones() }, [fecha])
  useEffect(() => { cargarArticulos() }, [fecha, filtroSev, filtroEstado])

  // ── Análisis IA — lanza POST y hace polling ──
  const lanzarAnalisis = async () => {
    if (analizando || !fecha) return
    setAnalizando(true)
    try {
      await api.post('/api/inventario/gestion/analizar', { fecha_inventario: fecha, usuario: auth.usuario?.email || '' })
      const poll = setInterval(async () => {
        try {
          const s = await api.get('/api/inventario/gestion/analisis-estado')
          setProgAct({ progreso: s.progreso || 0, total: s.total || 0 })
          if (s.estado === 'ok' || s.estado === 'error') {
            clearInterval(poll); setAnalizando(false)
            await Promise.all([cargarDashboard(), cargarArticulos()])
          }
        } catch (_) { clearInterval(poll); setAnalizando(false) }
      }, 2000)
    } catch (e) { alert('Error: ' + e.message); setAnalizando(false) }
  }

  // ── Descargar PDFs ──
  const descargarInforme = async () => {
    if (generandoInforme || !fecha) return
    setGenerandoInforme(true)
    try {
      window.open(`/api/inventario/informes/inventario.pdf?fecha=${fecha}`, '_blank')
    } catch (e) { alert('Error: ' + e.message) }
    finally { setTimeout(() => setGenerandoInforme(false), 1000) }
  }
  const descargarAnalisisIA = async () => {
    if (generandoIA || !fecha) return
    setGenerandoIA(true)
    try {
      window.open(`/api/inventario/informes/analisis-ia.pdf?fecha=${fecha}`, '_blank')
    } catch (e) { alert('Error: ' + e.message) }
    finally { setTimeout(() => setGenerandoIA(false), 1000) }
  }

  // ── Observaciones ──
  const agregarObservacion = async (e) => {
    e.preventDefault()
    if (!nuevaObsTexto.trim()) return
    try {
      await api.post('/api/inventario/observaciones', {
        fecha_inventario: fecha,
        tipo: nuevaObsTipo,
        descripcion: nuevaObsTexto.trim(),
        usuario: auth.usuario?.email || '',
      })
      setNuevaObsTexto('')
      cargarObservaciones()
    } catch (er) { alert('Error: ' + er.message) }
  }
  const eliminarObservacion = async (id) => {
    try {
      await api.delete(`/api/inventario/observaciones/${id}`)
      cargarObservaciones()
    } catch (er) { alert('Error: ' + er.message) }
  }

  if (!fecha) return null

  return (
    <>
      <div className="ges-subtabs">
        <button className={`ges-subtab ${subtab === 'dashboard' ? 'active' : ''}`}
                onClick={() => setSubtab('dashboard')}>
          <span className="material-icons" style={{ fontSize: 14 }}>dashboard</span> Dashboard
        </button>
        <button className={`ges-subtab ${subtab === 'auditoria' ? 'active' : ''}`}
                onClick={() => setSubtab('auditoria')}>
          <span className="material-icons" style={{ fontSize: 14 }}>fact_check</span> Auditoría OPs
        </button>
      </div>

      {subtab === 'dashboard' && (
        <div className="ges-scroll-container">
          {calculando && (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)' }}>
              Calculando dashboard inicial…
            </div>
          )}

          {!calculando && dash && (
            <div className="ges-dashboard">
              {/* KPIs */}
              <div className="ges-kpis">
                <div className="ges-kpi">
                  <div className="ges-kpi-label">Valor Teórico</div>
                  <div className="ges-kpi-value">${fmtMoney(dash.valor_teorico)}</div>
                </div>
                <div className="ges-kpi">
                  <div className="ges-kpi-label">Valor Físico</div>
                  <div className="ges-kpi-value">${fmtMoney(dash.valor_fisico)}</div>
                </div>
                <div className={`ges-kpi ges-kpi-impacto ${dash.impacto_total < 0 ? 'neg' : 'pos'}`}>
                  <div className="ges-kpi-label">Impacto</div>
                  <div className="ges-kpi-value">${fmtMoney(dash.impacto_total)}</div>
                </div>
                <div className="ges-kpi">
                  <div className="ges-kpi-label">Con diferencia</div>
                  <div className="ges-kpi-value">
                    {dash.con_diferencia} <small>/ {dash.total_articulos}</small>
                  </div>
                </div>
              </div>

              {/* Severidad */}
              <div className="ges-severidad-row">
                <div className={`ges-sev-card ges-sev-critica ${filtroSev === 'critica' ? 'sel' : ''}`}
                     onClick={() => setFiltroSev(filtroSev === 'critica' ? null : 'critica')}>
                  <span className="ges-sev-count">{dash.por_severidad?.critica?.count || 0}</span>
                  <span className="ges-sev-label">Críticas</span>
                </div>
                <div className={`ges-sev-card ges-sev-significativa ${filtroSev === 'significativa' ? 'sel' : ''}`}
                     onClick={() => setFiltroSev(filtroSev === 'significativa' ? null : 'significativa')}>
                  <span className="ges-sev-count">{dash.por_severidad?.significativa?.count || 0}</span>
                  <span className="ges-sev-label">Significativas</span>
                </div>
                <div className={`ges-sev-card ges-sev-menor ${filtroSev === 'menor' ? 'sel' : ''}`}
                     onClick={() => setFiltroSev(filtroSev === 'menor' ? null : 'menor')}>
                  <span className="ges-sev-count">{dash.por_severidad?.menor?.count || 0}</span>
                  <span className="ges-sev-label">Menores</span>
                </div>
              </div>

              {/* Filtros con labels */}
              <div className="inv-filters-row" style={{ marginTop: 12 }}>
                <span className="inv-bodegas-label">Severidad</span>
                <button className={`inv-pill ${!filtroSev ? 'active' : ''}`}
                        onClick={() => setFiltroSev(null)}>Todas</button>
                <button className={`inv-pill ges-pill-critica ${filtroSev === 'critica' ? 'active' : ''}`}
                        onClick={() => setFiltroSev(filtroSev === 'critica' ? null : 'critica')}>Críticas</button>
                <button className={`inv-pill ges-pill-significativa ${filtroSev === 'significativa' ? 'active' : ''}`}
                        onClick={() => setFiltroSev(filtroSev === 'significativa' ? null : 'significativa')}>Significativas</button>
                <button className={`inv-pill ges-pill-menor ${filtroSev === 'menor' ? 'active' : ''}`}
                        onClick={() => setFiltroSev(filtroSev === 'menor' ? null : 'menor')}>Menores</button>

                <span className="inv-separator" />

                <span className="inv-bodegas-label">Estado</span>
                <button className={`inv-pill ${!filtroEstado ? 'active' : ''}`}
                        onClick={() => setFiltroEstado(null)}>Todos</button>
                {[
                  { v: 'pendiente',       l: 'Pendientes' },
                  { v: 'analizado',       l: 'Analizados' },
                  { v: 'justificada',     l: 'Justificadas' },
                  { v: 'requiere_ajuste', l: 'Req. ajuste' },
                ].map(({ v, l }) => (
                  <button key={v} className={`inv-pill ${filtroEstado === v ? 'active' : ''}`}
                          onClick={() => setFiltroEstado(filtroEstado === v ? null : v)}>{l}</button>
                ))}
              </div>

              {/* Barra acciones */}
              <div className="ges-actions-bar">
                <button className="ges-action-btn" disabled={analizando} onClick={lanzarAnalisis}>
                  <span className={`material-icons ${analizando ? 'spin' : ''}`} style={{ fontSize: 15 }}>psychology</span>
                  {analizando ? `Analizando ${progAct.progreso}/${progAct.total}…` : 'Analizar inconsistencias'}
                </button>
                <span className="ges-accion-info">{articulos.length} artículos</span>
                <button className="ges-action-btn-sec" disabled>Expandir todos</button>
                <button className="ges-action-btn-sec" disabled>Colapsar todos</button>
                <button className="ges-action-btn" disabled={generandoInforme} onClick={descargarInforme} style={{ marginLeft: 'auto' }}>
                  <span className={`material-icons ${generandoInforme ? 'spin' : ''}`} style={{ fontSize: 15 }}>picture_as_pdf</span>
                  {generandoInforme ? 'Generando…' : 'Informe PDF'}
                </button>
                <button className="ges-action-btn ges-action-btn-ia" disabled={generandoIA} onClick={descargarAnalisisIA}>
                  <span className={`material-icons ${generandoIA ? 'spin' : ''}`} style={{ fontSize: 15 }}>psychology</span>
                  {generandoIA ? 'Analizando…' : 'Análisis IA'}
                </button>
              </div>

              {/* Observaciones */}
              <div className="ges-observaciones">
                <div className="ges-obs-header" onClick={() => setObsExpanded(v => !v)} style={{ cursor: 'pointer' }}>
                  <span className={`material-icons ges-chevron ${obsExpanded ? 'expandido' : ''}`}>chevron_right</span>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>Observaciones del inventario</span>
                  {observaciones.length > 0 && <span className="ges-subtab-badge">{observaciones.length}</span>}
                </div>
                {obsExpanded && (
                  <div className="ges-obs-body">
                    {observaciones.map(obs => (
                      <div key={obs.id} className="ges-obs-item">
                        <span className={`ges-obs-tipo obs-${obs.tipo}`}>
                          {TIPOS_OBS.find(t => t.val === obs.tipo)?.label || obs.tipo}
                        </span>
                        <span className="ges-obs-texto">{obs.descripcion}</span>
                        <span className="ges-obs-fecha">{obs.registrado_por} · {obs.created_at?.slice(0, 10)}</span>
                        <button className="ges-obs-del" onClick={(e) => { e.stopPropagation(); eliminarObservacion(obs.id) }} title="Eliminar">
                          <span className="material-icons" style={{ fontSize: 12 }}>close</span>
                        </button>
                      </div>
                    ))}
                    {!observaciones.length && (
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', padding: '6px 0' }}>Sin observaciones</div>
                    )}
                    <form className="ges-obs-form" onSubmit={agregarObservacion}>
                      <select value={nuevaObsTipo} onChange={e => setNuevaObsTipo(e.target.value)} className="ges-obs-select">
                        {TIPOS_OBS.map(t => <option key={t.val} value={t.val}>{t.label}</option>)}
                      </select>
                      <input value={nuevaObsTexto} onChange={e => setNuevaObsTexto(e.target.value)}
                             className="ges-obs-input" placeholder="Escribir observación..." />
                      <button type="submit" className="ges-obs-add" disabled={!nuevaObsTexto.trim()}>
                        <span className="material-icons" style={{ fontSize: 14 }}>add</span>
                      </button>
                    </form>
                  </div>
                )}
              </div>

              {/* Tabla artículos con diferencia */}
              <div className="inv-table-wrap" style={{ marginTop: 8 }}>
                <table className="inv-table">
                  <thead>
                    <tr>
                      <th>Cód</th>
                      <th>Artículo</th>
                      <th>Grupo</th>
                      <th style={{ textAlign: 'right' }}>Teórico</th>
                      <th style={{ textAlign: 'right' }}>Físico</th>
                      <th style={{ textAlign: 'right' }}>Dif.</th>
                      <th style={{ textAlign: 'right' }}>Impacto</th>
                      <th>Severidad</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {articulos.map(a => (
                      <tr key={a.id}>
                        <td>{a.id_effi}</td>
                        <td>{a.nombre}</td>
                        <td><span className="grupo-chip">{a.grupo || '—'}</span></td>
                        <td style={{ textAlign: 'right' }}>{a.inventario_teorico ?? '—'}</td>
                        <td style={{ textAlign: 'right' }}>{a.inventario_fisico ?? '—'}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>
                          {a.diferencia != null ? (a.diferencia > 0 ? '+' : '') + Math.round(a.diferencia) : '—'}
                        </td>
                        <td style={{ textAlign: 'right', color: a.impacto < 0 ? 'var(--color-error)' : 'var(--accent)' }}>
                          ${fmtMoney(a.impacto)}
                        </td>
                        <td><span className={`ges-pill-${a.severidad || 'menor'}`}>{a.severidad || '—'}</span></td>
                        <td><span className="estado-chip">{a.estado || 'pendiente'}</span></td>
                      </tr>
                    ))}
                    {!articulos.length && (
                      <tr><td colSpan={9} style={{ textAlign: 'center', padding: 20, color: 'var(--text-tertiary)' }}>
                        Sin artículos con los filtros aplicados
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!cargando && !calculando && !dash && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
              Sin datos de gestión todavía. Calculá el inventario teórico desde el aside.
            </div>
          )}
        </div>
      )}

      {subtab === 'auditoria' && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
          <span className="material-icons" style={{ fontSize: 32, marginBottom: 8, display: 'block' }}>fact_check</span>
          Auditoría OPs — pendiente de migrar (modal de detalle por OP, marcar revisadas)
        </div>
      )}
    </>
  )
}
