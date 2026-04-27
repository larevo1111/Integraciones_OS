"""
refresh_effi_produccion.py — orquesta refresh completo de catálogo + OPs desde Effi.

Pasos:
  1. export_inventario.js                 → /exports/inventario/inventario_*.xlsx
  2. export_produccion_encabezados.js     → /exports/produccion_encabezados/*.xlsx
  3. export_produccion_reportes.js        → /exports/produccion/{materiales,articulos_producidos,otros_costos}/*.xlsx
  4. Import a effi_data (5 tablas): zeffi_inventario, zeffi_produccion_encabezados,
     zeffi_articulos_producidos, zeffi_materiales, zeffi_otros_costos
  5. Sync a VPS os_integracion (mismas 5 tablas)

Uso: python3 scripts/refresh_effi_produccion.py
Salida JSON línea-por-línea para que el API la pueda parsear como progreso.
"""
import os, sys, subprocess, json
from pathlib import Path
import pymysql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local, cfg_integracion

REPO = Path(__file__).resolve().parent.parent
EXPORTS = Path('/exports')

EXPORTS_MAP = {
    'zeffi_inventario':                EXPORTS / 'inventario',
    'zeffi_produccion_encabezados':    EXPORTS / 'produccion' / 'encabezados_prod',
    'zeffi_articulos_producidos':      EXPORTS / 'produccion' / 'articulos_producidos',
    'zeffi_materiales':                EXPORTS / 'produccion' / 'materiales',
    'zeffi_otros_costos':              EXPORTS / 'produccion' / 'otros_costos',
}

def log(paso, msg, ok=True):
    print(json.dumps({'paso': paso, 'msg': msg, 'ok': ok}), flush=True)


def run_node(script, descripcion, timeout=600):
    log(descripcion, f'Ejecutando {script}...')
    r = subprocess.run(['node', f'scripts/{script}'], cwd=REPO,
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(descripcion, f'ERROR: {r.stderr[-300:]}', ok=False)
        sys.exit(1)
    log(descripcion, f'✅ {descripcion} OK')


def importar_via_node():
    """Invoca import_all.js (Node) que maneja xlsx Y HTML correctamente.
    Importa todas las tablas de /exports/* — sí, también las que no necesitamos,
    pero es el camino más confiable (los reportes de produccion son HTML disfrazado de xlsx)."""
    log('import_all', 'Importando todos los xlsx a effi_data via import_all.js...')
    r = subprocess.run(['node', 'scripts/import_all.js'], cwd=REPO,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log('import_all', f'ERROR: {r.stderr[-300:]}', ok=False)
        sys.exit(1)
    # Capturar la última línea del stdout (resumen)
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'import OK'
    log('import_all', f'✅ {last}')


def sync_a_vps(tabla):
    """Copia effi_data.<tabla> → os_integracion.<tabla> (DDL + datos)."""
    cnx_l = pymysql.connect(**cfg_local(), database='effi_data', charset='utf8mb4')
    cur_l = cnx_l.cursor()
    cnx_v = pymysql.connect(**cfg_integracion(dict_cursor=False))
    cur_v = cnx_v.cursor()
    cur_l.execute(f'SHOW CREATE TABLE `{tabla}`'); ddl = cur_l.fetchone()[1]
    cur_v.execute(f'DROP TABLE IF EXISTS `{tabla}`'); cur_v.execute(ddl)
    cur_l.execute(f'SELECT * FROM `{tabla}`')
    cols = [d[0] for d in cur_l.description]; rows = cur_l.fetchall()
    if rows:
        ph = ','.join(['%s']*len(cols))
        col_names = ','.join(f'`{c}`' for c in cols)
        sql = f'INSERT INTO `{tabla}` ({col_names}) VALUES ({ph})'
        for i in range(0, len(rows), 200):
            cur_v.executemany(sql, rows[i:i+200])
    cnx_v.commit(); cnx_l.close(); cnx_v.close()
    log(f'sync:{tabla}', f'✅ {len(rows)} filas → VPS os_integracion.{tabla}')


def main():
    log('inicio', 'Refresh Effi → effi_data → VPS')

    # Fase 1: exports
    run_node('export_inventario.js',             'Export inventario (artículos)')
    run_node('export_produccion_encabezados.js', 'Export OPs (encabezados)')
    run_node('export_produccion_reportes.js',    'Export materiales+productos+costos OPs')

    # Fase 2: import a local (todas las tablas, vía import_all.js para soportar HTML disfrazado)
    importar_via_node()

    # Fase 3: sync VPS
    for tabla in EXPORTS_MAP.keys():
        sync_a_vps(tabla)

    log('fin', '✅ Refresh Effi completo: 5 tablas actualizadas en local + VPS')


if __name__ == '__main__':
    main()
