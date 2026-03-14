"""
OS IA — Bot de Telegram
python-telegram-bot v20 (async)

Arranca con:
  python3 scripts/telegram_bot/bot.py
"""
import sys, os, logging, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction

import api_ia, db, tabla as tabla_mod
from teclado import REPLY_KB, inline_ajustes, MAX_INLINE

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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _nombre(user) -> str:
    return user.first_name or user.username or str(user.id)


def _escape(texto: str) -> str:
    """Escapa caracteres especiales para MarkdownV2."""
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
    nombre = _nombre(user)
    db.guardar_sesion(user.id, user.username or '', nombre)
    await update.message.reply_text(
        f'¡Hola {nombre}! 👋\n\n'
        'Soy el asistente IA de Origen Silvestre. Pregúntame lo que quieras sobre ventas, '
        'productos, clientes o cualquier dato del negocio.\n\n'
        'Escribe tu pregunta directamente o usa los botones de abajo.',
        reply_markup=REPLY_KB
    )


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📖 *Cómo usar el bot*\n\n'
        'Escribe cualquier pregunta en lenguaje natural. Ejemplos:\n'
        '  _¿Cuánto vendimos en febrero?_\n'
        '  _Top 5 productos del mes pasado_\n'
        '  _¿Qué clientes compraron más este año?_\n\n'
        '*Comandos disponibles:*\n'
        '/ventas — Ventas del día de hoy\n'
        '/mes — Resumen del mes en curso\n'
        '/estado — Ver agente activo\n'
        '/agente — Cambiar modelo de IA\n'
        '/limpiar — Limpiar historial\n'
        '/ayuda — Ver esta ayuda',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=REPLY_KB
    )


async def cmd_estado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = db.obtener_sesion(update.effective_user.id)
    agente = sesion.get('agente_preferido') or 'automático'
    nombres = {
        'gemini-flash':   'Gemini Flash ⚡ (rápido, gratis)',
        'gemini-pro':     'Gemini Pro 🧠 (análisis)',
        'claude-sonnet':  'Claude Sonnet 🤖 (premium)',
        'deepseek-chat':  'DeepSeek Chat 💡 (económico)',
        'automático':     'Automático 🔀 (el sistema elige según la pregunta)',
    }
    await update.message.reply_text(
        '📊 *Estado actual*\n\n'
        f'🤖 Agente: {nombres.get(agente, agente)}\n'
        f'🏢 Empresa: Origen Silvestre\n\n'
        'Usa /agente para cambiar el modelo.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=REPLY_KB
    )


async def cmd_agente(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sesion = db.obtener_sesion(update.effective_user.id)
    agente = sesion.get('agente_preferido')
    await update.message.reply_text(
        '🤖 *Selecciona el agente de IA*\n\n'
        '💡 *DeepSeek Chat* — recomendado para uso diario. Excelente para análisis de datos, muy económico.\n'
        '🧠 *Gemini Pro* — análisis profundo, contexto masivo.\n'
        '⚡ *Gemini Flash* — respuestas rápidas.\n'
        '🤖 *Claude Sonnet* — mejor tono conversacional.',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=inline_ajustes(agente)
    )


async def cmd_limpiar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.guardar_sesion(user.id, user.username or '', _nombre(user), conversacion_id=0)
    await update.message.reply_text(
        '🗑️ Historial limpiado. La próxima pregunta empieza desde cero.',
        reply_markup=REPLY_KB
    )


async def cmd_ventas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    update.message.text = '¿Cuánto hemos vendido hoy?'
    await handle_mensaje(update, ctx)


async def cmd_mes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    update.message.text = '¿Cuánto llevamos vendido este mes y cómo vamos vs el mes anterior?'
    await handle_mensaje(update, ctx)


# ─── Handler principal de mensajes ───────────────────────────────────────────

async def handle_mensaje(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    texto   = update.message.text.strip()
    nombre  = _nombre(user)

    # Shortcuts de los botones rápidos
    if texto == '📊 Ventas hoy':
        texto = '¿Cuánto hemos vendido hoy?'
    elif texto == '📈 Este mes':
        texto = '¿Cuánto llevamos vendido este mes y cómo vamos vs el mes anterior?'
    elif texto == '⚙️ Ajustes':
        sesion = db.obtener_sesion(user.id)
        agente = sesion.get('agente_preferido')
        await update.message.reply_text(
            '⚙️ *Ajustes*\n\n'
            f'Agente actual: `{agente or "automático"}`',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=inline_ajustes(agente)
        )
        return

    # Registrar / actualizar sesión
    sesion = db.obtener_sesion(user.id)
    db.guardar_sesion(user.id, user.username or '', nombre)

    # Indicador de escritura
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Llamar ia_service
    resultado = api_ia.consultar(
        pregunta=texto,
        usuario_id=str(user.id),
        nombre_usuario=nombre,
        agente=sesion.get('agente_preferido'),
        empresa=sesion.get('empresa', 'ori_sil_2'),
        conversacion_id=sesion.get('conversacion_id'),
        canal='telegram'
    )

    # Actualizar conversacion_id en sesión
    if resultado.get('conversacion_id'):
        db.guardar_sesion(user.id, user.username or '', nombre,
                          conversacion_id=resultado['conversacion_id'])

    # Procesar tabla si hay datos
    info = tabla_mod.procesar_tabla(resultado, texto,
                                    sesion.get('empresa', 'ori_sil_2'))
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
        await update.message.reply_text(msg, reply_markup=REPLY_KB)
        return

    # Construir teclado inline
    if token or n_filas > 0:
        kb = _inline_datos(token, n_filas)
    else:
        kb = _inline_solo_nuevo()

    # Pie sutil con el agente usado
    agente_usado = resultado.get('agente', '')
    iconos = {
        'gemini-pro':    '🧠', 'gemini-flash': '⚡',
        'gemini-flash-lite': '⚡', 'claude-sonnet': '🤖',
        'deepseek-chat': '💡', 'deepseek-reasoner': '💡',
        'groq-llama': '🔥', 'gemma-router': '🔀',
    }
    icono = iconos.get(agente_usado, '🤖')
    pie   = f'\n\n_{icono} {agente_usado}_' if agente_usado else ''

    # Enviar respuesta — intentar Markdown, caer a texto plano si falla
    try:
        await update.message.reply_text(
            texto_resp + pie,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception:
        await update.message.reply_text(
            texto_resp,
            reply_markup=kb
        )


# ─── Handler de callbacks (botones inline) ───────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = query.from_user

    if data == 'nueva_consulta':
        await query.message.reply_text(
            '¿Sobre qué quieres consultar ahora?',
            reply_markup=REPLY_KB
        )

    elif data == 'limpiar_historial':
        db.guardar_sesion(user.id, user.username or '', _nombre(user),
                          conversacion_id=0)
        await query.edit_message_text('🗑️ Historial limpiado. Empezamos de cero.')

    elif data == 'cerrar':
        await query.edit_message_text('✅ Ajustes cerrados.')

    elif data.startswith('agente:'):
        agente = data.split(':', 1)[1]
        db.guardar_sesion(user.id, user.username or '', _nombre(user),
                          agente_preferido=agente)
        nombres = {
            'gemini-flash':    'Gemini Flash ⚡',
            'gemini-pro':      'Gemini Pro 🧠',
            'claude-sonnet':   'Claude Sonnet 🤖',
            'deepseek-chat':   'DeepSeek Chat 💡',
        }
        await query.edit_message_text(
            f'✅ Agente cambiado a *{nombres.get(agente, agente)}*\n\n'
            'Ya puedes hacer tu próxima consulta.',
            parse_mode=ParseMode.MARKDOWN
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        log.error('TELEGRAM_BOT_TOKEN no configurado en .env')
        sys.exit(1)

    log.info('Iniciando OS IA Bot...')
    db.limpiar_tablas_viejas()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start',   cmd_start))
    app.add_handler(CommandHandler('ayuda',   cmd_ayuda))
    app.add_handler(CommandHandler('help',    cmd_ayuda))
    app.add_handler(CommandHandler('estado',  cmd_estado))
    app.add_handler(CommandHandler('agente',  cmd_agente))
    app.add_handler(CommandHandler('limpiar', cmd_limpiar))
    app.add_handler(CommandHandler('ventas',  cmd_ventas))
    app.add_handler(CommandHandler('mes',     cmd_mes))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensaje))

    log.info('Bot corriendo — polling...')
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
