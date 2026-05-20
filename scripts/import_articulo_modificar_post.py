"""
import_articulo_modificar_post.py — Modifica un artículo en Effi vía POST directo.

Endpoint: POST https://effi.com.co/app/articulo/modificar_articulo
Mismo form que Crear (PAYLOAD_DEFAULTS) + 3 campos extra:
  - id              = ID real del artículo (no cifrado)
  - session_empresa
  - session_usuario

Estrategia: scrape de /app/articulo para leer TODOS los datos actuales del artículo
desde los `data-*` del link `.modificar`, mergea con los campos a cambiar (parcial),
y POSTea el payload completo.

Uso:
  # Cambiar nombre + costo
  python3 scripts/import_articulo_modificar_post.py --cod 587 --nombre "Nuevo nombre" --costo 5000

  # Cambiar solo costo
  python3 scripts/import_articulo_modificar_post.py --cod 587 --costo 3500

  # Desde JSON (override completo)
  python3 scripts/import_articulo_modificar_post.py --cod 587 --json /tmp/cambios.json

  # Dry-run
  python3 scripts/import_articulo_modificar_post.py --cod 587 --costo 5000 --dry-run

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
sys.path.insert(0, str(REPO / 'scripts'))
from lib import sesion_effi_http
EFFI_BASE = 'https://effi.com.co'


def crear_session_http():
    """Verifica sesión Effi (renueva si expirada) — fuente única lib/effi_session.py"""
    return sesion_effi_http(referer=f'{EFFI_BASE}/app/articulo')


def get_session_info(s):
    r = s.get(f'{EFFI_BASE}/app/articulo', timeout=15, allow_redirects=False)
    if r.status_code != 200 or '/ingreso' in r.headers.get('Location', '') or '/ingreso' in r.url:
        raise RuntimeError('Sesión Effi expirada')
    html = r.text
    emp = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', html)
    usr = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', html)
    return (emp.group(1) if emp else '12355',
            usr.group(1) if usr else 'origensilvestre.col@gmail.com')


def html_decode(s):
    """Effi guarda los data-* HTML-encoded (&quot;→\", &amp;→&). Decodear para mandar bien."""
    if not s: return s
    return (s.replace('&amp;', '&').replace('&quot;', '"').replace('&#039;', "'")
              .replace('&lt;', '<').replace('&gt;', '>'))


def scrapear_data_articulo(s, cod):
    """Scrape /app/articulo para extraer TODOS los data-* del link .modificar del cod dado.
    El link es `<a href="#" class="modificar" data-codigo="..." data-id="..." ...>` con
    atributos en múltiples líneas. Buscamos el bloque por `class="modificar"` (no asumimos
    orden de atributos) y filtramos por data-id == cod."""
    cod = str(cod)
    for page in range(1, 30):
        r = s.get(f'{EFFI_BASE}/app/articulo', params={'page': page}, timeout=30)
        # `[^>]*?` no matchea `>`. `class="modificar"` puede estar en cualquier posición.
        for m in re.finditer(r'<a\b[^>]*?\bclass="modificar"[^>]*>', r.text):
            atts = m.group(0)
            id_m = re.search(r'data-id="(\d+)"', atts)
            if not id_m or id_m.group(1) != cod:
                continue
            data = {}
            for am in re.finditer(r'data-([\w_]+)="([^"]*)"', atts):
                data[am.group(1)] = html_decode(am.group(2))
            return data
        if 'class="modificar"' not in r.text: break
    raise RuntimeError(f'cod {cod} no encontrado en /app/articulo (¿anulado?)')


# Mapeo data-* (HTML) → name del form (POST). Muchos coinciden, otros no.
MAP_DATA_TO_FORM = {
    'descripcion': 'descripcion',
    'referencia': 'referencia',
    'sucursal': 'sucursal',
    't_articulo': 't_articulo',
    'categoria': 'categoria',
    'marca': 'marca',
    'p_costo': 'p_costo',
    'p_min_venta': 'p_min_venta',
    'gestion_stock': 'gestion_stock',
    'stock_minimo': 'stock_minimo',
    'stock_optimo': 'stock_optimo',
    'compras': 'compras',
    'ventas': 'ventas',
    'descuento': 'descuento',
    'descuento_max': 'descuento_max',
    'alquiler': 'alquiler',
    'deposito': 'deposito',
    'mandato': 'mandato',
    'cuenta_contable_activo': 'cuenta_contable_activo',
    'cuenta_contable_ingreso_venta': 'cuenta_contable_ingreso_venta',
    'cuenta_contable_devolucion_ingreso_venta': 'cuenta_contable_devolucion_ingreso_venta',
    'cuenta_contable_costo_venta': 'cuenta_contable_costo_venta',
    'cuenta_contable_depreciacion_gasto': 'cuenta_contable_depreciacion_gasto',
    'cuenta_contable_depreciacion_acumulada': 'cuenta_contable_depreciacion_acumulada',
    'costo_inicial': 'costo_inicial',
    'valor_residual': 'valor_residual',
    'valor_depreciado': 'valor_depreciado',
    'vida_util_meses': 'vida_util_meses',
    'fecha_inicio_depreciacion': 'fecha_inicio_depreciacion',
    'fecha_fin_depreciacion': 'fecha_fin_depreciacion',
    'fecha_baja': 'fecha_baja',
    'observacion_activo_fijo': 'observacion_activo_fijo',
    'url_video': 'url_video',
    'descripcion_detallada': 'descripcion_detallada',
    'valor_ref': 'valor_ref',
    'porcentaje_ref': 'porcentaje_ref',
    'numero_ref': 'numero_ref',
    'texto_ref': 'texto_ref',
}


def construir_payload_modificar(data_actual, cambios, session_empresa, session_usuario):
    """Construye el payload POST: parte del estado actual del artículo + aplica cambios."""
    # Mapear data-* (estado actual) → form fields
    p = {}
    for data_key, form_key in MAP_DATA_TO_FORM.items():
        v = data_actual.get(data_key, '')
        # Effi usa "default" para selects vacíos. Si viene "" en data, dejamos "" salvo
        # los que requieren default. Simplificación: dejamos como viene.
        p[form_key] = str(v) if v not in (None, '') else ''
    # Campos que la UI siempre manda con default si no hay valor
    for k in ['marca', 'cuenta_contable_activo', 'cuenta_contable_ingreso_venta',
              'cuenta_contable_devolucion_ingreso_venta', 'cuenta_contable_costo_venta',
              'cuenta_contable_depreciacion_gasto', 'cuenta_contable_depreciacion_acumulada']:
        if not p.get(k): p[k] = 'default'
    # Checkboxes: la UI manda "on" si activo, omite si inactivo
    # Los data-* tienen "1" o "0" — convertimos
    for cb in ['gestion_stock', 'compras', 'ventas', 'descuento', 'alquiler', 'mandato']:
        v = p.get(cb, '0')
        if v == '1': p[cb] = 'on'
        elif v == '0' or v == '': p.pop(cb, None)  # omitir si off

    # Aplicar cambios del usuario (mapeo amigable + override directo)
    if 'nombre' in cambios: p['descripcion'] = cambios['nombre']
    if 'descripcion' in cambios: p['descripcion'] = cambios['descripcion']
    if 'costo' in cambios: p['p_costo'] = str(cambios['costo'])
    if 'p_costo' in cambios: p['p_costo'] = str(cambios['p_costo'])
    if 'tipo' in cambios: p['t_articulo'] = str(cambios['tipo'])
    for k, v in cambios.items():
        if k in MAP_DATA_TO_FORM.values() and k not in ('nombre','costo','tipo'):
            p[k] = str(v) if v is not None else ''

    # Campos especiales que SIEMPRE se mandan
    p['id'] = str(data_actual['id'])
    p['session_empresa'] = session_empresa
    p['session_usuario'] = session_usuario

    # p_costo_promedio: lo trae como `data-p_costo_promedio`
    if 'p_costo_promedio' in data_actual:
        p['p_costo_promedio'] = data_actual['p_costo_promedio']

    # c_barras[]: vacío si no hay
    payload_list = list(p.items())
    payload_list.append(('c_barras[]', ''))
    payload_list.append(('articulo_combo[]', ''))
    payload_list.append(('cantidad_combo[]', '1'))
    payload_list.append(('porcentaje_combo[]', ''))

    # Tarifas estándar: mantener vacías si no se especifican
    for tid in ['13', '15', '16', '19']:
        payload_list.append(('tarifa_precio[]', tid))
        payload_list.append(('p_venta[]', ''))

    return payload_list


def modificar_articulo(cod, cambios, dry_run=False):
    s = crear_session_http()
    print(f'🔄 Scrapeando estado actual cod {cod}...')
    data_actual = scrapear_data_articulo(s, cod)
    print(f'   nombre actual: {data_actual.get("descripcion")}')
    print(f'   t_articulo={data_actual.get("t_articulo")} categoria={data_actual.get("categoria")} costo={data_actual.get("p_costo")}')

    emp, usr = get_session_info(s)
    payload = construir_payload_modificar(data_actual, cambios, emp, usr)

    if dry_run:
        print(f'\n[DRY-RUN] POST /app/articulo/modificar_articulo ({len(payload)} fields)')
        cambiados = {k: v for k, v in payload if any(k == m for m in cambios.values()) or k in cambios}
        for k, v in payload:
            if k in ('descripcion', 'p_costo', 't_articulo', 'categoria', 'id'): print(f'   {k} = {v!r}')
        return

    print(f'🚀 POST /app/articulo/modificar_articulo ({len(payload)} fields)...')
    t0 = time.time()
    r = s.post(f'{EFFI_BASE}/app/articulo/modificar_articulo', data=payload, timeout=30)
    dur = time.time() - t0
    body = r.text[:300]
    print(f'   ⏱ {dur:.2f}s | HTTP {r.status_code} | response: {body[:200]!r}')
    if r.status_code != 200 or 'Error' in body[:50]:
        raise RuntimeError(f'POST falló: {body[:200]}')
    print(f'✅ Artículo cod {cod} modificado')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cod', required=True, help='ID del artículo a modificar')
    parser.add_argument('--json', help='JSON con los cambios a aplicar')
    parser.add_argument('--nombre', help='Nuevo nombre (descripcion)')
    parser.add_argument('--costo', type=float, help='Nuevo costo manual (p_costo)')
    parser.add_argument('--tipo', type=int, help='Nuevo tipo (1=MP 2=PP 3=PT 4=Servicio 5=Activo)')
    parser.add_argument('--categoria', help='Nuevo ID categoría')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    cambios = {}
    if args.json:
        cambios = json.loads(Path(args.json).read_text())
    if args.nombre is not None: cambios['nombre'] = args.nombre
    if args.costo is not None: cambios['costo'] = args.costo
    if args.tipo is not None: cambios['tipo'] = args.tipo
    if args.categoria is not None: cambios['categoria'] = args.categoria

    if not cambios: parser.error('No hay cambios — pasá --nombre/--costo/--tipo/--categoria/--json')

    print(f'📝 Cambios para cod {args.cod}: {cambios}')
    modificar_articulo(args.cod, cambios, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
