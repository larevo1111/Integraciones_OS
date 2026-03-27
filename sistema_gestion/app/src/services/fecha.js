/**
 * Utilidades de fecha — siempre hora local (Colombia UTC-5).
 * NUNCA usar new Date().toISOString().slice(0,10) para "hoy",
 * porque después de las 7pm Colombia eso devuelve el día siguiente (UTC).
 */

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
