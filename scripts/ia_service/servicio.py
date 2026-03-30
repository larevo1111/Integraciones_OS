"""
Orquestador principal del servicio de IA.
Expone la función consultar() que es el punto de entrada único.

Módulos auxiliares (extraídos para separación de responsabilidades):
  - seguridad.py:       rate limit, circuit breaker, verificar_limites
  - alertas.py:         notificaciones Telegram, verificar gasto
  - aprendizaje.py:     guardar reglas, ejemplos SQL, depurador, resúmenes
  - utilidades_sql.py:  columnas reales, fecha máxima, cobertura tablas
"""
import json
import time
from .config import get_local_conn
from . import contexto, ejecutor_sql, formateador, esquema, rag as rag_module
from .proveedores import openai_compat, google, anthropic_prov
from .seguridad import (
    verificar_rate_usuario, verificar_limites, slugs_router,
    get_config_simple, nivel_usuario, mejor_agente_para_nivel,
)
from .alertas import notificar, verificar_gasto_y_notificar
from .aprendizaje import (
    procesar_bloque_aprendizaje, guardar_ejemplo_sql,
    obtener_ejemplos_dinamicos, obtener_logica_negocio,
    generar_resumen, depurar_logica_negocio,
    registrar_feedback,
)
from .utilidades_sql import (
    obtener_columnas_reales, obtener_fecha_maxima, obtener_cobertura_tablas,
)


def _resolver_agente_disponible(nivel_usr: int, agente_bloqueado: str, empresa: str) -> dict | None:
    """
    Busca el siguiente agente disponible cuando el preferido está bloqueado (capa 2 o 3).
    Respeta nivel del usuario y orden de prioridad.
    Retorna dict del agente si encuentra uno, o None si todos están bloqueados.
    """
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug FROM ia_agentes "
                "WHERE activo=1 AND api_key != '' AND nivel_minimo <= %s AND slug != %s "
                "ORDER BY orden ASC",
                (nivel_usr, agente_bloqueado)
            )
            candidatos = cur.fetchall()
        conn.close()

        for cand in candidatos:
            bloqueo = verificar_limites(cand['slug'], empresa)
            if bloqueo is None:
                agente_cfg = _cargar_agente(cand['slug'])
                if agente_cfg:
                    return agente_cfg
        return None
    except Exception:
        return None

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
    MAX_PIPELINE_SEG = 900  # timeout total del pipeline (15 min)
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
        _frases_guarda = (
            'lo guardo en mi memoria de negocio', '¿lo guardo así', '¿quieres que lo guarde',
            'quieres que guarde esto', 'guárdalo', '¿lo guardo', 'lo guardo así',
        )
        if _pregunta_lower in _confirmaciones and historial_ctx and \
                any(f in historial_ctx.lower() for f in _frases_guarda):
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

        # Detección pre-router: si el bot indicó que está en sesión de aprendizaje activa
        # (dijo "listo para aprender" o similar en el historial) → continuar en aprendizaje
        # Evita que el router confunda la instrucción del usuario como analisis_datos
        if not tipo and historial_ctx:
            _hctx_lower = historial_ctx.lower()
            _frases_modo_aprendizaje = (
                'estoy listo para aprender', 'cuéntame qué quieres enseñarme',
                'qué quieres enseñarme', 'modo aprendizaje', 'cuéntame sobre el concepto',
                'what do you want to teach me',  # por si viene en inglés
            )
            if any(f in _hctx_lower for f in _frases_modo_aprendizaje):
                tipo = 'aprendizaje'
                tema = tema or 'general'
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

    # Si el usuario pide explícitamente más detalle o una tabla, forzar SQL nuevo
    # aunque el router diga que se puede responder con el caché (que puede ser agregado).
    _pide_detalle = ('detalle', 'desglose', 'tabla adjunta', 'tabla completa',
                     'ver la tabla', 'dame la tabla', 'muéstrame la tabla',
                     'muestrame la tabla', 'más datos', 'mas datos', 'todos los',
                     'todas las', 'listado completo', 'listame', 'lístalos',
                     'dame todo', 'cada uno', 'uno por uno')
    # Preguntas sobre períodos actuales SIEMPRE deben consultar datos frescos
    # porque el pipeline pudo haber actualizado los datos desde la última consulta.
    _periodo_actual = ('este mes', 'mes actual', 'esta semana', 'semana actual',
                       'hoy', 'de hoy', 'ventas del mes', 'ventas de este',
                       'ventas del', 'dame las ventas', 'las ventas',
                       'cuánto llevamos', 'cuanto llevamos', 'cómo vamos',
                       'como vamos', 'lo que va', 'cuánto hemos vendido',
                       'cuanto hemos vendido', 'facturado')
    if tipo == 'analisis_datos' and not requiere_sql:
        preg_lower = pregunta.lower()
        if any(kw in preg_lower for kw in _pide_detalle):
            requiere_sql = True
        elif any(kw in preg_lower for kw in _periodo_actual):
            requiere_sql = True

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
        agente_slug = agente_cfg['slug'] if agente_cfg else 'gemini-flash-lite'

    # ── 4b. Verificar nivel de usuario vs agente ─────────────────────
    nivel_usr = nivel_usuario(usuario_id, empresa)
    agente_nivel_min = (agente_cfg or {}).get('nivel_minimo', 1) or 1
    if nivel_usr < agente_nivel_min:
        # Redirigir silenciosamente al mejor agente disponible para su nivel
        agente_slug = mejor_agente_para_nivel(nivel_usr)
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

    # ── 4c. Verificar límites de seguridad (con fallback automático) ──
    bloqueo = verificar_limites(agente_slug, empresa)
    if bloqueo:
        capa = bloqueo.get('capa', 1)
        if capa == 1:
            # Presupuesto global agotado — no hay alternativa
            return {
                'ok': False, 'conversacion_id': conv_id,
                'respuesta': bloqueo['error'],
                'formato': 'texto', 'tabla': None, 'sql_generado': None,
                'agente': agente_slug, 'tema': tema,
                'tokens': {'in': 0, 'out': 0}, 'costo_usd': 0.0,
                'pasos': [], 'log_id': None, 'error': bloqueo['error'],
            }
        # Capa 2 (RPD) o 3 (circuit breaker) — intentar otro agente
        agente_alt = _resolver_agente_disponible(nivel_usr, agente_slug, empresa)
        if agente_alt:
            notificar(
                f"🔄 <b>Fallback automático</b>\n"
                f"Agente <code>{agente_slug}</code> bloqueado (capa {capa})\n"
                f"Alternativa: <code>{agente_alt['slug']}</code>"
            )
            agente_slug = agente_alt['slug']
            agente_cfg  = agente_alt
            # Si el agente SQL era el mismo que el bloqueado, actualizar también
            if agente_cfg_sql.get('slug') == agente_slug:
                agente_cfg_sql = agente_alt
        else:
            # Todos los agentes bloqueados — error al usuario
            return {
                'ok': False, 'conversacion_id': conv_id,
                'respuesta': '⛔ Todos los agentes están temporalmente suspendidos. Intenta en unos minutos.',
                'formato': 'texto', 'tabla': None, 'sql_generado': None,
                'agente': agente_slug, 'tema': tema,
                'tokens': {'in': 0, 'out': 0}, 'costo_usd': 0.0,
                'pasos': [], 'log_id': None,
                'error': 'Todos los agentes bloqueados',
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
    _logica_negocio = obtener_logica_negocio(empresa, pregunta)

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
            # Timeout global del pipeline
            if (time.time() - t_inicio) > MAX_PIPELINE_SEG:
                raise Exception(f"Timeout: pipeline superó {MAX_PIPELINE_SEG}s")

            if paso == 'generar_sql':
                pasos_ejecutados.append('generar_sql')
                # Recuperar ejemplos dinámicos de consultas exitosas anteriores
                ejemplos_din = obtener_ejemplos_dinamicos(empresa, pregunta)
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
                            notificar(
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
                    # Agregar oferta de aprendizaje con mensaje claro de acción
                    texto_base = res['texto'].strip()
                    respuesta_final = (
                        texto_base + "\n\n"
                        "💡 ¿Quieres que guarde esto en mi memoria de negocio? "
                        "Responde **'sí, guárdalo'** y lo registraré para futuras consultas."
                    )
                    break  # Salir del loop de pasos — no hay SQL que ejecutar

            elif paso == 'ejecutar':
                pasos_ejecutados.append('ejecutar')
                if not sql_generado:
                    raise Exception("No hay SQL para ejecutar.")

                res_sql = ejecutor_sql.ejecutar(sql_generado)
                if not res_sql['ok']:
                    # Reintento: obtener columnas REALES de las tablas usadas y enviar al LLM
                    error_sql = res_sql['error']
                    columnas_reales = obtener_columnas_reales(sql_generado)
                    prompt_retry = (
                        f"El SQL que generaste falló con este error:\n{error_sql}\n\n"
                        f"SQL fallido:\n{sql_generado}\n\n"
                        f"{columnas_reales}"
                        "Genera un SQL corregido usando SOLO las columnas listadas arriba. "
                        "Solo responde con el SQL corregido en un bloque ```sql```, sin explicaciones."
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
                                # Retry exitoso → registrar corrección
                                registrar_feedback(
                                    empresa, 'correccion', pregunta,
                                    sql_fallido=sql_generado, sql_correcto=sql_retry,
                                    error_original=error_sql,
                                )
                                sql_generado = sql_retry
                            else:
                                registrar_feedback(
                                    empresa, 'sql_error', pregunta,
                                    sql_fallido=sql_generado, error_original=error_sql,
                                )
                                raise Exception(f"Error ejecutando SQL: {res_sql['error']}")
                        else:
                            registrar_feedback(
                                empresa, 'sql_error', pregunta,
                                sql_fallido=sql_generado, error_original=error_sql,
                            )
                            raise Exception(f"Error ejecutando SQL: {error_sql}")
                    else:
                        registrar_feedback(
                            empresa, 'sql_error', pregunta,
                            sql_fallido=sql_generado, error_original=error_sql,
                        )
                        raise Exception(f"Error ejecutando SQL: {error_sql}")

                datos_crudos = res_sql['filas']
                tabla_resultado = formateador.filas_a_tabla(res_sql['filas'], res_sql['columnas'])
                # Guardar caché SQL para posibles seguimientos sin re-ejecutar
                contexto.guardar_cache_sql(conv_id, pregunta, res_sql['columnas'], datos_crudos)

                # Retry inteligente: si 0 filas, reenviar al LLM con contexto de fecha máxima
                # (máx 2 reintentos). Corrige filtros demasiado estrictos, fechas erróneas, etc.
                if len(datos_crudos) == 0:
                    for _ in range(2):
                        fecha_max_ctx = obtener_fecha_maxima(sql_generado)
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
                guardar_ejemplo_sql(empresa, pregunta, sql_generado)

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
                resumen_nuevo = generar_resumen(resumen_anterior, pregunta, respuesta_final, empresa)

                # Detectar bloque [GUARDAR_NEGOCIO] en la respuesta
                procesar_bloque_aprendizaje(respuesta_final, empresa)

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
                            notificar(
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
                resumen_nuevo = generar_resumen(resumen_anterior, pregunta, respuesta_final, empresa)
                # Red de seguridad: solo en conversacion — analisis_datos NUNCA debe guardar lógica de negocio
                if tipo == 'conversacion':
                    procesar_bloque_aprendizaje(res['texto'], empresa)

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
                resumen_nuevo = generar_resumen(resumen_anterior, pregunta, respuesta_final, empresa)
                # Red de seguridad: clasificacion mal enrutada puede contener una enseñanza
                procesar_bloque_aprendizaje(res['texto'], empresa)

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
    verificar_gasto_y_notificar(empresa, costo_usd)

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
    for slug in slugs_router():
        cand = _cargar_agente(slug)
        if not (cand and cand.get('api_key')):
            continue

        res = _llamar_agente(cand, msgs, temperatura=0.1, max_tokens=80)
        _log_aux(cand, res, 'router', pregunta, empresa)  # loguear siempre — ok o error
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


_cache_agentes = {}  # slug → {'data': dict, 'ts': float}
_cache_tipos = {}    # slug → {'data': dict, 'ts': float}
_CACHE_CONFIG_TTL = 300  # 5 minutos


def _cargar_agente(slug: str) -> dict | None:
    cached = _cache_agentes.get(slug)
    if cached and (time.time() - cached['ts']) < _CACHE_CONFIG_TTL:
        return cached['data']
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ia_agentes WHERE slug = %s AND activo = 1", (slug,))
            row = cur.fetchone()
        _cache_agentes[slug] = {'data': row, 'ts': time.time()}
        return row
    finally:
        conn.close()


def _cargar_tipo(slug: str) -> dict | None:
    cached = _cache_tipos.get(slug)
    if cached and (time.time() - cached['ts']) < _CACHE_CONFIG_TTL:
        return cached['data']
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ia_tipos_consulta WHERE slug = %s AND activo = 1", (slug,))
            row = cur.fetchone()
        _cache_tipos[slug] = {'data': row, 'ts': time.time()}
        return row
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
        n_total = len(datos_crudos)
        filas_texto = json.dumps(datos_crudos[:50], ensure_ascii=False, default=str)
        tiene_tabla = n_total > 2
        instruccion_tabla = (
            f"Hay {n_total} registros en total — el sistema mostrará un botón 'Ver tabla completa' "
            f"para que el usuario pueda verlos todos con filtros. "
            f"Tu respuesta debe ser un resumen ejecutivo BREVE (3-5 líneas máximo) que incluya SIEMPRE:\n"
            f"1. Total de registros ({n_total})\n"
            f"2. El valor o métrica principal (suma, total, promedio) si hay columnas numéricas\n"
            f"3. Los 2-3 registros más destacados (mayor valor, más reciente, etc.)\n"
            f"Luego indica que puede ver el detalle completo en la tabla.\n"
        ) if tiene_tabla else (
            f"Responde la pregunta de forma directa y concisa con los datos obtenidos. "
            f"Presenta cada dato con viñetas así: • **Nombre legible**: valor formateado\n"
            f"IMPORTANTE: traduce los nombres de columna a español legible. "
            f"Ejemplos: fin_ventas_netas_sin_iva → Ventas netas, cto_utilidad_bruta → Utilidad bruta, "
            f"vol_unidades_vendidas → Unidades vendidas, margen_utilidad_pct → Margen de utilidad, "
            f"vol_num_facturas → Facturas, cat_num_referencias → Referencias. "
            f"Formatea cifras con separador de miles y signo $ donde aplique. "
            f"Porcentajes con símbolo %. NO repitas el mismo dato con nombre diferente.\n"
        )
        return (
            f"Pregunta del usuario: {pregunta}\n\n"
            f"Datos obtenidos de la base de datos ({n_total} registros):\n{filas_texto}\n\n"
            f"{instruccion_tabla}"
            f"REGLA ABSOLUTA: NUNCA uses tablas, cuadros, pipes (|), guiones (---), ni caracteres de dibujo (┌─┐│└┘├┤┬┴┼). Solo viñetas y texto plano."
        )

    return pregunta


def _calcular_costo(agente: dict, tokens_in: int, tokens_out: int) -> float:
    if not agente:
        return 0.0
    costo_in  = float(agente.get('costo_input')  or 0)
    costo_out = float(agente.get('costo_output') or 0)
    return round((tokens_in * costo_in + tokens_out * costo_out) / 1_000_000, 6)


def _log_aux(agente_cfg: dict, res: dict, tipo: str, pregunta_breve: str,
             empresa: str = 'ori_sil_2', latencia_ms: int = 0):
    """
    Loguea llamadas auxiliares (router, resumen, depurador) en ia_logs.
    Sin esta función, los costos reales de Gemini son invisibles en el dashboard interno.
    Falla silenciosamente para no interrumpir el flujo principal.
    """
    try:
        if not agente_cfg:
            return
        costo = _calcular_costo(agente_cfg, res.get('tokens_in', 0) or 0, res.get('tokens_out', 0) or 0)
        _guardar_log(
            conversacion_id=None,
            agente_slug=agente_cfg.get('slug', ''),
            tipo_consulta=tipo,
            canal='interno',
            pregunta=pregunta_breve[:300],
            sql_generado=None,
            datos_crudos=None,
            respuesta=None,
            formato='texto',
            tokens_in=res.get('tokens_in', 0) or 0,
            tokens_out=res.get('tokens_out', 0) or 0,
            costo_usd=costo,
            latencia_ms=latencia_ms,
            pasos_ejecutados=[tipo],
            error=res.get('error') if not res.get('ok') else None,
        )
        if costo > 0:
            verificar_gasto_y_notificar(empresa, costo)
    except Exception:
        pass


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
