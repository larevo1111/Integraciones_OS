/**
 * sistema_gestion/api/db.js
 * SSH tunnel → Hostinger MySQL 3306
 * 3 pools: comunidad (RO), gestion (RW), integracion (RO)
 */

const mysql  = require('mysql2/promise')
const { Client } = require('ssh2')
const net    = require('net')
const path   = require('path')
const fs     = require('fs')
const os     = require('os')

// ─── Config ────────────────────────────────────────────────────────
const SSH_HOST     = '109.106.250.195'
const SSH_PORT     = 65002
const SSH_USER     = 'u768061575'
const SSH_KEY_PATH = path.join(os.homedir(), '.ssh', 'sos_erp')
const MYSQL_HOST   = '127.0.0.1'
const MYSQL_PORT   = 3306
const LOCAL_PORT   = 3311   // Puerto local del tunnel (3308=ERP, 3310=gestion-test)

const DB_USER_GESTION    = 'u768061575_os_gestion'
const DB_PASS            = 'Epist2487.'
const DB_COMUNIDAD       = 'u768061575_os_comunidad'
const DB_GESTION         = 'u768061575_os_gestion'
const DB_INTEGRACION     = 'u768061575_os_integracion'

// ─── Estado del tunnel ─────────────────────────────────────────────
let sshClient   = null
let tcpServer   = null
let tunnelReady = false

// ─── Pools (se inicializan después de establecer el tunnel) ────────
let poolComunidad   = null
let poolGestion     = null
let poolIntegracion = null

/**
 * Establece el SSH tunnel y crea los 3 pools MySQL.
 * Retorna promise que resuelve cuando todo está listo.
 */
function conectar() {
  return new Promise((resolve, reject) => {
    if (tunnelReady) return resolve()

    const privateKey = fs.readFileSync(SSH_KEY_PATH)
    sshClient = new Client()

    tcpServer = net.createServer(localSocket => {
      sshClient.forwardOut(
        '127.0.0.1', LOCAL_PORT,
        MYSQL_HOST,  MYSQL_PORT,
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

    tcpServer.listen(LOCAL_PORT, '127.0.0.1', () => {
      sshClient.connect({
        host:       SSH_HOST,
        port:       SSH_PORT,
        username:   SSH_USER,
        privateKey
      })
    })

    tcpServer.on('error', err => {
      // Si el puerto ya está en uso, el tunnel probablemente ya existe
      if (err.code === 'EADDRINUSE') {
        console.log('[db] Puerto local ya en uso — asumiendo tunnel activo')
        crearPools()
        tunnelReady = true
        return resolve()
      }
      reject(err)
    })

    sshClient.on('ready', () => {
      console.log('[db] SSH tunnel establecido → Hostinger MySQL')
      crearPools()
      tunnelReady = true
      resolve()
    })

    sshClient.on('error', err => {
      console.error('[db] SSH error:', err.message)
      reject(err)
    })
  })
}

function crearPools() {
  const base = {
    host:             '127.0.0.1',
    port:             LOCAL_PORT,
    user:             DB_USER_GESTION,
    password:         DB_PASS,
    waitForConnections: true,
    connectionLimit:  10,
    timezone:         'local'
  }

  poolComunidad   = mysql.createPool({ ...base, database: DB_COMUNIDAD })
  poolGestion     = mysql.createPool({ ...base, database: DB_GESTION })
  poolIntegracion = mysql.createPool({ ...base, database: DB_INTEGRACION })
}

module.exports = {
  conectar,
  get comunidad()   { return poolComunidad },
  get gestion()     { return poolGestion },
  get integracion() { return poolIntegracion }
}
