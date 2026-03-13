"""
Módulo RAG (Retrieval-Augmented Generation).

Fragmenta documentos en chunks de ~500 palabras y los indexa en ia_rag_fragmentos.
La búsqueda usa FULLTEXT MATCH...AGAINST de MariaDB — sin infra extra.

Tablas:
  ia_temas          — espacios de conocimiento por empresa y área (comercial, finanzas, etc.)
  ia_rag_documentos — documentos originales por tema y empresa
  ia_rag_fragmentos — chunks indexados con FULLTEXT para búsqueda

Flujo:
  1. Admin sube documento → crear_documento() → indexar_documento()
  2. Al consultar → obtener_contexto_rag(pregunta, empresa, tema_slug) inyecta fragmentos relevantes
"""
import json as _json
from .config import get_local_conn

CHUNK_SIZE    = 500   # palabras por fragmento
CHUNK_OVERLAP = 50    # solapamiento para no perder contexto entre chunks
MAX_RESULTADOS = 5    # máximo de fragmentos inyectados al contexto


# ─────────────────────────────────────────────────────────────────────────────
# Fragmentación
# ─────────────────────────────────────────────────────────────────────────────

def fragmentar_texto(texto: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Divide texto en fragmentos de ~chunk_size palabras con solapamiento."""
    palabras = texto.split()
    if not palabras:
        return []
    if len(palabras) <= chunk_size:
        return [texto]

    fragmentos = []
    inicio = 0
    while inicio < len(palabras):
        fin = min(inicio + chunk_size, len(palabras))
        fragmentos.append(' '.join(palabras[inicio:fin]))
        if fin >= len(palabras):
            break
        inicio += chunk_size - overlap
    return fragmentos


def indexar_documento(documento_id: int, contenido: str, tema_id: int, empresa: str = 'ori_sil_2') -> int:
    """
    Fragmenta un documento y guarda los chunks en ia_rag_fragmentos.
    Elimina fragmentos anteriores del mismo documento antes de indexar.
    Retorna el número de fragmentos creados.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ia_rag_fragmentos WHERE documento_id = %s", (documento_id,))

            fragmentos = fragmentar_texto(contenido)
            for orden, frag in enumerate(fragmentos):
                cur.execute(
                    "INSERT INTO ia_rag_fragmentos (empresa, tema_id, documento_id, contenido, orden) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (empresa, tema_id, documento_id, frag, orden)
                )

            tokens_est = int(len(contenido.split()) * 1.33)
            cur.execute(
                "UPDATE ia_rag_documentos SET fragmentos_total = %s, tokens_estimados = %s WHERE id = %s",
                (len(fragmentos), tokens_est, documento_id)
            )
            conn.commit()
            return len(fragmentos)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Búsqueda
# ─────────────────────────────────────────────────────────────────────────────

def buscar(pregunta: str, empresa: str = 'ori_sil_2', tema_id: int = None,
           max_resultados: int = MAX_RESULTADOS) -> list:
    """
    Busca fragmentos relevantes usando FULLTEXT MATCH...AGAINST.

    Args:
        pregunta:       Texto de la pregunta del usuario.
        empresa:        Filtra por empresa (default: 'ori_sil_2').
        tema_id:        Si se da, filtra a ese tema. None = todos los temas activos.
        max_resultados: Máximo de fragmentos a retornar.

    Returns:
        Lista de dicts: {contenido, nombre_documento, tema_slug, tema_nombre, score}
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            if tema_id:
                cur.execute(
                    """SELECT f.contenido,
                              d.nombre   AS nombre_documento,
                              t.slug     AS tema_slug,
                              t.nombre   AS tema_nombre,
                              MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
                       FROM ia_rag_fragmentos f
                       JOIN ia_rag_documentos d ON f.documento_id = d.id
                       JOIN ia_temas          t ON f.tema_id      = t.id
                       WHERE f.empresa = %s AND f.tema_id = %s
                         AND d.activo = 1 AND t.activo = 1
                         AND MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) > 0
                       ORDER BY score DESC LIMIT %s""",
                    (pregunta, empresa, tema_id, pregunta, max_resultados)
                )
            else:
                cur.execute(
                    """SELECT f.contenido,
                              d.nombre   AS nombre_documento,
                              t.slug     AS tema_slug,
                              t.nombre   AS tema_nombre,
                              MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
                       FROM ia_rag_fragmentos f
                       JOIN ia_rag_documentos d ON f.documento_id = d.id
                       JOIN ia_temas          t ON f.tema_id      = t.id
                       WHERE f.empresa = %s AND d.activo = 1 AND t.activo = 1
                         AND MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) > 0
                       ORDER BY score DESC LIMIT %s""",
                    (pregunta, empresa, pregunta, max_resultados)
                )
            return cur.fetchall() or []
    finally:
        conn.close()


def obtener_contexto_rag(pregunta: str, empresa: str = 'ori_sil_2', tema_id: int = None) -> str:
    """
    Busca fragmentos relevantes y los formatea como bloque de contexto
    para inyectar en el system prompt (CAPA 2).
    Retorna string vacío si no hay resultados.
    """
    fragmentos = buscar(pregunta, empresa, tema_id)
    if not fragmentos:
        return ''

    partes = ['## Información relevante de la base de conocimiento:\n']
    for f in fragmentos:
        partes.append(f"### Fuente: {f['nombre_documento']} [{f['tema_nombre']}]\n{f['contenido']}\n")
    return '\n'.join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de temas (usados por endpoints de ia-admin)
# ─────────────────────────────────────────────────────────────────────────────

def listar_temas(empresa: str = 'ori_sil_2') -> list:
    """Retorna todos los temas de una empresa con conteo de documentos y fragmentos."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT t.*,
                          COUNT(DISTINCT d.id)            AS total_documentos,
                          COALESCE(SUM(d.fragmentos_total), 0) AS total_fragmentos,
                          COALESCE(SUM(d.tokens_estimados), 0) AS total_tokens
                   FROM ia_temas t
                   LEFT JOIN ia_rag_documentos d ON d.tema_id = t.id AND d.activo = 1
                   WHERE t.empresa = %s
                   GROUP BY t.id
                   ORDER BY t.nombre""",
                (empresa,)
            )
            return cur.fetchall() or []
    finally:
        conn.close()


def listar_empresas() -> list:
    """Retorna las empresas distintas que tienen temas."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT empresa FROM ia_temas ORDER BY empresa")
            return [row['empresa'] for row in (cur.fetchall() or [])]
    finally:
        conn.close()


def listar_documentos(tema_id: int) -> list:
    """Retorna documentos de un tema (sin contenido_original)."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at "
                "FROM ia_rag_documentos WHERE tema_id = %s ORDER BY nombre",
                (tema_id,)
            )
            return cur.fetchall() or []
    finally:
        conn.close()


def crear_documento(tema_id: int, nombre: str, tipo: str, contenido: str,
                    empresa: str = 'ori_sil_2') -> dict:
    """
    Crea un documento e indexa sus fragmentos.
    Retorna {id, fragmentos_creados}.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ia_rag_documentos (empresa, tema_id, nombre, tipo, contenido_original) "
                "VALUES (%s, %s, %s, %s, %s)",
                (empresa, tema_id, nombre, tipo, contenido)
            )
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            doc_id = cur.fetchone()['id']
            conn.commit()

        n = indexar_documento(doc_id, contenido, tema_id, empresa)
        return {'id': doc_id, 'fragmentos_creados': n}
    finally:
        conn.close()


def eliminar_documento(documento_id: int):
    """Elimina documento y sus fragmentos (CASCADE en BD)."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ia_rag_documentos WHERE id = %s", (documento_id,))
            conn.commit()
    finally:
        conn.close()


def obtener_tema_por_slug(slug: str, empresa: str = 'ori_sil_2') -> dict:
    """Retorna un tema por slug y empresa. None si no existe."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM ia_temas WHERE slug = %s AND empresa = %s AND activo = 1",
                (slug, empresa)
            )
            return cur.fetchone()
    finally:
        conn.close()
