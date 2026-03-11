#!/usr/bin/env python3
"""
sync_hostinger.py
Sincroniza todas las tablas de effi_data (local MariaDB) → Hostinger MySQL.
Se ejecuta como paso 5 del pipeline, después de los scripts analíticos.

Estrategia: TRUNCATE + INSERT en lotes de 500 filas.
Estructura: recrea tabla en Hostinger si no existe (usando SHOW CREATE TABLE local).
Conexión Hostinger: SSH tunnel vía alias hostinger_erp (~/.ssh/sos_erp).
"""

import sys
import os
import datetime
import mysql.connector
from sshtunnel import SSHTunnelForwarder

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_LOCAL = dict(
    host='127.0.0.1',
    port=3306,
    user='osadmin',
    password='Epist2487.',
    database='effi_data',
    charset='utf8mb4',
)

SSH_HOST     = '109.106.250.195'
SSH_PORT     = 65002
SSH_USER     = 'u768061575'
SSH_KEY      = os.path.expanduser('~/.ssh/sos_erp')

DB_HOSTINGER = dict(
    user='u768061575_osserver',
    password='Epist2487.',
    database='u768061575_os_integracion',
    charset='utf8mb4',
)

BATCH_SIZE = 500   # filas por INSERT

# Tablas a excluir del sync (ninguna por ahora)
TABLAS_EXCLUIDAS = set()

# Tablas analíticas que viven SOLO en Hostinger.
# El pipeline las calcula en local (staging temporal), el sync las copia a Hostinger,
# y luego se eliminan de local. Fuente de verdad = Hostinger.
TABLAS_SOLO_HOSTINGER = {
    'resumen_ventas_facturas_mes',
    'resumen_ventas_facturas_canal_mes',
    'resumen_ventas_facturas_cliente_mes',
    'resumen_ventas_facturas_producto_mes',
    'resumen_ventas_remisiones_mes',
    'resumen_ventas_remisiones_canal_mes',
    'resumen_ventas_remisiones_cliente_mes',
    'resumen_ventas_remisiones_producto_mes',
}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def get_tablas(cursor):
    cursor.execute("SHOW TABLES")
    return [list(row.values())[0] for row in cursor.fetchall()
            if list(row.values())[0] not in TABLAS_EXCLUIDAS]

def get_create_table(cursor, tabla):
    cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
    row = cursor.fetchone()
    return list(row.values())[1]

def sync_tabla(conn_src, cursor_src, cursor_dst, conn_dst, tabla):
    # 1. Crear tabla en destino si no existe
    create_sql = get_create_table(cursor_src, tabla)
    # Reemplazar ENGINE por InnoDB (Hostinger puede no tener Aria)
    create_sql_dst = create_sql.replace('ENGINE=Aria', 'ENGINE=InnoDB') \
                               .replace('PAGE_CHECKSUM=1', '') \
                               .replace('TRANSACTIONAL=1', '')
    # CREATE TABLE IF NOT EXISTS
    create_sql_dst = create_sql_dst.replace(
        f'CREATE TABLE `{tabla}`',
        f'CREATE TABLE IF NOT EXISTS `{tabla}`',
        1
    )
    # Para tablas resumen_: DROP + CREATE para asegurar que el schema siempre esté actualizado
    if tabla.startswith('resumen_'):
        cursor_dst.execute(f"DROP TABLE IF EXISTS `{tabla}`")
        conn_dst.commit()
        final_sql = create_sql_dst.replace(
            f'CREATE TABLE IF NOT EXISTS `{tabla}`',
            f'CREATE TABLE `{tabla}`',
            1
        )
    else:
        final_sql = create_sql_dst
    cursor_dst.execute(final_sql)
    conn_dst.commit()

    # 2. TRUNCATE (para tablas zeffi_; resumen_ ya están vacías tras DROP+CREATE)
    cursor_dst.execute(f"TRUNCATE TABLE `{tabla}`")
    conn_dst.commit()

    # 3. Leer columnas (cursor independiente para no mezclar resultados)
    cur_schema = conn_src.cursor(dictionary=True, buffered=True)
    cur_schema.execute(f"SELECT * FROM `{tabla}` LIMIT 0")
    cols = [d[0] for d in cur_schema.description]
    cur_schema.close()
    if not cols:
        return 0

    cols_sql     = ', '.join(f'`{c}`' for c in cols)
    placeholders = ', '.join(['%s'] * len(cols))
    insert_sql   = f"INSERT INTO `{tabla}` ({cols_sql}) VALUES ({placeholders})"

    # 4. Leer y escribir en lotes
    cursor_src.execute(f"SELECT * FROM `{tabla}`")
    total = 0
    while True:
        rows = cursor_src.fetchmany(BATCH_SIZE)
        if not rows:
            break
        vals = [tuple(row.values()) for row in rows]
        cursor_dst.executemany(insert_sql, vals)
        conn_dst.commit()
        total += len(rows)

    return total

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    inicio = datetime.datetime.now()
    print(f'▶ sync_hostinger.py — {inicio.strftime("%Y-%m-%d %H:%M:%S")}')

    # ── Conectar a MariaDB local ──────────────────────────────────────────────
    conn_local  = mysql.connector.connect(**DB_LOCAL)
    cur_local   = conn_local.cursor(dictionary=True, buffered=True)

    tablas = get_tablas(cur_local)
    print(f'   Tablas a sincronizar: {len(tablas)}')

    # ── Abrir SSH tunnel a Hostinger ─────────────────────────────────────────
    tunnel = SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY,
        remote_bind_address=('127.0.0.1', 3306),
    )
    tunnel.start()

    conn_host = mysql.connector.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        **DB_HOSTINGER,
    )
    cur_host = conn_host.cursor(dictionary=True, buffered=True)

    # Deshabilitar checks para import más rápido
    cur_host.execute("SET FOREIGN_KEY_CHECKS=0")
    cur_host.execute("SET UNIQUE_CHECKS=0")
    cur_host.execute("SET SESSION sql_mode='NO_ENGINE_SUBSTITUTION'")

    # ── Sincronizar tabla por tabla ───────────────────────────────────────────
    errores  = []
    resumen  = []

    for tabla in tablas:
        try:
            n = sync_tabla(conn_local, cur_local, cur_host, conn_host, tabla)
            resumen.append(f'   ✅ {tabla}: {n} filas')
            print(resumen[-1])
        except Exception as e:
            msg = f'   ❌ {tabla}: {e}'
            errores.append(msg)
            print(msg)
            conn_host.rollback()

    # Restaurar checks
    cur_host.execute("SET FOREIGN_KEY_CHECKS=1")
    cur_host.execute("SET UNIQUE_CHECKS=1")
    conn_host.commit()

    # ── Limpiar tablas analíticas de local (viven solo en Hostinger) ─────────
    cur_cleanup = conn_local.cursor()
    for t in TABLAS_SOLO_HOSTINGER:
        try:
            cur_cleanup.execute(f"DROP TABLE IF EXISTS `{t}`")
        except Exception:
            pass
    conn_local.commit()
    cur_cleanup.close()

    # ── Cerrar conexiones ─────────────────────────────────────────────────────
    cur_local.close()
    conn_local.close()
    cur_host.close()
    conn_host.close()
    tunnel.stop()

    dur = int((datetime.datetime.now() - inicio).total_seconds())
    ok  = len(tablas) - len(errores)
    print(f'\n✅ sync_hostinger — {ok}/{len(tablas)} tablas OK  ❌ {len(errores)} errores  [{dur}s]')

    if errores:
        sys.exit(1)

if __name__ == '__main__':
    main()
