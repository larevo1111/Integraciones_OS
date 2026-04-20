#!/usr/bin/env python3
"""
Diagnóstico diario del sistema OS.
Revisa servicios, BDs, apps, GPU, conectividad y pipeline.
Envía reporte por Telegram. Si hay fallos, opcionalmente llama a Claude Code.

Uso:
  python3 diagnostico_diario.py              # Diagnóstico completo + reporte
  python3 diagnostico_diario.py --silencioso # Solo si hay fallos
  python3 diagnostico_diario.py --con-claude # Si hay fallos, llama a Claude Code
"""
import os
import sys
import json
import subprocess
import time
import argparse
from datetime import datetime, date

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

from checks_sistema import (
    _ok, _fail, _warn, _run,
    check_servicios, check_opencode, check_bot_errores,
)

BOT_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
NOTIF_TOKEN = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN')
SANTI_CHAT  = os.getenv('TELEGRAM_NOTIF_CHAT_ID')
CLAUDE_BIN       = '/home/osserver/.local/bin/claude'
REPO_DIR         = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
RD_SESSION_FILE  = os.path.join(BASE_DIR, '.rd_session_id')  # persiste el ID de sesión RD
LOG_FILE    = os.path.join(REPO_DIR, 'logs', 'diagnostico.log')
BOT_LOG     = os.path.join(REPO_DIR, 'logs', 'telegram_bot.log')
HOY         = date.today().isoformat()

SERVICIOS_REQUERIDOS = [
    'ia-service', 'ollama', 'os-telegram-bot', 'wa-bridge',
    'os-erp-frontend', 'os-ia-admin', 'os-gestion',
    'os-inventario-api', 'os-ialocal', 'effi-webhook',
]

APPS_WEB = [
    ('ERP Frontend', 'http://localhost:9100'),
    ('IA Admin',     'http://localhost:9200'),
    ('Gestión',      'http://localhost:9300'),
    ('Inventario',   'http://localhost:9401'),
    ('IA Service',   'http://localhost:5100/ia/health'),
    ('IA Local',     'http://localhost:9500'),
]

BDS_LOCALES = ['ia_service_os', 'effi_data', 'os_inventario', 'os_whatsapp', 'espocrm']

sys.path.insert(0, BASE_DIR)
from lib import cfg_remota_ssh, cfg_remota_db

_ssh_i = cfg_remota_ssh('INTEGRACION')
_db_i  = cfg_remota_db('INTEGRACION')
HOSTINGER_CFG = dict(
    host=_ssh_i['host'], port=3306,
    user=_db_i['user'], password=_db_i['password'],
    database=_db_i['database'],
    connect_timeout=10, read_timeout=10,
)


# ── Helpers locales ───────────────────────────────────────────────────────────

def _enviar_gmail(asunto, cuerpo_texto):
    """Envía email por Gmail. Se usa cuando todo está OK (sin fallos)."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    usuario  = os.getenv('GMAIL_USER', '')
    password = os.getenv('GMAIL_APP_PASSWORD', '')
    destino  = os.getenv('EMAIL_DESTINO', 'larevo1111@gmail.com')
    if not usuario or not password:
        _log('⚠️  Gmail no configurado en .env — omitiendo email.')
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = f'OS Sistema <{usuario}>'
        msg['To']      = destino
        msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(usuario, password)
            smtp.sendmail(usuario, destino, msg.as_string())
        _log(f'📧 Email enviado → {destino}')
    except Exception as e:
        _log(f'Error enviando email: {e}')


def _enviar_telegram(mensaje, con_boton_claude=False):
    """Envía reporte por el bot principal (para que Santi pueda responder)."""
    import requests
    token = BOT_TOKEN or NOTIF_TOKEN
    chat = SANTI_CHAT
    if not token or not chat:
        print('⚠️  Sin tokens Telegram configurados')
        return
    payload = {'chat_id': chat, 'text': mensaje, 'parse_mode': 'HTML'}
    if con_boton_claude:
        payload['reply_markup'] = json.dumps({
            'inline_keyboard': [[
                {'text': '🔧 Abrir con Claude Code', 'callback_data': f'rd_claude:{HOY}'}
            ]]
        })
    try:
        requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                      json=payload, timeout=10)
    except Exception as e:
        print(f'Error enviando Telegram: {e}')


def _log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts}  {msg}'
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


# ── Checks exclusivos del diagnóstico diario ──────────────────────────────────

def check_bds_locales():
    """Verifica conexión a BDs locales. (lineas, fallos, acciones)"""
    import pymysql
    resultados, fallos = [], 0
    for bd in BDS_LOCALES:
        try:
            from lib import cfg_local
            conn = pymysql.connect(
                **cfg_local(), database=bd, connect_timeout=5,
            )
            conn.close()
            resultados.append(_ok(bd))
        except Exception as e:
            resultados.append(_fail(f'{bd} — {str(e)[:60]}'))
            fallos += 1
    return resultados, fallos, []


def check_hostinger():
    """Verifica conexión a Hostinger. (lineas, fallos, acciones)"""
    import pymysql
    try:
        conn = pymysql.connect(**HOSTINGER_CFG)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM zeffi_facturas_venta_encabezados')
        n = cur.fetchone()[0]
        conn.close()
        return [_ok(f'Hostinger ({n} facturas)')], 0, []
    except Exception as e:
        err = str(e)[:80]
        rc, warp_st, _ = _run(['warp-cli', '--accept-tos', 'status'])
        if 'Disconnected' in warp_st:
            _log('Hostinger inalcanzable — activando WARP...')
            _run(['warp-cli', '--accept-tos', 'connect'], timeout=10)
            time.sleep(5)
            try:
                conn = pymysql.connect(**HOSTINGER_CFG)
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) FROM zeffi_facturas_venta_encabezados')
                n = cur.fetchone()[0]
                conn.close()
                return [_warn(f'Hostinger ({n} fact) — WARP activado')], 0, []
            except Exception:
                pass
        return [_fail(f'Hostinger — {err}')], 1, []


def check_warp():
    """Estado de Cloudflare WARP. (lineas, fallos, acciones)"""
    rc, out, _ = _run(['warp-cli', '--accept-tos', 'status'])
    if 'Connected' in out:
        return [_ok('WARP conectado')], 0, []
    elif 'Disconnected' in out:
        return [_ok('WARP desconectado (no necesario)')], 0, []
    return [_warn(f'WARP — {out[:60]}')], 0, []


def check_gpu_ollama():
    """Verifica GPU VRAM y modelo Ollama cargado. (lineas, fallos, acciones)"""
    import requests
    resultados, fallos = [], 0

    rc, out, _ = _run(['nvidia-smi', '--query-gpu=memory.used,memory.total',
                        '--format=csv,noheader,nounits'])
    if rc == 0 and out:
        parts = out.split(',')
        usado, total = parts[0].strip(), parts[1].strip()
        resultados.append(_ok(f'GPU {usado}/{total} MB'))
    else:
        resultados.append(_fail('GPU no disponible'))
        fallos += 1

    try:
        r = requests.get('http://localhost:11434/api/ps', timeout=5)
        modelos = r.json().get('models', [])
        if modelos:
            nombres = ', '.join(m['name'].split(':')[0] for m in modelos)
            resultados.append(_ok(f'Ollama: {nombres}'))
        else:
            resultados.append(_ok('Ollama activo (sin modelo en VRAM)'))
    except Exception:
        resultados.append(_fail('Ollama no responde'))
        fallos += 1

    return resultados, fallos, []


def check_apps_web():
    """Verifica que las apps web respondan. (lineas, fallos, acciones)"""
    import requests
    resultados, fallos = [], 0
    for nombre, url in APPS_WEB:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                resultados.append(_ok(nombre))
            else:
                resultados.append(_fail(f'{nombre} — HTTP {r.status_code}'))
                fallos += 1
        except Exception:
            resultados.append(_fail(f'{nombre} — no responde'))
            fallos += 1
    return resultados, fallos, []


def check_claude_code():
    """Verifica que el binario de Claude Code existe y tiene versión válida."""
    rc, out, _ = _run([CLAUDE_BIN, '--version'], timeout=10)
    if rc == 0 and out.strip():
        return [_ok(f'Claude Code {out.strip()}')], 0, []
    return [_fail('Claude Code — binario no responde')], 1, []


def check_pipeline():
    """Verifica último pipeline ejecutado. (lineas, fallos, acciones)"""
    log_path = os.path.join(REPO_DIR, 'logs', 'pipeline.log')
    if not os.path.exists(log_path):
        return [_fail('Pipeline — sin log')], 1, []

    ultima_fin = ''
    with open(log_path, 'r') as f:
        for line in f:
            if '🏁 FIN' in line:
                ultima_fin = line.strip()

    if not ultima_fin:
        return [_warn('Pipeline — sin ejecución registrada')], 0, []
    if '❌' in ultima_fin:
        return [_warn('Pipeline — último con errores')], 0, []
    return [_ok('Pipeline: última ejecución OK')], 0, []


def check_disco():
    """Verifica espacio en disco. (lineas, fallos, acciones)"""
    rc, out, _ = _run(['df', '-h', '/'])
    if rc == 0:
        lines = out.split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            uso = parts[4] if len(parts) > 4 else '?'
            uso_num = int(uso.replace('%', '')) if '%' in uso else 0
            if uso_num >= 90:
                return [_fail(f'Disco: {uso} usado')], 1, []
            elif uso_num >= 80:
                return [_warn(f'Disco: {uso} usado')], 0, []
            else:
                return [_ok(f'Disco: {uso} usado')], 0, []
    return [_warn('Disco: no se pudo verificar')], 0, []


# ── Claude Code ──────────────────────────────────────────────────────────────

def llamar_claude(fallos_texto):
    """Llama a Claude Code con un prompt de diagnóstico para que corrija fallos."""
    prompt = (
        f'RD - {HOY}\n\n'
        f'Diagnóstico diario automático detectó estos fallos:\n\n'
        f'{fallos_texto}\n\n'
        f'REGLAS OBLIGATORIAS — léelas antes de tocar cualquier cosa:\n'
        f'1. Lee primero: .agent/CONTEXTO_ACTIVO.md y .agent/MANIFESTO.md para entender el sistema.\n'
        f'2. Lee SIEMPRE el archivo completo antes de modificarlo. Nunca editar sin leer.\n'
        f'3. Filosofía 5S: una función = una operación. No duplicar lógica. No parches superficiales.\n'
        f'4. Diagnostica la causa raíz — no el síntoma. Si no hay causa clara, solo documenta.\n'
        f'5. MODO AUTÓNOMO: SOLO puedes modificar datos en BD (ia_config, ia_ejemplos_sql, ia_tipos_consulta). '
        f'NUNCA modificar archivos .py, .js o de configuración sin sesión interactiva con Santi.\n'
        f'6. No meter try/except vacíos, no hardcodear valores, no workarounds.\n'
        f'7. Verifica con systemctl/curl que el servicio responde tras cualquier cambio.\n\n'
        f'Al terminar, notifica a Santi por Telegram usando:\n'
        f'  python3 {REPO_DIR}/scripts/ia_service/alertas.py\n'
        f'o bien con curl directo al bot con el resumen de lo que hiciste (máx 3 líneas).\n'
    )
    env = os.environ.copy()
    env.pop('CLAUDECODE', None)
    env.pop('ANTHROPIC_API_KEY', None)

    # Reusar siempre la misma sesión RD para no proliferar conversaciones
    session_id = None
    if os.path.exists(RD_SESSION_FILE):
        session_id = open(RD_SESSION_FILE).read().strip() or None

    cmd = [CLAUDE_BIN, '-p', prompt, '--output-format', 'json', '--model', 'sonnet']
    if session_id:
        cmd.extend(['--resume', session_id])
        _log(f'Retomando sesión RD {session_id[:8]}...')
    else:
        _log(f'Iniciando nueva sesión RD...')

    def _run_claude(cmd_args):
        return subprocess.run(
            cmd_args, capture_output=True, text=True,
            cwd=REPO_DIR, timeout=600, env=env,
        )

    def _es_error_contexto(proc):
        txt = (proc.stdout + proc.stderr).lower()
        return ('too long' in txt or 'context' in txt or
                'session' in txt or not proc.stdout.strip())

    try:
        proc = _run_claude(cmd)

        # Si --resume falla (sesión inválida o contexto lleno) → reintentar sin ella
        if session_id and _es_error_contexto(proc):
            _log('Sesión RD expirada o contexto lleno — iniciando sesión nueva...')
            if os.path.exists(RD_SESSION_FILE):
                os.remove(RD_SESSION_FILE)
            cmd_nuevo = [c for c in cmd if c not in ['--resume', session_id]]
            proc = _run_claude(cmd_nuevo)

        if proc.stdout.strip():
            data = json.loads(proc.stdout.strip().split('\n')[-1])
            new_sid = data.get('session_id')
            if new_sid:
                open(RD_SESSION_FILE, 'w').write(new_sid)
            return data.get('result', '')[:500]
    except Exception as e:
        _log(f'Error llamando Claude: {e}')
    return None


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--silencioso', action='store_true',
                        help='Solo reportar si hay fallos')
    parser.add_argument('--con-claude', action='store_true',
                        help='Llamar a Claude Code si hay fallos')
    args = parser.parse_args()

    _log(f'=== Diagnóstico diario {HOY} ===')

    checks = [
        ('SERVICIOS',    lambda: check_servicios(SERVICIOS_REQUERIDOS, _log)),
        ('BD LOCALES',   check_bds_locales),
        ('HOSTINGER',    check_hostinger),
        ('WARP',         check_warp),
        ('GPU / OLLAMA', check_gpu_ollama),
        ('APPS WEB',     check_apps_web),
        ('OPENCODE',     lambda: check_opencode(_log)),
        ('CLAUDE CODE',  check_claude_code),
        ('PIPELINE',     check_pipeline),
        ('BOT',          lambda: check_bot_errores(BOT_LOG, _log)),
        ('DISCO',        check_disco),
    ]

    todas_lineas, total_fallos, fallos_detalle = [], 0, []

    for titulo, fn in checks:
        try:
            lineas, fallos, _ = fn()
        except Exception as e:
            lineas = [_fail(f'{titulo} — {str(e)[:80]}')]
            fallos = 1
        todas_lineas.append(f'\n<b>{titulo}</b>')
        todas_lineas.extend(lineas)
        total_fallos += fallos
        if fallos > 0:
            fallos_detalle.extend([l for l in lineas if l.startswith('❌')])

    encabezado = (
        f'🟢 <b>RD — {HOY}</b>\nTodo operativo' if not total_fallos
        else f'🔴 <b>RD — {HOY}</b>\n{total_fallos} fallo(s) detectado(s)'
    )
    reporte = encabezado + '\n' + '\n'.join(todas_lineas)

    for l in todas_lineas:
        _log(l)
    _log(f'Total fallos: {total_fallos}')

    if total_fallos == 0:
        # Sin fallos → email silencioso a Gmail
        if not args.silencioso:
            cuerpo = reporte.replace('<b>', '').replace('</b>', '')
            _enviar_gmail(f'✅ RD {HOY} — Todo operativo', cuerpo)
    else:
        # Con fallos → Telegram para acción inmediata
        if len(reporte) > 4000:
            reporte = reporte[:3990] + '\n...(truncado)'
        _enviar_telegram(reporte, con_boton_claude=True)

    reporte_path = os.path.join(REPO_DIR, 'logs', 'ultimo_diagnostico.txt')
    with open(reporte_path, 'w') as f:
        f.write(reporte)

    if args.con_claude and total_fallos > 0 and fallos_detalle:
        _log(f'Invocando Claude Code para {total_fallos} fallo(s)...')
        respuesta_claude = llamar_claude('\n'.join(fallos_detalle))
        if respuesta_claude:
            _log(f'Claude respondió: {respuesta_claude[:200]}')
            _enviar_telegram(f'🤖 <b>Claude Code corrigió fallos:</b>\n{respuesta_claude[:600]}')

    return total_fallos


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
