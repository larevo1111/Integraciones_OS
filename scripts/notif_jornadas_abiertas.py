"""
Notificación de jornadas abiertas — se ejecuta a las 8pm todos los días vía cron.
- Envía recordatorio por WhatsApp al usuario con jornada abierta.
- Envía resumen al admin (Santiago) por WhatsApp.
- Si alguien no tiene teléfono registrado, lo reporta en el resumen.

Fuentes de datos:
- Jornadas: os_gestion (VPS Contabo)
- Usuarios y teléfonos: sos_master_erp.sis_usuarios (VPS) — desde 2026-04-24
- NUNCA consultar ia_service_os para datos de usuarios.
"""
import os
import sys

import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ── Helper central de BD (SSH tunnel + SET time_zone='-05:00' en sesión) ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import gestion, master

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


def obtener_contactos(emails):
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
    hoy = date.today().isoformat()
    print(f'[notif_jornadas] {hoy} — verificando jornadas abiertas...')

    # 1. Consultar jornadas abiertas. NOW() devuelve hora Colombia (el helper
    # hace SET time_zone='-05:00' en la sesión) → consistente con cómo se
    # guarda `hora_inicio_registro` (también NOW() en pool con -05:00).
    with gestion(dict_cursor=True) as conn_g:
        with conn_g.cursor() as cur:
            cur.execute("""
                SELECT j.id, j.usuario, j.fecha, j.hora_inicio,
                       j.hora_inicio_registro,
                       TIMESTAMPDIFF(MINUTE, j.hora_inicio_registro, NOW()) AS minutos_activa
                FROM g_jornadas j
                WHERE j.empresa = %s
                  AND j.fecha = %s
                  AND j.hora_fin IS NULL
                ORDER BY j.hora_inicio_registro
            """, (EMPRESA, hoy))
            abiertas = cur.fetchall()

    if not abiertas:
        print('  Sin jornadas abiertas. OK.')
        return

    print(f'  {len(abiertas)} jornada(s) abierta(s)')

    # 2. Consultar teléfonos desde sis_usuarios (master VPS)
    emails = [j['usuario'] for j in abiertas]
    contactos = obtener_contactos(emails)

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
