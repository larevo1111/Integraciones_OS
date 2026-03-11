#!/usr/bin/env python3
"""
Servidor webhook para disparar pasos del pipeline de Effi a demanda.
Corre en el host en 0.0.0.0:5050 — accesible desde Docker via 172.18.0.1:5050.
Iniciado por systemd: effi-webhook.service

Endpoints:
  POST /trigger      → solo 7a+7b (CRM → Effi)
  POST /trigger-sync → 6c+6d+7a+7b (sync bidireccional CRM ↔ Effi)
  GET  /status       → estado del último proceso
  GET  /health       → health check
"""

import os
import threading
import subprocess
import datetime
from flask import Flask, jsonify, request

SCRIPTS_DIR  = os.path.dirname(os.path.abspath(__file__))
GENERAR_SCRIPT  = os.path.join(SCRIPTS_DIR, 'generar_plantilla_import_effi.py')
IMPORT_SCRIPT   = os.path.join(SCRIPTS_DIR, 'import_clientes_effi.js')
SYNC_CRM_SCRIPT = os.path.join(SCRIPTS_DIR, 'sync_espocrm_contactos.py')
SYNC_HOST_SCRIPT= os.path.join(SCRIPTS_DIR, 'sync_espocrm_to_hostinger.py')

app = Flask(__name__)

_lock    = threading.Lock()
_running = False
_last    = {
    'status':    'idle',
    'message':   'Sin ejecuciones previas.',
    'timestamp': None,
}


def _run():
    global _running, _last
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # ── 7a. Generar plantilla ─────────────────────────────────────────────
        r7a = subprocess.run(
            ['python3', GENERAR_SCRIPT],
            capture_output=True, text=True, timeout=90, cwd=SCRIPTS_DIR
        )
        salida_7a = r7a.stdout.strip()

        if r7a.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 7a falló: {r7a.stderr[:300]}', 'timestamp': ts}
            return

        if 'contactos →' not in salida_7a:
            _last = {'status': 'ok', 'message': 'Sin contactos pendientes para enviar a Effi.', 'timestamp': ts}
            return

        # Extraer ruta del xlsx generado
        xlsx_path = None
        for linea in salida_7a.splitlines():
            if '/tmp/import_clientes_effi_' in linea and '.xlsx' in linea:
                partes = linea.split('→')
                if len(partes) >= 2:
                    xlsx_path = partes[-1].strip()
                    break

        # ── 7b. Subir a Effi ──────────────────────────────────────────────────
        cmd_7b = ['node', IMPORT_SCRIPT]
        if xlsx_path:
            cmd_7b.append(xlsx_path)

        r7b = subprocess.run(
            cmd_7b,
            capture_output=True, text=True, timeout=180, cwd=SCRIPTS_DIR
        )

        if r7b.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 7b falló: {r7b.stderr[:300]}', 'timestamp': ts}
            return

        resumen = salida_7a.splitlines()[-1] if salida_7a else '(sin detalle)'
        _last = {'status': 'ok', 'message': f'Importación completada. {resumen}', 'timestamp': ts}

    except subprocess.TimeoutExpired:
        _last = {'status': 'error', 'message': 'Timeout: el proceso tardó demasiado.', 'timestamp': ts}
    except Exception as e:
        _last = {'status': 'error', 'message': f'Error inesperado: {e}', 'timestamp': ts}
    finally:
        with _lock:
            _running = False


def _run_sync_full():
    """Sincronización bidireccional completa: 6c (Effi→CRM) + 6d (CRM→Hostinger) + 7a+7b (CRM→Effi)."""
    global _running, _last
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pasos_ok = []

    try:
        # ── 6c. Effi → EspoCRM ───────────────────────────────────────────────
        r6c = subprocess.run(
            ['python3', SYNC_CRM_SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=SCRIPTS_DIR
        )
        if r6c.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 6c falló: {r6c.stderr[:300]}', 'timestamp': ts}
            return
        pasos_ok.append('6c:OK')

        # ── 6d. EspoCRM → Hostinger ───────────────────────────────────────────
        r6d = subprocess.run(
            ['python3', SYNC_HOST_SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=SCRIPTS_DIR
        )
        if r6d.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 6d falló: {r6d.stderr[:300]}', 'timestamp': ts}
            return
        pasos_ok.append('6d:OK')

        # ── 7a. Generar plantilla ─────────────────────────────────────────────
        r7a = subprocess.run(
            ['python3', GENERAR_SCRIPT],
            capture_output=True, text=True, timeout=90, cwd=SCRIPTS_DIR
        )
        salida_7a = r7a.stdout.strip()
        if r7a.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 7a falló: {r7a.stderr[:300]}', 'timestamp': ts}
            return
        pasos_ok.append('7a:OK')

        if 'contactos →' not in salida_7a:
            _last = {'status': 'ok',
                     'message': f'Sync completado ({", ".join(pasos_ok)}). Sin contactos CRM pendientes para Effi.',
                     'timestamp': ts}
            return

        # Extraer ruta xlsx
        xlsx_path = None
        for linea in salida_7a.splitlines():
            if '/tmp/import_clientes_effi_' in linea and '.xlsx' in linea:
                partes = linea.split('→')
                if len(partes) >= 2:
                    xlsx_path = partes[-1].strip()
                    break

        # ── 7b. Subir a Effi ──────────────────────────────────────────────────
        cmd_7b = ['node', IMPORT_SCRIPT]
        if xlsx_path:
            cmd_7b.append(xlsx_path)
        r7b = subprocess.run(
            cmd_7b,
            capture_output=True, text=True, timeout=180, cwd=SCRIPTS_DIR
        )
        if r7b.returncode != 0:
            _last = {'status': 'error', 'message': f'Paso 7b falló: {r7b.stderr[:300]}', 'timestamp': ts}
            return

        resumen = salida_7a.splitlines()[-1] if salida_7a else ''
        _last = {'status': 'ok',
                 'message': f'Sync bidireccional completado. {resumen}',
                 'timestamp': ts}

    except subprocess.TimeoutExpired:
        _last = {'status': 'error', 'message': 'Timeout: el proceso tardó demasiado.', 'timestamp': ts}
    except Exception as e:
        _last = {'status': 'error', 'message': f'Error inesperado: {e}', 'timestamp': ts}
    finally:
        with _lock:
            _running = False


@app.route('/trigger', methods=['POST'])
def trigger():
    global _running
    with _lock:
        if _running:
            return jsonify({'status': 'busy', 'message': 'Ya hay un proceso en curso. Espera y vuelve a intentar.'}), 409
        _running = True

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'message': 'Proceso iniciado. Los contactos aparecerán en Effi en 1-2 minutos.'})


@app.route('/trigger-sync', methods=['POST'])
def trigger_sync():
    global _running
    with _lock:
        if _running:
            return jsonify({'status': 'busy', 'message': 'Ya hay una sincronización en curso. Espera y vuelve a intentar.'}), 409
        _running = True

    threading.Thread(target=_run_sync_full, daemon=True).start()
    return jsonify({'status': 'started', 'message': 'Sincronización bidireccional iniciada (1-3 min). Effi → CRM y CRM → Effi.'})


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'running': _running, 'last': _last})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)
