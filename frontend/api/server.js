const express = require('express')
const cors    = require('cors')
const { query } = require('./db')
const ExcelJS = require('exceljs')
const PDFDocument = require('pdfkit')

const app = express()
app.use(cors())
app.use(express.json())

// ── HELPER: aplicar filtros WHERE ─────────────────────
function buildWhere(filters) {
  if (!filters || filters.length === 0) return { sql: '', params: [] }
  const parts = []
  const params = []
  for (const f of filters) {
    if (f.op === 'contains') {
      parts.push(`\`${f.field}\` LIKE ?`)
      params.push(`%${f.value}%`)
    } else if (f.op === 'eq') {
      parts.push(`\`${f.field}\` = ?`)
      params.push(f.value)
    } else if (f.op === 'gte') {
      parts.push(`\`${f.field}\` >= ?`)
      params.push(f.value)
    } else if (f.op === 'lte') {
      parts.push(`\`${f.field}\` <= ?`)
      params.push(f.value)
    } else if (f.op === 'mes') {
      // Filtro por mes sobre campo TEXT tipo 'YYYY-MM-DD HH:MM:SS'
      parts.push(`LEFT(\`${f.field}\`, 7) = ?`)
      params.push(f.value)
    }
  }
  return { sql: ' WHERE ' + parts.join(' AND '), params }
}

// ── HELPER: exportar ──────────────────────────────────
async function exportData(res, rows, fields, format, filename) {
  const columns = fields && fields.length > 0 ? fields : Object.keys(rows[0] || {})

  if (format === 'csv') {
    res.setHeader('Content-Type', 'text/csv')
    res.setHeader('Content-Disposition', `attachment; filename="${filename}.csv"`)
    const header = columns.join(',')
    const body = rows.map(r => columns.map(c => `"${r[c] ?? ''}"`).join(',')).join('\n')
    return res.send(header + '\n' + body)
  }

  if (format === 'xlsx') {
    const wb = new ExcelJS.Workbook()
    const ws = wb.addWorksheet('Datos')
    ws.addRow(columns)
    ws.getRow(1).font = { bold: true }
    rows.forEach(r => ws.addRow(columns.map(c => r[c] ?? '')))
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    res.setHeader('Content-Disposition', `attachment; filename="${filename}.xlsx"`)
    return wb.xlsx.write(res)
  }

  if (format === 'pdf') {
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `attachment; filename="${filename}.pdf"`)
    const doc = new PDFDocument({ margin: 30, size: 'A4', layout: 'landscape' })
    doc.pipe(res)
    doc.fontSize(14).text(filename, { underline: true }).moveDown(0.5)
    doc.fontSize(7)
    const colW = Math.floor((doc.page.width - 60) / Math.min(columns.length, 10))
    const visibleCols = columns.slice(0, 10)
    // Header
    visibleCols.forEach((c, i) => doc.text(c, 30 + i * colW, doc.y, { width: colW, continued: i < visibleCols.length - 1 }))
    doc.moveDown(0.3)
    rows.slice(0, 200).forEach(r => {
      const y = doc.y
      visibleCols.forEach((c, i) => {
        doc.text(String(r[c] ?? '').slice(0, 20), 30 + i * colW, y, { width: colW, continued: i < visibleCols.length - 1 })
      })
      doc.moveDown(0.2)
      if (doc.y > doc.page.height - 50) doc.addPage()
    })
    return doc.end()
  }
}

// ── ENDPOINTS ─────────────────────────────────────────

// Resumen por mes
app.get('/api/ventas/resumen-mes', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM resumen_ventas_facturas_mes${sql} ORDER BY mes DESC`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Resumen por canal+mes
app.get('/api/ventas/resumen-canal', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'mes', op: 'eq', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM resumen_ventas_facturas_canal_mes${sql} ORDER BY mes DESC, fin_ventas_netas_sin_iva DESC`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Resumen por cliente+mes
app.get('/api/ventas/resumen-cliente', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'mes', op: 'eq', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM resumen_ventas_facturas_cliente_mes${sql} ORDER BY mes DESC, fin_ventas_netas_sin_iva DESC`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Resumen por producto+mes
app.get('/api/ventas/resumen-producto', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'mes', op: 'eq', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM resumen_ventas_facturas_producto_mes${sql} ORDER BY mes DESC, fin_ventas_netas_sin_iva DESC`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Facturas encabezados por mes
// Nota: fecha_de_creacion es TEXT con formato 'YYYY-MM-DD HH:MM:SS'
// El filtro por mes usa LEFT(fecha_de_creacion, 7)
app.get('/api/ventas/facturas', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'fecha_de_creacion', op: 'mes', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM zeffi_facturas_venta_encabezados${sql} ORDER BY fecha_de_creacion DESC LIMIT 500`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Cotizaciones por mes
app.get('/api/ventas/cotizaciones', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'fecha_de_creacion', op: 'mes', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM zeffi_cotizaciones_ventas_encabezados${sql} ORDER BY fecha_de_creacion DESC LIMIT 500`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Remisiones por mes
app.get('/api/ventas/remisiones', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'fecha_de_creacion', op: 'mes', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM zeffi_remisiones_venta_encabezados${sql} ORDER BY fecha_de_creacion DESC LIMIT 500`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Columnas de una tabla
app.get('/api/columnas/:tabla', async (req, res) => {
  try {
    const rows = await query(`SHOW COLUMNS FROM \`${req.params.tabla}\``)
    res.json(rows.map(r => r.Field))
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Export endpoint
app.get('/api/export/:recurso', async (req, res) => {
  try {
    const { recurso } = req.params
    const { format = 'xlsx', mes, fields: fieldsRaw, filters: filtersRaw } = req.query
    const filters = filtersRaw ? JSON.parse(filtersRaw) : []
    const fields  = fieldsRaw  ? JSON.parse(fieldsRaw)  : []

    const MAP = {
      'resumen-mes':      { tabla: 'resumen_ventas_facturas_mes',         order: 'mes DESC' },
      'resumen-canal':    { tabla: 'resumen_ventas_facturas_canal_mes',    order: 'mes DESC' },
      'resumen-cliente':  { tabla: 'resumen_ventas_facturas_cliente_mes',  order: 'mes DESC' },
      'resumen-producto': { tabla: 'resumen_ventas_facturas_producto_mes', order: 'mes DESC' },
      'facturas':         { tabla: 'zeffi_facturas_venta_encabezados',          order: 'fecha_de_creacion DESC' },
      'cotizaciones':     { tabla: 'zeffi_cotizaciones_ventas_encabezados',     order: 'fecha_de_creacion DESC' },
      'remisiones':       { tabla: 'zeffi_remisiones_venta_encabezados',        order: 'fecha_de_creacion DESC' },
    }
    if (!MAP[recurso]) return res.status(404).json({ error: 'recurso no encontrado' })

    const { tabla, order } = MAP[recurso]
    if (mes) {
      if (recurso === 'facturas') {
        filters.push({ field: 'fecha_de_creacion', op: 'mes', value: mes })
      } else {
        filters.push({ field: 'mes', op: 'eq', value: mes })
      }
    }
    const { sql, params } = buildWhere(filters)
    const rows = await query(`SELECT * FROM ${tabla}${sql} ORDER BY ${order} LIMIT 5000`, params)

    await exportData(res, rows, fields, format, recurso)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Health check
app.get('/api/health', (req, res) => res.json({ ok: true }))

// Servir frontend estático (dist/spa) — debe ir DESPUÉS de todas las rutas /api
const path = require('path')
const DIST  = path.join(__dirname, '../app/dist/spa')
app.use(express.static(DIST))
// SPA fallback: todas las rutas que no son /api/ devuelven index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(DIST, 'index.html'))
})

const PORT = 9100
app.listen(PORT, '0.0.0.0', () => console.log(`✅ OS ERP corriendo en puerto ${PORT}`))
