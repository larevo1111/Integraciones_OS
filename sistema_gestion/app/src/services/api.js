const KEY_JWT = 'gestion_jwt'

function getToken() { return localStorage.getItem(KEY_JWT) || '' }

function limpiarSesion() {
  localStorage.removeItem(KEY_JWT)
  localStorage.removeItem('gestion_usuario')
  localStorage.removeItem('gestion_empresa')
  window.location.hash = '/login'
}

export function apiFetch(url, options = {}) {
  const { headers = {}, ...rest } = options
  return fetch(url, {
    ...rest,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}`, ...headers }
  }).then(res => {
    if (res.status === 401) { limpiarSesion(); throw new Error('Sesión expirada') }
    return res
  })
}

export async function api(url, options = {}) {
  const res = await apiFetch(url, options)
  if (!res.ok) {
    let msg = `Error ${res.status}`
    try { const e = await res.json(); msg = e.error || msg } catch {}
    // 403 por token temporal → volver al login
    if (res.status === 403 && msg === 'Selección de empresa pendiente') limpiarSesion()
    throw new Error(msg)
  }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res.text()
}
