/**
 * ialocal/server.js
 * Puerto: 9500
 * Chat UI para modelos Ollama locales
 * Proxy: /api/* → localhost:11434/api/*
 */

const express = require('express')
const path    = require('path')
const http    = require('http')

const PORT        = 9500
const OLLAMA_HOST = 'localhost'
const OLLAMA_PORT = 11434

const app = express()
app.use(express.json({ limit: '1mb' }))
app.use(express.static(path.join(__dirname, 'public')))

// ─── CORS ──────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  next()
})

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

// ─── GET /api/tags — lista de modelos ──────────────────────────────
app.get('/api/tags', (req, res) => {
  proxyToOllama(req, res, '/api/tags')
})

// ─── GET /api/ps — modelo activo en VRAM ───────────────────────────
app.get('/api/ps', (req, res) => {
  proxyToOllama(req, res, '/api/ps')
})

// ─── POST /api/chat — chat streaming ──────────────────────────────
app.post('/api/chat', (req, res) => {
  const body = { ...req.body, stream: true }
  proxyToOllama(req, res, '/api/chat', 'POST', body)
})

// ─── Fallback → index.html ─────────────────────────────────────────
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'))
})

app.listen(PORT, () => {
  console.log(`[ialocal] Chat UI corriendo en http://localhost:${PORT}`)
  console.log(`[ialocal] Proxy → Ollama en ${OLLAMA_HOST}:${OLLAMA_PORT}`)
})
