"""
Proveedor para Google Gemini (API nativa de Google).
"""
import time
import requests


def llamar(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096) -> dict:
    """
    Llama a la API de Google Gemini.

    Los mensajes vienen en formato OpenAI [{role, content}] y se convierten
    al formato nativo de Google antes de enviar.

    Returns:
        {
            "ok": bool,
            "texto": str,
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
    if system_instruction:
        payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}

    t0 = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        texto = data['candidates'][0]['content']['parts'][0]['text']
        usage = data.get('usageMetadata', {})
        tokens_in  = usage.get('promptTokenCount', 0)
        tokens_out = usage.get('candidatesTokenCount', 0)

        return {
            'ok':          True,
            'texto':       texto,
            'tokens_in':   tokens_in,
            'tokens_out':  tokens_out,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error':       None,
        }

    except requests.exceptions.HTTPError as e:
        return {
            'ok': False, 'texto': '', 'tokens_in': 0, 'tokens_out': 0,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error': f"HTTP {e.response.status_code}: {e.response.text[:300]}",
        }
    except Exception as e:
        return {
            'ok': False, 'texto': '', 'tokens_in': 0, 'tokens_out': 0,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error': str(e),
        }
