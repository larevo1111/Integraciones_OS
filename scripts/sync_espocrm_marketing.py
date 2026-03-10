#!/usr/bin/env python3
"""
sync_espocrm_marketing.py — Paso 6b del pipeline
Gestiona los campos custom de la entidad Contact en EspoCRM.

Enums dinámicos (sincronizados desde Effi):
  - tipoDeMarketing  ← zeffi_tipos_marketing
  - tipoCliente      ← zeffi_tipo_de_cliente  (si se exporta) o valores fijos
  - tarifaPrecios    ← zeffi_tarifas_precios

Campos fijos (no dependen de Effi):
  - numeroIdentificacion, tipoIdentificacion, tipoPersona,
    formaPago, vendedorEffi

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

ESPOCRM_CONTAINER = 'espocrm'

ENTITY_DEFS_PATH   = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/Contact.json'
I18N_PATH          = '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX/Contact.json'
LAYOUT_PATH        = '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact/detail.json'
REBUILD_SCRIPT     = '/var/www/html/rebuild.php'
CLEAR_CACHE_SCRIPT = '/var/www/html/clear_cache.php'

TMP_ENTITY = '/tmp/espo_contact_entitydefs.json'
TMP_I18N   = '/tmp/espo_contact_i18n.json'
TMP_LAYOUT = '/tmp/espo_contact_layout.json'

# Enums fijos
TIPOS_IDENTIFICACION = [
    '', 'Cédula de ciudadanía', 'Cédula de extranjería',
    'Número de Identificación Tributaria CO', 'Pasaporte'
]
TIPOS_PERSONA = ['', 'Física (natural)', 'Jurídica (moral)']

LAYOUT_JSON = [
    {
        "label": "",
        "rows": [
            [{"name": "name"},                  {"name": "accounts"}],
            [{"name": "emailAddress"},           {"name": "phoneNumber"}],
            [{"name": "tipoDeMarketing"},        {"name": "tipoCliente"}],
            [{"name": "numeroIdentificacion"},   {"name": "tipoIdentificacion"}],
            [{"name": "tipoPersona"},            {"name": "vendedorEffi"}],
            [{"name": "tarifaPrecios"},          {"name": "formaPago"}],
            [{"name": "address"},                False],
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


def generar_json(tipos_marketing, tipos_cliente, tarifas_precios):
    entity_defs = {
        'fields': {
            'tipoDeMarketing': {
                'type': 'enum',
                'options': [''] + tipos_marketing
            },
            'tipoCliente': {
                'type': 'enum',
                'options': [''] + tipos_cliente
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
                'type': 'varchar',
                'maxLength': 100
            },
            'vendedorEffi': {
                'type': 'varchar',
                'maxLength': 200
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
        }
    }
    with open(TMP_ENTITY, 'w', encoding='utf-8') as f:
        json.dump(entity_defs, f, ensure_ascii=False, indent=2)
    with open(TMP_I18N, 'w', encoding='utf-8') as f:
        json.dump(i18n, f, ensure_ascii=False, indent=2)
    with open(TMP_LAYOUT, 'w', encoding='utf-8') as f:
        json.dump(LAYOUT_JSON, f, ensure_ascii=False, indent=2)


def aplicar_a_espocrm():
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact'])

    run(['docker', 'cp', TMP_ENTITY, f'{ESPOCRM_CONTAINER}:{ENTITY_DEFS_PATH}'])
    run(['docker', 'cp', TMP_I18N,   f'{ESPOCRM_CONTAINER}:{I18N_PATH}'])
    run(['docker', 'cp', TMP_LAYOUT, f'{ESPOCRM_CONTAINER}:{LAYOUT_PATH}'])

    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', REBUILD_SCRIPT])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', CLEAR_CACHE_SCRIPT])


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Leer opciones vigentes de Effi
    tipos_marketing = query_opciones('zeffi_tipos_marketing', 'tipo_de_marketing')
    tarifas_precios = query_opciones('zeffi_tarifas_precios', 'nombre')
    # tipo_de_cliente viene de zeffi_clientes (no tiene tabla propia exportada)
    tipos_cliente   = query_opciones('zeffi_clientes', 'tipo_de_cliente')

    # Comparar con lo que ya hay en EspoCRM
    mk_espo  = get_opciones_actuales_espocrm('tipoDeMarketing')
    tar_espo = get_opciones_actuales_espocrm('tarifaPrecios')
    cli_espo = get_opciones_actuales_espocrm('tipoCliente')

    sin_cambios = (
        set(tipos_marketing) == set(mk_espo)  and len(tipos_marketing) == len(mk_espo) and
        set(tarifas_precios) == set(tar_espo) and len(tarifas_precios) == len(tar_espo) and
        set(tipos_cliente)   == set(cli_espo) and len(tipos_cliente)   == len(cli_espo)
    )

    if sin_cambios:
        print(f'✅ sync_espocrm_marketing — sin cambios '
              f'({len(tipos_marketing)} marketing, {len(tarifas_precios)} tarifas, '
              f'{len(tipos_cliente)} tipos cliente)')
        return

    generar_json(tipos_marketing, tipos_cliente, tarifas_precios)
    aplicar_a_espocrm()

    print(f'✅ sync_espocrm_marketing — actualizado: '
          f'{len(tipos_marketing)} marketing | {len(tarifas_precios)} tarifas | '
          f'{len(tipos_cliente)} tipos cliente')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_espocrm_marketing — ERROR: {e}', file=sys.stderr)
        sys.exit(1)
