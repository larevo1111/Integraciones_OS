/**
 * lib/timezone.js — Fuente ÚNICA de timezone para todo el repo (Node).
 *
 * Lee APP_TIMEZONE desde `integracion_conexionesbd.env` (cargado por db_conn.js).
 * Si cambia el país de operación → se edita UNA vez el .env, nada más.
 *
 * Reglas:
 *   - Ningún archivo debe hardcodear "-05:00" ni "America/Bogota".
 *   - Para parsear horas HH:MM del usuario usar `parseHora()`.
 *   - Para fecha local YYYY-MM-DD usar `localDate()`.
 *   - Para insertar/leer en MySQL pasar `TZ_OFFSET` al pool (ya lo hace db_conn.js).
 *
 * Uso:
 *   const { TZ_OFFSET, TZ_NAME, localDate, parseHora } = require('./timezone')
 */
// Se asume que integracion_conexionesbd.env ya fue cargado por db_conn.js al require'arlo.
// Si no, este require fuerza la carga.
require('./db_conn')

const TZ_OFFSET = process.env.APP_TIMEZONE || process.env.DB_TIMEZONE || '-05:00'
const TZ_NAME   = process.env.APP_TIMEZONE_NAME || 'America/Bogota'

/** Fecha YYYY-MM-DD en timezone configurado, sin depender del OS del servidor. */
function localDate(d = new Date()) {
  return d.toLocaleDateString('en-CA', {
    timeZone: TZ_NAME,
    year: 'numeric', month: '2-digit', day: '2-digit',
  })
}

/**
 * Parsea un datetime del backend ("YYYY-MM-DD HH:MM:SS" sin offset) como hora
 * del timezone configurado. Evita que Node asuma UTC u otra zona local.
 *
 * Mirror de `sistema_gestion/app/src/services/fecha.js#parseBackendDate` —
 * cualquier cambio debe sincronizar ambos lados.
 *
 * Úsalo SIEMPRE para `new Date(row.fecha_X)` cuando row viene del pool
 * (mysql2 con `dateStrings:true` devuelve strings sin offset).
 */
function parseBackendDate(str) {
  if (!str) return null
  const s = String(str)
  if (s.includes('Z') || s.includes('+') || s.match(/-\d{2}:\d{2}$/)) return new Date(s)
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return new Date(`${s}T00:00:00${TZ_OFFSET}`)
  return new Date(s.replace(' ', 'T') + TZ_OFFSET)
}

/**
 * Parsea una hora HH:MM o un datetime sin offset como si fuera hora local
 * del timezone configurado.
 *
 * - `parseHora('2026-04-21', '08:30')` → Date del 21-abr 08:30 Colombia.
 * - `parseHora(null, '2026-04-21T08:30')` → lo mismo.
 * - Si el string ya trae offset (`Z`, `+05:00`, etc.), lo respeta.
 *
 * Devuelve `null` si la entrada es vacía.
 */
function parseHora(fechaYYYYMMDD, hora) {
  if (!hora && !fechaYYYYMMDD) return null
  const s = hora == null ? '' : String(hora).trim()
  if (!s) return null

  // Solo HH:MM → necesita fecha
  if (s.match(/^\d{2}:\d{2}$/)) {
    if (!fechaYYYYMMDD) return null
    return new Date(`${fechaYYYYMMDD}T${s}:00${TZ_OFFSET}`)
  }
  // Ya trae offset explícito
  if (s.match(/[zZ]|[+-]\d{2}:?\d{2}$/)) return new Date(s)
  // Datetime sin offset → asumir local
  return new Date(`${s}${TZ_OFFSET}`)
}

module.exports = { TZ_OFFSET, TZ_NAME, localDate, parseHora, parseBackendDate }
