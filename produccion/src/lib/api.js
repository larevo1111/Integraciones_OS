import { auth } from './auth'

const BASE = window.location.origin

/**
 * Política de cache: GETs SIEMPRE bypass cache.
 * - Header no-cache (que browser/Cloudflare lo respeten)
 * - Cache-buster `_t=ts` en query (garantía 100% si headers se ignoran)
 * - fetch con cache:'no-store' (nivel browser)
 *
 * Razón: la app muestra datos que mutan vía POST/PATCH/DELETE; un GET cacheado
 * después de mutar muestra estado viejo y confunde al usuario.
 */
function bustCache(path) {
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}_t=${Date.now()}`
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  const t = auth.token
  if (t) headers['Authorization'] = `Bearer ${t}`

  const isGet = !options.method || options.method === 'GET'
  if (isGet) {
    headers['Cache-Control'] = 'no-cache'
    headers['Pragma'] = 'no-cache'
  }
  const url = isGet ? bustCache(path) : path

  const resp = await fetch(BASE + url, { ...options, headers, cache: 'no-store' })

  // Auto-logout si el token expiró / inválido (solo si había token)
  if (resp.status === 401 && t) {
    auth.logout()
  }

  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try {
      const data = await resp.json()
      msg = data.detail || msg
    } catch {}
    throw new Error(msg)
  }
  return resp.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),
}
