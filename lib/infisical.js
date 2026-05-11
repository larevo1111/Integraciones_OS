/**
 * Cliente Infisical para Node.js — con cache local cifrada y SSH key loader en memoria pura.
 *
 * Uso:
 *   const { get, getMany, getSSHKey } = require('./secrets');
 *
 *   const dbPass = await get('DB_LOCAL_PASS');             // path por defecto: /shared
 *   const dbPass = await get('DB_LOCAL_PASS', '/shared');  // path explícito
 *   const sshKey = await getSSHKey('VPS');                  // devuelve string crudo de la key
 *
 * Variables de entorno requeridas (en .env mínimo del servicio):
 *   INFISICAL_HOST          - https://vps-contabo.tail44c420.ts.net
 *   INFISICAL_PROJECT_ID    - a332fa07-1e9f-41eb-ad25-ba701da6c5bd
 *   INFISICAL_CLIENT_ID     - UUID del client
 *   INFISICAL_CLIENT_SECRET - secret hex
 *   INFISICAL_ENV           - prod | dev | staging (default: prod)
 *
 * Cache:
 *   Memoria por proceso (Map). TTL configurable, default 5 min.
 *   No persiste a disco (cache cifrada en disco la haremos cuando se valide piloto).
 */

const https = require('https');
const path = require('path');
const fs = require('fs');

const HOST = process.env.INFISICAL_HOST || 'https://vps-contabo.tail44c420.ts.net';
const PROJECT_ID = process.env.INFISICAL_PROJECT_ID || 'a332fa07-1e9f-41eb-ad25-ba701da6c5bd';
const CLIENT_ID = process.env.INFISICAL_CLIENT_ID;
const CLIENT_SECRET = process.env.INFISICAL_CLIENT_SECRET;
const ENV = process.env.INFISICAL_ENV || 'prod';
const CACHE_TTL_MS = parseInt(process.env.INFISICAL_CACHE_TTL_MS || '300000', 10); // 5 min

if (!CLIENT_ID || !CLIENT_SECRET) {
  // Carga desde archivo de bootstrap si las env vars no están (fallback útil en local)
  const bootstrapFile = '/home/osserver/tempoclv/.infisical_admin_bootstrap.env';
  if (fs.existsSync(bootstrapFile)) {
    const content = fs.readFileSync(bootstrapFile, 'utf8');
    const lines = content.split('\n');
    for (const line of lines) {
      const m = line.match(/^INFISICAL_(\w+)=(.+)$/);
      if (m) process.env[`INFISICAL_${m[1]}`] = m[2];
    }
  }
}

// Cache: Map<cacheKey, {value, expiresAt}>
const _cache = new Map();
let _accessToken = null;
let _tokenExpiresAt = 0;

function _httpRequest(method, urlPath, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(HOST + urlPath);
    const opts = {
      method,
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname + url.search,
      headers: { 'Content-Type': 'application/json', ...headers },
    };
    const req = https.request(opts, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        try {
          const parsed = data ? JSON.parse(data) : null;
          resolve({ status: res.statusCode, body: parsed });
        } catch (e) {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function _ensureToken() {
  const now = Date.now();
  if (_accessToken && now < _tokenExpiresAt - 30000) return _accessToken; // 30s margin

  const clientId = process.env.INFISICAL_CLIENT_ID;
  const clientSecret = process.env.INFISICAL_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    throw new Error('INFISICAL_CLIENT_ID y INFISICAL_CLIENT_SECRET requeridos');
  }
  const { status, body } = await _httpRequest(
    'POST',
    '/api/v1/auth/universal-auth/login',
    { clientId, clientSecret }
  );
  if (status !== 200 || !body.accessToken) {
    throw new Error(`Infisical login failed: HTTP ${status} ${JSON.stringify(body).slice(0, 200)}`);
  }
  _accessToken = body.accessToken;
  _tokenExpiresAt = now + (body.expiresIn || 2592000) * 1000;
  return _accessToken;
}

/**
 * Obtiene un secret de Infisical (con cache).
 *
 * @param {string} key - nombre del secret (ej: 'DB_LOCAL_PASS')
 * @param {string} folder - folder/path (ej: '/shared', default '/shared')
 * @param {object} opts - { ttlMs, env, force }
 * @returns {Promise<string>} valor del secret
 */
async function get(key, folder = '/shared', opts = {}) {
  const env = opts.env || ENV;
  const cacheKey = `${env}:${folder}:${key}`;
  const now = Date.now();

  if (!opts.force) {
    const cached = _cache.get(cacheKey);
    if (cached && cached.expiresAt > now) return cached.value;
  }

  const token = await _ensureToken();
  const params = new URLSearchParams({
    workspaceId: PROJECT_ID,
    environment: env,
    secretPath: folder,
  });
  const { status, body } = await _httpRequest(
    'GET',
    `/api/v3/secrets/raw/${encodeURIComponent(key)}?${params}`,
    null,
    { Authorization: `Bearer ${token}` }
  );
  if (status !== 200) {
    throw new Error(`Infisical GET ${folder}/${key} failed: HTTP ${status} ${JSON.stringify(body).slice(0, 200)}`);
  }
  const value = body?.secret?.secretValue ?? body?.secretValue;
  if (value === undefined) {
    throw new Error(`Infisical: secret '${folder}/${key}' sin valor en respuesta`);
  }
  _cache.set(cacheKey, { value, expiresAt: now + (opts.ttlMs || CACHE_TTL_MS) });
  return value;
}

/**
 * Obtiene múltiples secrets de UN folder de una sola vez (más eficiente).
 *
 * @param {string} folder - path del folder (ej: '/shared')
 * @returns {Promise<Object>} { KEY1: value1, KEY2: value2, ... }
 */
async function getMany(folder = '/shared', opts = {}) {
  const env = opts.env || ENV;
  const token = await _ensureToken();
  const params = new URLSearchParams({
    workspaceId: PROJECT_ID,
    environment: env,
    secretPath: folder,
  });
  const { status, body } = await _httpRequest(
    'GET',
    `/api/v3/secrets/raw?${params}`,
    null,
    { Authorization: `Bearer ${token}` }
  );
  if (status !== 200) {
    throw new Error(`Infisical getMany ${folder} failed: HTTP ${status}`);
  }
  const result = {};
  const now = Date.now();
  for (const s of body.secrets || []) {
    result[s.secretKey] = s.secretValue;
    _cache.set(`${env}:${folder}:${s.secretKey}`, {
      value: s.secretValue,
      expiresAt: now + (opts.ttlMs || CACHE_TTL_MS),
    });
  }
  return result;
}

/**
 * Obtiene una SSH key privada de Infisical como string (para uso en memoria pura).
 * No escribe a disco.
 *
 * @param {string} which - 'VPS' o 'HOSTINGER'
 * @returns {Promise<string>} key privada como string (con BEGIN/END marcadores)
 */
async function getSSHKey(which) {
  const keyMap = {
    VPS: 'SSH_KEY_VPS_PRIVATE_ED25519',
    HOSTINGER: 'SSH_KEY_HOSTINGER_PRIVATE',
  };
  const secretName = keyMap[which.toUpperCase()];
  if (!secretName) throw new Error(`SSH key '${which}' desconocida (válidas: VPS, HOSTINGER)`);
  return get(secretName, '/ssh-keys-privadas');
}

/** Limpia el cache (útil para tests o post-rotación). */
function clearCache() {
  _cache.clear();
  _accessToken = null;
  _tokenExpiresAt = 0;
}

module.exports = { get, getMany, getSSHKey, clearCache };
