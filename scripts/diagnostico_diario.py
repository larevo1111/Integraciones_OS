#!/usr/bin/env python3
"""
Diagnóstico diario del sistema OS.
Revisa servicios, BDs, apps, GPU, conectividad y pipeline.
Envía reporte por Telegram. Si hay fallos, intenta corregir y opcionalmente llama a Claude Code.

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

BOT_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')          # Bot principal (interactivo)
NOTIF_TOKEN = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN')    # Bot notificaciones (fallback)
SANTI_CHAT  = os.getenv('TELEGRAM_NOTIF_CHAT_ID')      # Chat de Santi
CLAUDE_BIN  = '/home/osserver/.local/bin/claude'
REPO_DIR    = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
LOG_FILE    = os.path.join(REPO_DIR, 'logs', 'diagnostico.log')
HOY         = date.today().isoformat()

# Servicios que DEBEN estar activos
SERVICIOS_REQUERIDOS = [
    'ia-service', 'ollama', 'os-telegram-bot', 'wa-bridge',
    'os-erp-frontend', 'os-ia-admin', 'os-gestion',
    'os-inventario-api', 'os-ialocal', 'effi-webhook',
]

# Apps web con su URL de health check
APPS_WEB = [
    ('ERP Frontend',    'http://localhost:9100'),
    ('IA Admin',        'http://localhost:9200'),
    ('Gestión',         'http://localhost:9300'),
    ('Inventario',      'http://localhost:9401'),
    ('IA Service',      'http://localhost:5100/ia/health'),
    ('IA Local',        'http://localhost:9500'),
]

# BDs locales
BDS_LOCALES = ['ia_service_os', 'effi_data', 'os_inventario', 'os_whatsapp', 'espocrm']

# Hostinger
HOSTINGER_CFG = dict(
    host='109.106.250.195', port=3306,
    user='u768061575_osserver', password='Epist2487.',
    database='u768061575_os_integracion',
    connect_timeout=10, read_timeout=10,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok(nombre):
    return f'✅ {nombre}'

def _fail(nombre, detalle=''):
    return f'❌ {nombre}' + (f' — {detalle}' if detalle else '')

def _warn(nombre, detalle=''):
    return f'⚠️ {nombre}' + (f' — {detalle}' if detalle else '')

def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return -1, '', str(e)


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


# ── Checks ───────────────────────────────────────────────────────────────────

def check_servicios():
    """Verifica servicios systemd requeridos. Reinicia los caídos."""
    resultados = []
    fallos = 0
    for svc in SERVICIOS_REQUERIDOS:
        rc, out, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
        if out == 'active':
            resultados.append(_ok(svc))
        else:
            # Intentar reiniciar
            _log(f'Reiniciando {svc}...')
            _run(['sudo', 'systemctl', 'restart', f'{svc}.service'], timeout=20)
            time.sleep(3)
            rc2, out2, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
            if out2 == 'active':
                resultados.append(_warn(svc, 'estaba caído → reiniciado'))
            else:
                resultados.append(_fail(svc, 'no arrancó'))
                fallos += 1
    return resultados, fallos


def check_bds_locales():
    """Verifica conexión a BDs locales."""
    import pymysql
    resultados = []
    fallos = 0
    for bd in BDS_LOCALES:
        try:
            conn = pymysql.connect(
                host='localhost', user='osadmin', password='Epist2487.',
                database=bd, connect_timeout=5,
            )
            conn.close()
            resultados.append(_ok(bd))
        except Exception as e:
            resultados.append(_fail(bd, str(e)[:60]))
            fallos += 1
    return resultados, fallos


def check_hostinger():
    """Verifica conexión a Hostinger."""
    import pymysql
    try:
        conn = pymysql.connect(**HOSTINGER_CFG)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM zeffi_facturas_venta_encabezados')
        n = cur.fetchone()[0]
        conn.close()
        return [_ok(f'Hostinger ({n} facturas)')], 0
    except Exception as e:
        err = str(e)[:80]
        # Verificar/activar WARP
        rc, warp_st, _ = _run(['warp-cli', '--accept-tos', 'status'])
        if 'Disconnected' in warp_st:
            _log('Hostinger inalcanzable — activando WARP...')
            _run(['warp-cli', '--accept-tos', 'connect'], timeout=10)
            time.sleep(5)
            # Reintentar
            try:
                conn = pymysql.connect(**HOSTINGER_CFG)
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) FROM zeffi_facturas_venta_encabezados')
                n = cur.fetchone()[0]
                conn.close()
                return [_warn(f'Hostinger ({n} fact) — WARP activado')], 0
            except Exception:
                pass
        return [_fail('Hostinger', err)], 1


def check_warp():
    """Estado de Cloudflare WARP."""
    rc, out, _ = _run(['warp-cli', '--accept-tos', 'status'])
    if 'Connected' in out:
        return [_ok('WARP conectado')], 0
    elif 'Disconnected' in out:
        return [_ok('WARP desconectado (no necesario)')], 0
    else:
        return [_warn('WARP', out[:60])], 0


def check_gpu_ollama():
    """Verifica GPU y modelo Ollama."""
    import requests
    resultados = []
    fallos = 0

    # GPU
    rc, out, _ = _run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'])
    if rc == 0 and out:
        parts = out.split(',')
        usado, total = parts[0].strip(), parts[1].strip()
        resultados.append(_ok(f'GPU {usado}/{total} MB'))
    else:
        resultados.append(_fail('GPU no disponible'))
        fallos += 1

    # Ollama
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

    return resultados, fallos


def check_apps_web():
    """Verifica que las apps web respondan."""
    import requests
    resultados = []
    fallos = 0
    for nombre, url in APPS_WEB:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                resultados.append(_ok(nombre))
            else:
                resultados.append(_fail(nombre, f'HTTP {r.status_code}'))
                fallos += 1
        except Exception:
            resultados.append(_fail(nombre, 'no responde'))
            fallos += 1
    return resultados, fallos


def check_pipeline():
    """Verifica último pipeline ejecutado."""
    log_path = os.path.join(REPO_DIR, 'logs', 'pipeline.log')
    if not os.path.exists(log_path):
        return [_fail('Pipeline', 'sin log')], 1

    # Buscar última línea FIN
    ultima_fin = ''
    with open(log_path, 'r') as f:
        for line in f:
            if '🏁 FIN' in line:
                ultima_fin = line.strip()

    if not ultima_fin:
        return [_warn('Pipeline', 'sin ejecución registrada')], 0

    if '❌' in ultima_fin:
        return [_warn(f'Pipeline: último con errores')], 0
    else:
        return [_ok('Pipeline: última ejecución OK')], 0


def check_bot_errores():
    """Verifica errores recientes del bot."""
    log_path = os.path.join(REPO_DIR, 'logs', 'telegram_bot.log')
    if not os.path.exists(log_path):
        return [_warn('Bot', 'sin log')], 0

    # Contar conflictos en última hora
    ahora = datetime.now()
    conflictos = 0
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if 'Conflict' in line and HOY in line:
                    conflictos += 1
    except Exception:
        pass

    if conflictos > 5:
        return [_warn(f'Bot: {conflictos} conflictos hoy')], 0
    return [_ok('Bot sin errores graves')], 0


def check_disco():
    """Verifica espacio en disco."""
    rc, out, _ = _run(['df', '-h', '/'])
    if rc == 0:
        lines = out.split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            uso = parts[4] if len(parts) > 4 else '?'
            uso_num = int(uso.replace('%', '')) if '%' in uso else 0
            if uso_num >= 90:
                return [_fail(f'Disco: {uso} usado')], 1
            elif uso_num >= 80:
                return [_warn(f'Disco: {uso} usado')], 0
            else:
                return [_ok(f'Disco: {uso} usado')], 0
    return [_warn('Disco: no se pudo verificar')], 0


# ── Claude Code ──────────────────────────────────────────────────────────────

def llamar_claude(fallos_texto):
    """Llama a Claude Code con un prompt de diagnóstico para que corrija fallos."""
    prompt = (
        f'RD - {HOY}\n\n'
        f'Diagnóstico diario automático detectó estos fallos:\n\n'
        f'{fallos_texto}\n\n'
        f'Revisa cada fallo, diagnostica la causa raíz y corrige lo que puedas. '
        f'Al terminar, envía un resumen breve de lo que hiciste por Telegram '
        f'usando la función notificar() de scripts/ia_service/alertas.py.'
    )

    env = os.environ.copy()
    env.pop('CLAUDECODE', None)
    env.pop('ANTHROPIC_API_KEY', None)

    _log(f'Llamando a Claude Code para corregir {fallos_texto[:100]}...')
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, '-p', prompt, '--output-format', 'json'],
            capture_output=True, text=True,
            cwd=REPO_DIR, timeout=600, env=env,
        )
        if proc.stdout.strip():
            data = json.loads(proc.stdout.strip().split('\n')[-1])
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
        ('SERVICIOS',   check_servicios),
        ('BD LOCALES',  check_bds_locales),
        ('HOSTINGER',   check_hostinger),
        ('WARP',        check_warp),
        ('GPU / OLLAMA', check_gpu_ollama),
        ('APPS WEB',    check_apps_web),
        ('PIPELINE',    check_pipeline),
        ('BOT',         check_bot_errores),
        ('DISCO',       check_disco),
    ]

    todas_lineas = []
    total_fallos = 0
    fallos_detalle = []

    for titulo, fn in checks:
        try:
            lineas, fallos = fn()
        except Exception as e:
            lineas = [_fail(titulo, str(e)[:80])]
            fallos = 1
        todas_lineas.append(f'\n<b>{titulo}</b>')
        todas_lineas.extend(lineas)
        total_fallos += fallos
        if fallos > 0:
            fallos_detalle.extend([l for l in lineas if l.startswith('❌')])

    # Construir reporte
    if total_fallos == 0:
        encabezado = f'🟢 <b>RD — {HOY}</b>\nTodo operativo'
    else:
        encabezado = f'🔴 <b>RD — {HOY}</b>\n{total_fallos} fallo(s) detectado(s)'

    reporte = encabezado + '\n' + '\n'.join(todas_lineas)

    # Log
    for l in todas_lineas:
        _log(l)
    _log(f'Total fallos: {total_fallos}')

    # Enviar por Telegram (bot principal para que Santi pueda responder)
    if not args.silencioso or total_fallos > 0:
        if len(reporte) > 4000:
            reporte = reporte[:3990] + '\n...(truncado)'
        _enviar_telegram(reporte, con_boton_claude=(total_fallos > 0))

    # Guardar reporte en archivo para que Claude Code lo lea si se invoca
    reporte_path = os.path.join(REPO_DIR, 'logs', 'ultimo_diagnostico.txt')
    with open(reporte_path, 'w') as f:
        f.write(reporte)

    return total_fallos


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
