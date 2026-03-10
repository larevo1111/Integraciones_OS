#!/usr/bin/env python3
"""
sync_espocrm_to_hostinger.py — Paso 6d del pipeline
Sincroniza los contactos de EspoCRM (BD local) → tabla crm_contactos en Hostinger.

Estrategia: TRUNCATE + INSERT en lotes.
Propósito: visibilidad de contactos EspoCRM en AppSheet / NocoDB.

Ejecutar manualmente:
  python3 scripts/sync_espocrm_to_hostinger.py
"""

import os
import sys
from datetime import datetime

import mysql.connector
from sshtunnel import SSHTunnelForwarder

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_ESPO = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='espocrm', charset='utf8mb4',
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

TABLA = 'crm_contactos'
BATCH = 500

# ─── DDL de la tabla en Hostinger ──────────────────────────────────────────────

DDL = f"""
CREATE TABLE IF NOT EXISTS `{TABLA}` (
    `id`                   VARCHAR(17)  NOT NULL,
    `nombre_completo`      VARCHAR(200) DEFAULT NULL,
    `first_name`           VARCHAR(100) DEFAULT NULL,
    `last_name`            VARCHAR(100) DEFAULT NULL,
    `numero_identificacion` VARCHAR(100) DEFAULT NULL,
    `tipo_identificacion`  VARCHAR(100) DEFAULT NULL,
    `tipo_persona`         VARCHAR(100) DEFAULT NULL,
    `email`                VARCHAR(200) DEFAULT NULL,
    `telefono`             VARCHAR(50)  DEFAULT NULL,
    `address_street`       VARCHAR(255) DEFAULT NULL,
    `address_city`         VARCHAR(100) DEFAULT NULL,
    `address_state`        VARCHAR(100) DEFAULT NULL,
    `address_country`      VARCHAR(100) DEFAULT NULL,
    `ciudad`               VARCHAR(200) DEFAULT NULL,
    `departamento`         VARCHAR(150) DEFAULT NULL,
    `pais`                 VARCHAR(100) DEFAULT NULL,
    `tipo_de_marketing`    VARCHAR(255) DEFAULT NULL,
    `tipo_cliente`         VARCHAR(100) DEFAULT NULL,
    `tarifa_precios`       VARCHAR(255) DEFAULT NULL,
    `forma_pago`           VARCHAR(100) DEFAULT NULL,
    `vendedor_effi`        VARCHAR(255) DEFAULT NULL,
    `fuente`               VARCHAR(50)  DEFAULT NULL,
    `enviado_a_effi`       TINYINT(1)   DEFAULT 0,
    `descripcion`          TEXT         DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ─── Leer contactos ────────────────────────────────────────────────────────────

def leer_contactos(conn_espo):
    cur = conn_espo.cursor(dictionary=True, buffered=True)
    cur.execute("""
        SELECT
            c.id,
            c.first_name,
            c.last_name,
            TRIM(CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.last_name,''))) AS nombre_completo,
            c.numero_identificacion,
            c.tipo_identificacion,
            c.tipo_persona,
            c.address_street,
            c.address_city,
            c.address_state,
            c.address_country,
            cd.name        AS ciudad,
            cd.departamento,
            cd.pais,
            c.tipo_de_marketing,
            c.tipo_cliente,
            c.tarifa_precios,
            c.forma_pago,
            c.vendedor_effi,
            c.fuente,
            c.enviado_a_effi,
            c.description  AS descripcion,
            -- email primario
            (SELECT ea.name FROM entity_email_address eea
             JOIN email_address ea ON ea.id = eea.email_address_id
             WHERE eea.entity_id = c.id AND eea.entity_type = 'Contact'
               AND eea.deleted = 0 AND eea.`primary` = 1 LIMIT 1) AS email,
            -- teléfono primario
            (SELECT pn.name FROM entity_phone_number epn
             JOIN phone_number pn ON pn.id = epn.phone_number_id
             WHERE epn.entity_id = c.id AND epn.entity_type = 'Contact'
               AND epn.deleted = 0 AND epn.`primary` = 1 LIMIT 1) AS telefono
        FROM contact c
        LEFT JOIN ciudad cd ON cd.id = c.ciudad_id
        WHERE c.deleted = 0
        ORDER BY c.first_name, c.last_name
    """)
    rows = cur.fetchall()
    cur.close()
    return rows


# ─── Insertar en Hostinger ─────────────────────────────────────────────────────

COLUMNAS = [
    'id', 'nombre_completo', 'first_name', 'last_name',
    'numero_identificacion', 'tipo_identificacion', 'tipo_persona',
    'email', 'telefono',
    'address_street', 'address_city', 'address_state', 'address_country',
    'ciudad', 'departamento', 'pais',
    'tipo_de_marketing', 'tipo_cliente', 'tarifa_precios', 'forma_pago',
    'vendedor_effi', 'fuente', 'enviado_a_effi', 'descripcion',
]

def insertar_lotes(cur_host, conn_host, contactos):
    cols   = ', '.join(f'`{c}`' for c in COLUMNAS)
    phs    = ', '.join(['%s'] * len(COLUMNAS))
    sql    = f"INSERT INTO `{TABLA}` ({cols}) VALUES ({phs})"

    total = 0
    for i in range(0, len(contactos), BATCH):
        lote = contactos[i:i + BATCH]
        vals = [tuple(r.get(c) for c in COLUMNAS) for r in lote]
        cur_host.executemany(sql, vals)
        conn_host.commit()
        total += len(lote)
    return total


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn_espo = mysql.connector.connect(**DB_ESPO)
    contactos = leer_contactos(conn_espo)
    conn_espo.close()

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

        # Crear tabla si no existe
        cur_host.execute(DDL)
        conn_host.commit()

        # TRUNCATE + INSERT
        cur_host.execute(f"TRUNCATE TABLE `{TABLA}`")
        conn_host.commit()

        total = insertar_lotes(cur_host, conn_host, contactos)

        cur_host.close()
        conn_host.close()

        print(f'✅ sync_espocrm_to_hostinger — {total} contactos → {TABLA} en Hostinger')

    finally:
        tunnel.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_espocrm_to_hostinger — ERROR: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
