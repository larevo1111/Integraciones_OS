// db.js — SSH tunnel + MySQL connection pool a Hostinger
const { spawn } = require('child_process')
const mysql = require('mysql2/promise')

const SSH_KEY    = '/home/osserver/.ssh/sos_erp'
const SSH_HOST   = '109.106.250.195'
const SSH_PORT   = 65002
const SSH_USER   = 'u768061575'
const LOCAL_PORT = 3308  // puerto local del tunnel (diferente al 3306 local)

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

async function startTunnel() {
  return new Promise((resolve, reject) => {
    // ssh -i key -p 65002 -L 3308:127.0.0.1:3306 u768061575@109.106.250.195 -N
    tunnelProcess = spawn('ssh', [
      '-i', SSH_KEY,
      '-p', String(SSH_PORT),
      '-L', `${LOCAL_PORT}:127.0.0.1:3306`,
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'ServerAliveInterval=30',
      '-N',
      `${SSH_USER}@${SSH_HOST}`
    ])
    tunnelProcess.on('error', reject)
    // Esperar 2s a que el tunnel levante
    setTimeout(resolve, 2000)
  })
}

async function getPool() {
  if (!pool) {
    await startTunnel()
    pool = mysql.createPool(DB_CONFIG)
  }
  return pool
}

async function query(sql, params = []) {
  const p = await getPool()
  const [rows] = await p.execute(sql, params)
  return rows
}

module.exports = { query, getPool }
