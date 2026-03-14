"""
Orquestador principal del servicio de IA.
Expone la función consultar() que es el punto de entrada único.
"""
import json
import time
from .config import get_local_conn
from . import contexto, ejecutor_sql, formateador, esquema, rag as rag_module
from .proveedores import openai_compat, google, anthropic_prov


# ── Seguridad: verificación de límites antes de cada llamada ─────────────────

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

# Prompt de resumen — se agrega al final de cada turno
_PROMPT_RESUMEN = """

---
Al final de tu respuesta incluye un resumen actualizado de esta conversación \
entre las etiquetas [RESUMEN_CONTEXTO] y [/RESUMEN_CONTEXTO].
El resumen debe ser DETALLADO (máximo 1000 palabras). Incluye siempre:
- Nombres de personas, clientes, productos mencionados
- Datos numéricos relevantes (ventas, fechas, cantidades, porcentajes)
- Decisiones tomadas o conclusiones a las que se llegó
- Preguntas ya respondidas (para no repetirlas)
- Contexto del negocio que emerge de la conversación
"""


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

    # ── 1. Obtener conversación ───────────────────────────────────────
    conv = contexto.obtener_o_crear(usuario_id, canal, conversacion_id, nombre_usuario)
    conv_id = conv['id']
    resumen_anterior = conv.get('resumen') or ''

    # ── 2. Enrutar: detectar tipo Y tema si no vienen ─────────────────
    if not tipo or not tema:
        tipo_enrutado, tema_enrutado = _enrutar(pregunta, empresa)
        if not tipo:
            tipo = tipo_enrutado
        if not tema:
            tema = tema_enrutado
        pasos_ejecutados.append('enrutar')

    # ── 3. Cargar tipo de consulta ────────────────────────────────────
    tipo_cfg = _cargar_tipo(tipo)
    if not tipo_cfg:
        tipo_cfg = _cargar_tipo('analisis_datos')  # fallback

    pasos_del_tipo = tipo_cfg.get('pasos') or ['redactar']
    if isinstance(pasos_del_tipo, str):
        pasos_del_tipo = json.loads(pasos_del_tipo)

    temperatura = float(tipo_cfg.get('temperatura', 0.3))

    # ── 4. Resolver agente ────────────────────────────────────────────
    # Prioridad: caller > conversación activa > tema preferido > tipo preferido > default
    tema_cfg = rag_module.obtener_tema_por_slug(tema, empresa) if tema else None
    agente_slug = (
        agente
        or conv.get('agente_activo')
        or (tema_cfg.get('agente_preferido') if tema_cfg else None)
        or tipo_cfg.get('agente_preferido')
        or 'gemini-flash'
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

    # ── 4b. Verificar límites de seguridad ────────────────────────────
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
    # CAPA 1: System prompt base (tema tiene prioridad sobre tipo)
    system_prompt = ''
    if tema_cfg and tema_cfg.get('system_prompt'):
        system_prompt = tema_cfg['system_prompt']
    elif tipo_cfg.get('system_prompt'):
        system_prompt = tipo_cfg['system_prompt']

    # CAPA 2: RAG — fragmentos relevantes filtrados por empresa y tema
    tema_id_rag = tema_cfg['id'] if tema_cfg else None
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

    # ── 6. Ejecutar pasos ─────────────────────────────────────────────
    sql_generado    = None
    datos_crudos    = None
    tabla_resultado = None
    imagen_b64      = None
    imagen_mime     = None
    tokens_in_total  = 0
    tokens_out_total = 0
    respuesta_final  = ''
    resumen_nuevo    = None
    error            = None

    try:
        mensajes_base = [{'role': 'system', 'content': system_prompt}]

        for paso in pasos_del_tipo:

            if paso == 'generar_sql':
                pasos_ejecutados.append('generar_sql')
                prompt_sql = (
                    f"Genera el SQL para responder esta pregunta:\n{pregunta}\n\n"
                    f"Responde SOLO con el SQL dentro de un bloque ```sql```. "
                    f"Sin explicaciones adicionales."
                )
                msgs = mensajes_base + [{'role': 'user', 'content': prompt_sql}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=0.1)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error generando SQL: {res['error']}")

                sql_generado = formateador.extraer_sql(res['texto'])
                if not sql_generado:
                    raise Exception("La IA no generó un SQL válido.")

            elif paso == 'ejecutar':
                pasos_ejecutados.append('ejecutar')
                if not sql_generado:
                    raise Exception("No hay SQL para ejecutar.")

                res_sql = ejecutor_sql.ejecutar(sql_generado)
                if not res_sql['ok']:
                    raise Exception(f"Error ejecutando SQL: {res_sql['error']}")

                datos_crudos = res_sql['filas']
                tabla_resultado = formateador.filas_a_tabla(res_sql['filas'], res_sql['columnas'])

            elif paso in ('redactar', 'resumir', 'generar_doc'):
                pasos_ejecutados.append(paso)
                prompt_resp = _construir_prompt_respuesta(
                    pregunta, paso, datos_crudos, tabla_resultado, sql_generado
                ) + _PROMPT_RESUMEN
                msgs = mensajes_base + [{'role': 'user', 'content': prompt_resp}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=temperatura)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error generando respuesta: {res['error']}")

                parsed = formateador.parsear_respuesta(res['texto'])
                respuesta_final = parsed['respuesta']
                resumen_nuevo   = parsed.get('resumen_nuevo')

            elif paso == 'analizar':
                pasos_ejecutados.append('analizar')
                # Para clasificación: un solo turno
                prompt_clas = pregunta + _PROMPT_RESUMEN
                msgs = mensajes_base + [{'role': 'user', 'content': prompt_clas}]
                res = _llamar_agente(agente_cfg, msgs, temperatura=temperatura)
                tokens_in_total  += res.get('tokens_in', 0)
                tokens_out_total += res.get('tokens_out', 0)

                if not res['ok']:
                    raise Exception(f"Error: {res['error']}")

                parsed = formateador.parsear_respuesta(res['texto'])
                respuesta_final = parsed['respuesta']
                resumen_nuevo   = parsed.get('resumen_nuevo')

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

def _enrutar(pregunta: str, empresa: str = 'ori_sil_2') -> tuple:
    """
    Detecta tipo de consulta Y tema en una sola llamada al enrutador.
    Prefiere Groq (velocidad), fallback a Gemma, fallback a valores default.

    Returns:
        (tipo: str, tema: str)  — ej: ('analisis_datos', 'comercial')
    """
    agente_cfg = None
    for slug in ('groq-llama', 'gemma-router', 'gemini-flash-lite', 'gemini-flash'):
        cand = _cargar_agente(slug)
        if cand and cand.get('api_key'):
            agente_cfg = cand
            break
    if not agente_cfg:
        return ('analisis_datos', 'general')

    tipo_enrut = _cargar_tipo('enrutamiento')
    system_base = tipo_enrut.get('system_prompt', '') if tipo_enrut else ''

    # Ampliar system prompt con temas disponibles para esta empresa
    temas_disponibles = rag_module.listar_temas(empresa)
    temas_str = ', '.join([f"{t['slug']} ({t['nombre']})" for t in temas_disponibles]) if temas_disponibles else 'general'
    system = system_base + f"""

Adicionalmente, clasifica el TEMA de la pregunta. Temas disponibles: {temas_str}.
Responde en formato JSON exacto: {{"tipo": "slug_tipo", "tema": "slug_tema"}}
Ejemplo: {{"tipo": "analisis_datos", "tema": "comercial"}}"""

    msgs = [
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': pregunta},
    ]
    res = _llamar_agente(agente_cfg, msgs, temperatura=0.1, max_tokens=50)

    tipo_default = 'conversacion'
    tema_default = 'general'

    if res['ok']:
        texto = res['texto'].strip()
        # Intentar parsear JSON {"tipo": "...", "tema": "..."}
        try:
            import re
            match = re.search(r'\{[^}]+\}', texto)
            if match:
                data = json.loads(match.group())
                tipos_validos = {'analisis_datos', 'redaccion', 'clasificacion', 'resumen',
                                 'generacion_documento', 'generacion_imagen', 'conversacion', 'enrutamiento'}
                temas_validos  = {t['slug'] for t in temas_disponibles} if temas_disponibles else {'general'}
                tipo_ret = data.get('tipo', tipo_default)
                tema_ret = data.get('tema', tema_default)
                return (
                    tipo_ret if tipo_ret in tipos_validos else tipo_default,
                    tema_ret if tema_ret in temas_validos  else tema_default,
                )
        except Exception:
            pass

        # Fallback: buscar tipo en texto plano
        texto_lower = texto.lower()
        for slug in ('analisis_datos', 'redaccion', 'clasificacion', 'resumen',
                     'generacion_documento', 'generacion_imagen', 'conversacion'):
            if slug in texto_lower:
                return (slug, tema_default)

    return (tipo_default, tema_default)


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
