/**
 * Helper de parseo y formateo numérico.
 *
 * Detecta automáticamente formato US (1234.56), COP/EU miles (1.234.567),
 * COP/EU decimal-coma (1.234,56) o US miles (1,234,567).
 *
 * Heurística: el ÚLTIMO separador (`.` o `,`) es decimal si tiene 1, 2 o
 * más de 3 dígitos después. Si tiene exactamente 3, se asume miles
 * (lo más común en es-CO, donde 1.234 = mil doscientos treinta y cuatro).
 *
 * Casos cubiertos:
 *   "1743406.00" → 1743406         (formato MySQL DECIMAL stringified)
 *   "1.234.567"  → 1234567         (formato COP / es-CO miles)
 *   "1.234,56"   → 1234.56         (formato es-CO con decimales)
 *   "1,234.56"   → 1234.56         (formato US con miles)
 *   "1,234,567"  → 1234567         (formato US miles, sin decimales)
 *   "45.2"       → 45.2
 *   "$1.234"     → 1234            (asume miles)
 *   "-100.50"    → -100.5
 */
export function parseNumeroFlexible(val) {
  if (val === null || val === undefined || val === '') return NaN
  const raw = String(val).replace(/[$%\s]/g, '').trim()
  if (raw === '' || raw === '-' || raw === '—') return NaN

  const sign = raw.startsWith('-') ? -1 : 1
  const body = raw.replace(/^-/, '')

  if (!/[.,]/.test(body)) {
    const n = Number(body)
    return Number.isFinite(n) ? sign * n : NaN
  }

  const lastDot = body.lastIndexOf('.')
  const lastComma = body.lastIndexOf(',')
  const lastSep = Math.max(lastDot, lastComma)
  const digitsAfter = body.length - lastSep - 1

  let normalized
  if (digitsAfter === 1 || digitsAfter === 2 || digitsAfter > 3) {
    // último separador = decimal
    normalized = body.slice(0, lastSep).replace(/[.,]/g, '') + '.' + body.slice(lastSep + 1)
  } else {
    // último separador = miles (3 dígitos después)
    normalized = body.replace(/[.,]/g, '')
  }

  const n = Number(normalized)
  return Number.isFinite(n) ? sign * n : NaN
}

/**
 * Formatea un número en estilo es-CO: punto separador de miles,
 * coma decimal. Decimales detectados automáticamente.
 *
 *   1234567        → "1.234.567"
 *   1234.56        → "1.234,56"
 *   45.2           → "45,2"
 *   100            → "100"
 *
 * @param {number|string} n  número a formatear
 * @param {object} opts      { maxDec?: 3, minDec?: 0 }
 */
export function fmtNum(n, opts = {}) {
  if (n === null || n === undefined || n === '' || n === '—') return '—'
  const num = typeof n === 'number' ? n : parseNumeroFlexible(n)
  if (!Number.isFinite(num)) return '—'

  const maxDec = opts.maxDec ?? 3
  const minDec = opts.minDec ?? 0

  const fracStr = String(num.toFixed(maxDec)).split('.')[1] || ''
  const decimals = Math.max(minDec, fracStr.replace(/0+$/, '').length)

  return num.toLocaleString('es-CO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * Heurística: ¿este string parece un número? Acepta los mismos formatos
 * que `parseNumeroFlexible`. Útil para detectar columnas numéricas.
 */
export function esNumero(val) {
  if (val === null || val === undefined || val === '') return true  // vacío = compatible
  return Number.isFinite(parseNumeroFlexible(val))
}
