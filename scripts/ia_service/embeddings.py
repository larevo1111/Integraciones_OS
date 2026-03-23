"""
Módulo de embeddings semánticos para búsqueda de ejemplos Q→SQL.

Usa Google gemini-embedding-001 (3072 dimensiones, API gratuita).
Almacena vectores como JSON en ia_ejemplos_sql.embedding.
La búsqueda por cosine similarity reemplaza la búsqueda por LIKE.

Escalabilidad: funciona igual bien con 10 que con 100,000 ejemplos.
"""
import json
import math
import os
import urllib.request
import urllib.parse

from .config import get_local_conn


# ── Configuración ────────────────────────────────────────────────────────────

_EMBEDDING_MODEL = 'gemini-embedding-001'
_EMBEDDING_DIMS  = 3072
_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={key}'


def _get_api_key() -> str:
    """Lee la API key de Google desde la BD (ia_agentes) o variable de entorno."""
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT api_key FROM ia_agentes WHERE proveedor = 'google' AND activo = 1 LIMIT 1"
            )
            row = cur.fetchone()
        conn.close()
        if row and row.get('api_key'):
            return row['api_key']
    except Exception:
        pass
    return os.environ.get('GOOGLE_API_KEY', '')


def generar_embedding(texto: str) -> list[float] | None:
    """
    Genera un vector de embeddings para un texto usando Google text-embedding-004.
    Devuelve lista de 768 floats, o None si falla.
    """
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        url  = _API_URL.format(model=_EMBEDDING_MODEL, key=api_key)
        body = json.dumps({
            'model':   f'models/{_EMBEDDING_MODEL}',
            'content': {'parts': [{'text': texto[:2000]}]},
            'taskType': 'SEMANTIC_SIMILARITY',
        }).encode('utf-8')
        req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data['embedding']['values']
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores."""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def guardar_embedding(ejemplo_id: int, texto: str):
    """
    Genera y guarda el embedding de un ejemplo en ia_ejemplos_sql.
    Se llama al guardar un ejemplo nuevo o al migrar los existentes.
    """
    vector = generar_embedding(texto)
    if not vector:
        return
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_ejemplos_sql SET embedding = %s WHERE id = %s",
                (json.dumps(vector), ejemplo_id)
            )
            conn.commit()
        conn.close()
    except Exception:
        pass


def buscar_ejemplos_semanticos(empresa: str, pregunta: str, n: int = 3) -> list[dict]:
    """
    Busca los N ejemplos Q→SQL más similares semánticamente a la pregunta.
    Requiere que los ejemplos tengan embedding guardado.

    Retorna lista de dicts con 'pregunta' y 'sql_generado'.
    Si la API falla o no hay embeddings, devuelve lista vacía (el caller tiene fallback por keywords).
    """
    vector_pregunta = generar_embedding(pregunta)
    if not vector_pregunta:
        return []

    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, pregunta, sql_generado, embedding
                FROM ia_ejemplos_sql
                WHERE empresa = %s AND embedding IS NOT NULL
                ORDER BY ultima_vez DESC
                LIMIT 500
                """,
                (empresa,)
            )
            filas = cur.fetchall()
        conn.close()
    except Exception:
        return []

    if not filas:
        return []

    # Calcular similitud coseno contra todos los ejemplos con embedding
    puntuados = []
    for fila in filas:
        try:
            vec = json.loads(fila['embedding'])
            sim = _cosine_similarity(vector_pregunta, vec)
            puntuados.append((sim, fila))
        except Exception:
            continue

    # Ordenar por similitud descendente y devolver los N mejores
    puntuados.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in puntuados[:n]]


def migrar_embeddings_faltantes(empresa: str | None = None):
    """
    Utilidad de mantenimiento: genera embeddings para todos los ejemplos
    que aún no tienen uno. Puede correrse manualmente o en background.
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            if empresa:
                cur.execute(
                    "SELECT id, pregunta FROM ia_ejemplos_sql WHERE embedding IS NULL AND empresa = %s",
                    (empresa,)
                )
            else:
                cur.execute("SELECT id, pregunta FROM ia_ejemplos_sql WHERE embedding IS NULL")
            pendientes = cur.fetchall()
        conn.close()
    except Exception:
        return

    for ej in pendientes:
        guardar_embedding(ej['id'], ej['pregunta'])
