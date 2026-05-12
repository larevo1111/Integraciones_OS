"""
cambiar_estado_orden_produccion_post.py — Cambia el estado de una OP en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/orden_produccion/cambiar_estado
Tiempo: ~2-3s vs Playwright ~30-60s.

Uso:
  python3 scripts/cambiar_estado_orden_produccion_post.py <id_orden> <estado> [observacion]

Estados válidos: "Procesada" | "Validado"
  (Generada = estado inicial, no se vuelve a él; Anulada = via anular_post.py)

Mapeo estado → est_orden_produccion:
  Procesada = 2
  Validado  = 3

Doc: .agent/docs/EFFI_POST_OP_OPERACIONES.md
"""
import sys, json, re, time, argparse, urllib.parse
from pathlib import Path
import requests

REPO = Path(__file__).resolve().parent.parent
SESSION_FILE = REPO / 'scripts' / 'session.json'
EFFI_BASE = 'https://effi.com.co'

ESTADO_MAP = {'Procesada': '2', 'Validado': '3'}


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
        'Accept': '*/*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    })
    return s


def scrapear_token(s, id_orden, max_pages=5):
    """Busca el token cifrado de la OP en el HTML de /app/orden_produccion.
    Pattern: <a class="cambiar_estado" data-prefijo_id="<ID>" data-id="<token URL-encoded>">.
    Itera páginas hasta encontrarla."""
    for page in range(1, max_pages + 1):
        r = s.get(f'{EFFI_BASE}/app/orden_produccion', params={'page': page}, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f'GET orden_produccion page={page} → HTTP {r.status_code}')
        # Match: data-prefijo_id="<id>" ... data-id="<token>" en mismo <a class="cambiar_estado">
        pat = rf'class="cambiar_estado"\s+data-prefijo_id="{re.escape(str(id_orden))}"\s+data-id="([^"]+)"'
        m = re.search(pat, r.text)
        if m:
            token_encoded = m.group(1)
            # requests.post() con data=dict re-encodea. Si pasamos el token TAL CUAL del HTML
            # (con %2F %3D) lo doble-encodea. Desencodear para que requests lo re-encode bien.
            return urllib.parse.unquote(token_encoded)
        # Si no está en esta página, seguir
    raise RuntimeError(f'OP {id_orden} no encontrada en las primeras {max_pages} páginas')


def cambiar_estado(id_orden, estado, observacion):
    if estado not in ESTADO_MAP:
        raise ValueError(f'Estado inválido "{estado}". Usar: {", ".join(ESTADO_MAP.keys())}')

    s = crear_session()
    print(f'🔄 Scrapeando token de OP {id_orden}...')
    t0 = time.time()
    token = scrapear_token(s, id_orden)
    print(f'   Token: {token[:30]}... ({time.time() - t0:.2f}s)')

    payload = {
        'id': token,
        'est_orden_produccion': ESTADO_MAP[estado],
        'observacion': observacion,
    }
    print(f'🚀 POST cambiar_estado → {estado} (est={ESTADO_MAP[estado]})...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/orden_produccion/cambiar_estado', data=payload, timeout=30)
    dur = time.time() - t0
    body = r.text[:300]
    print(f'   Status: {r.status_code}, bytes: {len(r.text)}, tardó: {dur:.2f}s')
    print(f'   Body: {body}')
    if r.status_code != 200 or body.strip() not in ('OK', '1', 'true'):
        raise RuntimeError(f'POST falló: HTTP {r.status_code} body={body}')
    print(f'✅ OP {id_orden} → estado "{estado}"')
    return {'ok': True, 'id_orden': id_orden, 'estado': estado, 'duracion_s': dur}


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    id_orden = sys.argv[1]
    estado   = sys.argv[2]
    obs      = sys.argv[3] if len(sys.argv) > 3 else f'SYS POST - Cambio estado a {estado}'
    try:
        cambiar_estado(id_orden, estado, obs)
    except Exception as e:
        print(f'❌ ERROR: {e}', file=sys.stderr)
        sys.exit(1)
