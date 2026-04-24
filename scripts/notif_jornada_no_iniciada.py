"""
Notificación de jornada NO iniciada — se ejecuta a las 9am L-V vía cron.

Criterios:
- Usuario activo = tuvo al menos una jornada en los últimos 7 días
- NO tiene jornada de hoy (ni abierta ni cerrada)
- Está en sis_usuarios con estado='activo' y tiene teléfono registrado

- Envía aviso por WhatsApp al usuario.
- Envía resumen al admin (Santiago) por WhatsApp.

Fuentes de datos:
- Jornadas: os_gestion (VPS Contabo)
- Usuarios y teléfonos: sos_master_erp.sis_usuarios (VPS) — desde 2026-04-24
"""
import os
import sys
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DRY_RUN = '--dry-run' in sys.argv

# ── Helper central de BD ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import gestion, master

WA_BRIDGE_URL = 'http://localhost:3100'
ADMIN_PHONE   = '573022921455'  # Santiago (ssierra047@gmail.com)

EMPRESA      = 'ori_sil_2'


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


def obtener_contactos(emails: list) -> dict:
    """Busca nombre y teléfono en sis_usuarios (master VPS)."""
    if not emails:
        return {}
    with master(dict_cursor=True) as conn:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(emails))
            cur.execute(
                f"SELECT email AS Email, nombre AS Nombre_Usuario, telefono FROM sis_usuarios "
                f"WHERE email IN ({placeholders}) AND estado='activo'",
                emails
            )
            return {r['Email']: r for r in cur.fetchall()}


def main():
    hoy        = date.today().isoformat()
    hace7dias  = (date.today() - timedelta(days=7)).isoformat()
    print(f'[notif_jornada_no_iniciada] {hoy} — verificando usuarios sin jornada hoy...')

    # 1. Usuarios activos (con jornada en últimos 7 días) SIN jornada hoy
    with gestion(dict_cursor=True) as conn_g:
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

    if not sin_jornada_hoy:
        print('  Todos los usuarios activos ya iniciaron jornada hoy. OK.')
        return

    print(f'  {len(sin_jornada_hoy)} usuario(s) activo(s) sin jornada hoy')

    # 2. Consultar teléfonos y nombres desde sis_usuarios (master VPS)
    emails = [u['usuario'] for u in sin_jornada_hoy]
    contactos = obtener_contactos(emails)

    # 3. Enviar notificaciones WhatsApp
    notificados   = []
    sin_telefono  = []
    inactivos     = []

    for u in sin_jornada_hoy:
        info = contactos.get(u['usuario'])
        # Si no está en sis_usuarios con estado='activo', se descarta
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
