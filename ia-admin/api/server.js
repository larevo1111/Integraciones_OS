/**
 * ia-admin/api/server.js
 * Express API para el panel de administración del Servicio Central de IA
 * Puerto: 9200 — sirve la API y el frontend estático (dist/spa)
 */

const express = require('express')
const path = require('path')
const mysql = require('mysql2/promise')

const app = express()
const PORT = 9200

app.use(express.json())

// ─── Conexión a ia_service_os (MariaDB local) ─────────────────
const db = mysql.createPool({
  host: 'localhost',
  user: 'osadmin',
  password: 'Epist2487.',
  database: 'ia_service_os',
  waitForConnections: true,
  connectionLimit: 10
})

// ─── Middleware: usuario autenticado via Cloudflare Access ─────
// En producción, Cloudflare inyecta el header CF-Access-Authenticated-User-Email
// En dev local, se usa el email del query param ?dev_email=... o admin por defecto
async function getUsuario(req) {
  const email = req.headers['cf-access-authenticated-user-email']
    || req.query.dev_email
    || 'dev@local'

  try {
    const [rows] = await db.query('SELECT * FROM ia_usuarios WHERE email = ? AND activo = 1', [email])
    if (rows.length) return rows[0]
    // Email no está en la tabla — crear como viewer automáticamente
    const nombre = email.split('@')[0]
    await db.query(
      'INSERT IGNORE INTO ia_usuarios (email, nombre, rol) VALUES (?, ?, ?)',
      [email, nombre, 'viewer']
    )
    return { email, nombre, rol: 'viewer', activo: 1 }
  } catch (e) {
    return { email, nombre: 'Admin', rol: 'admin', activo: 1 }
  }
}

// ─── /api/ia/me ───────────────────────────────────────────────
app.get('/api/ia/me', async (req, res) => {
  const u = await getUsuario(req)
  res.json({ email: u.email, nombre: u.nombre, rol: u.rol })
})

// ─── /api/ia/health ───────────────────────────────────────────
app.get('/api/health', async (req, res) => {
  try {
    await db.query('SELECT 1')
    // Verificar que ia-service esté corriendo
    const http = require('http')
    const iaOk = await new Promise(resolve => {
      const req = http.get('http://localhost:5100/ia/health', r => resolve(r.statusCode === 200))
      req.on('error', () => resolve(false))
      req.setTimeout(2000, () => { req.destroy(); resolve(false) })
    })
    res.json({ status: 'ok', db: 'ok', ia_service: iaOk ? 'ok' : 'unreachable' })
  } catch (e) {
    res.status(500).json({ status: 'error', error: e.message })
  }
})

// ─── /api/ia/consumo (proxy al ia-service) ────────────────────
app.get('/api/ia/consumo', async (req, res) => {
  try {
    const http = require('http')
    const data = await new Promise((resolve, reject) => {
      http.get('http://localhost:5100/ia/consumo', r => {
        let body = ''
        r.on('data', d => body += d)
        r.on('end', () => resolve(JSON.parse(body)))
      }).on('error', reject)
    })
    res.json(data)
  } catch (e) {
    res.status(502).json({ error: 'ia-service no disponible: ' + e.message })
  }
})

// ─── /api/ia/logs ─────────────────────────────────────────────
app.get('/api/ia/logs', async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit) || 50, 200)
    const offset = parseInt(req.query.offset) || 0
    const conds = []
    const vals = []

    if (req.query.agente)       { conds.push('agente_slug = ?');       vals.push(req.query.agente) }
    if (req.query.tipo)         { conds.push('tipo_consulta = ?');      vals.push(req.query.tipo) }
    if (req.query.usuario)      { conds.push('usuario_id LIKE ?');      vals.push(`%${req.query.usuario}%`) }
    if (req.query.fecha_desde)  { conds.push('DATE(created_at) >= ?'); vals.push(req.query.fecha_desde) }
    if (req.query.fecha_hasta)  { conds.push('DATE(created_at) <= ?'); vals.push(req.query.fecha_hasta) }
    if (req.query.solo_errores) { conds.push('error_mensaje IS NOT NULL') }

    const where = conds.length ? 'WHERE ' + conds.join(' AND ') : ''
    const [[{ total }]] = await db.query(`SELECT COUNT(*) as total FROM ia_logs ${where}`, vals)
    const [rows] = await db.query(
      `SELECT id, created_at, usuario_id, canal, agente_slug, tipo_consulta,
              tokens_in, tokens_out, tokens_total, costo_usd, latencia_ms,
              error_mensaje, pregunta_usuario, sql_generado, respuesta_texto
       FROM ia_logs ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`,
      [...vals, limit, offset]
    )
    res.json({ rows, total, limit, offset })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── AGENTES — Admin (con api_key status) ─────────────────────
app.get('/api/ia/agentes-admin', async (req, res) => {
  try {
    const [rows] = await db.query(
      `SELECT slug, nombre, proveedor, modelo_id,
              rate_limit_rpd, rate_limit_rpm, costo_input_1k, costo_output_1k,
              capacidades, orden, activo,
              (LENGTH(api_key) > 0) AS tiene_key
       FROM ia_agentes ORDER BY orden, slug`
    )
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/agentes-admin', async (req, res) => {
  const { slug, nombre, proveedor, modelo_id, api_key, rate_limit_rpd, rate_limit_rpm,
          costo_input_1k, costo_output_1k, capacidades, orden, activo } = req.body
  if (!slug || !nombre || !modelo_id) return res.status(400).send('slug, nombre y modelo_id son requeridos')
  try {
    await db.query(
      `INSERT INTO ia_agentes (slug, nombre, proveedor, modelo_id, api_key, rate_limit_rpd,
        rate_limit_rpm, costo_input_1k, costo_output_1k, capacidades, orden, activo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [slug, nombre, proveedor || 'google', modelo_id, api_key || '',
       rate_limit_rpd || null, rate_limit_rpm || null,
       costo_input_1k || 0, costo_output_1k || 0,
       capacidades || '["texto"]', orden ?? 99, activo ? 1 : 0]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/agentes-admin/:slug', async (req, res) => {
  const { nombre, proveedor, modelo_id, api_key, rate_limit_rpd, rate_limit_rpm,
          costo_input_1k, costo_output_1k, capacidades, orden, activo } = req.body
  try {
    const sets = ['nombre=?','proveedor=?','modelo_id=?','rate_limit_rpd=?','rate_limit_rpm=?',
                  'costo_input_1k=?','costo_output_1k=?','capacidades=?','orden=?','activo=?']
    const vals = [nombre, proveedor, modelo_id, rate_limit_rpd || null, rate_limit_rpm || null,
                  costo_input_1k || 0, costo_output_1k || 0,
                  capacidades || '["texto"]', orden ?? 99, activo ? 1 : 0]
    // Solo actualizar api_key si se envió una nueva
    if (api_key && api_key.length > 5) {
      sets.push('api_key=?')
      vals.push(api_key)
    }
    vals.push(req.params.slug)
    await db.query(`UPDATE ia_agentes SET ${sets.join(',')} WHERE slug=?`, vals)
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/agentes-admin/:slug', async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    const vals = [...Object.values(req.body), req.params.slug]
    await db.query(`UPDATE ia_agentes SET ${sets} WHERE slug=?`, vals)
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/agentes-admin/:slug', async (req, res) => {
  try {
    await db.query('DELETE FROM ia_agentes WHERE slug=?', [req.params.slug])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── TIPOS DE CONSULTA — Admin ────────────────────────────────
app.get('/api/ia/tipos-admin', async (req, res) => {
  try {
    const [rows] = await db.query('SELECT * FROM ia_tipos_consulta ORDER BY tipo')
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/tipos-admin', async (req, res) => {
  const { tipo, descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  if (!tipo || !agente_preferido) return res.status(400).send('tipo y agente_preferido son requeridos')
  try {
    await db.query(
      `INSERT INTO ia_tipos_consulta (tipo, descripcion, agente_preferido, system_prompt,
        requiere_bd, puede_generar_imagen, max_tokens_respuesta, activo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [tipo, descripcion || '', agente_preferido, system_prompt || '',
       requiere_bd ? 1 : 0, puede_generar_imagen ? 1 : 0,
       max_tokens_respuesta || 2048, activo ? 1 : 0]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/tipos-admin/:tipo', async (req, res) => {
  const { descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  try {
    await db.query(
      `UPDATE ia_tipos_consulta SET descripcion=?, agente_preferido=?, system_prompt=?,
        requiere_bd=?, puede_generar_imagen=?, max_tokens_respuesta=?, activo=?
       WHERE tipo=?`,
      [descripcion || '', agente_preferido, system_prompt || '',
       requiere_bd ? 1 : 0, puede_generar_imagen ? 1 : 0,
       max_tokens_respuesta || 2048, activo ? 1 : 0, req.params.tipo]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/tipos-admin/:tipo', async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    const vals = [...Object.values(req.body), req.params.tipo]
    await db.query(`UPDATE ia_tipos_consulta SET ${sets} WHERE tipo=?`, vals)
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/tipos-admin/:tipo', async (req, res) => {
  try {
    await db.query('DELETE FROM ia_tipos_consulta WHERE tipo=?', [req.params.tipo])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── USUARIOS ─────────────────────────────────────────────────
app.get('/api/ia/usuarios', async (req, res) => {
  try {
    const [rows] = await db.query('SELECT email, nombre, rol, activo, created_at FROM ia_usuarios ORDER BY nombre')
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/usuarios', async (req, res) => {
  const { email, nombre, rol, activo } = req.body
  if (!email || !nombre) return res.status(400).send('email y nombre son requeridos')
  try {
    await db.query(
      'INSERT INTO ia_usuarios (email, nombre, rol, activo) VALUES (?, ?, ?, ?)',
      [email, nombre, rol || 'viewer', activo ? 1 : 0]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/usuarios/:email', async (req, res) => {
  const { nombre, rol, activo } = req.body
  try {
    await db.query(
      'UPDATE ia_usuarios SET nombre=?, rol=?, activo=? WHERE email=?',
      [nombre, rol || 'viewer', activo ? 1 : 0, req.params.email]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/usuarios/:email', async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    const vals = [...Object.values(req.body), req.params.email]
    await db.query(`UPDATE ia_usuarios SET ${sets} WHERE email=?`, vals)
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/usuarios/:email', async (req, res) => {
  try {
    await db.query('DELETE FROM ia_usuarios WHERE email=?', [req.params.email])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── Frontend estático (Quasar build) ─────────────────────────
const distPath = path.join(__dirname, '../app/dist/spa')
app.use(express.static(distPath))
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

// ─── Start ────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log(`IA Admin — puerto ${PORT}`)
})
