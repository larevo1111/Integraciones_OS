import { useState, useMemo, useEffect, useRef, useCallback } from "react"
import { createPortal } from "react-dom"
import {
  SlidersHorizontal, Download, X, Filter, ChevronUp, ChevronDown,
  FileText, Table as TableIcon, FileIcon, Inbox,
} from "lucide-react"
import { cn } from "@/lib/utils"

const AGG_OPTIONS = [
  { value: 'sum', label: 'Suma',     icon: 'Σ' },
  { value: 'avg', label: 'Promedio', icon: 'x̄' },
  { value: 'max', label: 'Máximo',   icon: '↑' },
  { value: 'min', label: 'Mínimo',   icon: '↓' },
]

const OP_LABELS = {
  eq: 'Igual a', contains: 'Contiene',
  gt: 'Mayor que', lt: 'Menor que',
  gte: 'Mayor o igual', lte: 'Menor o igual',
  between: 'Entre',
}

export function OsDataTable({
  rows = [],
  columns = [],
  loading = false,
  title = '',
  onRowClick,
  renderCell,  // función: (row, col, value) => ReactNode | null (null = usar default)
}) {
  const [localColumns, setLocalColumns] = useState([])
  useEffect(() => { setLocalColumns(columns.map(c => ({ ...c }))) }, [columns])

  const visibleColumns = useMemo(() => localColumns.filter(c => c.visible !== false), [localColumns])

  // Toolbar popups
  const [showFields, setShowFields] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const toolbarRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (!toolbarRef.current?.contains(e.target)) {
        setShowFields(false)
        setShowExport(false)
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [])

  // Column popup
  const [colPopup, setColPopup] = useState(null)
  const [colPopupStyle, setColPopupStyle] = useState({})
  const inputRef = useRef(null)

  const openColPopup = (key, event) => {
    if (colPopup === key) { setColPopup(null); return }
    const rect = event.currentTarget.getBoundingClientRect()
    setColPopupStyle({ top: (rect.bottom + 4) + 'px', left: Math.max(4, rect.left) + 'px' })
    setColPopup(key)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  // Column filters
  const [columnFilters, setColumnFilters] = useState({})
  const getFilterOp = (k) => columnFilters[k]?.op || 'eq'
  const getFilterVal = (k) => columnFilters[k]?.val || ''
  const getFilterVal2 = (k) => columnFilters[k]?.val2 || ''

  const setFilter = (k, patch) => {
    setColumnFilters(prev => ({
      ...prev,
      [k]: { op: 'eq', val: '', val2: '', selected: [], ...prev[k], ...patch },
    }))
  }

  const getColumnOptions = (k) => {
    const col = localColumns.find(c => c.key === k)
    if (!col?.options) return []
    return col.options.map(o => typeof o === 'string' ? { value: o, label: o } : o)
  }

  const isOptionSelected = (k, v) => (columnFilters[k]?.selected || []).includes(v)
  const toggleOption = (k, v) => {
    const selected = [...(columnFilters[k]?.selected || [])]
    const idx = selected.indexOf(v)
    if (idx === -1) selected.push(v); else selected.splice(idx, 1)
    setFilter(k, { selected })
  }

  const hasFilter = (k) => {
    const f = columnFilters[k]
    if (!f) return false
    if ((f.selected || []).length > 0) return true
    return (f.val || '').trim() !== ''
  }

  const activeFilterCount = useMemo(
    () => Object.keys(columnFilters).filter(k => hasFilter(k)).length,
    [columnFilters]
  )

  const clearAllFilters = () => setColumnFilters({})

  // Sort
  const [sortKey, setSortKey] = useState('')
  const [sortDir, setSortDir] = useState('asc')
  const setSort = (k, dir) => {
    if (sortKey === k && sortDir === dir) setSortKey('')
    else { setSortKey(k); setSortDir(dir) }
  }

  // Aggregates
  const [columnAggregates, setColumnAggregates] = useState({})
  const toggleAggregate = (k, type) => {
    setColumnAggregates(prev => {
      if (prev[k] === type) { const c = { ...prev }; delete c[k]; return c }
      return { ...prev, [k]: type }
    })
  }
  const activeAggregateCount = Object.keys(columnAggregates).length
  const hasAggregates = activeAggregateCount > 0

  // Filtered rows
  const filteredRows = useMemo(() => {
    const keys = Object.keys(columnFilters).filter(k => hasFilter(k))
    if (keys.length === 0) return rows
    return rows.filter(row => keys.every(k => {
      const f = columnFilters[k]
      if ((f.selected || []).length > 0) return f.selected.includes(row[k])
      const fv = (f.val || '').trim()
      if (!fv) return true
      const raw = row[k]
      const rawNum = parseFloat(String(raw).replace(',', '.'))
      const fNum = parseFloat(fv)
      const val = String(raw ?? '').toLowerCase()
      switch (f.op) {
        case 'eq': return val === fv.toLowerCase()
        case 'contains': return val.includes(fv.toLowerCase())
        case 'gt': return !isNaN(fNum) && !isNaN(rawNum) && rawNum > fNum
        case 'lt': return !isNaN(fNum) && !isNaN(rawNum) && rawNum < fNum
        case 'gte': return !isNaN(fNum) && !isNaN(rawNum) && rawNum >= fNum
        case 'lte': return !isNaN(fNum) && !isNaN(rawNum) && rawNum <= fNum
        case 'between': {
          const fv2 = f.val2?.trim(); const fNum2 = parseFloat(fv2)
          if (isNaN(rawNum) || isNaN(fNum)) return false
          if (!fv2 || isNaN(fNum2)) return rawNum >= fNum
          return rawNum >= fNum && rawNum <= fNum2
        }
        default: return val.includes(fv.toLowerCase())
      }
    }))
  }, [rows, columnFilters])

  // Sorted rows
  const sortedRows = useMemo(() => {
    if (!sortKey) return filteredRows
    return [...filteredRows].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey]
      const n = v => parseFloat(String(v).replace(',', '.'))
      const r = isNaN(n(av)) ? String(av ?? '').localeCompare(String(bv ?? '')) : n(av) - n(bv)
      return sortDir === 'asc' ? r : -r
    })
  }, [filteredRows, sortKey, sortDir])

  // Compute aggregate for a column
  const computeAggregate = (key, type) => {
    const vals = sortedRows.map(r => parseFloat(String(r[key]).replace(',', '.'))).filter(n => !isNaN(n))
    if (!vals.length) return null
    if (type === 'sum') return vals.reduce((a, b) => a + b, 0)
    if (type === 'avg') return vals.reduce((a, b) => a + b, 0) / vals.length
    if (type === 'max') return Math.max(...vals)
    if (type === 'min') return Math.min(...vals)
    return null
  }

  const aggLabel = (type) => ({ sum: 'Σ', avg: 'x̄', max: '↑', min: '↓' }[type] || '')

  // Numeric detection
  const isNumeric = (key) => {
    const col = localColumns.find(c => c.key === key)
    if (col?.numeric) return true
    if (key.includes('costo') || key.includes('valor') || key.includes('impacto') ||
        key.includes('cantidad') || key.includes('precio')) return true
    const sample = rows.slice(0, 5)
    if (!sample.length) return false
    return sample.every(r => {
      const v = r[key]
      if (v === null || v === undefined || v === '') return true
      const s = String(v).trim()
      return s !== '' && !isNaN(Number(s))
    })
  }

  // Format cell
  const fmtNum = (n) => {
    if (n === null || n === undefined || isNaN(n)) return '—'
    let decimals = 0
    const abs = Math.abs(n)
    if (abs - Math.floor(abs) > 0.0005) {
      const s = n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '')
      decimals = s.split('.')[1]?.length || 0
      if (decimals > 3) decimals = 3
    }
    return n.toLocaleString('de-DE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  const formatCell = (val, key) => {
    if (val === null || val === undefined) return '—'
    if (key.includes('_pct')) {
      const n = parseFloat(val); if (isNaN(n)) return val
      return fmtNum(n * 100) + '%'
    }
    if (key.includes('costo') || key.includes('valor') || key.includes('impacto') || key.includes('precio')) {
      const n = parseFloat(String(val).replace(',', '.'))
      if (!isNaN(n)) return '$' + fmtNum(n)
    }
    if (isNumeric(key)) {
      const n = parseFloat(String(val).replace(',', '.'))
      if (!isNaN(n)) return fmtNum(n)
    }
    return val
  }

  // Export
  const doExport = async (format) => {
    setShowExport(false)
    const cols = visibleColumns
    const data = sortedRows
    const name = title || 'export'

    if (format === 'csv') {
      const header = cols.map(c => `"${c.label}"`).join(',')
      const body = data.map(r => cols.map(c => `"${r[c.key] ?? ''}"`).join(',')).join('\n')
      const blob = new Blob(['﻿' + header + '\n' + body], { type: 'text/csv;charset=utf-8' })
      triggerDownload(blob, `${name}.csv`); return
    }
    if (format === 'xlsx') {
      const XLSX = await import('xlsx')
      const ws = XLSX.utils.aoa_to_sheet([
        cols.map(c => c.label),
        ...data.map(r => cols.map(c => r[c.key] ?? '')),
      ])
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Datos')
      XLSX.writeFile(wb, `${name}.xlsx`); return
    }
    if (format === 'pdf') {
      // PDF simple via window.print de la tabla actual
      alert('Para PDF usa "Imprimir" del navegador (Ctrl+P) o exporta a Excel y convierte.')
    }
  }

  const triggerDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  }

  const clearColumn = (key) => {
    setColumnFilters(prev => { const c = { ...prev }; delete c[key]; return c })
    setColumnAggregates(prev => { const c = { ...prev }; delete c[key]; return c })
    if (sortKey === key) setSortKey('')
    setColPopup(null)
  }

  const showAll = () => setLocalColumns(cols => cols.map(c => ({ ...c, visible: true })))
  const hideAll = () => setLocalColumns(cols => cols.map(c => ({ ...c, visible: false })))
  const toggleColVisible = (key) => setLocalColumns(cols => cols.map(c => c.key === key ? { ...c, visible: c.visible === false } : c))

  return (
    <div className="flex flex-col rounded-lg border bg-card overflow-visible relative">
      {/* TOOLBAR */}
      <div ref={toolbarRef} className="flex items-center justify-between h-11 px-3.5 border-b bg-secondary/20">
        <div className="flex items-center gap-2">
          {title && <span className="text-sm font-semibold">{title}</span>}
          {!loading && <span className="text-xs font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">{filteredRows.length}</span>}
          {activeFilterCount > 0 && (
            <button
              onClick={clearAllFilters}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary bg-primary/10 border border-primary/25 rounded-full px-2 py-0.5 cursor-pointer hover:bg-primary/20"
              title="Limpiar filtros"
            >
              <Filter className="h-2.5 w-2.5" />
              {activeFilterCount}
              <X className="h-2.5 w-2.5" />
            </button>
          )}
          {activeAggregateCount > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 rounded-full px-2 py-0.5">
              Σ {activeAggregateCount}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 relative">
          {/* Campos */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowFields(v => !v); setShowExport(false) }}
              className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md border border-border bg-transparent text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" /> Campos
            </button>
            {showFields && (
              <div onClick={e => e.stopPropagation()} className="absolute right-0 top-full mt-1.5 z-50 bg-card border border-border rounded-lg shadow-xl min-w-[280px] py-2">
                <div className="px-3.5 pt-1 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Propiedades visibles</div>
                <div className="flex flex-wrap gap-1.5 px-3 pb-2">
                  {localColumns.map(col => (
                    <button
                      key={col.key}
                      onClick={() => toggleColVisible(col.key)}
                      className={cn(
                        "h-6 px-2.5 rounded-full border text-xs transition-colors cursor-pointer",
                        col.visible !== false
                          ? "bg-primary/10 border-primary/30 text-primary font-medium"
                          : "border-border text-muted-foreground hover:text-foreground"
                      )}
                    >{col.label}</button>
                  ))}
                </div>
                <div className="border-t border-border pt-1.5 px-2 flex gap-1">
                  <button onClick={showAll} className="h-6 px-2 rounded text-xs text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer">Mostrar todos</button>
                  <button onClick={hideAll} className="h-6 px-2 rounded text-xs text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer">Ocultar todos</button>
                </div>
              </div>
            )}
          </div>

          {/* Exportar */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowExport(v => !v); setShowFields(false) }}
              className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md border border-border bg-transparent text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer"
            >
              <Download className="h-3.5 w-3.5" /> Exportar
            </button>
            {showExport && (
              <div onClick={e => e.stopPropagation()} className="absolute right-0 top-full mt-1.5 z-50 bg-card border border-border rounded-lg shadow-xl min-w-[220px] py-2">
                <div className="px-3.5 pt-1 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Exportar como</div>
                <div className="px-1.5 pb-1 flex flex-col gap-0.5">
                  <ExportRow icon={FileText} label="CSV" desc="Separado por comas" onClick={() => doExport('csv')} />
                  <ExportRow icon={TableIcon} label="Excel" desc="Archivo .xlsx" onClick={() => doExport('xlsx')} />
                  <ExportRow icon={FileIcon} label="PDF" desc="Documento PDF" onClick={() => doExport('pdf')} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* TABLA */}
      <div className="overflow-auto max-h-[calc(100vh-260px)]">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {visibleColumns.map(col => (
                <th
                  key={col.key}
                  onClick={(e) => openColPopup(col.key, e)}
                  className={cn(
                    "text-left px-3 h-9 text-[11px] font-semibold uppercase tracking-wider bg-background border-b border-border cursor-pointer select-none whitespace-nowrap sticky top-0 z-10 transition-colors",
                    hasFilter(col.key) ? "text-primary" : "text-muted-foreground",
                    sortKey === col.key && "text-foreground",
                    columnAggregates[col.key] && "border-b-emerald-500",
                    colPopup === col.key && "bg-primary/10 text-primary",
                    "hover:text-foreground"
                  )}
                >
                  <div className="flex items-center gap-1">
                    <span className="flex-1">{col.label}</span>
                    {sortKey === col.key && (
                      sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                    {hasFilter(col.key) && <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(8)].map((_, i) => (
                <tr key={i}><td colSpan={visibleColumns.length} className="p-3"><div className="h-3.5 rounded bg-muted/50 animate-pulse" /></td></tr>
              ))
            ) : (
              <>
                {hasAggregates && sortedRows.length > 0 && (
                  <tr className="bg-emerald-500/5 sticky z-[5]" style={{ top: '36px' }}>
                    {visibleColumns.map(col => (
                      <td key={col.key} className="px-3 py-2 font-semibold border-b-2 border-emerald-500/25 bg-emerald-500/5">
                        {columnAggregates[col.key] && (
                          <>
                            <span className="text-[10px] text-emerald-400 font-bold mr-1">{aggLabel(columnAggregates[col.key])}</span>
                            <span className="text-sm">{formatCell(computeAggregate(col.key, columnAggregates[col.key]), col.key)}</span>
                          </>
                        )}
                      </td>
                    ))}
                  </tr>
                )}
                {sortedRows.length === 0 ? (
                  <tr><td colSpan={visibleColumns.length} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground text-sm">
                      <Inbox className="h-6 w-6" /> Sin resultados
                    </div>
                  </td></tr>
                ) : sortedRows.map((row, idx) => (
                  <tr
                    key={row.id ?? idx}
                    onClick={() => onRowClick?.(row)}
                    className={cn("border-b border-border/40 hover:bg-accent/30 transition-colors group", onRowClick && "cursor-pointer")}
                  >
                    {visibleColumns.map(col => {
                      const value = row[col.key]
                      const custom = renderCell?.(row, col, value)
                      return (
                        <td key={col.key} className={cn("px-3 py-2 align-middle", col.nowrap && "whitespace-nowrap")}>
                          {custom !== undefined && custom !== null ? custom : formatCell(value, col.key)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>

      {/* FOOTER */}
      {!loading && sortedRows.length > 0 && (
        <div className="px-3.5 py-2 text-xs text-muted-foreground border-t">
          {sortedRows.length} filas
          {activeFilterCount > 0 && <span> · {rows.length - sortedRows.length} filtradas</span>}
        </div>
      )}

      {/* COL POPUP */}
      {colPopup && createPortal(
        <div className="fixed inset-0 z-[9999]" onClick={() => setColPopup(null)}>
          <div
            className="fixed min-w-[220px] max-w-[300px] bg-card border border-border rounded-lg shadow-2xl py-2"
            style={colPopupStyle}
            onClick={e => e.stopPropagation()}
          >
            {/* Filtrar */}
            <div className="px-3 py-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">Filtrar</label>
              {getColumnOptions(colPopup).length > 0 ? (
                <div className="flex flex-col gap-0.5 max-h-56 overflow-y-auto py-1">
                  {getColumnOptions(colPopup).map(opt => (
                    <label key={opt.value} className="flex items-center gap-2 px-1 py-1 rounded text-xs cursor-pointer hover:bg-accent">
                      <input
                        type="checkbox"
                        checked={isOptionSelected(colPopup, opt.value)}
                        onChange={() => toggleOption(colPopup, opt.value)}
                        className="cursor-pointer accent-primary"
                      />
                      {opt.color && <span className="w-2 h-2 rounded-full" style={{ background: opt.color }} />}
                      {opt.label}
                    </label>
                  ))}
                </div>
              ) : (
                <>
                  <select
                    value={getFilterOp(colPopup)}
                    onChange={e => setFilter(colPopup, { op: e.target.value })}
                    className="w-full h-7 rounded border border-border bg-input text-xs px-2 mb-1.5 cursor-pointer"
                  >
                    {Object.entries(OP_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                  <div className="flex flex-col gap-1">
                    <input
                      ref={inputRef}
                      value={getFilterVal(colPopup)}
                      onChange={e => setFilter(colPopup, { val: e.target.value })}
                      onKeyDown={e => { if (e.key === 'Enter' || e.key === 'Escape') setColPopup(null) }}
                      placeholder={getFilterOp(colPopup) === 'between' ? 'Desde' : 'Valor'}
                      className="w-full h-7 rounded border border-border bg-input text-xs px-2 outline-none focus:border-primary"
                    />
                    {getFilterOp(colPopup) === 'between' && (
                      <input
                        value={getFilterVal2(colPopup)}
                        onChange={e => setFilter(colPopup, { val2: e.target.value })}
                        placeholder="Hasta"
                        className="w-full h-7 rounded border border-border bg-input text-xs px-2 outline-none focus:border-primary"
                      />
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Ordenar */}
            <div className="px-3 py-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">Ordenar</label>
              <div className="flex gap-1">
                <SortBtn active={sortKey === colPopup && sortDir === 'asc'} onClick={() => setSort(colPopup, 'asc')}>
                  <ChevronUp className="h-3 w-3" /> Ascendente
                </SortBtn>
                <SortBtn active={sortKey === colPopup && sortDir === 'desc'} onClick={() => setSort(colPopup, 'desc')}>
                  <ChevronDown className="h-3 w-3" /> Descendente
                </SortBtn>
              </div>
            </div>

            {/* Subtotal */}
            {isNumeric(colPopup) && (
              <>
                <div className="h-px bg-border my-1" />
                <div className="px-3 py-1">
                  <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">Subtotal</label>
                  <div className="flex gap-1 flex-wrap">
                    {AGG_OPTIONS.map(agg => (
                      <button
                        key={agg.value}
                        onClick={() => toggleAggregate(colPopup, agg.value)}
                        className={cn(
                          "inline-flex items-center gap-1 h-6 px-2 rounded text-xs transition-colors cursor-pointer",
                          columnAggregates[colPopup] === agg.value
                            ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                            : "border border-border text-muted-foreground hover:text-foreground"
                        )}
                      >
                        <span>{agg.icon}</span> {agg.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {(hasFilter(colPopup) || columnAggregates[colPopup] || sortKey === colPopup) && (
              <div className="border-t border-border pt-1.5 px-2 mt-1">
                <button
                  onClick={() => clearColumn(colPopup)}
                  className="w-full h-7 rounded text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
                >
                  Limpiar todo
                </button>
              </div>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}

function ExportRow({ icon: Icon, label, desc, onClick }) {
  return (
    <button onClick={onClick} className="flex items-center gap-2.5 px-2.5 py-2 rounded hover:bg-accent cursor-pointer w-full text-left">
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="text-sm text-foreground font-medium flex-1">{label}</span>
      <span className="text-[11px] text-muted-foreground whitespace-nowrap">{desc}</span>
    </button>
  )
}

function SortBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex-1 inline-flex items-center gap-1 h-7 px-2 rounded text-xs justify-center transition-colors cursor-pointer",
        active
          ? "bg-primary/10 border border-primary/30 text-primary"
          : "border border-border text-muted-foreground hover:text-foreground"
      )}
    >{children}</button>
  )
}
