/**
 * Cronómetro — fuente de verdad única.
 * calcTotalSeg(tarea) → total de segundos (acumulado + intervalo activo)
 * formatCrono(seg) → "HH:MM:SS"
 */

function parseInicio(str) {
  if (!str) return null
  if (str.includes('Z') || str.includes('+') || str.includes('-', 10)) return new Date(str)
  return new Date(str.replace(' ', 'T') + '-05:00')
}

export function calcTotalSeg(tarea) {
  if (!tarea) return 0
  let total = tarea.crono_acumulado_seg || 0
  if (tarea.crono_inicio) {
    const ini = parseInicio(tarea.crono_inicio)
    if (ini) total += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))
  }
  return total
}

export function formatCrono(totalSeg) {
  const h = Math.floor(totalSeg / 3600)
  const m = Math.floor((totalSeg % 3600) / 60)
  const s = totalSeg % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
