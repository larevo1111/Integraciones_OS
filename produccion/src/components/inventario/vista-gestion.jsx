/**
 * VistaGestion — Tab "Gestión" del inventario.
 * Sub-tabs: Dashboard (KPIs + lista artículos por diferencia), Auditoría OPs (placeholder).
 *
 * Endpoints:
 *  - GET  /api/inventario/gestion/dashboard?fecha=
 *  - POST /api/inventario/gestion/calcular  (si dashboard.vacio)
 *  - GET  /api/inventario/gestion?fecha=&severidad=&estado=&grupo=
 */
import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const fmtMoney = (n) => {
  if (n == null || isNaN(n)) return '0'
  return Math.round(n).toLocaleString('es-CO')
}

export function VistaGestion({ fecha }) {
  const [subtab, setSubtab] = useState('dashboard')
  const [dash, setDash] = useState(null)
  const [articulos, setArticulos] = useState([])
  const [filtroSev, setFiltroSev] = useState(null)
  const [filtroEstado, setFiltroEstado] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [calculando, setCalculando] = useState(false)

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

  useEffect(() => { cargarDashboard() }, [fecha])
  useEffect(() => { cargarArticulos() }, [fecha, filtroSev, filtroEstado])

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

              {/* Filtros estado */}
              <div className="inv-filters-row" style={{ marginTop: 12 }}>
                <button className={`inv-pill ${!filtroEstado ? 'active' : ''}`}
                        onClick={() => setFiltroEstado(null)}>Todos</button>
                {['pendiente', 'analizado', 'justificada', 'requiere_ajuste'].map(e => (
                  <button key={e} className={`inv-pill ${filtroEstado === e ? 'active' : ''}`}
                          onClick={() => setFiltroEstado(filtroEstado === e ? null : e)}>
                    {e === 'pendiente' ? 'Pendientes'
                      : e === 'analizado' ? 'Analizados'
                      : e === 'justificada' ? 'Justificadas' : 'Req. ajuste'}
                  </button>
                ))}
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
