"""
Sistema de aprendizaje del servicio de IA.
Guarda reglas de negocio, ejemplos SQL, genera resúmenes y depura la lógica.
"""
import re
import threading
from .config import get_local_conn
from . import embeddings as embeddings_module
from .alertas import notificar
from .seguridad import get_config_simple, slugs_router


def depurar_logica_negocio(empresa: str):
    """
    Depurador de lógica de negocio: si el total de palabras supera 800,
    comprime las reglas más largas UNA A UNA hasta bajar del target.
    NUNCA borra, desactiva ni fusiona reglas. Solo acorta la explicación.
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, concepto, explicacion, palabras FROM ia_logica_negocio "
                "WHERE empresa=%s AND activo=1 ORDER BY palabras DESC",
                (empresa,)
            )
            fragmentos = cur.fetchall()
        conn.close()

        total_palabras = sum(f.get('palabras') or len(f['explicacion'].split()) for f in fragmentos)
        TARGET = 900

        if total_palabras <= 1000:
            return

        # Buscar agente — importar aquí para evitar circular
        from .servicio import _cargar_agente, _llamar_agente
        agente_cfg = None
        for slug in ('gemini-flash-lite', 'cerebras-llama', 'groq-llama', 'gemini-flash'):
            cand = _cargar_agente(slug)
            if cand and cand.get('api_key'):
                agente_cfg = cand
                break
        if not agente_cfg:
            return

        actualizadas = 0
        for f in fragmentos:
            if total_palabras <= TARGET:
                break

            palabras_regla = f.get('palabras') or len(f['explicacion'].split())
            if palabras_regla <= 30:
                continue

            exceso = total_palabras - TARGET
            reducir = min(exceso, int(palabras_regla * 0.6))
            target_regla = max(20, palabras_regla - reducir)

            msgs = [
                {'role': 'system', 'content': 'Comprimes texto técnico. Preservas TODOS los nombres de campos, tablas, cifras y porcentajes. Solo devuelves el texto comprimido.'},
                {'role': 'user', 'content': (
                    f"Comprime este texto de {palabras_regla} a ~{target_regla} palabras. "
                    f"Preserva cifras, nombres de campos y tablas. Elimina redundancias.\n\n"
                    f"{f['explicacion']}"
                )},
            ]

            res = _llamar_agente(agente_cfg, msgs, temperatura=0.1, max_tokens=500)
            if not res.get('ok') or not res.get('texto'):
                continue

            texto_nuevo = res['texto'].strip()
            palabras_nuevas = len(texto_nuevo.split())

            if palabras_nuevas < palabras_regla * 0.9:
                conn = get_local_conn()
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE ia_logica_negocio SET explicacion=%s, palabras=%s WHERE id=%s",
                        (texto_nuevo, palabras_nuevas, f['id'])
                    )
                conn.commit()
                conn.close()
                total_palabras -= (palabras_regla - palabras_nuevas)
                actualizadas += 1

        if actualizadas > 0:
            notificar(
                f"🗜️ <b>Lógica depurada</b>\n"
                f"{actualizadas} reglas comprimidas → ~{total_palabras} palabras\n"
                f"Ninguna regla eliminada"
            )
    except Exception:
        pass


def _extraer_guardado_json(respuesta: str) -> dict | None:
    """Intenta extraer {"guardar": {"concepto":..., "keywords":..., "explicacion":...}} de la respuesta."""
    import json as _json
    for pattern in [
        r'\{[^{}]*"guardar"\s*:\s*\{[^{}]+\}[^{}]*\}',
        r'```json\s*(\{[^`]+\})\s*```',
    ]:
        m = re.search(pattern, respuesta, re.DOTALL | re.IGNORECASE)
        if m:
            try:
                obj = _json.loads(m.group(1) if m.lastindex else m.group(0))
                g = obj.get('guardar', obj)
                if g.get('concepto') and g.get('explicacion'):
                    return {
                        'concepto': str(g['concepto']).strip()[:100],
                        'keywords': str(g.get('keywords', '')).strip()[:500],
                        'explicacion': str(g['explicacion']).strip(),
                    }
            except Exception:
                continue
    return None


def procesar_bloque_aprendizaje(respuesta: str, empresa: str):
    """
    Detecta aprendizaje en la respuesta del agente.
    Soporta dos formatos:
      1. JSON: {"guardar": {"concepto":..., "keywords":..., "explicacion":...}}
      2. Etiquetas: [GUARDAR_NEGOCIO]...[/GUARDAR_NEGOCIO]
    """
    # Intentar JSON primero (más robusto)
    datos_json = _extraer_guardado_json(respuesta)
    if datos_json:
        concepto_txt = datos_json['concepto']
        keywords_txt = datos_json['keywords']
        explicacion_txt = datos_json['explicacion']
    else:
        # Fallback: regex tolerante
        match = re.search(
            r'\[GUARDAR[_ ]NEGOCIO\](.*?)\[/GUARDAR[_ ]NEGOCIO\]',
            respuesta, re.DOTALL | re.IGNORECASE
        )
        if not match:
            return

        try:
            bloque = match.group(1).strip()
            concepto  = re.search(r'concepto\s*:\s*(.+)', bloque, re.IGNORECASE)
            keywords  = re.search(r'keywords\s*:\s*(.+)', bloque, re.IGNORECASE)
            explicacion = re.search(r'explicacion\s*:\s*([\s\S]+)', bloque, re.IGNORECASE)

            if not (concepto and keywords and explicacion):
                return

            concepto_txt    = concepto.group(1).strip()[:100]
            keywords_txt    = keywords.group(1).strip()[:500]
            explicacion_txt = explicacion.group(1).strip()

            for tag in ['concepto', 'keywords']:
                idx = explicacion_txt.lower().find(f'\n{tag}')
                if idx > 0:
                    explicacion_txt = explicacion_txt[:idx].strip()
        except Exception:
            return

    try:
        palabras = len(explicacion_txt.split())

        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ia_logica_negocio SET activo=0 WHERE empresa=%s AND concepto=%s",
                (empresa, concepto_txt)
            )
            cur.execute("""
                INSERT INTO ia_logica_negocio
                (empresa, concepto, explicacion, keywords, siempre_presente, palabras, creado_por)
                VALUES (%s, %s, %s, %s, 0, %s, %s)
            """, (empresa, concepto_txt, explicacion_txt, keywords_txt, palabras, 'usuario-aprendizaje'))
        conn.commit()
        conn.close()

        notificar(
            f"🧠 <b>Nueva lógica de negocio aprendida</b>\n"
            f"Concepto: <i>{concepto_txt}</i>\n"
            f"Palabras: {palabras}"
        )

        threading.Thread(target=depurar_logica_negocio, args=(empresa,), daemon=True).start()

    except Exception:
        pass


def extraer_palabras_clave(texto: str) -> str:
    """Extrae palabras relevantes de una pregunta para indexar ejemplos SQL."""
    palabras_negocio = [
        'ventas', 'venta', 'facturas', 'factura', 'remisiones', 'remision',
        'clientes', 'cliente', 'productos', 'producto', 'mes', 'dia', 'hoy',
        'ayer', 'semana', 'año', 'canal', 'margen', 'utilidad', 'costo',
        'consignacion', 'pendiente', 'top', 'mejor', 'mayor', 'menor',
        'comparar', 'comparame', 'vs', 'resumen', 'total', 'cuanto', 'cuantos'
    ]
    texto_lower = texto.lower()
    encontradas = [p for p in palabras_negocio if p in texto_lower]
    return ','.join(encontradas[:10])


def guardar_ejemplo_sql(empresa: str, pregunta: str, sql: str):
    """Guarda un Q→SQL exitoso para auto-mejora progresiva del agente."""
    try:
        tablas_raw = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, re.IGNORECASE)
        tablas = [t for par in tablas_raw for t in par if t]
        tablas_str = ','.join(set(tablas))[:500]
        palabras = extraer_palabras_clave(pregunta)
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ia_ejemplos_sql (empresa, pregunta, sql_generado, tablas_usadas, palabras_clave)
                VALUES (%s, %s, %s, %s, %s)
            """, (empresa, pregunta[:500], sql[:2000], tablas_str, palabras))
            ejemplo_id = cur.lastrowid
            conn.commit()
        conn.close()
        threading.Thread(
            target=embeddings_module.guardar_embedding,
            args=(ejemplo_id, pregunta),
            daemon=True
        ).start()
    except Exception:
        pass


def _incrementar_uso_ejemplos(ids: list):
    """Incrementa veces_usado y actualiza ultima_vez para los ejemplos recuperados."""
    if not ids:
        return
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(ids))
            cur.execute(
                f"UPDATE ia_ejemplos_sql SET veces_usado = veces_usado + 1, "
                f"ultima_vez = NOW() WHERE id IN ({placeholders})", ids
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def obtener_ejemplos_dinamicos(empresa: str, pregunta: str, n: int = 3) -> str:
    """
    Recupera los N ejemplos Q→SQL más relevantes para la pregunta actual.
    Estrategia: embeddings semánticos (principal) → keywords LIKE (fallback).
    """
    try:
        filas = embeddings_module.buscar_ejemplos_semanticos(empresa, pregunta, n)
        if filas:
            _incrementar_uso_ejemplos([f['id'] for f in filas])
            ejemplos = '\n\n'.join([
                f"Pregunta: {f['pregunta']}\nSQL:\n{f['sql_generado']}"
                for f in filas
            ])
            return f"\n\nEJEMPLOS DE CONSULTAS ANTERIORES EXITOSAS (referencia):\n{ejemplos}"
    except Exception:
        pass

    try:
        palabras = extraer_palabras_clave(pregunta).split(',')
        if not palabras:
            return ''
        condicion = ' OR '.join([f"palabras_clave LIKE %s" for _ in palabras])
        params = [f'%{p}%' for p in palabras] + [empresa, n]
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, pregunta, sql_generado FROM ia_ejemplos_sql
                WHERE ({condicion}) AND empresa = %s
                ORDER BY veces_usado DESC, ultima_vez DESC
                LIMIT %s
            """, params)
            filas = cur.fetchall()
        conn.close()
        if not filas:
            return ''
        _incrementar_uso_ejemplos([f['id'] for f in filas])
        ejemplos = '\n\n'.join([
            f"Pregunta: {f['pregunta']}\nSQL:\n{f['sql_generado']}"
            for f in filas
        ])
        return f"\n\nEJEMPLOS DE CONSULTAS ANTERIORES EXITOSAS (referencia):\n{ejemplos}"
    except Exception:
        return ''


def obtener_logica_negocio(empresa: str, pregunta: str) -> str:
    """
    Recupera fragmentos de lógica de negocio relevantes para la pregunta.
    - siempre_presente=1 → siempre se inyectan
    - otros → se inyectan si alguna keyword aparece en la pregunta
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT concepto, explicacion, keywords, siempre_presente "
                "FROM ia_logica_negocio WHERE empresa=%s AND activo=1",
                (empresa,)
            )
            fragmentos = cur.fetchall()
        conn.close()

        if not fragmentos:
            return ''

        pregunta_lower = pregunta.lower()
        relevantes = []
        for f in fragmentos:
            if f.get('siempre_presente'):
                relevantes.append(f)
                continue
            keywords = [k.strip().lower() for k in (f.get('keywords') or '').split(',') if k.strip()]
            if any(kw in pregunta_lower for kw in keywords):
                relevantes.append(f)

        if not relevantes:
            return ''

        partes = [f"### {f['concepto']}\n{f['explicacion']}" for f in relevantes]
        return '<logica_negocio>\n' + '\n\n'.join(partes) + '\n</logica_negocio>'
    except Exception:
        return ''


def generar_resumen(resumen_anterior: str, pregunta: str, respuesta: str,
                    empresa: str = 'ori_sil_2') -> str | None:
    """
    Genera el resumen actualizado de conversación.
    Retorna el nuevo resumen como texto plano, o None si falla.
    """
    from .servicio import _cargar_agente, _llamar_agente, _log_aux

    agente_cfg = None
    slug_resumen = get_config_simple('rol_resumen_agente', 'groq-llama')
    cadena_resumen = [slug_resumen] + [s for s in slugs_router() if s != slug_resumen]
    for slug in cadena_resumen:
        cand = _cargar_agente(slug)
        if cand and cand.get('api_key'):
            agente_cfg = cand
            break
    if not agente_cfg:
        return None

    contexto_previo = f'Resumen previo:\n{resumen_anterior}\n\n' if resumen_anterior else ''
    prompt = (
        f'{contexto_previo}'
        f'Nuevo intercambio:\n'
        f'Usuario: {pregunta}\n'
        f'Asistente: {respuesta}\n\n'
        f'Actualiza el resumen de la conversación en máximo 600 palabras. '
        f'Incluye: datos numéricos mencionados, preguntas ya respondidas, '
        f'nombres de clientes/productos/períodos, decisiones o conclusiones. '
        f'Solo el resumen, sin etiquetas ni explicaciones.'
    )
    msgs = [
        {'role': 'system', 'content': 'Eres un asistente que genera resúmenes concisos de conversaciones.'},
        {'role': 'user',   'content': prompt},
    ]
    res = _llamar_agente(agente_cfg, msgs, temperatura=0.1, max_tokens=900)
    _log_aux(agente_cfg, res, 'resumen', '(resumen conversación)', empresa)
    if res['ok'] and res.get('texto'):
        return res['texto'].strip()
    return None


def registrar_feedback(
    empresa: str,
    tipo: str,
    pregunta: str = None,
    sql_fallido: str = None,
    sql_correcto: str = None,
    error_original: str = None,
    notas: str = None,
    log_id: int = None,
):
    """
    Registra feedback en ia_feedback para mejora continua.
    Tipos: sql_error, respuesta_mala, sql_bueno, correccion.
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ia_feedback
                (empresa, log_id, tipo, pregunta, sql_fallido, sql_correcto, error_original, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (empresa, log_id, tipo, pregunta, sql_fallido, sql_correcto, error_original, notas))
        conn.commit()
        conn.close()
    except Exception:
        pass
