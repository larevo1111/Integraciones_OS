/**
 * Utilidades de fecha — SIEMPRE en timezone configurado en integracion_conexionesbd.env
 * (APP_TIMEZONE / APP_TIMEZONE_NAME, expuestos al frontend vía quasar.config.js build.env).
 *
 * NUNCA usar new Date().toISOString().slice(0,10) para "hoy",
 * porque después de las 7pm Colombia eso devuelve el día siguiente (UTC).
 */

/** Offset configurado en el .env central (ej: "-05:00"). Única fuente en el frontend. */
export const TZ_OFFSET = import.meta.env.VITE_APP_TIMEZONE || '-05:00'

/** Nombre IANA del timezone (ej: "America/Bogota"). */
export const TZ_NAME = import.meta.env.VITE_APP_TIMEZONE_NAME || 'America/Bogota'

/** YYYY-MM-DD en hora local */
export function localISO(d = new Date()) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

/** Hoy en YYYY-MM-DD local */
export function hoyLocal() {
  return localISO(new Date())
}

/** Mañana en YYYY-MM-DD local */
export function mananaLocal() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return localISO(d)
}

/**
 * Parsea un datetime del backend ("YYYY-MM-DD HH:MM:SS" sin offset) como hora del
 * timezone configurado. Evita que el browser asuma UTC u otra zona local.
 */
export function parseBackendDate(str) {
  if (!str) return null
  const s = String(str)
  if (s.includes('Z') || s.includes('+') || s.match(/-\d{2}:\d{2}$/)) return new Date(s)
  return new Date(s.replace(' ', 'T') + TZ_OFFSET)
}
