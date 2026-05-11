/**
 * sistema_gestion/api/db.js
 * Wrapper sobre lib/db_conn.js — pools: master, gestion, integracion, inventario, comunidad.
 *
 * MASTER = fuente de verdad de usuarios/empresas/roles. Reside en POSTGRES
 * desde el 9-may-2026 (migrado de MariaDB). El helper central expone un
 * adapter mysql2-compat → las queries siguen usando `?` y `const [rows] = ...`.
 *
 * GESTION / INTEGRACION / INVENTARIO / COMUNIDAD = MariaDB (sin cambios).
 *
 * Getters dinámicos: leen el pool actual del helper central EN CADA ACCESO.
 * Si el SSH tunnel se reconecta, el pool se recrea y los consumers ven el nuevo.
 */
const central = require('../../lib/db_conn')

async function conectar() {
  // master en Postgres (local, sin SSH). gestion/integracion/inventario en
  // MariaDB local (mismo VPS). comunidad en Hostinger (legacy, opcional).
  await Promise.all([central.master(), central.gestion(), central.integracion(), central.inventario()])
  intentarComunidad()
  console.log(`[db] Pools listos (master Postgres + gestion/integracion/inventario MariaDB) — timezone: ${central.TIMEZONE}`)
}

async function intentarComunidad() {
  try {
    await central.comunidad()
    console.log('[db] comunidad (Hostinger) listo (legacy)')
  } catch (err) {
    console.warn('[db] comunidad reintentando en 15s:', err.message)
    setTimeout(intentarComunidad, 15000)
  }
}

module.exports = {
  conectar,
  get master()      { return central.poolMaster },
  get comunidad()   { return central.poolComunidad },
  get gestion()     { return central.poolGestion },
  get integracion() { return central.poolIntegracion },
  get inventario()  { return central.poolInventario },
}
