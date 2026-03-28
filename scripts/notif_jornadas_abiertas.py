"""
Notificación de jornadas abiertas — se ejecuta a las 8pm todos los días vía cron.
- Envía recordatorio por WhatsApp al usuario con jornada abierta.
- Envía resumen al admin (Santiago) por WhatsApp.
- Si alguien no tiene teléfono registrado, lo reporta en el resumen.

Fuentes de datos:
- Jornadas: u768061575_os_gestion (Hostinger)
- Usuarios y teléfonos: u768061575_os_comunidad.sys_usuarios (Hostinger)
- NUNCA consultar ia_service_os para datos de usuarios.
"""
import os
import pymysql
import requests
from datetime import date
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

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

EMPRESA      = 'ori_sil_2'


def enviar_whatsapp(telefono, mensaje):
    """Envía mensaje por WhatsApp vía wa_bridge. Retorna True si exitoso."""
    if not telefono:
        return False
    # wa_bridge espera número sin '+' (ej: 573214550933)
    tel = telefono.lstrip('+')
    try:
        r = requests.post(
            f'{WA_BRIDGE_URL}/api/send/text',
            json={'to': tel, 'message': mensaje, 'caller_service': 'notif_jornadas'},
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
    hoy = date.today().isoformat()
    print(f'[notif_jornadas] {hoy} — verificando jornadas abiertas...')

    # Conectar a Hostinger vía SSH tunnel
    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_pkey=SSH_KEY,
        remote_bind_address=('127.0.0.1', 3306),
        local_bind_address=('127.0.0.1', 0)
    ) as tunnel:
        local_port = tunnel.local_bind_port

        # 1. Consultar jornadas abiertas (os_gestion)
        conn_g = pymysql.connect(
            host='127.0.0.1', port=local_port,
            user=GESTION_USER, password=GESTION_PASS,
            database=GESTION_DB,
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            with conn_g.cursor() as cur:
                cur.execute("""
                    SELECT j.id, j.usuario, j.fecha, j.hora_inicio,
                           j.hora_inicio_registro,
                           TIMESTAMPDIFF(MINUTE, j.hora_inicio_registro, UTC_TIMESTAMP()) AS minutos_activa
                    FROM g_jornadas j
                    WHERE j.empresa = %s
                      AND j.fecha = %s
                      AND j.hora_fin IS NULL
                    ORDER BY j.hora_inicio_registro
                """, (EMPRESA, hoy))
                abiertas = cur.fetchall()
        finally:
            conn_g.close()

        if not abiertas:
            print('  Sin jornadas abiertas. OK.')
            return

        print(f'  {len(abiertas)} jornada(s) abierta(s)')

        # 2. Consultar teléfonos desde sys_usuarios (os_comunidad)
        emails = [j['usuario'] for j in abiertas]
        contactos = obtener_contactos(emails, local_port)

    # 3. Enviar notificaciones WhatsApp
    notificados = []
    sin_telefono = []

    for j in abiertas:
        info = contactos.get(j['usuario'])
        nombre = (info['Nombre_Usuario'] if info else None) or j['usuario'].split('@')[0]
        mins = j['minutos_activa'] or 0
        horas = mins // 60
        minutos = mins % 60
        tiempo = f'{horas}h {minutos}m' if horas > 0 else f'{minutos}m'

        if info and info.get('telefono'):
            msg = (
                f"⏰ *Jornada abierta*\n\n"
                f"Hola {nombre}, tienes una jornada abierta "
                f"desde hace *{tiempo}*.\n\n"
                f"Si ya terminaste tu día, ciérrala desde "
                f"https://gestion.oscomunidad.com"
            )
            ok = enviar_whatsapp(info['telefono'], msg)
            if ok:
                notificados.append(nombre)
                print(f'  ✓ Notificado: {nombre} ({j["usuario"]})')
            else:
                sin_telefono.append(f'{nombre} ({j["usuario"]}) — error envío')
        else:
            sin_telefono.append(f'{nombre} ({j["usuario"]}) — sin teléfono')

    # 4. Resumen al admin por WhatsApp
    lineas = []
    for j in abiertas:
        info = contactos.get(j['usuario'])
        nombre = (info['Nombre_Usuario'] if info else None) or j['usuario'].split('@')[0]
        mins = j['minutos_activa'] or 0
        horas = mins // 60
        minutos = mins % 60
        tiempo = f'{horas}h {minutos}m' if horas > 0 else f'{minutos}m'
        lineas.append(f"• {nombre} — {tiempo}")

    resumen = (
        f"📋 *Jornadas abiertas — {hoy}*\n\n"
        + '\n'.join(lineas)
        + f"\n\n✅ Notificados: {len(notificados)}"
    )
    if sin_telefono:
        resumen += f"\n⚠️ Sin WhatsApp: {', '.join(sin_telefono)}"

    enviar_whatsapp(ADMIN_PHONE, resumen)
    print(f'  Resumen enviado al admin.')


if __name__ == '__main__':
    main()
