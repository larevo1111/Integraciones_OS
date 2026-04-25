"""
checks_sistema.py — Funciones de chequeo compartidas.
Usadas por monitor_ia.py y diagnostico_diario.py.
Cada función retorna (lineas, fallos, acciones).
"""
import os
import subprocess
import time
import pymysql
import pymysql.cursors

OC_BIN = '/home/osserver/.nvm/versions/node/v22.17.0/bin/opencode'
BOT_LOG = '/home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/telegram_bot.log'


# ── Helpers base ─────────────────────────────────────────────────────────────

def _run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return -1, '', str(e)

def _ok(txt):   return f'✅ {txt}'
def _fail(txt): return f'❌ {txt}'
def _warn(txt): return f'⚠️ {txt}'
def _fix(txt):  return f'🔧 {txt}'


# ── BD ia_service_os ──────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local

def _db_ia():
    return pymysql.connect(
        **cfg_local(), database='ia_service_os', charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True, connect_timeout=5,
    )

def get_ia_config(clave):
    try:
        conn = _db_ia()
        with conn.cursor() as cur:
            cur.execute("SELECT valor FROM ia_config WHERE clave=%s", (clave,))
            row = cur.fetchone()
        conn.close()
        return row['valor'] if row else None
    except Exception:
        return None

def set_ia_config(clave, valor):
    try:
        conn = _db_ia()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ia_config (clave, valor) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE valor=%s",
                (clave, valor, valor),
            )
        conn.close()
        return True
    except Exception:
        return False


# ── Checks compartidos ────────────────────────────────────────────────────────

def check_servicios(lista, log_fn=print):
    """Chequea y reinicia servicios systemd. (lineas, fallos, acciones)"""
    lineas, acciones = [], []
    fallos = 0
    for svc in lista:
        _, out, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
        if out == 'active':
            lineas.append(_ok(svc))
            continue
        log_fn(f'Reiniciando {svc}...')
        _run(['sudo', 'systemctl', 'restart', f'{svc}.service'], timeout=20)
        time.sleep(3)
        _, out2, _ = _run(['systemctl', 'is-active', f'{svc}.service'])
        if out2 == 'active':
            lineas.append(_warn(f'{svc} caído → reiniciado'))
            acciones.append(_fix(f'{svc}: reiniciado automáticamente'))
        else:
            lineas.append(_fail(f'{svc}: no arrancó'))
            fallos += 1
    return lineas, fallos, acciones


def _oc_responde(modelo, timeout=90):
    """Prueba un modelo OpenCode con pregunta SQL real. Retorna True si da texto útil."""
    rc, out, _ = _run(
        [OC_BIN, 'run', '--format', 'json', '-m', modelo,
         'cuantas filas tiene zeffi_facturas_venta_encabezados? responde solo el número'],
        timeout=timeout,
    )
    if rc != 0 or '"type":"text"' not in out:
        return False
    # Verificar que el texto contiene un número (respuesta real, no solo "Terminado")
    import re
    for line in out.split('\n'):
        try:
            import json as _json
            ev = _json.loads(line)
            if ev.get('type') == 'text':
                txt = ev.get('part', {}).get('text', '')
                if re.search(r'\d{2,}', txt):
                    return True
        except Exception:
            continue
    return False


def check_opencode(log_fn=print):
    """
    Verifica OpenCode con el modelo activo en ia_config BD.
    Si falla, prueba los fallbacks en orden y actualiza la BD.
    (lineas, fallos, acciones)
    """
    modelo = get_ia_config('sa_opencode_modelo') or 'opencode/big-pickle'
    fallbacks_str = get_ia_config('sa_opencode_fallbacks') or ''
    fallbacks = [f.strip() for f in fallbacks_str.split(',') if f.strip()]
    nombre = modelo.split('/')[-1]

    if _oc_responde(modelo):
        return [_ok(f'OpenCode ({nombre})')], 0, []

    log_fn(f'OpenCode {nombre} no respondió SQL correctamente')

    for fallback in [m for m in fallbacks if m != modelo]:
        if _oc_responde(fallback):
            set_ia_config('sa_opencode_modelo', fallback)
            fb = fallback.split('/')[-1]
            log_fn(f'OpenCode: {nombre} → {fb}')
            return (
                [_warn(f'OpenCode: {nombre} → {fb} (auto)')],
                0,
                [_fix(f'OpenCode: {nombre} falló → <b>{fb}</b>')],
            )

    return [_fail(f'OpenCode: todos los modelos fallaron ({nombre})')], 1, []


def check_gpu(log_fn=print):
    """Verifica GPU VRAM. (lineas, fallos, acciones)"""
    rc, out, _ = _run(
        ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits']
    )
    if rc == 0 and out:
        partes = [p.strip() for p in out.split(',')]
        usado, total = partes[0], partes[1]
        pct = int(usado) * 100 // max(int(total), 1)
        if pct >= 95:
            return [_warn(f'GPU VRAM {pct}% — {usado}/{total} MB')], 0, []
        return [_ok(f'GPU {usado}/{total} MB')], 0, []
    return [_warn('GPU: nvidia-smi sin respuesta')], 0, []


def check_bot_errores(log_path=BOT_LOG, log_fn=print):
    """
    Verifica el bot. Los 409 esporádicos son normales (httpx keepalive).
    Solo alarma si hay racha de 10+ conflictos consecutivos sin recovery.
    (lineas, fallos, acciones)
    """
    if not os.path.exists(log_path):
        return [_warn('Bot: sin log')], 0, []
    try:
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 20000))
            lines = f.read().decode('utf-8', errors='ignore').splitlines()
        max_racha = racha = 0
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


def check_ia_service(log_fn=print):
    """Verifica health del IA Service (puerto 5100). (lineas, fallos, acciones)"""
    try:
        import requests
        r = requests.get('http://localhost:5100/ia/health', timeout=5)
        if r.status_code == 200:
            return [_ok('IA Service (5100)')], 0, []
        return [_fail(f'IA Service HTTP {r.status_code}')], 1, []
    except Exception:
        return [_fail('IA Service no responde')], 1, []


def check_consumo_ia(log_fn=print):
    """Verifica consumo IA del día. Alerta si > 90% del límite. (lineas, fallos, acciones)"""
    try:
        import requests
        r = requests.get('http://localhost:5100/ia/consumo', timeout=5)
        if r.status_code == 200:
            data = r.json()
            costo = data.get('hoy', {}).get('costo_usd', 0)
            limite = data.get('limite_dia_usd', 5)
            if limite and costo / max(limite, 0.001) >= 0.9:
                return [_warn(f'Consumo IA: ${costo:.3f}/${limite} ({costo/limite*100:.0f}%)')], 0, []
            return [_ok(f'Consumo IA: ${costo:.3f} hoy')], 0, []
    except Exception:
        pass
    return [_warn('Consumo IA: no disponible')], 0, []
