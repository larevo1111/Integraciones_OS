#!/usr/bin/env python3
"""
sync_inventario_catalogo.py — Paso del pipeline
Sincroniza artículos de effi_data.zeffi_inventario (local) → inv_catalogo_articulos en Hostinger.
Agrega columnas calculadas: unidad y grupo.

Estrategia: DROP + CREATE + INSERT en lotes (mismo patrón que sync_espocrm_to_hostinger.py).

Ejecutar manualmente:
  python3 scripts/sync_inventario_catalogo.py
"""

import os
import re
import sys
from datetime import datetime

import mysql.connector
from sshtunnel import SSHTunnelForwarder
import pymysql

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_EFFI = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='effi_data', charset='utf8mb4',
)

SSH_HOST = '109.106.250.195'
SSH_PORT = 65002
SSH_USER = 'u768061575'
SSH_KEY  = os.path.expanduser('~/.ssh/sos_erp')

DB_HOSTINGER = dict(
    user='u768061575_osserver',
    password='Epist2487.',
    database='u768061575_os_integracion',
    charset='utf8mb4',
)

TABLA = 'inv_catalogo_articulos'
BATCH = 500

# ─── DDL ───────────────────────────────────────────────────────────────────────

DDL = f"""
CREATE TABLE IF NOT EXISTS `{TABLA}` (
    `id_effi`          VARCHAR(20)    NOT NULL,
    `cod_barras`       VARCHAR(50)    DEFAULT NULL,
    `nombre`           VARCHAR(255)   NOT NULL,
    `categoria`        VARCHAR(100)   DEFAULT NULL,
    `vigencia`         VARCHAR(20)    DEFAULT 'Vigente',
    `tipo_articulo`    VARCHAR(50)    DEFAULT NULL,
    `gestion_stock`    VARCHAR(10)    DEFAULT NULL,
    `costo_promedio`   DECIMAL(15,2)  DEFAULT 0,
    `stock_total`      DECIMAL(15,2)  DEFAULT 0,
    `unidad`           VARCHAR(5)     NOT NULL DEFAULT 'UND',
    `grupo`            VARCHAR(5)     NOT NULL DEFAULT 'MP',
    `actualizado_en`   DATETIME       DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id_effi`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ─── Detección de unidad (misma lógica que calcular_rangos.py) ─────────────────

def detectar_unidad(nombre):
    n = (nombre or '').upper()
    if re.search(r'\bX\s*KG\b|\bKG\b|\bX\s*KILO\b|\bKILO\b|\bKL\b', n):
        return 'KG'
    if re.search(r'\bGRS?\b|\bGRAMOS?\b|\b\d+\s*GRS?\b|\b\d+\s*G\b', n):
        return 'GRS'
    if re.search(r'\bLT\b|\bLITRO\b|\bLTS\b|\bX\s*LT\b', n):
        return 'LT'
    if re.search(r'\bML\b|\bMILILITROS?\b', n):
        return 'ML'
    return 'UND'


# ─── Detección de grupo (misma lógica que calcular_rangos.py) ──────────────────

def detectar_grupo(id_effi, nombre, categoria, ids_producidos):
    nom = (nombre or '').upper()
    cat = (categoria or '').upper()

    if 'DESPERDICIO' in nom or 'DESPERDI' in nom:
        return 'DES'
    if cat.startswith('TPT'):
        return 'PT'
    if cat.startswith('T03'):
        return 'INS'
    if 'DESARROLLO' in cat:
        return 'DS'
    if str(id_effi) in ids_producidos:
        return 'PP'
    return 'MP'


# ─── Leer artículos ───────────────────────────────────────────────────────────

def leer_articulos():
    conn = pymysql.connect(**DB_EFFI, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, cod_barras, nombre, categoria, vigencia, tipo_de_articulo,
                   gestion_de_stock,
                   CAST(REPLACE(COALESCE(costo_promedio, '0'), ',', '.') AS DECIMAL(15,2)) AS costo_promedio,
                   CAST(REPLACE(COALESCE(stock_total_empresa, '0'), ',', '.') AS DECIMAL(15,2)) AS stock_total
            FROM zeffi_inventario
            WHERE vigencia = 'Vigente'
            ORDER BY nombre
        """)
        articulos = cur.fetchall()

        # IDs producidos en OPs (para detectar PP)
        cur.execute("""
            SELECT DISTINCT cod_articulo
            FROM zeffi_articulos_producidos
            WHERE vigencia = 'Orden vigente'
        """)
        ids_producidos = {str(r['cod_articulo']) for r in cur.fetchall()}
    conn.close()

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    resultado = []
    for a in articulos:
        unidad = detectar_unidad(a['nombre'])
        grupo = detectar_grupo(a['id'], a['nombre'], a['categoria'], ids_producidos)
        resultado.append({
            'id_effi': str(a['id']),
            'cod_barras': a['cod_barras'],
            'nombre': a['nombre'],
            'categoria': a['categoria'],
            'vigencia': a['vigencia'],
            'tipo_articulo': a['tipo_de_articulo'],
            'gestion_stock': a['gestion_de_stock'],
            'costo_promedio': float(a['costo_promedio'] or 0),
            'stock_total': float(a['stock_total'] or 0),
            'unidad': unidad,
            'grupo': grupo,
            'actualizado_en': ahora,
        })

    return resultado


# ─── Insertar en Hostinger ─────────────────────────────────────────────────────

COLUMNAS = [
    'id_effi', 'cod_barras', 'nombre', 'categoria', 'vigencia',
    'tipo_articulo', 'gestion_stock', 'costo_promedio', 'stock_total',
    'unidad', 'grupo', 'actualizado_en',
]

def insertar_lotes(cur_host, conn_host, articulos):
    cols = ', '.join(f'`{c}`' for c in COLUMNAS)
    phs  = ', '.join(['%s'] * len(COLUMNAS))
    sql  = f"INSERT INTO `{TABLA}` ({cols}) VALUES ({phs})"

    total = 0
    for i in range(0, len(articulos), BATCH):
        lote = articulos[i:i + BATCH]
        vals = [tuple(r.get(c) for c in COLUMNAS) for r in lote]
        cur_host.executemany(sql, vals)
        conn_host.commit()
        total += len(lote)
    return total


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    articulos = leer_articulos()

    # También guardar en effi_data local (para la API de inventario)
    conn_local = pymysql.connect(**DB_EFFI)
    with conn_local.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS `{TABLA}`")
        cur.execute(DDL.replace('IF NOT EXISTS ', ''))
        cols = ', '.join(f'`{c}`' for c in COLUMNAS)
        phs  = ', '.join(['%s'] * len(COLUMNAS))
        for i in range(0, len(articulos), BATCH):
            lote = articulos[i:i + BATCH]
            vals = [tuple(r.get(c) for c in COLUMNAS) for r in lote]
            cur.executemany(f"INSERT INTO `{TABLA}` ({cols}) VALUES ({phs})", vals)
        conn_local.commit()
    conn_local.close()
    print(f'  📦 {len(articulos)} artículos → {TABLA} en effi_data (local)')

    # Sync a Hostinger
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY,
        remote_bind_address=('127.0.0.1', 3306),
    )
    tunnel.start()

    try:
        conn_host = mysql.connector.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            **DB_HOSTINGER,
        )
        cur_host = conn_host.cursor()
        cur_host.execute("SET SESSION sql_mode='NO_ENGINE_SUBSTITUTION'")

        cur_host.execute(f"DROP TABLE IF EXISTS `{TABLA}`")
        cur_host.execute(DDL)
        conn_host.commit()

        total = insertar_lotes(cur_host, conn_host, articulos)

        cur_host.close()
        conn_host.close()

        print(f'✅ sync_inventario_catalogo — {total} artículos → {TABLA} en Hostinger')

    finally:
        tunnel.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_inventario_catalogo — ERROR: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
