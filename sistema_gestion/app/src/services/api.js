const KEY_JWT = 'gestion_jwt'

function getToken() { return localStorage.getItem(KEY_JWT) || '' }

function handle401() {
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
    if (res.status === 401) { handle401(); throw new Error('Sesión expirada') }
    return res
  })
}

export async function api(url, options = {}) {
  const res = await apiFetch(url, options)
  if (!res.ok) { const e = await res.text(); throw new Error(e || `Error ${res.status}`) }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res.text()
}
