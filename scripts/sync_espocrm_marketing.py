#!/usr/bin/env python3
"""
sync_espocrm_marketing.py — Paso 6b del pipeline
Gestiona los campos custom de la entidad Contact en EspoCRM.

Enums dinámicos (sincronizados desde Effi):
  - tipoDeMarketing  ← zeffi_tipos_marketing
  - tarifaPrecios    ← zeffi_tarifas_precios
  - vendedorEffi     ← DISTINCT zeffi_clientes.vendedor UNION zeffi_remisiones_venta_encabezados.vendedor

Enums fijos:
  - tipoCliente      ← 6 valores hardcodeados (estables en Effi)
  - tipoIdentificacion, tipoPersona

Campos varchar fijos:
  - numeroIdentificacion, formaPago

Solo hace rebuild si detecta cambios en alguno de los enums dinámicos.

Ejecutar manualmente:
  python3 scripts/sync_espocrm_marketing.py
"""

import json
import subprocess
import sys

import mysql.connector

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_LOCAL = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='effi_data',
)

DB_ESPO = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='espocrm',
)

ESPOCRM_CONTAINER = 'espocrm'

ENTITY_DEFS_PATH   = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/Contact.json'
I18N_PATH          = '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX/Contact.json'
LAYOUT_PATH        = '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact/detail.json'
JS_DATA_PATH       = '/var/www/html/client/custom/src/data/ciudades-colombia.js'
REBUILD_SCRIPT     = '/var/www/html/rebuild.php'
CLEAR_CACHE_SCRIPT = '/var/www/html/clear_cache.php'

TMP_ENTITY  = '/tmp/espo_contact_entitydefs.json'
TMP_I18N    = '/tmp/espo_contact_i18n.json'
TMP_LAYOUT  = '/tmp/espo_contact_layout.json'
TMP_JS_DATA = '/tmp/espo_ciudades_colombia.js'

# Enums fijos
TIPOS_IDENTIFICACION = [
    '', 'Cédula de ciudadanía', 'Cédula de extranjería',
    'Número de Identificación Tributaria CO', 'Pasaporte'
]
TIPOS_PERSONA  = ['', 'Física (natural)', 'Jurídica (moral)']
TIPOS_CLIENTE  = ['', 'Común', 'Fiel', 'Desertor', 'Mayorista', 'Importador', 'Industrial']

LAYOUT_JSON = [
    {
        "label": "",
        "rows": [
            [{"name": "firstName"},              {"name": "lastName"}],
            [{"name": "emailAddress"},           {"name": "phoneNumber"}],
            [{"name": "tipoDeMarketing"},        {"name": "tipoCliente"}],
            [{"name": "numeroIdentificacion"},   {"name": "tipoIdentificacion"}],
            [{"name": "tipoPersona"},            {"name": "vendedorEffi"}],
            [{"name": "tarifaPrecios"},          {"name": "formaPago"}],
            [{"name": "departamento"},           {"name": "ciudadNombre"}],
            [{"name": "direccion"},              {"name": "direccionLinea2"}],
            [{"name": "fuente"},                 {"name": "enviadoAEffi"}],
            [{"name": "description", "fullWidth": True}]
        ]
    }
]

# ─── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Comando falló: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def query_opciones(tabla, columna):
    """Lee opciones únicas vigentes de una tabla de effi_data."""
    conn = mysql.connector.connect(**DB_LOCAL)
    cur = conn.cursor()
    # Intentar filtrar por vigencia si la columna existe
    try:
        cur.execute(
            f"SELECT DISTINCT `{columna}` FROM `{tabla}` "
            f"WHERE vigencia = 'Vigente' AND `{columna}` IS NOT NULL AND `{columna}` != '' "
            f"ORDER BY `{columna}`"
        )
    except Exception:
        cur.execute(
            f"SELECT DISTINCT `{columna}` FROM `{tabla}` "
            f"WHERE `{columna}` IS NOT NULL AND `{columna}` != '' ORDER BY `{columna}`"
        )
    opciones = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return opciones


def query_departamentos_y_municipios():
    """
    Lee departamentos y municipios de codigos_ciudades_dane (effi_data).
    Retorna:
      deptos     — lista de nombres de departamento ordenada
      municipios — lista plana de nombres de municipio ordenada
      mapa       — dict {depto: [municipios...]} para el JS de cascading
    """
    conn = mysql.connector.connect(**DB_LOCAL)
    cur = conn.cursor()
    cur.execute(
        "SELECT nombre_departamento, nombre_municipio "
        "FROM codigos_ciudades_dane "
        "ORDER BY nombre_departamento, nombre_municipio"
    )
    mapa = {}
    for depto, muni in cur.fetchall():
        mapa.setdefault(depto, []).append(muni)
    cur.close()
    conn.close()

    deptos     = sorted(mapa.keys())
    municipios = sorted({m for lista in mapa.values() for m in lista})
    return deptos, municipios, mapa


def query_vendedores():
    """DISTINCT vendedores de zeffi_clientes + zeffi_remisiones_venta_encabezados."""
    conn = mysql.connector.connect(**DB_LOCAL)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT vendedor FROM (
            SELECT vendedor FROM zeffi_clientes
              WHERE vendedor IS NOT NULL AND vendedor != ''
            UNION
            SELECT vendedor FROM zeffi_remisiones_venta_encabezados
              WHERE vendedor IS NOT NULL AND vendedor != ''
        ) t
        ORDER BY vendedor
    """)
    opciones = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return opciones


def get_opciones_actuales_espocrm(campo):
    """Lee las opciones actuales de un campo enum en EspoCRM."""
    try:
        raw = run(['docker', 'exec', ESPOCRM_CONTAINER, 'cat', ENTITY_DEFS_PATH], check=False)
        if not raw:
            return []
        defs = json.loads(raw)
        opts = defs.get('fields', {}).get(campo, {}).get('options', [])
        return [o for o in opts if o]
    except Exception:
        return []


def generar_json(tipos_marketing, tarifas_precios, vendedores, deptos, municipios, mapa_deptos):
    entity_defs = {
        'fields': {
            'tipoDeMarketing': {
                'type': 'enum',
                'options': [''] + tipos_marketing
            },
            'tipoCliente': {
                'type': 'enum',
                'options': TIPOS_CLIENTE
            },
            'tarifaPrecios': {
                'type': 'enum',
                'options': [''] + tarifas_precios
            },
            'numeroIdentificacion': {
                'type': 'varchar',
                'maxLength': 100
            },
            'tipoIdentificacion': {
                'type': 'enum',
                'options': TIPOS_IDENTIFICACION
            },
            'tipoPersona': {
                'type': 'enum',
                'options': TIPOS_PERSONA
            },
            'formaPago': {
                'type': 'enum',
                'options': ['', 'Contraentrega', 'Contado', '15 días', '30 días', '45 días', '60 días']
            },
            'vendedorEffi': {
                'type': 'enum',
                'options': [''] + vendedores
            },
            'fuente': {
                'type': 'enum',
                'options': ['CRM', 'Effi'],
                'default': 'CRM'
            },
            'enviadoAEffi': {
                'type': 'bool',
                'default': False,
                'readOnly': True
            },
            'departamento': {
                'type': 'enum',
                'options': [''] + deptos
            },
            'ciudadNombre': {
                'type': 'enum',
                'options': [''] + municipios
            },
            'direccion': {
                'type': 'varchar',
                'maxLength': 255
            },
            'direccionLinea2': {
                'type': 'varchar',
                'maxLength': 255
            }
        }
    }
    i18n = {
        'fields': {
            'tipoDeMarketing':      'Tipo de Marketing',
            'tipoCliente':          'Tipo de Cliente',
            'tarifaPrecios':        'Tarifa de Precios',
            'numeroIdentificacion': 'N° Identificación',
            'tipoIdentificacion':   'Tipo Identificación',
            'tipoPersona':          'Tipo de Persona',
            'formaPago':            'Forma de Pago',
            'vendedorEffi':         'Vendedor (Effi)',
            'fuente':               'Fuente',
            'enviadoAEffi':         'Enviado a Effi',
            'departamento':         'Departamento',
            'ciudadNombre':         'Municipio',
            'direccion':            'Dirección',
            'direccionLinea2':      'Referencia / Línea 2',
        }
    }
    # Archivo JS con mapa departamento → [municipios] para cascading en EspoCRM
    js_lines = ["define('custom:data/ciudades-colombia', [], function () {", "    return "]
    js_lines.append(json.dumps(mapa_deptos, ensure_ascii=False, indent=4) + ";")
    js_lines.append("});")

    with open(TMP_ENTITY, 'w', encoding='utf-8') as f:
        json.dump(entity_defs, f, ensure_ascii=False, indent=2)
    with open(TMP_I18N, 'w', encoding='utf-8') as f:
        json.dump(i18n, f, ensure_ascii=False, indent=2)
    with open(TMP_LAYOUT, 'w', encoding='utf-8') as f:
        json.dump(LAYOUT_JSON, f, ensure_ascii=False, indent=2)
    with open(TMP_JS_DATA, 'w', encoding='utf-8') as f:
        f.write('\n'.join(js_lines) + '\n')


def aplicar_a_espocrm():
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/client/custom/src/data'])

    run(['docker', 'cp', TMP_ENTITY,  f'{ESPOCRM_CONTAINER}:{ENTITY_DEFS_PATH}'])
    run(['docker', 'cp', TMP_I18N,    f'{ESPOCRM_CONTAINER}:{I18N_PATH}'])
    run(['docker', 'cp', TMP_LAYOUT,  f'{ESPOCRM_CONTAINER}:{LAYOUT_PATH}'])
    run(['docker', 'cp', TMP_JS_DATA, f'{ESPOCRM_CONTAINER}:{JS_DATA_PATH}'])

    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', REBUILD_SCRIPT])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', CLEAR_CACHE_SCRIPT])


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Leer opciones dinámicas
    tipos_marketing             = query_opciones('zeffi_tipos_marketing', 'tipo_de_marketing')
    tarifas_precios             = query_opciones('zeffi_tarifas_precios', 'nombre')
    vendedores                  = query_vendedores()
    deptos, municipios, mapa_deptos = query_departamentos_y_municipios()

    # Comparar con lo que ya hay en EspoCRM
    mk_espo   = get_opciones_actuales_espocrm('tipoDeMarketing')
    tar_espo  = get_opciones_actuales_espocrm('tarifaPrecios')
    vend_espo = get_opciones_actuales_espocrm('vendedorEffi')
    dep_espo  = get_opciones_actuales_espocrm('departamento')
    mun_espo  = get_opciones_actuales_espocrm('ciudadNombre')

    sin_cambios = (
        set(tipos_marketing) == set(mk_espo)   and len(tipos_marketing) == len(mk_espo) and
        set(tarifas_precios) == set(tar_espo)  and len(tarifas_precios) == len(tar_espo) and
        set(vendedores)      == set(vend_espo) and len(vendedores)      == len(vend_espo) and
        set(deptos)          == set(dep_espo)  and len(deptos)          == len(dep_espo)  and
        set(municipios)      == set(mun_espo)  and len(municipios)      == len(mun_espo)
    )

    if sin_cambios:
        print(f'✅ sync_espocrm_marketing — sin cambios '
              f'({len(tipos_marketing)} marketing, {len(tarifas_precios)} tarifas, '
              f'{len(vendedores)} vendedores, {len(deptos)} deptos, {len(municipios)} municipios)')
        return

    generar_json(tipos_marketing, tarifas_precios, vendedores, deptos, municipios, mapa_deptos)
    aplicar_a_espocrm()

    print(f'✅ sync_espocrm_marketing — actualizado: '
          f'{len(tipos_marketing)} marketing | {len(tarifas_precios)} tarifas | '
          f'{len(vendedores)} vendedores | {len(deptos)} deptos | {len(municipios)} municipios')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_espocrm_marketing — ERROR: {e}', file=sys.stderr)
        sys.exit(1)
