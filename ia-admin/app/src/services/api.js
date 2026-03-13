/**
 * Helpers de fetch con JWT automático.
 *
 * apiFetch: drop-in de fetch() — retorna Response igual que fetch nativo.
 *   const res = await apiFetch('/api/ia/agentes-admin')
 *   const data = await res.json()
 *
 * api: retorna JSON directamente — versión corta.
 *   const data = await api('/api/ia/agentes-admin')
 */

function getToken() {
  return localStorage.getItem('ia_jwt') || ''
}

function handle401() {
  localStorage.removeItem('ia_jwt')
  localStorage.removeItem('ia_usuario')
  localStorage.removeItem('ia_empresa')
  window.location.hash = '/login'
}

export function apiFetch(url, options = {}) {
  const { headers = {}, ...rest } = options
  return fetch(url, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
      ...headers
    }
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
