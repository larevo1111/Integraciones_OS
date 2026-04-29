"""
import_articulo_anular_post.py — Anula artículos en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/articulo/anular
Campos:
  - codigo (token cifrado por artículo, scrapeado de /app/articulo)
  - session_empresa
  - session_usuario

El campo `codigo` es un token cifrado por backend. NO se puede generar
localmente: hay que scrapearlo del HTML de la página `/app/articulo` donde
viene en `<a class="modificar" data-codigo="..." data-id="<cod>">`.

Uso:
  # 1 artículo
  python3 scripts/import_articulo_anular_post.py 587

  # múltiples artículos (separados por coma)
  python3 scripts/import_articulo_anular_post.py 587,588,589

  # desde CSV (1 cod por línea, primera col)
  python3 scripts/import_articulo_anular_post.py --csv /tmp/anular.csv

  # dry-run (NO ejecuta, solo lista qué haría)
  python3 scripts/import_articulo_anular_post.py 587 --dry-run

Doc: .claude/skills/effi-tecnico/SKILL.md §Anular artículo
"""
import sys
import os
import json
import re
import time
import argparse
import urllib.parse
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


def crear_session_http():
    s = requests.Session()
    cookies = cargar_cookies()
    if not cookies:
        raise RuntimeError('Sin cookies de sesión Effi en session.json')
    s.cookies.update(cookies)
    s.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{EFFI_BASE}/app/articulo',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    })
    return s


def get_session_info(s):
    """Obtiene session_empresa y session_usuario navegando a la página."""
    r = s.get(f'{EFFI_BASE}/app/articulo', timeout=15, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada — regenerar con scripts/session.js')
    html = r.text
    emp_m = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html) or \
            re.search(r'value=["\'](\d+)["\'][^>]*name=["\']session_empresa["\']', html)
    usr_m = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html) or \
            re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']session_usuario["\']', html)
    return (emp_m.group(1) if emp_m else '12355',
            usr_m.group(1) if usr_m else 'origensilvestre.col@gmail.com')


def scrapear_mapa_codigos(s, max_pages=30):
    """Recorre todas las páginas de /app/articulo y extrae mapa cod_articulo → codigo cifrado.
    Retorna dict {cod (str): codigo_cifrado (str URL-encoded)}.
    """
    mapping = {}
    for page in range(1, max_pages + 1):
        r = s.get(f'{EFFI_BASE}/app/articulo', params={'page': page}, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f'Página {page} → HTTP {r.status_code}')
        # Pattern: class="modificar" ... data-codigo="X" ... data-id="N"
        matches = re.findall(r'class="modificar"[^>]+data-codigo="([^"]+)"[^>]+data-id="(\d+)"', r.text)
        if not matches:
            break
        for codigo, cod in matches:
            mapping.setdefault(cod, codigo)
        if len(matches) < 50:
            break  # última página parcial
    return mapping


def anular_articulo(s, codigo, session_empresa, session_usuario, descripcion='', dry_run=False):
    """POSTea anulación de un artículo. `codigo` es el token cifrado tal como viene del HTML
    (URL-encoded — Effi lo espera ASÍ, NO desencodeado; requests al hacer form-urlencode
    deja `%3D%3D` literal en el payload final, que es lo que Effi necesita)."""
    payload = {
        'codigo': codigo,  # ← TAL CUAL del HTML (con %3D%3D)
        'session_empresa': session_empresa,
        'session_usuario': session_usuario,
    }
    if dry_run:
        print(f'  [DRY-RUN] POST /app/articulo/anular | codigo={codigo[:30]}... | {descripcion}')
        return {'ok': True, 'dry_run': True}
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/articulo/anular', data=payload, timeout=30)
    dur = time.time() - t0
    body = r.text[:300]
    # Effi devuelve HTTP 200 incluso en error; el OK real es el body == 'OK'
    real_ok = (r.status_code == 200) and ('OK' in body[:10] and 'Error' not in body)
    return {
        'ok': real_ok,
        'status': r.status_code,
        'response': body,
        'duracion': round(dur, 2),
    }


def main():
    parser = argparse.ArgumentParser(description='Anular artículos en Effi vía POST directo.')
    parser.add_argument('cods', nargs='?', help='Lista de cods separados por coma. Ej: 587,588,589')
    parser.add_argument('--csv', help='Archivo CSV con 1 cod por línea (primera col)')
    parser.add_argument('--dry-run', action='store_true', help='NO ejecuta, solo lista qué haría')
    parser.add_argument('--delay', type=float, default=0.5, help='Segundos entre POSTs (default 0.5)')
    args = parser.parse_args()

    # Construir lista de cods
    cods = []
    if args.csv:
        import csv as _csv
        with open(args.csv) as f:
            reader = _csv.reader(f, delimiter=';')
            next(reader, None)  # header
            for row in reader:
                if row and row[0].strip().isdigit():
                    cods.append(row[0].strip())
    elif args.cods:
        cods = [c.strip() for c in args.cods.split(',') if c.strip()]
    else:
        parser.error('Hay que pasar cods o --csv')

    print(f'📋 Cods a anular: {len(cods)}')
    if not cods:
        sys.exit(1)

    s = crear_session_http()
    print('🔐 Sesión Effi cargada')

    print('🔄 Obteniendo session_info...')
    emp, usr = get_session_info(s)
    print(f'   session_empresa={emp} | session_usuario={usr}')

    print('🔄 Scrapeando mapa cod → codigo cifrado de /app/articulo (~10 páginas)...')
    mapping = scrapear_mapa_codigos(s)
    print(f'   {len(mapping)} artículos mapeados')

    # Validar que todos los cods estén en el mapa
    faltantes = [c for c in cods if c not in mapping]
    if faltantes:
        print(f'⚠️  {len(faltantes)} cods NO encontrados en el listado vigente (quizás ya anulados):')
        for c in faltantes[:10]:
            print(f'   - {c}')
        if len(faltantes) > 10:
            print(f'   ... y {len(faltantes)-10} más')

    presentes = [c for c in cods if c in mapping]
    print(f'\n🚀 Anulando {len(presentes)} artículos{" (DRY-RUN)" if args.dry_run else ""}...')

    ok, fail = 0, 0
    for i, cod in enumerate(presentes, 1):
        codigo = mapping[cod]
        res = anular_articulo(s, codigo, emp, usr, descripcion=f'cod {cod}', dry_run=args.dry_run)
        if res.get('ok'):
            ok += 1
            print(f'  [{i}/{len(presentes)}] ✅ cod {cod} → {res.get("response", "")[:60] if not args.dry_run else "DRY"}')
        else:
            fail += 1
            print(f'  [{i}/{len(presentes)}] ❌ cod {cod} → HTTP {res.get("status")}: {res.get("response", "")[:200]}')
        if not args.dry_run and i < len(presentes):
            time.sleep(args.delay)

    print(f'\n✅ {ok} OK | ❌ {fail} fail | ⏭ {len(faltantes)} skipped')


if __name__ == '__main__':
    main()
