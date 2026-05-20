"""
import_traslado_inventario_post.py — crea traslado de inventario en Effi vía POST directo.

Uso: python3 scripts/import_traslado_inventario_post.py /tmp/traslado.json

JSON esperado:
  {
    "sucursal_origen": 1,
    "bodega_origen": 17,        // id bodega (ej: 17 = "Productos No Conformes Bod PPAL")
    "sucursal_destino": 1,
    "bodega_destino": 1,        // 1 = Principal
    "observacion": "Reproceso OP 2245",
    "articulos": [
      { "cod_articulo": "231", "descripcion": "POLEN DE ABEJA OS 320 GRS", "cantidad": 1, "lote": "", "serie": "" }
    ]
  }

Tiempo: ~2-4s. Si la sesión expira, falla con RuntimeError (mismo patrón que OP POST).
Endpoint identificado por espionaje del form #form_CR el 2026-05-19.
"""
import sys, os, json, re, time as _t
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
from lib import sesion_effi_http

EFFI_BASE = 'https://effi.com.co'
ENDPOINT = f'{EFFI_BASE}/app/traslado_inventario/crear_traslado_inventario'


def _get_session_info(s):
    """Obtiene session_empresa y session_usuario navegando a la página."""
    r = s.get(f'{EFFI_BASE}/app/traslado_inventario', timeout=15, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada')
    html = r.text
    emp_m = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html) or \
            re.search(r'value=["\'](\d+)["\'][^>]*name=["\']session_empresa["\']', html)
    usr_m = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html) or \
            re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']session_usuario["\']', html)
    return (emp_m.group(1) if emp_m else '12355',
            usr_m.group(1) if usr_m else 'origensilvestre.col@gmail.com')


def _max_traslado_id(s):
    """Scrapea el listado para obtener el último id_traslado, así detectamos el creado."""
    r = s.get(f'{EFFI_BASE}/app/traslado_inventario', timeout=15)
    ids = re.findall(r'data-id[\"=]+(\d+)', r.text)
    return max((int(x) for x in ids), default=0)


def crear_traslado(json_path):
    data = json.loads(Path(json_path).read_text())
    s = sesion_effi_http(referer=f'{EFFI_BASE}/app/traslado_inventario')

    print('🔄 Cargando session info...')
    session_empresa, session_usuario = _get_session_info(s)
    print(f'   session_empresa={session_empresa}, session_usuario={session_usuario}')

    # Construir payload form-urlencoded (arrays con [])
    payload = [
        ('sucursal_origen', str(data['sucursal_origen'])),
        ('bodega_origen', str(data['bodega_origen'])),
        ('sucursal_destino', str(data['sucursal_destino'])),
        ('bodega_destino', str(data['bodega_destino'])),
        ('observacion', data.get('observacion', '')),
        ('session_empresa', session_empresa),
        ('session_usuario', session_usuario),
    ]
    for a in data['articulos']:
        payload += [
            ('articulo[]', str(a['cod_articulo'])),
            ('descripcion[]', a.get('descripcion', '')),
            ('lote[]', a.get('lote', '')),
            ('serie[]', a.get('serie', '')),
            ('cantidad[]', str(a['cantidad'])),
        ]

    print('🔄 MAX(id) antes del POST...')
    max_antes = _max_traslado_id(s)
    print(f'   MAX antes: {max_antes}')

    print(f'🚀 POST a {ENDPOINT} ({len(payload)} fields)...')
    t0 = _t.time()
    r = s.post(ENDPOINT, data=payload, timeout=30)
    dur = _t.time() - t0
    print(f'   ⏱️  POST {dur:.2f}s — status: {r.status_code}, bytes: {len(r.text)}')
    if r.status_code != 200:
        print(f'   Response: {r.text[:300]!r}')
    r.raise_for_status()

    print('🔄 MAX(id) tras POST...')
    max_despues = _max_traslado_id(s)
    print(f'   MAX después: {max_despues}')
    if max_despues <= max_antes:
        raise RuntimeError(f'POST no creó traslado (max antes={max_antes}, después={max_despues}). Response: {r.text[:200]!r}')
    print(f'TRASLADO_CREADO:{max_despues}')
    return max_despues


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Uso: python3 import_traslado_inventario_post.py <archivo.json>')
        sys.exit(1)
    crear_traslado(sys.argv[1])
