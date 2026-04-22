/**
 * Servicio único de duraciones de tareas (5S).
 *
 * Modelo de datos en backend (todas en segundos):
 *   - duracion_usuario_seg    → confirmada por el usuario en el modal
 *   - duracion_cronometro_seg → contador real del cronómetro (acumulado)
 *   - duracion_sistema_seg    → fecha_fin_real - fecha_inicio_real
 *
 * Campo interno (timestamp, no es duración):
 *   - crono_inicio (DATETIME) → cuándo arrancó el contador en curso. NULL si pausado.
 *
 * Reglas:
 *   - En tareas "En Progreso": duracion_usuario_seg = duracion_cronometro_seg SIEMPRE
 *   - Cuando crono_inicio NO es null, el valor real se calcula en vivo: acumulado + (NOW - crono_inicio)
 */

import { parseBackendDate } from './fecha'

// parseInicio: wrapper hacia el helper central (timezone desde .env vía quasar.config.js)
const parseInicio = parseBackendDate

/** Formato único: HH:MM:SS — usado en TODA la app. */
export function formatHHMMSS(seg) {
  if (!seg || seg < 0) seg = 0
  const total = Math.floor(seg)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/**
 * Devuelve el valor a mostrar para la tarea (en segundos).
 * - Pendiente → 0
 * - En Progreso con crono corriendo → cronómetro acumulado + delta NOW
 * - En Progreso pausado → cronómetro acumulado guardado
 * - Completada/Cancelada → duracion_usuario_seg (lo que confirmó el usuario en el modal)
 *
 * En En Progreso, duracion_usuario_seg debería estar igualada al crono pero usamos
 * crono_inicio + acumulado para tener el valor en vivo segundo a segundo.
 */
export function calcDuracionVivo(tarea) {
  if (!tarea) return 0
  if (tarea.estado === 'Pendiente') return 0
  if (tarea.estado === 'En Progreso') {
    let total = tarea.duracion_cronometro_seg || 0
    if (tarea.crono_inicio) {
      const ini = parseInicio(tarea.crono_inicio)
      if (ini) total += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
    }
    return total
  }
  // Completada o Cancelada → valor confirmado por el usuario
  return tarea.duracion_usuario_seg || 0
}

/**
 * Duración sistema en vivo: fecha_fin_real - fecha_inicio_real.
 * Si la tarea está en progreso, calcula con NOW.
 */
export function calcDuracionSistema(tarea) {
  if (!tarea) return 0
  // Si ya está guardada (Completada/Cancelada), usarla
  if (tarea.estado === 'Completada' || tarea.estado === 'Cancelada') {
    return tarea.duracion_sistema_seg || 0
  }
  // En progreso: calcular en vivo
  if (!tarea.fecha_inicio_real) return 0
  const ini = parseInicio(tarea.fecha_inicio_real)
  if (!ini) return 0
  return Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
}
