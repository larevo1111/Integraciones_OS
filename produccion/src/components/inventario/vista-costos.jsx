/**
 * VistaCostos — Tab "Costos" del inventario.
 * Tabla con valorización: costo_manual, cantidades, valores teórico/físico, impacto.
 *
 * GET /api/inventario/costos?fecha=
 */
import { useEffect, useState, useMemo } from "react"
import { api } from "@/lib/api"

const fmtNum = (n) => n == null ? '—' : (Math.round(n * 100) / 100).toLocaleString('es-CO')
const fmtMoney = (n) => n == null ? '$0' : '$' + Math.round(n).toLocaleString('es-CO')

export function VistaCostos({ fecha }) {
  const [rows, setRows] = useState([])
  const [cargando, setCargando] = useState(false)
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    if (!fecha) return
    setCargando(true)
    api.get(`/api/inventario/costos?fecha=${fecha}`)
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(e => { console.error(e); setRows([]) })
      .finally(() => setCargando(false))
  }, [fecha])

  const filtradas = useMemo(() => {
    if (!busqueda.trim()) return rows
    const q = busqueda.trim().toLowerCase()
    return rows.filter(r => (r.nombre || '').toLowerCase().includes(q) || (r.id_effi || '').toLowerCase().includes(q))
  }, [rows, busqueda])

  const totales = useMemo(() => {
    return filtradas.reduce((acc, r) => ({
      val_teorico: acc.val_teorico + (Number(r.valor_teorico) || 0),
      val_fisico:  acc.val_fisico  + (Number(r.valor_fisico)  || 0),
      impacto:     acc.impacto     + (Number(r.impacto)       || 0),
    }), { val_teorico: 0, val_fisico: 0, impacto: 0 })
  }, [filtradas])

  if (!fecha) return null

  return (
    <div className="costos-container">
      <div className="inv-toolbar" style={{ marginTop: 8 }}>
        <div className="inv-search-box">
          <span className="material-icons inv-search-icon">search</span>
          <input value={busqueda} onChange={e => setBusqueda(e.target.value)}
                 className="inv-search-input" type="text"
                 placeholder="Filtrar por nombre o código..." />
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: 12, alignItems: 'center' }}>
          <span><strong style={{ color: 'var(--text-tertiary)' }}>Val. Teórico:</strong> {fmtMoney(totales.val_teorico)}</span>
          <span><strong style={{ color: 'var(--text-tertiary)' }}>Val. Físico:</strong> {fmtMoney(totales.val_fisico)}</span>
          <span style={{ color: totales.impacto < 0 ? 'var(--color-error)' : 'var(--accent)' }}>
            <strong>Impacto:</strong> {fmtMoney(totales.impacto)}
          </span>
        </div>
      </div>

      {cargando && <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)' }}>Cargando…</div>}

      {!cargando && (
        <div className="inv-table-wrap" style={{ marginTop: 8 }}>
          <table className="inv-table">
            <thead>
              <tr>
                <th>Cód</th>
                <th>Artículo</th>
                <th>Categoría</th>
                <th>Tipo</th>
                <th style={{ textAlign: 'right' }}>Costo Unit.</th>
                <th style={{ textAlign: 'right' }}>Teórico</th>
                <th style={{ textAlign: 'right' }}>Físico</th>
                <th style={{ textAlign: 'right' }}>Dif.</th>
                <th style={{ textAlign: 'right' }}>Val. Teórico</th>
                <th style={{ textAlign: 'right' }}>Val. Físico</th>
                <th style={{ textAlign: 'right' }}>Impacto</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map(r => (
                <tr key={r.id}>
                  <td>{r.id_effi}</td>
                  <td>{r.nombre}</td>
                  <td>{r.categoria || '—'}</td>
                  <td><span className="grupo-chip">{r.grupo || '—'}</span></td>
                  <td style={{ textAlign: 'right' }}>{fmtMoney(r.costo_manual)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNum(r.teorico)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNum(r.fisico)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600 }}>
                    {r.diferencia != null ? (r.diferencia > 0 ? '+' : '') + fmtNum(r.diferencia) : '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>{fmtMoney(r.valor_teorico)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoney(r.valor_fisico)}</td>
                  <td style={{ textAlign: 'right', color: (r.impacto || 0) < 0 ? 'var(--color-error)' : 'var(--accent)' }}>
                    {fmtMoney(r.impacto)}
                  </td>
                </tr>
              ))}
              {!filtradas.length && (
                <tr><td colSpan={11} style={{ textAlign: 'center', padding: 20, color: 'var(--text-tertiary)' }}>
                  Sin datos
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
