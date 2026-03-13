"""
Módulo RAG (Retrieval-Augmented Generation).

Fragmenta documentos en chunks de ~500 palabras y los indexa en ia_rag_fragmentos.
La búsqueda usa FULLTEXT MATCH...AGAINST de MariaDB — sin infra extra.

Tablas que usa:
  ia_rag_colecciones  — espacios de conocimiento (ej: 'negocio-os', 'erp-manual')
  ia_rag_documentos   — documentos originales por colección
  ia_rag_fragmentos   — chunks indexados con FULLTEXT para búsqueda

Flujo:
  1. Usuario sube documento → indexar_documento()
  2. Al consultar → obtener_contexto_rag() inyecta los fragmentos relevantes al system prompt
"""
from .config import get_local_conn

CHUNK_SIZE    = 500   # palabras por fragmento
CHUNK_OVERLAP = 50    # solapamiento para no perder contexto entre chunks
MAX_RESULTADOS = 5    # máximo de fragmentos inyectados al contexto


# ─────────────────────────────────────────────────────────────────────────────
# Fragmentación
# ─────────────────────────────────────────────────────────────────────────────

def fragmentar_texto(texto: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Divide texto en fragmentos de ~chunk_size palabras con solapamiento.
    Retorna lista de strings.
    """
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


def indexar_documento(documento_id: int, contenido: str, coleccion_id: int) -> int:
    """
    Fragmenta un documento y guarda los chunks en ia_rag_fragmentos.
    Elimina fragmentos anteriores del mismo documento antes de indexar.

    Args:
        documento_id:  ID del registro en ia_rag_documentos.
        contenido:     Texto completo del documento.
        coleccion_id:  ID de la colección padre.

    Returns:
        Número de fragmentos creados.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            # Limpiar fragmentos anteriores
            cur.execute("DELETE FROM ia_rag_fragmentos WHERE documento_id = %s", (documento_id,))

            fragmentos = fragmentar_texto(contenido)
            for orden, frag in enumerate(fragmentos):
                cur.execute(
                    "INSERT INTO ia_rag_fragmentos (documento_id, coleccion_id, contenido, orden) "
                    "VALUES (%s, %s, %s, %s)",
                    (documento_id, coleccion_id, frag, orden)
                )

            # Actualizar conteo y tokens estimados en el documento
            tokens_est = int(len(contenido.split()) * 1.33)  # ~1.33 tokens por palabra
            cur.execute(
                "UPDATE ia_rag_documentos SET fragmentos_total = %s, tokens_estimados = %s "
                "WHERE id = %s",
                (len(fragmentos), tokens_est, documento_id)
            )
            conn.commit()
            return len(fragmentos)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Búsqueda
# ─────────────────────────────────────────────────────────────────────────────

def buscar(pregunta: str, coleccion_id: int = None, max_resultados: int = MAX_RESULTADOS) -> list:
    """
    Busca fragmentos relevantes usando FULLTEXT MATCH...AGAINST de MariaDB.

    Args:
        pregunta:       Texto de la pregunta del usuario.
        coleccion_id:   Si se da, filtra a esa colección. None = todas las activas.
        max_resultados: Máximo de fragmentos a retornar.

    Returns:
        Lista de dicts: {contenido, nombre_documento, coleccion_slug, score}
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            if coleccion_id:
                cur.execute(
                    """SELECT f.contenido,
                              d.nombre       AS nombre_documento,
                              c.slug         AS coleccion_slug,
                              MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
                       FROM ia_rag_fragmentos f
                       JOIN ia_rag_documentos   d ON f.documento_id  = d.id
                       JOIN ia_rag_colecciones  c ON f.coleccion_id  = c.id
                       WHERE f.coleccion_id = %s
                         AND d.activo = 1
                         AND c.activo = 1
                         AND MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) > 0
                       ORDER BY score DESC
                       LIMIT %s""",
                    (pregunta, coleccion_id, pregunta, max_resultados)
                )
            else:
                cur.execute(
                    """SELECT f.contenido,
                              d.nombre       AS nombre_documento,
                              c.slug         AS coleccion_slug,
                              MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
                       FROM ia_rag_fragmentos f
                       JOIN ia_rag_documentos   d ON f.documento_id  = d.id
                       JOIN ia_rag_colecciones  c ON f.coleccion_id  = c.id
                       WHERE d.activo = 1
                         AND c.activo = 1
                         AND MATCH(f.contenido) AGAINST (%s IN NATURAL LANGUAGE MODE) > 0
                       ORDER BY score DESC
                       LIMIT %s""",
                    (pregunta, pregunta, max_resultados)
                )
            return cur.fetchall() or []
    finally:
        conn.close()


def obtener_contexto_rag(pregunta: str, coleccion_id: int = None) -> str:
    """
    Busca fragmentos relevantes y los formatea como bloque de contexto
    listo para inyectar en el system prompt.

    Retorna string vacío si no hay resultados (no hay RAG documentos cargados
    o la pregunta no hace match con ningún fragmento).
    """
    fragmentos = buscar(pregunta, coleccion_id)
    if not fragmentos:
        return ''

    partes = ['## Información relevante de la base de conocimiento:\n']
    for f in fragmentos:
        partes.append(f"### Fuente: {f['nombre_documento']}\n{f['contenido']}\n")

    return '\n'.join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# Gestión de colecciones y documentos (usados por los endpoints de ia-admin)
# ─────────────────────────────────────────────────────────────────────────────

def listar_colecciones() -> list:
    """Retorna todas las colecciones con conteo de documentos y fragmentos."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT c.*,
                          COUNT(DISTINCT d.id)  AS total_documentos,
                          SUM(d.fragmentos_total) AS total_fragmentos,
                          SUM(d.tokens_estimados) AS total_tokens
                   FROM ia_rag_colecciones c
                   LEFT JOIN ia_rag_documentos d ON d.coleccion_id = c.id AND d.activo = 1
                   GROUP BY c.id
                   ORDER BY c.nombre"""
            )
            return cur.fetchall() or []
    finally:
        conn.close()


def listar_documentos(coleccion_id: int) -> list:
    """Retorna documentos de una colección."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, tipo, tokens_estimados, fragmentos_total, activo, created_at "
                "FROM ia_rag_documentos WHERE coleccion_id = %s ORDER BY nombre",
                (coleccion_id,)
            )
            return cur.fetchall() or []
    finally:
        conn.close()


def crear_documento(coleccion_id: int, nombre: str, tipo: str, contenido: str) -> dict:
    """
    Crea un documento y lo indexa en fragmentos.
    Retorna {id, fragmentos_creados}.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ia_rag_documentos (coleccion_id, nombre, tipo, contenido_original) "
                "VALUES (%s, %s, %s, %s)",
                (coleccion_id, nombre, tipo, contenido)
            )
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            doc_id = cur.fetchone()['id']
            conn.commit()

        n = indexar_documento(doc_id, contenido, coleccion_id)
        return {'id': doc_id, 'fragmentos_creados': n}
    finally:
        conn.close()


def eliminar_documento(documento_id: int):
    """Elimina documento y sus fragmentos (CASCADE)."""
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ia_rag_documentos WHERE id = %s", (documento_id,))
            conn.commit()
    finally:
        conn.close()
