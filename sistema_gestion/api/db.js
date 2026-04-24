/**
 * sistema_gestion/api/db.js
 * Wrapper sobre lib/db_conn.js — pools: master, gestion, integracion, comunidad.
 *
 * MASTER = fuente de verdad de usuarios/empresas/roles (reemplaza comunidad
 * desde 2026-04-24, tras aislar Hostinger).
 *
 * Getters dinámicos: leen el pool actual del helper central EN CADA ACCESO.
 * Si el SSH tunnel se reconecta, el pool se recrea automáticamente y todos
 * los `db.gestion.query(...)` posteriores usan el nuevo pool sin cachear uno viejo.
 */
const central = require('../../lib/db_conn')

async function conectar() {
  // master/gestion/integracion viven en VPS Contabo (misma red local para el server
  // que corre allí; SSH para el local). comunidad (Hostinger) queda como legacy
  // opcional — algún query aún lo puede usar hasta refactor completo.
  await Promise.all([central.master(), central.gestion(), central.integracion()])
  intentarComunidad()
  console.log(`[db] Pools listos (master+gestion+integracion) — timezone: ${central.TIMEZONE}`)
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
}
