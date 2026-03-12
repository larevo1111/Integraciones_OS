"""
Proveedor para Google Gemini (API nativa de Google).
Soporta modelos de texto y de generación de imágenes (gemini-2.5-flash-image).
"""
import time
import requests


def llamar(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096) -> dict:
    """
    Llama a la API de Google Gemini.
    Detecta automáticamente si el modelo genera imágenes según el modelo_id.

    Returns:
        {
            "ok": bool,
            "texto": str,
            "imagen_b64": str|None,   # base64 de la imagen si aplica
            "imagen_mime": str|None,  # "image/png" o "image/jpeg"
            "tokens_in": int,
            "tokens_out": int,
            "latencia_ms": int,
            "error": str|None
        }
    """
    modelo = agente['modelo_id']
    api_key = agente['api_key']
    base_url = agente['endpoint_url'].rstrip('/')
    url = f"{base_url}/models/{modelo}:generateContent?key={api_key}"

    # Detectar si es modelo de imagen
    es_imagen = 'image' in modelo.lower()

    # Convertir mensajes formato OpenAI → Google
    system_instruction = None
    contents = []

    for m in mensajes:
        role = m['role']
        content = m['content']
        if role == 'system':
            system_instruction = content
        elif role == 'user':
            contents.append({'role': 'user', 'parts': [{'text': content}]})
        elif role == 'assistant':
            contents.append({'role': 'model', 'parts': [{'text': content}]})

    payload = {
        'contents': contents,
        'generationConfig': {
            'temperature':     temperatura,
            'maxOutputTokens': max_tokens,
        },
    }

    # Para modelos de imagen: pedir respuesta multimodal (imagen + texto)
    if es_imagen:
        payload['generationConfig']['responseModalities'] = ['IMAGE', 'TEXT']

    if system_instruction:
        payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}

    t0 = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()

        usage = data.get('usageMetadata', {})
        tokens_in  = usage.get('promptTokenCount', 0)
        tokens_out = usage.get('candidatesTokenCount', 0)

        # Parsear partes de la respuesta (texto y/o imagen)
        texto      = ''
        imagen_b64  = None
        imagen_mime = None

        parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        for part in parts:
            if 'text' in part:
                texto += part['text']
            elif 'inlineData' in part:
                imagen_b64  = part['inlineData'].get('data')
                imagen_mime = part['inlineData'].get('mimeType', 'image/png')

        return {
            'ok':          True,
            'texto':       texto,
            'imagen_b64':  imagen_b64,
            'imagen_mime': imagen_mime,
            'tokens_in':   tokens_in,
            'tokens_out':  tokens_out,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error':       None,
        }

    except requests.exceptions.HTTPError as e:
        return {
            'ok': False, 'texto': '', 'imagen_b64': None, 'imagen_mime': None,
            'tokens_in': 0, 'tokens_out': 0,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error': f"HTTP {e.response.status_code}: {e.response.text[:300]}",
        }
    except Exception as e:
        return {
            'ok': False, 'texto': '', 'imagen_b64': None, 'imagen_mime': None,
            'tokens_in': 0, 'tokens_out': 0,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error': str(e),
        }
