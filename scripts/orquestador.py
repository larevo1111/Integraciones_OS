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
SYNC_CATALOGO_SCRIPT              = SCRIPTS_DIR / 'sync_catalogo_articulos.py'
SYNC_HOSTINGER_SCRIPT             = SCRIPTS_DIR / 'sync_hostinger.py'
SYNC_ESPOCRM_MARKETING_SCRIPT     = SCRIPTS_DIR / 'sync_espocrm_marketing.py'
SYNC_ESPOCRM_CONTACTOS_SCRIPT     = SCRIPTS_DIR / 'sync_espocrm_contactos.py'
SYNC_ESPOCRM_HOSTINGER_SCRIPT     = SCRIPTS_DIR / 'sync_espocrm_to_hostinger.py'
GENERAR_PLANTILLA_SCRIPT          = SCRIPTS_DIR / 'generar_plantilla_import_effi.py'
IMPORT_EFFI_SCRIPT                = SCRIPTS_DIR / 'import_clientes_effi.js'

EXPORT_TIMEOUT        = 30 * 60   # 30 minutos
IMPORT_TIMEOUT        =  5 * 60   # 5 minutos
RESUMEN_TIMEOUT       =  2 * 60   # 2 minutos
SYNC_TIMEOUT          =  8 * 60   # 8 minutos (sync Hostinger ~300s con trazabilidad 64K filas)
SYNC_ESPO_TIMEOUT     =  2 * 60   # 2 minutos (sync EspoCRM marketing)
SYNC_ESPO_CON_TIMEOUT =  3 * 60   # 3 minutos (sync EspoCRM contactos)
SYNC_ESPO_HOST_TIMEOUT = 2 * 60   # 2 minutos (sync EspoCRM → Hostinger)
GENERAR_PLANTILLA_TIMEOUT = 1 * 60  # 1 minuto
IMPORT_EFFI_TIMEOUT       = 3 * 60  # 3 minutos (Playwright upload)

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
    """Extrae resumen + errores de sync_hostinger."""
    lineas = salida.splitlines()
    resumen = '(sin salida)'
    errores_sync = []
    for linea in lineas:
        stripped = linea.strip()
        if '❌' in stripped and ':' in stripped and 'tablas OK' not in stripped:
            errores_sync.append(stripped)
        if 'tablas OK' in stripped or 'sync_hostinger' in stripped:
            resumen = stripped
    if errores_sync:
        return resumen + '\n' + '\n'.join(errores_sync)
    return resumen

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

    # ── 4e. SYNC CATÁLOGO ARTÍCULOS (nuevos productos) ───────────
    log.info('▶ sync_catalogo_articulos.py ...')
    t_cat = datetime.datetime.now()
    exit_cat, salida_cat = ejecutar(['python3', str(SYNC_CATALOGO_SCRIPT)], 60)
    dur_cat = int((datetime.datetime.now() - t_cat).total_seconds())
    log.info(f'   {salida_cat.strip().splitlines()[-1] if salida_cat.strip() else "sin salida"}  [{dur_cat}s]')

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

    # ── 6c. SYNC ESPOCRM CONTACTOS ───────────────────────────────
    log.info('▶ sync_espocrm_contactos.py ...')
    t_espo_con = datetime.datetime.now()
    exit_espo_con, salida_espo_con = ejecutar(['python3', str(SYNC_ESPOCRM_CONTACTOS_SCRIPT)], SYNC_ESPO_CON_TIMEOUT)
    dur_espo_con = int((datetime.datetime.now() - t_espo_con).total_seconds())
    resumen_espo_con = salida_espo_con.strip().splitlines()[-1] if salida_espo_con.strip() else 'sin salida'
    log.info(f'   {resumen_espo_con}  [{dur_espo_con}s]')

    # ── 6d. SYNC ESPOCRM → HOSTINGER ─────────────────────────────
    log.info('▶ sync_espocrm_to_hostinger.py ...')
    t_espo_host = datetime.datetime.now()
    exit_espo_host, salida_espo_host = ejecutar(['python3', str(SYNC_ESPOCRM_HOSTINGER_SCRIPT)], SYNC_ESPO_HOST_TIMEOUT)
    dur_espo_host = int((datetime.datetime.now() - t_espo_host).total_seconds())
    resumen_espo_host = salida_espo_host.strip().splitlines()[-1] if salida_espo_host.strip() else 'sin salida'
    log.info(f'   {resumen_espo_host}  [{dur_espo_host}s]')

    # ── 7a. GENERAR PLANTILLA EFFI ────────────────────────────
    log.info('▶ generar_plantilla_import_effi.py ...')
    t_gen = datetime.datetime.now()
    exit_gen, salida_gen = ejecutar(['python3', str(GENERAR_PLANTILLA_SCRIPT)], GENERAR_PLANTILLA_TIMEOUT)
    dur_gen = int((datetime.datetime.now() - t_gen).total_seconds())
    resumen_gen = salida_gen.strip().splitlines()[-1] if salida_gen.strip() else 'sin salida'
    log.info(f'   {resumen_gen}  [{dur_gen}s]')

    # ── 7b. IMPORT A EFFI (solo si hay pendientes) ────────────
    hay_pendientes_effi = exit_gen == 0 and 'contactos →' in salida_gen
    exit_imp_effi    = 0
    salida_imp_effi  = '(omitido — sin contactos pendientes)'
    dur_imp_effi     = 0
    resumen_imp_effi = salida_imp_effi
    if hay_pendientes_effi:
        # Extraer ruta del XLSX de la salida del generador
        xlsx_path = None
        for linea in salida_gen.splitlines():
            if '/tmp/import_clientes_effi_' in linea and '.xlsx' in linea:
                partes = linea.split('→')
                if len(partes) >= 2:
                    xlsx_path = partes[-1].strip()
                    break
        log.info('▶ import_clientes_effi.js ...')
        t_imp_effi = datetime.datetime.now()
        cmd_imp_effi = ['node', str(IMPORT_EFFI_SCRIPT)]
        if xlsx_path is not None:
            cmd_imp_effi.append(xlsx_path)
        exit_imp_effi, salida_imp_effi = ejecutar(cmd_imp_effi, IMPORT_EFFI_TIMEOUT)
        dur_imp_effi = int((datetime.datetime.now() - t_imp_effi).total_seconds())
        resumen_imp_effi = salida_imp_effi.strip().splitlines()[-1] if salida_imp_effi.strip() else 'sin salida'
        log.info(f'   {resumen_imp_effi}  [{dur_imp_effi}s]')

    # ── 8. Estado global ─────────────────────────────────────────
    hay_error = (exit_exp != 0 or exit_imp != 0 or exit_rsm != 0 or exit_rsm_canal != 0
                 or exit_rsm_cliente != 0 or exit_rsm_producto != 0 or exit_rsm_rem != 0
                 or exit_rem_canal != 0 or exit_rem_cli != 0 or exit_rem_prod != 0
                 or exit_cat != 0
                 or exit_sync != 0 or exit_espo != 0 or exit_espo_con != 0
                 or exit_espo_host != 0 or exit_gen != 0 or exit_imp_effi != 0
                 or len(errores_exp) > 0)
    estado    = '❌ CON ERRORES' if hay_error else '✅ EXITOSO'
    dur_total = dur_exp + dur_imp + dur_rsm + dur_rsm_canal + dur_rsm_cliente + dur_rsm_producto + dur_rsm_rem + dur_rem_canal + dur_rem_cli + dur_rem_prod + dur_cat + dur_sync + dur_espo + dur_espo_con + dur_espo_host + dur_gen + dur_imp_effi
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

── SYNC ESPOCRM CONTACTOS ─────────────────────────
{resumen_espo_con}

── SYNC ESPOCRM → HOSTINGER ──────────────────────
{resumen_espo_host}

── GENERAR PLANTILLA EFFI (paso 7a) ───────────────
{resumen_gen}

── IMPORT A EFFI (paso 7b) ────────────────────────
{resumen_imp_effi}
"""
    enviar_email(env, asunto, cuerpo)

    # ── 6. Telegram (solo en error) ──────────────────────────────
    if hay_error:
        partes = [f'<b>⚠️ Pipeline Effi — ERROR</b>', f'📅 {ahora}']

        # Scripts de export que fallaron
        fallidos = [l for l in errores_exp if 'Falló definitivamente' in l]
        if fallidos:
            partes.append('\n<b>Export fallidos:</b>')
            for f in fallidos:
                nombre = f.split(':', 1)[-1].strip()
                partes.append(f'  • {nombre}')

        # Cada paso con su estado
        pasos = [
            ('Import', exit_imp, resumen_imp),
            ('Resumen facturas mes', exit_rsm, resumen_rsm),
            ('Resumen facturas canal', exit_rsm_canal, resumen_rsm_canal),
            ('Resumen facturas cliente', exit_rsm_cliente, resumen_rsm_cliente),
            ('Resumen facturas producto', exit_rsm_producto, resumen_rsm_producto),
            ('Resumen remisiones mes', exit_rsm_rem, resumen_rsm_rem),
            ('Sync Hostinger', exit_sync, resumen_sync),
            ('Sync EspoCRM marketing', exit_espo, resumen_espo),
            ('Sync EspoCRM contactos', exit_espo_con, resumen_espo_con),
            ('Sync EspoCRM → Hostinger', exit_espo_host, resumen_espo_host),
            ('Plantilla Effi', exit_gen, resumen_gen),
            ('Import a Effi', exit_imp_effi, resumen_imp_effi),
        ]
        for nombre, exit_code, resumen in pasos:
            icono_paso = '❌' if exit_code != 0 else '✅'
            # Solo mostrar los que fallaron + import (siempre útil)
            if exit_code != 0 or nombre == 'Import':
                partes.append(f'{icono_paso} {nombre}: {resumen}')

        enviar_telegram(env, '\n'.join(partes))


if __name__ == '__main__':
    main()
