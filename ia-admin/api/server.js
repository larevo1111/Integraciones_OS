/**
 * ia-admin/api/server.js
 * Express API para el panel de administración del Servicio Central de IA
 * Puerto: 9200 — sirve la API y el frontend estático (dist/spa)
 * Auth: Google OAuth (id_token) → JWT propio
 */

const express = require('express')
const path    = require('path')
const mysql   = require('mysql2/promise')
const jwt     = require('jsonwebtoken')
const https   = require('https')
const fs      = require('fs')

// ─── Config desde .env ────────────────────────────────────────────
const envPath = path.join(__dirname, '.env')
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const [k, ...v] = line.split('=')
    if (k && v.length) process.env[k.trim()] = v.join('=').trim()
  })
}

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID
const JWT_SECRET       = process.env.JWT_SECRET
const PORT             = 9200

if (!GOOGLE_CLIENT_ID || !JWT_SECRET) {
  console.error('ERROR: Faltan GOOGLE_CLIENT_ID o JWT_SECRET en .env')
  process.exit(1)
}

const app = express()
app.use(express.json())

// ─── BD ia_service_os ──────────────────────────────────────────────
const db = mysql.createPool({
  host: 'localhost', user: 'osadmin', password: 'Epist2487.',
  database: 'ia_service_os', waitForConnections: true, connectionLimit: 10
})

// ─── Validar id_token con Google ─────────────────────────────────
function validarTokenGoogle(idToken) {
  return new Promise((resolve, reject) => {
    const url = `https://oauth2.googleapis.com/tokeninfo?id_token=${idToken}`
    https.get(url, res => {
      let body = ''
      res.on('data', d => body += d)
      res.on('end', () => {
        try {
          const payload = JSON.parse(body)
          if (payload.error) return reject(new Error('Token de Google inválido o expirado'))
          if (payload.aud !== GOOGLE_CLIENT_ID) return reject(new Error('Token no corresponde a esta aplicación'))
          if (!payload.email) return reject(new Error('No se obtuvo email de Google'))
          resolve(payload)
        } catch (e) { reject(e) }
      })
    }).on('error', reject)
  })
}

// ─── Middleware de autenticación JWT ─────────────────────────────
function requireAuth(req, res, next) {
  const header = req.headers.authorization || ''
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null
  if (!token) return res.status(401).json({ error: 'No autenticado' })
  try {
    req.usuario = jwt.verify(token, JWT_SECRET)
    next()
  } catch (e) {
    res.status(401).json({ error: 'Token expirado o inválido' })
  }
}

// Middleware solo para admins
function requireAdmin(req, res, next) {
  if (req.usuario?.rol !== 'admin') return res.status(403).json({ error: 'Se requiere rol admin' })
  next()
}

// ─── AUTH — Google OAuth ──────────────────────────────────────────
app.post('/api/ia/auth/google', async (req, res) => {
  const { id_token } = req.body
  if (!id_token) return res.status(400).json({ error: 'Falta id_token' })

  try {
    const payload = await validarTokenGoogle(id_token)
    const email   = payload.email

    // Buscar o crear usuario
    let [rows] = await db.query('SELECT * FROM ia_usuarios WHERE email = ?', [email])
    let usuario

    if (rows.length) {
      usuario = rows[0]
      if (!usuario.activo) return res.status(403).json({ error: 'Usuario inactivo. Contacta al administrador.' })
    } else {
      // Email no registrado — rechazar
      return res.status(403).json({ error: 'No tienes acceso a este panel. Contacta al administrador.' })
    }

    // Emitir JWT propio (7 días)
    const jwtPayload = {
      email:  usuario.email,
      nombre: usuario.nombre,
      rol:    usuario.rol,
      foto:   payload.picture || ''
    }
    const token = jwt.sign(jwtPayload, JWT_SECRET, { expiresIn: '7d' })

    res.json({ ok: true, token, usuario: jwtPayload })
  } catch (e) {
    res.status(401).json({ error: e.message })
  }
})

// ─── ME — perfil del usuario autenticado ─────────────────────────
app.get('/api/ia/me', requireAuth, (req, res) => {
  res.json(req.usuario)
})

// ─── Health (sin auth) ────────────────────────────────────────────
app.get('/api/health', async (req, res) => {
  try {
    await db.query('SELECT 1')
    const http = require('http')
    const iaOk = await new Promise(resolve => {
      const r = http.get('http://localhost:5100/ia/health', r => resolve(r.statusCode === 200))
      r.on('error', () => resolve(false))
      r.setTimeout(2000, () => { r.destroy(); resolve(false) })
    })
    res.json({ status: 'ok', db: 'ok', ia_service: iaOk ? 'ok' : 'unreachable' })
  } catch (e) {
    res.status(500).json({ status: 'error', error: e.message })
  }
})

// ─── A partir de aquí: TODOS los endpoints requieren auth ─────────
app.use('/api/ia', requireAuth)

// ─── /api/ia/consumo (proxy al ia-service) ────────────────────────
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

// ─── LOGS ─────────────────────────────────────────────────────────
app.get('/api/ia/logs', async (req, res) => {
  try {
    const limit  = Math.min(parseInt(req.query.limit) || 50, 200)
    const offset = parseInt(req.query.offset) || 0
    const conds = [], vals = []

    if (req.query.agente)      { conds.push('agente_slug = ?');       vals.push(req.query.agente) }
    if (req.query.tipo)        { conds.push('tipo_consulta = ?');      vals.push(req.query.tipo) }
    if (req.query.usuario)     { conds.push('usuario_id LIKE ?');      vals.push(`%${req.query.usuario}%`) }
    if (req.query.fecha_desde) { conds.push('DATE(created_at) >= ?'); vals.push(req.query.fecha_desde) }
    if (req.query.fecha_hasta) { conds.push('DATE(created_at) <= ?'); vals.push(req.query.fecha_hasta) }
    if (req.query.solo_errores){ conds.push('error_mensaje IS NOT NULL') }

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
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── AGENTES ──────────────────────────────────────────────────────
app.get('/api/ia/agentes-admin', async (req, res) => {
  try {
    const [rows] = await db.query(
      `SELECT slug, nombre, proveedor, modelo_id, rate_limit_rpd, rate_limit_rpm,
              costo_input_1k, costo_output_1k, capacidades, orden, activo,
              (LENGTH(api_key) > 0) AS tiene_key
       FROM ia_agentes ORDER BY orden, slug`
    )
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/agentes-admin', requireAdmin, async (req, res) => {
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

app.put('/api/ia/agentes-admin/:slug', requireAdmin, async (req, res) => {
  const { nombre, proveedor, modelo_id, api_key, rate_limit_rpd, rate_limit_rpm,
          costo_input_1k, costo_output_1k, capacidades, orden, activo } = req.body
  try {
    const sets = ['nombre=?','proveedor=?','modelo_id=?','rate_limit_rpd=?','rate_limit_rpm=?',
                  'costo_input_1k=?','costo_output_1k=?','capacidades=?','orden=?','activo=?']
    const vals = [nombre, proveedor, modelo_id, rate_limit_rpd || null, rate_limit_rpm || null,
                  costo_input_1k || 0, costo_output_1k || 0,
                  capacidades || '["texto"]', orden ?? 99, activo ? 1 : 0]
    if (api_key && api_key.length > 5) { sets.push('api_key=?'); vals.push(api_key) }
    vals.push(req.params.slug)
    await db.query(`UPDATE ia_agentes SET ${sets.join(',')} WHERE slug=?`, vals)
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/agentes-admin/:slug', requireAdmin, async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    await db.query(`UPDATE ia_agentes SET ${sets} WHERE slug=?`, [...Object.values(req.body), req.params.slug])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/agentes-admin/:slug', requireAdmin, async (req, res) => {
  try {
    await db.query('DELETE FROM ia_agentes WHERE slug=?', [req.params.slug])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── TIPOS DE CONSULTA ────────────────────────────────────────────
app.get('/api/ia/tipos-admin', async (req, res) => {
  try {
    const [rows] = await db.query('SELECT * FROM ia_tipos_consulta ORDER BY tipo')
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/tipos-admin', requireAdmin, async (req, res) => {
  const { tipo, descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  if (!tipo || !agente_preferido) return res.status(400).send('tipo y agente_preferido son requeridos')
  try {
    await db.query(
      `INSERT INTO ia_tipos_consulta (tipo, descripcion, agente_preferido, system_prompt,
        requiere_bd, puede_generar_imagen, max_tokens_respuesta, activo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [tipo, descripcion || '', agente_preferido, system_prompt || '',
       requiere_bd ? 1 : 0, puede_generar_imagen ? 1 : 0, max_tokens_respuesta || 2048, activo ? 1 : 0]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/tipos-admin/:tipo', requireAdmin, async (req, res) => {
  const { descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  try {
    await db.query(
      `UPDATE ia_tipos_consulta SET descripcion=?, agente_preferido=?, system_prompt=?,
        requiere_bd=?, puede_generar_imagen=?, max_tokens_respuesta=?, activo=? WHERE tipo=?`,
      [descripcion || '', agente_preferido, system_prompt || '',
       requiere_bd ? 1 : 0, puede_generar_imagen ? 1 : 0,
       max_tokens_respuesta || 2048, activo ? 1 : 0, req.params.tipo]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/tipos-admin/:tipo', requireAdmin, async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    await db.query(`UPDATE ia_tipos_consulta SET ${sets} WHERE tipo=?`, [...Object.values(req.body), req.params.tipo])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/tipos-admin/:tipo', requireAdmin, async (req, res) => {
  try {
    await db.query('DELETE FROM ia_tipos_consulta WHERE tipo=?', [req.params.tipo])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── USUARIOS ─────────────────────────────────────────────────────
app.get('/api/ia/usuarios', requireAdmin, async (req, res) => {
  try {
    const [rows] = await db.query('SELECT email, nombre, rol, activo, created_at FROM ia_usuarios ORDER BY nombre')
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/usuarios', requireAdmin, async (req, res) => {
  const { email, nombre, rol, activo } = req.body
  if (!email || !nombre) return res.status(400).send('email y nombre son requeridos')
  try {
    await db.query('INSERT INTO ia_usuarios (email, nombre, rol, activo) VALUES (?, ?, ?, ?)',
      [email, nombre, rol || 'viewer', activo ? 1 : 0])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/usuarios/:email', requireAdmin, async (req, res) => {
  const { nombre, rol, activo } = req.body
  try {
    await db.query('UPDATE ia_usuarios SET nombre=?, rol=?, activo=? WHERE email=?',
      [nombre, rol || 'viewer', activo ? 1 : 0, req.params.email])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.patch('/api/ia/usuarios/:email', requireAdmin, async (req, res) => {
  try {
    const sets = Object.keys(req.body).map(k => `${k}=?`).join(',')
    await db.query(`UPDATE ia_usuarios SET ${sets} WHERE email=?`, [...Object.values(req.body), req.params.email])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.delete('/api/ia/usuarios/:email', requireAdmin, async (req, res) => {
  try {
    await db.query('DELETE FROM ia_usuarios WHERE email=?', [req.params.email])
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

// ─── Frontend estático ────────────────────────────────────────────
const distPath = path.join(__dirname, '../app/dist/spa')
app.use(express.static(distPath))
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

app.listen(PORT, '0.0.0.0', () => console.log(`IA Admin — puerto ${PORT}`))
