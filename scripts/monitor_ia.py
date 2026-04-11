#!/usr/bin/env python3
"""
monitor_ia.py — Monitor ligero del sistema IA (cada 2 horas).

Chequea los componentes críticos del stack IA y toma acciones correctivas
automáticas cuando es posible. Notifica al bot de Telegram.

Uso:
  python3 monitor_ia.py              # Siempre notifica
  python3 monitor_ia.py --silencioso # Solo si hay algo que reportar
"""
import os
import sys
import json
import subprocess
import time
import argparse
import pymysql
import pymysql.cursors
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

BOT_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
NOTIF_TOKEN = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN')
SANTI_CHAT  = os.getenv('TELEGRAM_NOTIF_CHAT_ID')
REPO_DIR    = '/home/osserver/Proyectos_Antigravity/Integraciones_OS'
LOG_FILE    = os.path.join(REPO_DIR, 'logs', 'monitor_ia.log')
OC_BIN      = '/home/osserver/.nvm/versions/node/v22.17.0/bin/opencode'

# Servicios críticos del stack IA
SERVICIOS_CRITICOS = [
    'ia-service', 'os-telegram-bot', 'ollama', 'os-ialocal',
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok(txt):   return f'✅ {txt}'
def _fail(txt): return f'❌ {txt}'
def _warn(txt): return f'⚠️ {txt}'
def _fix(txt):  return f'🔧 {txt}'

def _run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return -1, '', str(e)

def _log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts}  {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def _db():
    return pymysql.connect(
        host='localhost', port=3306,
        user='osadmin', password='Epist2487.',
        database='ia_service_os',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
    )

def _get_config(clave):
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute("SELECT valor FROM ia_config WHERE clave=%s", (clave,))
            row = cur.fetchone()
        conn.close()
        return row['valor'] if row else None
    except Exception:
        return None

def _set_config(clave, valor):
    try:
        conn = _db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ia_config (clave, valor) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE valor=%s",
                (clave, valor, valor)
            )
        conn.close()
        return True
    except Exception:
        return False

def _enviar_telegram(mensaje):
    try:
        import requests
        token = BOT_TOKEN or NOTIF_TOKEN
        if not token or not SANTI_CHAT:
            _log('Sin tokens Telegram')
            return
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': SANTI_CHAT, 'text': mensaje, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        _log(f'Error Telegram: {e}')


# ── Checks ───────────────────────────────────────────────────────────────────

def check_servicios():
    """Verifica servicios críticos. Reinicia los caídos."""
    lineas = []
    acciones = []
    fallos = 0

    for svc in SERVICIOS_CRITICOS:
        _, out, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
        if out == 'active':
            lineas.append(_ok(svc))
            continue

        _log(f'Reiniciando {svc}...')
        _run(['sudo', 'systemctl', 'restart', f'{svc}.service'], timeout=20)
        time.sleep(3)
        _, out2, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
        if out2 == 'active':
            lineas.append(_warn(f'{svc} caído → reiniciado'))
            acciones.append(_fix(f'{svc}: caído → reiniciado automáticamente'))
        else:
            lineas.append(_fail(f'{svc}: no arrancó'))
            fallos += 1

    return lineas, fallos, acciones


def check_ia_service():
    """Verifica health del IA Service."""
    try:
        import requests
        r = requests.get('http://localhost:5100/ia/health', timeout=5)
        if r.status_code == 200:
            return [_ok('IA Service (5100)')], 0, []
        return [_fail(f'IA Service HTTP {r.status_code}')], 1, []
    except Exception:
        return [_fail('IA Service no responde')], 1, []


def check_opencode():
    """
    Verifica OpenCode con el modelo activo.
    Si falla, prueba fallbacks y actualiza ia_config automáticamente.
    """
    modelo_actual = _get_config('sa_opencode_modelo') or 'opencode/minimax-m2.5-free'
    fallbacks_str = _get_config('sa_opencode_fallbacks') or ''
    fallbacks = [f.strip() for f in fallbacks_str.split(',') if f.strip()]

    # Probar modelo actual
    rc, out, err = _run(
        [OC_BIN, 'run', '--format', 'json', '-m', modelo_actual, 'responde OK'],
        timeout=35,
    )
    nombre_corto = modelo_actual.split('/')[-1]
    if rc == 0 and 'text' in out:
        return [_ok(f'OpenCode ({nombre_corto})')], 0, []

    _log(f'OpenCode {modelo_actual} falló: {(err or out)[:120]}')

    # Probar fallbacks en orden
    modelos_probar = [m for m in fallbacks if m != modelo_actual]
    for fallback in modelos_probar:
        rc2, out2, err2 = _run(
            [OC_BIN, 'run', '--format', 'json', '-m', fallback, 'responde OK'],
            timeout=35,
        )
        if rc2 == 0 and 'text' in out2:
            _set_config('sa_opencode_modelo', fallback)
            _log(f'OpenCode: modelo cambiado {modelo_actual} → {fallback}')
            fb_corto = fallback.split('/')[-1]
            accion = _fix(f'OpenCode: {nombre_corto} falló → cambiado a <b>{fb_corto}</b>')
            return [_warn(f'OpenCode: {nombre_corto} → {fb_corto} (auto)')], 0, [accion]

    # Todos fallaron
    return [_fail(f'OpenCode: todos los modelos fallaron ({nombre_corto})')], 1, []


def check_gpu():
    """Verifica GPU (VRAM libre)."""
    rc, out, _ = _run(
        ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
    )
    if rc == 0 and out:
        parts = [p.strip() for p in out.split(',')]
        usado, total = parts[0], parts[1]
        pct = int(usado) * 100 // int(total) if int(total) > 0 else 0
        if pct >= 95:
            return [_warn(f'GPU VRAM {pct}% — {usado}/{total} MB')], 0, []
        return [_ok(f'GPU {usado}/{total} MB')], 0, []
    return [_warn('GPU: no disponible o nvidia-smi sin respuesta')], 0, []


def check_bot_errores():
    """
    Verifica el bot. Los 409 Conflict son normales en python-telegram-bot v20
    (connection pooling httpx) y se auto-resuelven en <15s. Solo alarma si hay
    un bloqueo sostenido: 3+ conflictos seguidos sin OK en el medio.
    """
    log_path = os.path.join(REPO_DIR, 'logs', 'telegram_bot.log')
    if not os.path.exists(log_path):
        return [_warn('Bot: sin log')], 0, []

    try:
        lines = []
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 20000))  # últimos 20KB
            lines = f.read().decode('utf-8', errors='ignore').splitlines()

        # Buscar rachas de 409s consecutivos sin OK en el medio (indica bloqueo real)
        max_racha = 0
        racha = 0
        for line in lines[-200:]:
            if '409 Conflict' in line:
                racha += 1
                max_racha = max(max_racha, racha)
            elif '200 OK' in line and 'getUpdates' in line:
                racha = 0

        if max_racha >= 10:
            return [_warn(f'Bot: racha de {max_racha} conflictos — posible bloqueo')], 0, []
    except Exception:
        pass

    return [_ok('Bot operativo')], 0, []


def check_consumo_ia():
    """Verifica consumo IA del día (alerta si > 80% del límite)."""
    try:
        import requests
        r = requests.get('http://localhost:5100/ia/consumo', timeout=5)
        if r.status_code == 200:
            data = r.json()
            costo = data.get('hoy', {}).get('costo_usd', 0)
            limite = data.get('limite_dia_usd', 5)
            if limite and limite > 0:
                pct = costo / limite * 100
                if pct >= 90:
                    return [_warn(f'Consumo IA: ${costo:.3f}/${limite} ({pct:.0f}%)')], 0, []
            return [_ok(f'Consumo IA: ${costo:.3f} hoy')], 0, []
    except Exception:
        pass
    return [_warn('Consumo IA: no disponible')], 0, []


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--silencioso', action='store_true',
                        help='Solo notificar si hay algo que reportar')
    args = parser.parse_args()

    ahora = datetime.now().strftime('%H:%M')
    _log(f'=== Monitor IA {ahora} ===')

    checks = [
        ('SERVICIOS',  check_servicios),
        ('IA SERVICE', check_ia_service),
        ('OPENCODE',   check_opencode),
        ('GPU',        check_gpu),
        ('BOT',        check_bot_errores),
        ('CONSUMO',    check_consumo_ia),
    ]

    todas_lineas = []
    todas_acciones = []
    total_fallos = 0

    for titulo, fn in checks:
        try:
            lineas, fallos, acciones = fn()
        except Exception as e:
            lineas = [_fail(f'{titulo}: {str(e)[:80]}')]
            fallos = 1
            acciones = []

        todas_lineas.extend(lineas)
        todas_acciones.extend(acciones)
        total_fallos += fallos

        for l in lineas:
            _log(l)

    _log(f'Fallos: {total_fallos} | Auto-correcciones: {len(todas_acciones)}')

    # Decidir si hay algo que notificar
    hay_novedad = total_fallos > 0 or len(todas_acciones) > 0

    if args.silencioso and not hay_novedad:
        return 0

    # Construir mensaje
    fecha_hora = datetime.now().strftime('%d/%m %H:%M')

    if total_fallos == 0 and not todas_acciones:
        encabezado = f'🟢 <b>Monitor IA — {fecha_hora}</b>\nTodo operativo'
    elif total_fallos == 0:
        encabezado = f'🔧 <b>Monitor IA — {fecha_hora}</b>\nAuto-correcciones aplicadas'
    else:
        encabezado = f'🔴 <b>Monitor IA — {fecha_hora}</b>\n{total_fallos} fallo(s) sin resolver'

    partes = [encabezado, '']

    # Items con problema o corrección
    for linea in todas_lineas:
        if linea.startswith('❌') or linea.startswith('⚠️'):
            partes.append(linea)

    if todas_acciones:
        partes.append('')
        partes.append('<b>Acciones automáticas:</b>')
        partes.extend(todas_acciones)

    if total_fallos > 0:
        partes.append('')
        partes.append('💬 Responde a este mensaje para que Claude investigue.')

    mensaje = '\n'.join(partes)
    if len(mensaje) > 4000:
        mensaje = mensaje[:3990] + '\n...'

    _enviar_telegram(mensaje)
    return total_fallos


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
