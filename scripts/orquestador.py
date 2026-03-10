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
EXPORT_SCRIPT   = SCRIPTS_DIR / 'export_all.sh'
IMPORT_SCRIPT   = SCRIPTS_DIR / 'import_all.js'
RESUMEN_SCRIPT       = SCRIPTS_DIR / 'calcular_resumen_ventas.py'
RESUMEN_CANAL_SCRIPT    = SCRIPTS_DIR / 'calcular_resumen_ventas_canal.py'
RESUMEN_CLIENTE_SCRIPT  = SCRIPTS_DIR / 'calcular_resumen_ventas_cliente.py'
RESUMEN_PRODUCTO_SCRIPT    = SCRIPTS_DIR / 'calcular_resumen_ventas_producto.py'
RESUMEN_REMISIONES_SCRIPT         = SCRIPTS_DIR / 'calcular_resumen_ventas_remisiones_mes.py'
RESUMEN_REM_CANAL_SCRIPT          = SCRIPTS_DIR / 'calcular_resumen_ventas_remisiones_canal_mes.py'
RESUMEN_REM_CLIENTE_SCRIPT        = SCRIPTS_DIR / 'calcular_resumen_ventas_remisiones_cliente_mes.py'
RESUMEN_REM_PRODUCTO_SCRIPT       = SCRIPTS_DIR / 'calcular_resumen_ventas_remisiones_producto_mes.py'
SYNC_HOSTINGER_SCRIPT             = SCRIPTS_DIR / 'sync_hostinger.py'
SYNC_ESPOCRM_MARKETING_SCRIPT     = SCRIPTS_DIR / 'sync_espocrm_marketing.py'

EXPORT_TIMEOUT   = 30 * 60   # 30 minutos
IMPORT_TIMEOUT   =  5 * 60   # 5 minutos
RESUMEN_TIMEOUT  =  2 * 60   # 2 minutos
SYNC_TIMEOUT     =  5 * 60   # 5 minutos (sync Hostinger ~100s)
SYNC_ESPO_TIMEOUT =  2 * 60  # 2 minutos (sync EspoCRM marketing)

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

def parsear_resumen(salida):
    """Extrae la línea de resumen de calcular_resumen_ventas."""
    for linea in reversed(salida.splitlines()):
        if 'meses actualizados' in linea or 'resumen_ventas' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

def parsear_resumen_canal(salida):
    """Extrae la línea de resumen de calcular_resumen_ventas_canal."""
    for linea in reversed(salida.splitlines()):
        if 'filas actualizadas' in linea or 'canal_mes' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

def parsear_resumen_cliente(salida):
    """Extrae la línea de resumen de calcular_resumen_ventas_cliente."""
    for linea in reversed(salida.splitlines()):
        if 'filas actualizadas' in linea or 'cliente_mes' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

def parsear_resumen_producto(salida):
    """Extrae la línea de resumen de calcular_resumen_ventas_producto."""
    for linea in reversed(salida.splitlines()):
        if 'filas actualizadas' in linea or 'producto_mes' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

def parsear_resumen_remisiones(salida):
    """Extrae la línea de resumen de calcular_resumen_ventas_remisiones_mes."""
    for linea in reversed(salida.splitlines()):
        if 'meses actualizados' in linea or 'remisiones_mes' in linea:
            return linea.strip()
    return salida.splitlines()[-1].strip() if salida else '(sin salida)'

def parsear_sync_hostinger(salida):
    """Extrae la línea de resumen de sync_hostinger."""
    for linea in reversed(salida.splitlines()):
        if 'tablas OK' in linea or 'sync_hostinger' in linea:
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

    # ── 3. RESUMEN MES ──────────────────────────────────────────
    log.info('▶ calcular_resumen_ventas.py ...')
    t2 = datetime.datetime.now()
    exit_rsm, salida_rsm = ejecutar(['python3', str(RESUMEN_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rsm = int((datetime.datetime.now() - t2).total_seconds())
    resumen_rsm = parsear_resumen(salida_rsm)
    log.info(f'   {resumen_rsm}  [{dur_rsm}s]')

    # ── 3b. RESUMEN CANAL ────────────────────────────────────────
    log.info('▶ calcular_resumen_ventas_canal.py ...')
    t3 = datetime.datetime.now()
    exit_rsm_canal, salida_rsm_canal = ejecutar(['python3', str(RESUMEN_CANAL_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rsm_canal = int((datetime.datetime.now() - t3).total_seconds())
    resumen_rsm_canal = parsear_resumen_canal(salida_rsm_canal)
    log.info(f'   {resumen_rsm_canal}  [{dur_rsm_canal}s]')

    # ── 3c. RESUMEN CLIENTE ──────────────────────────────────────
    log.info('▶ calcular_resumen_ventas_cliente.py ...')
    t4 = datetime.datetime.now()
    exit_rsm_cliente, salida_rsm_cliente = ejecutar(['python3', str(RESUMEN_CLIENTE_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rsm_cliente = int((datetime.datetime.now() - t4).total_seconds())
    resumen_rsm_cliente = parsear_resumen_cliente(salida_rsm_cliente)
    log.info(f'   {resumen_rsm_cliente}  [{dur_rsm_cliente}s]')

    # ── 3d. RESUMEN PRODUCTO ─────────────────────────────────────
    log.info('▶ calcular_resumen_ventas_producto.py ...')
    t5 = datetime.datetime.now()
    exit_rsm_producto, salida_rsm_producto = ejecutar(['python3', str(RESUMEN_PRODUCTO_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rsm_producto = int((datetime.datetime.now() - t5).total_seconds())
    resumen_rsm_producto = parsear_resumen_producto(salida_rsm_producto)
    log.info(f'   {resumen_rsm_producto}  [{dur_rsm_producto}s]')

    # ── 4a. RESUMEN REMISIONES MES ───────────────────────────────
    log.info('▶ calcular_resumen_ventas_remisiones_mes.py ...')
    t6 = datetime.datetime.now()
    exit_rsm_rem, salida_rsm_rem = ejecutar(['python3', str(RESUMEN_REMISIONES_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rsm_rem = int((datetime.datetime.now() - t6).total_seconds())
    resumen_rsm_rem = parsear_resumen_remisiones(salida_rsm_rem)
    log.info(f'   {resumen_rsm_rem}  [{dur_rsm_rem}s]')

    # ── 4b. RESUMEN REMISIONES CANAL ─────────────────────────────
    log.info('▶ calcular_resumen_ventas_remisiones_canal_mes.py ...')
    t_rem_canal = datetime.datetime.now()
    exit_rem_canal, salida_rem_canal = ejecutar(['python3', str(RESUMEN_REM_CANAL_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rem_canal = int((datetime.datetime.now() - t_rem_canal).total_seconds())
    log.info(f'   {salida_rem_canal.strip().splitlines()[-1] if salida_rem_canal.strip() else "sin salida"}  [{dur_rem_canal}s]')

    # ── 4c. RESUMEN REMISIONES CLIENTE ───────────────────────────
    log.info('▶ calcular_resumen_ventas_remisiones_cliente_mes.py ...')
    t_rem_cli = datetime.datetime.now()
    exit_rem_cli, salida_rem_cli = ejecutar(['python3', str(RESUMEN_REM_CLIENTE_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rem_cli = int((datetime.datetime.now() - t_rem_cli).total_seconds())
    log.info(f'   {salida_rem_cli.strip().splitlines()[-1] if salida_rem_cli.strip() else "sin salida"}  [{dur_rem_cli}s]')

    # ── 4d. RESUMEN REMISIONES PRODUCTO ──────────────────────────
    log.info('▶ calcular_resumen_ventas_remisiones_producto_mes.py ...')
    t_rem_prod = datetime.datetime.now()
    exit_rem_prod, salida_rem_prod = ejecutar(['python3', str(RESUMEN_REM_PRODUCTO_SCRIPT)], RESUMEN_TIMEOUT)
    dur_rem_prod = int((datetime.datetime.now() - t_rem_prod).total_seconds())
    log.info(f'   {salida_rem_prod.strip().splitlines()[-1] if salida_rem_prod.strip() else "sin salida"}  [{dur_rem_prod}s]')

    # ── 5. SYNC HOSTINGER ────────────────────────────────────────
    log.info('▶ sync_hostinger.py ...')
    t7 = datetime.datetime.now()
    exit_sync, salida_sync = ejecutar(['python3', str(SYNC_HOSTINGER_SCRIPT)], SYNC_TIMEOUT)
    dur_sync = int((datetime.datetime.now() - t7).total_seconds())
    resumen_sync = parsear_sync_hostinger(salida_sync)
    log.info(f'   {resumen_sync}  [{dur_sync}s]')

    # ── 6b. SYNC ESPOCRM MARKETING ───────────────────────────────
    log.info('▶ sync_espocrm_marketing.py ...')
    t_espo = datetime.datetime.now()
    exit_espo, salida_espo = ejecutar(['python3', str(SYNC_ESPOCRM_MARKETING_SCRIPT)], SYNC_ESPO_TIMEOUT)
    dur_espo = int((datetime.datetime.now() - t_espo).total_seconds())
    resumen_espo = salida_espo.strip().splitlines()[-1] if salida_espo.strip() else 'sin salida'
    log.info(f'   {resumen_espo}  [{dur_espo}s]')

    # ── 6. Estado global ─────────────────────────────────────────
    hay_error = (exit_exp != 0 or exit_imp != 0 or exit_rsm != 0 or exit_rsm_canal != 0
                 or exit_rsm_cliente != 0 or exit_rsm_producto != 0 or exit_rsm_rem != 0
                 or exit_rem_canal != 0 or exit_rem_cli != 0 or exit_rem_prod != 0
                 or exit_sync != 0 or exit_espo != 0 or len(errores_exp) > 0)
    estado    = '❌ CON ERRORES' if hay_error else '✅ EXITOSO'
    dur_total = dur_exp + dur_imp + dur_rsm + dur_rsm_canal + dur_rsm_cliente + dur_rsm_producto + dur_rsm_rem + dur_rem_canal + dur_rem_cli + dur_rem_prod + dur_sync + dur_espo
    log.info(f'🏁 FIN — {estado}  [total {dur_total}s]')
    log.info('=' * 60)

    # ── 5. Email (siempre) ───────────────────────────────────────
    icono  = '❌' if hay_error else '✅'
    asunto = f'{icono} [Effi Pipeline] {estado} — {ahora}'

    cuerpo = f"""Pipeline Effi → MariaDB
{'=' * 50}
Fecha:    {ahora}
Estado:   {estado}
Duración: {dur_total}s  (export {dur_exp}s + import {dur_imp}s + resumen {dur_rsm}s + canal {dur_rsm_canal}s + cliente {dur_rsm_cliente}s + producto {dur_rsm_producto}s + remisiones {dur_rsm_rem}s + sync {dur_sync}s)

── EXPORT ──────────────────────────────────────────
{resumen_exp}
{'Warnings: ' + str(len(warnings_exp)) if warnings_exp else ''}
{chr(10).join(warnings_exp) if warnings_exp else ''}

{salida_exp}

── IMPORT ──────────────────────────────────────────
{resumen_imp}

{salida_imp}

── RESUMEN VENTAS MES ──────────────────────────────
{resumen_rsm}

── RESUMEN VENTAS CANAL ────────────────────────────
{resumen_rsm_canal}

── RESUMEN VENTAS CLIENTE ──────────────────────────
{resumen_rsm_cliente}

── RESUMEN VENTAS PRODUCTO ─────────────────────────
{resumen_rsm_producto}

── RESUMEN REMISIONES MES ──────────────────────────
{resumen_rsm_rem}

── SYNC HOSTINGER ──────────────────────────────────
{resumen_sync}

── SYNC ESPOCRM MARKETING ─────────────────────────
{resumen_espo}
"""
    enviar_email(env, asunto, cuerpo)

    # ── 6. Telegram (solo en error) ──────────────────────────────
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

        # Resumen
        if exit_rsm != 0:
            partes.append(f'\n❌ Resumen: {resumen_rsm}')

        enviar_telegram(env, '\n'.join(partes))


if __name__ == '__main__':
    main()
