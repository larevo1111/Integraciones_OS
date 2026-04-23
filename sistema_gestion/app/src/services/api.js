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
  const maxRetries = options.maxRetries ?? 5
  let intento = 0
  while (true) {
    const res = await apiFetch(url, options)
    if (res.ok) {
      const ct = res.headers.get('content-type') || ''
      return ct.includes('application/json') ? res.json() : res.text()
    }
    // 503 con flag retry → el server no puede atender (ej: sin Playwright), reintentar
    // hasta que Cloudflare rote al otro tunnel.
    if (res.status === 503 && intento < maxRetries) {
      try {
        const e = await res.clone().json()
        if (e?.retry) {
          intento++
          await new Promise(r => setTimeout(r, 800 + Math.random() * 600))
          continue
        }
      } catch {}
    }
    let msg = `Error ${res.status}`
    try { const e = await res.json(); msg = e.error || msg } catch {}
    if (res.status === 403 && msg === 'Selección de empresa pendiente') limpiarSesion()
    throw new Error(msg)
  }
}
