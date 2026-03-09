#!/usr/bin/env python3
"""
orquestador.py
Pipeline Effi → MariaDB — Orquestador Python

Horario operativo: cada 2h | 06:00–20:00 | Lunes–Sábado
Auto-restart: vía systemd (Restart=on-failure)
Notificaciones: email (siempre) + Telegram (solo en error)
"""

import os
import sys
import subprocess
import itertools
import smtplib
import logging
import datetime
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ─── Rutas ─────────────────────────────────────────────────────────────────────

SCRIPTS_DIR   = Path('/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts')
ENV_FILE      = SCRIPTS_DIR / '.env'
LOG_FILE      = Path('/home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/pipeline.log')
EXPORT_SCRIPT = SCRIPTS_DIR / 'export_all.sh'
IMPORT_SCRIPT = SCRIPTS_DIR / 'import_all.js'

EXPORT_TIMEOUT = 30 * 60   # 30 minutos (margen sobre los ~20 min reales)
IMPORT_TIMEOUT =  5 * 60   # 5 minutos

# ─── Logging ───────────────────────────────────────────────────────────────────

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ]
)
log = logging.getLogger(__name__)

# ─── Leer .env ─────────────────────────────────────────────────────────────────

def cargar_env():
    env = {}
    if not ENV_FILE.exists():
        log.warning(f'Archivo .env no encontrado en {ENV_FILE}')
        return env
    for linea in ENV_FILE.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if linea and not linea.startswith('#') and '=' in linea:
            clave, _, valor = linea.partition('=')
            env[clave.strip()] = valor.strip().strip('"').strip("'")
    return env

# ─── Horario operativo ─────────────────────────────────────────────────────────

def es_horario_operativo():
    """
    Retorna (True, '') si debe correr.
    Retorna (False, motivo) si debe omitirse.
    Horario: Lun–Sab (0–5), 06:00–19:59.
    """
    ahora = datetime.datetime.now()
    if ahora.weekday() == 6:   # 6 = domingo
        return False, 'domingo'
    if ahora.hour < 6 or ahora.hour >= 20:
        return False, f'fuera de horario ({ahora.strftime("%H:%M")})'
    return True, ''

# ─── Ejecutar subproceso ───────────────────────────────────────────────────────

def ejecutar(cmd, timeout, cwd=None):
    """Ejecuta un comando. Retorna (exit_code, salida_str)."""
    try:
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or SCRIPTS_DIR),
        )
        salida = resultado.stdout
        if resultado.stderr.strip():
            salida += '\n[STDERR]\n' + resultado.stderr
        return resultado.returncode, salida.strip()
    except subprocess.TimeoutExpired:
        return 1, f'❌ TIMEOUT: el proceso tardó más de {timeout}s y fue terminado.'
    except Exception as e:
        return 1, f'❌ Error al ejecutar comando: {e}'

# ─── Parsers de resultado ──────────────────────────────────────────────────────

def parsear_export(salida: str) -> tuple[str, list[str], list[str]]:
    """Extrae la línea de resumen del export y cuenta errores."""
    resumen: str = ''
    for linea in salida.splitlines():
        if 'RESULTADO:' in linea:
            resumen = linea.strip()
    # Excluir la línea de resumen al buscar errores/warnings reales
    errores:  list[str] = [l.strip() for l in salida.splitlines() if '❌' in l and 'RESULTADO:' not in l]
    warnings: list[str] = [l.strip() for l in salida.splitlines() if '⚠️' in l and 'RESULTADO:' not in l]
    return resumen or '(sin resumen)', errores, warnings

def parsear_import(salida):
    """Extrae la línea de resumen del import."""
    for linea in reversed(salida.splitlines()):
        if 'tablas importadas' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

# ─── Notificaciones ────────────────────────────────────────────────────────────

def enviar_email(env, asunto, cuerpo):
    usuario  = env.get('GMAIL_USER', '')
    password = env.get('GMAIL_APP_PASSWORD', '')
    destino  = env.get('EMAIL_DESTINO', 'larevo1111@gmail.com')

    if not usuario or not password:
        log.warning('📧 Email no configurado en .env — omitiendo.')
        return

    try:
        msg            = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = f'Effi Pipeline <{usuario}>'
        msg['To']      = destino
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(usuario, password)
            smtp.sendmail(usuario, destino, msg.as_string())
        log.info(f'📧 Email enviado → {destino}')
    except Exception as e:
        log.error(f'Error enviando email: {e}')


def enviar_telegram(env, mensaje):
    token   = env.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = env.get('TELEGRAM_CHAT_ID', '')

    if not token or not chat_id:
        log.warning('📱 Telegram no configurado en .env — omitiendo.')
        return

    try:
        url  = f'https://api.telegram.org/bot{token}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id':    chat_id,
            'text':       mensaje,
            'parse_mode': 'HTML',
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.info('📱 Telegram enviado.')
            else:
                log.warning(f'Telegram error status: {resp.status}')
    except Exception as e:
        log.error(f'Error enviando Telegram: {e}')

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    forzar = '--forzar' in sys.argv
    env    = cargar_env()
    ahora  = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    operable, motivo = es_horario_operativo()
    if not operable and not forzar:
        log.info(f'⏸  Omitido: {motivo}')
        return
    if not operable and forzar:
        log.info(f'⚡ Ejecución forzada (fuera de horario: {motivo})')

    log.info('=' * 60)
    log.info(f'🚀 PIPELINE INICIO — {ahora}')
    log.info('=' * 60)

    # ── 1. EXPORT ───────────────────────────────────────────────
    log.info('▶ export_all.sh ...')
    t0 = datetime.datetime.now()
    exit_exp, salida_exp = ejecutar(['bash', str(EXPORT_SCRIPT)], EXPORT_TIMEOUT)
    dur_exp = int((datetime.datetime.now() - t0).total_seconds())
    resumen_exp, errores_exp, warnings_exp = parsear_export(salida_exp)
    log.info(f'   {resumen_exp}  [{dur_exp}s]')

    # ── 2. IMPORT ───────────────────────────────────────────────
    log.info('▶ import_all.js ...')
    t1 = datetime.datetime.now()
    exit_imp, salida_imp = ejecutar(['node', str(IMPORT_SCRIPT)], IMPORT_TIMEOUT)
    dur_imp = int((datetime.datetime.now() - t1).total_seconds())
    resumen_imp = parsear_import(salida_imp)
    log.info(f'   {resumen_imp}  [{dur_imp}s]')

    # ── 3. Estado global ─────────────────────────────────────────
    hay_error = (exit_exp != 0 or exit_imp != 0 or len(errores_exp) > 0)
    estado    = '❌ CON ERRORES' if hay_error else '✅ EXITOSO'
    dur_total = dur_exp + dur_imp
    log.info(f'🏁 FIN — {estado}  [total {dur_total}s]')
    log.info('=' * 60)

    # ── 4. Email (siempre) ───────────────────────────────────────
    icono  = '❌' if hay_error else '✅'
    asunto = f'{icono} [Effi Pipeline] {estado} — {ahora}'

    cuerpo = f"""Pipeline Effi → MariaDB
{'=' * 50}
Fecha:    {ahora}
Estado:   {estado}
Duración: {dur_total}s  (export {dur_exp}s + import {dur_imp}s)

── EXPORT ──────────────────────────────────────────
{resumen_exp}
{'Warnings: ' + str(len(warnings_exp)) if warnings_exp else ''}
{chr(10).join(warnings_exp) if warnings_exp else ''}

{salida_exp}

── IMPORT ──────────────────────────────────────────
{resumen_imp}

{salida_imp}
"""
    enviar_email(env, asunto, cuerpo)

    # ── 5. Telegram (solo en error) ──────────────────────────────
    if hay_error:
        partes = [f'<b>⚠️ Pipeline Effi — ERROR</b>', f'📅 {ahora}']

        # Scripts que fallaron definitivamente (líneas "Falló definitivamente: export_X")
        fallidos = [l for l in errores_exp if 'Falló definitivamente' in l]
        if fallidos:
            partes.append('\n<b>Scripts fallidos:</b>')
            for f in fallidos:
                nombre = f.split(':', 1)[-1].strip()
                partes.append(f'  • {nombre}')

        # Import
        if exit_imp != 0:
            partes.append(f'\n❌ Import: {resumen_imp}')
        else:
            partes.append(f'\n✅ Import: {resumen_imp}')

        enviar_telegram(env, '\n'.join(partes))


if __name__ == '__main__':
    main()
