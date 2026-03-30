"""
Proveedor para Anthropic Claude.
"""
import time
import requests


def llamar(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096) -> dict:
    """
    Llama a la API de Anthropic Claude.

    Los mensajes vienen en formato OpenAI [{role, content}] y se convierten
    al formato de Anthropic (system separado del array de messages).

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
    url = agente['endpoint_url'].rstrip('/') + '/v1/messages'
    headers = {
        'x-api-key':         agente['api_key'],
        'anthropic-version': '2023-06-01',
        'Content-Type':      'application/json',
    }

    # Separar system del array de mensajes (formato Anthropic)
    system_text = ''
    conv_msgs = []
    for m in mensajes:
        if m['role'] == 'system':
            system_text = m['content']
        else:
            conv_msgs.append({'role': m['role'], 'content': m['content']})

    payload = {
        'model':       agente['modelo_id'],
        'max_tokens':  max_tokens,
        'temperature': temperatura,
        'messages':    conv_msgs,
    }
    if system_text:
        payload['system'] = system_text

    t0 = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=900)
        resp.raise_for_status()
        data = resp.json()

        texto      = data['content'][0]['text']
        tokens_in  = data.get('usage', {}).get('input_tokens', 0)
        tokens_out = data.get('usage', {}).get('output_tokens', 0)

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
