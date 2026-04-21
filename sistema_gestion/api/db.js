/**
 * sistema_gestion/api/db.js
 * Wrapper sobre lib/db_conn.js — 3 pools: comunidad (RO), gestion (RW), integracion (RO).
 * Todas las credenciales viven en `integracion_conexionesbd.env` de la raíz del repo.
 */
const central = require('../../lib/db_conn')

let _comunidad = null
let _gestion = null
let _integracion = null

async function conectar() {
  [_comunidad, _gestion, _integracion] = await Promise.all([
    central.comunidad(),
    central.gestion(),
    central.integracion(),
  ])
  console.log(`[db] Pools listos — timezone: ${central.TIMEZONE}`)
}

module.exports = {
  conectar,
  get comunidad()   { return _comunidad },
  get gestion()     { return _gestion },
  get integracion() { return _integracion },
}
