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
const { exec } = require('child_process')
const util     = require('util')
const execAsync = util.promisify(exec)

async function indexarEnPython(docId, contenido, temaId, empresa = 'ori_sil_2') {
  const escaped = contenido.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '')
  const script = `import sys, json\nsys.path.insert(0, 'scripts')\nfrom ia_service import rag\nn = rag.indexar_documento(${docId}, """${contenido.replace(/"""/g, "\\\"\\\"\\\"").replace(/\\/g, '\\\\')}""", ${temaId}, "${empresa}")\nprint(json.dumps({'fragmentos': n}))`
  // Usar archivo temporal para evitar problemas de escape con contenido largo
  const tmpFile = `/tmp/rag_idx_${Date.now()}.py`
  const pyScript = `import sys, json
sys.path.insert(0, 'scripts')
from ia_service import rag
contenido = ${JSON.stringify(contenido)}
n = rag.indexar_documento(${docId}, contenido, ${temaId}, ${JSON.stringify(empresa)})
print(json.dumps({'fragmentos': n}))
`
  fs.writeFileSync(tmpFile, pyScript)
  try {
    const { stdout } = await execAsync(`python3 ${tmpFile}`, {
      cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
    })
    const data = JSON.parse(stdout.trim())
    return data.fragmentos
  } finally {
    try { fs.unlinkSync(tmpFile) } catch(e) {}
  }
}

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

// ─── helper proxy al ia-service ───────────────────────────────────
function proxyIaService(path) {
  return new Promise((resolve, reject) => {
    const http = require('http')
    http.get(`http://localhost:5100${path}`, r => {
      let body = ''
      r.on('data', d => body += d)
      r.on('end', () => { try { resolve(JSON.parse(body)) } catch(e) { reject(e) } })
    }).on('error', reject)
  })
}

// ─── /api/ia/consumo (proxy al ia-service) ────────────────────────
app.get('/api/ia/consumo', async (req, res) => {
  try {
    res.json(await proxyIaService('/ia/consumo'))
  } catch (e) {
    res.status(502).json({ error: 'ia-service no disponible: ' + e.message })
  }
})

// ─── /api/ia/consumo/historico (proxy al ia-service) ──────────────
app.get('/api/ia/consumo/historico', async (req, res) => {
  try {
    res.json(await proxyIaService('/ia/consumo/historico'))
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
    if (req.query.usuario)     { conds.push('canal LIKE ?');           vals.push(`%${req.query.usuario}%`) }
    if (req.query.fecha_desde) { conds.push('DATE(created_at) >= ?'); vals.push(req.query.fecha_desde) }
    if (req.query.fecha_hasta) { conds.push('DATE(created_at) <= ?'); vals.push(req.query.fecha_hasta) }
    if (req.query.solo_errores){ conds.push('error IS NOT NULL') }

    const where = conds.length ? 'WHERE ' + conds.join(' AND ') : ''
    const [[{ total }]] = await db.query(`SELECT COUNT(*) as total FROM ia_logs ${where}`, vals)
    const [rows] = await db.query(
      `SELECT id, created_at, canal, agente_slug, tipo_consulta,
              tokens_in, tokens_out, (IFNULL(tokens_in,0)+IFNULL(tokens_out,0)) AS tokens_total,
              costo_usd, latencia_ms,
              error AS error_mensaje, pregunta AS pregunta_usuario,
              sql_generado, respuesta AS respuesta_texto
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
      `SELECT slug, nombre, proveedor, modelo_id, tipo, capacidades, orden, activo,
              rate_limit_rpd, rate_limit_rpm,
              costo_input, costo_output,
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
        rate_limit_rpm, costo_input, costo_output, capacidades, orden, activo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [slug, nombre, proveedor || 'google', modelo_id, api_key || '',
       rate_limit_rpd || null, rate_limit_rpm || null,
       req.body.costo_input || 0, req.body.costo_output || 0,
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
                  'costo_input=?','costo_output=?','capacidades=?','orden=?','activo=?']
    const vals = [nombre, proveedor, modelo_id, rate_limit_rpd || null, rate_limit_rpm || null,
                  req.body.costo_input || 0, req.body.costo_output || 0,
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
    const [rows] = await db.query(
      `SELECT slug, nombre, descripcion, agente_preferido, system_prompt,
              requiere_estructura, requiere_ejecucion, formato_salida, temperatura, activo
       FROM ia_tipos_consulta ORDER BY slug`
    )
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/ia/tipos-admin', requireAdmin, async (req, res) => {
  const { tipo, descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  if (!tipo || !agente_preferido) return res.status(400).send('tipo y agente_preferido son requeridos')
  try {
    const { slug: tSlug, nombre: tNombre, agente_preferido: tAgente, system_prompt: tPrompt,
            requiere_estructura, requiere_ejecucion, formato_salida, temperatura, activo: tActivo } = req.body
    if (!tSlug || !tAgente) return res.status(400).send('slug y agente_preferido son requeridos')
    await db.query(
      `INSERT INTO ia_tipos_consulta (slug, nombre, descripcion, agente_preferido, system_prompt,
        requiere_estructura, requiere_ejecucion, formato_salida, temperatura, activo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [tSlug, tNombre || tSlug, descripcion || '', tAgente, tPrompt || '',
       requiere_estructura ? 1 : 0, requiere_ejecucion ? 1 : 0,
       formato_salida || 'texto', temperatura || 0.3, tActivo ? 1 : 0]
    )
    res.json({ ok: true })
  } catch (e) { res.status(500).send(e.message) }
})

app.put('/api/ia/tipos-admin/:tipo', requireAdmin, async (req, res) => {
  const { descripcion, agente_preferido, system_prompt, requiere_bd,
          puede_generar_imagen, max_tokens_respuesta, activo } = req.body
  try {
    const { nombre: pNombre, agente_preferido: pAgente, system_prompt: pPrompt, descripcion: pDesc,
            requiere_estructura: pReqEst, requiere_ejecucion: pReqEjec, formato_salida: pFormato,
            temperatura: pTemp, activo: pActivo } = req.body
    await db.query(
      `UPDATE ia_tipos_consulta SET nombre=?, descripcion=?, agente_preferido=?, system_prompt=?,
        requiere_estructura=?, requiere_ejecucion=?, formato_salida=?, temperatura=?, activo=? WHERE slug=?`,
      [pNombre || req.params.tipo, pDesc || '', pAgente, pPrompt || '',
       pReqEst ? 1 : 0, pReqEjec ? 1 : 0,
       pFormato || 'texto', pTemp || 0.3, pActivo ? 1 : 0, req.params.tipo]
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


// ─── PLAYGROUND — proxy a ia-service ────────────────────────────────────────
app.post('/api/ia/consultar', async (req, res) => {
  try {
    const http = require('http')
    const body = JSON.stringify(req.body)
    const data = await new Promise((resolve, reject) => {
      const r = http.request(
        { host: 'localhost', port: 5100, path: '/ia/consultar', method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } },
        (rsp) => {
          let d = ''
          rsp.on('data', c => d += c)
          rsp.on('end', () => resolve(JSON.parse(d)))
        }
      )
      r.on('error', reject)
      r.write(body)
      r.end()
    })
    res.json(data)
  } catch (e) { res.status(502).json({ error: 'ia-service no disponible: ' + e.message }) }
})

// ─── RAG — TEMAS ─────────────────────────────────────────────────

// GET /api/ia/rag/temas?empresa=ori_sil_2
app.get('/api/ia/rag/temas', requireAuth, async (req, res) => {
  const empresa = req.query.empresa || 'ori_sil_2'
  try {
    const [rows] = await db.execute(`
      SELECT t.*,
             COUNT(DISTINCT d.id)                      AS total_documentos,
             COALESCE(SUM(d.fragmentos_total), 0)      AS total_fragmentos,
             COALESCE(SUM(d.tokens_estimados), 0)      AS total_tokens
      FROM ia_temas t
      LEFT JOIN ia_rag_documentos d ON d.tema_id = t.id AND d.activo = 1 AND d.empresa = t.empresa
      WHERE t.empresa = ?
      GROUP BY t.id
      ORDER BY t.nombre
    `, [empresa])
    res.json({ ok: true, temas: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/ia/rag/temas — crear tema
app.post('/api/ia/rag/temas', requireAdmin, async (req, res) => {
  const { empresa = 'ori_sil_2', slug, nombre, descripcion = '', system_prompt = '', agente_preferido = null } = req.body
  if (!slug || !/^[a-z0-9-]+$/.test(slug)) return res.status(400).json({ error: 'slug inválido (solo minúsculas, guiones y números)' })
  if (!nombre?.trim()) return res.status(400).json({ error: 'nombre es requerido' })
  try {
    const [result] = await db.execute(
      'INSERT INTO ia_temas (empresa, slug, nombre, descripcion, system_prompt, agente_preferido) VALUES (?, ?, ?, ?, ?, ?)',
      [empresa, slug, nombre.trim(), descripcion, system_prompt, agente_preferido || null]
    )
    res.json({ ok: true, id: result.insertId })
  } catch (e) {
    if (e.code === 'ER_DUP_ENTRY') return res.status(400).json({ error: 'Ya existe un tema con ese slug en esta empresa' })
    res.status(500).json({ error: e.message })
  }
})

// PUT /api/ia/rag/temas/:id — editar tema
app.put('/api/ia/rag/temas/:id', requireAdmin, async (req, res) => {
  const { nombre, descripcion, system_prompt, agente_preferido, activo } = req.body
  const fields = [], params = []
  if (nombre !== undefined)          { fields.push('nombre = ?');           params.push(nombre) }
  if (descripcion !== undefined)     { fields.push('descripcion = ?');      params.push(descripcion) }
  if (system_prompt !== undefined)   { fields.push('system_prompt = ?');    params.push(system_prompt) }
  if (agente_preferido !== undefined){ fields.push('agente_preferido = ?'); params.push(agente_preferido || null) }
  if (activo !== undefined)          { fields.push('activo = ?');           params.push(activo ? 1 : 0) }
  if (!fields.length) return res.status(400).json({ error: 'Nada que actualizar' })
  params.push(req.params.id)
  try {
    await db.execute(`UPDATE ia_temas SET ${fields.join(', ')} WHERE id = ?`, params)
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// DELETE /api/ia/rag/temas/:id — eliminar solo si no tiene documentos
app.delete('/api/ia/rag/temas/:id', requireAdmin, async (req, res) => {
  try {
    const [[{ total }]] = await db.execute('SELECT COUNT(*) AS total FROM ia_rag_documentos WHERE tema_id = ?', [req.params.id])
    if (total > 0) return res.status(400).json({ error: `No se puede eliminar: el tema tiene ${total} documento(s). Elimínalos primero.` })
    await db.execute('DELETE FROM ia_temas WHERE id = ?', [req.params.id])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── RAG — DOCUMENTOS ─────────────────────────────────────────────

// GET /api/ia/rag/temas/:id/documentos
app.get('/api/ia/rag/temas/:id/documentos', requireAuth, async (req, res) => {
  try {
    const [rows] = await db.execute(
      'SELECT id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at FROM ia_rag_documentos WHERE tema_id = ? ORDER BY nombre',
      [req.params.id]
    )
    res.json({ ok: true, documentos: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/ia/rag/temas/:id/documentos — crear + indexar
app.post('/api/ia/rag/temas/:id/documentos', requireAdmin, async (req, res) => {
  const { nombre, tipo = 'texto', contenido } = req.body
  if (!nombre?.trim()) return res.status(400).json({ error: 'nombre es requerido' })
  if (!contenido?.trim()) return res.status(400).json({ error: 'contenido es requerido' })
  const temaId = parseInt(req.params.id)
  try {
    const [[tema]] = await db.execute('SELECT empresa FROM ia_temas WHERE id = ?', [temaId])
    if (!tema) return res.status(404).json({ error: 'Tema no encontrado' })

    const [result] = await db.execute(
      'INSERT INTO ia_rag_documentos (empresa, tema_id, nombre, tipo, contenido_original) VALUES (?, ?, ?, ?, ?)',
      [tema.empresa, temaId, nombre.trim(), tipo, contenido]
    )
    const docId = result.insertId

    try {
      const fragmentos = await indexarEnPython(docId, contenido, temaId, tema.empresa)
      res.json({ ok: true, id: docId, fragmentos_creados: fragmentos })
    } catch (e) {
      res.json({ ok: true, id: docId, fragmentos_creados: 0, advertencia: 'Documento creado pero indexación falló: ' + e.message })
    }
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/ia/rag/documentos/:id — con contenido_original
app.get('/api/ia/rag/documentos/:id', requireAuth, async (req, res) => {
  try {
    const [[doc]] = await db.execute('SELECT * FROM ia_rag_documentos WHERE id = ?', [req.params.id])
    if (!doc) return res.status(404).json({ error: 'Documento no encontrado' })
    res.json({ ok: true, documento: doc })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/ia/rag/documentos/:id — actualizar, re-indexar si cambia contenido
app.put('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => {
  const { nombre, tipo, contenido, activo } = req.body
  try {
    const [[doc]] = await db.execute('SELECT * FROM ia_rag_documentos WHERE id = ?', [req.params.id])
    if (!doc) return res.status(404).json({ error: 'Documento no encontrado' })

    const fields = [], params = []
    if (nombre !== undefined)    { fields.push('nombre = ?');              params.push(nombre) }
    if (tipo !== undefined)      { fields.push('tipo = ?');                params.push(tipo) }
    if (activo !== undefined)    { fields.push('activo = ?');              params.push(activo ? 1 : 0) }
    if (contenido !== undefined) { fields.push('contenido_original = ?'); params.push(contenido) }

    if (fields.length) {
      params.push(req.params.id)
      await db.execute(`UPDATE ia_rag_documentos SET ${fields.join(', ')} WHERE id = ?`, params)
    }

    let fragmentos_creados = null
    if (contenido !== undefined) {
      fragmentos_creados = await indexarEnPython(doc.id, contenido, doc.tema_id, doc.empresa)
    }

    res.json({ ok: true, fragmentos_creados })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// DELETE /api/ia/rag/documentos/:id
app.delete('/api/ia/rag/documentos/:id', requireAdmin, async (req, res) => {
  try {
    await db.execute('DELETE FROM ia_rag_documentos WHERE id = ?', [req.params.id])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── RAG — BÚSQUEDA DE PRUEBA ─────────────────────────────────────

// POST /api/ia/rag/buscar
app.post('/api/ia/rag/buscar', requireAuth, async (req, res) => {
  const { pregunta, tema_id, empresa = 'ori_sil_2' } = req.body
  if (!pregunta?.trim()) return res.status(400).json({ error: 'pregunta es requerida' })
  try {
    const tmpFile = `/tmp/rag_buscar_${Date.now()}.py`
    const pyScript = `import sys, json, decimal
sys.path.insert(0, 'scripts')
from ia_service import rag

def fix(o):
    if isinstance(o, decimal.Decimal): return float(o)
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list): return [fix(i) for i in o]
    return o

result = rag.buscar(${JSON.stringify(pregunta)}, empresa=${JSON.stringify(empresa)}${tema_id ? `, tema_id=${parseInt(tema_id)}` : ''})
print(json.dumps({'fragmentos': fix(result)}))
`
    fs.writeFileSync(tmpFile, pyScript)
    try {
      const { stdout } = await execAsync(`python3 ${tmpFile}`, {
        cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
      })
      const data = JSON.parse(stdout.trim())
      res.json({ ok: true, ...data })
    } finally {
      try { fs.unlinkSync(tmpFile) } catch(e) {}
    }
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  }
})

// ─── Frontend estático ────────────────────────────────────────────
const distPath = path.join(__dirname, '../app/dist/spa')
app.use(express.static(distPath))
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

app.listen(PORT, '0.0.0.0', () => console.log(`IA Admin — puerto ${PORT}`))
