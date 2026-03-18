"""
Proveedor Tavily — búsqueda web para ia_service_os.
Retorna resultados limpios listos para sintetizar por el LLM.
"""
import os
import requests
from ..config import get_local_conn

# API key desde config/BD
def _get_api_key() -> str:
    key = os.getenv('TAVILY_API_KEY', '')
    if key:
        return key
    try:
        conn = get_local_conn()
        with conn.cursor() as c:
            c.execute("SELECT api_key FROM ia_agentes WHERE slug='tavily' AND activo=1")
            row = c.fetchone()
        conn.close()
        return row['api_key'] if row else ''
    except Exception:
        return ''


def buscar(pregunta: str, max_resultados: int = 5, modo: str = 'general') -> dict:
    """
    Busca en internet usando Tavily.

    Args:
        pregunta: consulta del usuario
        max_resultados: cuántos resultados traer (3-5 recomendado)
        modo: 'general' | 'news' (noticias recientes) | 'finance'

    Returns:
        {
          'ok': bool,
          'resultados': [{'titulo', 'url', 'contenido', 'score'}],
          'respuesta_directa': str | None,  # respuesta concisa de Tavily si la tiene
          'error': str | None
        }
    """
    api_key = _get_api_key()
    if not api_key:
        return {'ok': False, 'resultados': [], 'respuesta_directa': None,
                'error': 'TAVILY_API_KEY no configurada'}

    try:
        payload = {
            'api_key':      api_key,
            'query':        pregunta,
            'search_depth': 'basic',       # 'basic' rápido | 'advanced' más completo
            'topic':        modo,
            'max_results':  max_resultados,
            'include_answer': True,        # respuesta directa si Tavily la tiene
            'include_raw_content': False,
        }
        resp = requests.post(
            'https://api.tavily.com/search',
            json=payload,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        resultados = [
            {
                'titulo':    r.get('title', ''),
                'url':       r.get('url', ''),
                'contenido': r.get('content', '')[:800],  # limitar largo
                'score':     round(r.get('score', 0), 2)
            }
            for r in data.get('results', [])
        ]

        return {
            'ok':               True,
            'resultados':       resultados,
            'respuesta_directa': data.get('answer'),
            'error':            None
        }

    except requests.Timeout:
        return {'ok': False, 'resultados': [], 'respuesta_directa': None,
                'error': 'Timeout al buscar en internet (>10s)'}
    except Exception as e:
        return {'ok': False, 'resultados': [], 'respuesta_directa': None,
                'error': str(e)}


def formatear_para_llm(resultado_busqueda: dict) -> str:
    """
    Convierte los resultados de Tavily en texto estructurado para el LLM.
    """
    if not resultado_busqueda.get('ok'):
        return f"[Error en búsqueda web: {resultado_busqueda.get('error')}]"

    partes = ['<resultados_web>']

    if resultado_busqueda.get('respuesta_directa'):
        partes.append(f"Respuesta directa: {resultado_busqueda['respuesta_directa']}\n")

    for i, r in enumerate(resultado_busqueda.get('resultados', []), 1):
        partes.append(
            f"[{i}] {r['titulo']}\n"
            f"URL: {r['url']}\n"
            f"{r['contenido']}\n"
        )

    partes.append('</resultados_web>')
    return '\n'.join(partes)
