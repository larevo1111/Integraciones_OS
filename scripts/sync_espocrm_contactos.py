#!/usr/bin/env python3
"""
sync_espocrm_contactos.py — Paso 6c del pipeline
Sincroniza los clientes vigentes de Effi (zeffi_clientes) a la entidad
Contact de EspoCRM.

Estrategia:
  - Clave de upsert: numero_de_identificacion (campo numeroIdentificacion en EspoCRM)
  - Si el contacto ya existe → UPDATE todos los campos
  - Si no existe → INSERT con ID generado (17 hex chars, formato EspoCRM)
  - Email y teléfono: gestionados en tablas separadas (email_address / phone_number)
  - Vendedor: match por nombre completo contra usuarios EspoCRM → assigned_user_id
  - Solo clientes con vigencia = 'Vigente'

Ejecutar manualmente:
  python3 scripts/sync_espocrm_contactos.py
"""

import secrets
import sys
from datetime import datetime, timezone

import mysql.connector

# ─── Configuración ─────────────────────────────────────────────────────────────

DB_EFFI = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='effi_data',
)
DB_ESPO = dict(
    host='127.0.0.1', port=3306,
    user='osadmin', password='Epist2487.',
    database='espocrm',
)

CREATED_BY_ID = '69ab7a26c5d84edd9'   # ssierra — responsable de la importación

# ─── Helpers ───────────────────────────────────────────────────────────────────

def gen_id():
    """Genera un ID de 17 caracteres hex, formato EspoCRM."""
    return secrets.token_hex(9)[:17]


def now_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def v(val):
    """Normaliza: None si vacío."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def split_nombre(nombre):
    """
    Divide nombre completo en first_name / last_name.
    Para clientes Effi: el 50% son nombres de empresa o persona única.
    Estrategia: últimas 2 palabras = apellidos, resto = nombres.
    Si hay ≤ 2 palabras → todo en first_name, last_name=''.
    """
    if not nombre:
        return '', ''
    partes = nombre.strip().split()
    if len(partes) <= 2:
        return nombre.strip(), ''
    # Últimas 2 palabras como apellidos
    last  = ' '.join(partes[-2:])
    first = ' '.join(partes[:-2])
    return first, last


def cargar_usuarios_espo(cur_espo):
    """Devuelve dict {nombre_completo_lower: user_id}."""
    cur_espo.execute(
        "SELECT id, TRIM(CONCAT(COALESCE(first_name,''), ' ', COALESCE(last_name,''))) AS nombre "
        "FROM user WHERE deleted=0 AND user_name != 'system'"
    )
    return {row[1].lower().strip(): row[0] for row in cur_espo.fetchall() if row[1].strip()}


def resolver_vendedor(nombre_vendedor, usuarios_map):
    """Match por nombre completo (case-insensitive). Retorna user_id o None."""
    if not nombre_vendedor:
        return None
    return usuarios_map.get(nombre_vendedor.lower().strip())


def cargar_ciudades_espo(cur_espo):
    """Devuelve dict para lookup: (nombre_lower, depto_lower, pais_lower) → ciudad_id."""
    cur_espo.execute(
        "SELECT id, LOWER(name), LOWER(COALESCE(departamento,'')), LOWER(COALESCE(pais,'')) "
        "FROM ciudad WHERE deleted=0"
    )
    mapa = {}
    for city_id, nombre, depto, pais in cur_espo.fetchall():
        mapa[(nombre, depto, pais)] = city_id
        # Índice de respaldo: solo nombre + pais
        if (nombre, pais) not in mapa:
            mapa[(nombre, pais)] = city_id
    return mapa


def resolver_ciudad(nombre_ciudad, departamento, pais, ciudades_map):
    """Resuelve nombre ciudad → ciudad_id. Retorna None si no hay match."""
    if not nombre_ciudad:
        return None
    n = nombre_ciudad.lower().strip()
    d = (departamento or '').lower().strip()
    p = (pais or 'colombia').lower().strip()
    result = ciudades_map.get((n, d, p))
    if result:
        return result
    return ciudades_map.get((n, p))


# ─── Email y teléfono ──────────────────────────────────────────────────────────

def upsert_email(cur, contact_id, email_raw, now):
    if not email_raw:
        return
    email = email_raw.strip().lower()

    # ¿Ya existe esta dirección?
    cur.execute("SELECT id FROM email_address WHERE lower = %s AND deleted=0", (email,))
    row = cur.fetchone()
    if row:
        email_id = row[0]
    else:
        email_id = gen_id()
        cur.execute(
            "INSERT INTO email_address (id, name, lower, invalid, opt_out) VALUES (%s,%s,%s,0,0)",
            (email_id, email_raw.strip(), email)
        )

    # ¿Ya está vinculado a este contacto?
    cur.execute(
        "SELECT id FROM entity_email_address "
        "WHERE entity_id=%s AND entity_type='Contact' AND email_address_id=%s AND deleted=0",
        (contact_id, email_id)
    )
    if not cur.fetchone():
        # Desmarcar primarios anteriores
        cur.execute(
            "UPDATE entity_email_address SET `primary`=0 "
            "WHERE entity_id=%s AND entity_type='Contact' AND deleted=0",
            (contact_id,)
        )
        cur.execute(
            "INSERT INTO entity_email_address (entity_id, email_address_id, entity_type, `primary`, deleted) "
            "VALUES (%s,%s,'Contact',1,0)",
            (contact_id, email_id)
        )


def upsert_phone(cur, contact_id, phone_raw, phone_type, is_primary, now):
    if not phone_raw:
        return
    phone = phone_raw.strip()

    cur.execute("SELECT id FROM phone_number WHERE name=%s AND deleted=0", (phone,))
    row = cur.fetchone()
    if row:
        phone_id = row[0]
    else:
        phone_id = gen_id()
        cur.execute(
            "INSERT INTO phone_number (id, name, type, invalid, opt_out) VALUES (%s,%s,%s,0,0)",
            (phone_id, phone, phone_type)
        )

    cur.execute(
        "SELECT id FROM entity_phone_number "
        "WHERE entity_id=%s AND entity_type='Contact' AND phone_number_id=%s AND deleted=0",
        (contact_id, phone_id)
    )
    if not cur.fetchone():
        if is_primary:
            cur.execute(
                "UPDATE entity_phone_number SET `primary`=0 "
                "WHERE entity_id=%s AND entity_type='Contact' AND deleted=0",
                (contact_id,)
            )
        cur.execute(
            "INSERT INTO entity_phone_number (entity_id, phone_number_id, entity_type, `primary`, deleted) "
            "VALUES (%s,%s,'Contact',%s,0)",
            (contact_id, phone_id, 1 if is_primary else 0)
        )


# ─── Sync principal ────────────────────────────────────────────────────────────

def main():
    conn_effi = mysql.connector.connect(**DB_EFFI)
    conn_espo = mysql.connector.connect(**DB_ESPO, autocommit=False)
    cur_effi  = conn_effi.cursor(dictionary=True, buffered=True)
    cur_espo  = conn_espo.cursor(buffered=True)

    try:
        # Cargar mapeos de lookup
        usuarios_map = cargar_usuarios_espo(cur_espo)
        ciudades_map = cargar_ciudades_espo(cur_espo)

        # Leer todos los clientes vigentes de Effi
        cur_effi.execute("""
            SELECT
                numero_de_identificacion, tipo_de_identificacion,
                nombre, email, celular, whatsapp, telefono_1,
                direccion, ciudad, departamento, pais,
                tipo_de_persona, tipo_de_cliente, tipo_de_marketing,
                tarifa_de_precios, forma_de_pago,
                vendedor, observacia_n
            FROM zeffi_clientes
            WHERE vigencia = 'Vigente'
              AND numero_de_identificacion IS NOT NULL
              AND numero_de_identificacion != ''
        """)
        clientes = cur_effi.fetchall()

        ins = upd = skip = 0
        now = now_utc()

        for c in clientes:
            num_id    = v(c['numero_de_identificacion'])
            if not num_id:
                skip += 1
                continue

            first, last = split_nombre(v(c['nombre']) or '')
            vendedor_id = resolver_vendedor(v(c['vendedor']), usuarios_map)
            ciudad_id   = resolver_ciudad(v(c['ciudad']), v(c['departamento']), v(c['pais']), ciudades_map)

            # ¿Existe ya en EspoCRM?
            cur_espo.execute(
                "SELECT id FROM contact WHERE numero_identificacion=%s AND deleted=0",
                (num_id,)
            )
            row = cur_espo.fetchone()

            campos = {
                'first_name':           first[:100] if first else '',
                'last_name':            last[:100]  if last  else '',
                'address_street':       (v(c['direccion']) or '')[:255],
                'address_city':         (v(c['ciudad'])    or '')[:100],
                'address_state':        (v(c['departamento']) or '')[:100],
                'address_country':      (v(c['pais'])       or 'Colombia')[:100],
                'description':          v(c['observacia_n']),
                # campos custom
                'numero_identificacion': num_id[:100],
                'tipo_identificacion':  v(c['tipo_de_identificacion']),
                'tipo_persona':         v(c['tipo_de_persona']),
                'tipo_cliente':         v(c['tipo_de_cliente']),
                'tipo_de_marketing':    v(c['tipo_de_marketing']),
                'tarifa_precios':       v(c['tarifa_de_precios']),
                'forma_pago':           v(c['forma_de_pago']),
                'vendedor_effi':        v(c['vendedor']),
                'ciudad_id':            ciudad_id,
                'assigned_user_id':     vendedor_id,
                'fuente':               'Effi',
                'modified_at':          now,
                'modified_by_id':       CREATED_BY_ID,
            }

            if row:
                # UPDATE
                contact_id = row[0]
                set_clause = ', '.join(f'`{k}`=%s' for k in campos)
                cur_espo.execute(
                    f"UPDATE contact SET {set_clause} WHERE id=%s",
                    list(campos.values()) + [contact_id]
                )
                upd += 1
            else:
                # INSERT
                contact_id = gen_id()
                campos['id']            = contact_id
                campos['created_at']    = now
                campos['created_by_id'] = CREATED_BY_ID
                campos['deleted']       = 0

                cols = ', '.join(f'`{k}`' for k in campos)
                phs  = ', '.join(['%s'] * len(campos))
                cur_espo.execute(
                    f"INSERT INTO contact ({cols}) VALUES ({phs})",
                    list(campos.values())
                )
                ins += 1

            # Email y teléfonos
            upsert_email(cur_espo, contact_id, v(c['email']), now)
            upsert_phone(cur_espo, contact_id, v(c['celular']),   'Mobile', True,  now)
            upsert_phone(cur_espo, contact_id, v(c['whatsapp']),  'Mobile', False, now)
            upsert_phone(cur_espo, contact_id, v(c['telefono_1']),'Phone',  False, now)

        conn_espo.commit()
        total = ins + upd
        print(f'✅ sync_espocrm_contactos — {total} contactos '
              f'({ins} nuevos, {upd} actualizados, {skip} omitidos sin ID)')

    except Exception:
        conn_espo.rollback()
        raise
    finally:
        cur_effi.close()
        cur_espo.close()
        conn_effi.close()
        conn_espo.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ sync_espocrm_contactos — ERROR: {e}', file=sys.stderr)
        sys.exit(1)
