"""
import_articulo_crear_post.py — Crea un artículo en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/articulo/crear (form `form_CART`, 41 campos no-vacíos)

Uso:
  # CLI (mínimo: nombre + tipo + categoria + costo)
  python3 scripts/import_articulo_crear_post.py \\
    --nombre "Mi Articulo Test" --tipo 1 --categoria 47 --costo 1000

  # Desde JSON
  python3 scripts/import_articulo_crear_post.py --json /tmp/nuevo_articulo.json

  # Dry-run
  python3 scripts/import_articulo_crear_post.py --nombre TEST --tipo 1 --categoria 47 --costo 1 --dry-run

Tipos de artículo (t_articulo):
  1 = Materia prima
  2 = Producto en proceso
  3 = Producto terminado
  4 = Servicio
  5 = Activo fijo

Devuelve el ID del artículo creado (scraping post-create).

Doc: .claude/skills/effi-tecnico/SKILL.md §3 + §13
"""
import sys
import os
import json
import re
import argparse
import time
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
            if 'effi.com.co' in c.get('domain', '')}


def crear_session_http():
    s = requests.Session()
    cookies = cargar_cookies()
    if not cookies:
        raise RuntimeError('Sin cookies de sesión Effi')
    s.cookies.update(cookies)
    s.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{EFFI_BASE}/app/articulo',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0',
    })
    return s


def get_session_info(s):
    r = s.get(f'{EFFI_BASE}/app/articulo', timeout=15, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada')
    html = r.text
    emp = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html) or \
          re.search(r'value=["\'](\d+)["\'][^>]*name=["\']session_empresa["\']', html)
    usr = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html)
    return (emp.group(1) if emp else '12355',
            usr.group(1) if usr else 'origensilvestre.col@gmail.com')


# Defaults: form Crear de Effi tiene 41 campos. Esos son los que la UI manda al hacer
# "Crear" con valores mínimos (nombre+tipo+categoria+costo). Los demás se infieren.
PAYLOAD_DEFAULTS = {
    'descripcion': '',           # nombre del artículo (obligatorio)
    'referencia': '',
    'sucursal': '1',             # Principal
    'c_barras[]': '',
    't_articulo': '1',           # 1=MP, 2=PP, 3=PT, 4=Servicio, 5=Activo fijo
    'categoria': 'default',      # ID de categoría
    'marca': 'default',
    'gestion_stock': 'on',
    'stock_minimo': '',
    'stock_optimo': '',
    'compras': 'on',
    'descuento_max': '',
    'deposito': '',
    'cuenta_contable_ingreso_venta': 'default',
    'cuenta_contable_devolucion_ingreso_venta': 'default',
    'cuenta_contable_activo': 'default',
    'cuenta_contable_costo_venta': 'default',
    'costo_inicial': '',
    'valor_residual': '',
    'valor_depreciado': '',
    'vida_util_meses': '',
    'fecha_inicio_depreciacion': '',
    'fecha_baja': '',
    'cuenta_contable_depreciacion_gasto': 'default',
    'cuenta_contable_depreciacion_acumulada': 'default',
    'observacion_activo_fijo': '',
    'articulo_combo[]': '',
    'cantidad_combo[]': '1',
    'porcentaje_combo[]': '',
    'p_costo': '',               # costo manual
    'p_min_venta': '',
    'valor_ref': '',
    'porcentaje_ref': '',
    'numero_ref': '',
    'texto_ref': '',
    'url_foto': '',
    'url_video': '',
    'descripcion_detallada': '',
    'codigo_dropshipping': '',
}


def construir_payload(data):
    """Construye payload form-urlencoded a partir de dict del usuario.
    Campos requeridos: descripcion, t_articulo, categoria. costo es opcional.
    """
    p = dict(PAYLOAD_DEFAULTS)
    # Mapeo simplificado nombre→descripcion, costo→p_costo, tipo→t_articulo
    if 'nombre' in data: p['descripcion'] = data['nombre']
    if 'descripcion' in data: p['descripcion'] = data['descripcion']
    if 'costo' in data: p['p_costo'] = str(data['costo'])
    if 'p_costo' in data: p['p_costo'] = str(data['p_costo'])
    if 'tipo' in data: p['t_articulo'] = str(data['tipo'])
    for k, v in data.items():
        if k in PAYLOAD_DEFAULTS:
            p[k] = str(v) if v is not None else ''

    # Tarifas: 4 tarifas estándar de Effi (ids 13, 15, 16, 19) con precios opcionales
    tarifas = data.get('tarifas', {'13': '', '15': '', '16': '', '19': ''})
    payload_list = list(p.items())
    for tid, precio in tarifas.items():
        payload_list.append(('tarifa_precio[]', str(tid)))
        payload_list.append(('p_venta[]', str(precio) if precio else ''))

    return payload_list


def crear_articulo(data, dry_run=False):
    if not data.get('nombre') and not data.get('descripcion'):
        raise ValueError('Falta "nombre" o "descripcion"')
    s = crear_session_http()
    payload = construir_payload(data)
    if dry_run:
        print(f'[DRY-RUN] POST /app/articulo/crear ({len(payload)} fields)')
        for k, v in payload[:10]: print(f'   {k} = {v!r}')
        print('   ...')
        return None
    print(f'🚀 POST /app/articulo/crear ({len(payload)} fields)...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/articulo/crear', data=payload, timeout=30)
    dur = time.time() - t0
    body = r.text[:300]
    print(f'   ⏱ {dur:.2f}s | HTTP {r.status_code} | response: {body[:200]!r}')
    if r.status_code != 200 or 'Error' in body[:50]:
        raise RuntimeError(f'POST falló: {body[:200]}')

    # Capturar el ID del artículo recién creado: scrape la primera fila de la lista
    # (los nuevos aparecen ordenados al final por id desc — tomar el último id)
    print('🔄 Scrapeando ID del artículo recién creado...')
    desc = data.get('nombre') or data.get('descripcion')
    for page in range(1, 30):
        rr = s.get(f'{EFFI_BASE}/app/articulo', params={'page': page}, timeout=20)
        # Match data-id + data-descripcion="N"
        for m in re.finditer(r'class="modificar"[^>]+data-codigo="([^"]+)"[^>]+data-id="(\d+)"[^>]+data-descripcion="([^"]+)"', rr.text):
            if m.group(3).strip() == desc.strip():
                cod_creado = m.group(2)
                print(f'✅ Artículo creado con id={cod_creado}: "{desc}"')
                return cod_creado
        if 'data-id' not in rr.text: break
    print(f'⚠ Creado pero no se encontró id por scrape (descripcion="{desc}")')
    return None


def main():
    parser = argparse.ArgumentParser(description='Crear artículo en Effi vía POST directo')
    parser.add_argument('--json', help='Path JSON con payload')
    parser.add_argument('--nombre', help='Descripción del artículo')
    parser.add_argument('--tipo', type=int, choices=[1, 2, 3, 4, 5],
                       help='1=MP 2=PP 3=PT 4=Servicio 5=Activo')
    parser.add_argument('--categoria', help='ID de categoría Effi')
    parser.add_argument('--costo', type=float, help='Costo manual')
    parser.add_argument('--sucursal', default='1', help='ID sucursal (default 1)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.json:
        data = json.loads(Path(args.json).read_text())
    else:
        if not args.nombre:
            parser.error('Falta --nombre o --json')
        data = {'nombre': args.nombre, 'sucursal': args.sucursal}
        if args.tipo: data['tipo'] = args.tipo
        if args.categoria: data['categoria'] = args.categoria
        if args.costo is not None: data['costo'] = args.costo

    cod = crear_articulo(data, dry_run=args.dry_run)
    if cod: print(cod)


if __name__ == '__main__':
    main()
