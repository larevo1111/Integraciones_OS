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
const crypto   = require('crypto')
const jwt      = require('jsonwebtoken')
const multer   = require('multer')
const { execFile } = require('child_process')
const db      = require('./db')

// ─── Upload config ─────────────────────────────────────────────────
const SUBIDOS_ROOT  = '/home/osserver/subidos'
const MIME_PERMITIDOS = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf']
const MAX_SIZE = 10 * 1024 * 1024 // 10 MB
const upload = multer({ dest: '/tmp/gestion-uploads/', limits: { fileSize: MAX_SIZE } })

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

/** Fecha YYYY-MM-DD en hora Colombia (UTC-5), sin depender de la zona del server */
function localDateCO(d = new Date()) {
  const y = d.toLocaleDateString('en-CA', { timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit' })
  return y // en-CA ya devuelve YYYY-MM-DD
}

if (!GOOGLE_CLIENT_ID || !JWT_SECRET) {
  console.error('ERROR: Faltan GOOGLE_CLIENT_ID o JWT_SECRET en .env')
  process.exit(1)
}

// ─── CACHÉ DE NIVELES DE USUARIO ──────────────────────────────────
// Se carga al iniciar y se refresca cada 5 minutos
const nivelCache = {}  // { 'email@...': nivel }

async function refrescarNiveles() {
  try {
    const [rows] = await db.comunidad.query('SELECT `Email` AS email, `Nivel_Acceso` AS nivel FROM sys_usuarios')
    for (const r of rows) nivelCache[r.email] = r.nivel || 1
    console.log(`[niveles] Caché actualizado: ${rows.length} usuarios`)
  } catch (e) {
    console.error('[niveles] Error refrescando caché:', e.message)
    // Mantener caché anterior — fallback seguro
  }
}

function filtrarPorNivel(items, reqUsuario, campoResponsables = 'responsables') {
  const miEmail = reqUsuario.email
  const miNivel = reqUsuario.nivel || nivelCache[miEmail] || 1
  return items.filter(item => {
    const responsables = item[campoResponsables]
    if (!responsables || !responsables.length) return true  // sin responsable → visible para todos
    return responsables.some(email =>
      email === miEmail || (nivelCache[email] || 1) < miNivel
    )
  })
}

// Inicializar caché después de que DB esté lista (ver al final del archivo)

const app = express()
app.use(express.json())
// sw.js e index.html sin caché para que el PWA se actualice
app.use((req, res, next) => {
  if (req.path === '/sw.js' || req.path === '/index.html' || req.path === '/') {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
  }
  next()
})
app.use(express.static(path.join(__dirname, 'public')))
app.use('/subidos', express.static(SUBIDOS_ROOT))

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

    const usuarioFinal = {
      email:   decoded.email,
      nombre:  decoded.nombre,
      foto:    decoded.foto || '',
      nivel:   decoded.nivel,
      tema:    config?.tema   || 'dark',
      perfil:  config?.perfil || null
    }
    res.json({ ok: true, token: newToken, usuario: usuarioFinal,
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
        SELECT c.id, c.nombre, c.color, c.icono, c.es_produccion, c.es_empaque, c.orden
        FROM g_categorias c
        JOIN g_categorias_perfiles cp ON cp.categoria_id = c.id
        JOIN g_perfiles p ON p.id = cp.perfil_id
        WHERE c.activa = 1 AND p.nombre = ?
        ORDER BY c.orden
      `, [perfil])
    } else {
      // Sin perfil → todas
      ;[rows] = await db.gestion.query(
        'SELECT id, nombre, color, icono, es_produccion, es_empaque, orden FROM g_categorias WHERE activa = 1 ORDER BY orden'
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

  // Filtro de fecha — siempre usar fecha Colombia via localDateCO()
  const hoyRef = fecha_hoy || localDateCO()
  function fechaRefOffset(dias) {
    const d = new Date(hoyRef + 'T00:00:00')
    d.setDate(d.getDate() + dias)
    return localDateCO(d)
  }

  if (filtro === 'hoy') {
    where.push('t.fecha_limite = ?'); params.push(hoyRef)
  } else if (filtro === 'manana') {
    where.push('t.fecha_limite = ?'); params.push(fechaRefOffset(1))
  } else if (filtro === 'ayer') {
    where.push('t.fecha_limite = ?'); params.push(fechaRefOffset(-1))
  } else if (filtro === 'semana') {
    const d   = new Date(hoyRef + 'T00:00:00')
    const dow = d.getDay() === 0 ? 6 : d.getDay() - 1  // lunes=0
    const lun = new Date(d); lun.setDate(d.getDate() - dow)
    const dom = new Date(lun); dom.setDate(lun.getDate() + 6)
    where.push('t.fecha_limite BETWEEN ? AND ?')
    params.push(localDateCO(lun), localDateCO(dom))
  }

  // Filtros adicionales (simples)
  if (responsable)  { where.push('EXISTS (SELECT 1 FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id AND tr.email = ?)'); params.push(responsable) }
  if (solo_mias === '1') { where.push('EXISTS (SELECT 1 FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id AND tr.email = ?)'); params.push(req.usuario.email) }
  if (estado)       { where.push('t.estado = ?');        params.push(estado) }

  // responsables: multi (comma-separated emails)
  const responsablesRaw = req.query.responsables
  if (responsablesRaw) {
    const emails = String(responsablesRaw).split(',').map(s => s.trim()).filter(Boolean)
    if (emails.length > 0) {
      where.push(`EXISTS (SELECT 1 FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id AND tr.email IN (${emails.map(() => '?').join(',')}))`)
      params.push(...emails)
    }
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
        t.id_op, t.id_remision, t.id_pedido, t.tiempo_real_min, t.tiempo_estimado_min, t.notas,
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
         WHERE et.tarea_id = t.id) AS etiquetas_json,
        (SELECT GROUP_CONCAT(tr.email SEPARATOR ',') FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id) AS responsables_csv
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

    // Enriquecer con nombres de responsables
    const allEmails = [...new Set(tareasBase.flatMap(t => (t.responsables_csv || '').split(',').filter(Boolean)))]
    let nombreMap = {}
    if (allEmails.length) {
      try {
        const [users] = await db.comunidad.query(
          `SELECT \`Email\` AS email, \`Nombre_Usuario\` AS nombre FROM sys_usuarios WHERE \`Email\` IN (${allEmails.map(() => '?').join(',')})`,
          allEmails
        )
        nombreMap = Object.fromEntries(users.map(u => [u.email, u.nombre]))
      } catch {}
    }
    const tareasFinales = tareasBase.map(t => {
      const responsables = t.responsables_csv ? t.responsables_csv.split(',') : []
      return {
        ...t,
        responsables,
        responsable_nombre: nombreMap[t.responsable] || null,
        responsables_nombres: responsables.map(e => nombreMap[e] || e.split('@')[0])
      }
    })

    res.json({ ok: true, tareas: filtrarPorNivel(tareasFinales, req.usuario) })
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
  if (responsable)  { where.push('EXISTS (SELECT 1 FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id AND tr.email = ?)'); params.push(responsable) }
  if (proyecto_id)  { where.push('t.proyecto_id = ?');  params.push(proyecto_id) }
  if (solo_mias === '1') { where.push('EXISTS (SELECT 1 FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id AND tr.email = ?)'); params.push(req.usuario.email) }

  try {
    const [tareasBase] = await db.gestion.query(`
      SELECT t.id, t.titulo, t.estado, t.prioridad, t.responsable,
             t.categoria_id, c.nombre AS categoria_nombre, c.color AS categoria_color,
             t.fecha_limite, t.fecha_fin_real, t.tiempo_real_min,
             t.usuario_creador, t.fecha_ult_modificacion,
             (SELECT GROUP_CONCAT(tr.email SEPARATOR ',') FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id) AS responsables_csv
      FROM g_tareas t
      JOIN g_categorias c ON c.id = t.categoria_id
      WHERE ${where.join(' AND ')}
      ORDER BY t.fecha_ult_modificacion DESC
      LIMIT 50
    `, params)
    const allEmails = [...new Set(tareasBase.flatMap(t => (t.responsables_csv || '').split(',').filter(Boolean)))]
    let nombreMap = {}
    if (allEmails.length) {
      try {
        const [users] = await db.comunidad.query(
          `SELECT \`Email\` AS email, \`Nombre_Usuario\` AS nombre FROM sys_usuarios WHERE \`Email\` IN (${allEmails.map(() => '?').join(',')})`,
          allEmails
        )
        nombreMap = Object.fromEntries(users.map(u => [u.email, u.nombre]))
      } catch {}
    }
    const tareas = tareasBase.map(t => {
      const responsables = t.responsables_csv ? t.responsables_csv.split(',') : []
      return { ...t, responsables, responsable_nombre: nombreMap[t.responsable] || null }
    })
    res.json({ ok: true, tareas: filtrarPorNivel(tareas, req.usuario) })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/gestion/tareas/:id
app.get('/api/gestion/tareas/:id', async (req, res) => {
  try {
    const [[tarea]] = await db.gestion.query(`
      SELECT t.*, c.nombre AS categoria_nombre, c.color AS categoria_color,
             c.icono AS categoria_icono, c.es_produccion, c.es_empaque,
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

    // Responsables de la tarea
    const [resps] = await db.gestion.query(
      'SELECT email FROM g_tareas_responsables WHERE tarea_id = ?', [req.params.id]
    )

    res.json({ ok: true, tarea: { ...tarea, tiempos, etiquetas, responsables: resps.map(r => r.email) } })
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
             (SELECT tt.inicio FROM g_tarea_tiempo tt WHERE tt.tarea_id = t.id AND tt.fin IS NULL LIMIT 1) AS cronometro_inicio,
             (SELECT GROUP_CONCAT(tr.email SEPARATOR ',') FROM g_tareas_responsables tr WHERE tr.tarea_id = t.id) AS responsables_csv
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
    const subsFinal = subtareas.map(t => ({
      ...t,
      responsables: t.responsables_csv ? t.responsables_csv.split(',') : [],
      responsable_nombre: nombreMap[t.responsable] || null
    }))
    res.json({ ok: true, subtareas: filtrarPorNivel(subsFinal, req.usuario) })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// POST /api/gestion/tareas
app.post('/api/gestion/tareas', async (req, res) => {
  const {
    titulo, descripcion, categoria_id, proyecto_id, prioridad, responsable, responsables,
    fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
    tiempo_estimado_min, id_op, id_remision, id_pedido, notas, etiquetas, parent_id
  } = req.body

  if (!titulo || !categoria_id) return res.status(400).json({ error: 'Faltan titulo y categoria_id' })

  // Determinar responsable principal (legacy) y lista de responsables
  const listaResps = Array.isArray(responsables) && responsables.length > 0
    ? responsables
    : (responsable ? [responsable] : [req.usuario.email])
  const respPrincipal = listaResps[0]

  try {
    const [result] = await db.gestion.query(`
      INSERT INTO g_tareas
        (empresa, parent_id, titulo, descripcion, categoria_id, proyecto_id, prioridad, responsable,
         fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
         tiempo_estimado_min, id_op, id_remision, id_pedido, notas, usuario_creador, usuario_ult_modificacion)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      req.empresa, parent_id || null,
      titulo, descripcion || null, categoria_id,
      proyecto_id || null,
      prioridad || 'Media',
      respPrincipal,
      fecha_limite || null,
      fecha_inicio_estimada || fecha_limite || null,
      fecha_fin_estimada    || fecha_limite || null,
      tiempo_estimado_min || null,
      id_op || null, id_remision || null, id_pedido || null, notas || null,
      req.usuario.email, req.usuario.email
    ])

    const tareaId = result.insertId

    // Insertar responsables en tabla relacional
    const valsResps = listaResps.map(e => [tareaId, e])
    await db.gestion.query('INSERT IGNORE INTO g_tareas_responsables (tarea_id, email) VALUES ?', [valsResps])

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
    res.status(201).json({ ok: true, tarea: { ...tarea, responsables: listaResps } })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// PUT /api/gestion/tareas/:id
app.put('/api/gestion/tareas/:id', async (req, res) => {
  const {
    titulo, descripcion, categoria_id, proyecto_id, estado, prioridad, responsable, responsables,
    fecha_limite, fecha_inicio_estimada, fecha_fin_estimada,
    fecha_inicio_real, fecha_fin_real,
    tiempo_real_min, tiempo_estimado_min, id_op, id_remision, id_pedido, notas, etiquetas
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
    if (id_remision      !== undefined) { sets.push('id_remision = ?');        params.push(id_remision) }
    if (id_pedido        !== undefined) { sets.push('id_pedido = ?');          params.push(id_pedido) }
    if (notas            !== undefined) { sets.push('notas = ?');              params.push(notas) }

    if (sets.length) {
      sets.push('usuario_ult_modificacion = ?')
      params.push(req.usuario.email)
      params.push(req.params.id, req.empresa)

      await db.gestion.query(
        `UPDATE g_tareas SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`,
        params
      )

      // Cascada a subtareas cuando cambia estado del padre
      if (estado === 'Completada') {
        await db.gestion.query(
          `UPDATE g_tareas SET estado='Completada', fecha_fin_real=COALESCE(fecha_fin_real, NOW()), usuario_ult_modificacion=?
           WHERE parent_id=? AND empresa=? AND estado NOT IN ('Completada','Cancelada')`,
          [req.usuario.email, req.params.id, req.empresa]
        )
      } else if (estado === 'Cancelada') {
        await db.gestion.query(
          `UPDATE g_tareas SET estado='Cancelada', usuario_ult_modificacion=?
           WHERE parent_id=? AND empresa=? AND estado NOT IN ('Completada','Cancelada')`,
          [req.usuario.email, req.params.id, req.empresa]
        )
      } else if (estado === 'Pendiente') {
        await db.gestion.query(
          `UPDATE g_tareas SET estado='Pendiente', fecha_fin_real=NULL, usuario_ult_modificacion=?
           WHERE parent_id=? AND empresa=? AND estado NOT IN ('Cancelada')`,
          [req.usuario.email, req.params.id, req.empresa]
        )
        // Si se resetea tiempo_real_min a 0 (revertir Completada→Pendiente), limpiar sesiones de cronómetro
        if (tiempo_real_min === 0) {
          await db.gestion.query('DELETE FROM g_tarea_tiempo WHERE tarea_id = ?', [req.params.id])
        }
      }
    }

    // Actualizar etiquetas (si se pasó el array — reemplaza todas)
    if (etiquetas !== undefined && Array.isArray(etiquetas)) {
      await db.gestion.query('DELETE FROM g_etiquetas_tareas WHERE tarea_id = ?', [req.params.id])
      if (etiquetas.length > 0) {
        const vals = etiquetas.map(eid => [req.params.id, eid])
        await db.gestion.query('INSERT IGNORE INTO g_etiquetas_tareas (tarea_id, etiqueta_id) VALUES ?', [vals])
      }
    }

    // Actualizar responsables (si se pasó el array — reemplaza todos)
    if (responsables !== undefined && Array.isArray(responsables)) {
      await db.gestion.query('DELETE FROM g_tareas_responsables WHERE tarea_id = ?', [req.params.id])
      if (responsables.length > 0) {
        const vals = responsables.map(e => [req.params.id, e])
        await db.gestion.query('INSERT IGNORE INTO g_tareas_responsables (tarea_id, email) VALUES ?', [vals])
        // Mantener legacy: primer responsable en campo directo
        await db.gestion.query('UPDATE g_tareas SET responsable = ? WHERE id = ?', [responsables[0], req.params.id])
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
    // Incluir etiquetas en la respuesta del PUT
    const [etiqPut] = await db.gestion.query(
      `SELECT e.id, e.nombre, e.color FROM g_etiquetas_tareas et
       JOIN g_etiquetas e ON e.id = et.etiqueta_id WHERE et.tarea_id = ?`,
      [req.params.id]
    )
    // Incluir responsables en la respuesta del PUT
    const [respsPut] = await db.gestion.query(
      'SELECT email FROM g_tareas_responsables WHERE tarea_id = ?', [req.params.id]
    )
    res.json({ ok: true, tarea: { ...tarea, etiquetas: etiqPut, responsables: respsPut.map(r => r.email) } })
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

    // Cerrar cualquier cronómetro abierto (seguridad) — new Date() → Colombia time vía timezone:'local'
    const ahoraIniciar = new Date()
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = ?, duracion_min = FLOOR(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [ahoraIniciar, ahoraIniciar, tareaId])

    // Iniciar nuevo registro
    const [result] = await db.gestion.query(
      'INSERT INTO g_tarea_tiempo (tarea_id, usuario, inicio) VALUES (?, ?, ?)',
      [tareaId, req.usuario.email, ahoraIniciar]
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
    // Cerrar registro abierto — new Date() → Colombia time vía timezone:'local'
    const ahoraDetener = new Date()
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = ?, duracion_min = FLOOR(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [ahoraDetener, ahoraDetener, tareaId])

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
      'UPDATE g_tarea_tiempo SET fin = ? WHERE tarea_id = ? AND fin IS NULL', [new Date(), tareaId]
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
    const ahoraCompletar = new Date()
    await db.gestion.query(`
      UPDATE g_tarea_tiempo
      SET fin = ?, duracion_min = FLOOR(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)
      WHERE tarea_id = ? AND fin IS NULL
    `, [ahoraCompletar, ahoraCompletar, tareaId])

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

    // Cascada: completar subtareas pendientes/en progreso
    await db.gestion.query(
      `UPDATE g_tareas SET estado='Completada', fecha_fin_real=COALESCE(fecha_fin_real, NOW()), usuario_ult_modificacion=?
       WHERE parent_id=? AND empresa=? AND estado NOT IN ('Completada','Cancelada')`,
      [req.usuario.email, tareaId, req.empresa]
    )

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

// ─── REMISIONES ───────────────────────────────────────────────────

// GET /api/gestion/remisiones — remisiones de venta (búsqueda)
app.get('/api/gestion/remisiones', async (req, res) => {
  const q = (req.query.q || '').trim()
  try {
    const [rows] = await db.integracion.query(`
      SELECT id_remision, cliente
      FROM zeffi_remisiones_venta_encabezados
      WHERE 1=1
        ${q ? "AND (id_remision LIKE ? OR cliente LIKE ?)" : ''}
      ORDER BY CAST(id_remision AS UNSIGNED) DESC
      LIMIT 30
    `, q ? [`%${q}%`, `%${q}%`] : [])
    res.json({ ok: true, remisiones: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/remision/:id — detalle de una remisión
app.get('/api/gestion/remision/:id', async (req, res) => {
  try {
    const [[row]] = await db.integracion.query(
      'SELECT id_remision, cliente FROM zeffi_remisiones_venta_encabezados WHERE id_remision = ? LIMIT 1',
      [req.params.id]
    )
    if (!row) return res.status(404).json({ error: 'Remisión no encontrada' })
    res.json({ ok: true, remision: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/remision/:id/pdf — PDF remisión via Playwright
app.get('/api/gestion/remision/:id/pdf', requireAuth, (req, res) => {
  const idRem = req.params.id.replace(/[^0-9]/g, '')
  if (!idRem) return res.status(400).json({ error: 'ID inválido' })
  const tmpPdf = `/tmp/remision_${idRem}_${Date.now()}.pdf`
  const script = '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/get_remision_pdf.js'
  res.setTimeout(90000)
  execFile(process.execPath, [script, idRem, tmpPdf], { timeout: 85000 }, (err) => {
    if (err || !fs.existsSync(tmpPdf)) {
      return res.status(500).json({ error: 'No se pudo generar el PDF', detalle: err?.message })
    }
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `inline; filename="Remision_${idRem}.pdf"`)
    const stream = fs.createReadStream(tmpPdf)
    stream.pipe(res)
    stream.on('close', () => fs.unlink(tmpPdf, () => {}))
  })
})

// ─── PEDIDOS (COTIZACIONES) ────────────────────────────────────────

// GET /api/gestion/pedidos — cotizaciones de venta (búsqueda)
app.get('/api/gestion/pedidos', async (req, res) => {
  const q = (req.query.q || '').trim()
  try {
    const [rows] = await db.integracion.query(`
      SELECT id_cotizacion, cliente
      FROM zeffi_cotizaciones_ventas_encabezados
      WHERE 1=1
        ${q ? "AND (id_cotizacion LIKE ? OR cliente LIKE ?)" : ''}
      ORDER BY CAST(id_cotizacion AS UNSIGNED) DESC
      LIMIT 30
    `, q ? [`%${q}%`, `%${q}%`] : [])
    res.json({ ok: true, pedidos: rows })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/pedido/:id — detalle de un pedido/cotización
app.get('/api/gestion/pedido/:id', async (req, res) => {
  try {
    const [[row]] = await db.integracion.query(
      'SELECT id_cotizacion, cliente FROM zeffi_cotizaciones_ventas_encabezados WHERE id_cotizacion = ? LIMIT 1',
      [req.params.id]
    )
    if (!row) return res.status(404).json({ error: 'Pedido no encontrado' })
    res.json({ ok: true, pedido: row })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/pedido/:id/pdf — PDF cotización via Playwright
app.get('/api/gestion/pedido/:id/pdf', requireAuth, (req, res) => {
  const idPed = req.params.id.replace(/[^0-9]/g, '')
  if (!idPed) return res.status(400).json({ error: 'ID inválido' })
  const tmpPdf = `/tmp/pedido_${idPed}_${Date.now()}.pdf`
  const script = '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/get_pedido_pdf.js'
  res.setTimeout(90000)
  execFile(process.execPath, [script, idPed, tmpPdf], { timeout: 85000 }, (err) => {
    if (err || !fs.existsSync(tmpPdf)) {
      return res.status(500).json({ error: 'No se pudo generar el PDF', detalle: err?.message })
    }
    res.setHeader('Content-Type', 'application/pdf')
    res.setHeader('Content-Disposition', `inline; filename="Pedido_${idPed}.pdf"`)
    const stream = fs.createReadStream(tmpPdf)
    stream.pipe(res)
    stream.on('close', () => fs.unlink(tmpPdf, () => {}))
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
// Query params: ?tipo=proyecto|dificultad|compromiso|idea  ?estado=Activo|...
app.get('/api/gestion/proyectos', async (req, res) => {
  const { estado, tipo } = req.query
  const where  = ['p.empresa = ?']
  const params = [req.empresa]
  if (tipo)   { where.push('p.tipo = ?');   params.push(tipo) }
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

    res.json({ ok: true, proyectos: filtrarPorNivel(result, req.usuario) })
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
const ESTADOS_DEFAULT = { proyecto: 'Activo', dificultad: 'Abierta', compromiso: 'Pendiente', idea: 'Nueva' }
const ESTADOS_VALIDOS = {
  proyecto:    ['Activo', 'Completado', 'Archivado'],
  dificultad:  ['Abierta', 'En progreso', 'Resuelta', 'Cerrada'],
  compromiso:  ['Pendiente', 'En progreso', 'Cumplido', 'Cancelado'],
  idea:        ['Nueva', 'En evaluación', 'Aprobada', 'Descartada'],
}
app.post('/api/gestion/proyectos', async (req, res) => {
  const { nombre, descripcion, color, categoria_id, prioridad, estado,
          fecha_estimada_fin, responsables, etiquetas, tipo } = req.body

  if (!nombre) return res.status(400).json({ error: 'Falta nombre' })
  const tipoVal = tipo || 'proyecto'
  if (!ESTADOS_VALIDOS[tipoVal]) return res.status(400).json({ error: 'Tipo inválido' })
  const estadoVal = estado || ESTADOS_DEFAULT[tipoVal]
  if (!ESTADOS_VALIDOS[tipoVal].includes(estadoVal)) return res.status(400).json({ error: `Estado '${estadoVal}' no válido para tipo '${tipoVal}'` })

  try {
    const [result] = await db.gestion.query(`
      INSERT INTO g_proyectos
        (empresa, tipo, nombre, descripcion, color, categoria_id, prioridad, estado,
         fecha_estimada_fin, usuario_creador, usuario_ult_modificacion)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)
    `, [
      req.empresa, tipoVal, nombre, descripcion||null, color||'#607D8B',
      categoria_id||null, prioridad||'Media', estadoVal,
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
    // Validar estado si se está cambiando
    if (estado !== undefined) {
      const [[row]] = await db.gestion.query('SELECT tipo FROM g_proyectos WHERE id = ? AND empresa = ?', [req.params.id, req.empresa])
      if (!row) return res.status(404).json({ error: 'No encontrado' })
      const validos = ESTADOS_VALIDOS[row.tipo] || []
      if (!validos.includes(estado)) return res.status(400).json({ error: `Estado '${estado}' no válido para tipo '${row.tipo}'` })
    }

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

// ─── JORNADAS ────────────────────────────────────────────────────────

// GET /api/gestion/jornadas/hoy — jornada del día del usuario actual + pausas
app.get('/api/gestion/jornadas/hoy', requireAuth, async (req, res) => {
  try {
    const hoy  = localDateCO()
    const ayer = localDateCO(new Date(Date.now() - 86400000))
    // Preferir jornada activa (sin hora_fin) de hoy o ayer (turno nocturno);
    // si no, la más reciente de hoy
    const [[jornada]] = await db.gestion.query(
      `SELECT * FROM g_jornadas
       WHERE empresa = ? AND usuario = ? AND (
         fecha = ? OR (fecha = ? AND hora_fin IS NULL)
       )
       ORDER BY CASE WHEN hora_fin IS NULL THEN 0 ELSE 1 END, id DESC LIMIT 1`,
      [req.empresa, req.usuario.email, hoy, ayer]
    )
    if (!jornada) return res.json({ ok: true, jornada: null })

    // Pausas con sus tipos
    const [pausas] = await db.gestion.query(`
      SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
      FROM g_jornada_pausas p
      LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
      LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
      WHERE p.jornada_id = ?
      GROUP BY p.id
      ORDER BY p.hora_inicio
    `, [jornada.id])

    jornada.pausas = pausas
    res.json({ ok: true, jornada })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/gestion/jornadas/iniciar — crear jornada del día
// Body opcional: { hora_inicio } — hora reportada por el usuario (si omite, usa NOW())
app.post('/api/gestion/jornadas/iniciar', requireAuth, async (req, res) => {
  try {
    const ahora = new Date()
    const hoy = localDateCO(ahora)

    // Verificar que no exista jornada ACTIVA hoy (sin hora_fin)
    const [[activa]] = await db.gestion.query(
      'SELECT id FROM g_jornadas WHERE empresa = ? AND usuario = ? AND fecha = ? AND hora_fin IS NULL',
      [req.empresa, req.usuario.email, hoy]
    )
    if (activa) return res.status(409).json({ error: 'Ya tienes una jornada activa hoy' })

    // Si ya hay una jornada cerrada hoy, exigir gap de 6 horas desde que se cerró
    const [[cerrada]] = await db.gestion.query(
      'SELECT hora_fin_registro FROM g_jornadas WHERE empresa = ? AND usuario = ? AND fecha = ? AND hora_fin IS NOT NULL ORDER BY id DESC LIMIT 1',
      [req.empresa, req.usuario.email, hoy]
    )
    if (cerrada) {
      const minDesdecierre = (ahora - new Date(cerrada.hora_fin_registro)) / 60000
      if (minDesdecierre < 360) {
        const restantes = Math.ceil(360 - minDesdecierre)
        const horas = Math.floor(restantes / 60)
        const mins  = restantes % 60
        const label = horas > 0 ? `${horas}h ${mins}m` : `${mins}m`
        return res.status(409).json({ error: `Debes esperar ${label} para iniciar una nueva jornada` })
      }
    }

    // hora_inicio = valor del usuario (editable), hora_inicio_registro = momento real del click (inmutable)
    const horaInicio = req.body.hora_inicio ? new Date(req.body.hora_inicio) : ahora

    const [result] = await db.gestion.query(`
      INSERT INTO g_jornadas (empresa, usuario, fecha, hora_inicio, hora_inicio_registro, usuario_creador, usuario_ult_modificacion)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, [req.empresa, req.usuario.email, hoy, horaInicio, ahora, req.usuario.email, req.usuario.email])

    const [[jornada]] = await db.gestion.query('SELECT * FROM g_jornadas WHERE id = ?', [result.insertId])
    jornada.pausas = []
    res.status(201).json({ ok: true, jornada })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/finalizar — registrar hora de fin
app.put('/api/gestion/jornadas/:id/finalizar', requireAuth, async (req, res) => {
  try {
    const [[jornada]] = await db.gestion.query(
      'SELECT * FROM g_jornadas WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!jornada) return res.status(404).json({ error: 'Jornada no encontrada' })
    if (jornada.hora_fin) return res.status(409).json({ error: 'La jornada ya fue finalizada' })

    // Verificar que no haya pausa activa
    const [[pausaAbierta]] = await db.gestion.query(
      'SELECT id FROM g_jornada_pausas WHERE jornada_id = ? AND hora_fin IS NULL',
      [jornada.id]
    )
    if (pausaAbierta) return res.status(409).json({ error: 'Hay una pausa activa. Reanuda antes de finalizar.' })

    const ahora = new Date()
    // hora_fin = valor del usuario (editable), hora_fin_registro = momento real del click (inmutable)
    const horaFin = req.body.hora_fin ? new Date(req.body.hora_fin) : ahora
    await db.gestion.query(`
      UPDATE g_jornadas SET hora_fin = ?, hora_fin_registro = ?, usuario_ult_modificacion = ?
      WHERE id = ?
    `, [horaFin, ahora, req.usuario.email, jornada.id])

    const [[updated]] = await db.gestion.query('SELECT * FROM g_jornadas WHERE id = ?', [jornada.id])
    res.json({ ok: true, jornada: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/editar — editar horas reportadas
app.put('/api/gestion/jornadas/:id/editar', requireAuth, async (req, res) => {
  try {
    const [[jornada]] = await db.gestion.query(
      'SELECT * FROM g_jornadas WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!jornada) return res.status(404).json({ error: 'Jornada no encontrada' })

    const { hora_inicio, hora_fin, observaciones } = req.body
    const sets = []; const params = []
    if (hora_inicio !== undefined) { sets.push('hora_inicio = ?'); params.push(hora_inicio) }
    if (hora_fin !== undefined)    { sets.push('hora_fin = ?');    params.push(hora_fin) }
    if (observaciones !== undefined) { sets.push('observaciones = ?'); params.push(observaciones) }
    if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })

    sets.push('usuario_ult_modificacion = ?')
    params.push(req.usuario.email, req.params.id, req.empresa)

    await db.gestion.query(
      `UPDATE g_jornadas SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`,
      params
    )
    const [[updated]] = await db.gestion.query('SELECT * FROM g_jornadas WHERE id = ?', [req.params.id])
    res.json({ ok: true, jornada: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/editar-admin — admin edita horas manuales y observaciones
// Solo modifica: hora_inicio, hora_fin, observaciones (NUNCA los campos _registro)
app.put('/api/gestion/jornadas/:id/editar-admin', requireAuth, async (req, res) => {
  try {
    if ((req.usuario.nivel || 1) < 7) return res.status(403).json({ error: 'Solo administradores' })
    const [[jornada]] = await db.gestion.query(
      'SELECT * FROM g_jornadas WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!jornada) return res.status(404).json({ error: 'Jornada no encontrada' })

    const { hora_inicio, hora_fin, observaciones } = req.body
    const sets = ['usuario_ult_modificacion = ?']
    const params = [req.usuario.email]

    if (hora_inicio !== undefined) { sets.push('hora_inicio = ?'); params.push(hora_inicio ? new Date(hora_inicio) : null) }
    if (hora_fin    !== undefined) { sets.push('hora_fin = ?');    params.push(hora_fin    ? new Date(hora_fin)    : null) }
    if (observaciones !== undefined) { sets.push('observaciones = ?'); params.push(observaciones || null) }

    params.push(req.params.id, req.empresa)
    await db.gestion.query(`UPDATE g_jornadas SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`, params)

    const [[updated]] = await db.gestion.query('SELECT * FROM g_jornadas WHERE id = ?', [req.params.id])
    res.json({ ok: true, jornada: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/jornadas/historial — historial con filtros y visibilidad por nivel
app.get('/api/gestion/jornadas/historial', requireAuth, async (req, res) => {
  try {
    const { usuario, fecha_desde, fecha_hasta } = req.query
    let where = 'j.empresa = ?'
    const params = [req.empresa]

    // Visibilidad por nivel
    if (req.usuario.nivel < 7) {
      if (usuario) {
        // Solo puede ver usuarios de nivel inferior o a sí mismo
        where += ' AND (j.usuario = ? OR EXISTS (SELECT 1 FROM ' +
          'u768061575_os_comunidad.sys_usuarios su ' +
          'WHERE su.Email = j.usuario AND su.Nivel_Acceso < ?))'
        params.push(req.usuario.email, req.usuario.nivel)
      } else {
        where += ' AND (j.usuario = ? OR EXISTS (SELECT 1 FROM ' +
          'u768061575_os_comunidad.sys_usuarios su ' +
          'WHERE su.Email = j.usuario AND su.Nivel_Acceso < ?))'
        params.push(req.usuario.email, req.usuario.nivel)
      }
    }

    if (usuario) { where += ' AND j.usuario = ?'; params.push(usuario) }
    if (fecha_desde) { where += ' AND j.fecha >= ?'; params.push(fecha_desde) }
    if (fecha_hasta) { where += ' AND j.fecha <= ?'; params.push(fecha_hasta) }

    const [jornadas] = await db.gestion.query(`
      SELECT j.*, su.Nombre_Usuario AS nombre_usuario
      FROM g_jornadas j
      LEFT JOIN u768061575_os_comunidad.sys_usuarios su ON su.Email = j.usuario
      WHERE ${where}
      ORDER BY j.fecha DESC, j.hora_inicio DESC
      LIMIT 100
    `, params)

    res.json({ ok: true, jornadas })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/gestion/jornadas/:id/pausas/iniciar — iniciar pausa
app.post('/api/gestion/jornadas/:id/pausas/iniciar', requireAuth, async (req, res) => {
  try {
    const [[jornada]] = await db.gestion.query(
      'SELECT * FROM g_jornadas WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!jornada) return res.status(404).json({ error: 'Jornada no encontrada' })

    const { tipos, observaciones, hora_inicio: hiBody, hora_fin: hfBody } = req.body
    const esRetroactiva = hiBody && hfBody // pausa completa retroactiva

    // Solo bloquear jornadas finalizadas si NO es retroactiva
    if (jornada.hora_fin && !esRetroactiva) return res.status(409).json({ error: 'La jornada ya fue finalizada' })

    // Verificar que no haya otra pausa abierta (solo si no es retroactiva)
    if (!esRetroactiva) {
      const [[pausaAbierta]] = await db.gestion.query(
        'SELECT id FROM g_jornada_pausas WHERE jornada_id = ? AND hora_fin IS NULL',
        [jornada.id]
      )
      if (pausaAbierta) return res.status(409).json({ error: 'Ya hay una pausa activa' })
    }
    if (!tipos || !Array.isArray(tipos) || !tipos.length) {
      return res.status(400).json({ error: 'Debes seleccionar al menos un tipo de pausa' })
    }

    const ahora = new Date()
    // Pausa retroactiva: hora_inicio y hora_fin del body → pausa completa inmediata
    // Pausa normal: hora_inicio = ahora, hora_fin = NULL (se cierra después con /reanudar)
    const horaInicioPausa = hiBody ? new Date(hiBody) : ahora
    const horaFinPausa    = hfBody ? new Date(hfBody) : null

    const [result] = await db.gestion.query(`
      INSERT INTO g_jornada_pausas (empresa, jornada_id, hora_inicio, hora_inicio_registro, hora_fin, hora_fin_registro, observaciones, usuario_creador, usuario_ult_modificacion)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [req.empresa, jornada.id, horaInicioPausa, ahora, horaFinPausa, horaFinPausa ? ahora : null, observaciones || null, req.usuario.email, req.usuario.email])

    // Insertar tipos de pausa (M:N)
    const vals = tipos.map(tipoId => [result.insertId, tipoId, req.empresa, req.usuario.email])
    await db.gestion.query(
      'INSERT INTO g_jornada_pausa_tipos (pausa_id, tipo_pausa_id, empresa, usuario_creador) VALUES ?',
      [vals]
    )

    // Retornar pausa con nombres de tipos
    const [[pausa]] = await db.gestion.query(`
      SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
      FROM g_jornada_pausas p
      LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
      LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
      WHERE p.id = ?
      GROUP BY p.id
    `, [result.insertId])

    res.status(201).json({ ok: true, pausa })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/pausas/:pausaId/editar — editar pausa (admin)
app.put('/api/gestion/jornadas/:id/pausas/:pausaId/editar', requireAuth, async (req, res) => {
  try {
    const [[pausa]] = await db.gestion.query(
      'SELECT p.* FROM g_jornada_pausas p JOIN g_jornadas j ON j.id = p.jornada_id WHERE p.id = ? AND j.id = ? AND j.empresa = ?',
      [req.params.pausaId, req.params.id, req.empresa]
    )
    if (!pausa) return res.status(404).json({ error: 'Pausa no encontrada' })

    const { hora_inicio, hora_fin, observaciones, tipos } = req.body

    // Actualizar campos editables (NUNCA _registro)
    const sets = []
    const vals = []
    if (hora_inicio !== undefined) { sets.push('hora_inicio = ?'); vals.push(hora_inicio ? new Date(hora_inicio) : null) }
    if (hora_fin !== undefined)    { sets.push('hora_fin = ?');    vals.push(hora_fin ? new Date(hora_fin) : null) }
    if (observaciones !== undefined) { sets.push('observaciones = ?'); vals.push(observaciones || null) }
    sets.push('usuario_ult_modificacion = ?'); vals.push(req.usuario.email)
    vals.push(pausa.id)

    await db.gestion.query(`UPDATE g_jornada_pausas SET ${sets.join(', ')} WHERE id = ?`, vals)

    // Actualizar tipos si se enviaron
    if (tipos && Array.isArray(tipos) && tipos.length) {
      await db.gestion.query('DELETE FROM g_jornada_pausa_tipos WHERE pausa_id = ? AND empresa = ?', [pausa.id, req.empresa])
      const tipoVals = tipos.map(tipoId => [pausa.id, tipoId, req.empresa, req.usuario.email])
      await db.gestion.query('INSERT INTO g_jornada_pausa_tipos (pausa_id, tipo_pausa_id, empresa, usuario_creador) VALUES ?', [tipoVals])
    }

    // Retornar pausa actualizada
    const [[updated]] = await db.gestion.query(`
      SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
      FROM g_jornada_pausas p
      LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
      LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
      WHERE p.id = ?
      GROUP BY p.id
    `, [pausa.id])

    res.json({ ok: true, pausa: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/pausas/:pausaId/reanudar — finalizar pausa
app.put('/api/gestion/jornadas/:id/pausas/:pausaId/reanudar', requireAuth, async (req, res) => {
  try {
    const [[pausa]] = await db.gestion.query(
      'SELECT p.* FROM g_jornada_pausas p JOIN g_jornadas j ON j.id = p.jornada_id WHERE p.id = ? AND j.id = ? AND j.empresa = ?',
      [req.params.pausaId, req.params.id, req.empresa]
    )
    if (!pausa) return res.status(404).json({ error: 'Pausa no encontrada' })
    if (pausa.hora_fin) return res.status(409).json({ error: 'La pausa ya fue cerrada' })

    const ahora = new Date()
    // hora_fin = valor del usuario (editable), hora_fin_registro = momento real del click (inmutable)
    const horaFinPausa = req.body.hora_fin ? new Date(req.body.hora_fin) : ahora
    await db.gestion.query(
      'UPDATE g_jornada_pausas SET hora_fin = ?, hora_fin_registro = ?, usuario_ult_modificacion = ? WHERE id = ?',
      [horaFinPausa, ahora, req.usuario.email, pausa.id]
    )

    const [[updated]] = await db.gestion.query(`
      SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
      FROM g_jornada_pausas p
      LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
      LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
      WHERE p.id = ?
      GROUP BY p.id
    `, [pausa.id])

    res.json({ ok: true, pausa: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/jornadas/:id/reabrir
// Permisos: dueño dentro de 1 hora desde cierre, O nivel >= 7
app.put('/api/gestion/jornadas/:id/reabrir', requireAuth, async (req, res) => {
  try {
    const [[jornada]] = await db.gestion.query(
      'SELECT * FROM g_jornadas WHERE id = ? AND empresa = ?',
      [req.params.id, req.empresa]
    )
    if (!jornada) return res.status(404).json({ error: 'Jornada no encontrada' })
    if (!jornada.hora_fin) return res.status(409).json({ error: 'La jornada no está finalizada' })

    const esDueno  = jornada.usuario === req.usuario.email
    const esAdmin  = (req.usuario.nivel || 1) >= 7
    const msDesde  = Date.now() - new Date(jornada.hora_fin_registro).getTime()
    const dentroVentana = msDesde <= 60 * 60 * 1000 // 1 hora

    if (!esAdmin && !(esDueno && dentroVentana)) {
      return res.status(403).json({ error: 'Sin permiso para reabrir esta jornada' })
    }

    await db.gestion.query(
      'UPDATE g_jornadas SET hora_fin = NULL, hora_fin_registro = NULL, usuario_ult_modificacion = ? WHERE id = ?',
      [req.usuario.email, jornada.id]
    )

    const [[updated]] = await db.gestion.query('SELECT * FROM g_jornadas WHERE id = ?', [jornada.id])
    const [pausas] = await db.gestion.query(`
      SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
      FROM g_jornada_pausas p
      LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
      LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
      WHERE p.jornada_id = ? GROUP BY p.id ORDER BY p.hora_inicio
    `, [jornada.id])
    updated.pausas = pausas
    res.json({ ok: true, jornada: updated })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// GET /api/gestion/jornadas/equipo — jornadas de hoy para TODOS los usuarios (admin)
// Incluye cálculos: tiempo_total_min, tiempo_pausa_min, tiempo_laborado_min
app.get('/api/gestion/jornadas/equipo', requireAuth, async (req, res) => {
  try {
    const hoy   = localDateCO()
    const desde = req.query.desde || req.query.fecha || hoy
    const hasta = req.query.hasta || req.query.fecha || hoy

    // Query jornadas + pausas desde gestion DB (sin cross-join)
    const [jornadas] = await db.gestion.query(`
      SELECT
        j.*,
        COALESCE(
          SUM(CASE WHEN p.hora_fin IS NOT NULL
            THEN TIMESTAMPDIFF(MINUTE, p.hora_inicio, p.hora_fin) ELSE 0 END), 0
        ) AS tiempo_pausa_min,
        CASE
          WHEN j.hora_fin IS NOT NULL THEN TIMESTAMPDIFF(MINUTE, j.hora_inicio, j.hora_fin)
          WHEN j.hora_inicio IS NOT NULL THEN TIMESTAMPDIFF(MINUTE, j.hora_inicio, UTC_TIMESTAMP())
          ELSE 0
        END AS tiempo_total_min
      FROM g_jornadas j
      LEFT JOIN g_jornada_pausas p ON p.jornada_id = j.id
      WHERE j.empresa = ? AND j.fecha BETWEEN ? AND ?
      GROUP BY j.id
      ORDER BY j.fecha DESC, j.hora_inicio
    `, [req.empresa, desde, hasta])

    // Enriquecer con nombres desde comunidad DB (pool separado, sin cross-join SQL)
    if (jornadas.length > 0) {
      const emails = jornadas.map(j => j.usuario)
      const placeholders = emails.map(() => '?').join(',')
      const [usuarios] = await db.comunidad.query(
        `SELECT \`Email\`, \`Nombre_Usuario\`, \`Nivel_Acceso\` FROM sys_usuarios WHERE \`Email\` IN (${placeholders})`,
        emails
      )
      const uMap = Object.fromEntries(usuarios.map(u => [u.Email, u]))
      jornadas.forEach(j => {
        j.Nombre_Usuario = uMap[j.usuario]?.Nombre_Usuario || null
        j.Nivel_Acceso   = uMap[j.usuario]?.Nivel_Acceso   || null
      })
    }

    // tiempo_laborado = total - pausas
    jornadas.forEach(j => {
      j.tiempo_laborado_min = Math.max(0, (j.tiempo_total_min || 0) - (j.tiempo_pausa_min || 0))
    })

    // Cargar pausas de todas las jornadas del rango
    if (jornadas.length > 0) {
      const jornadaIds = jornadas.map(j => j.id)
      const placeholdersPausas = jornadaIds.map(() => '?').join(',')
      const [todasPausas] = await db.gestion.query(`
        SELECT p.*, GROUP_CONCAT(tp.nombre ORDER BY tp.orden SEPARATOR ', ') AS tipos_nombre
        FROM g_jornada_pausas p
        LEFT JOIN g_jornada_pausa_tipos pt ON pt.pausa_id = p.id
        LEFT JOIN g_tipos_pausa tp ON tp.id = pt.tipo_pausa_id
        WHERE p.jornada_id IN (${placeholdersPausas})
        GROUP BY p.id
        ORDER BY p.hora_inicio
      `, jornadaIds)

      // Asignar pausas a cada jornada
      const pausasPorJornada = {}
      for (const p of todasPausas) {
        if (!pausasPorJornada[p.jornada_id]) pausasPorJornada[p.jornada_id] = []
        pausasPorJornada[p.jornada_id].push(p)
      }
      jornadas.forEach(j => { j.pausas = pausasPorJornada[j.id] || [] })
    }

    // Filtrar por nivel: solo jornadas de usuarios con nivel inferior + las propias
    const miNivel = req.usuario.nivel || nivelCache[req.usuario.email] || 1
    const jornadasFiltradas = jornadas.filter(j =>
      j.usuario === req.usuario.email || (nivelCache[j.usuario] || 1) < miNivel
    )
    res.json({ ok: true, desde, hasta, jornadas: jornadasFiltradas })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── TIPOS DE PAUSA ──────────────────────────────────────────────────

// GET /api/gestion/tipos-pausa
app.get('/api/gestion/tipos-pausa', requireAuth, async (req, res) => {
  try {
    const [tipos] = await db.gestion.query(
      'SELECT * FROM g_tipos_pausa WHERE empresa = ? AND activa = 1 ORDER BY orden',
      [req.empresa]
    )
    res.json({ ok: true, tipos })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// POST /api/gestion/tipos-pausa
app.post('/api/gestion/tipos-pausa', requireAuth, async (req, res) => {
  try {
    const { nombre, orden } = req.body
    if (!nombre) return res.status(400).json({ error: 'Nombre requerido' })
    const [result] = await db.gestion.query(
      'INSERT INTO g_tipos_pausa (empresa, nombre, orden, usuario_creador, usuario_ult_modificacion) VALUES (?, ?, ?, ?, ?)',
      [req.empresa, nombre, orden || 0, req.usuario.email, req.usuario.email]
    )
    const [[tipo]] = await db.gestion.query('SELECT * FROM g_tipos_pausa WHERE id = ?', [result.insertId])
    res.status(201).json({ ok: true, tipo })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// PUT /api/gestion/tipos-pausa/:id
app.put('/api/gestion/tipos-pausa/:id', requireAuth, async (req, res) => {
  try {
    const { nombre, activa, orden } = req.body
    const sets = []; const params = []
    if (nombre !== undefined) { sets.push('nombre = ?'); params.push(nombre) }
    if (activa !== undefined) { sets.push('activa = ?'); params.push(activa) }
    if (orden !== undefined)  { sets.push('orden = ?');  params.push(orden) }
    if (!sets.length) return res.status(400).json({ error: 'Nada que actualizar' })

    sets.push('usuario_ult_modificacion = ?')
    params.push(req.usuario.email, req.params.id, req.empresa)

    await db.gestion.query(
      `UPDATE g_tipos_pausa SET ${sets.join(', ')} WHERE id = ? AND empresa = ?`,
      params
    )
    const [[tipo]] = await db.gestion.query('SELECT * FROM g_tipos_pausa WHERE id = ?', [req.params.id])
    res.json({ ok: true, tipo })
  } catch (e) { res.status(500).json({ error: e.message }) }
})

// ─── Upload de archivos (imágenes en TipTap) ──────────────────────
function slugify(str) {
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40)
}

app.post('/api/gestion/upload', upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'Falta archivo' })
  if (!MIME_PERMITIDOS.includes(req.file.mimetype)) {
    fs.unlink(req.file.path, () => {})
    return res.status(400).json({ error: 'Formato no permitido. Usa: jpg, png, webp, gif, pdf' })
  }

  const { tipo, item_id, item_nombre } = req.body
  const tipoVal = tipo || 'general'
  const idSlug  = item_id ? `${item_id}_${slugify(item_nombre || 'sin-nombre')}` : 'sin-item'

  // Timestamp Colombia
  const now = new Date()
  const ts  = now.toLocaleString('sv-SE', { timeZone: 'America/Bogota' }).replace(/[- :]/g, '').slice(0, 15)
  const stamp = ts.slice(0, 8) + '-' + ts.slice(8)
  const hash  = crypto.randomBytes(3).toString('hex')
  const ext   = path.extname(req.file.originalname).toLowerCase() || '.jpg'

  const relDir  = `gestion/${tipoVal}/${idSlug}`
  const relPath = `${relDir}/${stamp}_${hash}${ext}`
  const absDir  = path.join(SUBIDOS_ROOT, relDir)
  const absPath = path.join(SUBIDOS_ROOT, relPath)

  fs.mkdirSync(absDir, { recursive: true })
  fs.renameSync(req.file.path, absPath)

  res.json({ ok: true, url: `/subidos/${relPath}`, ruta_relativa: relPath })
})

// ─── Fallback SPA ──────────────────────────────────────────────────
app.use((req, res) => {
  const pwa = path.join(__dirname, '../app/dist/pwa/index.html')
  if (fs.existsSync(pwa)) return res.sendFile(pwa)
  res.status(404).json({ error: 'Frontend no desplegado aún' })
})

// ─── Arrancar ─────────────────────────────────────────────────────
async function arrancar() {
  try {
    console.log('[server] Conectando SSH tunnel → Hostinger...')
    await db.conectar()
    console.log('[server] Pools MySQL listos (comunidad / gestion / integracion)')

    await refrescarNiveles()
    setInterval(refrescarNiveles, 5 * 60 * 1000)  // cada 5 min

    app.listen(PORT, () => {
      console.log(`[server] OS Gestión API corriendo en puerto ${PORT}`)
    })
  } catch (e) {
    console.error('[server] Error al iniciar:', e.message)
    process.exit(1)
  }
}

arrancar()
