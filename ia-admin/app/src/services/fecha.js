/**
 * Helpers de fecha/timezone para ia-admin.
 *
 * Mantiene la misma semántica que lib/timezone.js (Node) y services/fecha.js
 * (frontend/sistema_gestion): todo en hora Colombia (America/Bogota).
 *
 * Uso:
 *   import { localDate, localMonth, localDatetime, fmtDatetime } from 'src/services/fecha'
 *   localDate()            // "2026-04-24"
 *   localMonth()           // "2026-04"
 *   localDatetime()        // "2026-04-24T13:45:30-05:00" (ISO válido con offset Colombia)
 *   fmtDatetime(ts)        // "24/04/2026 1:45 PM" (siempre en hora Colombia, no del navegador)
 *
 * Nota: ia-admin es un proyecto Quasar separado y no puede importar directamente
 * de ../../../../lib/timezone.js por las fronteras de build. Este archivo es la
 * copia mínima para ia-admin. Si cambia la zona horaria, sincronizar con el
 * TZ del resto del repo (APP_TIMEZONE_NAME en integracion_conexionesbd.env).
 */

const TZ_NAME = 'America/Bogota'
const TZ_OFFSET = '-05:00'

export function localDate(d = new Date()) {
  return d.toLocaleDateString('en-CA', {
    timeZone: TZ_NAME,
    year: 'numeric', month: '2-digit', day: '2-digit',
  })
}

export function localMonth(d = new Date()) {
  return localDate(d).slice(0, 7)
}

/**
 * Timestamp ISO 8601 con offset Colombia explícito. Reemplazo seguro de
 * `new Date().toISOString()` cuando querés guardar un "momento" sin depender
 * de la zona del servidor/navegador.
 */
export function localDatetime(d = new Date()) {
  // "YYYY-MM-DD HH:MM:SS" en hora Colombia (sv-SE locale da ese formato ordenado)
  const s = d.toLocaleString('sv-SE', { timeZone: TZ_NAME })
  return s.replace(' ', 'T') + TZ_OFFSET
}

/**
 * Formatea un timestamp (string ISO o Date) SIEMPRE en hora Colombia,
 * independiente de la zona del navegador. Devuelve '—' si el input es vacío.
 */
export function fmtDatetime(ts, opts = { dateStyle: 'short', timeStyle: 'short' }) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-CO', { timeZone: TZ_NAME, ...opts })
}
