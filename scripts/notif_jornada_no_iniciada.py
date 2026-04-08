"""
Notificación de jornada NO iniciada — se ejecuta a las 9am L-V vía cron.

Criterios:
- Usuario activo = tuvo al menos una jornada en los últimos 7 días
- NO tiene jornada de hoy (ni abierta ni cerrada)
- Está en sys_usuarios con estado='Activo' y tiene teléfono registrado

- Envía aviso por WhatsApp al usuario.
- Envía resumen al admin (Santiago) por WhatsApp.

Fuentes de datos:
- Jornadas: u768061575_os_gestion (Hostinger)
- Usuarios y teléfonos: u768061575_os_comunidad.sys_usuarios (Hostinger)
"""
import os
import sys
import pymysql
import requests
from datetime import date, timedelta
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DRY_RUN = '--dry-run' in sys.argv

# ── Config ──────────────────────────────────────────────────────
SSH_HOST     = '109.106.250.195'
SSH_PORT     = 65002
SSH_USER     = 'u768061575'
SSH_KEY      = os.path.expanduser('~/.ssh/sos_erp')

GESTION_DB   = 'u768061575_os_gestion'
GESTION_USER = 'u768061575_os_gestion'
GESTION_PASS = 'Epist2487.'

COMUNIDAD_DB   = 'u768061575_os_comunidad'
COMUNIDAD_USER = 'u768061575_ssierra047'
COMUNIDAD_PASS = 'Epist2487.'

WA_BRIDGE_URL = 'http://localhost:3100'
ADMIN_PHONE   = '573022921455'  # Santiago (ssierra047@gmail.com)

EMPRESA      = 'Ori_Sil_2'


def enviar_whatsapp(telefono, mensaje):
    """Envía mensaje por WhatsApp vía wa_bridge. Retorna True si exitoso."""
    if not telefono:
        return False
    tel = telefono.lstrip('+')
    if DRY_RUN:
        print(f'  [DRY-RUN] → {tel}')
        for line in mensaje.split('\n'):
            print(f'             {line}')
        return True
    try:
        r = requests.post(
            f'{WA_BRIDGE_URL}/api/send/text',
            json={'to': tel, 'message': mensaje, 'caller_service': 'notif_jornada_no_iniciada'},
            timeout=15
        )
        return r.ok
    except Exception as e:
        print(f'  Error WhatsApp → {tel}: {e}')
        return False


def obtener_contactos(emails: list, tunnel_port: int) -> dict:
    """Busca nombre y teléfono en sys_usuarios (os_comunidad) vía SSH tunnel."""
    if not emails:
        return {}
    conn = pymysql.connect(
        host='127.0.0.1', port=tunnel_port,
        user=COMUNIDAD_USER, password=COMUNIDAD_PASS,
        database=COMUNIDAD_DB,
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(emails))
            cur.execute(
                f"SELECT `Email`, `Nombre_Usuario`, `telefono` FROM sys_usuarios "
                f"WHERE `Email` IN ({placeholders}) AND estado='Activo'",
                emails
            )
            return {r['Email']: r for r in cur.fetchall()}
    finally:
        conn.close()


def main():
    hoy        = date.today().isoformat()
    hace7dias  = (date.today() - timedelta(days=7)).isoformat()
    print(f'[notif_jornada_no_iniciada] {hoy} — verificando usuarios sin jornada hoy...')

    # Conectar a Hostinger vía SSH tunnel
    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY,
        remote_bind_address=('127.0.0.1', 3306),
        local_bind_address=('127.0.0.1', 0)
    ) as tunnel:
        local_port = tunnel.local_bind_port

        # 1. Usuarios activos (con jornada en últimos 7 días) SIN jornada hoy
        conn_g = pymysql.connect(
            host='127.0.0.1', port=local_port,
            user=GESTION_USER, password=GESTION_PASS,
            database=GESTION_DB,
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            with conn_g.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT j.usuario
                    FROM g_jornadas j
                    WHERE j.empresa = %s
                      AND j.fecha >= %s
                      AND j.usuario NOT IN (
                          SELECT usuario FROM g_jornadas
                          WHERE empresa = %s AND fecha = %s
                      )
                    ORDER BY j.usuario
                """, (EMPRESA, hace7dias, EMPRESA, hoy))
                sin_jornada_hoy = cur.fetchall()
        finally:
            conn_g.close()

        if not sin_jornada_hoy:
            print('  Todos los usuarios activos ya iniciaron jornada hoy. OK.')
            return

        print(f'  {len(sin_jornada_hoy)} usuario(s) activo(s) sin jornada hoy')

        # 2. Consultar teléfonos y nombres desde sys_usuarios (os_comunidad)
        emails = [u['usuario'] for u in sin_jornada_hoy]
        contactos = obtener_contactos(emails, local_port)

    # 3. Enviar notificaciones WhatsApp
    notificados   = []
    sin_telefono  = []
    inactivos     = []

    for u in sin_jornada_hoy:
        info = contactos.get(u['usuario'])
        # Si no está en sys_usuarios con estado='Activo', se descarta
        if not info:
            inactivos.append(u['usuario'])
            continue

        nombre = info.get('Nombre_Usuario') or u['usuario'].split('@')[0]

        if info.get('telefono'):
            msg = (
                f"⏰ *Jornada no iniciada*\n\n"
                f"Hola {nombre}, ya son las 9am y no has iniciado tu jornada hoy.\n\n"
                f"Ábrela desde https://gestion.oscomunidad.com"
            )
            ok = enviar_whatsapp(info['telefono'], msg)
            if ok:
                notificados.append(nombre)
                print(f'  ✓ Notificado: {nombre} ({u["usuario"]})')
            else:
                sin_telefono.append(f'{nombre} ({u["usuario"]}) — error envío')
        else:
            sin_telefono.append(f'{nombre} ({u["usuario"]}) — sin teléfono')

    # 4. Resumen al admin por WhatsApp
    if not notificados and not sin_telefono and not inactivos:
        print('  Nada que reportar al admin.')
        return

    lineas = []
    for u in sin_jornada_hoy:
        info = contactos.get(u['usuario'])
        if not info:
            continue
        nombre = info.get('Nombre_Usuario') or u['usuario'].split('@')[0]
        lineas.append(f"• {nombre}")

    resumen = f"📋 *Jornadas no iniciadas — {hoy}*\n\n"
    if lineas:
        resumen += '\n'.join(lineas) + f"\n\n✅ Notificados: {len(notificados)}"
    else:
        resumen += "(ningún usuario activo sin jornada hoy)"

    if sin_telefono:
        resumen += f"\n⚠️ Sin WhatsApp: {', '.join(sin_telefono)}"

    enviar_whatsapp(ADMIN_PHONE, resumen)
    print(f'  Resumen enviado al admin.')


if __name__ == '__main__':
    main()
