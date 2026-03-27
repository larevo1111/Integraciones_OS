"""
wa_bridge.py — Cliente Python para wa_bridge (WhatsApp HTTP Bridge)

Uso:
    from wa_bridge.wa_bridge import wa_send_text, wa_send_image, wa_status

    wa_send_text('573001234567', 'Hola!')
    wa_send_image('573001234567', '/ruta/imagen.jpg', caption='Foto')

También actúa como receptor de webhook si se usa junto a Flask/FastAPI.
El webhook llega a POST /webhook/whatsapp — manejarlo en tu app principal.
"""

import requests
import os

WA_BRIDGE = os.environ.get('WA_BRIDGE_URL', 'http://localhost:3100')
_TIMEOUT = 15


def _post(endpoint: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{WA_BRIDGE}{endpoint}", json=payload, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {'ok': False, 'error': 'wa_bridge no disponible (ConnectionError)'}
    except requests.exceptions.Timeout:
        return {'ok': False, 'error': 'wa_bridge timeout'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def wa_status() -> dict:
    """Retorna estado de la conexión WhatsApp."""
    try:
        r = requests.get(f"{WA_BRIDGE}/api/status", timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def wa_send_text(to: str, message: str) -> dict:
    """
    Envía texto.
    to: número sin + (ej: '573001234567')
    """
    return _post('/api/send/text', {'to': to, 'message': message})


def wa_send_image(to: str, file_path: str, caption: str = '') -> dict:
    """
    Envía imagen desde ruta del servidor.
    file_path: ruta absoluta en el servidor donde corre wa_bridge.
    """
    return _post('/api/send/image', {'to': to, 'filePath': file_path, 'caption': caption})


def wa_send_image_b64(to: str, base64_data: str, caption: str = '', ext: str = 'jpg') -> dict:
    """Envía imagen desde base64."""
    return _post('/api/send/image', {'to': to, 'base64': base64_data, 'ext': ext, 'caption': caption})


def wa_send_audio(to: str, file_path: str, ptt: bool = True) -> dict:
    """
    Envía audio.
    ptt=True → nota de voz (ícono micrófono). ptt=False → archivo de audio.
    """
    return _post('/api/send/audio', {'to': to, 'filePath': file_path, 'ptt': ptt})


def wa_send_document(to: str, file_path: str, file_name: str = '', mimetype: str = '') -> dict:
    """Envía documento/archivo."""
    return _post('/api/send/document', {
        'to': to,
        'filePath': file_path,
        'fileName': file_name or os.path.basename(file_path),
        'mimetype': mimetype,
    })


def wa_send_video(to: str, file_path: str, caption: str = '') -> dict:
    """Envía video."""
    return _post('/api/send/video', {'to': to, 'filePath': file_path, 'caption': caption})


# ── Ejemplo de webhook receiver (Flask) ───────────────────────────────────────
# Pegar esto en tu app Flask si quieres recibir mensajes entrantes:
#
# @app.route('/webhook/whatsapp', methods=['POST'])
# def whatsapp_webhook():
#     data = request.json
#     # data = {
#     #   'from': '573001234567@s.whatsapp.net',
#     #   'type': 'text' | 'image' | 'audio' | 'video' | 'document' | 'sticker' | 'location',
#     #   'text': '...',          # si type == 'text'
#     #   'mediaPath': '/ruta',   # si hay archivo descargado
#     #   'caption': '...',
#     #   'fileName': '...',
#     #   'latitude': float,      # si type == 'location'
#     #   'longitude': float,
#     #   'timestamp': int,
#     #   'messageId': str,
#     # }
#     manejar_mensaje_whatsapp(data)
#     return {'ok': True}
