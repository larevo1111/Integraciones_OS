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

// Años disponibles en facturas (para filtro de fechas)
app.get('/api/ventas/anios-facturas', async (req, res) => {
  try {
    const rows = await query(`
      SELECT DISTINCT LEFT(fecha_creacion_factura, 4) AS anio
      FROM zeffi_facturas_venta_detalle
      WHERE fecha_creacion_factura IS NOT NULL AND fecha_creacion_factura != ''
        AND LEFT(fecha_creacion_factura, 4) REGEXP '^[0-9]{4}$'
      ORDER BY anio DESC
    `)
    res.json(rows.map(r => r.anio))
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Helper: cláusula WHERE de fecha sobre zeffi_facturas_venta_detalle.fecha_creacion_factura
function fechaWhereDetalle(desde, hasta) {
  const parts = ["d.cod_articulo IS NOT NULL AND d.cod_articulo != ''"]
  const params = []
  if (desde) { parts.push("LEFT(d.fecha_creacion_factura, 10) >= ?"); params.push(desde) }
  if (hasta) { parts.push("LEFT(d.fecha_creacion_factura, 10) <= ?"); params.push(hasta) }
  return { where: parts.join(' AND '), params }
}
function fechaWhereNC(desde, hasta) {
  const parts = ["nc2.cod_articulo IS NOT NULL AND nc2.cod_articulo != ''"]
  const params = []
  if (desde) { parts.push("LEFT(nc2.fecha_factura, 10) >= ?"); params.push(desde) }
  if (hasta) { parts.push("LEFT(nc2.fecha_factura, 10) <= ?"); params.push(hasta) }
  return { where: parts.join(' AND '), params }
}

// Resumen por producto — con filtro de fechas opcional (?desde=YYYY-MM-DD&hasta=YYYY-MM-DD)
app.get('/api/ventas/resumen-por-producto', async (req, res) => {
  try {
    const { desde, hasta } = req.query
    const wD = fechaWhereDetalle(desde, hasta)
    const wNC = fechaWhereNC(desde, hasta)
    const rows = await query(`
      SELECT
        d.cod_articulo,
        COALESCE(ca.grupo_producto, MIN(d.descripcion_articulo))                              AS grupo_producto,
        MIN(d.descripcion_articulo)                                                           AS descripcion,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4))))          AS cantidad_total,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_ventas_brutas,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))))   AS fin_descuentos,
        ROUND(SUM(
          CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))
        ))                                                                                     AS fin_ventas_netas,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_costo_total,
        ROUND(SUM(
          CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2))
        ))                                                                                     AS fin_utilidad_bruta,
        COALESCE(ROUND(
          SUM(
            CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2))
          ) /
          NULLIF(SUM(
            CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))
          ), 0) * 100, 1
        ), 0)                                                                                  AS margen_pct,
        COALESCE(nc.fin_notas_credito, 0)                                                     AS fin_notas_credito,
        COALESCE(nc.cantidad_nc, 0)                                                           AS cantidad_nc,
        COUNT(DISTINCT d.id_interno)                                                          AS num_facturas,
        COUNT(DISTINCT d.id_cliente)                                                          AS num_clientes
      FROM zeffi_facturas_venta_detalle d
      LEFT JOIN catalogo_articulos ca ON ca.cod_articulo = d.cod_articulo
      LEFT JOIN (
        SELECT
          nc2.cod_articulo,
          ROUND(SUM(CAST(REPLACE(COALESCE(nc2.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
                    CAST(REPLACE(COALESCE(nc2.descuento_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_notas_credito,
          ROUND(SUM(CAST(REPLACE(COALESCE(nc2.cantidad,'0'),',','.') AS DECIMAL(15,4))))        AS cantidad_nc
        FROM zeffi_notas_credito_venta_detalle nc2
        WHERE ${wNC.where}
        GROUP BY nc2.cod_articulo
      ) nc ON nc.cod_articulo = d.cod_articulo
      WHERE ${wD.where}
      GROUP BY d.cod_articulo
      ORDER BY fin_ventas_netas DESC
    `, [...wD.params, ...wNC.params])
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Resumen por grupo producto — con filtro de fechas opcional
app.get('/api/ventas/resumen-por-grupo', async (req, res) => {
  try {
    const { desde, hasta } = req.query
    const wD = fechaWhereDetalle(desde, hasta)
    const wNC = fechaWhereNC(desde, hasta)
    const rows = await query(`
      SELECT
        COALESCE(ca.grupo_producto, d.cod_articulo)                                           AS grupo_producto,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4))))          AS cantidad_total,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_ventas_brutas,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))))   AS fin_descuentos,
        ROUND(SUM(
          CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))
        ))                                                                                     AS fin_ventas_netas,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_costo_total,
        ROUND(SUM(
          CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2)) -
          CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2))
        ))                                                                                     AS fin_utilidad_bruta,
        COALESCE(ROUND(
          SUM(
            CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.costo_promedio_total,'0'),',','.') AS DECIMAL(15,2))
          ) /
          NULLIF(SUM(
            CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
            CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))
          ), 0) * 100, 1
        ), 0)                                                                                  AS margen_pct,
        COALESCE(nc.fin_notas_credito, 0)                                                     AS fin_notas_credito,
        COUNT(DISTINCT d.id_interno)                                                          AS num_facturas,
        COUNT(DISTINCT d.id_cliente)                                                          AS num_clientes,
        COUNT(DISTINCT d.cod_articulo)                                                        AS num_referencias
      FROM zeffi_facturas_venta_detalle d
      LEFT JOIN catalogo_articulos ca ON ca.cod_articulo = d.cod_articulo
      LEFT JOIN (
        SELECT
          COALESCE(ca2.grupo_producto, nc2.cod_articulo) AS grupo_producto,
          ROUND(SUM(CAST(REPLACE(COALESCE(nc2.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
                    CAST(REPLACE(COALESCE(nc2.descuento_total,'0'),',','.') AS DECIMAL(15,2)))) AS fin_notas_credito
        FROM zeffi_notas_credito_venta_detalle nc2
        LEFT JOIN catalogo_articulos ca2 ON ca2.cod_articulo = nc2.cod_articulo
        WHERE ${wNC.where}
        GROUP BY COALESCE(ca2.grupo_producto, nc2.cod_articulo)
      ) nc ON nc.grupo_producto = COALESCE(ca.grupo_producto, d.cod_articulo)
      WHERE ${wD.where}
      GROUP BY COALESCE(ca.grupo_producto, d.cod_articulo)
      ORDER BY fin_ventas_netas DESC
    `, [...wD.params, ...wNC.params])
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

// Facturas por producto (cod_articulo)
app.get('/api/ventas/facturas-producto/:cod_articulo', async (req, res) => {
  try {
    const cod = decodeURIComponent(req.params.cod_articulo)
    const rows = await query(`
      SELECT
        e.id_interno, e.id_numeracion, e.fecha_de_creacion,
        e.cliente, e.id_cliente, e.ciudad, e.vendedor,
        CAST(REPLACE(COALESCE(e.subtotal,'0'),',','.') AS DECIMAL(15,2))    AS fin_subtotal,
        CAST(REPLACE(COALESCE(e.total_neto,'0'),',','.') AS DECIMAL(15,2))  AS fin_total_neto,
        e.estado_cxc,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4))))         AS cantidad_producto,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
                  CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))))  AS fin_venta_producto
      FROM zeffi_facturas_venta_encabezados e
      JOIN zeffi_facturas_venta_detalle d ON d.id_interno = e.id_interno
      WHERE d.cod_articulo = ?
      GROUP BY e.id_interno, e.id_numeracion, e.fecha_de_creacion,
               e.cliente, e.id_cliente, e.ciudad, e.vendedor,
               e.subtotal, e.total_neto, e.estado_cxc
      ORDER BY e.fecha_de_creacion DESC
    `, [cod])
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Facturas por grupo producto
app.get('/api/ventas/facturas-grupo/:grupo', async (req, res) => {
  try {
    const grupo = decodeURIComponent(req.params.grupo)
    const rows = await query(`
      SELECT
        e.id_interno, e.id_numeracion, e.fecha_de_creacion,
        e.cliente, e.id_cliente, e.ciudad, e.vendedor,
        CAST(REPLACE(COALESCE(e.subtotal,'0'),',','.') AS DECIMAL(15,2))    AS fin_subtotal,
        CAST(REPLACE(COALESCE(e.total_neto,'0'),',','.') AS DECIMAL(15,2))  AS fin_total_neto,
        e.estado_cxc,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4))))         AS cantidad_grupo,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2)) -
                  CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))))  AS fin_venta_grupo
      FROM zeffi_facturas_venta_encabezados e
      JOIN zeffi_facturas_venta_detalle d ON d.id_interno = e.id_interno
      JOIN catalogo_articulos ca ON ca.cod_articulo = d.cod_articulo
      WHERE ca.grupo_producto = ?
      GROUP BY e.id_interno, e.id_numeracion, e.fecha_de_creacion,
               e.cliente, e.id_cliente, e.ciudad, e.vendedor,
               e.subtotal, e.total_neto, e.estado_cxc
      ORDER BY e.fecha_de_creacion DESC
    `, [grupo])
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

// ── DETALLE CLIENTE: productos comprados en un mes ────
app.get('/api/ventas/cliente-productos', async (req, res) => {
  try {
    const { mes, id_cliente } = req.query
    if (!id_cliente) return res.status(400).json({ error: 'id_cliente requerido' })
    const params = [id_cliente]
    let sql = `
      SELECT d.cod_articulo, d.descripcion_articulo AS nombre,
             SUM(d.precio_bruto_total - d.descuento_total) AS fin_ventas_netas_sin_iva,
             SUM(d.cantidad) AS vol_unidades_vendidas,
             COUNT(DISTINCT d.id_interno) AS vol_num_facturas
      FROM zeffi_facturas_venta_detalle d
      WHERE d.id_cliente = ?`
    if (mes) { sql += ` AND LEFT(d.fecha_creacion_factura, 7) = ?`; params.push(mes) }
    sql += ` GROUP BY d.cod_articulo, d.descripcion_articulo ORDER BY fin_ventas_netas_sin_iva DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE CANAL: clientes del canal en un mes ───────
app.get('/api/ventas/canal-clientes', async (req, res) => {
  try {
    const { mes, canal } = req.query
    if (!canal) return res.status(400).json({ error: 'canal requerido' })
    const params = [canal]
    let sql = `
      SELECT d.id_cliente, d.cliente,
             SUM(d.precio_bruto_total - d.descuento_total) AS fin_ventas_netas_sin_iva,
             COUNT(DISTINCT d.id_interno) AS vol_num_facturas,
             SUM(d.cantidad) AS vol_unidades_vendidas
      FROM zeffi_facturas_venta_detalle d
      WHERE d.marketing_cliente = ?`
    if (mes) { sql += ` AND LEFT(d.fecha_creacion_factura, 7) = ?`; params.push(mes) }
    sql += ` GROUP BY d.id_cliente, d.cliente ORDER BY fin_ventas_netas_sin_iva DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE CANAL: productos del canal en un mes ──────
app.get('/api/ventas/canal-productos', async (req, res) => {
  try {
    const { mes, canal } = req.query
    if (!canal) return res.status(400).json({ error: 'canal requerido' })
    const params = [canal]
    let sql = `
      SELECT d.cod_articulo, d.descripcion_articulo AS nombre,
             SUM(d.precio_bruto_total - d.descuento_total) AS fin_ventas_netas_sin_iva,
             SUM(d.cantidad) AS vol_unidades_vendidas,
             COUNT(DISTINCT d.id_interno) AS vol_num_facturas
      FROM zeffi_facturas_venta_detalle d
      WHERE d.marketing_cliente = ?`
    if (mes) { sql += ` AND LEFT(d.fecha_creacion_factura, 7) = ?`; params.push(mes) }
    sql += ` GROUP BY d.cod_articulo, d.descripcion_articulo ORDER BY fin_ventas_netas_sin_iva DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE CANAL: facturas del canal en un mes ───────
app.get('/api/ventas/canal-facturas', async (req, res) => {
  try {
    const { mes, canal } = req.query
    if (!canal) return res.status(400).json({ error: 'canal requerido' })
    const params = [canal]
    let sql = `
      SELECT DISTINCT e.*
      FROM zeffi_facturas_venta_encabezados e
      JOIN zeffi_facturas_venta_detalle d ON d.id_interno = e.id_interno AND d.id_numeracion = e.id_numeracion
      WHERE d.marketing_cliente = ?`
    if (mes) { sql += ` AND LEFT(e.fecha_de_creacion, 7) = ?`; params.push(mes) }
    sql += ` ORDER BY e.fecha_de_creacion DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE CANAL: remisiones del canal en un mes ─────
app.get('/api/ventas/canal-remisiones', async (req, res) => {
  try {
    const { mes, canal } = req.query
    if (!canal) return res.status(400).json({ error: 'canal requerido' })
    const params = [canal]
    let sql = `
      SELECT DISTINCT e.*
      FROM zeffi_remisiones_venta_encabezados e
      JOIN zeffi_remisiones_venta_detalle d ON d.id_remision = e.id_remision
      WHERE d.tipo_de_marketing_cliente = ?`
    if (mes) { sql += ` AND LEFT(e.fecha_de_creacion, 7) = ?`; params.push(mes) }
    sql += ` ORDER BY e.fecha_de_creacion DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE PRODUCTO: canales del producto en un mes ──
app.get('/api/ventas/producto-canales', async (req, res) => {
  try {
    const { mes, cod_articulo } = req.query
    if (!cod_articulo) return res.status(400).json({ error: 'cod_articulo requerido' })
    const params = [cod_articulo]
    let sql = `
      SELECT d.marketing_cliente AS canal,
             SUM(d.precio_bruto_total - d.descuento_total) AS fin_ventas_netas_sin_iva,
             SUM(d.cantidad) AS vol_unidades_vendidas,
             COUNT(DISTINCT d.id_cliente) AS cli_clientes_activos
      FROM zeffi_facturas_venta_detalle d
      WHERE d.cod_articulo = ?`
    if (mes) { sql += ` AND LEFT(d.fecha_creacion_factura, 7) = ?`; params.push(mes) }
    sql += ` GROUP BY d.marketing_cliente ORDER BY fin_ventas_netas_sin_iva DESC`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE PRODUCTO: clientes del producto en un mes ─
app.get('/api/ventas/producto-clientes', async (req, res) => {
  try {
    const { mes, cod_articulo } = req.query
    if (!cod_articulo) return res.status(400).json({ error: 'cod_articulo requerido' })
    const params = [cod_articulo]
    let sql = `
      SELECT d.id_cliente, d.cliente,
             SUM(d.precio_bruto_total - d.descuento_total) AS fin_ventas_netas_sin_iva,
             SUM(d.cantidad) AS vol_unidades_vendidas
      FROM zeffi_facturas_venta_detalle d
      WHERE d.cod_articulo = ?`
    if (mes) { sql += ` AND LEFT(d.fecha_creacion_factura, 7) = ?`; params.push(mes) }
    sql += ` GROUP BY d.id_cliente, d.cliente ORDER BY fin_ventas_netas_sin_iva DESC LIMIT 300`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE PRODUCTO: facturas del producto en un mes ─
app.get('/api/ventas/producto-facturas', async (req, res) => {
  try {
    const { mes, cod_articulo } = req.query
    if (!cod_articulo) return res.status(400).json({ error: 'cod_articulo requerido' })
    const params = [cod_articulo]
    let sql = `
      SELECT DISTINCT e.*
      FROM zeffi_facturas_venta_encabezados e
      JOIN zeffi_facturas_venta_detalle d ON d.id_interno = e.id_interno AND d.id_numeracion = e.id_numeracion
      WHERE d.cod_articulo = ?`
    if (mes) { sql += ` AND LEFT(e.fecha_de_creacion, 7) = ?`; params.push(mes) }
    sql += ` ORDER BY e.fecha_de_creacion DESC LIMIT 500`
    const rows = await query(sql, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── DETALLE FACTURA: encabezado + ítems ───────────────
app.get('/api/ventas/factura/:id_interno/:id_numeracion', async (req, res) => {
  try {
    const { id_interno, id_numeracion } = req.params
    const [encabezado] = await query(
      `SELECT * FROM zeffi_facturas_venta_encabezados WHERE id_interno = ? AND id_numeracion = ?`,
      [id_interno, id_numeracion]
    )
    const items = await query(
      `SELECT * FROM zeffi_facturas_venta_detalle WHERE id_interno = ? AND id_numeracion = ?`,
      [id_interno, id_numeracion]
    )
    res.json({ encabezado: encabezado || null, items })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CARTERA CxC ──────────────────────────────────────

// Cartera: facturas con saldo pendiente
app.get('/api/ventas/cartera', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'fecha_de_creacion', op: 'mes', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`
      SELECT id_interno, id_numeracion, fecha_de_creacion, cliente, id_cliente,
             ciudad, vendedor, formas_de_pago,
             CAST(REPLACE(COALESCE(total_neto,'0'),',','.') AS DECIMAL(15,2)) AS total_neto,
             CAST(REPLACE(COALESCE(subtotal,'0'),',','.') AS DECIMAL(15,2)) AS subtotal,
             CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2)) AS pdte_de_cobro,
             estado_cxc,
             CAST(REPLACE(COALESCE(dias_mora,'0'),',','.') AS SIGNED) AS dias_mora,
             CAST(REPLACE(COALESCE(valor_mora,'0'),',','.') AS DECIMAL(15,2)) AS valor_mora
      FROM zeffi_facturas_venta_encabezados${sql}
      HAVING pdte_de_cobro > 0
      ORDER BY dias_mora DESC, pdte_de_cobro DESC
      LIMIT 2000`, params)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// Resumen cartera por cliente (con tramos de antigüedad y plazo del cliente)
app.get('/api/ventas/cartera-cliente', async (req, res) => {
  try {
    const rows = await query(`
      SELECT
        sub.id_cliente,
        MAX(sub.cliente)                                                          AS cliente,
        MAX(sub.ciudad)                                                           AS ciudad,
        MAX(sub.vendedor)                                                         AS vendedor,
        MAX(c.forma_de_pago)                                                      AS plazo,
        COUNT(*)                                                                  AS num_facturas_pendientes,
        SUM(sub.pdte_num)                                                         AS total_pendiente,
        SUM(CASE WHEN sub.ant BETWEEN  1 AND  30 THEN sub.pdte_num ELSE 0 END)   AS saldo_1_30,
        SUM(CASE WHEN sub.ant BETWEEN 31 AND  60 THEN sub.pdte_num ELSE 0 END)   AS saldo_31_60,
        SUM(CASE WHEN sub.ant BETWEEN 61 AND  90 THEN sub.pdte_num ELSE 0 END)   AS saldo_61_90,
        SUM(CASE WHEN sub.ant > 90               THEN sub.pdte_num ELSE 0 END)   AS saldo_mas_90,
        ROUND(AVG(sub.ant), 0)                                                    AS promedio_antiguedad,
        MAX(sub.ant)                                                              AS antiguedad_max
      FROM (
        SELECT *,
               CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2)) AS pdte_num,
               DATEDIFF(CURDATE(), fecha_de_creacion)                               AS ant
        FROM zeffi_facturas_venta_encabezados
        WHERE CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2)) > 0
      ) sub
      LEFT JOIN (
        SELECT numero_de_identificacion, MAX(forma_de_pago) AS forma_de_pago
        FROM zeffi_clientes
        GROUP BY numero_de_identificacion
      ) c ON c.numero_de_identificacion = SUBSTRING_INDEX(sub.id_cliente, ' ', -1)
      GROUP BY sub.id_cliente
      ORDER BY total_pendiente DESC
      LIMIT 1000`)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CARTERA DETALLE: facturas pendientes de un cliente ────
app.get('/api/ventas/cartera-cliente/:id_cliente', async (req, res) => {
  try {
    const id_cliente = decodeURIComponent(req.params.id_cliente)
    const rows = await query(`
      SELECT
        id_interno, id_numeracion, fecha_de_creacion,
        cliente, id_cliente, ciudad, vendedor, formas_de_pago, estado_cxc,
        CAST(REPLACE(COALESCE(total_neto,'0'),',','.') AS DECIMAL(15,2))    AS fin_total_neto,
        CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2)) AS fin_pendiente,
        DATEDIFF(CURDATE(), fecha_de_creacion)                               AS dias_antiguedad
      FROM zeffi_facturas_venta_encabezados
      WHERE id_cliente = ?
        AND CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2)) > 0
      ORDER BY fecha_de_creacion ASC`,
      [id_cliente])
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CONSIGNACIÓN: resumen agrupado por cliente (Nivel 1) ─
app.get('/api/ventas/consignacion', async (req, res) => {
  try {
    const rows = await query(`
      SELECT
        id_cliente,
        MAX(nombre_cliente)  AS nombre_cliente,
        MAX(ciudad)          AS ciudad,
        MAX(vendedor)        AS vendedor,
        COUNT(*)             AS num_ordenes,
        ROUND(SUM(CAST(REPLACE(COALESCE(total_neto,'0'),',','.') AS DECIMAL(15,2))),2) AS fin_total_consignacion,
        MIN(fecha_de_creacion) AS fecha_primera_orden,
        MAX(fecha_de_creacion) AS fecha_ultima_orden
      FROM zeffi_ordenes_venta_encabezados
      WHERE vigencia = 'Vigente'
      GROUP BY id_cliente
      ORDER BY fin_total_consignacion DESC`)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CONSIGNACIÓN CLIENTE: órdenes activas de un cliente (Nivel 2) ─
app.get('/api/ventas/consignacion-cliente/:id_cliente', async (req, res) => {
  try {
    const id_cliente = decodeURIComponent(req.params.id_cliente)
    const rows = await query(`
      SELECT id_orden, nombre_cliente, id_cliente, vendedor, ciudad,
             CAST(REPLACE(COALESCE(total_neto,'0'),',','.') AS DECIMAL(15,2)) AS total_neto_num,
             fecha_de_creacion, fecha_de_entrega, vigencia
      FROM zeffi_ordenes_venta_encabezados
      WHERE vigencia = 'Vigente' AND id_cliente = ?
      ORDER BY fecha_de_creacion ASC`,
      [id_cliente])
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CONSIGNACIÓN ORDEN: encabezado + ítems de una orden (Nivel 3) ─
app.get('/api/ventas/consignacion-por-producto', async (req, res) => {
  try {
    const rows = await query(`
      SELECT
        d.cod_articulo,
        MIN(COALESCE(NULLIF(TRIM(d.descripcion_en_factura),''), d.descripcion_original)) AS descripcion_articulo,
        COUNT(DISTINCT d.id_orden)                                                        AS num_ordenes,
        COUNT(DISTINCT e.id_cliente)                                                      AS num_clientes,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4))))     AS cantidad_total,
        ROUND(SUM(CAST(REPLACE(COALESCE(d.total_neto,'0'),',','.') AS DECIMAL(15,2))))   AS fin_total
      FROM zeffi_ordenes_venta_encabezados e
      JOIN zeffi_ordenes_venta_detalle d ON d.id_orden = e.id_orden
      WHERE e.vigencia = 'Vigente'
      GROUP BY d.cod_articulo
      ORDER BY fin_total DESC`)
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── CONSIGNACIÓN PRODUCTO: órdenes activas que contienen un producto (Nivel 2 desde producto) ─
app.get('/api/ventas/consignacion-producto/:cod_articulo', async (req, res) => {
  try {
    const cod = decodeURIComponent(req.params.cod_articulo)
    const rows = await query(`
      SELECT e.id_orden, e.nombre_cliente, e.id_cliente, e.vendedor, e.ciudad,
             CAST(REPLACE(COALESCE(e.total_neto,'0'),',','.') AS DECIMAL(15,2)) AS fin_total_orden,
             e.fecha_de_creacion, e.fecha_de_entrega,
             MIN(COALESCE(NULLIF(TRIM(d.descripcion_en_factura),''), d.descripcion_original)) AS descripcion_articulo,
             ROUND(SUM(CAST(REPLACE(COALESCE(d.cantidad,'0'),',','.') AS DECIMAL(15,4)))) AS cantidad_producto,
             ROUND(SUM(CAST(REPLACE(COALESCE(d.total_neto,'0'),',','.') AS DECIMAL(15,2)))) AS fin_total_producto
      FROM zeffi_ordenes_venta_encabezados e
      JOIN zeffi_ordenes_venta_detalle d ON d.id_orden = e.id_orden
      WHERE e.vigencia = 'Vigente' AND d.cod_articulo = ?
      GROUP BY e.id_orden, e.nombre_cliente, e.id_cliente, e.vendedor, e.ciudad,
               e.total_neto, e.fecha_de_creacion, e.fecha_de_entrega
      ORDER BY e.fecha_de_creacion ASC`,
      [cod])
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.get('/api/ventas/consignacion-orden/:id_orden', async (req, res) => {
  try {
    const { id_orden } = req.params
    const [encabezado] = await query(
      `SELECT * FROM zeffi_ordenes_venta_encabezados WHERE id_orden = ? LIMIT 1`,
      [id_orden]
    )
    const items = await query(`
      SELECT
        cod_articulo,
        COALESCE(NULLIF(TRIM(descripcion_en_factura),''), descripcion_original) AS descripcion_articulo,
        CAST(REPLACE(COALESCE(cantidad,'0'),',','.') AS DECIMAL(15,4))         AS cantidad,
        CAST(REPLACE(COALESCE(precio_unitario,'0'),',','.') AS DECIMAL(15,2))  AS precio_unitario,
        CAST(REPLACE(COALESCE(total_neto,'0'),',','.') AS DECIMAL(15,2))       AS total
      FROM zeffi_ordenes_venta_detalle
      WHERE id_orden = ?
      ORDER BY _pk`,
      [id_orden]
    )
    res.json({ encabezado: encabezado || null, items })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ── TOOLTIPS — diccionario de columnas ───────────────

const COLUMN_TOOLTIPS = {
  // Identificación
  mes: 'Período en formato YYYY-MM',
  _key: 'Clave única compuesta (mes|dimensión)',
  fecha_actualizacion: 'Última vez que se recalculó este registro',

  // Financiero
  fin_ventas_brutas: 'Suma total antes de descuentos (precio de lista)',
  fin_descuentos: 'Total de descuentos aplicados',
  fin_pct_descuento: 'Porcentaje de descuento promedio sobre ventas brutas',
  fin_ventas_netas_sin_iva: 'Ventas brutas menos descuentos, sin incluir IVA',
  fin_impuestos: 'Total de IVA facturado (va a la DIAN)',
  fin_ventas_netas: 'Total neto facturado incluyendo IVA',
  fin_devoluciones: 'Notas crédito emitidas en el período (sin IVA)',
  fin_ingresos_netos: 'Ventas netas sin IVA menos devoluciones — ingreso real',
  fin_pct_del_mes: 'Participación de este ítem en el total del mes',

  // Costo
  cto_costo_total: 'Costo de la mercancía vendida',
  cto_utilidad_bruta: 'Ventas netas menos costo = ganancia bruta',
  cto_margen_utilidad_pct: 'Margen de utilidad bruta como porcentaje',

  // Volumen
  vol_unidades_vendidas: 'Cantidad total de unidades vendidas',
  vol_num_facturas: 'Número de facturas emitidas',
  vol_ticket_promedio: 'Valor promedio por factura',
  vol_precio_unitario_prom: 'Precio promedio por unidad vendida',

  // Clientes
  cli_clientes_activos: 'Clientes distintos con compra en el período',
  cli_clientes_nuevos: 'Clientes cuya primera compra fue en este período',
  cli_vtas_por_cliente: 'Venta promedio por cliente activo',
  cli_es_nuevo: '1 si es la primera compra histórica del cliente',

  // Consignación
  id_orden:                'Número de orden de venta',
  nombre_cliente:          'Nombre del cliente de la orden',
  total_neto_num:          'Valor total neto de la orden',
  fecha_de_entrega:        'Fecha comprometida de entrega al cliente',
  dias_en_calle:           'Días transcurridos desde la fecha de creación de la orden',
  descripcion_articulo:    'Descripción del artículo en la orden',
  precio_unitario:         'Precio unitario del artículo',

  // Cartera CxC — detalle factura
  fin_total_neto:          'Valor total neto de la factura',
  fin_pendiente:           'Saldo pendiente de cobro de esta factura',
  dias_antiguedad:         'Días transcurridos desde la fecha de creación de la factura',
  formas_de_pago:          'Forma de pago acordada en la factura',

  // Cartera CxC
  total_pendiente:         'Suma total de saldos pendientes del cliente',
  num_facturas_pendientes: 'Cantidad de facturas con saldo sin cobrar',
  plazo:                   'Plazo de pago acordado con el cliente (ej: 30 días, Contado)',
  saldo_1_30:              'Saldo en facturas con antigüedad de 1 a 30 días',
  saldo_31_60:             'Saldo en facturas con antigüedad de 31 a 60 días',
  saldo_61_90:             'Saldo en facturas con antigüedad de 61 a 90 días',
  saldo_mas_90:            'Saldo en facturas con más de 90 días de antigüedad',
  promedio_antiguedad:     'Promedio de días transcurridos desde la fecha de cada factura pendiente',
  antiguedad_max:          'Días transcurridos desde la factura pendiente más antigua del cliente',
  pdte_de_cobro:           'Saldo pendiente de cobro de esta factura',
  estado_cxc:              'Estado actual de la cuenta por cobrar',
  dias_mora:               'Días en mora según el sistema Effi',
  valor_mora:              'Valor de intereses o penalización por mora',

  // Catálogo
  cat_num_referencias: 'Productos distintos (SKUs) vendidos',
  cat_vtas_por_referencia: 'Venta promedio por referencia de producto',
  cat_num_canales: 'Canales de marketing activos',

  // Consignación
  con_consignacion_pp: 'Mercancía entregada en consignación (órdenes de venta)',
  cod_articulo:        'Código interno del artículo en Effi',
  descripcion_articulo:'Nombre o descripción del producto',
  num_ordenes:         'Cantidad de órdenes de venta vigentes que incluyen este producto',
  num_clientes:        'Cantidad de clientes distintos con este producto en consignación',
  cantidad_total:      'Unidades totales del producto actualmente en consignación',

  // Proyección
  pry_dia_del_mes: 'Día del mes actual (para calcular proyección)',
  pry_proyeccion_mes: 'Proyección lineal de ventas al cierre del mes',
  pry_ritmo_pct: 'Proyección vs mismo mes del año anterior',

  // Comparativos — año anterior
  year_ant_ventas_netas: 'Ventas netas del mismo período, un año antes',
  year_ant_var_ventas_pct: 'Variación % de ventas vs el año anterior',
  year_ant_devoluciones: 'Devoluciones del mismo período, año anterior',
  year_ant_var_devoluciones_pct: 'Variación % devoluciones vs año anterior',
  year_ant_ingresos_netos: 'Ingresos netos del mismo período, año anterior',
  year_ant_var_ingresos_netos_pct: 'Variación % ingresos netos vs año anterior',
  year_ant_ticket_promedio: 'Ticket promedio del mismo período, año anterior',
  year_ant_var_ticket_promedio_pct: 'Variación % ticket promedio vs año anterior',
  year_ant_clientes_activos: 'Clientes activos del mismo período, año anterior',
  year_ant_var_clientes_activos_pct: 'Variación % clientes activos vs año anterior',
  year_ant_clientes_nuevos: 'Clientes nuevos del mismo período, año anterior',
  year_ant_var_clientes_nuevos_pct: 'Variación % clientes nuevos vs año anterior',
  year_ant_consignacion_pp: 'Consignación del mismo período, año anterior',
  year_ant_var_consignacion_pct: 'Variación % consignación vs año anterior',
  year_ant_costo_total: 'Costo total del mismo período, año anterior',
  year_ant_var_costo_total_pct: 'Variación % costo vs año anterior',
  year_ant_margen_utilidad_pct: 'Margen de utilidad del año anterior',
  year_ant_var_margen_pct: 'Diferencia en puntos porcentuales del margen vs año anterior',
  year_ant_unidades: 'Unidades vendidas del mismo período, año anterior',
  year_ant_var_unidades_pct: 'Variación % unidades vs año anterior',

  // Comparativos — mes anterior
  mes_ant_ventas_netas: 'Ventas netas del mes inmediatamente anterior',
  mes_ant_var_ventas_pct: 'Variación % ventas vs mes anterior',
  mes_ant_devoluciones: 'Devoluciones del mes anterior',
  mes_ant_var_devoluciones_pct: 'Variación % devoluciones vs mes anterior',
  mes_ant_ingresos_netos: 'Ingresos netos del mes anterior',
  mes_ant_var_ingresos_netos_pct: 'Variación % ingresos netos vs mes anterior',
  mes_ant_ticket_promedio: 'Ticket promedio del mes anterior',
  mes_ant_var_ticket_promedio_pct: 'Variación % ticket promedio vs mes anterior',
  mes_ant_clientes_activos: 'Clientes activos del mes anterior',
  mes_ant_var_clientes_activos_pct: 'Variación % clientes activos vs mes anterior',
  mes_ant_clientes_nuevos: 'Clientes nuevos del mes anterior',
  mes_ant_var_clientes_nuevos_pct: 'Variación % clientes nuevos vs mes anterior',
  mes_ant_consignacion_pp: 'Consignación del mes anterior',
  mes_ant_var_consignacion_pct: 'Variación % consignación vs mes anterior',
  mes_ant_costo_total: 'Costo total del mes anterior',
  mes_ant_var_costo_total_pct: 'Variación % costo vs mes anterior',
  mes_ant_margen_utilidad_pct: 'Margen de utilidad del mes anterior',
  mes_ant_var_margen_pct: 'Diferencia en pp del margen vs mes anterior',
  mes_ant_unidades: 'Unidades del mes anterior',
  mes_ant_var_unidades_pct: 'Variación % unidades vs mes anterior',

  // Cartera CxC
  pdte_de_cobro: 'Saldo pendiente de cobro de la factura',
  estado_cxc: 'Estado de la cuenta por cobrar',
  dias_mora: 'Días de mora desde el vencimiento',
  valor_mora: 'Valor de intereses por mora',
  total_pendiente: 'Suma total pendiente de cobro del cliente',
  total_mora: 'Suma total de mora del cliente',
  max_dias_mora: 'Mayor cantidad de días en mora',
  num_facturas_pendientes: 'Facturas con saldo pendiente',
  factura_mas_antigua: 'Fecha de la factura más antigua pendiente',
}

app.get('/api/tooltips', (req, res) => {
  res.json(COLUMN_TOOLTIPS)
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
      'cartera':          { tabla: 'zeffi_facturas_venta_encabezados',          order: 'fecha_de_creacion DESC' },
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

// Bot tabla: leer token de bot_tablas_temp (ia_service_os local)
app.get('/api/bot/tabla', async (req, res) => {
  const { token } = req.query
  if (!token) return res.status(400).json({ ok: false, error: 'Token requerido' })
  const mysql2 = require('mysql2/promise')
  let conn
  try {
    conn = await mysql2.createConnection({
      host: 'localhost', user: 'osadmin', password: 'Epist2487.', database: 'ia_service_os'
    })
    const [rows] = await conn.execute(
      'SELECT pregunta, columnas, filas FROM bot_tablas_temp WHERE token = ? AND created_at > NOW() - INTERVAL 24 HOUR',
      [token]
    )
    if (!rows.length) return res.status(404).json({ ok: false, error: 'Token no encontrado o expirado' })
    const row = rows[0]
    res.json({
      ok: true,
      pregunta: row.pregunta,
      columnas: typeof row.columnas === 'string' ? JSON.parse(row.columnas) : row.columnas,
      filas: typeof row.filas === 'string' ? JSON.parse(row.filas) : row.filas
    })
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  } finally {
    if (conn) conn.end()
  }
})

// Pipeline: forzar actualización de datos desde Effi
app.post('/api/pipeline/actualizar', (req, res) => {
  const { spawn } = require('child_process')
  const proc = spawn('python3', [
    '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/orquestador.py',
    '--forzar'
  ], { detached: true, stdio: 'ignore' })
  proc.unref()
  res.json({ ok: true, mensaje: 'Pipeline iniciado. Los datos se actualizarán en ~15 minutos.' })
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
