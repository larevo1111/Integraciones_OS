/**
 * frontend/api/db.js
 * Wrapper sobre lib/db_conn.js — pool único a BD integración.
 * Todas las credenciales viven en `integracion_conexionesbd.env` de la raíz del repo.
 */
const central = require('../../lib/db_conn')

let _pool = null

async function getPool() {
  if (!_pool) _pool = await central.integracion()
  return _pool
}

async function query(sql, params = []) {
  const p = await getPool()
  try {
    const [rows] = await p.execute(sql, params)
    return rows
  } catch (err) {
    if (err.code === 'ECONNREFUSED' || err.code === 'PROTOCOL_CONNECTION_LOST') {
      _pool = null
    }
    throw err
  }
}

module.exports = { query, getPool }
