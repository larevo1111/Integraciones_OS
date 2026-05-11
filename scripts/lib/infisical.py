"""
Cliente Infisical para Python — con cache en memoria y SSH key loader sin tocar disco.

Uso:
    from lib.secrets import get, get_many, get_ssh_key_object

    db_pass = get('DB_LOCAL_PASS')                  # path default: /shared
    db_pass = get('DB_LOCAL_PASS', folder='/shared')

    # SSH key como objeto paramiko, en memoria pura
    pkey = get_ssh_key_object('VPS')
    with SSHTunnelForwarder((host, 22), ssh_pkey=pkey, ...):
        ...

Variables de entorno requeridas:
    INFISICAL_HOST          - https://vps-contabo.tail44c420.ts.net
    INFISICAL_PROJECT_ID    - a332fa07-1e9f-41eb-ad25-ba701da6c5bd
    INFISICAL_CLIENT_ID     - UUID del client (id de Universal Auth)
    INFISICAL_CLIENT_SECRET - secret hex
    INFISICAL_ENV           - prod | dev | staging (default: prod)
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from io import StringIO
from typing import Any

# ── Config ───────────────────────────────────────────────────────────────────

HOST = os.getenv('INFISICAL_HOST', 'https://vps-contabo.tail44c420.ts.net')
PROJECT_ID = os.getenv(
    'INFISICAL_PROJECT_ID', 'a332fa07-1e9f-41eb-ad25-ba701da6c5bd'
)
ENV = os.getenv('INFISICAL_ENV', 'prod')
CACHE_TTL_S = int(os.getenv('INFISICAL_CACHE_TTL_S', '300'))  # 5 min

# Fallback: si las env vars no están, leer del archivo de bootstrap (útil en local)
if not os.getenv('INFISICAL_CLIENT_ID'):
    _bootstrap = '/home/osserver/tempoclv/.infisical_admin_bootstrap.env'
    if os.path.exists(_bootstrap):
        with open(_bootstrap) as f:
            for line in f:
                if line.startswith('INFISICAL_') and '=' in line:
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)


# ── Cache + token ────────────────────────────────────────────────────────────

_cache: dict[str, tuple[Any, float]] = {}  # cacheKey -> (value, expiresAt)
_access_token: str | None = None
_token_expires_at: float = 0.0


def _http(method: str, path: str, body: Any = None, headers: dict | None = None) -> tuple[int, Any]:
    """HTTP request usando urllib (sin dependencias externas)."""
    url = HOST + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = r.read()
            return r.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, payload.decode(errors='ignore')


def _ensure_token() -> str:
    """Obtiene access token (login con Universal Auth) si no hay uno válido en cache."""
    global _access_token, _token_expires_at
    now = time.time()
    if _access_token and now < _token_expires_at - 30:
        return _access_token

    client_id = os.environ.get('INFISICAL_CLIENT_ID')
    client_secret = os.environ.get('INFISICAL_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise RuntimeError(
            'INFISICAL_CLIENT_ID y INFISICAL_CLIENT_SECRET son requeridos'
        )

    status, body = _http(
        'POST',
        '/api/v1/auth/universal-auth/login',
        {'clientId': client_id, 'clientSecret': client_secret},
    )
    if status != 200 or not isinstance(body, dict) or 'accessToken' not in body:
        raise RuntimeError(f'Infisical login failed: HTTP {status} {str(body)[:200]}')

    _access_token = body['accessToken']
    _token_expires_at = now + body.get('expiresIn', 2_592_000)
    return _access_token


# ── API pública ──────────────────────────────────────────────────────────────


def get(key: str, folder: str = '/shared', *, env: str | None = None,
        ttl_s: int | None = None, force: bool = False) -> str:
    """Obtiene un secret de Infisical (con cache).

    Args:
        key:    nombre del secret (ej: 'DB_LOCAL_PASS')
        folder: path del folder (default '/shared')
        env:    environment (default desde INFISICAL_ENV)
        ttl_s:  TTL del cache en segundos (default CACHE_TTL_S)
        force:  si True, ignora cache y refetcha
    """
    env = env or ENV
    cache_key = f'{env}:{folder}:{key}'
    now = time.time()

    if not force and cache_key in _cache:
        value, expires_at = _cache[cache_key]
        if now < expires_at:
            return value

    token = _ensure_token()
    qs = urllib.parse.urlencode(
        {'workspaceId': PROJECT_ID, 'environment': env, 'secretPath': folder}
    )
    status, body = _http(
        'GET',
        f'/api/v3/secrets/raw/{urllib.parse.quote(key)}?{qs}',
        headers={'Authorization': f'Bearer {token}'},
    )
    if status != 200:
        raise RuntimeError(
            f"Infisical GET {folder}/{key} failed: HTTP {status} {str(body)[:200]}"
        )
    secret = (body or {}).get('secret') or body
    value = secret.get('secretValue') if isinstance(secret, dict) else None
    if value is None:
        raise RuntimeError(f"Infisical: secret '{folder}/{key}' sin valor")

    _cache[cache_key] = (value, now + (ttl_s or CACHE_TTL_S))
    return value


def get_many(folder: str = '/shared', *, env: str | None = None,
             ttl_s: int | None = None) -> dict[str, str]:
    """Obtiene TODOS los secrets de un folder de una sola llamada (más eficiente)."""
    env = env or ENV
    token = _ensure_token()
    qs = urllib.parse.urlencode(
        {'workspaceId': PROJECT_ID, 'environment': env, 'secretPath': folder}
    )
    status, body = _http(
        'GET', f'/api/v3/secrets/raw?{qs}',
        headers={'Authorization': f'Bearer {token}'},
    )
    if status != 200:
        raise RuntimeError(f'Infisical getMany {folder} failed: HTTP {status}')

    result: dict[str, str] = {}
    now = time.time()
    ttl = ttl_s or CACHE_TTL_S
    for s in (body or {}).get('secrets', []):
        k = s.get('secretKey')
        v = s.get('secretValue')
        if k is not None and v is not None:
            result[k] = v
            _cache[f'{env}:{folder}:{k}'] = (v, now + ttl)
    return result


def get_ssh_key_string(which: str) -> str:
    """Devuelve la SSH key privada como string (con BEGIN/END markers).

    Args:
        which: 'VPS' o 'HOSTINGER'
    """
    key_map = {
        'VPS': 'SSH_KEY_VPS_PRIVATE_ED25519',
        'HOSTINGER': 'SSH_KEY_HOSTINGER_PRIVATE',
    }
    secret_name = key_map.get(which.upper())
    if not secret_name:
        raise ValueError(f"SSH key '{which}' desconocida (válidas: VPS, HOSTINGER)")
    return get(secret_name, '/ssh-keys-privadas')


def get_ssh_key_object(which: str):
    """Devuelve la SSH key como objeto paramiko (en memoria, sin tocar disco).

    Uso con sshtunnel:
        from sshtunnel import SSHTunnelForwarder
        pkey = get_ssh_key_object('VPS')
        with SSHTunnelForwarder((host, 22), ssh_pkey=pkey, ...):
            ...

    Args:
        which: 'VPS' o 'HOSTINGER'
    """
    from paramiko import Ed25519Key, RSAKey
    key_str = get_ssh_key_string(which)
    buf = StringIO(key_str)
    # Ed25519 es nuestro caso. Si en el futuro hay RSA, podemos detectar por header.
    try:
        return Ed25519Key.from_private_key(buf)
    except Exception:
        buf.seek(0)
        return RSAKey.from_private_key(buf)


def clear_cache() -> None:
    """Limpia el cache (útil para tests o post-rotación)."""
    global _access_token, _token_expires_at
    _cache.clear()
    _access_token = None
    _token_expires_at = 0.0
