/**
 * Tests de lib/timezone.js — helper único de timezone del repo.
 *
 * Corre con: npm test
 *
 * Los tests asumen los defaults del helper (APP_TIMEZONE=-05:00, APP_TIMEZONE_NAME=America/Bogota)
 * porque el `integracion_conexionesbd.env` real está gitignored y en CI no existe.
 */
const { test, describe } = require('node:test')
const assert = require('node:assert/strict')
const path = require('path')

const { TZ_OFFSET, TZ_NAME, localDate, parseHora } = require(path.resolve(__dirname, '..', 'lib', 'timezone'))

describe('TZ_OFFSET / TZ_NAME', () => {
  test('TZ_OFFSET tiene valor default -05:00 cuando no hay env', () => {
    assert.equal(TZ_OFFSET, '-05:00')
  })

  test('TZ_NAME tiene valor default America/Bogota cuando no hay env', () => {
    assert.equal(TZ_NAME, 'America/Bogota')
  })
})

describe('localDate()', () => {
  test('sin argumentos devuelve string formato YYYY-MM-DD', () => {
    const hoy = localDate()
    assert.match(hoy, /^\d{4}-\d{2}-\d{2}$/)
  })

  test('a las 18:00 UTC del 24-abr (13:00 COL mismo día) devuelve 2026-04-24', () => {
    const d = new Date('2026-04-24T18:00:00Z')
    assert.equal(localDate(d), '2026-04-24')
  })

  test('a las 04:00 UTC del 25-abr (23:00 COL del 24) devuelve 2026-04-24', () => {
    // Este es el caso crítico que rompe `toISOString().slice(0,10)`:
    // en UTC es ya día 25, pero en Colombia todavía es día 24.
    const d = new Date('2026-04-25T04:00:00Z')
    assert.equal(localDate(d), '2026-04-24')
  })

  test('a las 05:00 UTC del 25-abr (00:00 COL del 25) devuelve 2026-04-25', () => {
    const d = new Date('2026-04-25T05:00:00Z')
    assert.equal(localDate(d), '2026-04-25')
  })

  test('a medianoche UTC (19:00 COL día anterior) devuelve día anterior', () => {
    const d = new Date('2026-04-25T00:00:00Z')
    assert.equal(localDate(d), '2026-04-24')
  })

  test('fecha de enero (sin DST issues) 15-ene 12:00 UTC devuelve 2026-01-15', () => {
    const d = new Date('2026-01-15T12:00:00Z')
    assert.equal(localDate(d), '2026-01-15')
  })
})

describe('parseHora()', () => {
  test('sin fecha ni hora retorna null', () => {
    assert.equal(parseHora(null, null), null)
  })

  test('hora vacía string retorna null', () => {
    assert.equal(parseHora('2026-04-24', ''), null)
  })

  test('solo HH:MM sin fecha retorna null', () => {
    assert.equal(parseHora(null, '08:30'), null)
  })

  test('HH:MM con fecha interpreta como hora Colombia', () => {
    const d = parseHora('2026-04-24', '08:30')
    // 08:30 COL = 13:30 UTC
    assert.equal(d.toISOString(), '2026-04-24T13:30:00.000Z')
  })

  test('datetime sin offset se interpreta como hora Colombia', () => {
    const d = parseHora(null, '2026-04-24T08:30')
    assert.equal(d.toISOString(), '2026-04-24T13:30:00.000Z')
  })

  test('datetime con Z (UTC) respeta UTC', () => {
    const d = parseHora(null, '2026-04-24T08:30:00Z')
    assert.equal(d.toISOString(), '2026-04-24T08:30:00.000Z')
  })

  test('datetime con offset explícito +02:00 respeta offset', () => {
    const d = parseHora(null, '2026-04-24T08:30:00+02:00')
    // 08:30 UTC+2 = 06:30 UTC
    assert.equal(d.toISOString(), '2026-04-24T06:30:00.000Z')
  })

  test('datetime con offset explícito -05:00 (Colombia) respeta offset', () => {
    const d = parseHora(null, '2026-04-24T08:30:00-05:00')
    assert.equal(d.toISOString(), '2026-04-24T13:30:00.000Z')
  })

  test('hora 00:00 del primer día del mes interpreta bien', () => {
    const d = parseHora('2026-05-01', '00:00')
    // 00:00 COL del 1-may = 05:00 UTC del 1-may
    assert.equal(d.toISOString(), '2026-05-01T05:00:00.000Z')
  })

  test('hora 23:59 del último día del mes interpreta bien', () => {
    const d = parseHora('2026-04-30', '23:59')
    // 23:59 COL del 30-abr = 04:59 UTC del 1-may
    assert.equal(d.toISOString(), '2026-05-01T04:59:00.000Z')
  })
})
