/**
 * ialocal/server.js
 * Puerto: 9500
 * Chat UI para modelos Ollama locales
 * Proxy: /api/chat, /api/tags, /api/ps, /api/show → Ollama localhost:11434
 * Persistencia: conversaciones + mensajes en MariaDB ia_local
 * Multimodal: transcripción (Whisper), visión (Ollama), generación imágenes (ComfyUI+FLUX)
 */

const express = require('express')
const path    = require('path')
const http    = require('http')
const fs      = require('fs')
const mysql   = require('mysql2/promise')
const multer  = require('multer')
const { execFile } = require('child_process')

const PORT          = 9500
const OLLAMA_HOST   = 'localhost'
const OLLAMA_PORT   = 11434
const COMFYUI_HOST  = 'localhost'
const COMFYUI_PORT  = 8188

const app = express()
app.use(express.json({ limit: '10mb' }))
app.use(express.static(path.join(__dirname, 'public')))

// Multer para uploads de audio
const upload = multer({ dest: '/tmp/ialocal-uploads/', limits: { fileSize: 25 * 1024 * 1024 } })

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
      [titulo || 'Nueva conversación', modelo || 'qwen-coder-ctx', contexto_max || 28672]
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

// ═══════════════════════════════════════════════════════════════════
// TRANSCRIPCIÓN DE AUDIO (Whisper)
// ═══════════════════════════════════════════════════════════════════

app.post('/api/transcribir', upload.single('audio'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No se recibió archivo de audio' })

  const audioPath = req.file.path
  const lang = req.body.language || 'Spanish'

  try {
    const result = await new Promise((resolve, reject) => {
      execFile('/home/osserver/.local/bin/whisper', [audioPath, '--model', 'medium', '--language', lang, '--output_format', 'txt', '--output_dir', '/tmp/ialocal-uploads/'], { timeout: 120000 }, (err, stdout, stderr) => {
        if (err) return reject(new Error(stderr || err.message))
        // Whisper genera archivo .txt con el mismo nombre
        const txtPath = audioPath + '.txt'
        fs.readFile(txtPath, 'utf-8', (e, data) => {
          if (e) return reject(new Error('No se pudo leer la transcripción'))
          // Limpiar archivos temporales
          fs.unlink(audioPath, () => {})
          fs.unlink(txtPath, () => {})
          resolve(data.trim())
        })
      })
    })

    res.json({ ok: true, texto: result })
  } catch (e) {
    fs.unlink(audioPath, () => {})
    console.error('[Whisper error]', e.message)
    res.status(500).json({ error: e.message })
  }
})

// ═══════════════════════════════════════════════════════════════════
// VRAM STATUS
// ═══════════════════════════════════════════════════════════════════

app.get('/api/vram', async (req, res) => {
  try {
    // Modelos Ollama cargados
    const ps = await ollamaJSON('/api/ps')
    const ollamaModels = (ps.models || []).map(m => ({
      nombre: m.name,
      vram_mb: Math.round((m.size_vram || 0) / 1024 / 1024)
    }))

    // GPU info via nvidia-smi
    const gpuInfo = await new Promise((resolve) => {
      execFile('nvidia-smi', ['--query-gpu=memory.used,memory.free,memory.total', '--format=csv,noheader,nounits'], (err, stdout) => {
        if (err) return resolve(null)
        const [used, free, total] = stdout.trim().split(', ').map(Number)
        resolve({ used_mb: used, free_mb: free, total_mb: total })
      })
    })

    res.json({ ollama: ollamaModels, gpu: gpuInfo })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// ═══════════════════════════════════════════════════════════════════
// GENERACIÓN DE IMÁGENES (ComfyUI + FLUX.1-schnell)
// ═══════════════════════════════════════════════════════════════════

// Parar todos los modelos Ollama de VRAM
async function pararOllama() {
  try {
    const ps = await ollamaJSON('/api/ps')
    for (const m of (ps.models || [])) {
      await new Promise((resolve) => {
        execFile('ollama', ['stop', m.name], { timeout: 10000 }, () => resolve())
      })
    }
  } catch {}
}

// Hacer request HTTP a ComfyUI
function comfyuiRequest(ruta, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: COMFYUI_HOST,
      port: COMFYUI_PORT,
      path: ruta,
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

// Obtener imagen generada como buffer
function comfyuiGetImage(filename, subfolder, type) {
  return new Promise((resolve, reject) => {
    const qs = `filename=${encodeURIComponent(filename)}&subfolder=${encodeURIComponent(subfolder || '')}&type=${encodeURIComponent(type || 'output')}`
    http.get(`http://${COMFYUI_HOST}:${COMFYUI_PORT}/view?${qs}`, res => {
      const chunks = []
      res.on('data', c => chunks.push(c))
      res.on('end', () => resolve(Buffer.concat(chunks)))
      res.on('error', reject)
    }).on('error', reject)
  })
}

app.post('/api/generar-imagen', async (req, res) => {
  const { prompt, width, height } = req.body
  if (!prompt) return res.status(400).json({ error: 'Se requiere un prompt' })

  const w = width || 768
  const h = height || 768

  try {
    // 1. Parar modelos Ollama para liberar VRAM
    await pararOllama()

    // 2. Armar workflow FLUX.1-schnell con GGUF
    const workflow = {
      "1": {
        "class_type": "UnetLoaderGGUF",
        "inputs": { "unet_name": "flux1-schnell-Q4_K_S.gguf" }
      },
      "2": {
        "class_type": "DualCLIPLoaderGGUF",
        "inputs": {
          "clip_name1": "clip_l.safetensors",
          "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
          "type": "flux"
        }
      },
      "3": {
        "class_type": "VAELoader",
        "inputs": { "vae_name": "flux-vae-bf16.safetensors" }
      },
      "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
          "text": prompt,
          "clip": ["2", 0]
        }
      },
      "5": {
        "class_type": "EmptySD3LatentImage",
        "inputs": { "width": w, "height": h, "batch_size": 1 }
      },
      "6": {
        "class_type": "RandomNoise",
        "inputs": { "noise_seed": Math.floor(Math.random() * 2**32) }
      },
      "7": {
        "class_type": "BasicScheduler",
        "inputs": {
          "scheduler": "simple",
          "steps": 4,
          "denoise": 1.0,
          "model": ["1", 0]
        }
      },
      "8": {
        "class_type": "KSamplerSelect",
        "inputs": { "sampler_name": "euler" }
      },
      "9": {
        "class_type": "BasicGuider",
        "inputs": {
          "model": ["1", 0],
          "conditioning": ["4", 0]
        }
      },
      "10": {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {
          "noise": ["6", 0],
          "guider": ["9", 0],
          "sampler": ["8", 0],
          "sigmas": ["7", 0],
          "latent_image": ["5", 0]
        }
      },
      "11": {
        "class_type": "VAEDecode",
        "inputs": {
          "samples": ["10", 0],
          "vae": ["3", 0]
        }
      },
      "12": {
        "class_type": "SaveImage",
        "inputs": {
          "filename_prefix": "ialocal",
          "images": ["11", 0]
        }
      }
    }

    // 3. Encolar en ComfyUI
    const queueResult = await comfyuiRequest('/prompt', 'POST', { prompt: workflow })
    const promptId = queueResult.prompt_id

    if (!promptId) {
      return res.status(500).json({ error: 'ComfyUI no aceptó el prompt', detail: JSON.stringify(queueResult) })
    }

    // 4. Esperar a que termine (polling)
    let imagen = null
    for (let i = 0; i < 120; i++) {
      await new Promise(r => setTimeout(r, 2000))

      const history = await comfyuiRequest(`/history/${promptId}`)
      if (history[promptId]) {
        const outputs = history[promptId].outputs
        // Buscar nodo SaveImage (nodo "12")
        const saveNode = outputs['12']
        if (saveNode && saveNode.images && saveNode.images.length > 0) {
          const img = saveNode.images[0]
          const buffer = await comfyuiGetImage(img.filename, img.subfolder, img.type)
          imagen = buffer.toString('base64')
          break
        }
        // Si hubo error
        if (history[promptId].status?.status_str === 'error') {
          return res.status(500).json({ error: 'ComfyUI reportó error al generar' })
        }
      }
    }

    if (!imagen) {
      return res.status(504).json({ error: 'Timeout esperando imagen de ComfyUI' })
    }

    res.json({ ok: true, imagen_b64: imagen, mime: 'image/png' })
  } catch (e) {
    console.error('[ComfyUI error]', e.message)
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
