import { auth } from './auth'

const BASE = window.location.origin

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  const t = auth.token
  if (t) headers['Authorization'] = `Bearer ${t}`

  const resp = await fetch(BASE + path, { ...options, headers })

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
