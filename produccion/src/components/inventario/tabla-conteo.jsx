/**
 * TablaConteo — usa OsDataTable para tener filtros/orden estándar.
 * Diseño compacto:
 *   - Móvil: 3 columnas visibles → Status + ID + Artículo (con chips: cat, unidad, teórico) + Conteo
 *   - Desktop: 4 columnas → Status + ID + Artículo + Categoría (chip aparte) + Conteo
 *   - Columnas Teórico/Físico/Diferencia existen para filtrar/ordenar pero ocultas por defecto
 */
import { useState } from "react"
import { OsDataTable } from "@/components/os-data-table"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

const GRUPO_NOMBRES = { MP: 'Materia Prima', PP: 'Producto en Proceso', PT: 'Producto Terminado', INS: 'Insumos', DS: 'Desarrollo', DES: 'Desperdicio', NM: 'No Matriculado' }
// Códigos cortos para mobile (idénticos a la convención interna del proyecto)
const GRUPO_CORTOS  = { MP: 'MP', PP: 'PP', PT: 'PT', INS: 'INS', DS: 'DS', DES: 'DES', NM: 'NM' }

const fmtNum = (n) => n != null ? Math.round(n) : '—'
const grupoNombre = (g) => GRUPO_NOMBRES[g] || g || ''
const grupoCorto  = (g) => GRUPO_CORTOS[g]  || g || ''
const parseDecimal = (s) => (s == null || s === '') ? NaN : parseFloat(String(s).replace(',', '.'))
const displayConteo = (a) => a.inventario_fisico != null ? a.inventario_fisico : ''

const claseFila = (a) => a.estado === 'contado' ? (a.diferencia === 0 ? 'row-ok' : 'row-diff') : ''
const claseDot  = (a) => {
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

export function TablaConteo({ articulos, cargando, conteoBloqueado, onChange, onAccionFila }) {
  const [menuAbierto, setMenuAbierto] = useState(null)
  const [localState, setLocalState] = useState({}) // { [id]: { fisico, estado, diferencia } }

  const handleAccion = (accion, art) => {
    setMenuAbierto(null)
    onAccionFila?.(accion, art)
  }

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
    guardarConteo(a, Math.max(0, actual + delta))
  }

  const onConteoBlur = (a, e) => {
    const valor = parseDecimal(e.target.value)
    if (isNaN(valor)) { e.target.value = displayConteo(a); return }
    guardarConteo(a, valor)
  }

  // Columnas:
  //   - Visibles por defecto: status, id, nombre, grupo, conteo
  //   - Ocultas por defecto (filtrables vía "Campos"): teorico, fisico, diferencia
  //   - Categoría se oculta en mobile via CSS (los chips ya están dentro de Artículo)
  const columns = [
    { key: 'status',    label: '',          visible: true, nowrap: true },
    { key: 'id_effi',   label: 'ID',        visible: true, nowrap: true },
    { key: 'nombre',    label: 'Artículo',  visible: true },
    { key: 'grupo',     label: 'Categoría', labelMobile: 'Cat', visible: true, nowrap: true,
      options: Object.keys(GRUPO_NOMBRES).map(g => ({ value: g, label: grupoNombre(g) })) },
    { key: 'inventario_teorico', label: 'Teórico',    labelMobile: 'Teo', visible: false, numeric: true, nowrap: true },
    { key: 'inventario_fisico',  label: 'Físico',     labelMobile: 'Fís', visible: false, numeric: true, nowrap: true },
    { key: 'diferencia',         label: 'Diferencia', labelMobile: 'Dif', visible: false, numeric: true, nowrap: true },
    { key: 'conteo',    label: 'Conteo',    labelMobile: 'Cnt', visible: true, nowrap: true },
  ]

  const renderCell = (a, col) => {
    if (col.key === 'status') {
      return <span className={`status-dot ${claseDot(a)}`} />
    }
    if (col.key === 'id_effi') {
      return <span className="text-[11px] text-muted-foreground font-mono">{a.id_effi}</span>
    }
    if (col.key === 'nombre') {
      return (
        <div className="min-w-0">
          <div className="articulo-line1">
            <span className="articulo-nombre">{a.nombre}</span>
            {a.unidad && <span className="unit-tag">{a.unidad}</span>}
          </div>
          {/* Chip TEO solo en mobile (categoría va en su propia columna) */}
          <div className="articulo-meta-movil sm:hidden">
            <span className="chip-teo">TEO {fmtNum(a.inventario_teorico)}</span>
          </div>
        </div>
      )
    }
    if (col.key === 'grupo') {
      return (
        <span title={grupoNombre(a.grupo)}>
          <span className={`grupo-tag grupo-tag-full grupo-${(a.grupo || 'mp').toLowerCase()}`}>{grupoNombre(a.grupo)}</span>
          <span className={`grupo-tag grupo-tag-short grupo-${(a.grupo || 'mp').toLowerCase()}`}>{grupoCorto(a.grupo)}</span>
        </span>
      )
    }
    if (col.key === 'inventario_teorico' || col.key === 'inventario_fisico') {
      const v = a[col.key]
      return v == null ? <span className="text-muted-foreground">—</span> : fmtNum(v)
    }
    if (col.key === 'diferencia') {
      return <span className={`diff-badge ${claseBadge(a)}`}>{textoBadge(a)}</span>
    }
    if (col.key === 'conteo') {
      return (
        <div className="conteo-cell" onClick={e => e.stopPropagation()}>
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
          <div className="conteo-cell-meta">
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
      )
    }
    return undefined
  }

  return (
    <OsDataTable
      rows={filas}
      columns={columns}
      loading={cargando}
      renderCell={renderCell}
      rowClassName={claseFila}
      rowIdKey="id"
    />
  )
}
