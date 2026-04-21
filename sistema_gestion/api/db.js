/**
 * sistema_gestion/api/db.js
 * Wrapper sobre lib/db_conn.js — pools: comunidad (RO), gestion (RW), integracion (RO), inventario (RO).
 * Todas las credenciales viven en `integracion_conexionesbd.env` de la raíz del repo.
 */
const central = require('../../lib/db_conn')

let _comunidad = null
let _gestion = null
let _integracion = null
let _inventario = null

async function conectar() {
  [_comunidad, _gestion, _integracion] = await Promise.all([
    central.comunidad(),
    central.gestion(),
    central.integracion(),
  ])
  _inventario = central.local('os_inventario')
  console.log(`[db] Pools listos — timezone: ${central.TIMEZONE}`)
}

module.exports = {
  conectar,
  get comunidad()   { return _comunidad },
  get gestion()     { return _gestion },
  get integracion() { return _integracion },
  get inventario()  { return _inventario },
}
