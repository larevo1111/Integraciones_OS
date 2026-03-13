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

// Resumen cartera por cliente
app.get('/api/ventas/cartera-cliente', async (req, res) => {
  try {
    const filters = req.query.filters ? JSON.parse(req.query.filters) : []
    if (req.query.mes) filters.push({ field: 'fecha_de_creacion', op: 'mes', value: req.query.mes })
    const { sql, params } = buildWhere(filters)
    const rows = await query(`
      SELECT id_cliente, MAX(cliente) AS cliente, MAX(ciudad) AS ciudad, MAX(vendedor) AS vendedor,
             COUNT(*) AS num_facturas_pendientes,
             SUM(CAST(REPLACE(COALESCE(pdte_de_cobro,'0'),',','.') AS DECIMAL(15,2))) AS total_pendiente,
             SUM(CAST(REPLACE(COALESCE(valor_mora,'0'),',','.') AS DECIMAL(15,2))) AS total_mora,
             MAX(CAST(REPLACE(COALESCE(dias_mora,'0'),',','.') AS SIGNED)) AS max_dias_mora,
             MIN(fecha_de_creacion) AS factura_mas_antigua
      FROM zeffi_facturas_venta_encabezados${sql}
      GROUP BY id_cliente
      HAVING total_pendiente > 0
      ORDER BY total_pendiente DESC
      LIMIT 1000`, params)
    res.json(rows)
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

  // Cartera
  car_saldo: 'Saldo pendiente de cobro',

  // Catálogo
  cat_num_referencias: 'Productos distintos (SKUs) vendidos',
  cat_vtas_por_referencia: 'Venta promedio por referencia de producto',
  cat_num_canales: 'Canales de marketing activos',

  // Consignación
  con_consignacion_pp: 'Mercancía entregada en consignación (órdenes de venta)',

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
