"""
Proveedor para Google Gemini (API nativa de Google).
Soporta modelos de texto y de generación de imágenes (gemini-2.5-flash-image).
"""
import time
import requests


def agente_con_capacidad(capacidad: str) -> dict | None:
    """
    Busca en BD el agente activo con la capacidad dada (ej: 'vision').
    Prioriza gemini-flash como default si tiene la capacidad.
    Retorna el dict del agente o None si no hay ninguno disponible.
    """
    import pymysql, pymysql.cursors, json as _json
    try:
        conn = pymysql.connect(
            host='localhost', user='osadmin', password='Epist2487.',
            database='ia_service_os', cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ia_agentes WHERE activo=1 AND api_key != '' ORDER BY orden ASC"
            )
            agentes = cur.fetchall()
        conn.close()
        # Primero intentar gemini-flash, luego cualquier otro con la capacidad
        candidatos = [a for a in agentes if _json.loads(a.get('capacidades') or '{}').get(capacidad)]
        preferido = next((a for a in candidatos if a['slug'] == 'gemini-flash'), None)
        return preferido or (candidatos[0] if candidatos else None)
    except Exception:
        return None


def llamar(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096,
           imagen_b64: str = None, imagen_mime: str = None) -> dict:
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

    for i, m in enumerate(mensajes):
        role = m['role']
        content = m['content']
        if role == 'system':
            system_instruction = content
        elif role == 'user':
            parts = [{'text': content}]
            # Si es el último mensaje de usuario y viene con imagen, adjuntarla
            if imagen_b64 and imagen_mime and i == len(mensajes) - 1:
                parts.append({'inlineData': {'mimeType': imagen_mime, 'data': imagen_b64}})
            contents.append({'role': 'user', 'parts': parts})
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
        if 'gemma' in modelo.lower():
            # Gemma no soporta systemInstruction — inyectar al inicio del primer user message
            if contents and contents[0].get('role') == 'user':
                contents[0]['parts'][0]['text'] = system_instruction + '\n\n' + contents[0]['parts'][0]['text']
        else:
            payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}

    t0 = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=900)
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
