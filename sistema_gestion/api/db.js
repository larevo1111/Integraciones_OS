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
  await Promise.all([
    central.comunidad(),
    central.gestion(),
    central.integracion(),
  ])
  console.log(`[db] Pools listos — timezone: ${central.TIMEZONE}`)
}

module.exports = {
  conectar,
  get comunidad()   { return central.poolComunidad },
  get gestion()     { return central.poolGestion },
  get integracion() { return central.poolIntegracion },
}
