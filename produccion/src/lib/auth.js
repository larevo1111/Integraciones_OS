/**
 * Store de auth simple basado en localStorage + eventos.
 * Usa el mismo patrón que sistema_gestion (JWT, usuario, tema).
 */

const KEY_JWT = 'produccion_jwt'
const KEY_USUARIO = 'produccion_usuario'

function decodePayload(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch { return null }
}

function isExpired(token) {
  const p = decodePayload(token)
  if (!p || !p.exp) return true
  return p.exp * 1000 < Date.now()
}

function leer() {
  const token = localStorage.getItem(KEY_JWT)
  if (!token || isExpired(token)) return { token: null, usuario: null }
  let usuario
  try { usuario = JSON.parse(localStorage.getItem(KEY_USUARIO) || 'null') }
  catch { usuario = null }
  if (!usuario) {
    const p = decodePayload(token)
    if (p) usuario = { email: p.email, nombre: p.nombre, nivel: p.nivel, foto: p.foto || '' }
  }
  return { token, usuario }
}

const listeners = new Set()

export const auth = {
  get token()   { return leer().token },
  get usuario() { return leer().usuario },
  get isAuth()  { return !!leer().token },

  login(token, usuario) {
    localStorage.setItem(KEY_JWT, token)
    localStorage.setItem(KEY_USUARIO, JSON.stringify(usuario))
    listeners.forEach(fn => fn())
  },
  logout() {
    localStorage.removeItem(KEY_JWT)
    localStorage.removeItem(KEY_USUARIO)
    listeners.forEach(fn => fn())
  },
  subscribe(fn) {
    listeners.add(fn)
    return () => listeners.delete(fn)
  },
}
