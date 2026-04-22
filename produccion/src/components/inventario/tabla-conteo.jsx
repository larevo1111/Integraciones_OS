/**
 * TablaConteo — clon EXACTO de la tabla del Vue (líneas ~315-440 de App.vue).
 * NO usa OsDataTable estándar — esta tabla es especial (inputs editables inline,
 * resaltado por diferencia, menu por fila).
 */
import { useState, useRef } from "react"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const GRUPO_NOMBRES = { MP: 'Materia Prima', PP: 'Producto en Proceso', PT: 'Producto Terminado', INS: 'Insumos', DS: 'Desarrollo', DES: 'Desperdicio', NM: 'No Matriculado' }
const GRUPO_CORTOS  = { MP: 'M.Prima', PP: 'Proceso', PT: 'P.Term', INS: 'Insumo', DS: 'Desarr', DES: 'Desper', NM: 'NoMatr' }

const fmtNum = (n) => n != null ? Math.round(n) : '—'
const grupoNombre = (g) => GRUPO_NOMBRES[g] || g || ''
const grupoCorto  = (g) => GRUPO_CORTOS[g]  || g || ''
const parseDecimal = (s) => (s == null || s === '') ? NaN : parseFloat(String(s).replace(',', '.'))
const displayConteo = (a) => a.inventario_fisico != null ? a.inventario_fisico : ''

const clasesFila = (a) => a.estado === 'contado' ? (a.diferencia === 0 ? 'row-ok' : 'row-diff') : ''
const claseDot   = (a) => {
  if (a.estado === 'pendiente') return 'dot-pending'
  if (a.diferencia === 0) return 'dot-ok'
  return Math.abs(a.diferencia) >= 10 ? 'dot-critical' : 'dot-warning'
}
const claseInput = (a) => {
  if (a.inventario_fisico == null) return ''
  if (a.diferencia === 0) return 'input-ok'
  return Math.abs(a.diferencia) >= 10 ? 'input-critical' : 'input-warning'
}
const claseBadge = (a) => {
  if (a.estado === 'pendiente') return 'badge-empty'
  if (a.diferencia === 0) return 'badge-ok'
  return Math.abs(a.diferencia) >= 10 ? 'badge-error' : 'badge-warning'
}
const textoBadge = (a) => {
  if (a.estado === 'pendiente') return '—'
  if (a.diferencia === 0) return 'OK'
  return (a.diferencia > 0 ? '+' : '') + Math.round(a.diferencia)
}

const COLUMNS = [
  { key: 'id_effi',   label: 'ID' },
  { key: 'nombre',    label: 'Artículo' },
  { key: 'categoria', label: 'Categ' },
]

export function TablaConteo({ articulos, cargando, conteoBloqueado, onChange, onAccionFila }) {
  const [menuAbierto, setMenuAbierto] = useState(null)
  const [localState, setLocalState] = useState({}) // { [id]: { fisico, estado, diferencia } } overrides en memoria

  const handleAccion = (accion, art) => {
    setMenuAbierto(null)
    if (onAccionFila) onAccionFila(accion, art)
  }

  // Mezclar estado local con artículos para reflejar conteos sin esperar reload
  const filas = articulos.map(a => ({ ...a, ...(localState[a.id] || {}) }))

  const guardarConteo = async (a, valor) => {
    setLocalState(s => ({ ...s, [a.id]: { inventario_fisico: valor, estado: 'contado', diferencia: a.diferencia } }))
    try {
      const data = await api.put?.(`/api/inventario/articulos/${a.id}/conteo`,
        { inventario_fisico: valor, contado_por: auth.usuario?.email || '' })
        || (await fetch(`/api/inventario/articulos/${a.id}/conteo`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${auth.token}` },
          body: JSON.stringify({ inventario_fisico: valor, contado_por: auth.usuario?.email || '' })
        })).then(r => r.json())
      setLocalState(s => ({ ...s, [a.id]: { inventario_fisico: valor, estado: 'contado', diferencia: data.diferencia } }))
      onChange?.()
    } catch (e) {
      setLocalState(s => { const c = { ...s }; delete c[a.id]; return c })
      alert(`Error guardando conteo de ${a.nombre}: ${e.message}`)
    }
  }

  const ajustarConteo = (a, delta) => {
    const actual = a.inventario_fisico != null ? a.inventario_fisico : (a.inventario_teorico || 0)
    const nuevo = Math.max(0, actual + delta)
    guardarConteo(a, nuevo)
  }

  const onConteoBlur = (a, e) => {
    const valor = parseDecimal(e.target.value)
    if (isNaN(valor)) { e.target.value = displayConteo(a); return }
    guardarConteo(a, valor)
  }

  if (cargando) {
    return (
      <div className="inv-table-container">
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>Cargando…</div>
      </div>
    )
  }

  return (
    <div className="inv-table-container">
      <table className="inv-table">
        <colgroup>
          <col className="col-status" />
          <col className="col-id" />
          <col className="col-articulo" />
          <col className="col-categoria" />
          <col className="col-conteo" />
        </colgroup>
        <thead>
          <tr>
            <th className="th th-nosort"></th>
            {COLUMNS.map(col => (
              <th key={col.key} className="th">
                <div className="th-inner">
                  <span className="th-label">{col.label}</span>
                </div>
              </th>
            ))}
            <th className="th th-nosort th-conteo">Conteo</th>
          </tr>
        </thead>
        <tbody>
          {filas.length === 0 && (
            <tr><td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>
              Sin resultados. Prueba ajustar filtros o búsqueda.
            </td></tr>
          )}
          {filas.map(a => (
            <tr key={a.id} className={clasesFila(a)}>
              <td className="td td-center"><span className={`status-dot ${claseDot(a)}`} /></td>
              <td className="td cell-id">{a.id_effi}</td>
              <td className="td cell-articulo">
                <div className="articulo-line1">
                  <span className="articulo-nombre">{a.nombre}</span>
                  {a.unidad && <span className="unit-tag">{a.unidad}</span>}
                </div>
                <div className="articulo-teorico-movil">TEO {fmtNum(a.inventario_teorico)}</div>
              </td>
              <td className="td cell-categoria" title={grupoNombre(a.grupo)}>
                <span className={`grupo-tag grupo-tag-full grupo-${(a.grupo || 'mp').toLowerCase()}`}>{grupoNombre(a.grupo)}</span>
                <span className={`grupo-tag grupo-tag-short grupo-${(a.grupo || 'mp').toLowerCase()}`}>{grupoCorto(a.grupo)}</span>
              </td>
              <td className="td">
                <div className="conteo-cell">
                  <div className="teorico-block">
                    <span className="teorico-label">Teo</span>
                    <span className="teorico-value">{fmtNum(a.inventario_teorico)}</span>
                  </div>
                  <div className={`stepper ${conteoBloqueado ? 'stepper-bloqueado' : ''}`}>
                    <button className="stepper-btn stepper-down" disabled={conteoBloqueado}
                            onClick={() => ajustarConteo(a, -1)} tabIndex={-1}>
                      <span className="material-icons" style={{ fontSize: 12 }}>remove</span>
                    </button>
                    <input className={`count-input ${claseInput(a)}`} readOnly={conteoBloqueado}
                           type="text" inputMode="decimal" placeholder="—"
                           defaultValue={displayConteo(a)}
                           onBlur={(e) => onConteoBlur(a, e)}
                           onKeyUp={(e) => { if (e.key === 'Enter') e.target.blur() }} />
                    <button className="stepper-btn stepper-up" disabled={conteoBloqueado}
                            onClick={() => ajustarConteo(a, 1)} tabIndex={-1}>
                      <span className="material-icons" style={{ fontSize: 12 }}>add</span>
                    </button>
                  </div>
                  <div className="diff-col">
                    <span className={`diff-badge ${claseBadge(a)}`}>{textoBadge(a)}</span>
                    {a.contado_por && <span className="contador-chip">{a.contado_por.substring(0, 3).toUpperCase()}</span>}
                  </div>
                  <div className="action-menu-wrap" style={{ position: 'relative' }}>
                    <button className={`action-btn ${(a.notas || a.foto) ? 'has-note' : ''}`}
                            onClick={(e) => { e.stopPropagation(); setMenuAbierto(menuAbierto === a.id ? null : a.id) }}>
                      <span className="material-icons" style={{ fontSize: 16 }}>more_vert</span>
                    </button>
                    {menuAbierto === a.id && (
                      <div className="action-menu" onClick={e => e.stopPropagation()}>
                        <div className="action-menu-item" onClick={() => handleAccion('nota', a)}>
                          <span className="material-icons" style={{ fontSize: 14 }}>edit_note</span>
                          <span>{a.notas ? 'Editar nota' : 'Agregar nota'}</span>
                        </div>
                        <div className="action-menu-item" onClick={() => handleAccion('foto', a)}>
                          <span className="material-icons" style={{ fontSize: 14 }}>photo_camera</span>
                          <span>Tomar foto</span>
                        </div>
                        {a.foto && (
                          <div className="action-menu-item" onClick={() => handleAccion('ver-foto', a)}>
                            <span className="material-icons" style={{ fontSize: 14 }}>visibility</span>
                            <span>Ver foto</span>
                          </div>
                        )}
                        {a.id_effi?.startsWith('NM-') && (
                          <div className="action-menu-item" onClick={() => handleAccion('asignar', a)}>
                            <span className="material-icons" style={{ fontSize: 14 }}>link</span>
                            <span>Asignar a Effi</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
