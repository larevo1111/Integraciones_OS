#!/usr/bin/env python3
"""
sync_espocrm_marketing.py — Paso 6b del pipeline
Sincroniza los tipos de marketing de Effi (zeffi_tipos_marketing) al campo
'tipoDeMarketing' (Enum) en la entidad Contact de EspoCRM.

Flujo:
  1. Lee tipos vigentes de effi_data local
  2. Compara con los que ya están en EspoCRM (custom metadata)
  3. Si hay diferencias → regenera los JSON + rebuild EspoCRM
  4. Si no hay diferencias → sale sin tocar nada

Ejecutar manualmente:
  python3 scripts/sync_espocrm_marketing.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import mysql.connector

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_LOCAL = dict(
    host='127.0.0.1',
    port=3306,
    user='osadmin',
    password='Epist2487.',
    database='effi_data',
)

ESPOCRM_CONTAINER = 'espocrm'

ENTITY_DEFS_PATH   = '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs/Contact.json'
I18N_PATH          = '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX/Contact.json'
LAYOUT_PATH        = '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact/detail.json'
REBUILD_SCRIPT     = '/var/www/html/rebuild.php'
CLEAR_CACHE_SCRIPT = '/var/www/html/clear_cache.php'

TMP_ENTITY  = '/tmp/espo_contact_entitydefs.json'
TMP_I18N    = '/tmp/espo_contact_i18n.json'
TMP_LAYOUT  = '/tmp/espo_contact_layout.json'

LAYOUT_JSON = [
    {
        "label": "",
        "rows": [
            [{"name": "name"}, {"name": "accounts"}],
            [{"name": "emailAddress"}, {"name": "phoneNumber"}],
            [{"name": "tipoDeMarketing"}, False],
            [{"name": "address"}, False],
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


def get_tipos_effi():
    conn = mysql.connector.connect(**DB_LOCAL)
    cur = conn.cursor()
    cur.execute(
        "SELECT tipo_de_marketing FROM zeffi_tipos_marketing "
        "WHERE vigencia = 'Vigente' ORDER BY tipo_de_marketing"
    )
    tipos = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tipos


def get_tipos_espocrm():
    """Lee las opciones actuales del campo en EspoCRM."""
    try:
        raw = run(['docker', 'exec', ESPOCRM_CONTAINER, 'cat', ENTITY_DEFS_PATH], check=False)
        if not raw:
            return []
        defs = json.loads(raw)
        opts = defs.get('fields', {}).get('tipoDeMarketing', {}).get('options', [])
        return [o for o in opts if o]  # excluir el '' inicial
    except Exception:
        return []


def generar_json(tipos):
    entity_defs = {
        'fields': {
            'tipoDeMarketing': {
                'type': 'enum',
                'options': [''] + tipos
            }
        }
    }
    i18n = {
        'fields': {
            'tipoDeMarketing': 'Tipo de Marketing'
        }
    }
    with open(TMP_ENTITY, 'w', encoding='utf-8') as f:
        json.dump(entity_defs, f, ensure_ascii=False, indent=2)
    with open(TMP_I18N, 'w', encoding='utf-8') as f:
        json.dump(i18n, f, ensure_ascii=False, indent=2)
    with open(TMP_LAYOUT, 'w', encoding='utf-8') as f:
        json.dump(LAYOUT_JSON, f, ensure_ascii=False, indent=2)


def aplicar_a_espocrm():
    # Asegurar que existan los directorios
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/metadata/entityDefs'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/i18n/es_MX'])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'mkdir', '-p',
         '/var/www/html/custom/Espo/Custom/Resources/layouts/Contact'])

    # Copiar archivos al contenedor
    run(['docker', 'cp', TMP_ENTITY,  f'{ESPOCRM_CONTAINER}:{ENTITY_DEFS_PATH}'])
    run(['docker', 'cp', TMP_I18N,    f'{ESPOCRM_CONTAINER}:{I18N_PATH}'])
    run(['docker', 'cp', TMP_LAYOUT,  f'{ESPOCRM_CONTAINER}:{LAYOUT_PATH}'])

    # Rebuild + clear cache
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', REBUILD_SCRIPT])
    run(['docker', 'exec', ESPOCRM_CONTAINER, 'php', CLEAR_CACHE_SCRIPT])


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    tipos_effi    = get_tipos_effi()
    tipos_espocrm = get_tipos_espocrm()

    if set(tipos_effi) == set(tipos_espocrm) and len(tipos_effi) == len(tipos_espocrm):
        print(f'✅ sync_espocrm_marketing — sin cambios ({len(tipos_effi)} tipos)')
        return

    generar_json(tipos_effi)
    aplicar_a_espocrm()

    agregados  = set(tipos_effi) - set(tipos_espocrm)
    eliminados = set(tipos_espocrm) - set(tipos_effi)
    print(f'✅ sync_espocrm_marketing — actualizado: '
          f'{len(tipos_effi)} tipos '
          f'(+{len(agregados)} -{len(eliminados)})')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_espocrm_marketing — ERROR: {e}', file=sys.stderr)
        sys.exit(1)
