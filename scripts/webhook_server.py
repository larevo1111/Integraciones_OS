#!/usr/bin/env python3
"""
Servidor webhook para disparar pasos 7a+7b del pipeline de Effi a demanda.
Corre en el host en 0.0.0.0:5050 — accesible desde Docker via 172.18.0.1:5050.
Iniciado por systemd: effi-webhook.service
"""

import os
import threading
import subprocess
import datetime
from flask import Flask, jsonify, request

SCRIPTS_DIR  = os.path.dirname(os.path.abspath(__file__))
GENERAR_SCRIPT = os.path.join(SCRIPTS_DIR, 'generar_plantilla_import_effi.py')
IMPORT_SCRIPT  = os.path.join(SCRIPTS_DIR, 'import_clientes_effi.js')

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


@app.route('/trigger', methods=['POST'])
def trigger():
    global _running
    with _lock:
        if _running:
            return jsonify({'status': 'busy', 'message': 'Ya hay un proceso en curso. Espera y vuelve a intentar.'}), 409
        _running = True

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'message': 'Proceso iniciado. Los contactos aparecerán en Effi en 1-2 minutos.'})


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'running': _running, 'last': _last})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)
