/**
 * lib/db_conn.js — Helper único de conexiones a BD (Node)
 * Lee credenciales de `integracion_conexionesbd.env` en la raíz del repo.
 * Provee pools mysql2 para BDs locales y remotas (via SSH tunnel con ssh2).
 *
 * Uso:
 *   const db = require('../../lib/db_conn')
 *   const poolEffi = await db.local('effi_data')
 *   const poolGes  = await db.gestion()
 *   const [rows]   = await poolGes.execute('SELECT 1')
 *
 * Cada BD remota usa su propio puerto local para evitar colisión cuando
 * se abren múltiples tuneles simultáneos (VPS + Hostinger).
 */

const mysql = require('mysql2/promise')
const net   = require('net')
const fs    = require('fs')
const path  = require('path')
// ssh2 se carga lazy — solo módulos que llaman a .integracion()/.gestion()/.comunidad() lo necesitan
let _ssh2 = null
function _loadSSH2() {
  if (!_ssh2) _ssh2 = require('ssh2')
  return _ssh2
}

// ─── Cargar .env central ─────────────────────────────────────────────
const ENV_PATH = path.resolve(__dirname, '..', 'integracion_conexionesbd.env')
function cargarEnv(ruta) {
  if (!fs.existsSync(ruta)) {
    console.warn(`[db_conn] WARN: ${ruta} no existe, usando variables de entorno del sistema`)
    return
  }
  fs.readFileSync(ruta, 'utf8').split('\n').forEach(linea => {
    const l = linea.trim()
    if (!l || l.startsWith('#')) return
    const i = l.indexOf('=')
    if (i < 0) return
    const k = l.slice(0, i).trim()
    const v = l.slice(i + 1).trim()
    if (!(k in process.env)) process.env[k] = v
  })
}
cargarEnv(ENV_PATH)

// TIMEZONE — lee de APP_TIMEZONE (fuente única); DB_TIMEZONE queda como alias legacy.
const TIMEZONE = process.env.APP_TIMEZONE || process.env.DB_TIMEZONE || '-05:00'

// ─── Lectura de config ───────────────────────────────────────────────
function _cfgLocal() {
  return {
    host: process.env.DB_LOCAL_HOST || '127.0.0.1',
    port: parseInt(process.env.DB_LOCAL_PORT || '3306', 10),
    user: process.env.DB_LOCAL_USER,
    password: process.env.DB_LOCAL_PASS,
  }
}

function _cfgRemota(prefijo) {
  const P = prefijo
  return {
    sshHost:    process.env[`DB_${P}_SSH_HOST`],
    sshPort:    parseInt(process.env[`DB_${P}_SSH_PORT`] || '22', 10),
    sshUser:    process.env[`DB_${P}_SSH_USER`],
    sshKey:     process.env[`DB_${P}_SSH_KEY`],
    remoteHost: process.env[`DB_${P}_REMOTE_HOST`] || '127.0.0.1',
    remotePort: parseInt(process.env[`DB_${P}_REMOTE_PORT`] || '3306', 10),
    localPort:  parseInt(process.env[`DB_${P}_LOCAL_PORT`], 10),
    dbName:     process.env[`DB_${P}_NAME`],
    dbUser:     process.env[`DB_${P}_USER`],
    dbPass:     process.env[`DB_${P}_PASS`],
  }
}

// ─── Pools locales (cached por nombre de BD) ─────────────────────────
const _poolsLocales = {}
function poolLocal(dbName) {
  if (_poolsLocales[dbName]) return _poolsLocales[dbName]
  const c = _cfgLocal()
  const pool = mysql.createPool({
    ...c, database: dbName,
    timezone: TIMEZONE, dateStrings: true,
    waitForConnections: true, connectionLimit: 10,
  })
  pool.pool.on('connection', conn => {
    conn.query(`SET time_zone = '${TIMEZONE}'`)
  })
  _poolsLocales[dbName] = pool
  return pool
}

// ─── Conexiones remotas (SSH tunnel + pool por prefijo) ──────────────
const _remotas = {
  INTEGRACION: { sshClient: null, tcpServer: null, ready: false, pool: null, reconectando: false },
  GESTION:     { sshClient: null, tcpServer: null, ready: false, pool: null, reconectando: false },
  INVENTARIO:  { sshClient: null, tcpServer: null, ready: false, pool: null, reconectando: false },
  COMUNIDAD:   { sshClient: null, tcpServer: null, ready: false, pool: null, reconectando: false },
}

function _crearPoolRemoto(prefijo, cfg) {
  const st = _remotas[prefijo]
  st.pool = mysql.createPool({
    host: '127.0.0.1', port: cfg.localPort,
    user: cfg.dbUser, password: cfg.dbPass, database: cfg.dbName,
    timezone: TIMEZONE, dateStrings: true,
    waitForConnections: true, connectionLimit: 10,
  })
  st.pool.pool.on('connection', conn => {
    conn.query(`SET time_zone = '${TIMEZONE}'`)
  })
}

function _destruirPoolRemoto(prefijo) {
  const st = _remotas[prefijo]
  if (st.pool) st.pool.end().catch(() => {})
  st.pool = null
}

function _conectarSSH(prefijo, cfg) {
  const st = _remotas[prefijo]
  return new Promise((resolve, reject) => {
    if (st.sshClient) { try { st.sshClient.destroy() } catch (_) {} st.sshClient = null }
    const key = fs.readFileSync(cfg.sshKey)
    const { Client } = _loadSSH2()
    const client = new Client()
    st.sshClient = client

    client.on('ready', () => {
      console.log(`[db_conn:${prefijo}] SSH tunnel listo → ${cfg.sshUser}@${cfg.sshHost}:${cfg.sshPort}`)
      _crearPoolRemoto(prefijo, cfg)
      st.ready = true
      resolve()
    })
    client.on('error', err => {
      console.error(`[db_conn:${prefijo}] SSH error:`, err.message)
      if (!st.ready) reject(err)
    })
    client.on('close', () => {
      if (st.sshClient === client && st.ready) {
        console.log(`[db_conn:${prefijo}] SSH tunnel cerrado — programando reconexión`)
        st.ready = false
        _destruirPoolRemoto(prefijo)
        st.sshClient = null
        _programarReconexion(prefijo, cfg, 5000)
      }
    })
    client.connect({ host: cfg.sshHost, port: cfg.sshPort, username: cfg.sshUser, privateKey: key })
  })
}

function _crearTcpServer(prefijo, cfg) {
  const st = _remotas[prefijo]
  return new Promise((resolve, reject) => {
    st.tcpServer = net.createServer(localSock => {
      if (!st.sshClient) { localSock.end(); return }
      st.sshClient.forwardOut('127.0.0.1', cfg.localPort, cfg.remoteHost, cfg.remotePort,
        (err, stream) => {
          if (err) { console.error(`[db_conn:${prefijo}] forwardOut error:`, err.message); localSock.end(); return }
          localSock.pipe(stream).pipe(localSock)
          localSock.on('error', () => stream.end())
          stream.on('error', () => localSock.end())
        }
      )
    })
    st.tcpServer.on('error', err => {
      if (err.code === 'EADDRINUSE') {
        console.log(`[db_conn:${prefijo}] puerto ${cfg.localPort} ocupado — asumiendo tunnel activo`)
        _crearPoolRemoto(prefijo, cfg)
        st.ready = true
        return resolve()
      }
      reject(err)
    })
    st.tcpServer.listen(cfg.localPort, '127.0.0.1', () => resolve())
  })
}

function _programarReconexion(prefijo, cfg, delay) {
  const st = _remotas[prefijo]
  if (st.reconectando) return
  st.reconectando = true
  setTimeout(() => {
    _conectarSSH(prefijo, cfg)
      .then(() => { st.reconectando = false })
      .catch(err => {
        console.error(`[db_conn:${prefijo}] reconexión falló:`, err.message)
        st.reconectando = false
        _programarReconexion(prefijo, cfg, 15000)
      })
  }, delay)
}

// Detecta si la BD remota es realmente local (mismo servidor) — salta el tunnel SSH
function _esLocal(cfg) {
  const h = (cfg.sshHost || '').toLowerCase()
  return h === 'localhost' || h === '127.0.0.1' || h === '' || h === 'direct'
}

async function _conectarRemota(prefijo) {
  const st = _remotas[prefijo]
  if (st.ready && st.pool) return st.pool
  const cfg = _cfgRemota(prefijo)
  if (!cfg.dbName) {
    throw new Error(`Config DB_${prefijo}_* incompleta en integracion_conexionesbd.env`)
  }

  // Modo directo (sin SSH): cuando la BD está en el mismo servidor que esta app
  if (_esLocal(cfg)) {
    console.log(`[db_conn:${prefijo}] modo directo (sin SSH tunnel) → ${cfg.remoteHost}:${cfg.remotePort}`)
    st.pool = mysql.createPool({
      host: cfg.remoteHost, port: cfg.remotePort,
      user: cfg.dbUser, password: cfg.dbPass, database: cfg.dbName,
      timezone: TIMEZONE, dateStrings: true,
      waitForConnections: true, connectionLimit: 10,
    })
    st.pool.pool.on('connection', conn => {
      conn.query(`SET time_zone = '${TIMEZONE}'`)
    })
    st.ready = true
    return st.pool
  }

  // Modo SSH tunnel (default)
  if (!cfg.sshHost) {
    throw new Error(`Config DB_${prefijo}_SSH_* incompleta en integracion_conexionesbd.env`)
  }
  if (!st.tcpServer) await _crearTcpServer(prefijo, cfg)
  if (st.ready) return st.pool  // EADDRINUSE path
  await _conectarSSH(prefijo, cfg)
  return st.pool
}

// ─── API pública ─────────────────────────────────────────────────────
// Getters sync (poolGestion etc) leen del state interno EN CADA ACCESO, así
// cuando el SSH se reconecta y el pool se recrea, los consumers ven el pool
// nuevo sin tener que refrescar cachés locales.
module.exports = {
  TIMEZONE,
  // Pool a BD local
  local(dbName) { return poolLocal(dbName) },
  // Async: abren tunnel+pool si aún no listo. Usar en `conectar()` del bootstrap.
  integracion() { return _conectarRemota('INTEGRACION') },
  gestion()     { return _conectarRemota('GESTION') },
  inventario()  { return _conectarRemota('INVENTARIO') },
  comunidad()   { return _conectarRemota('COMUNIDAD') },
  // Sync getters al pool actual (pueden ser null si aún no conectado o cerrando)
  get poolIntegracion() { return _remotas.INTEGRACION.pool },
  get poolGestion()     { return _remotas.GESTION.pool },
  get poolInventario()  { return _remotas.INVENTARIO.pool },
  get poolComunidad()   { return _remotas.COMUNIDAD.pool },
}
