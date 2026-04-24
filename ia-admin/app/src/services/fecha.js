/**
 * Helpers de fecha/timezone para ia-admin.
 *
 * Mantiene la misma semántica que lib/timezone.js (Node) y services/fecha.js
 * (frontend/sistema_gestion): todo en hora Colombia (America/Bogota).
 *
 * Uso:
 *   import { localDate, localMonth } from 'src/services/fecha'
 *   localDate()            // "2026-04-24"
 *   localMonth()           // "2026-04"
 *   localMonth(new Date(f))
 *
 * Nota: ia-admin es un proyecto Quasar separado y no puede importar directamente
 * de ../../../../lib/timezone.js por las fronteras de build. Este archivo es la
 * copia mínima para ia-admin. Si cambia la zona horaria, sincronizar con el
 * TZ del resto del repo (APP_TIMEZONE_NAME en integracion_conexionesbd.env).
 */

const TZ_NAME = 'America/Bogota'

export function localDate(d = new Date()) {
  return d.toLocaleDateString('en-CA', {
    timeZone: TZ_NAME,
    year: 'numeric', month: '2-digit', day: '2-digit',
  })
}

export function localMonth(d = new Date()) {
  return localDate(d).slice(0, 7)
}
