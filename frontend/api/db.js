// db.js — SSH tunnel + MySQL connection pool a Hostinger (con auto-reconexión)
const { spawn } = require('child_process')
const mysql = require('mysql2/promise')

const SSH_KEY    = '/home/osserver/.ssh/sos_erp'
const SSH_HOST   = '109.106.250.195'
const SSH_PORT   = 65002
const SSH_USER   = 'u768061575'
const LOCAL_PORT = 3308

const DB_CONFIG = {
  host: '127.0.0.1',
  port: LOCAL_PORT,
  user: 'u768061575_osserver',
  password: 'Epist2487.',
  database: 'u768061575_os_integracion',
  waitForConnections: true,
  connectionLimit: 5,
  queueLimit: 0
}

let pool = null
let tunnelProcess = null
let tunnelReady = false

function startTunnel() {
  return new Promise((resolve) => {
    if (tunnelProcess) {
      try { tunnelProcess.kill() } catch (_) {}
      tunnelProcess = null
    }
    tunnelReady = false

    tunnelProcess = spawn('ssh', [
      '-i', SSH_KEY,
      '-p', String(SSH_PORT),
      '-L', `${LOCAL_PORT}:127.0.0.1:3306`,
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'ServerAliveInterval=30',
      '-o', 'ServerAliveCountMax=3',
      '-o', 'ExitOnForwardFailure=yes',
      '-N',
      `${SSH_USER}@${SSH_HOST}`
    ])

    tunnelProcess.on('error', (err) => {
      console.error('[db.js] tunnel error:', err.message)
      tunnelReady = false
    })

    tunnelProcess.on('close', (code) => {
      console.error(`[db.js] tunnel cerrado (code ${code}), reconectando en 5s...`)
      tunnelReady = false
      tunnelProcess = null
      setTimeout(() => startTunnel().catch(() => {}), 5000)
    })

    // Esperar a que el puerto esté listo
    let tries = 0
    const check = setInterval(async () => {
      tries++
      try {
        const net = require('net')
        const sock = net.createConnection(LOCAL_PORT, '127.0.0.1')
        sock.on('connect', () => {
          sock.destroy()
          clearInterval(check)
          tunnelReady = true
          resolve()
        })
        sock.on('error', () => { sock.destroy() })
      } catch (_) {}
      if (tries > 20) { clearInterval(check); resolve() }
    }, 500)
  })
}

async function getPool() {
  if (!tunnelReady || !tunnelProcess) {
    await startTunnel()
  }
  if (!pool) {
    pool = mysql.createPool(DB_CONFIG)
  }
  return pool
}

async function query(sql, params = []) {
  const p = await getPool()
  try {
    const [rows] = await p.execute(sql, params)
    return rows
  } catch (err) {
    // Si el tunnel se cayó, forzar reconexión en el próximo intento
    if (err.code === 'ECONNREFUSED' || err.code === 'PROTOCOL_CONNECTION_LOST') {
      tunnelReady = false
      if (pool) { try { await pool.end() } catch (_) {} pool = null }
    }
    throw err
  }
}

module.exports = { query, getPool }
