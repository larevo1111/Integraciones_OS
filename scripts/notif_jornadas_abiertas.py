"""
Notificación de jornadas abiertas — se ejecuta a las 8pm L-V vía cron.
Detecta jornadas sin cerrar y envía recordatorio por Telegram al usuario.
Si hay jornadas abiertas de otros, envía resumen al admin (Santiago).
"""
import os
import sys
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

LOCAL_DB     = 'ia_service_os'
LOCAL_USER   = os.getenv('DB_USER', 'osadmin')
LOCAL_PASS   = os.getenv('DB_PASS', 'Epist2487.')

BOT_TOKEN    = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_TG_ID  = os.getenv('TELEGRAM_NOTIF_CHAT_ID', '6833317403')

EMPRESA      = 'ori_sil_2'


def enviar_telegram(chat_id, mensaje):
    """Envía mensaje por Telegram. Retorna True si exitoso."""
    if not BOT_TOKEN or not chat_id:
        return False
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={'chat_id': str(chat_id), 'text': mensaje, 'parse_mode': 'HTML'},
            timeout=10
        )
        return r.ok
    except Exception as e:
        print(f'  Error Telegram → {chat_id}: {e}')
        return False


def obtener_telegram_ids(emails: list) -> dict:
    """Busca telegram_id en ia_usuarios local para una lista de emails."""
    if not emails:
        return {}
    conn = pymysql.connect(
        host='127.0.0.1', port=3306,
        user=LOCAL_USER, password=LOCAL_PASS,
        database=LOCAL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(emails))
            cur.execute(
                f"SELECT email, nombre, telegram_id FROM ia_usuarios "
                f"WHERE email IN ({placeholders}) AND activo=1 AND telegram_id IS NOT NULL",
                emails
            )
            return {r['email']: r for r in cur.fetchall()}
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
        local_bind_address=('127.0.0.1', 0)  # puerto local aleatorio
    ) as tunnel:
        local_port = tunnel.local_bind_port
        conn = pymysql.connect(
            host='127.0.0.1', port=local_port,
            user=GESTION_USER, password=GESTION_PASS,
            database=GESTION_DB,
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            with conn.cursor() as cur:
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
            conn.close()

    if not abiertas:
        print('  Sin jornadas abiertas. OK.')
        return

    print(f'  {len(abiertas)} jornada(s) abierta(s)')

    # Buscar telegram_ids
    emails = [j['usuario'] for j in abiertas]
    tg_map = obtener_telegram_ids(emails)

    notificados = []
    sin_telegram = []

    for j in abiertas:
        tg_info = tg_map.get(j['usuario'])
        nombre = (tg_info['nombre'] if tg_info else None) or j['usuario'].split('@')[0]
        mins = j['minutos_activa'] or 0
        horas = mins // 60
        minutos = mins % 60
        tiempo = f'{horas}h {minutos}m' if horas > 0 else f'{minutos}m'

        if tg_info and tg_info['telegram_id']:
            msg = (
                f"⏰ <b>Jornada abierta</b>\n\n"
                f"Hola {nombre}, tienes una jornada abierta "
                f"desde hace <b>{tiempo}</b>.\n\n"
                f"Si ya terminaste tu día, ciérrala desde "
                f"<a href=\"https://gestion.oscomunidad.com\">Gestión OS</a>."
            )
            ok = enviar_telegram(tg_info['telegram_id'], msg)
            if ok:
                notificados.append(nombre)
                print(f'  ✓ Notificado: {nombre} ({j["usuario"]})')
            else:
                sin_telegram.append(f'{nombre} ({j["usuario"]}) — error envío')
        else:
            sin_telegram.append(f'{nombre} ({j["usuario"]}) — sin Telegram')

    # Resumen al admin
    if abiertas:
        lineas = []
        for j in abiertas:
            ti = tg_map.get(j['usuario'])
            nombre = (ti['nombre'] if ti else None) or j['usuario'].split('@')[0]
            mins = j['minutos_activa'] or 0
            horas = mins // 60
            minutos = mins % 60
            tiempo = f'{horas}h {minutos}m' if horas > 0 else f'{minutos}m'
            lineas.append(f"• {nombre} — {tiempo}")

        resumen = (
            f"📋 <b>Jornadas abiertas — {hoy}</b>\n\n"
            + '\n'.join(lineas)
            + f"\n\n✉️ Notificados: {len(notificados)}"
        )
        if sin_telegram:
            resumen += f"\n⚠️ Sin Telegram: {', '.join(sin_telegram)}"

        enviar_telegram(ADMIN_TG_ID, resumen)
        print(f'  Resumen enviado al admin.')


if __name__ == '__main__':
    main()
