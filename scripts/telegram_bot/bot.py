"""
OS IA — Bot de Telegram
python-telegram-bot v20 (async)

Arranca con:
  python3 scripts/telegram_bot/bot.py
"""
import sys, os, logging, asyncio, base64, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction

import api_ia, db, tabla as tabla_mod, whisper as whisper_mod, superagente as sa_mod
import superagente_oc as saoc_mod
import handlers_sa
import handlers_sa_oc
from teclado import REPLY_KB, reply_kb, inline_ajustes, MAX_INLINE, teclado_compartir_telefono, AGENTES

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         '..', 'logs', 'telegram_bot.log')
        )
    ]
)
log = logging.getLogger('os_ia_bot')

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Set de user_ids que forzaron "Nueva conversación" — el próximo mensaje crea sesión
SA_FORZAR_NUEVA = set()
SAOC_FORZAR_NUEVA = set()

NOMBRES_AGENTES = {
    'gemini-flash':      'Gemini Flash ⚡',
    'gemini-flash-lite': 'Gemini Flash Lite ⚡',
    'gpt-oss-120b':      'GPT-OSS 120B 🧪',
    'gemini-pro':        'Gemini Pro 🧠',
    'claude-sonnet':     'Claude Sonnet 🤖',
    'deepseek-chat':     'DeepSeek Chat 💡',
    'automático':        'Automático 🔀',
    'superagente':       'Super Agente 🦾',
    'superagente-oc':    'Super Agente OC 🧩',
    'ollama-qwen-coder': 'Qwen Coder 🏠',
    'ollama-qwen-14b':   'Qwen 14B 🏠',
    'ollama-qwen-7b':    'Qwen 7B 🏠',
    'ollama-deepseek-r1': 'DeepSeek R1 🏠',
    'ollama-llama-3b':   'Llama 3B 🏠',
}

ICONOS_AGENTES = {
    'gemini-pro':        '🧠',
    'gemini-flash':      '⚡',
    'gemini-flash-lite': '⚡',
    'claude-sonnet':     '🤖',
    'deepseek-chat':     '💡',
    'deepseek-reasoner': '💡',
    'groq-llama':        '🔥',
    'gemma-router':      '🔀',
    'gpt-oss-120b':      '🧪',
    'cerebras-llama':    '🔥',
    'ollama-qwen-coder': '🏠',
    'ollama-qwen-14b':   '🏠',
    'ollama-qwen-7b':    '🏠',
    'ollama-deepseek-r1': '🏠',
    'ollama-llama-3b':   '🏠',
}


# ─── Autenticación ────────────────────────────────────────────────────────────

async def _verificar_acceso(update: Update) -> dict | None:
    """
    Verifica si el usuario tiene acceso al bot.

    Flujo:
    1. Si ya está autorizado en bot_sesiones → OK, retorna sesión.
    2. Si tiene telegram_id en ia_usuarios → autorizar y guardar sesión.
    3. Si no → pedir que comparta el número de teléfono.

    Retorna la sesión dict si tiene acceso, None si no.
    """
    user   = update.effective_user
    sesion = db.obtener_sesion(user.id)

    # Ya autorizado previamente
    if sesion.get('autorizado'):
        return sesion

    # Verificar por telegram_id (puede haber sido añadido manualmente en BD)
    usuario = db.verificar_por_telegram_id(user.id)
    if usuario:
        db.guardar_sesion(
            user.id, user.username or '', usuario['nombre'],
            autorizado=1, nivel=usuario['nivel']
        )
        return db.obtener_sesion(user.id)

    # No autorizado — pedir teléfono
    await update.message.reply_text(
        '👋 Hola, soy el asistente IA de *Origen Silvestre*.\n\n'
        'Para usar el bot necesito verificar tu identidad.\n'
        'Comparte tu número de teléfono para continuar:',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=teclado_compartir_telefono()
    )
    return None


async def handle_contacto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Recibe el número de teléfono y verifica contra ia_usuarios."""
    user     = update.effective_user
    contacto = update.message.contact

    # Telegram solo permite compartir el propio contacto
    if contacto.user_id != user.id:
        await update.message.reply_text('Por favor comparte tu propio número.')
        return

    telefono = contacto.phone_number
    if not telefono.startswith('+'):
        telefono = '+' + telefono

    usuario = db.verificar_por_telefono(telefono)

    if not usuario:
        await update.message.reply_text(
            '❌ Tu número no está registrado.\n\n'
            'Contacta a Santiago para que te dé acceso.',
            reply_markup=teclado_compartir_telefono()
        )
        log.warning(f'Acceso denegado: {user.id} (@{user.username}) tel={telefono}')
        return

    # Vincular telegram_id al usuario en ia_usuarios
    db.vincular_telegram_id(telefono, user.id)
    db.guardar_sesion(
        user.id, user.username or '', usuario['nombre'],
        autorizado=1, nivel=usuario['nivel']
    )

    log.info(f'Acceso concedido: {usuario["nombre"]} (nivel {usuario["nivel"]}) tel={telefono}')

    await update.message.reply_text(
        f'✅ ¡Bienvenida/o, *{usuario["nombre"]}*!\n\n'
        'Ya puedes usar el bot. Escribe tu pregunta sobre ventas, '
        'productos, clientes o cualquier dato del negocio.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_kb(usuario['nivel'])
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _nombre(user) -> str:
    return user.first_name or user.username or str(user.id)


def _escape(texto: str) -> str:
    for ch in r'_*[]()~`>#+-=|{}.!':
        texto = texto.replace(ch, f'\\{ch}')
    return texto


def _inline_datos(token: str, n_filas: int) -> InlineKeyboardMarkup:
    botones = []
    if token:
        botones.append(
            InlineKeyboardButton(
                f'📋 Ver tabla completa ({n_filas} filas)',
                url=f'https://menu.oscomunidad.com/bot/tabla?token={token}'
            )
        )
    botones.append(InlineKeyboardButton('↩ Nueva consulta', callback_data='nueva_consulta'))
    return InlineKeyboardMarkup([botones])


def _inline_solo_nuevo() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton('↩ Nueva consulta', callback_data='nueva_consulta')
    ]])


# ─── Handlers de comandos ────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    nombre = sesion.get('nombre') or _nombre(user)
    nivel  = sesion.get('nivel', 1)
    await update.message.reply_text(
        f'¡Hola {nombre}! 👋\n\n'
        'Soy el asistente IA de Origen Silvestre. Pregúntame lo que quieras sobre ventas, '
        'productos, clientes o cualquier dato del negocio.\n\n'
        'Escribe tu pregunta directamente o usa los botones de abajo.',
        reply_markup=reply_kb(nivel)
    )


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    await update.message.reply_text(
        '📖 *Cómo usar el bot*\n\n'
        'Escribe cualquier pregunta en lenguaje natural. Ejemplos:\n'
        '  _¿Cuánto vendimos en febrero?_\n'
        '  _Top 5 productos del mes pasado_\n'
        '  _¿Qué clientes compraron más este año?_\n\n'
        '*Comandos disponibles:*\n'
        '/ventas — Ventas del día de hoy\n'
        '/mes — Resumen del mes en curso\n'
        '/actualizar — Forzar actualización de datos desde Effi\n'
        '/estado — Ver agente activo\n'
        '/agente — Cambiar modelo de IA\n'
        '/limpiar — Limpiar historial\n'
        '/ayuda — Ver esta ayuda',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_kb(sesion.get('nivel', 1))
    )


async def cmd_estado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    agente = sesion.get('agente_preferido') or 'automático'
    nivel  = sesion.get('nivel', 1)
    await update.message.reply_text(
        '📊 *Estado actual*\n\n'
        f'🤖 Agente: {NOMBRES_AGENTES.get(agente, agente)}\n'
        f'🏢 Empresa: Origen Silvestre\n'
        f'🔑 Nivel de acceso: {nivel}\n\n'
        'Usa /agente para cambiar el modelo.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_kb(nivel)
    )


async def cmd_agente(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    agente = sesion.get('agente_preferido')
    nivel  = sesion.get('nivel', 1)

    await update.message.reply_text(
        '🤖 *Selecciona el agente de IA*\n\n'
        'Solo se muestran los agentes disponibles para tu nivel de acceso.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=inline_ajustes(agente, nivel)
    )


async def cmd_limpiar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    user = update.effective_user
    db.guardar_sesion(user.id, user.username or '', _nombre(user), conversacion_id=0)
    await update.message.reply_text(
        '🗑️ Historial limpiado. La próxima pregunta empieza desde cero.',
        reply_markup=reply_kb(sesion.get('nivel', 1))
    )


async def cmd_actualizar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    if sesion.get('nivel', 1) < 5:
        await update.message.reply_text('❌ No tienes permiso para ejecutar esta acción.')
        return

    await update.message.reply_text(
        '🔄 Iniciando actualización de datos desde Effi...\n'
        '_Esto tarda entre 10 y 20 minutos. Te aviso cuando termine._',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_kb(sesion.get('nivel', 1))
    )

    import subprocess, threading

    def _lanzar():
        subprocess.Popen(
            ['python3', '/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/orquestador.py',
             '--forzar', '--chat-id', str(update.effective_user.id)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    threading.Thread(target=_lanzar, daemon=True).start()
    log.info(f'Orquestador forzado por {update.effective_user.id} (nivel {sesion.get("nivel")})')


async def cmd_ventas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    update.message.text = '¿Cuánto hemos vendido hoy?'
    await handle_mensaje(update, ctx)


async def cmd_mes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    update.message.text = '¿Cuánto llevamos vendido este mes y cómo vamos vs el mes anterior?'
    await handle_mensaje(update, ctx)


# ─── Detección de búsqueda web (para mensaje intermedio) ─────────────────────

_WEB_KEYWORDS = [
    'busca en internet', 'consulta en internet', 'buscar en internet',
    'busca en la web', 'consulta en la web', 'búscalo en internet',
    'búscalo en la web', 'consúltalo en internet', 'busca en google',
    'googlealo', 'googléalo',
    'precio del dólar', 'precio del euro', 'precio del dolar', 'tasa de cambio',
    'cotización de', 'cotizacion de', 'precio de referencia',
    'en bolsa', 'bolsa de valores',
    'noticias de', 'noticias del', 'qué pasó con', 'que paso con',
    'regulación', 'regulacion', 'normativa', 'ley de', 'decreto ',
    'requisitos invima', 'requisitos ica', 'certificación', 'certificacion',
    'clima en', 'temperatura en', 'pronóstico del tiempo',
    'tendencias de', 'quién es ', 'quien es ',
    'cuánto vale el dólar', 'cuanto vale el dolar',
]

def _es_busqueda_web(texto: str) -> bool:
    t = texto.lower()
    return any(kw in t for kw in _WEB_KEYWORDS)


# ─── Handler principal de mensajes ───────────────────────────────────────────

async def handle_mensaje(update: Update, ctx: ContextTypes.DEFAULT_TYPE, texto_override: str = None):
    user  = update.effective_user
    texto = (texto_override or update.message.text or '').strip()

    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    nombre = sesion.get('nombre') or _nombre(user)
    nivel  = sesion.get('nivel', 1)

    # Shortcuts de los botones rápidos
    if texto == '📊 Ventas hoy':
        texto = '¿Cuánto hemos vendido hoy?'
    elif texto == '📈 Este mes':
        texto = '¿Cuánto llevamos vendido este mes y cómo vamos vs el mes anterior?'
    elif texto == '⚙️ Ajustes':
        agente = sesion.get('agente_preferido')
        await update.message.reply_text(
            '⚙️ *Ajustes*\n\n'
            f'Agente actual: `{agente or "automático"}`',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=inline_ajustes(agente, nivel)
        )
        return
    elif texto == '🔄 Actualizar datos':
        await cmd_actualizar(update, ctx)
        return

    # Actualizar sesión
    db.guardar_sesion(user.id, user.username or '', nombre)

    # Mensaje intermedio si parece búsqueda web
    msg_intermedio = None
    if _es_busqueda_web(texto):
        msg_intermedio = await update.message.reply_text('🔍 Buscando en internet...')

    # Indicador de escritura
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Validar que el agente guardado está permitido para el nivel del usuario
    agente_sesion = sesion.get('agente_preferido')
    agente_slug   = None
    if agente_sesion:
        nivel_min_agente = next(
            (n for _, d, n in AGENTES if agente_sesion in d), 1
        )
        agente_slug = agente_sesion if nivel >= nivel_min_agente else None

    # ── Modo Super Agente (bypass ia_service) ────────────────────────────────
    if agente_slug == 'superagente':
        uid = str(user.id)
        empresa_sa = sesion.get('empresa', 'ori_sil_2')

        # Botón "📝 Nueva" → marcar flag y pedir primera pregunta
        if texto == '📝 Nueva':
            SA_FORZAR_NUEVA.add(uid)
            await update.message.reply_text(
                '🆕 *Nueva conversación*\nEscribí tu primera pregunta.',
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=handlers_sa.teclado_sa()
            )
            return

        # Botón "📋 Conversaciones" → listar
        if texto == '📋 Conversaciones':
            await handlers_sa.listar_conversaciones_msg(
                update, sa_mod, uid, empresa_sa
            )
            return

        # Si el usuario pidió "Nueva conversación", forzar creación
        if uid in SA_FORZAR_NUEVA:
            SA_FORZAR_NUEVA.discard(uid)
            await update.effective_chat.send_action(ChatAction.TYPING)
            resultado = sa_mod.nueva_conversacion(
                pregunta=texto, usuario_id=uid,
                nombre_usuario=nombre, nivel=nivel,
                empresa=empresa_sa
            )
            if not resultado.get('ok'):
                await update.message.reply_text(
                    f'😔 {resultado.get("error", "Error.")}',
                    reply_markup=handlers_sa.teclado_sa()
                )
                return
            await handlers_sa.manejar_superagente(
                update, sa_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
                sesion=sesion, nombre=nombre, nivel=nivel,
                empresa=empresa_sa, pregunta=texto,
                resultado_previo=resultado
            )
            return

        await handlers_sa.manejar_superagente(
            update, sa_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
            sesion=sesion, nombre=nombre, nivel=nivel,
            empresa=empresa_sa, pregunta=texto
        )
        return

    # ── Modo Super Agente OpenCode (bypass ia_service) ────────────────────
    if agente_slug == 'superagente-oc':
        uid = str(user.id)
        empresa_sa = sesion.get('empresa', 'ori_sil_2')

        # Botón "📝 Nueva" → marcar flag y pedir primera pregunta
        if texto == '📝 Nueva':
            SAOC_FORZAR_NUEVA.add(uid)
            await update.message.reply_text(
                '🆕 *Nueva conversación OpenCode*\nEscribí tu primera pregunta.',
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=handlers_sa_oc.teclado_saoc(nivel)
            )
            return

        # Botón "📋 Conversaciones" → listar
        if texto == '📋 Conversaciones':
            await handlers_sa_oc.listar_conversaciones_msg(
                update, saoc_mod, uid, empresa_sa
            )
            return

        # Si el usuario pidió "Nueva conversación", forzar creación
        if uid in SAOC_FORZAR_NUEVA:
            SAOC_FORZAR_NUEVA.discard(uid)
            await update.effective_chat.send_action(ChatAction.TYPING)
            resultado = saoc_mod.nueva_conversacion(
                pregunta=texto, usuario_id=uid,
                nombre_usuario=nombre, nivel=nivel,
                empresa=empresa_sa
            )
            if not resultado.get('ok'):
                await update.message.reply_text(
                    f'😔 {resultado.get("error", "Error.")}',
                    reply_markup=handlers_sa_oc.teclado_saoc(nivel)
                )
                return
            await handlers_sa_oc.manejar_superagente_oc(
                update, saoc_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
                sesion=sesion, nombre=nombre, nivel=nivel,
                empresa=empresa_sa, pregunta=texto,
                resultado_previo=resultado
            )
            return

        await handlers_sa_oc.manejar_superagente_oc(
            update, saoc_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
            sesion=sesion, nombre=nombre, nivel=nivel,
            empresa=empresa_sa, pregunta=texto
        )
        return

    # Llamar ia_service
    resultado = api_ia.consultar(
        pregunta=texto,
        usuario_id=str(user.id),
        nombre_usuario=nombre,
        agente=agente_slug,
        empresa=sesion.get('empresa', 'ori_sil_2'),
        conversacion_id=sesion.get('conversacion_id'),
        canal='telegram'
    )

    # Actualizar conversacion_id en sesión
    if resultado.get('conversacion_id'):
        db.guardar_sesion(user.id, user.username or '', nombre,
                          conversacion_id=resultado['conversacion_id'])

    # Procesar tabla si hay datos
    info       = tabla_mod.procesar_tabla(resultado, texto, sesion.get('empresa', 'ori_sil_2'))
    texto_resp = info['texto']
    token      = info['token']
    n_filas    = info['n_filas']

    # Error del servicio
    if not resultado.get('ok'):
        retry = resultado.get('retry_after')
        if retry:
            msg = f'⏳ Demasiadas consultas seguidas. Intenta en {retry} segundos.'
        else:
            msg = '😔 No pude obtener esa información. Intenta reformular la pregunta o pregúntame algo más.'
        await update.message.reply_text(msg, reply_markup=reply_kb(nivel))
        return

    # Teclado inline
    kb = _inline_datos(token, n_filas) if (token or n_filas > 0) else _inline_solo_nuevo()

    # Pie con agente usado
    agente_usado = resultado.get('agente', '')
    icono = ICONOS_AGENTES.get(agente_usado, '🤖')
    nombre_agente = NOMBRES_AGENTES.get(agente_usado, agente_usado)
    pie   = f'\n\n_{icono} {nombre_agente}_' if agente_usado else ''

    MAX_LEN = 4000
    texto_enviar = texto_resp + pie
    if len(texto_enviar) > MAX_LEN:
        if token:
            # Hay tabla — mandar aviso corto y dejar que el usuario la abra
            texto_enviar = f'El detalle tiene {n_filas} filas — demasiado para mostrar en el chat.\n\nAbrí la tabla para verlo completo con filtros y totales.{pie}'
        else:
            texto_enviar = texto_resp[:MAX_LEN] + '\n\n_… respuesta recortada._'

    try:
        if msg_intermedio:
            # Editar el mensaje "Buscando..." con la respuesta final
            try:
                await msg_intermedio.edit_text(
                    texto_enviar,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb
                )
            except Exception:
                await msg_intermedio.edit_text(texto_enviar[:MAX_LEN], reply_markup=kb)
        else:
            await update.message.reply_text(
                texto_enviar,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
    except Exception:
        await update.message.reply_text(texto_enviar[:MAX_LEN], reply_markup=kb)


# ─── Handler de fotos (visión) ───────────────────────────────────────────────

async def handle_foto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user

    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    # Super Agente: guardar imagen en /tmp y pasarla como ruta en el prompt
    if sesion.get('agente_preferido') == 'superagente':
        await update.effective_chat.send_action(ChatAction.TYPING)
        foto    = update.message.photo[-1]
        archivo = await foto.get_file()
        ts      = int(__import__('time').time())
        ruta    = f'/tmp/sa_foto_{user.id}_{ts}.jpg'
        await archivo.download_to_drive(ruta)
        caption = (update.message.caption or '').strip()
        if caption:
            prompt = f'{caption}\n\n[Se envía imagen adjunta en: {ruta} — revisala como parte del mensaje]'
        else:
            prompt = f'[Se envía imagen adjunta en: {ruta} — revisala como parte del mensaje]'
        nombre_u = sesion.get('nombre') or _nombre(user)
        nivel    = sesion.get('nivel', 1)
        empresa  = sesion.get('empresa', 'ori_sil_2')
        await handlers_sa.manejar_superagente(
            update, sa_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
            sesion=sesion, nombre=nombre_u, nivel=nivel,
            empresa=empresa, pregunta=prompt
        )
        return

    # Super Agente OpenCode: guardar imagen en /tmp y pasarla como ruta
    if sesion.get('agente_preferido') == 'superagente-oc':
        await update.effective_chat.send_action(ChatAction.TYPING)
        foto    = update.message.photo[-1]
        archivo = await foto.get_file()
        ts      = int(__import__('time').time())
        ruta    = f'/home/osserver/Proyectos_Antigravity/sa_opencode/uploads/foto_{user.id}_{ts}.jpg'
        await archivo.download_to_drive(ruta)
        caption = (update.message.caption or '').strip()
        if caption:
            prompt = f'{caption}\n\n[Se envía imagen adjunta en: {ruta} — revisala como parte del mensaje]'
        else:
            prompt = f'[Se envía imagen adjunta en: {ruta} — revisala como parte del mensaje]'
        nombre_u = sesion.get('nombre') or _nombre(user)
        nivel    = sesion.get('nivel', 1)
        empresa  = sesion.get('empresa', 'ori_sil_2')
        await handlers_sa_oc.manejar_superagente_oc(
            update, saoc_mod, tabla_mod, _inline_datos, _inline_solo_nuevo,
            sesion=sesion, nombre=nombre_u, nivel=nivel,
            empresa=empresa, pregunta=prompt, con_imagen=True
        )
        return

    nombre = sesion.get('nombre') or _nombre(user)
    await update.effective_chat.send_action(ChatAction.TYPING)

    foto    = update.message.photo[-1]
    archivo = await foto.get_file()
    buf     = io.BytesIO()
    await archivo.download_to_memory(buf)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    caption = (update.message.caption or '').strip()

    db.guardar_sesion(user.id, user.username or '', nombre)

    resultado = api_ia.consultar(
        pregunta        = caption,
        usuario_id      = str(user.id),
        nombre_usuario  = nombre,
        agente          = sesion.get('agente_preferido'),
        empresa         = sesion.get('empresa', 'ori_sil_2'),
        conversacion_id = sesion.get('conversacion_id'),
        canal           = 'telegram',
        imagen_b64      = img_b64,
        imagen_mime     = 'image/jpeg',
    )

    if resultado.get('conversacion_id'):
        db.guardar_sesion(user.id, user.username or '', nombre,
                          conversacion_id=resultado['conversacion_id'])

    info       = tabla_mod.procesar_tabla(resultado, caption, sesion.get('empresa', 'ori_sil_2'))
    texto_resp = info['texto']
    token      = info['token']
    n_filas    = info['n_filas']

    if not resultado.get('ok'):
        await update.message.reply_text(
            '😔 No pude procesar la imagen. Intenta de nuevo o envíala con una instrucción.',
            reply_markup=reply_kb(sesion.get('nivel', 1))
        )
        return

    kb     = _inline_datos(token, n_filas) if (token or n_filas > 0) else _inline_solo_nuevo()
    agente_usado = resultado.get('agente', '')
    nombre_ag = NOMBRES_AGENTES.get(agente_usado, agente_usado)
    pie    = f'\n\n_{ICONOS_AGENTES.get(agente_usado,"🤖")} {nombre_ag}_' if agente_usado else ''

    try:
        await update.message.reply_text(
            texto_resp + pie,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception:
        await update.message.reply_text(texto_resp, reply_markup=kb)


# ─── Handler de voz (Whisper) ────────────────────────────────────────────────

async def handle_voz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = await _verificar_acceso(update)
    if not sesion:
        return

    await update.effective_chat.send_action(ChatAction.TYPING)

    # Descargar y transcribir audio
    voz     = update.message.voice or update.message.audio
    archivo = await voz.get_file()
    buf     = io.BytesIO()
    await archivo.download_to_memory(buf)
    texto = whisper_mod.transcribir(buf.getvalue(), 'audio.ogg')

    if not texto:
        await update.message.reply_text(
            '😔 No pude entender el audio. Intenta de nuevo o escribe tu pregunta.',
            reply_markup=reply_kb(sesion.get('nivel', 1))
        )
        return

    # Mostrar transcripción
    await update.message.reply_text(
        f'🎙️ _Escuché:_ "{_escape(texto)}"',
        parse_mode=ParseMode.MARKDOWN_V2
    )

    # Procesar exactamente igual que un mensaje de texto
    await handle_mensaje(update, ctx, texto_override=texto)


# ─── Handler de callbacks (botones inline) ───────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = query.from_user

    sesion = db.obtener_sesion(user.id)
    nivel  = sesion.get('nivel', 1)

    if data == 'nueva_consulta':
        await query.message.reply_text(
            '¿Sobre qué quieres consultar ahora?',
            reply_markup=reply_kb(sesion.get('nivel', 1))
        )

    elif data == 'limpiar_historial':
        db.guardar_sesion(user.id, user.username or '', _nombre(user), conversacion_id=0)
        await query.edit_message_text('🗑️ Historial limpiado. Empezamos de cero.')

    elif data == 'cerrar':
        await query.edit_message_text('✅ Ajustes cerrados.')

    elif data.startswith('agente:'):
        agente = data.split(':', 1)[1]

        # Verificar nivel de acceso para el agente
        nivel_min = next((n for _, d, n in AGENTES if agente in d), 1)
        if nivel < nivel_min:
            await query.answer('No tienes acceso a este agente.', show_alert=True)
            return

        db.guardar_sesion(user.id, user.username or '', _nombre(user),
                          agente_preferido=agente)
        if agente == 'superagente':
            await query.edit_message_text(
                f'✅ Agente cambiado a *{NOMBRES_AGENTES.get(agente, agente)}*\n\n'
                'Ya puedes hacer tu próxima consulta.',
                parse_mode=ParseMode.MARKDOWN
            )
            await query.message.reply_text(
                '🦾 Modo Super Agente activo.',
                reply_markup=handlers_sa.teclado_sa()
            )
        elif agente == 'superagente-oc':
            await query.edit_message_text(
                f'✅ Agente cambiado a *{NOMBRES_AGENTES.get(agente, agente)}*\n\n'
                'Ya puedes hacer tu próxima consulta.',
                parse_mode=ParseMode.MARKDOWN
            )
            await query.message.reply_text(
                '🧩 Modo Super Agente OpenCode activo.',
                reply_markup=handlers_sa_oc.teclado_saoc(nivel)
            )
        else:
            await query.edit_message_text(
                f'✅ Agente cambiado a *{NOMBRES_AGENTES.get(agente, agente)}*\n\n'
                'Ya puedes hacer tu próxima consulta.',
                parse_mode=ParseMode.MARKDOWN
            )

    elif data.startswith('saoc_'):
        await handlers_sa_oc.handle_saoc_callback(query, user, nivel, _nombre(user), saoc_mod)

    elif data.startswith('sa_'):
        await handlers_sa.handle_sa_callback(query, user, nivel, _nombre(user), sa_mod)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        log.error('TELEGRAM_BOT_TOKEN no configurado en .env')
        sys.exit(1)

    log.info('Iniciando OS IA Bot...')
    db.limpiar_tablas_viejas()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start',      cmd_start))
    app.add_handler(CommandHandler('ayuda',      cmd_ayuda))
    app.add_handler(CommandHandler('help',       cmd_ayuda))
    app.add_handler(CommandHandler('estado',     cmd_estado))
    app.add_handler(CommandHandler('agente',     cmd_agente))
    app.add_handler(CommandHandler('limpiar',    cmd_limpiar))
    app.add_handler(CommandHandler('actualizar', cmd_actualizar))
    app.add_handler(CommandHandler('ventas',     cmd_ventas))
    app.add_handler(CommandHandler('mes',        cmd_mes))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contacto))
    app.add_handler(MessageHandler(filters.PHOTO, handle_foto))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voz))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensaje))

    log.info('Bot corriendo — polling...')
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
