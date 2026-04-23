/**
 * sistema_gestion/api/db.js
 * Wrapper sobre lib/db_conn.js — pools: comunidad, gestion, integracion.
 *
 * Getters dinámicos: leen el pool actual del helper central EN CADA ACCESO.
 * Si el SSH tunnel se reconecta, el pool se recrea automáticamente y todos
 * los `db.gestion.query(...)` posteriores usan el nuevo pool sin cachear uno viejo.
 */
const central = require('../../lib/db_conn')

async function conectar() {
  // gestion/integracion son críticos (viven en VPS Contabo, misma red). comunidad
  // está en Hostinger (SSH externo, a veces falla handshake) — lo dejamos opcional:
  // si tarda demasiado, arranca igual e intenta reconectar en background después.
  await Promise.all([central.gestion(), central.integracion()])
  central.comunidad().catch(err => {
    console.warn('[db] comunidad (Hostinger) no disponible al arranque:', err.message)
  })
  console.log(`[db] Pools listos (gestion+integracion) — timezone: ${central.TIMEZONE}`)
}

module.exports = {
  conectar,
  get comunidad()   { return central.poolComunidad },
  get gestion()     { return central.poolGestion },
  get integracion() { return central.poolIntegracion },
}
