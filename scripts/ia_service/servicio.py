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
        # Pasar historial reciente para que el enrutador pueda decidir requiere_sql
        # (distingue entre "dame ventas de ayer" vs "explícame ese margen")
        historial_ctx = contexto.obtener_mensajes_recientes_formateados(conv)
        tipo_enrutado, tema_enrutado, requiere_sql = _enrutar(pregunta, empresa, historial_ctx)
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

    # Si el enrutador determinó que no se necesita SQL nuevo, saltar generar_sql y ejecutar.
    # La respuesta se construye con los datos ya presentes en el contexto conversacional.
    if tipo == 'analisis_datos' and not requiere_sql:
        pasos_del_tipo = ['redactar']
        pasos_ejecutados.append('sin_sql')  # trazabilidad en logs

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

    # CAPA 1: System prompt base (tema tiene prioridad sobre tipo)
    system_prompt = _fecha_ctx + '\n\n'
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
    agente_cfg = None
    for slug in ('groq-llama', 'gemma-router', 'gemini-flash-lite', 'gemini-flash'):
        cand = _cargar_agente(slug)
        if cand and cand.get('api_key'):
            agente_cfg = cand
            break
    if not agente_cfg:
        return ('analisis_datos', 'general', True)

    tipo_enrut = _cargar_tipo('enrutamiento')
    system_base = tipo_enrut.get('system_prompt', '') if tipo_enrut else ''

    # Ampliar system prompt con temas disponibles para esta empresa
    temas_disponibles = rag_module.listar_temas(empresa)
    temas_str = ', '.join([f"{t['slug']} ({t['nombre']})" for t in temas_disponibles]) if temas_disponibles else 'general'
    system = system_base + f'\n\nTemas disponibles para clasificar: {temas_str}.'

    # Incluir historial reciente para que el enrutador pueda determinar requiere_sql
    # Si ya hay datos en la conversación, preguntas de interpretación no necesitan SQL nuevo
    user_content = pregunta
    if historial_reciente:
        user_content = f'Historial reciente:\n{historial_reciente}\n\nPregunta actual: {pregunta}'

    msgs = [
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': user_content},
    ]
    res = _llamar_agente(agente_cfg, msgs, temperatura=0.1, max_tokens=80)

    tipo_default = 'conversacion'
    tema_default = 'general'

    if res['ok']:
        texto = res['texto'].strip()
        try:
            import re
            match = re.search(r'\{[^}]+\}', texto)
            if match:
                data = json.loads(match.group())
                tipos_validos = {'analisis_datos', 'redaccion', 'clasificacion', 'resumen',
                                 'generacion_documento', 'generacion_imagen', 'conversacion', 'enrutamiento'}
                temas_validos  = {t['slug'] for t in temas_disponibles} if temas_disponibles else {'general'}
                tipo_ret  = data.get('tipo', tipo_default)
                tema_ret  = data.get('tema', tema_default)
                # requiere_sql: default True para analisis_datos (conservador)
                req_sql = bool(data.get('requiere_sql', True))
                return (
                    tipo_ret if tipo_ret in tipos_validos else tipo_default,
                    tema_ret if tema_ret in temas_validos  else tema_default,
                    req_sql,
                )
        except Exception:
            pass

        # Fallback: buscar tipo en texto plano — sin historial no podemos saber requiere_sql
        texto_lower = texto.lower()
        for slug in ('analisis_datos', 'redaccion', 'clasificacion', 'resumen',
                     'generacion_documento', 'generacion_imagen', 'conversacion'):
            if slug in texto_lower:
                return (slug, tema_default, True)

    return (tipo_default, tema_default, True)


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
