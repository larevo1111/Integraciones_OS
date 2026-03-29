/**
 * ialocal/server.js
 * Puerto: 9500
 * Chat UI para modelos Ollama locales
 * Proxy: /api/chat, /api/tags, /api/ps, /api/show → Ollama localhost:11434
 * Persistencia: conversaciones + mensajes en MariaDB ia_local
 */

const express = require('express')
const path    = require('path')
const http    = require('http')
const mysql   = require('mysql2/promise')

const PORT        = 9500
const OLLAMA_HOST = 'localhost'
const OLLAMA_PORT = 11434

const app = express()
app.use(express.json({ limit: '2mb' }))
app.use(express.static(path.join(__dirname, 'public')))

// ─── CORS ──────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  next()
})

// ─── Pool MySQL ────────────────────────────────────────────────────
const pool = mysql.createPool({
  host: '127.0.0.1',
  user: 'osadmin',
  password: 'Epist2487.',
  database: 'ia_local',
  waitForConnections: true,
  connectionLimit: 5
})

// ─── Helpers ───────────────────────────────────────────────────────
function estimarTokens(texto) {
  return Math.ceil((texto || '').length / 4)
}

// ─── Proxy genérico a Ollama ───────────────────────────────────────
function proxyToOllama(req, res, ollamaPath, method = 'GET', body = null) {
  const opts = {
    hostname: OLLAMA_HOST,
    port: OLLAMA_PORT,
    path: ollamaPath,
    method,
    headers: { 'Content-Type': 'application/json' }
  }

  const proxyReq = http.request(opts, proxyRes => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers)
    proxyRes.pipe(res)
  })

  proxyReq.on('error', err => {
    console.error(`[Ollama proxy error] ${err.message}`)
    res.status(502).json({ error: 'No se pudo conectar con Ollama', detail: err.message })
  })

  if (body) proxyReq.write(JSON.stringify(body))
  proxyReq.end()
}

// Petición JSON a Ollama (no streaming, para uso interno)
function ollamaJSON(ollamaPath, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: OLLAMA_HOST,
      port: OLLAMA_PORT,
      path: ollamaPath,
      method,
      headers: { 'Content-Type': 'application/json' }
    }
    const req = http.request(opts, res => {
      let data = ''
      res.on('data', c => data += c)
      res.on('end', () => {
        try { resolve(JSON.parse(data)) }
        catch { resolve(data) }
      })
    })
    req.on('error', reject)
    if (body) req.write(JSON.stringify(body))
    req.end()
  })
}

// ═══════════════════════════════════════════════════════════════════
// PROXY OLLAMA
// ═══════════════════════════════════════════════════════════════════

app.get('/api/tags', (req, res) => proxyToOllama(req, res, '/api/tags'))
app.get('/api/ps', (req, res) => proxyToOllama(req, res, '/api/ps'))
app.post('/api/chat', (req, res) => {
  proxyToOllama(req, res, '/api/chat', 'POST', { ...req.body, stream: true })
})

// GET /api/show — obtener info del modelo (context_length, etc)
app.post('/api/show', (req, res) => {
  proxyToOllama(req, res, '/api/show', 'POST', req.body)
})

// ═══════════════════════════════════════════════════════════════════
// API CONVERSACIONES
// ═══════════════════════════════════════════════════════════════════

// GET /api/conversaciones — listar
app.get('/api/conversaciones', async (req, res) => {
  try {
    const [rows] = await pool.execute(
      `SELECT id, titulo, modelo, tokens_usados, contexto_max, created_at, updated_at
       FROM conversaciones WHERE activa = 1
       ORDER BY updated_at DESC`
    )
    res.json(rows)
  } catch (e) {
    console.error('[DB error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// POST /api/conversaciones — crear nueva
app.post('/api/conversaciones', async (req, res) => {
  try {
    const { modelo, contexto_max, titulo } = req.body
    const [result] = await pool.execute(
      `INSERT INTO conversaciones (titulo, modelo, contexto_max) VALUES (?, ?, ?)`,
      [titulo || 'Nueva conversación', modelo || 'qwen2.5-coder:14b', contexto_max || 32768]
    )
    res.json({ id: result.insertId })
  } catch (e) {
    console.error('[DB error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// GET /api/conversaciones/:id — obtener con mensajes visibles
app.get('/api/conversaciones/:id', async (req, res) => {
  try {
    const [convs] = await pool.execute(
      'SELECT * FROM conversaciones WHERE id = ?', [req.params.id]
    )
    if (convs.length === 0) return res.status(404).json({ error: 'No encontrada' })

    const [msgs] = await pool.execute(
      `SELECT id, rol, contenido, tokens_estimados, visible, created_at
       FROM mensajes WHERE conversacion_id = ? AND visible = 1
       ORDER BY created_at ASC`,
      [req.params.id]
    )
    res.json({ ...convs[0], mensajes: msgs })
  } catch (e) {
    console.error('[DB error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// GET /api/conversaciones/:id/completa — todos los mensajes (incluye compactados)
app.get('/api/conversaciones/:id/completa', async (req, res) => {
  try {
    const [convs] = await pool.execute(
      'SELECT * FROM conversaciones WHERE id = ?', [req.params.id]
    )
    if (convs.length === 0) return res.status(404).json({ error: 'No encontrada' })

    const [msgs] = await pool.execute(
      `SELECT id, rol, contenido, tokens_estimados, visible, created_at
       FROM mensajes WHERE conversacion_id = ?
       ORDER BY created_at ASC`,
      [req.params.id]
    )
    res.json({ ...convs[0], mensajes: msgs })
  } catch (e) {
    console.error('[DB error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// PUT /api/conversaciones/:id/titulo — renombrar
app.put('/api/conversaciones/:id/titulo', async (req, res) => {
  try {
    const { titulo } = req.body
    await pool.execute(
      'UPDATE conversaciones SET titulo = ? WHERE id = ?',
      [titulo, req.params.id]
    )
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// DELETE /api/conversaciones/:id — eliminar (CASCADE borra mensajes)
app.delete('/api/conversaciones/:id', async (req, res) => {
  try {
    await pool.execute('DELETE FROM conversaciones WHERE id = ?', [req.params.id])
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ═══════════════════════════════════════════════════════════════════
// API MENSAJES
// ═══════════════════════════════════════════════════════════════════

// POST /api/mensajes — guardar mensaje
app.post('/api/mensajes', async (req, res) => {
  try {
    const { conversacion_id, rol, contenido } = req.body
    const tokens = estimarTokens(contenido)

    const [result] = await pool.execute(
      `INSERT INTO mensajes (conversacion_id, rol, contenido, tokens_estimados)
       VALUES (?, ?, ?, ?)`,
      [conversacion_id, rol, contenido, tokens]
    )

    // Actualizar tokens_usados en la conversación
    await pool.execute(
      `UPDATE conversaciones
       SET tokens_usados = (
         SELECT COALESCE(SUM(tokens_estimados), 0)
         FROM mensajes WHERE conversacion_id = ? AND visible = 1
       )
       WHERE id = ?`,
      [conversacion_id, conversacion_id]
    )

    // Auto-título: si es el primer mensaje de usuario, usar como título
    if (rol === 'usuario') {
      const [conv] = await pool.execute(
        'SELECT titulo FROM conversaciones WHERE id = ?', [conversacion_id]
      )
      if (conv.length && conv[0].titulo === 'Nueva conversación') {
        const autoTitulo = contenido.substring(0, 60).replace(/\n/g, ' ')
        await pool.execute(
          'UPDATE conversaciones SET titulo = ? WHERE id = ?',
          [autoTitulo, conversacion_id]
        )
      }
    }

    // Devolver estado actual
    const [updated] = await pool.execute(
      'SELECT tokens_usados, contexto_max, titulo FROM conversaciones WHERE id = ?',
      [conversacion_id]
    )

    res.json({
      id: result.insertId,
      tokens_estimados: tokens,
      ...(updated[0] || {})
    })
  } catch (e) {
    console.error('[DB error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// ═══════════════════════════════════════════════════════════════════
// COMPACTAR CONVERSACIÓN
// ═══════════════════════════════════════════════════════════════════

app.post('/api/conversaciones/:id/compactar', async (req, res) => {
  try {
    const convId = req.params.id

    // Obtener conversación
    const [convs] = await pool.execute(
      'SELECT * FROM conversaciones WHERE id = ?', [convId]
    )
    if (convs.length === 0) return res.status(404).json({ error: 'No encontrada' })
    const conv = convs[0]

    // Obtener mensajes visibles
    const [msgs] = await pool.execute(
      `SELECT id, rol, contenido FROM mensajes
       WHERE conversacion_id = ? AND visible = 1
       ORDER BY created_at ASC`,
      [convId]
    )

    if (msgs.length < 4) {
      return res.status(400).json({ error: 'Muy pocos mensajes para compactar' })
    }

    // Dejar los últimos 2 intercambios (4 mensajes) sin compactar
    const keepCount = 4
    const toCompact = msgs.slice(0, -keepCount)
    const toKeep = msgs.slice(-keepCount)

    // Construir texto de los mensajes a compactar
    const textoParaResumir = toCompact.map(m =>
      `${m.rol === 'usuario' ? 'Usuario' : 'Asistente'}: ${m.contenido}`
    ).join('\n\n')

    // Pedir al modelo que resuma
    const resumenResponse = await ollamaJSON('/api/chat', 'POST', {
      model: conv.modelo,
      stream: false,
      messages: [{
        role: 'user',
        content: `Resume la siguiente conversación en máximo 500 palabras. Conserva datos específicos, números, código, decisiones y conclusiones importantes. El resumen será usado como contexto para continuar la conversación.\n\n${textoParaResumir}`
      }]
    })

    const resumenTexto = resumenResponse.message?.content || 'Error al generar resumen'

    // Marcar mensajes antiguos como no visibles
    const idsCompactar = toCompact.map(m => m.id)
    await pool.execute(
      `UPDATE mensajes SET visible = 0 WHERE id IN (${idsCompactar.map(() => '?').join(',')})`,
      idsCompactar
    )

    // Insertar mensaje resumen
    const tokensResumen = estimarTokens(resumenTexto)
    await pool.execute(
      `INSERT INTO mensajes (conversacion_id, rol, contenido, tokens_estimados, visible)
       VALUES (?, 'resumen', ?, ?, 1)`,
      [convId, resumenTexto, tokensResumen]
    )

    // Recalcular tokens
    await pool.execute(
      `UPDATE conversaciones
       SET tokens_usados = (
         SELECT COALESCE(SUM(tokens_estimados), 0)
         FROM mensajes WHERE conversacion_id = ? AND visible = 1
       )
       WHERE id = ?`,
      [convId, convId]
    )

    const [updated] = await pool.execute(
      'SELECT tokens_usados, contexto_max FROM conversaciones WHERE id = ?', [convId]
    )

    res.json({
      ok: true,
      mensajes_compactados: idsCompactar.length,
      resumen_tokens: tokensResumen,
      ...(updated[0] || {})
    })
  } catch (e) {
    console.error('[Compactar error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// ─── Fallback → index.html ─────────────────────────────────────────
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'))
})

app.listen(PORT, () => {
  console.log(`[ialocal] Chat UI corriendo en http://localhost:${PORT}`)
  console.log(`[ialocal] Proxy → Ollama en ${OLLAMA_HOST}:${OLLAMA_PORT}`)
  console.log(`[ialocal] BD → ia_local (MariaDB)`)
})
