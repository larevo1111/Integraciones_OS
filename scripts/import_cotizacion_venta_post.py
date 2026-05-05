"""
import_cotizacion_venta_post.py — Crea cotización de venta en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/cotizacion/crear (form `form_CR`)
Tiempo: ~1s vs Playwright que tardaría 60-90s.

Uso:
  python3 scripts/import_cotizacion_venta_post.py /tmp/cotiz.json
  python3 scripts/import_cotizacion_venta_post.py /tmp/cotiz.json --dry-run

Formato JSON:
{
  "sucursal_id": 1,
  "bodega_id": 1,
  "centro_costos_id": 1,
  "fecha_entrega": "2026-05-04",
  "divisa": "COP",
  "trm": 1,
  "cliente_id": "687",
  "direccion_cliente_id": "default",
  "vendedor_id": "default",
  "tercero_id": "",
  "descuento_global": 0,
  "garantia": "",
  "observacion": "",
  "prontopago": "",
  "fecha_prontopago": "",
  "propina": 0,
  "conceptos": [
    {
      "cod_articulo": "175",
      "cantidad": 2,
      "precio": 17000,
      "descuento": 0,
      "lote": "",
      "serie": "",
      "observacion": "",
      "impuestos": ["1"]
    }
  ],
  "formas_pago": [
    {"t_forma_pago": "1", "valor": 34000}
  ],
  "retenciones": []
}

Doc: .claude/skills/effi-tecnico/SKILL.md §3
"""
import sys, os, json, re, time, argparse, random
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
        'Referer': f'{EFFI_BASE}/app/cotizacion',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0',
    })
    return s


def get_session_info(s):
    r = s.get(f'{EFFI_BASE}/app/cotizacion', timeout=20, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada — regenerar session.json')
    html = r.text
    emp = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html)
    usr = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html)
    return (emp.group(1) if emp else '12355',
            usr.group(1) if usr else 'origensilvestre.col@gmail.com',
            html)


def _id_concepto():
    """Effi genera un id random de 21 dígitos por línea de concepto.
    Se usa como clave en `impuestos[<id>][]`."""
    return str(random.randint(10**20, 10**21 - 1))


def _max_cotizacion_id(s):
    """Scrape el listado para detectar la cotización recién creada (max id antes/después)."""
    r = s.get(f'{EFFI_BASE}/app/cotizacion', timeout=20)
    ids = re.findall(r'data-id=["\'](\d+)["\']', r.text)
    return max((int(x) for x in ids), default=0)


def construir_payload(data, session_empresa, session_usuario):
    """Convierte el dict de usuario en lista de tuplas form-urlencoded."""
    # Calcular totales línea por línea
    bruto_total = 0
    descuento_total = 0
    for c in data['conceptos']:
        cant = float(c['cantidad'])
        precio = float(c['precio'])
        bruto = cant * precio
        desc = float(c.get('descuento', 0))
        bruto_total += bruto
        descuento_total += desc

    descuento_global = float(data.get('descuento_global', 0))
    propina = float(data.get('propina', 0))
    subtotal = bruto_total - descuento_total - descuento_global

    payload = [
        # Header
        ('sucursal',         str(data.get('sucursal_id', 1))),
        ('bodega',           str(data.get('bodega_id', 1))),
        ('centro_costos',    str(data.get('centro_costos_id', 1))),
        ('fecha_entrega',    data.get('fecha_entrega', '')),
        ('divisa',           str(data.get('divisa', 'COP'))),
        ('trm',              str(data.get('trm', 1))),
        ('cliente',          str(data['cliente_id'])),
        ('direccion_cliente', str(data.get('direccion_cliente_id', 'default'))),
        ('vendedor',         str(data.get('vendedor_id', 'default'))),
        ('tercero',          str(data.get('tercero_id', ''))),
        ('descuento_global', f'{descuento_global:.2f}'),
        ('garantia',         data.get('garantia', '')),
        ('observacion',      data.get('observacion', '')),
        ('prontopago',       str(data.get('prontopago', ''))),
        ('fecha_prontopago', data.get('fecha_prontopago', '')),
        ('propina',          str(int(propina)) if propina == int(propina) else f'{propina:.2f}'),
        ('session_empresa',  session_empresa),
        ('session_usuario',  session_usuario),
    ]

    # Conceptos (líneas)
    for c in data['conceptos']:
        cant = float(c['cantidad'])
        precio = float(c['precio'])
        bruto = cant * precio
        desc = float(c.get('descuento', 0))
        total = bruto - desc
        idc = _id_concepto()
        payload += [
            ('id_concepto[]',          idc),
            ('articulo[]',             str(c['cod_articulo'])),
            ('descripcion[]',          c.get('descripcion', '')),
            ('cantidad[]',             str(c['cantidad'])),
            ('precio[]',               str(precio)),
            ('bruto[]',                str(int(bruto)) if bruto == int(bruto) else f'{bruto:.2f}'),
            ('descuento[]',            str(desc)),
            ('total_concepto[]',       str(int(total)) if total == int(total) else f'{total:.2f}'),
            ('alquiler[]',             '0'),
            ('observacion_concepto[]', c.get('observacion', '')),
            ('lote[]',                 c.get('lote', '')),
            ('serie[]',                c.get('serie', '')),
            ('gift[]',                 '0'),
        ]
        # Impuestos por línea: si no se especifica, va vacío
        impuestos = c.get('impuestos', [])
        if impuestos:
            for imp in impuestos:
                payload.append((f'impuestos[{idc}][]', str(imp)))
        else:
            # Effi espera la clave aunque sea vacía si se usaron impuestos en otra línea — dejar omitido
            pass

    # Totales (Effi recalcula pero los manda igual el form)
    total_impuesto = 0  # No calculamos % de impuesto aquí — Effi recalcula
    total_neto = subtotal + propina + total_impuesto
    payload += [
        ('bruto_transaccion',    str(int(bruto_total)) if bruto_total == int(bruto_total) else f'{bruto_total:.2f}'),
        ('subtotal_transaccion', str(int(subtotal)) if subtotal == int(subtotal) else f'{subtotal:.2f}'),
        ('total_descuento',      str(int(descuento_total + descuento_global))),
        ('total_impuesto',       str(int(total_impuesto))),
        ('total_retencion',      '0'),
        ('total_transaccion',    str(int(total_neto)) if total_neto == int(total_neto) else f'{total_neto:.2f}'),
    ]

    # Retenciones (opcional, default vacío)
    for ret in data.get('retenciones', []):
        payload += [
            ('retencion[]',       str(ret.get('id', 'default'))),
            ('base_retencion[]',  str(ret.get('base', ''))),
            ('valor_retencion[]', str(ret.get('valor', ''))),
        ]
    if not data.get('retenciones'):
        payload += [
            ('retencion[]',       'default'),
            ('base_retencion[]',  ''),
            ('valor_retencion[]', ''),
        ]

    # Formas de pago
    formas = data.get('formas_pago', [])
    if not formas:
        # Default: contado total con id 1
        formas = [{'t_forma_pago': '1', 'valor': total_neto}]
    for fp in formas:
        valor = float(fp.get('valor', 0))
        payload += [
            ('t_forma_pago[]',    str(fp.get('t_forma_pago', '1'))),
            ('valor_forma_pago[]', f'{valor:.2f}'),
        ]

    return payload


def crear_cotizacion(json_path, dry_run=False):
    data = json.loads(Path(json_path).read_text())
    s = crear_session_http()

    print('🔄 Cargando página y obteniendo session info...')
    session_empresa, session_usuario, _ = get_session_info(s)
    print(f'   session_empresa={session_empresa}, session_usuario={session_usuario}')

    payload = construir_payload(data, session_empresa, session_usuario)
    print(f'📦 Payload construido: {len(payload)} fields')

    if dry_run:
        print('[DRY-RUN] Primeros 25 fields:')
        for k, v in payload[:25]:
            print(f'   {k} = {v!r}')
        print('   ...')
        return None

    print('🔄 Consultando MAX(id_cotizacion) en Effi antes del POST...')
    max_antes = _max_cotizacion_id(s)
    print(f'   MAX antes: {max_antes}')

    print(f'🚀 POST {EFFI_BASE}/app/cotizacion/crear ({len(payload)} fields)...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/cotizacion/crear', data=payload, timeout=30)
    dur = time.time() - t0
    print(f'   ⏱  {dur:.2f}s | HTTP {r.status_code} | bytes: {len(r.text)}')
    print(f'   Response (200 chars): {r.text[:200]!r}')
    r.raise_for_status()

    body = r.text.strip()
    if body and body != 'OK' and 'error' in body.lower()[:60]:
        raise RuntimeError(f'POST falló: {body[:300]}')

    print('🔄 Consultando MAX(id_cotizacion) tras el POST...')
    max_despues = _max_cotizacion_id(s)
    print(f'   MAX después: {max_despues}')
    if max_despues <= max_antes:
        raise RuntimeError(f'POST no creó cotización nueva (max antes={max_antes}, después={max_despues})')

    print(f'COTIZACION_CREADA:{max_despues}')
    return max_despues


def main():
    p = argparse.ArgumentParser(description='Crear cotización de venta en Effi vía POST directo')
    p.add_argument('json_path', help='Archivo JSON con datos de la cotización')
    p.add_argument('--dry-run', action='store_true', help='Solo mostrar payload, no postear')
    args = p.parse_args()
    crear_cotizacion(args.json_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
