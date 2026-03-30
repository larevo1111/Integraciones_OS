"""
Proveedor para APIs compatibles con el formato OpenAI.
Cubre: Groq, DeepSeek.
"""
import time
import requests


def llamar(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096) -> dict:
    """
    Llama a una API compatible con OpenAI.

    Args:
        agente: fila de ia_agentes (dict con endpoint_url, api_key, modelo_id)
        mensajes: lista [{"role": "system"|"user"|"assistant", "content": "..."}]
        temperatura: 0.0–1.0
        max_tokens: máximo de tokens en la respuesta

    Returns:
        {
            "ok": bool,
            "texto": str,       # respuesta completa
            "tokens_in": int,
            "tokens_out": int,
            "error": str|None
        }
    """
    url = agente['endpoint_url'].rstrip('/') + '/chat/completions'
    headers = {
        'Authorization': f"Bearer {agente['api_key']}",
        'Content-Type':  'application/json',
    }
    payload = {
        'model':       agente['modelo_id'],
        'messages':    mensajes,
        'temperature': temperatura,
        'max_tokens':  max_tokens,
    }

    t0 = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=900)
        resp.raise_for_status()
        data = resp.json()

        texto      = data['choices'][0]['message']['content']
        tokens_in  = data.get('usage', {}).get('prompt_tokens', 0)
        tokens_out = data.get('usage', {}).get('completion_tokens', 0)

        return {
            'ok':         True,
            'texto':      texto,
            'tokens_in':  tokens_in,
            'tokens_out': tokens_out,
            'latencia_ms': int((time.time() - t0) * 1000),
            'error':      None,
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
