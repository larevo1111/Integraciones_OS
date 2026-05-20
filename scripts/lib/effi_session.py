"""
effi_session.py — fuente única de verdad para "obtener sesión Effi válida".

Regla absoluta (Santi 2026-05-20): TODO script que hace POST/GET a Effi debe
verificar que la sesión esté viva ANTES de operar, y si está expirada renovarla
automáticamente. Sin esto, los scripts de background fallan en silencio cuando
las cookies de session.json caducan (típicamente cada 24-48h).

Uso típico:
    from lib.effi_session import sesion_effi_http
    s = sesion_effi_http()              # devuelve requests.Session con cookies vivas
    r = s.post('https://effi.com.co/...', data=...)

Internamente:
    1. Carga cookies de scripts/session.json
    2. Verifica con HEAD/GET a una página privada de Effi (rápido, sin descargar HTML)
    3. Si redirige a /ingreso o devuelve no-200 → ejecuta node scripts/refresh_session.js
    4. Recarga cookies y devuelve la session

Renovación: usa el wrapper Node existente (refresh_session.js → session.js → Playwright login).
Tiempo: ~0.3s si la sesión está viva, ~20-30s si hay que renovar.
"""
import json
import subprocess
from pathlib import Path
from typing import Dict

import requests

_REPO = Path(__file__).resolve().parent.parent.parent
_SESSION_FILE = _REPO / 'scripts' / 'session.json'
_REFRESH_SCRIPT = _REPO / 'scripts' / 'refresh_session.js'
_EFFI_BASE = 'https://effi.com.co'
_PROBE_URL = f'{_EFFI_BASE}/app/tercero/cliente'  # página privada barata, igual que session.js
_UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0'


def _leer_cookies() -> Dict[str, str]:
    if not _SESSION_FILE.exists():
        raise RuntimeError(f'No existe {_SESSION_FILE}. Generar primero con scripts/session.js')
    state = json.loads(_SESSION_FILE.read_text())
    return {
        c['name']: c['value']
        for c in state.get('cookies', [])
        if c.get('domain', '').endswith('effi.com.co')
    }


def _sesion_viva(s: requests.Session) -> bool:
    """True si la sesión Effi sigue válida. Hace GET sin follow redirects:
    Effi devuelve 302 → /ingreso cuando la cookie expiró."""
    try:
        r = s.get(_PROBE_URL, timeout=10, allow_redirects=False)
        if r.status_code == 200:
            return True
        if r.status_code in (301, 302, 303, 307, 308):
            return '/ingreso' not in r.headers.get('Location', '')
        return False
    except requests.RequestException:
        return False


def _renovar_via_node() -> None:
    """Ejecuta refresh_session.js (~20-30s) y lanza si falla."""
    if not _REFRESH_SCRIPT.exists():
        raise RuntimeError(f'No existe {_REFRESH_SCRIPT}')
    r = subprocess.run(
        ['node', str(_REFRESH_SCRIPT)],
        cwd=str(_REPO), capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f'refresh_session.js falló (exit {r.returncode}). '
            f'stderr={r.stderr[-500:]!r} stdout={r.stdout[-500:]!r}'
        )


def sesion_effi_http(referer: str = f'{_EFFI_BASE}/app/orden_produccion') -> requests.Session:
    """Devuelve una requests.Session con cookies Effi vivas. Renueva si expiró.

    Parámetros:
        referer: URL a usar en el header Referer (cada endpoint Effi espera la
                 página de la que vendría el form).

    Raises:
        RuntimeError si no hay cookies, si la verificación falla, o si la
        renovación con Playwright no termina exitosamente.
    """
    cookies = _leer_cookies()
    if not cookies:
        # session.json existe pero no tiene cookies de effi.com.co → renovar
        _renovar_via_node()
        cookies = _leer_cookies()
        if not cookies:
            raise RuntimeError('refresh_session.js completó pero session.json sigue sin cookies Effi')

    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': referer,
        'User-Agent': _UA,
        'Accept': '*/*',
        'Accept-Language': 'es-ES,es;q=0.9',
    })

    if _sesion_viva(s):
        return s

    # Sesión expirada → renovar y reintentar UNA vez
    _renovar_via_node()
    cookies = _leer_cookies()
    s2 = requests.Session()
    s2.cookies.update(cookies)
    s2.headers.update(s.headers)
    if not _sesion_viva(s2):
        raise RuntimeError(
            'Sesión Effi inválida incluso después de refresh_session.js. '
            'Verificar que EFFI_USER/EFFI_PASS sean correctos en Infisical/.env.'
        )
    return s2
