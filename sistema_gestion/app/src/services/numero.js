// Acepta coma o punto como separador decimal y devuelve Number o null.
export function parseDecimal(v) {
  if (v == null || v === '') return null
  const s = String(v).trim().replace(',', '.')
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}

// Formato de display en es-CO (coma decimal, sin ceros de relleno).
export function fmtNum(n, maxDec = 3) {
  if (n == null || !Number.isFinite(Number(n))) return ''
  return Number(n).toLocaleString('es-CO', { maximumFractionDigits: maxDec })
}
