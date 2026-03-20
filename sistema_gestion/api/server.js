/**
 * sistema_gestion/api/server.js
 * Puerto: 9300
 * Auth: Google OAuth (id_token) → JWT propio, multi-empresa
 * Usuarios/empresas: READ de u768061575_os_comunidad (sys_usuarios, sys_empresa, sys_usuarios_empresas)
 * Datos: READ/WRITE de u768061575_os_gestion (g_*)
 * OPs: READ de u768061575_os_integracion (zeffi_produccion_encabezados)
 */

const express  = require('express')
const path     = require('path')
const https    = require('https')
const fs       = require('fs')
const jwt      = require('jsonwebtoken')
const { execFile } = require('child_process')
const db      = require('./db')

// ─── Cargar .env ───────────────────────────────────────────────────
const envPath = path.join(__dirname, '.env')
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const [k, ...v] = line.split('=')
    if (k && v.length) process.env[k.trim()] = v.join('=').trim()
  })
}

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID
const JWT_SECRET       = process.env.JWT_SECRET
const PORT             = 9300

if (!GOOGLE_CLIENT_ID || !JWT_SECRET) {
  console.error('ERROR: Faltan GOOGLE_CLIENT_ID o JWT_SECRET en .env')
  process.exit(1)
}

const app = express()
app.use(express.json())
app.use(express.static(path.join(__dirname, '../app/dist/spa')))

// ─── CORS ──────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  next()
})

// ─── Logger errores ────────────────────────────────────────────────
app.use((req, res, next) => {
  const orig = res.json.bind(res)
  res.json = function(body) {
    if (res.statusCode >= 400) {
      console.log(`[${res.statusCode}] ${req.method} ${req.path} → ${JSON.stringify(body)}`)
    }
    return orig(body)
  }
  next()
})

// ─── Validar id_token con Google ──────────────────────────────────
function validarTokenGoogle(idToken) {
  return new Promise((resolve, reject) => {
    https.get(`https://oauth2.googleapis.com/tokeninfo?id_token=${idToken}`, res => {
      let body = ''
      res.on('data', d => body += d)
      res.on('end', () => {
        try {
          const p = JSON.parse(body)
          if (p.error)         return reject(new Error('Token de Google inválido o expirado'))
          if (p.aud !== GOOGLE_CLIENT_ID) return reject(new Error('Token no corresponde a esta aplicación'))
          if (!p.email)        return reject(new Error('No se obtuvo email de Google'))
          resolve(p)
        } catch (e) { reject(e) }
      })
    }).on('error', reject)
  })
}

// ─── Middleware JWT ────────────────────────────────────────────────
function requireAuth(req, res, next) {
  const header = req.headers.authorization || ''
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null
  if (!token) return res.status(401).json({ error: 'No autenticado' })
  try {
    const decoded = jwt.verify(token, JWT_SECRET)
    req.usuario = decoded
    req.empresa = decoded.empresa_activa || null
    if (decoded.tipo === 'temporal' && !req.path.endsWith('/seleccionar_empresa')) {
      return res.status(403).json({ error: 'Selección de empresa pendiente' })
    }
    next()
  } catch (e) {
    res.status(401).json({ error: 'Token expirado o inválido' })
  }
}

// ─── AUTH ──────────────────────────────────────────────────────────

// POST /api/gestion/auth/google
app.post('/api/gestion/auth/google', async (req, res) => {
  const { id_token } = req.body
  if (!id_token) return res.status(400).json({ error: 'Falta id_token' })

  try {
    const payload = await validarTokenGoogle(id_token)
    const email   = payload.email

    // Verificar en sys_usuarios (comunidad)
    const [[usuario]] = await db.comunidad.query(
      'SELECT `Email`, `Nombre_Usuario`, `Nivel_Acceso`, `estado` FROM `sys_usuarios` WHERE `Email` = ?',
      [email]
    )
    if (!usuario)              return res.status(403).json({ error: 'No tienes acceso. Contacta al administrador.' })
    if (usuario.estado !== 'Activo') return res.status(403).json({ error: 'Usuario inactivo. Contacta al administrador.' })

    // Obtener empresas del usuario
    const [empresas] = await db.comunidad.query(`
      SELECT e.uid, e.nombre_empresa AS nombre, e.siglas, ue.Nivel_Acceso AS nivel_ue
      FROM sys_usuarios_empresas ue
      JOIN sys_empresa e ON e.uid = ue.empresa
      WHERE ue.usuario = ? AND ue.estado = 'Activo' AND (e.estado = 'Activa' OR e.estado IS NULL)
      ORDER BY e.nombre_empresa
    `, [email])

    if (!empresas.length) return res.status(403).json({ error: 'No tienes empresas asignadas.' })

    // Leer config del usuario en gestion (tema, perfil)
    const [[config]] = await db.gestion.query(
      'SELECT tema, perfil FROM g_usuarios_config WHERE email = ?',
      [email]
    )

    const userBase = {
      email:  usuario.Email,
      nombre: usuario.Nombre_Usuario,
      foto:   payload.picture || '',
      nivel:  usuario.Nivel_Acceso,
      tema:   config?.tema  || 'dark',
      perfil: config?.perfil || null
    }

    // 1 empresa → JWT final (7 días)
    if (empresas.length === 1) {
      const emp   = empresas[0]
      const token = jwt.sign({
        tipo: 'final', ...userBase,
        empresa_activa: emp.uid,
        empresa_nombre: emp.nombre,
        empresa_siglas: emp.siglas || ''
      }, JWT_SECRET, { expiresIn: '7d' })

      return res.json({ ok: true, token, tipo: 'final', usuario: userBase,
        empresa: { uid: emp.uid, nombre: emp.nombre, siglas: emp.siglas || '' } })
    }

    // Varias empresas → JWT temporal (30 min)
    const token = jwt.sign({
      tipo: 'temporal', ...userBase,
      empresas: empresas.map(e => ({ uid: e.uid, nombre: e.nombre, siglas: e.siglas || '' }))
    }, JWT_SECRET, { expiresIn: '30m' })

    return res.json({ ok: true, token, tipo: 'temporal', usuario: userBase,
      empresas: empresas.map(e => ({ uid: e.uid, nombre: e.nombre, siglas: e.siglas || '' })) })

  } catch (e) {
    console.error('[auth/google]', e.message)
    res.status(401).json({ error: e.message })
  }
})

// POST /api/gestion/auth/seleccionar_empresa
app.post('/api/gestion/auth/seleccionar_empresa', async (req, res) => {
  const header = req.headers.authorization || ''
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null
  if (!token) return res.status(401).json({ error: 'No autenticado' })

  let decoded
  try { decoded = jwt.verify(token, JWT_SECRET) }
  catch (e) { return res.status(401).json({ error: 'Token expirado o inválido' }) }

  if (decoded.tipo !== 'temporal') return res.status(400).json({ error: 'Solo acepta tokens temporales' })

  const { empresa_uid } = req.body
  if (!empresa_uid) return res.status(400).json({ error: 'Falta empresa_uid' })

  try {
    const [[emp]] = await db.comunidad.query(`
      SELECT e.uid, e.nombre_empresa AS nombre, e.siglas
      FROM sys_usuarios_empresas ue
      JOIN sys_empresa e ON e.uid = ue.empresa
      WHERE ue.usuario = ? AND ue.empresa = ? AND ue.estado = 'Activo' AND (e.estado = 'Activa' OR e.estado IS NULL)
    `, [decoded.email, empresa_uid])

    if (!emp) return res.status(403).json({ error: 'No tienes acceso a esa empresa' })

    const [[config]] = await db.gestion.query(
      'SELECT tema, perfil FROM g_usuarios_config WHERE email = ?',
      [decoded.email]
    )

    const newToken = jwt.sign({
      tipo:           'final',
      email:          decoded.email,
      nombre:         decoded.nombre,
      foto:           decoded.foto || '',
      nivel:          decoded.nivel,
      tema:           config?.tema  || 'dark',
      perfil:         config?.perfil || null,
      empresa_activa: emp.uid,
      empresa_nombre: emp.nombre,
      empresa_siglas: emp.siglas || ''
    }, JWT_SECRET, { expiresIn: '7d' })

    res.json({ ok: true, token: newToken,
      empresa: { uid: emp.uid, nombre: emp.nombre, siglas: emp.siglas || '' } })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/auth/me
app.get('/api/gestion/auth/me', requireAuth, (req, res) => {
  res.json({ ok: true, usuario: req.usuario, empresa: req.empresa })
})

// PUT /api/gestion/auth/config  — guarda tema y/o perfil
app.put('/api/gestion/auth/config', requireAuth, async (req, res) => {
  const { tema, perfil } = req.body
  const email = req.usuario.email
  try {
    await db.gestion.query(`
      INSERT INTO g_usuarios_config (email, tema, perfil, usuario_ult_modificacion)
      VALUES (?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
        tema = COALESCE(VALUES(tema), tema),
        perfil = COALESCE(VALUES(perfil), perfil),
        usuario_ult_modificacion = VALUES(usuario_ult_modificacion),
        fecha_ult_modificacion = NOW()
    `, [email, tema || 'dark', perfil || null, email])
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/auth/fcm-token
app.post('/api/gestion/auth/fcm-token', requireAuth, async (req, res) => {
  const { token_fcm } = req.body
  if (!token_fcm) return res.status(400).json({ error: 'Falta token_fcm' })
  try {
    await db.gestion.query(`
      INSERT INTO g_usuarios_config (email, token_fcm, usuario_ult_modificacion)
      VALUES (?, ?, ?)
      ON DUPLICATE KEY UPDATE
        token_fcm = VALUES(token_fcm),
        usuario_ult_modificacion = VALUES(usuario_ult_modificacion),
        fecha_ult_modificacion = NOW()
    `, [req.usuario.email, token_fcm, req.usuario.email])
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── Todas las rutas siguientes requieren auth ────────────────────
app.use('/api/gestion', requireAuth)

// ─── USUARIOS (de la empresa activa) ─────────────────────────────

// GET /api/gestion/usuarios
app.get('/api/gestion/usuarios', async (req, res) => {
  try {
    const [rows] = await db.comunidad.query(`
      SELECT u.\`Email\` AS email, u.\`Nombre_Usuario\` AS nombre,
             u.\`Nivel_Acceso\` AS nivel, u.\`foto_url\` AS foto, ue.rol
      FROM sys_usuarios_empresas ue
      JOIN sys_usuarios u ON u.\`Email\` = ue.usuario
      WHERE ue.empresa = ? AND ue.estado = 'Activo' AND u.\`estado\` = 'Activo'
      ORDER BY u.\`Nombre_Usuario\`
    `, [req.empresa])
    res.json({ ok: true, usuarios: rows })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── CATEGORÍAS ───────────────────────────────────────────────────

// GET /api/gestion/categorias  (opcionalmente filtradas por perfil del usuario)
app.get('/api/gestion/categorias', async (req, res) => {
  try {
    const perfil = req.usuario.perfil
    let rows

    if (perfil) {
      // Filtrar categorías del perfil del usuario
      ;[rows] = await db.gestion.query(`
        SELECT c.id, c.nombre, c.color, c.icono, c.es_produccion, c.orden
        FROM g_categorias c
        JOIN g_categorias_perfiles cp ON cp.categoria_id = c.id
        JOIN g_perfiles p ON p.id = cp.perfil_id
        WHERE c.activa = 1 AND p.nombre = ?
        ORDER BY c.orden
      `, [perfil])
    } else {
      // Sin perfil → todas
      ;[rows] = await db.gestion.query(
        'SELECT id, nombre, color, icono, es_produccion, orden FROM g_categorias WHERE activa = 1 ORDER BY orden'
      )
    }

    res.json({ ok: true, categorias: rows })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── PERFILES ─────────────────────────────────────────────────────

// GET /api/gestion/perfiles
app.get('/api/gestion/perfiles', async (req, res) => {
  try {
    const [perfiles] = await db.gestion.query(
      'SELECT id, nombre, descripcion, es_admin FROM g_perfiles WHERE activo = 1 ORDER BY orden'
    )
    // Incluir categorías de cada perfil
    const [relaciones] = await db.gestion.query(`
      SELECT cp.perfil_id, c.id, c.nombre, c.color, c.icono
      FROM g_categorias_perfiles cp
      JOIN g_categorias c ON c.id = cp.categoria_id
      ORDER BY c.orden
    `)
    const map = {}
    relaciones.forEach(r => {
      if (!map[r.perfil_id]) map[r.perfil_id] = []
      map[r.perfil_id].push({ id: r.id, nombre: r.nombre, color: r.color, icono: r.icono })
    })
    const resultado = perfiles.map(p => ({ ...p, categorias: map[p.id] || [] }))
    res.json({ ok: true, perfiles: resultado })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── TAREAS ───────────────────────────────────────────────────────

// GET /api/gestion/tareas
// Filtros: ?filtro=hoy|manana|ayer|semana&responsable=email&categoria_id=&estado=&prioridad=&agrupar=categoria|prioridad|fecha|persona
app.get('/api/gestion/tareas', async (req, res) => {
  const { filtro, responsable, categoria_id, estado, prioridad, solo_mias, proyecto_id, fecha_hoy, id_op } = req.query
  const empresa = req.empresa

  const where  = ['t.empresa = ?', 't.parent_id IS NULL']   // excluir subtareas de la lista principal
  const params = [empresa]

  // fecha_hoy viene del cliente (zona horaria local del usuario) para evitar desfase con servidor Hostinger
  // Si no viene, fallback a CURDATE() del servidor
  function fechaOffset(dias) {
    if (fecha_hoy) {
      const d = new Date(fecha_hoy + 'T00:00:00')
      d.setDate(d.getDate() + dias)
      return d.toISOString().slice(0, 10)
    }
    return null
  }

  // Filtro de fecha
  if (filtro === 'hoy') {
    if (fecha_hoy) { where.push('t.fecha_limite = ?'); params.push(fecha_hoy) }
    else where.push('t.fecha_limite = CURDATE()')
  } else if (filtro === 'manana') {
    const f = fechaOffset(1)
    if (f) { where.push('t.fecha_limite = ?'); params.push(f) }
    else where.push('t.fecha_limite = CURDATE() + INTERVAL 1 DAY')
  } else if (filtro === 'ayer') {
    const f = fechaOffset(-1)
    if (f) { where.push('t.fecha_limite = ?'); params.push(f) }
    else where.push('t.fecha_limite = CURDATE() - INTERVAL 1 DAY')
  } else if (filtro === 'semana') {
    if (fecha_hoy) {
      const d   = new Date(fecha_hoy + 'T00:00:00')
      const dow = d.getDay() === 0 ? 6 : d.getDay() - 1  // lunes=0
      const lun = new Date(d); lun.setDate(d.getDate() - dow)
      const dom = new Date(lun); dom.setDate(lun.getDate() + 6)
      where.push('t.fecha_limite BETWEEN ? AND ?')
      params.push(lun.toISOString().slice(0, 10), dom.toISOString().slice(0, 10))
    } else {
      where.push('t.fecha_limite BETWEEN CURDATE() - INTERVAL WEEKDAY(CURDATE()) DAY AND CURDATE() + INTERVAL (6 - WEEKDAY(CURDATE())) DAY')
    }
  }

  // Filtros adicionales (simples)
  if (responsable)  { where.push('t.responsable = ?');   params.push(responsable) }
  if (solo_mias === '1') { where.push('t.responsable = ?'); params.push(req.usuario.email) }
  if (estado)       { where.push('t.estado = ?');        params.push(estado) }

  // responsables: multi (comma-separated emails)
  const responsablesRaw = req.query.responsables
  if (responsablesRaw) {
    const emails = String(responsablesRaw).split(',').map(s => s.trim()).filter(Boolean)
    if (emails.length === 1) { where.push('t.responsable = ?'); params.push(emails[0]) }
    else if (emails.length > 1) { where.push(`t.responsable IN (${emails.map(() => '?').join(',')})`); params.push(...emails) }
  }

  // id_op: búsqueda parcial en OP Effi
  if (id_op) { where.push('t.id_op LIKE ?'); params.push(`%${id_op}%`) }

  // categoria_id: soporte simple y multi (categorias=1,2,3)
  const categoriasRaw = req.query.categorias || categoria_id
  if (categoriasRaw) {
    const ids = String(categoriasRaw).split(',').map(Number).filter(Boolean)
    if (ids.length === 1) { where.push('t.categoria_id = ?'); params.push(ids[0]) }
    else if (ids.length > 1) { where.push(`t.categoria_id IN (${ids.map(() => '?').join(',')})`); params.push(...ids) }
  }

  // prioridad: soporte simple y multi (prioridades=Urgente,Alta)
  const prioridadesRaw = req.query.prioridades || prioridad
  if (prioridadesRaw) {
    const vals = String(prioridadesRaw).split(',').map(s => s.trim()).filter(Boolean)
    if (vals.length === 1) { where.push('t.prioridad = ?'); params.push(vals[0]) }
    else if (vals.length > 1) { where.push(`t.prioridad IN (${vals.map(() => '?').join(',')})`); params.push(...vals) }
  }

  // proyecto_id: simple
  if (proyecto_id === 'null') { where.push('t.proyecto_id IS NULL') }
  else if (proyecto_id) { where.push('t.proyecto_id = ?'); params.push(proyecto_id) }

  // Rango de fechas personalizado (filtro personalizado)
  const { fecha_desde, fecha_hasta } = req.query
  if (fecha_desde) { where.push('t.fecha_limite >= ?'); params.push(fecha_desde) }
  if (fecha_hasta) { where.push('t.fecha_limite <= ?'); params.push(fecha_hasta) }

  // Etiquetas múltiples (etiquetas=1,2,3)
  const etiquetasRaw = req.query.etiquetas
  if (etiquetasRaw) {
    const eids = String(etiquetasRaw).split(',').map(Number).filter(Boolean)
    if (eids.length > 0) {
      where.push(`EXISTS (SELECT 1 FROM g_etiquetas_tareas et WHERE et.tarea_id = t.id AND et.etiqueta_id IN (${eids.map(() => '?').join(',')}))`)
      params.push(...eids)
    }
  }

  // Por defecto excluir completadas y canceladas (se muestran en sección separada)
  if (!estado) {
    where.push("t.estado NOT IN ('Completada', 'Cancelada')")
  }

  try {
    const [tareas] = await db.gestion.query(`
      SELECT
        t.id, t.parent_id, t.empresa, t.titulo, t.estado, t.prioridad,
        t.responsable, t.categoria_id,
        c.nombre AS categoria_nombre, c.color AS categoria_color, c.icono AS categoria_icono,
        t.proyecto_id,
        p.nombre AS proyecto_nombre, p.color AS proyecto_color,
        t.fecha_limite, t.fecha_inicio_estimada, t.fecha_fin_estimada,
        t.fecha_inicio_real, t.fecha_fin_real,
        t.id_op, t.tiempo_real_min, t.tiempo_estimado_min, t.notas,
        t.usuario_creador, t.fecha_creacion, t.fecha_ult_modificacion,
        -- ¿Hay cronómetro corriendo?
        (SELECT COUNT(*) FROM g_tarea_tiempo tt WHERE tt.tarea_id = t.id AND tt.fin IS NULL) AS cronometro_activo,
        (SELECT tt.inicio FROM g_tarea_tiempo tt WHERE tt.tarea_id = t.id AND tt.fin IS NULL LIMIT 1) AS cronometro_inicio,
        -- Conteo subtareas
        (SELECT COUNT(*) FROM g_tareas s WHERE s.parent_id = t.id) AS subtareas_total,
        (SELECT COUNT(*) FROM g_tareas s WHERE s.parent_id = t.id AND s.estado IN ('Completada','Cancelada')) AS subtareas_completadas,
        -- Etiquetas como JSON array
        (SELECT JSON_ARRAYAGG(JSON_OBJECT('id', e.id, 'nombre', e.nombre, 'color', e.color))
         FROM g_etiquetas_tareas et JOIN g_etiquetas e ON e.id = et.etiqueta_id
         WHERE et.tarea_id = t.id) AS etiquetas_json
      FROM g_tareas t
      JOIN g_categorias c ON c.id = t.categoria_id
      LEFT JOIN g_proyectos p ON p.id = t.proyecto_id
      WHERE ${where.join(' AND ')}
      ORDER BY
        FIELD(t.prioridad, 'Urgente', 'Alta', 'Media', 'Baja'),
        t.fecha_limite ASC,
        t.fecha_creacion DESC
    `, params)

    // Parsear etiquetas_json
    const tareasBase = tareas.map(t => ({
      ...t,
      etiquetas: t.etiquetas_json ? (typeof t.etiquetas_json === 'string' ? JSON.parse(t.etiquetas_json) : t.etiquetas_json) : []
    }))

    // Enriquecer con nombre del responsable (pool comunidad, diferente BD)
    const emails = [...new Set(tareasBase.map(t => t.responsable).filter(Boolean))]
    let nombreMap = {}
    if (emails.length) {
      try {
        const [users] = await db.comunidad.query(
          `SELECT \`Email\` AS email, \`Nombre_Usuario\` AS nombre FROM sys_usuarios WHERE \`Email\` IN (${emails.map(() => '?').join(',')})`,
          emails
        )
        nombreMap = Object.fromEntries(users.map(u => [u.email, u.nombre]))
      } catch {}
    }
    const tareasConEtiquetas = tareasBase.map(t => ({
      ...t,
      responsable_nombre: nombreMap[t.responsable] || null
    }))

    res.json({ ok: true, tareas: tareasConEtiquetas })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/tareas/completadas
app.get('/api/gestion/tareas/completadas', async (req, res) => {
  const { categoria_id, responsable, proyecto_id, solo_mias } = req.query
  const where  = ["t.empresa = ?", "t.estado IN ('Completada', 'Cancelada')", "t.parent_id IS NULL"]
  const params = [req.empresa]

  if (categoria_id) { where.push('t.categoria_id = ?'); params.push(categoria_id) }
  if (responsable)  { where.push('t.responsable = ?');  params.push(responsable) }
  if (proyecto_id)  { where.push('t.proyecto_id = ?');  params.push(proyecto_id) }
  if (solo_mias === '1') { where.push('t.responsable = ?'); params.push(req.usuario.email) }

  try {
    const [tareas] = await db.gestion.query(`
      SELECT t.id, t.titulo, t.estado, t.prioridad, t.responsable,
             t.categoria_id, c.nombre AS categoria_nombre, c.color AS categoria_color,
             t.fecha_limite, t.fecha_fin_real, t.tiempo_real_min,
             t.usuario_creador, t.fecha_ult_modificacion
      FROM g_tareas t
      JOIN g_categorias c ON c.id = t.categoria_id
      WHERE ${where.join(' AND ')}
      ORDER BY t.fecha_ult_modificacion DESC
      LIMIT 50
    `, params)
    res.json({ ok: true, tareas })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/tareas/:id
app.get('/api/gestion/tareas/:id', async (req, res) => {
  try {
    const [[tarea]] = await db.gestion.query(`
      SELECT t.*, c.nombre AS categoria_nombre, c.color AS categoria_color,
             c.icono AS categoria_icono, c.es_produccion,
             p.nombre AS proyecto_nombre, p.color AS proyecto_color
      FROM g_tareas t
      JOIN g_categorias c ON c.id = t.categoria_id
      LEFT JOIN g_proyectos p ON p.id = t.proyecto_id
      WHERE t.id = ? AND t.empresa = ?
    `, [req.params.id, req.empresa])

    if (!tarea) return res.status(404).json({ error: 'Tarea no encontrada' })

    // Registros de tiempo
    const [tiempos] = await db.gestion.query(
      'SELECT * FROM g_tarea_tiempo WHERE tarea_id = ? ORDER BY inicio',
      [req.params.id]
    )

    // Etiquetas de la tarea
    const [etiquetas] = await db.gestion.query(`
      SELECT e.id, e.nombre, e.color
      FROM g_etiquetas_tareas et JOIN g_etiquetas e ON e.id = et.etiqueta_id
      WHERE et.tarea_id = ?
    `, [req.params.id])

    res.json({ ok: true, tarea: { ...tarea, tiempos, etiquetas } })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/tareas/:id/subtareas
app.get('/api/gestion/tareas/:id/subtareas', async (req, res) => {
  try {
    const [subtareas] = await db.gestion.query(`
      SELECT t.id, t.parent_id, t.titulo, t.estado, t.prioridad,
             t.responsable, t.categoria_id,
             c.nombre AS categoria_nombre, c.color AS categoria_color,
             t.proyecto_id, t.fecha_limite, t.tiempo_real_min, t.tiempo_estimado_min,
             t.fecha_inicio_real, t.fecha_fin_real,
             (SELECT COUNT(*) FROM g_tarea_tiempo tt WHERE tt.tarea_id = t.id AND tt.fin IS NULL) AS cronometro_activo,
             (SELECT tt.inicio FROM g_tarea_tiempo tt WHERE tt.tarea_id = t.id AND tt.fin IS NULL LIMIT 1) AS cronometro_inicio
      FROM g_tareas t
      JOIN g_categorias c ON c.id = t.categoria_id
      WHERE t.parent_id = ? AND t.empresa = ?
      ORDER BY FIELD(t.estado,'Pendiente','En Progreso','Completada','Cancelada'),
               FIELD(t.prioridad,'Urgente','Alta','Media','Baja'),
               t.fecha_creacion ASC
    `, [req.params.id, req.empresa])

    // Enriquecer con nombre del responsable
    const emails = [...new Set(subtareas.map(t => t.responsable).filter(Boolean))]
    let nombreMap = {}
    if (emails.length) {
      try {
        const [users] = await db.comunidad.query(
          `SELECT \`Email\` AS email, \`Nombre_Usuario\` AS nombre FROM sys_usuarios WHERE \`Email\` IN (${emails.map(() => '?').join(',')})`,
          emails
        )
        nombreMap = Object.fromEntries(users.map(u => [u.email, u.nombre]))
      } catch {}
    }
    res.json({ ok: true, subtareas: subtareas.map(t => ({ ...t, responsable_nombre: nombreMap[t.responsable] || null })) })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/tareas
app.post('/api/gestion/tareas', async (req, res) => {
  const {
    titulo, descripcion, categoria_id, proyecto_id, prioridad, responsable,
    fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
    tiempo_estimado_min, id_op, notas, etiquetas, parent_id
  } = req.body

  if (!titulo || !categoria_id) return res.status(400).json({ error: 'Faltan titulo y categoria_id' })

  try {
    const [result] = await db.gestion.query(`
      INSERT INTO g_tareas
        (empresa, parent_id, titulo, descripcion, categoria_id, proyecto_id, prioridad, responsable,
         fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
         tiempo_estimado_min, id_op, notas, usuario_creador, usuario_ult_modificacion)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      req.empresa, parent_id || null,
      titulo, descripcion || null, categoria_id,
      proyecto_id || null,
      prioridad || 'Media',
      responsable || req.usuario.email,
      fecha_limite || null,
      fecha_inicio_estimada || fecha_limite || null,
      fecha_fin_estimada    || fecha_limite || null,
      tiempo_estimado_min || null,
      id_op || null, notas || null,
      req.usuario.email, req.usuario.email
    ])

    const tareaId = result.insertId

    // Insertar etiquetas si se pasaron
    if (etiquetas && Array.isArray(etiquetas) && etiquetas.length > 0) {
      const vals = etiquetas.map(eid => [tareaId, eid])
      await db.gestion.query('INSERT IGNORE INTO g_etiquetas_tareas (tarea_id, etiqueta_id) VALUES ?', [vals])
    }

    const [[tarea]] = await db.gestion.query(
      `SELECT t.*, c.nombre AS categoria_nombre, c.color AS categoria_color,
              p.nombre AS proyecto_nombre, p.color AS proyecto_color
       FROM g_tareas t
       JOIN g_categorias c ON c.id = t.categoria_id
       LEFT JOIN g_proyectos p ON p.id = t.proyecto_id
       WHERE t.id = ?`,
      [tareaId]
    )
    res.status(201).json({ ok: true, tarea })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// PUT /api/gestion/tareas/:id
app.put('/api/gestion/tareas/:id', async (req, res) => {
  const {
    titulo, descripcion, categoria_id, proyecto_id, estado, prioridad, responsable,
    fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
    fecha_inicio_real, fecha_fin_real,
    tiempo_real_min, tiempo_estimado_min, id_op, notas, etiquetas
  } = req.body

  try {
    const sets    = []
    const params  = []

    if (titulo           !== undefined) { sets.push('titulo = ?');             params.push(titulo) }
    if (descripcion      !== undefined) { sets.push('descripcion = ?');        params.push(descripcion) }
    if (categoria_id     !== undefined) { sets.push('categoria_id = ?');       params.push(categoria_id) }
    if (proyecto_id      !== undefined) { sets.push('proyecto_id = ?');        params.push(proyecto_id) }
    if (estado           !== undefined) {
      sets.push('estado = ?')
      params.push(estado)
      // Auto-fechas reales según cambio de estado
      if (estado === 'En Progreso') {
        sets.push('fecha_inicio_real = NOW()')  // Opción B: siempre actualiza
      }
      if (estado === 'Completada') {
        sets.push('fecha_fin_real = COALESCE(fecha_fin_real, NOW())')  // solo si no tiene
      }
    }
    if (prioridad        !== undefined) { sets.push('prioridad = ?');          params.push(prioridad) }
    if (responsable      !== undefined) { sets.push('responsable = ?');        params.push(responsable) }
    if (fecha_limite     !== undefined) { sets.push('fecha_limite = ?');       params.push(fecha_limite) }
    if (fecha_inicio_estimada !== undefined) { sets.push('fecha_inicio_estimada = ?'); params.push(fecha_inicio_estimada) }
    if (fecha_fin_estimada    !== undefined) { sets.push('fecha_fin_estimada = ?');    params.push(fecha_fin_estimada) }
    if (fecha_inicio_real     !== undefined) { sets.push('fecha_inicio_real = ?');     params.push(fecha_inicio_real) }
    if (fecha_fin_real        !== undefined) { sets.push('fecha_fin_real = ?');        params.push(fecha_fin_real) }
    if (tiempo_real_min       !== undefined) { sets.push('tiempo_real_min = ?');       params.push(tiempo_real_min) }
    if (tiempo_estimado_min   !== undefined) { sets.push('tiempo_estimado_min = ?');   params.push(tiempo_estimado_min) }
    if (id_op            !== undefined) { sets.push('id_op = ?');              params.push(id_op) }
    if (notas            !== undefined) { sets.push('notas = ?');              params.push(notas) }

    if (sets.length) {
      sets.push('usuario_ult_modificacion = ?')
      params.push(req.usuario.email)
      params.push(req.params.id, req.empresa)

      await db.gestion.query(
        `UPDATE g_tareas SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`,
        params
      )
    }

    // Actualizar etiquetas (si se pasó el array — reemplaza todas)
    if (etiquetas !== undefined && Array.isArray(etiquetas)) {
      await db.gestion.query('DELETE FROM g_etiquetas_tareas WHERE tarea_id = ?', [req.params.id])
      if (etiquetas.length > 0) {
        const vals = etiquetas.map(eid => [req.params.id, eid])
        await db.gestion.query('INSERT IGNORE INTO g_etiquetas_tareas (tarea_id, etiqueta_id) VALUES ?', [vals])
      }
    }

    const [[tarea]] = await db.gestion.query(
      `SELECT t.*, c.nombre AS categoria_nombre, c.color AS categoria_color,
              p.nombre AS proyecto_nombre, p.color AS proyecto_color
       FROM g_tareas t
       JOIN g_categorias c ON c.id = t.categoria_id
       LEFT JOIN g_proyectos p ON p.id = t.proyecto_id
       WHERE t.id = ?`,
      [req.params.id]
    )
    // Incluir etiquetas en la respuesta del PUT (para que el panel no las pierda)
    const [etiqPut] = await db.gestion.query(
      `SELECT e.id, e.nombre, e.color FROM g_etiquetas_tareas et
       JOIN g_etiquetas e ON e.id = et.etiqueta_id WHERE et.tarea_id = ?`,
      [req.params.id]
    )
    res.json({ ok: true, tarea: { ...tarea, etiquetas: etiqPut } })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// DELETE /api/gestion/tareas/:id
app.delete('/api/gestion/tareas/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_tareas WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── CRONÓMETRO ───────────────────────────────────────────────────

// POST /api/gestion/tareas/:id/iniciar
app.post('/api/gestion/tareas/:id/iniciar', async (req, res) => {
  const tareaId = req.params.id
  try {
    // Verificar que la tarea existe y pertenece a la empresa
    const [[tarea]] = await db.gestion.query(
      'SELECT id, estado FROM g_tareas WHERE id = ? AND empresa = ?',
      [tareaId, req.empresa]
    )
    if (!tarea) return res.status(404).json({ error: 'Tarea no encontrada' })

    // Cerrar cualquier cronómetro abierto (seguridad)
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = NOW(), duracion_min = ROUND(TIMESTAMPDIFF(SECOND, inicio, NOW()) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [tareaId])

    // Iniciar nuevo registro
    const [result] = await db.gestion.query(
      'INSERT INTO g_tarea_tiempo (tarea_id, usuario, inicio) VALUES (?, ?, NOW())',
      [tareaId, req.usuario.email]
    )

    // Actualizar estado a En Progreso
    await db.gestion.query(
      "UPDATE g_tareas SET estado = 'En Progreso', usuario_ult_modificacion = ? WHERE id = ?",
      [req.usuario.email, tareaId]
    )

    const [[tiempo]] = await db.gestion.query(
      'SELECT * FROM g_tarea_tiempo WHERE id = ?', [result.insertId]
    )
    res.json({ ok: true, tiempo })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/tareas/:id/detener
app.post('/api/gestion/tareas/:id/detener', async (req, res) => {
  const tareaId = req.params.id
  try {
    // Cerrar registro abierto
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = NOW(), duracion_min = ROUND(TIMESTAMPDIFF(SECOND, inicio, NOW()) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [tareaId])

    // Recalcular tiempo_real_min total
    const [[{ total }]] = await db.gestion.query(
      'SELECT COALESCE(SUM(duracion_min), 0) AS total FROM g_tarea_tiempo WHERE tarea_id = ?',
      [tareaId]
    )

    await db.gestion.query(
      "UPDATE g_tareas SET estado = 'Pendiente', tiempo_real_min = ?, usuario_ult_modificacion = ? WHERE id = ?",
      [total, req.usuario.email, tareaId]
    )

    res.json({ ok: true, tiempo_real_min: total })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/tareas/:id/reiniciar-tiempo
app.post('/api/gestion/tareas/:id/reiniciar-tiempo', async (req, res) => {
  const tareaId = req.params.id
  try {
    const [[tarea]] = await db.gestion.query(
      'SELECT id FROM g_tareas WHERE id = ? AND empresa = ?', [tareaId, req.empresa]
    )
    if (!tarea) return res.status(404).json({ error: 'Tarea no encontrada' })
    // Cerrar timer abierto si existe
    await db.gestion.query(
      'UPDATE g_tarea_tiempo SET fin = NOW() WHERE tarea_id = ? AND fin IS NULL', [tareaId]
    )
    // Eliminar todos los registros de tiempo de esta tarea
    await db.gestion.query('DELETE FROM g_tarea_tiempo WHERE tarea_id = ?', [tareaId])
    // Resetear tiempo_real_min a 0
    await db.gestion.query(
      'UPDATE g_tareas SET tiempo_real_min = 0, usuario_ult_modificacion = ? WHERE id = ?',
      [req.usuario.email, tareaId]
    )
    res.json({ ok: true, tiempo_real_min: 0 })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/tareas/:id/completar
// Body opcional: { tiempo_real_min } — si el usuario corrige el tiempo manualmente
app.post('/api/gestion/tareas/:id/completar', async (req, res) => {
  const tareaId = req.params.id
  const { tiempo_real_min: tiempoManual } = req.body

  try {
    // Cerrar cronómetro si estaba corriendo
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = NOW(), duracion_min = ROUND(TIMESTAMPDIFF(SECOND, inicio, NOW()) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [tareaId])

    // Calcular tiempo total (o usar el manual si se proveyó)
    let tiempoFinal = tiempoManual
    if (tiempoFinal === undefined || tiempoFinal === null) {
      const [[{ total }]] = await db.gestion.query(
        'SELECT COALESCE(SUM(duracion_min), 0) AS total FROM g_tarea_tiempo WHERE tarea_id = ?',
        [tareaId]
      )
      tiempoFinal = total
    }

    await db.gestion.query(`
      UPDATE g_tareas
      SET estado = 'Completada',
          tiempo_real_min = ?,
          fecha_fin_real = NOW(),
          usuario_ult_modificacion = ?
      WHERE id = ? AND empresa = ?
    `, [tiempoFinal, req.usuario.email, tareaId, req.empresa])

    const [[tarea]] = await db.gestion.query(
      'SELECT t.*, c.nombre AS categoria_nombre FROM g_tareas t JOIN g_categorias c ON c.id = t.categoria_id WHERE t.id = ?',
      [tareaId]
    )
    res.json({ ok: true, tarea })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ─── OP LOOKUP (Effi) ─────────────────────────────────────────────

// GET /api/gestion/ops  — OPs pendientes (Vigente + no Procesada) con artículos
// ?q=texto  → filtra por id_orden o descripción de artículo
app.get('/api/gestion/ops', async (req, res) => {
  const q = (req.query.q || '').trim()
  try {
    const [rows] = await db.integracion.query(`
      SELECT e.id_orden, e.estado, e.fecha_final,
             GROUP_CONCAT(DISTINCT a.descripcion_articulo_producido
               ORDER BY a.descripcion_articulo_producido
               SEPARATOR ' / ') AS articulos
      FROM zeffi_produccion_encabezados e
      LEFT JOIN zeffi_articulos_producidos a ON a.id_orden = e.id_orden
      WHERE e.vigencia = 'Vigente' AND e.estado != 'Procesada'
        ${q ? "AND (e.id_orden LIKE ? OR a.descripcion_articulo_producido LIKE ?)" : ''}
      GROUP BY e.id_orden, e.estado, e.fecha_final
      ORDER BY e.id_orden DESC
      LIMIT 30
    `, q ? [`%${q}%`, `%${q}%`] : [])
    res.json({ ok: true, ops: rows })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/op/:id_op  — detalle de una OP
app.get('/api/gestion/op/:id_op', async (req, res) => {
  try {
    const [[op]] = await db.integracion.query(`
      SELECT e.id_orden, e.estado, e.vigencia, e.nombre_encargado,
             e.fecha_inicial, e.fecha_final,
             GROUP_CONCAT(DISTINCT a.descripcion_articulo_producido
               ORDER BY a.descripcion_articulo_producido SEPARATOR ' / ') AS articulos
      FROM zeffi_produccion_encabezados e
      LEFT JOIN zeffi_articulos_producidos a ON a.id_orden = e.id_orden
      WHERE e.id_orden = ?
      GROUP BY e.id_orden, e.estado, e.vigencia, e.nombre_encargado, e.fecha_inicial, e.fecha_final
    `, [req.params.id_op])
    if (!op) return res.status(404).json({ error: 'OP no encontrada' })
    res.json({ ok: true, op })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/op/:id_op/pdf — descarga PDF de la OP via Playwright
app.get('/api/gestion/op/:id_op/pdf', requireAuth, (req, res) => {
  const idOp   = req.params.id_op.replace(/[^0-9]/g, '')  // solo números
  if (!idOp) return res.status(400).json({ error: 'ID inválido' })

  const tmpPdf  = `/tmp/op_${idOp}_${Date.now()}.pdf`
  const script  = '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/get_op_pdf.js'
  const node    = process.execPath

  res.setTimeout(90000)  // 90s timeout para Playwright

  execFile(node, [script, idOp, tmpPdf], { timeout: 85000 }, (err, stdout, stderr) => {
    if (err || !fs.existsSync(tmpPdf)) {
      console.error('PDF error:', err?.message || stderr)
      return res.status(500).json({ error: 'No se pudo generar el PDF', detalle: err?.message })
    }
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `inline; filename="OP_${idOp}.pdf"`)
    const stream = fs.createReadStream(tmpPdf)
    stream.pipe(res)
    stream.on('close', () => fs.unlink(tmpPdf, () => {}))  // limpiar tmp
  })
})

// ─── DIFICULTADES ─────────────────────────────────────────────────

app.get('/api/gestion/dificultades', async (req, res) => {
  const { estado, categoria, prioridad } = req.query
  const where  = ['empresa = ?']
  const params = [req.empresa]
  if (estado)    { where.push('estado = ?');    params.push(estado) }
  if (categoria) { where.push('categoria = ?'); params.push(categoria) }
  if (prioridad) { where.push('prioridad = ?'); params.push(prioridad) }
  try {
    const [rows] = await db.gestion.query(
      `SELECT * FROM g_dificultades WHERE ${where.join(' AND ')} ORDER BY FIELD(prioridad,'Urgente','Alta','Media','Baja'), fecha_creacion DESC`,
      params
    )
    res.json({ ok: true, dificultades: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.get('/api/gestion/dificultades/:id', async (req, res) => {
  try {
    const [[row]] = await db.gestion.query(
      'SELECT * FROM g_dificultades WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!row) return res.status(404).json({ error: 'No encontrada' })
    res.json({ ok: true, dificultad: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/gestion/dificultades', async (req, res) => {
  const { titulo, descripcion, estrategia, categoria, estado, prioridad } = req.body
  if (!titulo) return res.status(400).json({ error: 'Falta titulo' })
  try {
    const [r] = await db.gestion.query(
      'INSERT INTO g_dificultades (empresa, titulo, descripcion, estrategia, categoria, estado, prioridad, usuario_creador, usuario_ult_modificacion) VALUES (?,?,?,?,?,?,?,?,?)',
      [req.empresa, titulo, descripcion||null, estrategia||null, categoria||null, estado||'Abierta', prioridad||'Media', req.usuario.email, req.usuario.email]
    )
    const [[row]] = await db.gestion.query('SELECT * FROM g_dificultades WHERE id = ?', [r.insertId])
    res.status(201).json({ ok: true, dificultad: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.put('/api/gestion/dificultades/:id', async (req, res) => {
  const { titulo, descripcion, estrategia, categoria, estado, prioridad } = req.body
  const sets = []; const params = []
  if (titulo      !== undefined) { sets.push('titulo = ?');      params.push(titulo) }
  if (descripcion !== undefined) { sets.push('descripcion = ?'); params.push(descripcion) }
  if (estrategia  !== undefined) { sets.push('estrategia = ?');  params.push(estrategia) }
  if (categoria   !== undefined) { sets.push('categoria = ?');   params.push(categoria) }
  if (estado      !== undefined) { sets.push('estado = ?');      params.push(estado) }
  if (prioridad   !== undefined) { sets.push('prioridad = ?');   params.push(prioridad) }
  if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })
  sets.push('usuario_ult_modificacion = ?'); params.push(req.usuario.email)
  params.push(req.params.id, req.empresa)
  try {
    await db.gestion.query(`UPDATE g_dificultades SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    const [[row]] = await db.gestion.query('SELECT * FROM g_dificultades WHERE id = ?', [req.params.id])
    res.json({ ok: true, dificultad: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.delete('/api/gestion/dificultades/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_dificultades WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── IDEAS Y HECHOS ───────────────────────────────────────────────

app.get('/api/gestion/ideas', async (req, res) => {
  const { tipo, categoria, prioridad, es_contenido } = req.query
  const where = ['empresa = ?']; const params = [req.empresa]
  if (tipo)        { where.push('tipo = ?');        params.push(tipo) }
  if (categoria)   { where.push('categoria = ?');   params.push(categoria) }
  if (prioridad)   { where.push('prioridad = ?');   params.push(prioridad) }
  if (es_contenido !== undefined) { where.push('es_contenido = ?'); params.push(es_contenido) }
  try {
    const [rows] = await db.gestion.query(
      `SELECT * FROM g_ideas_hechos WHERE ${where.join(' AND ')} ORDER BY FIELD(prioridad,'Urgente','Alta','Media','Baja'), fecha_creacion DESC`,
      params
    )
    res.json({ ok: true, ideas: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.get('/api/gestion/ideas/:id', async (req, res) => {
  try {
    const [[row]] = await db.gestion.query('SELECT * FROM g_ideas_hechos WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    if (!row) return res.status(404).json({ error: 'No encontrada' })
    res.json({ ok: true, idea: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/gestion/ideas', async (req, res) => {
  const { titulo, tipo, descripcion, categoria, prioridad, es_contenido, pilar_contenido, tipo_contenido, fecha } = req.body
  if (!titulo || !tipo) return res.status(400).json({ error: 'Faltan titulo y tipo' })
  try {
    const [r] = await db.gestion.query(
      'INSERT INTO g_ideas_hechos (empresa, titulo, tipo, prioridad, descripcion, categoria, es_contenido, pilar_contenido, tipo_contenido, fecha, usuario_creador, usuario_ult_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
      [req.empresa, titulo, tipo, prioridad||'Media', descripcion||null, categoria||null, es_contenido||0, pilar_contenido||null, tipo_contenido||null, fecha||null, req.usuario.email, req.usuario.email]
    )
    const [[row]] = await db.gestion.query('SELECT * FROM g_ideas_hechos WHERE id = ?', [r.insertId])
    res.status(201).json({ ok: true, idea: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.put('/api/gestion/ideas/:id', async (req, res) => {
  const { titulo, tipo, descripcion, categoria, prioridad, es_contenido, pilar_contenido, tipo_contenido, fecha } = req.body
  const sets = []; const params = []
  if (titulo          !== undefined) { sets.push('titulo = ?');          params.push(titulo) }
  if (tipo            !== undefined) { sets.push('tipo = ?');            params.push(tipo) }
  if (descripcion     !== undefined) { sets.push('descripcion = ?');     params.push(descripcion) }
  if (categoria       !== undefined) { sets.push('categoria = ?');       params.push(categoria) }
  if (prioridad       !== undefined) { sets.push('prioridad = ?');       params.push(prioridad) }
  if (es_contenido    !== undefined) { sets.push('es_contenido = ?');    params.push(es_contenido) }
  if (pilar_contenido !== undefined) { sets.push('pilar_contenido = ?'); params.push(pilar_contenido) }
  if (tipo_contenido  !== undefined) { sets.push('tipo_contenido = ?');  params.push(tipo_contenido) }
  if (fecha           !== undefined) { sets.push('fecha = ?');           params.push(fecha) }
  if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })
  sets.push('usuario_ult_modificacion = ?'); params.push(req.usuario.email)
  params.push(req.params.id, req.empresa)
  try {
    await db.gestion.query(`UPDATE g_ideas_hechos SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    const [[row]] = await db.gestion.query('SELECT * FROM g_ideas_hechos WHERE id = ?', [req.params.id])
    res.json({ ok: true, idea: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.delete('/api/gestion/ideas/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_ideas_hechos WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── PENDIENTES ───────────────────────────────────────────────────

app.get('/api/gestion/pendientes', async (req, res) => {
  const { estado, categoria, prioridad, responsable } = req.query
  const where = ['empresa = ?']; const params = [req.empresa]
  if (estado)      { where.push('estado = ?');      params.push(estado) }
  if (categoria)   { where.push('categoria = ?');   params.push(categoria) }
  if (prioridad)   { where.push('prioridad = ?');   params.push(prioridad) }
  if (responsable) { where.push('responsable = ?'); params.push(responsable) }
  try {
    const [rows] = await db.gestion.query(
      `SELECT * FROM g_pendientes WHERE ${where.join(' AND ')} ORDER BY FIELD(prioridad,'Urgente','Alta','Media','Baja'), fecha_limite ASC, fecha_creacion DESC`,
      params
    )
    res.json({ ok: true, pendientes: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.get('/api/gestion/pendientes/:id', async (req, res) => {
  try {
    const [[row]] = await db.gestion.query('SELECT * FROM g_pendientes WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    if (!row) return res.status(404).json({ error: 'No encontrado' })
    res.json({ ok: true, pendiente: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/gestion/pendientes', async (req, res) => {
  const { titulo, descripcion, categoria, responsable, estado, prioridad, fecha_limite } = req.body
  if (!titulo) return res.status(400).json({ error: 'Falta titulo' })
  try {
    const [r] = await db.gestion.query(
      'INSERT INTO g_pendientes (empresa, titulo, descripcion, categoria, responsable, estado, prioridad, fecha_limite, usuario_creador, usuario_ult_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?)',
      [req.empresa, titulo, descripcion||null, categoria||null, responsable||null, estado||'Pendiente', prioridad||'Media', fecha_limite||null, req.usuario.email, req.usuario.email]
    )
    const [[row]] = await db.gestion.query('SELECT * FROM g_pendientes WHERE id = ?', [r.insertId])
    res.status(201).json({ ok: true, pendiente: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.put('/api/gestion/pendientes/:id', async (req, res) => {
  const { titulo, descripcion, categoria, responsable, estado, prioridad, fecha_limite, fecha_completado } = req.body
  const sets = []; const params = []
  if (titulo           !== undefined) { sets.push('titulo = ?');           params.push(titulo) }
  if (descripcion      !== undefined) { sets.push('descripcion = ?');      params.push(descripcion) }
  if (categoria        !== undefined) { sets.push('categoria = ?');        params.push(categoria) }
  if (responsable      !== undefined) { sets.push('responsable = ?');      params.push(responsable) }
  if (estado           !== undefined) { sets.push('estado = ?');           params.push(estado) }
  if (prioridad        !== undefined) { sets.push('prioridad = ?');        params.push(prioridad) }
  if (fecha_limite     !== undefined) { sets.push('fecha_limite = ?');     params.push(fecha_limite) }
  if (fecha_completado !== undefined) { sets.push('fecha_completado = ?'); params.push(fecha_completado) }
  if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })
  sets.push('usuario_ult_modificacion = ?'); params.push(req.usuario.email)
  params.push(req.params.id, req.empresa)
  try {
    await db.gestion.query(`UPDATE g_pendientes SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    const [[row]] = await db.gestion.query('SELECT * FROM g_pendientes WHERE id = ?', [req.params.id])
    res.json({ ok: true, pendiente: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.delete('/api/gestion/pendientes/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_pendientes WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── INFORMES ─────────────────────────────────────────────────────

app.get('/api/gestion/informes', async (req, res) => {
  const { tipo } = req.query
  const where = ['empresa = ?']; const params = [req.empresa]
  if (tipo) { where.push('tipo = ?'); params.push(tipo) }
  try {
    const [rows] = await db.gestion.query(
      `SELECT id, empresa, nombre, tipo, fecha_informe, usuario_creador, fecha_creacion FROM g_informes WHERE ${where.join(' AND ')} ORDER BY fecha_informe DESC`,
      params
    )
    res.json({ ok: true, informes: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.get('/api/gestion/informes/:id', async (req, res) => {
  try {
    const [[row]] = await db.gestion.query('SELECT * FROM g_informes WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    if (!row) return res.status(404).json({ error: 'No encontrado' })
    res.json({ ok: true, informe: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.post('/api/gestion/informes', async (req, res) => {
  const { nombre, tipo, fecha_informe, contenido } = req.body
  if (!nombre || !tipo) return res.status(400).json({ error: 'Faltan nombre y tipo' })
  try {
    const [r] = await db.gestion.query(
      'INSERT INTO g_informes (empresa, nombre, tipo, fecha_informe, contenido, usuario_creador, usuario_ult_modificacion) VALUES (?,?,?,?,?,?,?)',
      [req.empresa, nombre, tipo, fecha_informe||null, contenido||null, req.usuario.email, req.usuario.email]
    )
    const [[row]] = await db.gestion.query('SELECT * FROM g_informes WHERE id = ?', [r.insertId])
    res.status(201).json({ ok: true, informe: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.put('/api/gestion/informes/:id', async (req, res) => {
  const { nombre, tipo, fecha_informe, contenido } = req.body
  const sets = []; const params = []
  if (nombre        !== undefined) { sets.push('nombre = ?');        params.push(nombre) }
  if (tipo          !== undefined) { sets.push('tipo = ?');          params.push(tipo) }
  if (fecha_informe !== undefined) { sets.push('fecha_informe = ?'); params.push(fecha_informe) }
  if (contenido     !== undefined) { sets.push('contenido = ?');     params.push(contenido) }
  if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })
  sets.push('usuario_ult_modificacion = ?'); params.push(req.usuario.email)
  params.push(req.params.id, req.empresa)
  try {
    await db.gestion.query(`UPDATE g_informes SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    const [[row]] = await db.gestion.query('SELECT * FROM g_informes WHERE id = ?', [req.params.id])
    res.json({ ok: true, informe: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

app.delete('/api/gestion/informes/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_informes WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── PROYECTOS ────────────────────────────────────────────────────

// GET /api/gestion/proyectos — lista proyectos de la empresa
app.get('/api/gestion/proyectos', async (req, res) => {
  const { estado } = req.query
  const where  = ['p.empresa = ?']
  const params = [req.empresa]
  if (estado) { where.push('p.estado = ?'); params.push(estado) }

  try {
    const [proyectos] = await db.gestion.query(`
      SELECT p.*,
        c.nombre AS categoria_nombre, c.color AS categoria_color,
        (SELECT COUNT(*) FROM g_tareas t WHERE t.proyecto_id = p.id AND t.estado NOT IN ('Completada','Cancelada')) AS tareas_pendientes,
        (SELECT GROUP_CONCAT(pr.email SEPARATOR ',') FROM g_proyectos_responsables pr WHERE pr.proyecto_id = p.id) AS responsables_csv,
        (SELECT JSON_ARRAYAGG(JSON_OBJECT('id', e.id, 'nombre', e.nombre, 'color', e.color))
         FROM g_etiquetas_proyectos ep JOIN g_etiquetas e ON e.id = ep.etiqueta_id
         WHERE ep.proyecto_id = p.id) AS etiquetas_json
      FROM g_proyectos p
      LEFT JOIN g_categorias c ON c.id = p.categoria_id
      WHERE ${where.join(' AND ')}
      ORDER BY p.fecha_creacion DESC
    `, params)

    const result = proyectos.map(p => ({
      ...p,
      responsables: p.responsables_csv ? p.responsables_csv.split(',') : [],
      etiquetas:    p.etiquetas_json ? (typeof p.etiquetas_json === 'string' ? JSON.parse(p.etiquetas_json) : p.etiquetas_json) : []
    }))

    res.json({ ok: true, proyectos: result })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/proyectos/:id
app.get('/api/gestion/proyectos/:id', async (req, res) => {
  try {
    const [[proyecto]] = await db.gestion.query(`
      SELECT p.*, c.nombre AS categoria_nombre, c.color AS categoria_color
      FROM g_proyectos p
      LEFT JOIN g_categorias c ON c.id = p.categoria_id
      WHERE p.id = ? AND p.empresa = ?
    `, [req.params.id, req.empresa])

    if (!proyecto) return res.status(404).json({ error: 'Proyecto no encontrado' })

    const [responsables] = await db.gestion.query(
      'SELECT email FROM g_proyectos_responsables WHERE proyecto_id = ?', [req.params.id]
    )
    const [etiquetas] = await db.gestion.query(`
      SELECT e.id, e.nombre, e.color
      FROM g_etiquetas_proyectos ep JOIN g_etiquetas e ON e.id = ep.etiqueta_id
      WHERE ep.proyecto_id = ?
    `, [req.params.id])

    res.json({ ok: true, proyecto: {
      ...proyecto,
      responsables: responsables.map(r => r.email),
      etiquetas
    }})
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/gestion/proyectos
app.post('/api/gestion/proyectos', async (req, res) => {
  const { nombre, descripcion, color, categoria_id, prioridad, estado,
          fecha_estimada_fin, responsables, etiquetas } = req.body

  if (!nombre) return res.status(400).json({ error: 'Falta nombre del proyecto' })

  try {
    const [result] = await db.gestion.query(`
      INSERT INTO g_proyectos
        (empresa, nombre, descripcion, color, categoria_id, prioridad, estado,
         fecha_estimada_fin, usuario_creador, usuario_ult_modificacion)
      VALUES (?,?,?,?,?,?,?,?,?,?)
    `, [
      req.empresa, nombre, descripcion||null, color||'#607D8B',
      categoria_id||null, prioridad||'Media', estado||'Activo',
      fecha_estimada_fin||null, req.usuario.email, req.usuario.email
    ])

    const pid = result.insertId

    // Responsables
    if (responsables && Array.isArray(responsables) && responsables.length > 0) {
      const vals = responsables.map(e => [pid, e])
      await db.gestion.query('INSERT IGNORE INTO g_proyectos_responsables (proyecto_id, email) VALUES ?', [vals])
    } else {
      await db.gestion.query('INSERT IGNORE INTO g_proyectos_responsables (proyecto_id, email) VALUES (?,?)', [pid, req.usuario.email])
    }

    // Etiquetas
    if (etiquetas && Array.isArray(etiquetas) && etiquetas.length > 0) {
      const vals = etiquetas.map(eid => [pid, eid])
      await db.gestion.query('INSERT IGNORE INTO g_etiquetas_proyectos (proyecto_id, etiqueta_id) VALUES ?', [vals])
    }

    const [[proyecto]] = await db.gestion.query(
      'SELECT p.*, c.nombre AS categoria_nombre, c.color AS categoria_color FROM g_proyectos p LEFT JOIN g_categorias c ON c.id = p.categoria_id WHERE p.id = ?',
      [pid]
    )
    const [resps] = await db.gestion.query('SELECT email FROM g_proyectos_responsables WHERE proyecto_id = ?', [pid])
    res.status(201).json({ ok: true, proyecto: { ...proyecto, responsables: resps.map(r=>r.email) } })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/proyectos/:id
app.put('/api/gestion/proyectos/:id', async (req, res) => {
  const { nombre, descripcion, color, categoria_id, prioridad, estado,
          fecha_estimada_fin, fecha_finalizacion_real, responsables, etiquetas } = req.body

  try {
    const sets = []; const params = []
    if (nombre            !== undefined) { sets.push('nombre = ?');            params.push(nombre) }
    if (descripcion       !== undefined) { sets.push('descripcion = ?');       params.push(descripcion) }
    if (color             !== undefined) { sets.push('color = ?');             params.push(color) }
    if (categoria_id      !== undefined) { sets.push('categoria_id = ?');      params.push(categoria_id) }
    if (prioridad         !== undefined) { sets.push('prioridad = ?');         params.push(prioridad) }
    if (estado            !== undefined) { sets.push('estado = ?');            params.push(estado) }
    if (fecha_estimada_fin     !== undefined) { sets.push('fecha_estimada_fin = ?');     params.push(fecha_estimada_fin) }
    if (fecha_finalizacion_real !== undefined) { sets.push('fecha_finalizacion_real = ?'); params.push(fecha_finalizacion_real) }

    if (sets.length) {
      sets.push('usuario_ult_modificacion = ?'); params.push(req.usuario.email)
      params.push(req.params.id, req.empresa)
      await db.gestion.query(`UPDATE g_proyectos SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    }

    // Responsables (reemplaza todos)
    if (responsables !== undefined && Array.isArray(responsables)) {
      await db.gestion.query('DELETE FROM g_proyectos_responsables WHERE proyecto_id = ?', [req.params.id])
      if (responsables.length > 0) {
        const vals = responsables.map(e => [req.params.id, e])
        await db.gestion.query('INSERT IGNORE INTO g_proyectos_responsables (proyecto_id, email) VALUES ?', [vals])
      }
    }

    // Etiquetas (reemplaza todas)
    if (etiquetas !== undefined && Array.isArray(etiquetas)) {
      await db.gestion.query('DELETE FROM g_etiquetas_proyectos WHERE proyecto_id = ?', [req.params.id])
      if (etiquetas.length > 0) {
        const vals = etiquetas.map(eid => [req.params.id, eid])
        await db.gestion.query('INSERT IGNORE INTO g_etiquetas_proyectos (proyecto_id, etiqueta_id) VALUES ?', [vals])
      }
    }

    const [[proyecto]] = await db.gestion.query(
      'SELECT p.*, c.nombre AS categoria_nombre, c.color AS categoria_color FROM g_proyectos p LEFT JOIN g_categorias c ON c.id = p.categoria_id WHERE p.id = ?',
      [req.params.id]
    )
    const [resps] = await db.gestion.query('SELECT email FROM g_proyectos_responsables WHERE proyecto_id = ?', [req.params.id])
    res.json({ ok: true, proyecto: { ...proyecto, responsables: resps.map(r=>r.email) } })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// DELETE /api/gestion/proyectos/:id
app.delete('/api/gestion/proyectos/:id', async (req, res) => {
  try {
    // Desanclar las tareas (proyecto_id → null) antes de eliminar
    await db.gestion.query('UPDATE g_tareas SET proyecto_id = NULL WHERE proyecto_id = ? AND empresa = ?', [req.params.id, req.empresa])
    await db.gestion.query('DELETE FROM g_proyectos WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── ETIQUETAS ────────────────────────────────────────────────────

// GET /api/gestion/etiquetas
app.get('/api/gestion/etiquetas', async (req, res) => {
  try {
    const [etiquetas] = await db.gestion.query(
      'SELECT * FROM g_etiquetas WHERE empresa = ? ORDER BY nombre',
      [req.empresa]
    )
    res.json({ ok: true, etiquetas })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/gestion/etiquetas
app.post('/api/gestion/etiquetas', async (req, res) => {
  const { nombre, color } = req.body
  if (!nombre) return res.status(400).json({ error: 'Falta nombre' })
  try {
    const [r] = await db.gestion.query(
      'INSERT INTO g_etiquetas (empresa, nombre, color, usuario_creador) VALUES (?,?,?,?)',
      [req.empresa, nombre.trim(), color||null, req.usuario.email]
    )
    const [[etiqueta]] = await db.gestion.query('SELECT * FROM g_etiquetas WHERE id = ?', [r.insertId])
    res.status(201).json({ ok: true, etiqueta })
  } catch (e) {
    if (e.code === 'ER_DUP_ENTRY') return res.status(409).json({ error: 'Ya existe esa etiqueta' })
    res.status(500).json({ error: e.message })
  }
})

// PUT /api/gestion/etiquetas/:id
app.put('/api/gestion/etiquetas/:id', async (req, res) => {
  const { nombre, color } = req.body
  const sets = []; const params = []
  if (nombre !== undefined) { sets.push('nombre = ?'); params.push(nombre.trim()) }
  if (color  !== undefined) { sets.push('color = ?');  params.push(color) }
  if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })
  params.push(req.params.id, req.empresa)
  try {
    await db.gestion.query(`UPDATE g_etiquetas SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)
    const [[etiqueta]] = await db.gestion.query('SELECT * FROM g_etiquetas WHERE id = ?', [req.params.id])
    res.json({ ok: true, etiqueta })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// DELETE /api/gestion/etiquetas/:id
app.delete('/api/gestion/etiquetas/:id', async (req, res) => {
  try {
    await db.gestion.query('DELETE FROM g_etiquetas WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
    res.json({ ok: true })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── Fallback SPA ──────────────────────────────────────────────────
app.use((req, res) => {
  const spa = path.join(__dirname, '../app/dist/spa/index.html')
  if (fs.existsSync(spa)) return res.sendFile(spa)
  res.status(404).json({ error: 'Frontend no desplegado aún' })
})

// ─── Arrancar ─────────────────────────────────────────────────────
async function arrancar() {
  try {
    console.log('[server] Conectando SSH tunnel → Hostinger...')
    await db.conectar()
    console.log('[server] Pools MySQL listos (comunidad / gestion / integracion)')

    app.listen(PORT, () => {
      console.log(`[server] OS Gestión API corriendo en puerto ${PORT}`)
    })
  } catch (e) {
    console.error('[server] Error al iniciar:', e.message)
    process.exit(1)
  }
}

arrancar()
