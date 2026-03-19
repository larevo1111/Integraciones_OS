"""
Orquestador principal del servicio de IA.
Expone la función consultar() que es el punto de entrada único.
"""
import json
import math
import threading
import time
from collections import defaultdict, deque
from .config import get_local_conn
from . import contexto, ejecutor_sql, formateador, esquema, rag as rag_module
from . import embeddings as embeddings_module
from .proveedores import openai_compat, google, anthropic_prov
import os, requests as _requests


# ── Notificaciones Telegram (bot de alertas) ──────────────────────────────────

def _notificar(mensaje: str):
    """Envía una alerta al bot de notificaciones del sistema. Falla silenciosamente."""
    try:
        token    = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id  = os.getenv('TELEGRAM_NOTIF_CHAT_ID')
        if not token or not chat_id:
            return
        _requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'HTML'},
            timeout=5
        )
    except Exception:
        pass


_alertas_enviadas = {}  # clave → timestamp último envío (anti-spam 1h)

def _verificar_gasto_y_notificar(empresa: str, costo_llamada: float):
    """Verifica gasto diario y por hora — notifica si supera umbrales."""
    try:
        ahora = time.time()
        conn  = get_local_conn()
        with conn.cursor() as cur:
            # Gasto del día
            cur.execute(
                "SELECT COALESCE(SUM(costo_usd),0) AS total FROM ia_logs "
                "WHERE empresa=%s AND DATE(created_at)=CURDATE()", (empresa,)
            )
            gasto_dia = float(cur.fetchone()['total'])
            # Gasto última hora
            cur.execute(
                "SELECT COALESCE(SUM(costo_usd),0) AS total FROM ia_logs "
                "WHERE empresa=%s AND created_at >= NOW() - INTERVAL 1 HOUR", (empresa,)
            )
            gasto_hora = float(cur.fetchone()['total'])
        conn.close()

        def _alerta_si(clave, condicion, msg):
            ultimo = _alertas_enviadas.get(clave, 0)
            if condicion and (ahora - ultimo) > 3600:
                _notificar(msg)
                _alertas_enviadas[clave] = ahora

        _alerta_si('gasto_dia_2',  gasto_dia  >= 2.0,
            f"💸 <b>Gasto Gemini alto hoy</b>: ${gasto_dia:.2f} USD (~COP {gasto_dia*4200:,.0f})\n"
            f"Límite sugerido: $2 USD/día. Revisa si hay uso excesivo.")
        _alerta_si('gasto_hora_05', gasto_hora >= 0.5,
            f"⚡ <b>Gasto elevado última hora</b>: ${gasto_hora:.2f} USD\n"
            f"Posible pico de consultas o bucle de llamadas.")
    except Exception:
        pass


# ── Rate limiter por usuario — sliding window in-memory ──────────────────────
# Clave: "{empresa}:{usuario_id}" → ventanas de timestamps por intervalo

_rl_lock    = threading.Lock()
_rl_windows = defaultdict(lambda: {'1s': deque(), '10s': deque(), '60s': deque()})

def _limpiar_ventana(dq: deque, ventana_seg: float, ahora: float):
    while dq and (ahora - dq[0]) > ventana_seg:
        dq.popleft()

def verificar_rate_usuario(usuario_id: str, empresa: str) -> dict | None:
    """
    Sliding window rate limit por usuario.
    Límites leídos de ia_config: rate_usuario_rps / rp10s / rpm.
    Devuelve None si OK, o dict {error, retry_after} si debe bloquearse.
    No falla aunque la BD no responda.
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT clave, valor FROM ia_config "
                "WHERE clave IN ('rate_usuario_rps','rate_usuario_rp10s','rate_usuario_rpm')"
            )
            cfg = {r['clave']: int(r['valor']) for r in cur.fetchall()}
        conn.close()
    except Exception:
        return None  # Si no puede leer config, deja pasar

    lim_1s  = cfg.get('rate_usuario_rps',   1)
    lim_10s = cfg.get('rate_usuario_rp10s', 3)
    lim_60s = cfg.get('rate_usuario_rpm',  15)

    clave = f"{empresa}:{usuario_id}"
    ahora = time.monotonic()

    with _rl_lock:
        w = _rl_windows[clave]

        _limpiar_ventana(w['1s'],  1.0,  ahora)
        _limpiar_ventana(w['10s'], 10.0, ahora)
        _limpiar_ventana(w['60s'], 60.0, ahora)

        # Verificar ANTES de registrar — más restrictivo primero (1s → 10s → 60s)
        if len(w['1s']) >= lim_1s:
            retry = math.ceil(1.0 - (ahora - w['1s'][0])) + 1
            return {
                'error': (
                    f"Solicitud rechazada: límite de {lim_1s} por segundo alcanzado. "
                    f"Intente en {retry} segundo{'s' if retry != 1 else ''}."
                ),
                'retry_after': retry,
            }

        if len(w['10s']) >= lim_10s:
            retry = math.ceil(10.0 - (ahora - w['10s'][0])) + 1
            return {
                'error': (
                    f"Solicitud rechazada: límite de {lim_10s} en 10 segundos alcanzado. "
                    f"Intente en {retry} segundos."
                ),
                'retry_after': retry,
            }

        if len(w['60s']) >= lim_60s:
            retry = math.ceil(60.0 - (ahora - w['60s'][0])) + 1
            return {
                'error': (
                    f"Solicitud rechazada: límite de {lim_60s} por minuto alcanzado. "
                    f"Intente en {retry} segundos."
                ),
                'retry_after': retry,
            }

        # Registrar el request en las 3 ventanas
        w['1s'].append(ahora)
        w['10s'].append(ahora)
        w['60s'].append(ahora)

    return None  # OK


# ── Seguridad: verificación de límites de costo y circuit breaker ─────────────

def _get_config(conn, clave: str, default):
    with conn.cursor() as cur:
        cur.execute("SELECT valor FROM ia_config WHERE clave = %s", (clave,))
        row = cur.fetchone()
    return row['valor'] if row else default


def verificar_limites(agente_slug: str, empresa: str) -> dict | None:
    """
    Verifica 3 capas de protección antes de llamar a la API externa.
    Devuelve None si todo OK, o dict {error: str} si hay que bloquear.
    """
    conn = get_local_conn()
    try:
        # — Config global —
        limite_costo = float(_get_config(conn, 'limite_costo_dia_usd', '0'))
        cb_errores   = int(_get_config(conn, 'circuit_breaker_errores', '5'))
        cb_ventana   = int(_get_config(conn, 'circuit_breaker_ventana_min', '10'))

        with conn.cursor() as cur:

            # CAPA 1: Costo diario global (toda la empresa)
            if limite_costo > 0:
                cur.execute(
                    "SELECT COALESCE(SUM(costo_usd), 0) AS total FROM ia_logs "
                    "WHERE empresa = %s AND DATE(created_at) = CURDATE()",
                    (empresa,)
                )
                costo_hoy = float(cur.fetchone()['total'])
                if costo_hoy >= limite_costo:
                    return {
                        'error': (
                            f"⛔ Límite de gasto diario alcanzado "
                            f"(${costo_hoy:.4f} / ${limite_costo:.2f} USD). "
                            f"Reinicia mañana o ajusta el límite en ia_config."
                        )
                    }

            # CAPA 2: RPD por agente (rate_limit_rpd de ia_agentes)
            cur.execute(
                "SELECT rate_limit_rpd FROM ia_agentes WHERE slug = %s",
                (agente_slug,)
            )
            agente_row = cur.fetchone()
            rpd = agente_row['rate_limit_rpd'] if agente_row else None
            if rpd:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM ia_logs "
                    "WHERE agente_slug = %s AND DATE(created_at) = CURDATE()",
                    (agente_slug,)
                )
                llamadas_hoy = cur.fetchone()['n']
                if llamadas_hoy >= rpd:
                    return {
                        'error': (
                            f"⛔ Agente '{agente_slug}' alcanzó su límite diario "
                            f"({llamadas_hoy}/{rpd} llamadas). "
                            f"Usa otro agente o espera mañana."
                        )
                    }

            # CAPA 3: Circuit breaker — errores recientes
            cur.execute(
                "SELECT COUNT(*) AS n FROM ia_logs "
                "WHERE agente_slug = %s "
                "  AND error IS NOT NULL "
                "  AND created_at >= NOW() - INTERVAL %s MINUTE",
                (agente_slug, cb_ventana)
            )
            errores_recientes = cur.fetchone()['n']
            if errores_recientes >= cb_errores:
                return {
                    'error': (
                        f"⛔ Agente '{agente_slug}' suspendido automáticamente "
                        f"({errores_recientes} errores en los últimos {cb_ventana} min). "
                        f"Revisa el agente o espera {cb_ventana} minutos."
                    )
                }

        return None  # Todo OK

    except Exception as e:
        # Si la verificación falla, dejar pasar (no bloquear por error de seguridad)
        return None
    finally:
        conn.close()

def _generar_resumen_groq(resumen_anterior: str, pregunta: str, respuesta: str) -> str | None:
    """
    Genera el resumen actualizado de conversación usando Groq (rápido, gratis).
    El agente principal ya no necesita incluir el resumen en su respuesta.
    Retorna el nuevo resumen como texto plano, o None si falla.
    """
    agente_cfg = None
    for slug in ('groq-llama', 'cerebras-llama', 'gemini-flash-lite'):
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
    if res['ok'] and res.get('texto'):
        return res['texto'].strip()
    return None


def _depurar_logica_negocio(empresa: str):
    """
    Bot depurador: si la lógica de negocio supera 800 palabras totales,
    llama a Groq para comprimirla a ~600 palabras preservando precisión exacta.
    Se llama en background después de guardar un nuevo fragmento.
    """
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, concepto, explicacion FROM ia_logica_negocio "
                "WHERE empresa=%s AND activo=1 ORDER BY siempre_presente DESC, id",
                (empresa,)
            )
            fragmentos = cur.fetchall()
        conn.close()

        texto_total = '\n\n'.join(f"### {f['concepto']}\n{f['explicacion']}" for f in fragmentos)
        total_palabras = len(texto_total.split())

        if total_palabras <= 800:
            return  # No necesita depuración

        # Buscar agente para comprimir — Groq primero, suplentes si falla
        agente_cfg = None
        for slug_dep in ('groq-llama', 'cerebras-llama', 'gemini-flash-lite', 'gemini-flash'):
            cand = _cargar_agente(slug_dep)
            if cand and cand.get('api_key'):
                agente_cfg = cand
                break
        if not agente_cfg:
            return

        prompt = (
            f"El siguiente es el documento de lógica de negocio de Origen Silvestre ({total_palabras} palabras). "
            f"Comprímelo a máximo 600 palabras.\n"
            f"REGLAS CRÍTICAS:\n"
            f"- NUNCA elimines ni cambies cifras, porcentajes ni reglas exactas\n"
            f"- NUNCA cambies nombres de campos, tablas o agentes\n"
            f"- Elimina redundancias y ejemplos repetidos\n"
            f"- Mantén la estructura ### Concepto\n"
            f"- Solo devuelve el texto comprimido, sin explicaciones\n\n"
            f"{texto_total}"
        )
        msgs = [
            {'role': 'system', 'content': 'Eres un asistente que comprime documentos técnicos preservando toda la precisión.'},
            {'role': 'user',   'content': prompt},
        ]
        res = _llamar_agente(agente_cfg, msgs, temperatura=0.1, max_tokens=900)
        if not res['ok'] or not res.get('texto'):
            # Suplente si el primero falló
            for slug_dep in ('groq-llama', 'cerebras-llama', 'gemini-flash-lite', 'gemini-flash'):
                if agente_cfg and agente_cfg.get('slug') == slug_dep:
                    continue
                cand = _cargar_agente(slug_dep)
                if cand and cand.get('api_key'):
                    res = _llamar_agente(cand, msgs, temperatura=0.1, max_tokens=900)
                    if res['ok'] and res.get('texto'):
                        agente_cfg = cand
                        break
            if not res['ok'] or not res.get('texto'):
                return

        texto_comprimido = res['texto'].strip()
        palabras_nuevas = len(texto_comprimido.split())

        # Reemplazar: marcar todos como inactivos y crear uno nuevo consolidado
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE ia_logica_negocio SET activo=0 WHERE empresa=%s", (empresa,))
            cur.execute("""
                INSERT INTO ia_logica_negocio (empresa, concepto, explicacion, keywords, siempre_presente, palabras, creado_por)
                VALUES (%s, %s, %s, %s, 1, %s, %s)
            """, (empresa, 'Lógica de negocio consolidada', texto_comprimido,
                  'negocio,tarifa,agente,canal,cliente,venta,produccion', palabras_nuevas, 'depurador-auto'))
        conn.commit()
        conn.close()
        _notificar(f"🗜️ <b>Lógica de negocio depurada</b>\n{total_palabras} → {palabras_nuevas} palabras")
    except Exception:
        pass


def _procesar_bloque_aprendizaje(respuesta: str, empresa: str):
    """
    Detecta [GUARDAR_NEGOCIO]...[/GUARDAR_NEGOCIO] en la respuesta del agente.
    Si lo encuentra, guarda el fragmento en ia_logica_negocio y llama al depurador.
    Falla silenciosamente para no interrumpir la respuesta al usuario.
    """
    import re
    match = re.search(
        r'\[GUARDAR_NEGOCIO\](.*?)\[/GUARDAR_NEGOCIO\]',
        respuesta, re.DOTALL | re.IGNORECASE
    )
    if not match:
        return

    try:
        bloque = match.group(1).strip()
        # Parsear concepto, keywords, explicacion
        concepto  = re.search(r'concepto\s*:\s*(.+)', bloque, re.IGNORECASE)
        keywords  = re.search(r'keywords\s*:\s*(.+)', bloque, re.IGNORECASE)
        explicacion = re.search(r'explicacion\s*:\s*([\s\S]+)', bloque, re.IGNORECASE)

        if not (concepto and keywords and explicacion):
            return

        concepto_txt    = concepto.group(1).strip()[:100]
        keywords_txt    = keywords.group(1).strip()[:500]
        explicacion_txt = explicacion.group(1).strip()

        # Limpiar si explicacion capturó keywords o concepto al final
        for tag in ['concepto', 'keywords']:
            idx = explicacion_txt.lower().find(f'\n{tag}')
            if idx > 0:
                explicacion_txt = explicacion_txt[:idx].strip()

        palabras = len(explicacion_txt.split())

        conn = get_local_conn()
        with conn.cursor() as cur:
            # Si ya existe un fragmento con el mismo concepto, desactivarlo
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

        _notificar(
            f"🧠 <b>Nueva lógica de negocio aprendida</b>\n"
            f"Concepto: <i>{concepto_txt}</i>\n"
            f"Palabras: {palabras}"
        )

        # Depurar si supera el límite
        import threading
        threading.Thread(target=_depurar_logica_negocio, args=(empresa,), daemon=True).start()

    except Exception:
        pass


def _extraer_palabras_clave(texto: str) -> str:
    """Extrae palabras relevantes de una pregunta para indexar ejemplos SQL."""
    import re
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


def _guardar_ejemplo_sql(empresa: str, pregunta: str, sql: str):
    """Guarda un Q→SQL exitoso para auto-mejora progresiva del agente."""
    try:
        import re
        tablas_raw = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, re.IGNORECASE)
        tablas = [t for par in tablas_raw for t in par if t]
        tablas_str = ','.join(set(tablas))[:500]
        palabras = _extraer_palabras_clave(pregunta)
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ia_ejemplos_sql (empresa, pregunta, sql_generado, tablas_usadas, palabras_clave)
                VALUES (%s, %s, %s, %s, %s)
            """, (empresa, pregunta[:500], sql[:2000], tablas_str, palabras))
            ejemplo_id = cur.lastrowid
            conn.commit()
        conn.close()
        # Generar y guardar embedding en background (no bloquea la respuesta)
        import threading
        threading.Thread(
            target=embeddings_module.guardar_embedding,
            args=(ejemplo_id, pregunta),
            daemon=True
        ).start()
    except Exception:
        pass  # No fallar si no se puede guardar


def _obtener_ejemplos_dinamicos(empresa: str, pregunta: str, n: int = 3) -> str:
    """
    Recupera los N ejemplos Q→SQL más relevantes para la pregunta actual.
    Estrategia: embeddings semánticos (principal) → keywords LIKE (fallback).
    """
    # Intento 1: búsqueda semántica por embeddings
    try:
        filas = embeddings_module.buscar_ejemplos_semanticos(empresa, pregunta, n)
        if filas:
            ejemplos = '\n\n'.join([
                f"Pregunta: {f['pregunta']}\nSQL:\n{f['sql_generado']}"
                for f in filas
            ])
            return f"\n\nEJEMPLOS DE CONSULTAS ANTERIORES EXITOSAS (referencia):\n{ejemplos}"
    except Exception:
        pass

    # Fallback: búsqueda por palabras clave (LIKE) — funciona aunque no haya embeddings
    try:
        palabras = _extraer_palabras_clave(pregunta).split(',')
        if not palabras:
            return ''
        condicion = ' OR '.join([f"palabras_clave LIKE %s" for _ in palabras])
        params = [f'%{p}%' for p in palabras] + [empresa, n]
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT pregunta, sql_generado FROM ia_ejemplos_sql
                WHERE ({condicion}) AND empresa = %s
                ORDER BY veces_usado DESC, ultima_vez DESC
                LIMIT %s
            """, params)
            filas = cur.fetchall()
        conn.close()
        if not filas:
            return ''
        ejemplos = '\n\n'.join([
            f"Pregunta: {f['pregunta']}\nSQL:\n{f['sql_generado']}"
            for f in filas
        ])
        return f"\n\nEJEMPLOS DE CONSULTAS ANTERIORES EXITOSAS (referencia):\n{ejemplos}"
    except Exception:
        return ''


_CACHE_COBERTURA: dict = {}   # {empresa: (timestamp, texto)}
_CACHE_COBERTURA_TTL = 3600  # 1 hora


def _obtener_cobertura_tablas(empresa: str = 'ori_sil_2') -> str:
    """
    Calcula y devuelve un bloque de texto con la cobertura real de datos
    de las tablas principales: rango de fechas, total de registros,
    días distintos con ventas, y última actualización.

    Se cachea 1 hora para no hacer queries en cada llamada.
    Se inyecta en el system prompt (Capa 0) para que el modelo sepa
    con qué datos cuenta antes de razonar — evita "no hay datos" falsos
    cuando en realidad el rango correcto sí tiene información.
    """
    import time
    ahora = time.time()
    if empresa in _CACHE_COBERTURA:
        ts, texto = _CACHE_COBERTURA[empresa]
        if ahora - ts < _CACHE_COBERTURA_TTL:
            return texto

    tablas_config = [
        {
            'tabla': 'zeffi_facturas_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "fecha_de_anulacion IS NULL",
            'etiqueta': 'Facturas de venta',
        },
        {
            'tabla': 'zeffi_remisiones_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "fecha_de_anulacion IS NULL",
            'etiqueta': 'Remisiones de venta',
        },
        {
            'tabla': 'zeffi_ordenes_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "vigencia = 'Vigente'",
            'etiqueta': 'Órdenes activas (consignación)',
        },
    ]

    lineas = ['Cobertura de datos disponibles en la base de datos:']
    try:
        from .config import get_hostinger_conn
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            for t in tablas_config:
                try:
                    where = f"WHERE {t['filtro']}" if t['filtro'] else ''
                    cur.execute(f"""
                        SELECT
                            MIN(DATE({t['col_fecha']}))                     AS fecha_min,
                            MAX(DATE({t['col_fecha']}))                     AS fecha_max,
                            COUNT(*)                                        AS total_registros,
                            COUNT(DISTINCT DATE({t['col_fecha']}))          AS dias_con_datos
                        FROM {t['tabla']}
                        {where}
                    """)
                    row = cur.fetchone()
                    if row and row.get('fecha_max'):
                        lineas.append(
                            f"  {t['etiqueta']}: {row['fecha_min']} → {row['fecha_max']} "
                            f"({row['total_registros']:,} registros en {row['dias_con_datos']:,} días distintos)"
                        )
                except Exception:
                    pass

            # Meses disponibles en resúmenes
            try:
                cur.execute(
                    "SELECT MIN(mes) AS desde, MAX(mes) AS hasta, COUNT(*) AS n "
                    "FROM resumen_ventas_facturas_mes"
                )
                row = cur.fetchone()
                if row and row.get('hasta'):
                    lineas.append(
                        f"  Resúmenes mensuales: {row['desde']} → {row['hasta']} ({row['n']} meses)"
                    )
            except Exception:
                pass

        conn.close()
    except Exception:
        return ''

    if len(lineas) <= 1:
        return ''

    lineas.append(
        'Nota: la ausencia de datos en un día específico puede significar que ese día '
        'no hubo ventas (fin de semana, feriado, o simplemente sin actividad). '
        'En ese caso, considera consultar la semana completa o el acumulado del período.'
    )

    texto = '\n'.join(lineas)
    _CACHE_COBERTURA[empresa] = (ahora, texto)
    return texto


def _obtener_fecha_maxima(sql: str) -> str:
    """
    Dado un SQL, detecta las tablas consultadas y obtiene la fecha máxima
    real disponible. Se usa para informar al LLM cuándo hay 0 filas.
    """
    try:
        import re
        tablas_raw = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, re.IGNORECASE)
        tablas = [t for par in tablas_raw for t in par if t]
        if not tablas:
            return ''
        # Columnas de fecha comunes en las tablas de Effi
        cols_fecha = ['fecha_de_creacion', 'fecha', 'fecha_factura', 'fecha_remision']
        resultados = []
        conn = get_local_conn()
        with conn.cursor() as cur:
            for tabla in set(tablas):
                for col in cols_fecha:
                    try:
                        cur.execute(f"SELECT MAX({col}) AS max_fecha FROM {tabla}")
                        row = cur.fetchone()
                        if row and row.get('max_fecha'):
                            resultados.append(f"{tabla}.{col}: {row['max_fecha']}")
                            break  # Con una columna de fecha por tabla es suficiente
                    except Exception:
                        continue
        conn.close()
        if resultados:
            return f"Fechas más recientes en las tablas consultadas:\n" + '\n'.join(resultados) + '\n\n'
        return ''
    except Exception:
        return ''


def _nivel_usuario(usuario_id: str, empresa: str) -> int:
    """Obtiene el nivel del usuario desde ia_usuarios. Default 1 si no existe."""
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT nivel FROM ia_usuarios WHERE email = %s", (usuario_id,))
            row = cur.fetchone()
        conn.close()
        return int(row['nivel']) if row else 1
    except Exception:
        return 1


def _mejor_agente_para_nivel(nivel: int) -> str:
    """Devuelve el slug del mejor agente disponible para el nivel dado."""
    try:
        conn = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug FROM ia_agentes "
                "WHERE activo=1 AND api_key != '' AND nivel_minimo <= %s "
                "ORDER BY nivel_minimo DESC, orden ASC LIMIT 1",
                (nivel,)
            )
            row = cur.fetchone()
        conn.close()
        return row['slug'] if row else 'gemini-flash'
    except Exception:
        return 'gemini-flash'


def consultar(
    pregunta:        str,
    tipo:            str  = None,
    agente:          str  = None,
    usuario_id:      str  = 'anonimo',
    canal:           str  = 'api',
    empresa:         str  = 'ori_sil_2',
    tema:            str  = None,
    conversacion_id: int  = None,
    nombre_usuario:  str  = None,
    contexto_extra:  str  = '',
    cliente:         dict = None,
    imagen_b64:      str  = None,
    imagen_mime:     str  = 'image/jpeg',
) -> dict:
    """
    Punto de entrada único del servicio de IA.

    Args:
        pregunta:        Pregunta o instrucción del usuario.
        tipo:            Slug de ia_tipos_consulta. None = enrutar automáticamente.
        agente:          Slug de ia_agentes. None = usar preferido del tema/tipo.
        usuario_id:      ID del usuario (telegram_id, email, etc.)
        canal:           Canal de origen: telegram, erp, api, script.
        empresa:         Empresa del caller. Filtra RAG y temas (default: 'ori_sil_2').
        tema:            Slug del tema (comercial, finanzas, etc.). None = enrutar automáticamente.
        conversacion_id: ID de conversación existente. None = buscar por usuario+canal.
        nombre_usuario:  Nombre para personalizar respuestas.
        contexto_extra:  Contexto adicional libre — pantalla activa del ERP, datos clave, etc.

    Returns:
        {
            "ok":              bool,
            "conversacion_id": int,
            "respuesta":       str,
            "formato":         str,    # texto|tabla|texto_tabla|json|documento
            "tabla":           dict|None,
            "sql":             str|None,
            "agente":          str,
            "tema":            str,
            "tokens":          {"in": int, "out": int},
            "costo_usd":       float,
            "pasos":           list[str],
            "log_id":          int|None,
            "error":           str|None
        }
    """
    t_inicio = time.time()
    pasos_ejecutados = []

    # ── 0. Rate limit por usuario (sliding window in-memory) ─────────
    rl = verificar_rate_usuario(usuario_id, empresa)
    if rl:
        return {
            'ok': False, 'conversacion_id': None,
            'respuesta': rl['error'],
            'formato': 'texto', 'tabla': None, 'sql_generado': None,
            'agente': None, 'tema': tema,
            'tokens': {'in': 0, 'out': 0}, 'costo_usd': 0.0,
            'pasos': [], 'log_id': None,
            'error': rl['error'], 'retry_after': rl['retry_after'],
        }

    # ── 1. Obtener conversación ───────────────────────────────────────
    conv = contexto.obtener_o_crear(usuario_id, canal, conversacion_id, nombre_usuario)
    conv_id = conv['id']
    resumen_anterior = conv.get('resumen') or ''

    # ── 2. Enrutar: detectar tipo, tema y si se necesita SQL nuevo ───────
    requiere_sql = True  # default conservador
    if not tipo or not tema:
        # Pasar resumen + historial reciente para que el enrutador asigne el tema
        # correctamente basándose en el contexto completo de la conversación
        historial_ctx = contexto.obtener_mensajes_recientes_formateados(conv)
        contexto_enrutador = (f'Resumen de la conversación:\n{resumen_anterior}\n\n{historial_ctx}'
                              if resumen_anterior else historial_ctx)

        # Agregar resumen del caché SQL para que el router razone si hay datos suficientes
        _cache_sql = contexto.leer_cache_sql(conv)
        if _cache_sql:
            _muestra = _cache_sql['datos'][:3] if _cache_sql.get('datos') else []
            contexto_enrutador += (
                f"\n\nÚltimo resultado SQL disponible (caché):"
                f"\nConsulta origen: \"{_cache_sql.get('pregunta','')}\""
                f"\nColumnas: {', '.join(_cache_sql.get('columnas', []))}"
                f"\nFilas totales: {_cache_sql.get('n_filas', 0)}"
                f"\nMuestra (primeras 3): {json.dumps(_muestra, ensure_ascii=False, default=str)}"
            )

        # Detección pre-router: si el bot acaba de preguntar "¿Lo guardo?" y el usuario confirma
        # → forzar conversacion para que el agente procese la confirmación y emita [GUARDAR_NEGOCIO]
        _confirmaciones = {'sí', 'si', 'dale', 'ok', 'sip', 'claro', 'correcto', 'perfecto',
                           'guardalo', 'guárdalo', 'adelante', 'exacto', 'así', 'asi', 'yes',
                           'sí guárdalo', 'si guardalo', 'sí guárdalo', 'dale guárdalo',
                           'sí dale', 'claro guárdalo', 'ok guárdalo'}
        import re as _re
        _pregunta_lower = _re.sub(r'[.,!¡¿?;:]+$', '', pregunta.strip().lower()).strip()
        if _pregunta_lower in _confirmaciones and historial_ctx and \
                'lo guardo en mi memoria de negocio' in historial_ctx.lower():
            tipo = 'conversacion'
            tema = tema or 'general'
            requiere_sql = False

        # Detección pre-router: si el usuario pide EXPLÍCITAMENTE buscar en internet
        # → forzar busqueda_web sin pasar por el router (que puede equivocarse con el contexto)
        _intento_internet = [
            'busca en internet', 'buscar en internet', 'consulta en internet',
            'consultes en internet', 'búscalo en internet', 'consúltalo en internet',
            'busca en la web', 'consulta en la web', 'búscalo en la web',
            'busca en google', 'googlealo', 'googléalo', 'míralo en internet',
            'búscalo online', 'busca online',
        ]
        _pregunta_norm = pregunta.lower()
        if not tipo and any(kw in _pregunta_norm for kw in _intento_internet):
            tipo = 'busqueda_web'
            tema = 'general'
            requiere_sql = False

        if not tipo:
            tipo_enrutado, tema_enrutado, requiere_sql = _enrutar(pregunta, empresa, contexto_enrutador)
            tipo = tipo_enrutado
            tema = tema_enrutado
        pasos_ejecutados.append('enrutar')

    # ── 3. Cargar tipo de consulta ────────────────────────────────────
    tipo_cfg = _cargar_tipo(tipo)
    if not tipo_cfg:
        tipo_cfg = _cargar_tipo('analisis_datos')  # fallback

    pasos_del_tipo = tipo_cfg.get('pasos') or ['redactar']
    if isinstance(pasos_del_tipo, str):
        pasos_del_tipo = json.loads(pasos_del_tipo)

    # Si el router decidió que no se necesita SQL nuevo, usar el caché SQL real.
    # Si no hay caché disponible, forzar SQL para no inventar datos.
    cache_sin_sql = None
    if tipo == 'analisis_datos' and not requiere_sql:
        cache_sin_sql = contexto.leer_cache_sql(conv)
        if cache_sin_sql and cache_sin_sql.get('datos'):
            pasos_del_tipo = ['redactar']
            pasos_ejecutados.append('sin_sql')
        else:
            requiere_sql = True  # sin caché → SQL obligatorio

    temperatura = float(tipo_cfg.get('temperatura', 0.3))

    # ── 4. Resolver agente ────────────────────────────────────────────
    # Prioridad: caller > conversación activa > tema preferido > tipo preferido > default
    tema_cfg = rag_module.obtener_tema_por_slug(tema, empresa) if tema else None
    agente_slug = (
        agente
        or conv.get('agente_activo')
        or (tema_cfg.get('agente_preferido') if tema_cfg else None)
        or tipo_cfg.get('agente_preferido')
        or 'gemini-flash-lite'
    )
    agente_cfg = _cargar_agente(agente_slug)
    # Si el agente no existe, no está activo o no tiene API key: buscar el primero disponible
    if not agente_cfg or not agente_cfg.get('activo') or not agente_cfg.get('api_key'):
        conn = get_local_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM ia_agentes WHERE activo = 1 AND api_key != '' ORDER BY orden LIMIT 1"
                )
                agente_cfg = cur.fetchone()
        finally:
            conn.close()
        agente_slug = agente_cfg['slug'] if agente_cfg else 'gemini-flash'

    # ── 4b. Verificar nivel de usuario vs agente ─────────────────────
    nivel_usr = _nivel_usuario(usuario_id, empresa)
    agente_nivel_min = (agente_cfg or {}).get('nivel_minimo', 1) or 1
    if nivel_usr < agente_nivel_min:
        # Redirigir silenciosamente al mejor agente disponible para su nivel
        agente_slug = _mejor_agente_para_nivel(nivel_usr)
        agente_cfg  = _cargar_agente(agente_slug)

    # ── 4d. Agente capa mecánica (generación SQL) ─────────────────────
    # El agente analítico (agente_cfg) interpreta y redacta la respuesta final.
    # El agente mecánico (agente_cfg_sql) genera y corrige SQL — más rápido y barato.
    agente_sql_slug = tipo_cfg.get('agente_sql')
    if agente_sql_slug and agente_sql_slug != agente_slug:
        agente_cfg_sql = _cargar_agente(agente_sql_slug)
        if not agente_cfg_sql or not agente_cfg_sql.get('activo') or not agente_cfg_sql.get('api_key'):
            agente_cfg_sql = agente_cfg  # fallback al agente analítico
    else:
        agente_cfg_sql = agente_cfg

    # ── 4c. Verificar límites de seguridad ────────────────────────────
    bloqueo = verificar_limites(agente_slug, empresa)
    if bloqueo:
        return {
            'ok': False, 'conversacion_id': conv_id,
            'respuesta': bloqueo['error'],
            'formato': 'texto', 'tabla': None, 'sql_generado': None,
            'agente': agente_slug, 'tema': tema,
            'tokens': {'in': 0, 'out': 0}, 'costo_usd': 0.0,
            'pasos': [], 'log_id': None, 'error': bloqueo['error'],
        }

    # ── 5. Construir contexto de sistema (6 capas) ───────────────────
    # CAPA 0: Fecha actual — siempre inyectada.
    from datetime import datetime
    _ahora = datetime.now()
    _dias   = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    _meses  = ['enero','febrero','marzo','abril','mayo','junio',
               'julio','agosto','septiembre','octubre','noviembre','diciembre']
    _fecha_ctx = (
        f"Fecha y hora actuales: {_ahora.strftime('%Y-%m-%d %H:%M')} "
        f"({_dias[_ahora.weekday()]}, {_ahora.day} de {_meses[_ahora.month-1]} de {_ahora.year})"
    )

    # CAPA 0b: Contexto del cliente (si viene en la llamada)
    # Permite que la IA sepa con quién habla y filtre datos por ese cliente.
    _cliente_ctx = ''
    if cliente and isinstance(cliente, dict):
        partes = []
        if cliente.get('nombre'):
            partes.append(f"Nombre: {cliente['nombre']}")
        if cliente.get('identificacion'):
            tipo_id = cliente.get('tipo_id', 'ID')
            partes.append(f"{tipo_id}: {cliente['identificacion']}")
        if cliente.get('telefono'):
            partes.append(f"Teléfono: {cliente['telefono']}")
        if cliente.get('email'):
            partes.append(f"Email: {cliente['email']}")
        if partes:
            _cliente_ctx = 'Cliente que consulta:\n' + '\n'.join(f'  {p}' for p in partes)

    # CAPA 0: Lógica de negocio — siempre presente o activada por keywords
    _logica_negocio = _obtener_logica_negocio(empresa, pregunta)

    # CAPA 1: System prompt base (tema tiene prioridad sobre tipo)
    system_prompt = _fecha_ctx + '\n\n'
    if nombre_usuario:
        system_prompt += f'El usuario que consulta se llama: {nombre_usuario}\n\n'
    if _logica_negocio:
        system_prompt += _logica_negocio + '\n\n'
    if _cliente_ctx:
        system_prompt += _cliente_ctx + '\n\n'
    if tema_cfg and tema_cfg.get('system_prompt'):
        system_prompt += tema_cfg['system_prompt']
    elif tipo_cfg.get('system_prompt'):
        system_prompt += tipo_cfg['system_prompt']

    # CAPA 2: RAG — fragmentos relevantes filtrados por empresa y tema
    # No aplica para imagen (confundiría al modelo visual con texto de negocio)
    tema_id_rag = tema_cfg['id'] if tema_cfg else None
    if tipo_cfg.get('slug') != 'generacion_imagen':
        rag_ctx = rag_module.obtener_contexto_rag(pregunta, empresa, tema_id_rag)
        if rag_ctx:
            system_prompt += f'\n\n{rag_ctx}'

    # CAPA 3: Schema BD — tablas del tema si lo tiene, sino schema completo
    if tipo_cfg.get('requiere_estructura'):
        if tema_cfg and tema_cfg.get('schema_tablas'):
            try:
                tablas_tema = json.loads(tema_cfg['schema_tablas']) if isinstance(tema_cfg['schema_tablas'], str) else tema_cfg['schema_tablas']
                if tablas_tema:
                    ddl = esquema.obtener_ddl(tablas=tablas_tema)
                else:
                    ddl = esquema.obtener_ddl()
            except Exception:
                ddl = esquema.obtener_ddl()
        else:
            ddl = esquema.obtener_ddl()
        system_prompt += f'\n\nEsquema de la base de datos:\n{ddl}'

    # CAPA 4: Resumen comprimido de la conversación (historial antiguo)
    if resumen_anterior:
        system_prompt += f'\n\nResumen de la conversación hasta ahora:\n{resumen_anterior}'

    # CAPA 5: Últimos 5 intercambios verbatim (historial reciente exacto)
    mensajes_recientes_ctx = contexto.obtener_mensajes_recientes_formateados(conv)
    if mensajes_recientes_ctx:
        system_prompt += f'\n\n{mensajes_recientes_ctx}'

    # Contexto extra del caller (instrucciones específicas del canal)
    if contexto_extra:
        system_prompt += f'\n\nContexto adicional: {contexto_extra}'

    # ── 5b. Visión — si viene imagen, extraer texto antes de enrutar ─────────────
    tokens_in_total  = 0
    tokens_out_total = 0
    if imagen_b64:
        agente_vision = google.agente_con_capacidad('vision')
        if agente_vision:
            prompt_vision = (
                "Eres un asistente que analiza documentos e imágenes de negocio. "
                "Extrae toda la información relevante de esta imagen de forma estructurada: "
                "números, nombres, fechas, cantidades, totales, referencias. "
                "Si es un documento, indica el tipo (remisión, factura, conteo, etc.).\n\n"
                f"Pregunta del usuario (si existe): {pregunta if pregunta else '(sin instrucción — describe lo que ves)'}"
            )
            res_vision = google.llamar(
                agente_vision,
                [{'role': 'user', 'content': prompt_vision}],
                temperatura=0.1,
                imagen_b64=imagen_b64,
                imagen_mime=imagen_mime,
            )
            if res_vision.get('ok') and res_vision.get('texto'):
                texto_extraido = res_vision['texto']
                tokens_in_total  += res_vision.get('tokens_in', 0)
                tokens_out_total += res_vision.get('tokens_out', 0)
                # Si la imagen está en blanco o sin contenido útil, responder directo
                sin_contenido = any(p in texto_extraido.lower() for p in [
                    'en blanco', 'blank', 'no hay información', 'no contiene', 'vacía', 'vacío'
                ])
                if sin_contenido and not pregunta:
                    return {
                        'ok': True, 'conversacion_id': conv_id,
                        'respuesta': texto_extraido + '\n\n¿Querías mostrarme algo en particular? Envíame la imagen de nuevo o cuéntame qué necesitas.',
                        'formato': 'texto', 'tabla': None, 'sql_generado': None,
                        'agente': agente_vision.get('slug','gemini-flash'), 'tema': tema,
                        'tokens': {'in': tokens_in_total, 'out': tokens_out_total},
                        'costo_usd': 0.0, 'pasos': ['vision'], 'log_id': None, 'error': None,
                        'imagen_b64': None, 'imagen_mime': None,
                    }
                # Inyectar el texto extraído como contexto para el flujo normal
                pregunta = (
                    f"[Imagen analizada — contenido extraído]\n{texto_extraido}\n\n"
                    f"[Instrucción del usuario]\n{pregunta if pregunta else 'Interpreta esta información y dime qué debo saber o qué puedo consultar.'}"
                )
                system_prompt += "\n\nNota: el usuario envió una imagen. El contenido ya fue extraído y se incluye en su mensaje."
            else:
                pregunta = f"[Error al leer la imagen: {res_vision.get('error','desconocido')}] Pregunta original: {pregunta}"

    # ── 6. Ejecutar pasos ─────────────────────────────────────────────
    sql_generado    = None
    # Si es sin_sql, inyectar datos reales del caché (nunca inventa datos)
    datos_crudos    = cache_sin_sql['datos']    if cache_sin_sql else None
    tabla_resultado = formateador.filas_a_tabla(cache_sin_sql['datos'], cache_sin_sql['columnas']) \
                      if cache_sin_sql else None
    imagen_b64      = None
    imagen_mime     = None
    respuesta_final  = ''
    resumen_nuevo    = None
    error            = None

    try:
        mensajes_base = [{'role': 'system', 'content': system_prompt}]

        for paso in pasos_del_tipo:

            if paso == 'generar_sql':
                pasos_ejecutados.append('generar_sql')
                # Recuperar ejemplos dinámicos de consultas exitosas anteriores
                ejemplos_din = _obtener_ejemplos_dinamicos(empresa, pregunta)
                prompt_sql = (
                    f"Genera el SQL para responder esta pregunta:\n{pregunta}"
                    f"{ejemplos_din}\n\n"
                    f"Responde SOLO con el SQL dentro de un bloque ```sql```. "
                    f"Sin explicaciones adicionales.\n"
                    f"Antes de devolver el SQL, verifica internamente: "
                    f"(1) todas las columnas usadas existen en el esquema, "
                    f"(2) el campo 'mes' se trata como VARCHAR 'YYYY-MM', "
                    f"(3) es compatible con MariaDB. Si algo falla, corrígelo."
                )
                msgs = mensajes_base + [{'role': 'user', 'content': prompt_sql}]
                res = _llamar_agente(agente_cfg_sql, msgs, temperatura=0.1)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                # Fallback general — si el agente SQL falla por cualquier error
                if not res['ok']:
                    slug_fb = tipo_cfg.get('agente_fallback')
                    if slug_fb and slug_fb != agente_cfg_sql.get('slug'):
                        ag_fb = _cargar_agente(slug_fb)
                        if ag_fb:
                            _notificar(
                                f"⚠️ <b>Agente SQL fallback activado</b>\n"
                                f"Principal: <code>{agente_cfg_sql.get('slug')}</code> falló\n"
                                f"Respaldo: <code>{slug_fb}</code>\n"
                                f"Error: {str(res.get('error',''))[:120]}"
                            )
                            res_fb = _llamar_agente(ag_fb, msgs, temperatura=0.1)
                            tokens_in_total  += res_fb.get('tokens_in', 0)
                            tokens_out_total += res_fb.get('tokens_out', 0)
                            if res_fb['ok']:
                                res = res_fb

                if not res['ok']:
                    raise Exception(f"Error generando SQL: {res['error']}")

                sql_generado = formateador.extraer_sql(res['texto'])
                if not sql_generado:
                    # El agente respondió en texto plano sin SQL → info no existe en BD
                    # Agregar oferta de aprendizaje al final de la respuesta
                    texto_base = res['texto'].strip()
                    respuesta_final = (
                        texto_base + "\n\n"
                        "💡 ¿Quieres enseñarme cómo funciona esto para que pueda responder mejor en el futuro?"
                    )
                    break  # Salir del loop de pasos — no hay SQL que ejecutar

            elif paso == 'ejecutar':
                pasos_ejecutados.append('ejecutar')
                if not sql_generado:
                    raise Exception("No hay SQL para ejecutar.")

                res_sql = ejecutor_sql.ejecutar(sql_generado)
                if not res_sql['ok']:
                    # Reintento: devolver el error al LLM para que corrija el SQL
                    error_sql = res_sql['error']
                    prompt_retry = (
                        f"El SQL que generaste falló con este error:\n{error_sql}\n\n"
                        f"SQL fallido:\n{sql_generado}\n\n"
                        "Genera un SQL corregido. Revisa los nombres de columnas en el esquema. "
                        "Solo responde con el SQL corregido, sin explicaciones."
                    )
                    msgs_retry = mensajes_base + [{'role': 'user', 'content': prompt_retry}]
                    res_retry = _llamar_agente(agente_cfg_sql, msgs_retry, temperatura=0.1)
                    tokens_in_total  += res_retry.get('tokens_in', 0)
                    tokens_out_total += res_retry.get('tokens_out', 0)
                    if res_retry['ok']:
                        sql_retry = formateador.extraer_sql(res_retry['texto'])
                        if sql_retry:
                            res_sql = ejecutor_sql.ejecutar(sql_retry)
                            if res_sql['ok']:
                                sql_generado = sql_retry
                            else:
                                raise Exception(f"Error ejecutando SQL: {res_sql['error']}")
                        else:
                            raise Exception(f"Error ejecutando SQL: {error_sql}")
                    else:
                        raise Exception(f"Error ejecutando SQL: {error_sql}")

                datos_crudos = res_sql['filas']
                tabla_resultado = formateador.filas_a_tabla(res_sql['filas'], res_sql['columnas'])
                # Guardar caché SQL para posibles seguimientos sin re-ejecutar
                contexto.guardar_cache_sql(conv_id, pregunta, res_sql['columnas'], datos_crudos)

                # Retry inteligente: si 0 filas, reenviar al LLM con contexto de fecha máxima
                # (máx 2 reintentos). Corrige filtros demasiado estrictos, fechas erróneas, etc.
                if len(datos_crudos) == 0:
                    for _ in range(2):
                        fecha_max_ctx = _obtener_fecha_maxima(sql_generado)
                        prompt_vacio = (
                            f"El SQL ejecutó sin errores pero devolvió 0 filas.\n"
                            f"SQL ejecutado:\n```sql\n{sql_generado}\n```\n\n"
                            f"{fecha_max_ctx}"
                            f"Revisa si el filtro de fecha es demasiado estricto, si el estado "
                            f"está mal escrito, o si hay una fecha futura por error. "
                            f"Genera un SQL corregido. Responde SOLO con el SQL en un bloque ```sql```."
                        )
                        msgs_vacio = mensajes_base + [{'role': 'user', 'content': prompt_vacio}]
                        res_vacio = _llamar_agente(agente_cfg_sql, msgs_vacio, temperatura=0.1)
                        tokens_in_total  += res_vacio.get('tokens_in', 0)
                        tokens_out_total += res_vacio.get('tokens_out', 0)
                        if res_vacio['ok']:
                            sql_vacio = formateador.extraer_sql(res_vacio['texto'])
                            if sql_vacio:
                                res_sql_v = ejecutor_sql.ejecutar(sql_vacio)
                                if res_sql_v['ok'] and len(res_sql_v['filas']) > 0:
                                    sql_generado    = sql_vacio
                                    datos_crudos    = res_sql_v['filas']
                                    tabla_resultado = formateador.filas_a_tabla(
                                        res_sql_v['filas'], res_sql_v['columnas']
                                    )
                                    break  # Encontró datos — salir del loop
                        # Si sigue vacío, continuar el siguiente intento (o dejarlo vacío)

                # Auto-mejora: guardar este Q→SQL exitoso para futuras consultas similares
                _guardar_ejemplo_sql(empresa, pregunta, sql_generado)

            elif paso == 'conversar':
                # Modo aprendizaje — conversación multi-turno con guardado al confirmar
                pasos_ejecutados.append('conversar')
                msgs = mensajes_base + [{'role': 'user', 'content': pregunta}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=0.3)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error en modo aprendizaje: {res['error']}")

                respuesta_final = res['texto'].strip()
                resumen_nuevo = _generar_resumen_groq(resumen_anterior, pregunta, respuesta_final)

                # Detectar bloque [GUARDAR_NEGOCIO] en la respuesta
                _procesar_bloque_aprendizaje(respuesta_final, empresa)

            elif paso in ('redactar', 'resumir', 'generar_doc'):
                pasos_ejecutados.append(paso)
                prompt_resp = _construir_prompt_respuesta(
                    pregunta, paso, datos_crudos, tabla_resultado, sql_generado
                )
                msgs = mensajes_base + [{'role': 'user', 'content': prompt_resp}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=temperatura)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                # Fallback general — si el agente principal falla por cualquier error
                if not res['ok']:
                    slug_fb = tipo_cfg.get('agente_fallback')
                    if slug_fb and slug_fb != agente_cfg.get('slug'):
                        ag_fb = _cargar_agente(slug_fb)
                        if ag_fb:
                            _notificar(
                                f"⚠️ <b>Agente fallback activado</b>\n"
                                f"Principal: <code>{agente_cfg.get('slug')}</code> falló\n"
                                f"Respaldo: <code>{slug_fb}</code>\n"
                                f"Error: {str(res.get('error',''))[:120]}"
                            )
                            res_fb = _llamar_agente(ag_fb, msgs, temperatura=temperatura)
                            tokens_in_total  += res_fb.get('tokens_in', 0)
                            tokens_out_total += res_fb.get('tokens_out', 0)
                            if res_fb['ok']:
                                res = res_fb

                if not res['ok']:
                    raise Exception(f"Error generando respuesta: {res['error']}")

                parsed = formateador.parsear_respuesta(res['texto'])
                respuesta_final = parsed['respuesta']
                # Resumen generado por Groq en lugar del agente principal
                resumen_nuevo = _generar_resumen_groq(resumen_anterior, pregunta, respuesta_final)
                # Red de seguridad: si el agente generó [GUARDAR_NEGOCIO] (conversacion con regla de negocio)
                _procesar_bloque_aprendizaje(res['texto'], empresa)

            elif paso == 'analizar':
                pasos_ejecutados.append('analizar')
                # Para clasificación: un solo turno
                msgs = mensajes_base + [{'role': 'user', 'content': pregunta}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=temperatura)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error: {res['error']}")

                parsed = formateador.parsear_respuesta(res['texto'])
                respuesta_final = parsed['respuesta']
                resumen_nuevo = _generar_resumen_groq(resumen_anterior, pregunta, respuesta_final)
                # Red de seguridad: clasificacion mal enrutada puede contener una enseñanza
                _procesar_bloque_aprendizaje(res['texto'], empresa)

            elif paso == 'buscar_web':
                pasos_ejecutados.append('buscar_web')
                from .proveedores import tavily as tavily_mod
                resultado_busqueda = tavily_mod.buscar(pregunta)
                if resultado_busqueda['ok']:
                    datos_crudos = tavily_mod.formatear_para_llm(resultado_busqueda)
                else:
                    # Búsqueda falló — convertir a conversacion para responder igual
                    datos_crudos = f"[No se pudo buscar en internet: {resultado_busqueda['error']}. Responde indicándole al usuario que no hay resultados disponibles en este momento.]"

            elif paso == 'generar_imagen':
                pasos_ejecutados.append('generar_imagen')
                msgs = mensajes_base + [{'role': 'user', 'content': pregunta}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=temperatura, max_tokens=512)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error generando imagen: {res['error']}")

                imagen_b64  = res.get('imagen_b64')
                imagen_mime = res.get('imagen_mime', 'image/png')
                respuesta_final = res.get('texto', 'Imagen generada.')
                if not imagen_b64:
                    raise Exception("El modelo no devolvió una imagen. Intenta con una descripción más específica.")

            elif paso == 'clasificar':
                pasos_ejecutados.append('clasificar')
                # Ya se hizo en 'analizar', nada más que hacer

    except Exception as e:
        error = str(e)
        if not respuesta_final:
            respuesta_final = f"Lo siento, ocurrió un error procesando tu consulta: {error}"

    # ── 7. Guardar contexto (resumen comprimido + mensajes recientes) ─
    if resumen_nuevo:
        contexto.guardar_resumen(conv_id, resumen_nuevo)
    if respuesta_final and not error:
        contexto.guardar_mensajes_recientes(conv_id, pregunta, respuesta_final)

    # ── 8. Calcular costo ─────────────────────────────────────────────
    costo_usd = _calcular_costo(agente_cfg, tokens_in_total, tokens_out_total)

    # ── 9. Guardar log ────────────────────────────────────────────────
    log_id = _guardar_log(
        conversacion_id=conv_id,
        agente_slug=agente_slug,
        tipo_consulta=tipo,
        canal=canal,
        pregunta=pregunta,
        sql_generado=sql_generado,
        datos_crudos=datos_crudos[:10] if datos_crudos else None,  # primeras 10 filas en log
        respuesta=respuesta_final,
        formato=tipo_cfg.get('formato_salida', 'texto'),
        tokens_in=tokens_in_total,
        tokens_out=tokens_out_total,
        costo_usd=costo_usd,
        latencia_ms=int((time.time() - t_inicio) * 1000),
        pasos_ejecutados=pasos_ejecutados,
        error=error,
    )

    # ── 9b. Alertas de gasto ──────────────────────────────────────────
    _verificar_gasto_y_notificar(empresa, costo_usd)

    # ── 10. Devolver resultado estándar ───────────────────────────────
    return {
        'ok':              error is None,
        'conversacion_id': conv_id,
        'respuesta':       respuesta_final,
        'formato':         tipo_cfg.get('formato_salida', 'texto'),
        'tabla':           tabla_resultado,
        'sql':             sql_generado,
        'imagen_b64':      imagen_b64,
        'imagen_mime':     imagen_mime,
        'agente':          agente_slug,
        'tema':            tema,
        'empresa':         empresa,
        'tokens':          {'in': tokens_in_total, 'out': tokens_out_total},
        'costo_usd':       costo_usd,
        'pasos':           pasos_ejecutados,
        'log_id':          log_id,
        'error':           error,
    }


# ── Funciones internas ────────────────────────────────────────────────────────

def _enrutar(pregunta: str, empresa: str = 'ori_sil_2', historial_reciente: str = '') -> tuple:
    """
    Detecta tipo de consulta, tema Y si se necesita SQL nuevo en una sola llamada.
    Prefiere Groq (velocidad), fallback a Gemma, fallback a valores default.

    Returns:
        (tipo: str, tema: str, requiere_sql: bool)
        — ej: ('analisis_datos', 'comercial', True)

    requiere_sql=False cuando la pregunta puede responderse con datos ya presentes
    en el historial de conversación (ej: "explícame ese margen", "cuál recomiendas").
    En ese caso el orquestador omite generar_sql y ejecutar, ahorrando 2 llamadas al LLM.
    """
    # Construir mensajes una sola vez (igual para todos los agentes candidatos)
    tipo_enrut = _cargar_tipo('enrutamiento')
    system_base = tipo_enrut.get('system_prompt', '') if tipo_enrut else ''

    temas_disponibles = rag_module.listar_temas(empresa)
    temas_str = ', '.join([f"{t['slug']} ({t['nombre']})" for t in temas_disponibles]) if temas_disponibles else 'general'
    system = system_base + f'\n\nTemas disponibles para clasificar: {temas_str}.'

    user_content = pregunta
    if historial_reciente:
        user_content = f'Historial reciente:\n{historial_reciente}\n\nPregunta actual: {pregunta}'

    msgs = [
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': user_content},
    ]

    tipo_default = 'conversacion'
    tema_default = 'general'
    tipos_validos = {'analisis_datos', 'redaccion', 'clasificacion', 'resumen', 'busqueda_web',
                     'generacion_documento', 'generacion_imagen', 'conversacion',
                     'aprendizaje', 'enrutamiento'}
    temas_validos = {t['slug'] for t in temas_disponibles} if temas_disponibles else {'general'}

    # Intentar cada agente candidato hasta obtener respuesta válida
    for slug in ('groq-llama', 'cerebras-llama', 'gemini-flash-lite', 'gemini-flash'):
        cand = _cargar_agente(slug)
        if not (cand and cand.get('api_key')):
            continue

        res = _llamar_agente(cand, msgs, temperatura=0.1, max_tokens=80)
        if not res['ok']:
            continue  # Fallo (rate limit, timeout, etc.) → intentar siguiente agente

        texto = res['texto'].strip()
        try:
            import re
            match = re.search(r'\{[^}]+\}', texto)
            if match:
                data = json.loads(match.group())
                tipo_ret = data.get('tipo', tipo_default)
                tema_ret = data.get('tema', tema_default)
                req_sql  = bool(data.get('requiere_sql', True))
                return (
                    tipo_ret if tipo_ret in tipos_validos else tipo_default,
                    tema_ret if tema_ret in temas_validos  else tema_default,
                    req_sql,
                )
        except Exception:
            pass

        # Fallback: buscar tipo en texto plano
        texto_lower = texto.lower()
        for slug_t in ('aprendizaje', 'busqueda_web', 'analisis_datos', 'redaccion',
                       'clasificacion', 'resumen', 'generacion_documento',
                       'generacion_imagen', 'conversacion'):
            if slug_t in texto_lower:
                return (slug_t, tema_default, slug_t == 'analisis_datos')

    return ('analisis_datos', 'general', True)  # default conservador: si todo falla, intentar SQL


def _obtener_logica_negocio(empresa: str, pregunta: str) -> str:
    """
    Capa 0: recupera fragmentos de lógica de negocio relevantes para la pregunta.
    - siempre_presente=1 → siempre se inyectan sin importar la pregunta
    - otros → se inyectan si alguna keyword aparece en la pregunta
    Falla silenciosamente si hay error de BD.
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


def _cargar_agente(slug: str) -> dict | None:
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ia_agentes WHERE slug = %s AND activo = 1", (slug,))
            return cur.fetchone()
    finally:
        conn.close()


def _cargar_tipo(slug: str) -> dict | None:
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ia_tipos_consulta WHERE slug = %s AND activo = 1", (slug,))
            return cur.fetchone()
    finally:
        conn.close()


def _llamar_agente(agente: dict, mensajes: list, temperatura: float = 0.3, max_tokens: int = 4096) -> dict:
    """Despacha la llamada al proveedor correcto según api_formato."""
    fmt = agente.get('api_formato', 'openai')
    if fmt == 'google':
        return google.llamar(agente, mensajes, temperatura, max_tokens)
    elif fmt == 'anthropic':
        return anthropic_prov.llamar(agente, mensajes, temperatura, max_tokens)
    else:  # openai (Groq, DeepSeek)
        return openai_compat.llamar(agente, mensajes, temperatura, max_tokens)


def _construir_prompt_respuesta(pregunta, paso, datos_crudos, tabla, sql_generado) -> str:
    """Construye el prompt para el paso de redacción."""
    if paso == 'resumir':
        return f"Por favor resume el siguiente texto:\n\n{pregunta}"

    if datos_crudos is not None:
        # datos_crudos puede ser lista (SQL) o string (búsqueda web)
        if isinstance(datos_crudos, str):
            return (
                f"Pregunta del usuario: {pregunta}\n\n"
                f"{datos_crudos}\n\n"
                f"Responde la pregunta usando la información anterior."
            )
        filas_texto = json.dumps(datos_crudos[:50], ensure_ascii=False, default=str)
        return (
            f"Pregunta del usuario: {pregunta}\n\n"
            f"Datos obtenidos de la base de datos:\n{filas_texto}\n\n"
            f"Responde la pregunta usando SOLO estos datos. "
            f"Si la tabla tiene muchas columnas, presenta las más relevantes. "
            f"Usa formato claro con números formateados."
        )

    return pregunta


def _calcular_costo(agente: dict, tokens_in: int, tokens_out: int) -> float:
    if not agente:
        return 0.0
    costo_in  = float(agente.get('costo_input')  or 0)
    costo_out = float(agente.get('costo_output') or 0)
    return round((tokens_in * costo_in + tokens_out * costo_out) / 1_000_000, 6)


def _guardar_log(**kwargs) -> int | None:
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ia_logs
                   (conversacion_id, agente_slug, tipo_consulta, canal,
                    pregunta, sql_generado, datos_crudos, respuesta, formato,
                    tokens_in, tokens_out, costo_usd, latencia_ms,
                    pasos_ejecutados, error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    kwargs.get('conversacion_id'),
                    kwargs.get('agente_slug'),
                    kwargs.get('tipo_consulta'),
                    kwargs.get('canal'),
                    kwargs.get('pregunta', '')[:2000],
                    kwargs.get('sql_generado'),
                    json.dumps(kwargs.get('datos_crudos'), ensure_ascii=False, default=str)
                        if kwargs.get('datos_crudos') else None,
                    (kwargs.get('respuesta') or '')[:5000],
                    kwargs.get('formato'),
                    kwargs.get('tokens_in'),
                    kwargs.get('tokens_out'),
                    kwargs.get('costo_usd'),
                    kwargs.get('latencia_ms'),
                    json.dumps(kwargs.get('pasos_ejecutados')),
                    kwargs.get('error'),
                )
            )
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            log_id = cur.fetchone()['id']

            # Actualizar consumo diario agregado
            agente_slug = kwargs.get('agente_slug', '')
            es_error = 1 if kwargs.get('error') else 0
            cur.execute(
                """INSERT INTO ia_consumo_diario
                       (fecha, agente_slug, modelo_id, llamadas, errores,
                        tokens_in, tokens_out, costo_usd, latencia_prom_ms)
                   SELECT CURDATE(), %s, modelo_id, 1, %s, %s, %s, %s, %s
                   FROM ia_agentes WHERE slug = %s
                   ON DUPLICATE KEY UPDATE
                       llamadas = llamadas + 1,
                       errores  = errores  + VALUES(errores),
                       tokens_in  = tokens_in  + VALUES(tokens_in),
                       tokens_out = tokens_out + VALUES(tokens_out),
                       costo_usd  = costo_usd  + VALUES(costo_usd),
                       latencia_prom_ms = ROUND(
                           (latencia_prom_ms * (llamadas - 1) + VALUES(latencia_prom_ms)) / llamadas
                       )""",
                (
                    agente_slug,
                    es_error,
                    kwargs.get('tokens_in', 0) or 0,
                    kwargs.get('tokens_out', 0) or 0,
                    kwargs.get('costo_usd', 0) or 0,
                    kwargs.get('latencia_ms', 0) or 0,
                    agente_slug,
                )
            )
            conn.commit()
            return log_id
    except Exception:
        return None
    finally:
        conn.close()
