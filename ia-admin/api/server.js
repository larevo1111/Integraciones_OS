/**
 * ia-admin/api/server.js
 * Express API para el panel de administración del Servicio Central de IA
 * Puerto: 9200 — sirve la API y el frontend estático (dist/spa)
 * Auth: Google OAuth (id_token) → JWT propio
 * Multi-empresa: JWT temporal → selección empresa → JWT final
 */

const express = require('express')
const path    = require('path')
const mysql   = require('mysql2/promise')
const jwt     = require('jsonwebtoken')
const https   = require('https')
const fs      = require('fs')
const os      = require('os')
const { exec } = require('child_process')
const util     = require('util')
const execAsync = util.promisify(exec)
const multer   = require('multer')

// Multer — archivos en /tmp, máx 50 MB
const upload = multer({
  dest: os.tmpdir(),
  limits: { fileSize: 50 * 1024 * 1024 }
})

// Extraer texto de un archivo usando el extractor Python
async function extraerTextoPython(rutaArchivo, nombreOriginal) {
  const tmpFile = `/tmp/rag_ext_${Date.now()}.py`
  const pyScript = `import sys, json
sys.path.insert(0, 'scripts')
from ia_service.extractor import extraer_texto
try:
    texto = extraer_texto(${JSON.stringify(rutaArchivo)}, ${JSON.stringify(nombreOriginal)})
    print(json.dumps({'ok': True, 'texto': texto}))
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}))
`
  fs.writeFileSync(tmpFile, pyScript)
  try {
    const { stdout } = await execAsync(`python3 ${tmpFile}`, {
      cwd: '/home/osserver/Proyectos_Antigravity/Integraciones_OS',
      timeout: 120000
    })
    const result = JSON.parse(stdout.trim())
    if (!result.ok) throw new Error(result.error)
    return result.texto
  } finally {
    try { fs.unlinkSync(tmpFile) } catch {}
    try { fs.unlinkSync(rutaArchivo) } catch {}
  }
}

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

// ─── Request logger (diagnóstico) ─────────────────────────────────
app.use((req, res, next) => {
  const orig = res.json.bind(res)
  res.json = function(body) {
    if (res.statusCode >= 400) {
      console.log(`[${res.statusCode}] ${req.method} ${req.path} | auth: ${(req.headers.authorization||'').slice(0,30)}... | body: ${JSON.stringify(body)}`)
    }
    return orig(body)
  }
  next()
})

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
    const decoded = jwt.verify(token, JWT_SECRET)
    req.usuario = decoded
    req.empresa = decoded.empresa_activa || null

    // Si es token temporal, rechazar salvo en /seleccionar_empresa
    if (decoded.tipo === 'temporal' && !req.path.endsWith('/seleccionar_empresa')) {
      return res.status(403).json({ error: 'Selección de empresa pendiente' })
    }

    next()
  } catch (e) {
    res.status(401).json({ error: 'Token expirado o inválido' })
  }
}

// Middleware solo para admins (verifica rol_empresa en token final, o rol en token legacy)
function requireAdmin(req, res, next) {
  const rolEmpresa = req.usuario?.rol_empresa || req.usuario?.rol
  if (rolEmpresa !== 'admin') return res.status(403).json({ error: 'Se requiere rol admin' })
  next()
}

// ─── AUTH — Google OAuth (flujo multi-empresa) ────────────────────
app.post('/api/ia/auth/google', async (req, res) => {
  const { id_token } = req.body
  if (!id_token) return res.status(400).json({ error: 'Falta id_token' })

  try {
    const payload = await validarTokenGoogle(id_token)
    const email   = payload.email

    // Verificar usuario en ia_usuarios
    let [rows] = await db.query('SELECT * FROM ia_usuarios WHERE email = ?', [email])
    let usuario

    if (rows.length) {
      usuario = rows[0]
      if (!usuario.activo) return res.status(403).json({ error: 'Usuario inactivo. Contacta al administrador.' })
    } else {
      return res.status(403).json({ error: 'No tienes acceso a este panel. Contacta al administrador.' })
    }

    // Obtener empresas del usuario
    const [empresas] = await db.query(`
      SELECT e.uid, e.nombre, e.siglas, ue.rol
      FROM ia_usuarios_empresas ue
      JOIN ia_empresas e ON e.uid = ue.empresa_uid
      WHERE ue.usuario_email = ? AND ue.activo = 1 AND e.estado = 'activo'
      ORDER BY e.nombre
    `, [email])

    if (empresas.length === 0) {
      return res.status(403).json({ error: 'No tienes empresas asignadas. Contacta al administrador.' })
    }

    // Si tiene 1 empresa → JWT final directo (7 días)
    if (empresas.length === 1) {
      const emp = empresas[0]
      const jwtPayload = {
        tipo:            'final',
        email:           usuario.email,
        nombre:          usuario.nombre,
        foto:            payload.picture || '',
        empresa_activa:  emp.uid,
        empresa_nombre:  emp.nombre,
        empresa_siglas:  emp.siglas,
        rol_empresa:     emp.rol
      }
      const token = jwt.sign(jwtPayload, JWT_SECRET, { expiresIn: '7d' })
      return res.json({
        ok: true,
        token,
        tipo: 'final',
        usuario: { email: usuario.email, nombre: usuario.nombre, foto: payload.picture || '' },
        empresa: { uid: emp.uid, nombre: emp.nombre, siglas: emp.siglas },
        rol_empresa: emp.rol
      })
    }

    // Si tiene múltiples → JWT temporal (30 min)
    const jwtPayload = {
      tipo:     'temporal',
      email:    usuario.email,
      nombre:   usuario.nombre,
      foto:     payload.picture || '',
      empresas: empresas.map(e => ({ uid: e.uid, nombre: e.nombre, siglas: e.siglas, rol: e.rol }))
    }
    const token = jwt.sign(jwtPayload, JWT_SECRET, { expiresIn: '30m' })
    return res.json({
      ok: true,
      token,
      tipo: 'temporal',
      usuario: { email: usuario.email, nombre: usuario.nombre, foto: payload.picture || '' },
      empresas: jwtPayload.empresas
    })

  } catch (e) {
    res.status(401).json({ error: e.message })
  }
})

// ─── SELECCIONAR EMPRESA (desde token temporal) ───────────────────
app.post('/api/ia/auth/seleccionar_empresa', async (req, res) => {
  const header = req.headers.authorization || ''
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null
  if (!token) return res.status(401).json({ error: 'No autenticado' })

  let decoded
  try {
    decoded = jwt.verify(token, JWT_SECRET)
  } catch (e) {
    return res.status(401).json({ error: 'Token expirado o inválido' })
  }

  if (decoded.tipo !== 'temporal') {
    return res.status(400).json({ error: 'Este endpoint solo acepta tokens temporales' })
  }

  const { empresa_uid } = req.body
  if (!empresa_uid) return res.status(400).json({ error: 'Falta empresa_uid' })

  try {
    // Verificar acceso real en BD
    const [rows] = await db.query(`
      SELECT ue.rol, e.uid, e.nombre, e.siglas
      FROM ia_usuarios_empresas ue
      JOIN ia_empresas e ON e.uid = ue.empresa_uid
      WHERE ue.usuario_email = ? AND ue.empresa_uid = ? AND ue.activo = 1 AND e.estado = 'activo'
    `, [decoded.email, empresa_uid])

    if (!rows.length) {
      return res.status(403).json({ error: 'No tienes acceso a esa empresa' })
    }

    const emp = rows[0]
    const jwtPayload = {
      tipo:           'final',
      email:          decoded.email,
      nombre:         decoded.nombre,
      foto:           decoded.foto || '',
      empresa_activa: emp.uid,
      empresa_nombre: emp.nombre,
      empresa_siglas: emp.siglas,
      rol_empresa:    emp.rol
    }
    const newToken = jwt.sign(jwtPayload, JWT_SECRET, { expiresIn: '7d' })
    res.json({
      ok: true,
      token: newToken,
      empresa: { uid: emp.uid, nombre: emp.nombre, siglas: emp.siglas },
      rol_empresa: emp.rol
    })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── MIS EMPRESAS (token temporal o final) ────────────────────────
app.get('/api/ia/mis-empresas', async (req, res) => {
  const header = req.headers.authorization || ''
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null
  if (!token) return res.status(401).json({ error: 'No autenticado' })

  try {
    const decoded = jwt.verify(token, JWT_SECRET)
    if (decoded.tipo === 'temporal') {
      return res.json({ ok: true, empresas: decoded.empresas || [] })
    }
    // Token final: retornar empresa activa como lista
    return res.json({
      ok: true,
      empresas: [{
        uid:    decoded.empresa_activa,
        nombre: decoded.empresa_nombre,
        siglas: decoded.empresa_siglas,
        rol:    decoded.rol_empresa
      }]
    })
  } catch (e) {
    res.status(401).json({ error: 'Token expirado o inválido' })
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
function proxyIaService(urlPath) {
  return new Promise((resolve, reject) => {
    const http = require('http')
    http.get(`http://localhost:5100${urlPath}`, r => {
      let body = ''
      r.on('data', d => body += d)
      r.on('end', () => { try { resolve(JSON.parse(body)) } catch(e) { reject(e) } })
    }).on('error', reject)
  })
}

// ─── /api/ia/consumo (proxy al ia-service, filtrado por empresa) ──
app.get('/api/ia/consumo', async (req, res) => {
  try {
    const empresa = req.empresa || 'ori_sil_2'
    const params  = new URLSearchParams({ empresa })
    if (req.query.periodo) params.set('periodo', req.query.periodo)
    if (req.query.agente)  params.set('agente',  req.query.agente)
    res.json(await proxyIaService(`/ia/consumo?${params}`))
  } catch (e) {
    res.status(502).json({ error: 'ia-service no disponible: ' + e.message })
  }
})

// ─── /api/ia/consumo/historico (proxy al ia-service, filtrado por empresa) ──
app.get('/api/ia/consumo/historico', async (req, res) => {
  try {
    const empresa = req.empresa || 'ori_sil_2'
    const params  = new URLSearchParams({ empresa })
    if (req.query.dias)   params.set('dias',   req.query.dias)
    if (req.query.agente) params.set('agente', req.query.agente)
    res.json(await proxyIaService(`/ia/consumo/historico?${params}`))
  } catch (e) {
    res.status(502).json({ error: 'ia-service no disponible: ' + e.message })
  }
})

// ─── LOGS ─────────────────────────────────────────────────────────
app.get('/api/ia/logs', async (req, res) => {
  try {
    const limit  = Math.min(parseInt(req.query.limit) || 50, 200)
    const offset = parseInt(req.query.offset) || 0
    const empresa = req.empresa
    const conds = [], vals = []

    // Filtro de empresa siempre presente
    if (empresa) { conds.push('empresa = ?'); vals.push(empresa) }

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

// ─── AGENTES (globales — sin filtro empresa) ──────────────────────
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

// GET /api/ia/rag/temas — filtrado por empresa del token
app.get('/api/ia/rag/temas', requireAuth, async (req, res) => {
  const empresa = req.empresa || req.query.empresa || 'ori_sil_2'
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

// POST /api/ia/rag/temas — empresa viene de req.empresa (del JWT), nunca del body
app.post('/api/ia/rag/temas', requireAdmin, async (req, res) => {
  const empresa = req.empresa || 'ori_sil_2'
  const { slug, nombre, descripcion = '', system_prompt = '', agente_preferido = null } = req.body
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

// GET /api/ia/rag/temas/:id/documentos — verificar empresa del tema
app.get('/api/ia/rag/temas/:id/documentos', requireAuth, async (req, res) => {
  try {
    const empresa = req.empresa
    if (empresa) {
      const [[tema]] = await db.execute('SELECT empresa FROM ia_temas WHERE id = ?', [req.params.id])
      if (!tema) return res.status(404).json({ error: 'Tema no encontrado' })
      if (tema.empresa !== empresa) return res.status(403).json({ error: 'No tienes acceso a este tema' })
    }
    const [rows] = await db.execute(
      'SELECT id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at FROM ia_rag_documentos WHERE tema_id = ? ORDER BY nombre',
      [req.params.id]
    )
    res.json({ ok: true, documentos: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/ia/rag/temas/:id/documentos — crear + indexar (empresa de req.empresa)
app.post('/api/ia/rag/temas/:id/documentos', requireAdmin, async (req, res) => {
  const { nombre, tipo = 'texto', contenido } = req.body
  if (!nombre?.trim()) return res.status(400).json({ error: 'nombre es requerido' })
  if (!contenido?.trim()) return res.status(400).json({ error: 'contenido es requerido' })
  const temaId = parseInt(req.params.id)
  try {
    const [[tema]] = await db.execute('SELECT empresa FROM ia_temas WHERE id = ?', [temaId])
    if (!tema) return res.status(404).json({ error: 'Tema no encontrado' })

    // Verificar que el tema pertenece a la empresa del token
    const empresaToken = req.empresa
    if (empresaToken && tema.empresa !== empresaToken) {
      return res.status(403).json({ error: 'No tienes acceso a este tema' })
    }

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

// POST /api/ia/rag/temas/:id/upload — subir archivo, extraer texto e indexar
app.post('/api/ia/rag/temas/:id/upload', requireAdmin, upload.single('archivo'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No se recibió ningún archivo' })
  const temaId = parseInt(req.params.id)
  const nombreOriginal = req.file.originalname || 'archivo'
  const { nombre } = req.body  // nombre opcional del documento (default = nombreOriginal sin ext)

  try {
    const [[tema]] = await db.execute('SELECT empresa FROM ia_temas WHERE id = ?', [temaId])
    if (!tema) return res.status(404).json({ error: 'Tema no encontrado' })
    if (req.empresa && tema.empresa !== req.empresa) {
      return res.status(403).json({ error: 'No tienes acceso a este tema' })
    }

    // Extraer texto del archivo
    let texto
    try {
      texto = await extraerTextoPython(req.file.path, nombreOriginal)
    } catch (e) {
      return res.status(422).json({ error: 'No se pudo extraer texto: ' + e.message })
    }

    if (!texto?.trim()) {
      return res.status(422).json({ error: 'El archivo no contiene texto extraíble' })
    }

    // Detectar tipo por extensión
    const ext = nombreOriginal.split('.').pop().toLowerCase()
    const tipoMap = { pdf: 'pdf', docx: 'manual', doc: 'manual',
                      xlsx: 'tabla', xls: 'tabla', xlsm: 'tabla',
                      csv: 'tabla', txt: 'texto', md: 'texto',
                      jpg: 'imagen', jpeg: 'imagen', png: 'imagen',
                      webp: 'imagen', gif: 'imagen' }
    const tipo = tipoMap[ext] || 'texto'
    const nombreDoc = (nombre?.trim() || nombreOriginal.replace(/\.[^.]+$/, '')).slice(0, 200)

    // Guardar documento en BD
    const [result] = await db.execute(
      'INSERT INTO ia_rag_documentos (empresa, tema_id, nombre, tipo, contenido_original) VALUES (?, ?, ?, ?, ?)',
      [tema.empresa, temaId, nombreDoc, tipo, texto]
    )
    const docId = result.insertId

    // Indexar fragmentos
    let fragmentos = 0
    try {
      fragmentos = await indexarEnPython(docId, texto, temaId, tema.empresa)
    } catch (e) {
      // Documento creado pero sin fragmentos — advertir pero no fallar
      return res.json({ ok: true, id: docId, fragmentos_creados: 0,
        advertencia: 'Documento creado pero indexación falló: ' + e.message })
    }

    res.json({ ok: true, id: docId, fragmentos_creados: fragmentos,
      nombre: nombreDoc, tipo, chars: texto.length })
  } catch (e) {
    try { fs.unlinkSync(req.file.path) } catch {}
    res.status(500).json({ error: e.message })
  }
})

// ─── RAG — BÚSQUEDA DE PRUEBA ─────────────────────────────────────

// POST /api/ia/rag/buscar
app.post('/api/ia/rag/buscar', requireAuth, async (req, res) => {
  const { pregunta, tema_id } = req.body
  const empresa = req.empresa || req.body.empresa || 'ori_sil_2'
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

// ═══════════════════════════════════════════════════════════════════
// MÓDULO CONEXIONES BD
// ═══════════════════════════════════════════════════════════════════

// GET /api/ia/conexiones
app.get('/api/ia/conexiones', requireAdmin, async (req, res) => {
  try {
    const empresa = req.empresa || 'ori_sil_2'
    const [rows] = await db.execute(
      'SELECT id, empresa, nombre, tipo, host, puerto, usuario, base_datos, activo, notas, ultima_sync, updated_at FROM ia_conexiones_bd WHERE empresa = ? ORDER BY nombre',
      [empresa]
    )
    res.json(rows)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/ia/conexiones/test-params — probar conexión con parámetros crudos (antes de guardar)
app.post('/api/ia/conexiones/test-params', requireAdmin, async (req, res) => {
  const body = JSON.stringify(req.body)
  const options = { host: 'localhost', port: 5100, path: '/ia/conexion/test-params', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }
  const result = await new Promise((resolve) => {
    const r = http.request(options, resp => {
      let d = ''
      resp.on('data', c => d += c)
      resp.on('end', () => { try { resolve(JSON.parse(d)) } catch { resolve({ ok: false, mensaje: d }) } })
    })
    r.on('error', e => resolve({ ok: false, mensaje: e.message }))
    r.write(body); r.end()
  })
  res.json(result)
})

// POST /api/ia/conexiones
app.post('/api/ia/conexiones', requireAdmin, async (req, res) => {
  const { nombre, tipo = 'mariadb', host, puerto = 3306, usuario, password = '', base_datos, notas = '' } = req.body
  if (!nombre || !host || !usuario || !base_datos)
    return res.status(400).json({ error: 'nombre, host, usuario y base_datos son obligatorios' })
  try {
    const [r] = await db.execute(
      'INSERT INTO ia_conexiones_bd (empresa, nombre, tipo, host, puerto, usuario, password, base_datos, notas, usuario_creacion) VALUES (?,?,?,?,?,?,?,?,?,?)',
      [req.empresa, nombre, tipo, host, puerto, usuario, password, base_datos, notas, req.user]
    )
    res.json({ ok: true, id: r.insertId })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/ia/conexiones/:id
app.put('/api/ia/conexiones/:id', requireAdmin, async (req, res) => {
  const { nombre, tipo, host, puerto, usuario, password, base_datos, notas, activo } = req.body
  try {
    const [[conn]] = await db.execute('SELECT id FROM ia_conexiones_bd WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    if (!conn) return res.status(404).json({ error: 'Conexión no encontrada' })
    const fields = [], params = []
    if (nombre     !== undefined) { fields.push('nombre = ?');     params.push(nombre) }
    if (tipo       !== undefined) { fields.push('tipo = ?');       params.push(tipo) }
    if (host       !== undefined) { fields.push('host = ?');       params.push(host) }
    if (puerto     !== undefined) { fields.push('puerto = ?');     params.push(puerto) }
    if (usuario    !== undefined) { fields.push('usuario = ?');    params.push(usuario) }
    if (password   !== undefined) { fields.push('password = ?');   params.push(password) }
    if (base_datos !== undefined) { fields.push('base_datos = ?'); params.push(base_datos) }
    if (notas      !== undefined) { fields.push('notas = ?');      params.push(notas) }
    if (activo     !== undefined) { fields.push('activo = ?');     params.push(activo) }
    fields.push('usuario_ult_mod = ?'); params.push(req.user)
    params.push(req.params.id)
    await db.execute(`UPDATE ia_conexiones_bd SET ${fields.join(', ')} WHERE id = ?`, params)
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// DELETE /api/ia/conexiones/:id
app.delete('/api/ia/conexiones/:id', requireAdmin, async (req, res) => {
  try {
    const [[used]] = await db.execute('SELECT COUNT(*) AS total FROM ia_esquemas WHERE conexion_id = ?', [req.params.id])
    if (used.total > 0)
      return res.status(409).json({ error: `Conexión en uso por ${used.total} esquema(s). Primero desvincula los esquemas.` })
    await db.execute('DELETE FROM ia_conexiones_bd WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/ia/conexiones/:id/test — probar conexión via Flask
app.post('/api/ia/conexiones/:id/test', requireAdmin, async (req, res) => {
  const body = JSON.stringify({ conexion_id: parseInt(req.params.id) })
  const options = { host: 'localhost', port: 5100, path: '/ia/conexion/test', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }
  const result = await new Promise((resolve) => {
    const r = http.request(options, resp => {
      let d = ''
      resp.on('data', c => d += c)
      resp.on('end', () => { try { resolve(JSON.parse(d)) } catch { resolve({ ok: false, mensaje: d }) } })
    })
    r.on('error', e => resolve({ ok: false, mensaje: e.message }))
    r.write(body); r.end()
  })
  res.json(result)
})

// GET /api/ia/conexiones/:id/tablas — listar tablas disponibles
app.get('/api/ia/conexiones/:id/tablas', requireAdmin, async (req, res) => {
  const body = JSON.stringify({ conexion_id: parseInt(req.params.id) })
  const options = { host: 'localhost', port: 5100, path: '/ia/conexion/test', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }
  const result = await new Promise((resolve) => {
    const r = http.request(options, resp => {
      let d = ''
      resp.on('data', c => d += c)
      resp.on('end', () => { try { resolve(JSON.parse(d)) } catch { resolve({ ok: false }) } })
    })
    r.on('error', e => resolve({ ok: false, mensaje: e.message }))
    r.write(body); r.end()
  })
  if (!result.ok) return res.status(400).json({ error: result.mensaje })
  res.json({ tablas: result.tablas_disponibles || [] })
})

// POST /api/ia/esquemas/:tema_id/sync — sincronizar schema via Flask
app.post('/api/ia/esquemas/:tema_id/sync', requireAdmin, async (req, res) => {
  const body = JSON.stringify({ tema_id: parseInt(req.params.tema_id), empresa: req.empresa })
  const options = { host: 'localhost', port: 5100, path: '/ia/esquema/sync', method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }
  const result = await new Promise((resolve) => {
    const r = http.request(options, resp => {
      let d = ''
      resp.on('data', c => d += c)
      resp.on('end', () => { try { resolve(JSON.parse(d)) } catch { resolve({ ok: false, mensaje: d }) } })
    })
    r.on('error', e => resolve({ ok: false, mensaje: e.message }))
    r.write(body); r.end()
  })
  res.json(result)
})

// GET /api/ia/esquemas/:tema_id
app.get('/api/ia/esquemas/:tema_id', requireAdmin, async (req, res) => {
  try {
    const [[row]] = await db.execute(
      `SELECT e.*, c.nombre AS conexion_nombre, c.tipo AS conexion_tipo
       FROM ia_esquemas e LEFT JOIN ia_conexiones_bd c ON c.id = e.conexion_id
       WHERE e.tema_id = ? AND e.empresa = ?`,
      [req.params.tema_id, req.empresa]
    )
    if (!row) return res.status(404).json({ error: 'Esquema no encontrado' })
    if (row.tablas_incluidas) {
      try { row.tablas_incluidas = JSON.parse(row.tablas_incluidas) } catch { row.tablas_incluidas = [] }
    }
    res.json(row)
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/ia/esquemas/:tema_id
app.put('/api/ia/esquemas/:tema_id', requireAdmin, async (req, res) => {
  const { tablas_incluidas, notas_manuales, conexion_id } = req.body
  try {
    const [[row]] = await db.execute('SELECT id FROM ia_esquemas WHERE tema_id = ? AND empresa = ?', [req.params.tema_id, req.empresa])
    if (!row) return res.status(404).json({ error: 'Esquema no encontrado' })
    const fields = [], params = []
    if (tablas_incluidas !== undefined) { fields.push('tablas_incluidas = ?'); params.push(JSON.stringify(tablas_incluidas)) }
    if (notas_manuales  !== undefined) { fields.push('notas_manuales = ?');   params.push(notas_manuales) }
    if (conexion_id     !== undefined) { fields.push('conexion_id = ?');      params.push(conexion_id) }
    if (tablas_incluidas !== undefined || conexion_id !== undefined) {
      fields.push('ddl_auto = NULL'); fields.push('ultima_sync = NULL')
    }
    fields.push('usuario_ult_mod = ?'); params.push(req.user)
    params.push(row.id)
    await db.execute(`UPDATE ia_esquemas SET ${fields.join(', ')} WHERE id = ?`, params)
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── Frontend estático ────────────────────────────────────────────
const distPath = path.join(__dirname, '../app/dist/spa')
app.use(express.static(distPath))
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

app.listen(PORT, '0.0.0.0', () => console.log(`IA Admin — puerto ${PORT}`))
