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
  // está en Hostinger (SSH externo, a veces falla handshake) — no bloquea arranque,
  // se reintenta cada 15s hasta que conecte.
  await Promise.all([central.gestion(), central.integracion()])
  intentarComunidad()
  console.log(`[db] Pools listos (gestion+integracion) — timezone: ${central.TIMEZONE}`)
}

async function intentarComunidad() {
  try {
    await central.comunidad()
    console.log('[db] comunidad (Hostinger) listo')
  } catch (err) {
    console.warn('[db] comunidad reintentando en 15s:', err.message)
    setTimeout(intentarComunidad, 15000)
  }
}

module.exports = {
  conectar,
  get comunidad()   { return central.poolComunidad },
  get gestion()     { return central.poolGestion },
  get integracion() { return central.poolIntegracion },
}
