/**
 * Tests de ia-admin/app/src/services/fecha.js
 *
 * Helper de timezone local a ia-admin (no puede importar lib/timezone.js por
 * la frontera de build de Quasar). Tests verifican que mantiene la misma
 * semántica que lib/timezone.js: todo en hora Colombia.
 */
const { test, describe } = require('node:test')
const assert = require('node:assert/strict')
const path = require('path')
const fs = require('fs')

// El helper usa sintaxis ESM (export). Para testearlo con node:test (CJS),
// leemos el archivo, sacamos el `export`, y lo evaluamos en un contexto CJS.
const SRC = fs.readFileSync(
  path.resolve(__dirname, '..', 'ia-admin', 'app', 'src', 'services', 'fecha.js'),
  'utf8'
)
const cjsSrc = SRC.replace(/export\s+function/g, 'function') + '\nmodule.exports = { localDate, localMonth }'
const mod = { exports: {} }
new Function('module', cjsSrc)(mod)
const { localDate, localMonth } = mod.exports

describe('localDate() — ia-admin', () => {
  test('sin args devuelve formato YYYY-MM-DD', () => {
    assert.match(localDate(), /^\d{4}-\d{2}-\d{2}$/)
  })

  test('23:00 UTC del 24-abr (18:00 COL mismo día) → 2026-04-24', () => {
    const d = new Date('2026-04-24T23:00:00Z')
    assert.equal(localDate(d), '2026-04-24')
  })

  test('04:00 UTC del 25-abr (23:00 COL del 24) → 2026-04-24', () => {
    const d = new Date('2026-04-25T04:00:00Z')
    assert.equal(localDate(d), '2026-04-24')
  })

  test('05:00 UTC del 25-abr (00:00 COL del 25) → 2026-04-25', () => {
    const d = new Date('2026-04-25T05:00:00Z')
    assert.equal(localDate(d), '2026-04-25')
  })
})

describe('localMonth() — ia-admin', () => {
  test('sin args devuelve formato YYYY-MM', () => {
    assert.match(localMonth(), /^\d{4}-\d{2}$/)
  })

  test('último día del mes a las 23:00 UTC (18:00 COL mismo día) → mes actual, NO mes siguiente', () => {
    // Regresión del bug original: toISOString().slice(0,7) acá saltaba a mes siguiente
    const d = new Date('2026-04-30T23:00:00Z')  // 30-abr 18:00 COL
    assert.equal(localMonth(d), '2026-04')
  })

  test('último día del mes a las 04:59 UTC del 1-may (23:59 COL del 30-abr) → 2026-04, NO 2026-05', () => {
    // Este es el caso crítico del bug: pre-fix devolvía "2026-05"
    const d = new Date('2026-05-01T04:59:00Z')
    assert.equal(localMonth(d), '2026-04')
  })

  test('primer minuto del mes en COL (05:00 UTC) → mes nuevo', () => {
    const d = new Date('2026-05-01T05:00:00Z')
    assert.equal(localMonth(d), '2026-05')
  })

  test('fecha tipo "Fri, 13 Mar 2026 00:00:00 GMT" (backend historico) → 2026-03, NO 2026-02', () => {
    // El backend devuelve este formato. 00:00 UTC del 13-mar = 19:00 COL del 12-mar.
    // Importante: debe devolver el mes real (marzo), no el COL (febrero).
    const d = new Date('Fri, 13 Mar 2026 00:00:00 GMT')
    // 00:00 UTC del 13-mar = 19:00 COL del 12-mar → localMonth devuelve '2026-03' si 12 es del mismo mes.
    assert.equal(localMonth(d), '2026-03')
  })
})
