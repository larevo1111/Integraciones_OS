"""
Parsea la respuesta cruda de la IA y extrae:
- El texto principal (sin las etiquetas internas)
- El SQL (si está entre ```sql ... ```)
- El resumen de contexto (si está entre [RESUMEN_CONTEXTO]...[/RESUMEN_CONTEXTO])
- El formato sugerido (texto, tabla, texto_tabla, json, documento)
"""
import re
import json

from .ejecutor_sql import limpiar_sql as _limpiar_sql


def parsear_respuesta(texto_crudo: str) -> dict:
    """
    Returns:
        {
            "respuesta": str,           # texto limpio para el usuario
            "resumen_nuevo": str|None,  # resumen de contexto actualizado
            "formato": str,             # texto|tabla|texto_tabla|json|documento
        }
    """
    texto = texto_crudo or ''

    # Extraer resumen de contexto
    resumen_nuevo = None
    match = re.search(r'\[RESUMEN_CONTEXTO\](.*?)\[/RESUMEN_CONTEXTO\]', texto, re.DOTALL)
    if match:
        resumen_nuevo = match.group(1).strip()
        texto = texto[:match.start()].strip()

    # Detectar formato
    formato = _detectar_formato(texto)

    return {
        'respuesta':    texto.strip(),
        'resumen_nuevo': resumen_nuevo,
        'formato':      formato,
    }


def extraer_sql(texto: str) -> str | None:
    """Extrae SQL de un bloque ```sql ... ``` o de texto plano si parece SQL."""
    # Bloque markdown — acepta (SELECT... (con paréntesis, para UNION parenthesizado)
    match = re.search(r'```(?:sql)?\s*([\s\S]*?SELECT[\s\S]*?)```', texto, re.DOTALL | re.IGNORECASE)
    if match:
        candidato = _limpiar_sql(match.group(1))
        # Verificar que realmente contiene SELECT
        if re.search(r'\bSELECT\b', candidato, re.IGNORECASE):
            return candidato

    # SQL sin markdown (línea que empieza con SELECT o con paréntesis + SELECT)
    match = re.search(r'(\(?\s*SELECT\s.+)', texto, re.DOTALL | re.IGNORECASE)
    if match:
        candidate = _limpiar_sql(match.group(1).strip())
        # Limitar a la primera sentencia
        candidate = candidate.split(';')[0].strip()
        # Eliminar backticks residuales al final (si el LLM no cerró el bloque)
        candidate = re.sub(r'`+\s*$', '', candidate).strip()
        if len(candidate) > 10:
            return candidate

    return None


def extraer_json(texto: str) -> dict | None:
    """Extrae un JSON de la respuesta si existe."""
    match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # JSON sin markdown
    match = re.search(r'(\{[^{}]*\}|\[[^\[\]]*\])', texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    return None


def _detectar_formato(texto: str) -> str:
    """Detecta el tipo de formato de la respuesta."""
    if re.search(r'```(?:json)', texto):
        return 'json'
    if re.search(r'\|.+\|', texto):  # tabla markdown
        return 'texto_tabla'
    return 'texto'


def filas_a_tabla(filas: list, columnas: list) -> dict:
    """Convierte filas de BD al formato tabla estándar del servicio."""
    return {
        'columnas': columnas,
        'filas': [
            [str(row[col]) if row.get(col) is not None else '' for col in columnas]
            for row in filas
        ]
    }
