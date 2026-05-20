"""
import_remision_compra_post.py — Crea remisión de compra en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/remision_c/crear (form `form_CR`)
Tiempo: ~1s vs Playwright que tardaría 60-90s.

Uso:
  python3 scripts/import_remision_compra_post.py /tmp/remision.json
  python3 scripts/import_remision_compra_post.py /tmp/remision.json --dry-run

Formato JSON:
{
  "sucursal_id": 1,
  "bodega_id": 1,
  "centro_costos_id": 1,
  "fecha_compra": "2026-05-04",
  "divisa": "COP",
  "trm": 1,
  "proveedor_id": "245",
  "direccion_proveedor_id": "default",
  "remision_proveedor": "FAC-1234",
  "descuento_global": 0,
  "garantia": "",
  "observacion": "",
  "prontopago": "",
  "fecha_prontopago": "",
  "conceptos": [
    {
      "cod_articulo": "175",
      "cantidad": 36,
      "precio": 2205,
      "descuento": 0,
      "t_egreso": "1",
      "lote": "",
      "serie": "",
      "observacion": "",
      "impuestos": ["1"]
    }
  ],
  "formas_pago": [
    {
      "t_forma_pago": "1",
      "valor": 79380,
      "medio_pago": "1",
      "caja_medio_pago": "1Ǆ2",
      "cuenta_medio_pago": "default",
      "observacion": ""
    }
  ],
  "retenciones": [],
  "anticipos": []
}

Doc: .agent/docs/EFFI_POST_REMISION_COMPRA.md + .claude/skills/effi-tecnico/SKILL.md §3
"""
import sys, json, re, time, argparse, random
from pathlib import Path
import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
from lib import sesion_effi_http
EFFI_BASE = 'https://effi.com.co'


def crear_session_http():
    """Verifica sesión Effi (renueva si expirada) — fuente única lib/effi_session.py"""
    return sesion_effi_http(referer=f'{EFFI_BASE}/app/remision_c')


def get_session_info(s):
    r = s.get(f'{EFFI_BASE}/app/remision_c', timeout=20, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada — regenerar session.json')
    html = r.text
    emp = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html)
    usr = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html)
    return (emp.group(1) if emp else '12355',
            usr.group(1) if usr else 'origensilvestre.col@gmail.com')


def _id_concepto():
    """Random 21 dígitos por línea — Effi lo usa como clave en `impuestos[<id>][]`."""
    return str(random.randint(10**20, 10**21 - 1))


# Tasas Effi (id → %) — extraído de form_CR (mismo set que cotización venta)
TASAS_IMPUESTO = {
    '1': 0.19,  # IVA 19%
    '2': 0.0,   # IVA Exento
    '3': 0.05,  # IVA 5%
    '4': 0.14,  # IVA 14%
    '5': 0.0,   # INCBP (monto fijo, no %)
    '6': 0.08,  # Impuesto consumo 8%
    '7': 0.0,   # IVA Excluido
}


def _max_remision_id(s):
    r = s.get(f'{EFFI_BASE}/app/remision_c', timeout=20)
    ids = re.findall(r'data-id=["\'](\d+)["\']', r.text)
    return max((int(x) for x in ids), default=0)


def construir_payload(data, session_empresa, session_usuario):
    bruto_total = 0
    descuento_total = 0
    impuesto_total = 0
    for c in data['conceptos']:
        cant = float(c['cantidad'])
        precio = float(c['precio'])
        bruto = cant * precio
        desc = float(c.get('descuento', 0))
        bruto_total += bruto
        descuento_total += desc
        base = bruto - desc
        for imp_id in c.get('impuestos', []):
            impuesto_total += base * TASAS_IMPUESTO.get(str(imp_id), 0.0)

    descuento_global = float(data.get('descuento_global', 0))
    subtotal = bruto_total - descuento_total - descuento_global

    payload = [
        ('sucursal',           str(data.get('sucursal_id', 1))),
        ('bodega',             str(data.get('bodega_id', 1))),
        ('centro_costos',      str(data.get('centro_costos_id', 1))),
        ('divisa',             str(data.get('divisa', 'COP'))),
        ('proveedor',          str(data['proveedor_id'])),
        ('direccion_proveedor', str(data.get('direccion_proveedor_id', 'default'))),
        ('fecha_compra',       data.get('fecha_compra', '')),
        ('remision_proveedor', data.get('remision_proveedor', '')),
        ('trm',                str(data.get('trm', 1))),
        ('descuento_global',   f'{descuento_global:.2f}'),
        ('garantia',           data.get('garantia', '')),
        ('observacion',        data.get('observacion', '')),
        ('prontopago',         str(data.get('prontopago', ''))),
        ('fecha_prontopago',   data.get('fecha_prontopago', '')),
        ('session_empresa',    session_empresa),
        ('session_usuario',    session_usuario),
        ('action',             '1'),
        ('json_ref',           ''),
    ]

    # Conceptos
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
            ('t_egreso[]',             str(c.get('t_egreso', '1'))),
            ('cantidad[]',             str(c['cantidad'])),
            ('precio[]',               str(precio)),
            ('bruto[]',                str(int(bruto)) if bruto == int(bruto) else f'{bruto:.2f}'),
            ('descuento[]',            str(desc)),
            ('total_concepto[]',       str(int(total)) if total == int(total) else f'{total:.2f}'),
            ('observacion_concepto[]', c.get('observacion', '')),
            ('lote[]',                 c.get('lote', '')),
            ('serie[]',                c.get('serie', '')),
            ('gift[]',                 '0'),
        ]
        for imp in c.get('impuestos', []):
            payload.append((f'impuestos[{idc}][]', str(imp)))

    # Totales — Effi VALIDA que coincidan con sus cálculos al guardar
    total_neto = subtotal + impuesto_total
    payload += [
        ('bruto_transaccion',    f'{bruto_total:.2f}'),
        ('subtotal_transaccion', f'{subtotal:.2f}'),
        ('total_descuento',      f'{(descuento_total + descuento_global):.2f}'),
        ('total_impuesto',       f'{impuesto_total:.2f}'),
        ('total_retencion',      '0'),
        ('total_transaccion',    f'{total_neto:.2f}'),
    ]

    # Retenciones (default vacías)
    if data.get('retenciones'):
        for ret in data['retenciones']:
            payload += [
                ('retencion[]',       str(ret.get('id', 'default'))),
                ('base_retencion[]',  str(ret.get('base', ''))),
                ('valor_retencion[]', str(ret.get('valor', ''))),
            ]
    else:
        payload += [
            ('retencion[]',       'default'),
            ('base_retencion[]',  ''),
            ('valor_retencion[]', ''),
        ]

    # Formas de pago (mínimo 1) — Effi exige suma == total_neto
    formas = data.get('formas_pago', [])
    if not formas:
        formas = [{
            't_forma_pago': '1',
            'valor': total_neto,
            'medio_pago': '1',
            'caja_medio_pago': '1Ǆ2',
            'cuenta_medio_pago': 'default',
            'observacion': '',
        }]
    for fp in formas:
        valor = float(fp.get('valor', 0)) if fp.get('valor') is not None else total_neto
        payload += [
            ('t_forma_pago[]',          str(fp.get('t_forma_pago', '1'))),
            ('valor_forma_pago[]',      f'{valor:.2f}'),
            ('medio_pago[]',            str(fp.get('medio_pago', '1'))),
            ('caja_medio_pago[]',       fp.get('caja_medio_pago', '1Ǆ2')),
            ('cuenta_medio_pago[]',     str(fp.get('cuenta_medio_pago', 'default'))),
            ('valor_medio_pago[]',      f'{valor:.2f}'),
            ('observacion_medio_pago[]', fp.get('observacion', '')),
        ]

    # Anticipos (vacíos por default)
    if data.get('anticipos'):
        for ant in data['anticipos']:
            payload += [
                ('sucursal_anticipo[]', str(ant.get('sucursal', ''))),
                ('id_anticipo[]',       str(ant.get('id', ''))),
            ]
    else:
        payload += [
            ('sucursal_anticipo[]', ''),
            ('id_anticipo[]',       ''),
        ]

    return payload


def crear_remision(json_path, dry_run=False):
    data = json.loads(Path(json_path).read_text())
    s = crear_session_http()

    print('🔄 Cargando página y obteniendo session info...')
    session_empresa, session_usuario = get_session_info(s)
    print(f'   session_empresa={session_empresa}, session_usuario={session_usuario}')

    payload = construir_payload(data, session_empresa, session_usuario)
    print(f'📦 Payload construido: {len(payload)} fields')

    if dry_run:
        print('[DRY-RUN] Primeros 30 fields:')
        for k, v in payload[:30]:
            print(f'   {k} = {v!r}')
        print('   ...')
        return None

    print('🔄 Consultando MAX(id_remision) en Effi antes del POST...')
    max_antes = _max_remision_id(s)
    print(f'   MAX antes: {max_antes}')

    print(f'🚀 POST {EFFI_BASE}/app/remision_c/crear ({len(payload)} fields)...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/remision_c/crear', data=payload, timeout=30)
    dur = time.time() - t0
    print(f'   ⏱  {dur:.2f}s | HTTP {r.status_code} | bytes: {len(r.text)}')
    print(f'   Response (200 chars): {r.text[:200]!r}')
    r.raise_for_status()

    # Effi responde JSON: {"respuesta":"OK"|"error","mensaje":"..."}
    body = r.text.strip()
    try:
        resp = json.loads(body)
        if resp.get('respuesta') != 'OK':
            raise RuntimeError(f'POST falló: {resp.get("mensaje", body)[:500]}')
    except json.JSONDecodeError:
        if 'error' in body.lower()[:60]:
            raise RuntimeError(f'POST falló: {body[:500]}')

    print('🔄 Consultando MAX(id_remision) tras el POST...')
    max_despues = _max_remision_id(s)
    print(f'   MAX después: {max_despues}')
    if max_despues <= max_antes:
        raise RuntimeError(f'POST no creó remisión nueva (max antes={max_antes}, después={max_despues})')

    print(f'REMISION_CREADA:{max_despues}')
    return max_despues


def main():
    p = argparse.ArgumentParser(description='Crear remisión de compra en Effi vía POST directo')
    p.add_argument('json_path', help='Archivo JSON con datos de la remisión')
    p.add_argument('--dry-run', action='store_true', help='Solo mostrar payload, no postear')
    args = p.parse_args()
    crear_remision(args.json_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
