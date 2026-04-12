#!/usr/bin/env python3
"""
monitor_ia.py — Monitor del stack IA (cada 2 horas).
Chequea componentes críticos, toma acciones correctivas y notifica.

Uso:
  python3 monitor_ia.py              # Siempre notifica
  python3 monitor_ia.py --silencioso # Solo si hay novedades
"""
import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

from checks_sistema import (
    check_servicios, check_opencode, check_gpu,
    check_bot_errores, check_ia_service, check_consumo_ia,
)

BOT_TOKEN  = os.getenv('TELEGRAM_BOT_TOKEN')
NOTIF_TOKEN = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN')
SANTI_CHAT = os.getenv('TELEGRAM_NOTIF_CHAT_ID')
REPO_DIR   = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
LOG_FILE   = os.path.join(REPO_DIR, 'logs', 'monitor_ia.log')
BOT_LOG    = os.path.join(REPO_DIR, 'logs', 'telegram_bot.log')

SERVICIOS = ['ia-service', 'os-telegram-bot', 'ollama', 'os-ialocal']


def _log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts}  {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _enviar_telegram(mensaje):
    try:
        import requests
        token = BOT_TOKEN or NOTIF_TOKEN
        if not token or not SANTI_CHAT:
            return
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': SANTI_CHAT, 'text': mensaje, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        _log(f'Error Telegram: {e}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--silencioso', action='store_true')
    args = parser.parse_args()

    _log(f'=== Monitor IA {datetime.now().strftime("%H:%M")} ===')

    checks = [
        ('SERVICIOS',  lambda: check_servicios(SERVICIOS, _log)),
        ('IA SERVICE', lambda: check_ia_service(_log)),
        ('OPENCODE',   lambda: check_opencode(_log)),
        ('GPU',        lambda: check_gpu(_log)),
        ('BOT',        lambda: check_bot_errores(BOT_LOG, _log)),
        ('CONSUMO',    lambda: check_consumo_ia(_log)),
    ]

    todas_lineas, todas_acciones, total_fallos = [], [], 0

    for titulo, fn in checks:
        try:
            lineas, fallos, acciones = fn()
        except Exception as e:
            lineas, fallos, acciones = [f'❌ {titulo}: {str(e)[:80]}'], 1, []
        todas_lineas.extend(lineas)
        todas_acciones.extend(acciones)
        total_fallos += fallos
        for l in lineas:
            _log(l)

    _log(f'Fallos: {total_fallos} | Auto-correcciones: {len(todas_acciones)}')

    hay_novedad = total_fallos > 0 or todas_acciones
    if args.silencioso and not hay_novedad:
        return 0

    fecha_hora = datetime.now().strftime('%d/%m %H:%M')
    if not total_fallos and not todas_acciones:
        encabezado = f'🟢 <b>Monitor IA — {fecha_hora}</b>\nTodo operativo'
    elif not total_fallos:
        encabezado = f'🔧 <b>Monitor IA — {fecha_hora}</b>\nAuto-correcciones aplicadas'
    else:
        encabezado = f'🔴 <b>Monitor IA — {fecha_hora}</b>\n{total_fallos} fallo(s) sin resolver'

    partes = [encabezado, '']
    partes += [l for l in todas_lineas if l.startswith(('❌', '⚠️'))]
    if todas_acciones:
        partes += ['', '<b>Acciones automáticas:</b>'] + todas_acciones
    if total_fallos:
        partes += ['', '💬 Responde a este mensaje para que Claude investigue.']

    mensaje = '\n'.join(partes)
    _enviar_telegram(mensaje[:4000])
    return total_fallos


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
