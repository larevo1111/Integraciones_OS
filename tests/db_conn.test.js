/**
 * Tests de lib/db_conn.js — helper único de conexiones a BD (Node).
 *
 * NO hace conexiones reales: mysql2.createPool es lazy (no conecta hasta que
 * ejecutes una query), así que validamos estructura, cache de pools y errores
 * de config sin necesitar una BD viva.
 */
const { test, describe } = require('node:test')
const assert = require('node:assert/strict')
const path = require('path')

const db = require(path.resolve(__dirname, '..', 'lib', 'db_conn'))

describe('API pública', () => {
  test('expone TIMEZONE como string', () => {
    assert.equal(typeof db.TIMEZONE, 'string')
    assert.match(db.TIMEZONE, /^[+-]\d{2}:\d{2}$/)
  })

  test('expone función local(dbName)', () => {
    assert.equal(typeof db.local, 'function')
  })

  test('expone funciones async para BDs remotas', () => {
    assert.equal(typeof db.integracion, 'function')
    assert.equal(typeof db.gestion, 'function')
    assert.equal(typeof db.inventario, 'function')
    assert.equal(typeof db.comunidad, 'function')
  })

  test('expone getters sync para pools remotos', () => {
    // Antes de que se llame a .integracion()/.gestion()/etc, los pools son null
    assert.equal(db.poolIntegracion, null)
    assert.equal(db.poolGestion, null)
    assert.equal(db.poolInventario, null)
    assert.equal(db.poolComunidad, null)
  })
})

describe('local(dbName) — pool a BD local', () => {
  test('retorna un objeto pool de mysql2', () => {
    const pool = db.local('effi_data')
    assert.ok(pool)
    assert.equal(typeof pool.execute, 'function')
    assert.equal(typeof pool.query, 'function')
    assert.equal(typeof pool.end, 'function')
  })

  test('cachea pools por nombre de BD — dos llamadas = misma instancia', () => {
    const p1 = db.local('effi_data')
    const p2 = db.local('effi_data')
    assert.equal(p1, p2)
  })

  test('pools de distintas BDs son instancias distintas', () => {
    const pEffi = db.local('effi_data')
    const pOtro = db.local('otra_bd_test')
    assert.notEqual(pEffi, pOtro)
  })
})

describe('Config incompleta — errores claros', () => {
  // Guardar/restaurar env para no contaminar otros tests.
  let envBackup
  test.beforeEach(() => {
    envBackup = { ...process.env }
  })
  test.afterEach(() => {
    process.env = envBackup
  })

  test('integracion() sin DB_INTEGRACION_NAME lanza error explícito', async () => {
    delete process.env.DB_INTEGRACION_NAME
    await assert.rejects(
      () => db.integracion(),
      /Config DB_INTEGRACION_\* incompleta/
    )
  })
})

describe('TIMEZONE — consistencia con lib/timezone.js', () => {
  test('db.TIMEZONE y timezone.TZ_OFFSET son el mismo valor', () => {
    const { TZ_OFFSET } = require(path.resolve(__dirname, '..', 'lib', 'timezone'))
    assert.equal(db.TIMEZONE, TZ_OFFSET)
  })
})
