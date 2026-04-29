"""
import_orden_produccion_post.py — crea OP en Effi vía POST directo (sin Playwright).

Uso: python3 scripts/import_orden_produccion_post.py /tmp/op.json
JSON: mismo formato que import_orden_produccion.js

Tiempo: ~3-5s vs Playwright que tarda 60-90s.
Doc: .agent/docs/EFFI_POST_DIRECTO.md
"""
import sys, os, json, re
from pathlib import Path
import requests
from urllib.parse import parse_qs

REPO = Path(__file__).resolve().parent.parent
SESSION_FILE = REPO / 'scripts' / 'session.json'

# Sesión Playwright → cookies para requests
def _cargar_cookies():
    if not SESSION_FILE.exists():
        raise SystemExit(f'❌ No existe {SESSION_FILE}. Generar con scripts/session.js')
    state = json.loads(SESSION_FILE.read_text())
    return {c['name']: c['value'] for c in state.get('cookies', [])
            if 'effi.com.co' in c.get('domain', '') or c.get('domain', '').endswith('effi.com.co')}


def _formato_coma(n):
    """Effi usa formato '17,000' para números con miles. NO usar punto decimal."""
    n = float(n)
    if n == int(n):
        return f'{int(n):,}'.replace(',', ',')  # 17000 → 17,000
    return f'{n:.2f}'.replace('.', ',')


def _fmt_fecha(iso):
    """ISO 2026-04-27 → 27/04/2026."""
    y, m, d = iso.split('-')
    return f'{d}/{m}/{y}'


def crear_session_http():
    s = requests.Session()
    cookies = _cargar_cookies()
    if not cookies:
        raise SystemExit('❌ Sin cookies de sesión Effi en session.json')
    s.cookies.update(cookies)
    s.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://effi.com.co/app/orden_produccion',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    })
    return s


# Mapeo CC/NIT → ID interno Effi.
# Resuelto desde zeffi_empleados.codigo (sync via pipeline Effi).
# Si Effi cambia un ID, refrescar y reconsultar la tabla.
MAPEO_ENCARGADOS = {
    '74084937':   '536',  # Deivy Andres Gonzalez Gutierrez (Empleado)
    '1128457413': '165',  # Jenifer Alexandra Cano Garcia (Empleado)
    '3506889':    '213',  # Santiago Sierra (Empleado)
    '1017206760': '687',  # Laura Echavarria (Cliente — Effi acepta cualquier tercero)
}


def resolver_encargado_id(cc):
    """CC → ID interno. Solo desde MAPEO_ENCARGADOS (cache estático).
    Si no está mapeado, lanza RuntimeError para que el wrapper caiga al fallback Playwright,
    que sí sabe resolverlo via modal #modalBuscarTercero."""
    cc = str(cc)
    if cc in MAPEO_ENCARGADOS:
        return MAPEO_ENCARGADOS[cc]
    raise RuntimeError(f'CC={cc} no está en MAPEO_ENCARGADOS — cae al fallback Playwright')


def get_session_info(s):
    """Obtiene session_empresa y session_usuario navegando a la página."""
    r = s.get('https://effi.com.co/app/orden_produccion', timeout=15)
    if r.status_code != 200 or '/ingreso' in r.url:
        raise SystemExit('❌ Sesión expirada — regenerar con scripts/session.js')
    html = r.text
    emp_m = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html) or \
            re.search(r'value=["\'](\d+)["\'][^>]*name=["\']session_empresa["\']', html)
    usr_m = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html) or \
            re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']session_usuario["\']', html)
    return (emp_m.group(1) if emp_m else '12355',
            usr_m.group(1) if usr_m else 'origensilvestre.col@gmail.com')


def crear_op(json_path):
    data = json.loads(Path(json_path).read_text())
    s = crear_session_http()

    print('🔄 Cargando página y obteniendo session info...')
    session_empresa, session_usuario = get_session_info(s)
    print(f'   session_empresa={session_empresa}, session_usuario={session_usuario}')

    print(f'🔄 Resolviendo encargado CC={data["encargado"]}...')
    encargado_id = resolver_encargado_id(data['encargado'])
    print(f'   ID interno: {encargado_id}')

    # Calcular totales
    costo_material = sum(float(m['cantidad']) * float(m['costo']) for m in data['materiales'])
    otros = sum(float(c['cantidad']) * float(c['costo']) for c in data.get('otros_costos', []))
    venta = sum(float(p['cantidad']) * float(p['precio']) for p in data['articulos_producidos'])
    beneficio = venta - costo_material - otros

    # Construir form-urlencoded como lista de tuplas (para arrays con [])
    payload = [
        ('sucursal', str(data['sucursal_id'])),
        ('bodega', str(data['bodega_id'])),
        ('fecha_inicio', _fmt_fecha(data['fecha_inicio'])),
        ('fecha_fin', _fmt_fecha(data['fecha_fin'])),
        ('encargado', encargado_id),
        ('observacion', data.get('observacion', '')),
        ('tercero', ''),
        ('maquina', 'default'),
        ('session_empresa', session_empresa),
        ('session_usuario', session_usuario),
        ('costo_material', str(int(costo_material))),
        ('otros_costos', str(int(otros))),
        ('precio_venta', str(int(venta))),
        ('beneficio', str(int(beneficio))),
    ]

    for m in data['materiales']:
        payload += [
            ('articuloM[]', str(m['cod_articulo'])),
            ('cantidadM[]', str(m['cantidad'])),
            ('costoM[]', _formato_coma(m['costo'])),
            ('loteM[]', m.get('lote', '')),
            ('serieM[]', m.get('serie', '')),
            ('descripcionM[]', ''),  # Effi lo recalcula
        ]

    for p in data['articulos_producidos']:
        payload += [
            ('articuloP[]', str(p['cod_articulo'])),
            ('cantidadP[]', str(p['cantidad'])),
            ('precioP[]', _formato_coma(p['precio'])),
            ('loteP[]', p.get('lote', '')),
            ('serieP[]', p.get('serie', '')),
            ('descripcionP[]', ''),
        ]

    for c in data.get('otros_costos', []):
        payload += [
            ('costo_produccion[]', str(c['tipo_costo_id'])),
            ('cantidad[]', str(c['cantidad'])),
            ('costo[]', _formato_coma(c['costo'])),
        ]

    # MAX antes del POST: scrapear data-id de la página de listado
    import re as _re
    def _max_op_effi():
        rr = s.get('https://effi.com.co/app/orden_produccion', timeout=15)
        ids = _re.findall(r'data-id[\"=]+(\d+)', rr.text)
        if not ids: return 0
        return max(int(x) for x in ids)

    print('🔄 Consultando MAX(id_orden) en Effi antes del POST...')
    max_antes = _max_op_effi()
    print(f'   MAX antes: {max_antes}')

    print(f'🚀 POST a /app/orden_produccion/crear ({len(payload)} fields)...')
    import time as _t
    t0 = _t.time()
    r = s.post('https://effi.com.co/app/orden_produccion/crear', data=payload, timeout=30)
    dur = _t.time() - t0
    print(f'   ⏱️  POST tardó {dur:.2f}s — status: {r.status_code}, bytes: {len(r.text)}')
    print(f'   Response (200 chars): {r.text[:200]!r}')
    r.raise_for_status()

    # MAX después del POST → ese es el id de la OP recién creada
    print('🔄 Consultando MAX(id_orden) en Effi tras el POST...')
    max_despues = _max_op_effi()
    print(f'   MAX después: {max_despues}')
    if max_despues <= max_antes:
        raise RuntimeError(f'POST no creó OP nueva (max antes={max_antes}, después={max_despues})')
    print(f'OP_CREADA:{max_despues}')
    return max_despues


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Uso: python3 import_orden_produccion_post.py <archivo.json>')
        sys.exit(1)
    crear_op(sys.argv[1])
