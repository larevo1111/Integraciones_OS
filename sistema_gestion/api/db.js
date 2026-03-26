/**
 * sistema_gestion/api/db.js
 * SSH tunnel → Hostinger MySQL 3306
 * 3 pools: comunidad (RO), gestion (RW), integracion (RO)
 * Auto-reconexión al detectar caída del tunnel
 */

const mysql      = require('mysql2/promise')
const { Client } = require('ssh2')
const net        = require('net')
const path       = require('path')
const fs         = require('fs')
const os         = require('os')

// ─── Config ────────────────────────────────────────────────────────
const SSH_HOST     = '109.106.250.195'
const SSH_PORT     = 65002
const SSH_USER     = 'u768061575'
const SSH_KEY_PATH = path.join(os.homedir(), '.ssh', 'sos_erp')
const MYSQL_HOST   = '127.0.0.1'
const MYSQL_PORT   = 3306
const LOCAL_PORT   = 3311

const DB_USER_GESTION     = 'u768061575_os_gestion'
const DB_USER_COMUNIDAD   = 'u768061575_ssierra047'
const DB_USER_INTEGRACION = 'u768061575_osserver'
const DB_PASS             = 'Epist2487.'
const DB_COMUNIDAD        = 'u768061575_os_comunidad'
const DB_GESTION          = 'u768061575_os_gestion'
const DB_INTEGRACION      = 'u768061575_os_integracion'

// ─── Estado ────────────────────────────────────────────────────────
let sshClient    = null
let tcpServer    = null
let tunnelReady  = false
let reconectando = false

let poolComunidad   = null
let poolGestion     = null
let poolIntegracion = null

// ─── Pools ─────────────────────────────────────────────────────────
function crearPools() {
  const base = {
    host: '127.0.0.1', port: LOCAL_PORT,
    password: DB_PASS, waitForConnections: true,
    connectionLimit: 10, timezone: 'local'
  }
  poolComunidad   = mysql.createPool({ ...base, user: DB_USER_COMUNIDAD,   database: DB_COMUNIDAD })
  poolIntegracion = mysql.createPool({ ...base, user: DB_USER_INTEGRACION, database: DB_INTEGRACION })
  poolGestion     = mysql.createPool({ ...base, user: DB_USER_GESTION,     database: DB_GESTION })
}

function destruirPools() {
  for (const p of [poolComunidad, poolGestion, poolIntegracion]) {
    if (p) p.end().catch(() => {})
  }
  poolComunidad = poolGestion = poolIntegracion = null
}

// ─── Reconexión automática ─────────────────────────────────────────
function programarReconexion(delay = 5000) {
  if (reconectando) return
  reconectando = true
  setTimeout(() => {
    console.log('[db] Intentando reconectar SSH tunnel...')
    conectarSSH()
      .then(() => {
        console.log('[db] Reconexión SSH exitosa')
        reconectando = false
      })
      .catch(err => {
        console.error('[db] Reconexión fallida, reintentando en 15s:', err.message)
        reconectando = false
        programarReconexion(15000)
      })
  }, delay)
}

// ─── SSH Client ────────────────────────────────────────────────────
function conectarSSH() {
  return new Promise((resolve, reject) => {
    if (sshClient) { try { sshClient.destroy() } catch (e) {} sshClient = null }

    const privateKey = fs.readFileSync(SSH_KEY_PATH)
    const client = new Client()
    sshClient = client

    client.on('ready', () => {
      console.log('[db] SSH tunnel establecido → Hostinger MySQL')
      crearPools()
      tunnelReady = true
      resolve()
    })

    client.on('error', err => {
      console.error('[db] SSH error:', err.message)
      if (!tunnelReady) reject(err)
    })

    client.on('close', () => {
      // Solo reaccionar si fue este cliente el que se cayó (no uno ya reemplazado)
      if (sshClient === client && tunnelReady) {
        console.log('[db] SSH tunnel cerrado — programando reconexión...')
        tunnelReady = false
        destruirPools()
        sshClient = null
        programarReconexion(5000)
      }
    })

    client.connect({ host: SSH_HOST, port: SSH_PORT, username: SSH_USER, privateKey })
  })
}

// ─── TCP Server (proxy local — se crea una sola vez) ───────────────
function crearTcpServer() {
  return new Promise((resolve, reject) => {
    tcpServer = net.createServer(localSocket => {
      // Leer sshClient en tiempo de ejecución (no en cierre de la función)
      // para que siempre use el cliente más reciente tras reconexiones
      if (!sshClient) { localSocket.end(); return }
      sshClient.forwardOut(
        '127.0.0.1', LOCAL_PORT, MYSQL_HOST, MYSQL_PORT,
        (err, stream) => {
          if (err) {
            console.error('[db] forwardOut error:', err.message)
            localSocket.end()
            return
          }
          localSocket.pipe(stream).pipe(localSocket)
          localSocket.on('error', () => stream.end())
          stream.on('error', () => localSocket.end())
        }
      )
    })

    tcpServer.on('error', err => {
      if (err.code === 'EADDRINUSE') {
        console.log('[db] Puerto local ya en uso — asumiendo tunnel activo')
        crearPools()
        tunnelReady = true
        return resolve()
      }
      reject(err)
    })

    tcpServer.listen(LOCAL_PORT, '127.0.0.1', () => resolve())
  })
}

// ─── Inicialización ────────────────────────────────────────────────
async function conectar() {
  if (tunnelReady) return
  await crearTcpServer()
  if (tunnelReady) return   // EADDRINUSE: ya listo
  await conectarSSH()
}

module.exports = {
  conectar,
  get comunidad()   { return poolComunidad },
  get gestion()     { return poolGestion },
  get integracion() { return poolIntegracion }
}
