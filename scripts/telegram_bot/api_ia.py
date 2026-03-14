"""
Cliente HTTP para ia_service (localhost:5100).
"""
import json, urllib.request, urllib.error

IA_URL = 'http://localhost:5100/ia/consultar'


def consultar(pregunta: str, usuario_id: str, nombre_usuario: str = None,
              agente: str = None, empresa: str = 'ori_sil_2',
              conversacion_id: int = None, canal: str = 'telegram') -> dict:
    payload = {
        'pregunta':       pregunta,
        'usuario_id':     str(usuario_id),
        'canal':          canal,
        'empresa':        empresa,
    }
    if nombre_usuario:
        payload['nombre_usuario'] = nombre_usuario
    if agente:
        payload['agente'] = agente
    if conversacion_id:
        payload['conversacion_id'] = conversacion_id

    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(IA_URL, data=data,
                                  headers={'Content-Type': 'application/json'},
                                  method='POST')
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'ok': False, 'error': f'HTTP {e.code}: {e.read().decode()[:200]}',
                'respuesta': 'Hubo un error contactando el servicio IA.'}
    except Exception as e:
        return {'ok': False, 'error': str(e),
                'respuesta': 'No se pudo conectar con el servicio IA.'}
