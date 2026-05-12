"""
anular_orden_produccion_post.py — Anula una OP en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/orden_produccion/anular
Tiempo: ~1-2s vs Playwright ~30-60s.

Uso:
  python3 scripts/anular_orden_produccion_post.py <id_orden> [observacion]

Doc: .agent/docs/EFFI_POST_OP_OPERACIONES.md
"""
import sys, json, re, time
from pathlib import Path
import requests

REPO = Path(__file__).resolve().parent.parent
SESSION_FILE = REPO / 'scripts' / 'session.json'
EFFI_BASE = 'https://effi.com.co'


def cargar_cookies():
    if not SESSION_FILE.exists():
        raise RuntimeError(f'No existe {SESSION_FILE}. Generar con scripts/session.js')
    state = json.loads(SESSION_FILE.read_text())
    return {c['name']: c['value'] for c in state.get('cookies', [])
            if 'effi.com.co' in c.get('domain', '') or c.get('domain', '').endswith('effi.com.co')}


def crear_session():
    s = requests.Session()
    s.cookies.update(cargar_cookies())
    s.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{EFFI_BASE}/app/orden_produccion',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    })
    return s


def get_session_info(s):
    """Extrae session_empresa y session_usuario del HTML de orden_produccion."""
    r = s.get(f'{EFFI_BASE}/app/orden_produccion', timeout=20, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada — regenerar session.json')
    html = r.text
    emp_m = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html) or \
            re.search(r'value=["\'](\d+)["\'][^>]*name=["\']session_empresa["\']', html)
    usr_m = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html) or \
            re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']session_usuario["\']', html)
    return (emp_m.group(1) if emp_m else '12355',
            usr_m.group(1) if usr_m else 'origensilvestre.col@gmail.com')


def anular_op(id_orden, observacion, sucursal='1'):
    s = crear_session()
    print(f'🔄 Obteniendo session info...')
    session_empresa, session_usuario = get_session_info(s)
    print(f'   session_empresa={session_empresa}, session_usuario={session_usuario}')

    payload = {
        'observacion_anular': observacion,
        'sucursal': str(sucursal),
        'id': str(id_orden),
        'session_empresa': session_empresa,
        'session_usuario': session_usuario,
    }
    print(f'🚀 POST anular OP {id_orden}...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/orden_produccion/anular', data=payload, timeout=30)
    dur = time.time() - t0
    body = r.text[:300]
    print(f'   Status: {r.status_code}, bytes: {len(r.text)}, tardó: {dur:.2f}s')
    print(f'   Body: {body}')
    if r.status_code != 200 or body.strip() not in ('OK', '1', 'true'):
        raise RuntimeError(f'POST anular falló: HTTP {r.status_code} body={body}')
    print(f'✅ OP {id_orden} anulada')
    return {'ok': True, 'id_orden': id_orden, 'duracion_s': dur}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    id_orden = sys.argv[1]
    obs      = sys.argv[2] if len(sys.argv) > 2 else f'SYS POST - Anulación OP {id_orden}'
    try:
        anular_op(id_orden, obs)
    except Exception as e:
        print(f'❌ ERROR: {e}', file=sys.stderr)
        sys.exit(1)
