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
const cjsSrc = SRC.replace(/export\s+function/g, 'function') + '\nmodule.exports = { localDate, localMonth, localDatetime, fmtDatetime }'
const mod = { exports: {} }
new Function('module', cjsSrc)(mod)
const { localDate, localMonth, localDatetime, fmtDatetime } = mod.exports

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

describe('localDatetime() — ia-admin', () => {
  test('devuelve formato ISO 8601 con offset -05:00', () => {
    const ts = localDatetime()
    assert.match(ts, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-05:00$/)
  })

  test('una fecha fija UTC devuelve su equivalente en offset COL', () => {
    // 2026-04-24 18:00 UTC = 13:00 COL
    const d = new Date('2026-04-24T18:00:00Z')
    assert.equal(localDatetime(d), '2026-04-24T13:00:00-05:00')
  })

  test('medianoche UTC (19:00 COL día anterior) devuelve día anterior en la salida', () => {
    const d = new Date('2026-04-25T00:00:00Z')
    assert.equal(localDatetime(d), '2026-04-24T19:00:00-05:00')
  })

  test('el string producido es parseable por Date() y representa el mismo instante', () => {
    const original = new Date('2026-04-24T18:00:00Z')
    const reparsed = new Date(localDatetime(original))
    assert.equal(reparsed.getTime(), original.getTime())
  })
})

describe('fmtDatetime() — ia-admin', () => {
  test('input vacío retorna "—"', () => {
    assert.equal(fmtDatetime(null), '—')
    assert.equal(fmtDatetime(undefined), '—')
    assert.equal(fmtDatetime(''), '—')
  })

  test('formatea en hora Colombia independiente del input timezone', () => {
    // Un ISO UTC y su equivalente ISO con offset-05:00 representan el mismo instante:
    // 2026-04-24 18:00 UTC = 13:00 COL.
    const resUtc = fmtDatetime('2026-04-24T18:00:00Z')
    const resCol = fmtDatetime('2026-04-24T13:00:00-05:00')
    assert.equal(resUtc, resCol, 'misma hora en UTC y offset COL debe formatearse igual')
  })

  test('el output contiene la hora esperada en Colombia', () => {
    // 2026-04-24 18:00 UTC = 13:00 COL.  'es-CO' con timeStyle: 'short' suele dar "1:00 p. m." o "13:00".
    const res = fmtDatetime('2026-04-24T18:00:00Z')
    assert.ok(res && res !== '—', 'no debe retornar placeholder')
    // No assertamos el formato exacto (varía con Intl impl), pero sí que NO contiene "6:00" (UTC)
    assert.ok(!/\b6:00\b/.test(res), `no debe mostrar hora UTC (6:00) — got: ${res}`)
  })
})
