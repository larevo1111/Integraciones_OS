"""
Constructores de teclados para el bot.
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# ── Reply keyboard — siempre visible en el fondo ─────────────────────────────
REPLY_KB = ReplyKeyboardMarkup(
    [['📊 Ventas hoy', '📈 Este mes', '⚙️ Ajustes']],
    resize_keyboard=True,
    input_field_placeholder='Escribe tu pregunta...'
)


def inline_respuesta(token: str = None, n_filas: int = 0) -> InlineKeyboardMarkup | None:
    """
    Botones inline debajo de cada respuesta con datos.
    """
    botones = []

    if token and n_filas > MAX_INLINE:
        botones.append(
            InlineKeyboardButton(
                f'📋 Ver tabla completa ({n_filas} filas)',
                web_app=None,  # Se setea en bot.py con WebAppInfo
                url=f'https://menu.oscomunidad.com/bot/tabla?token={token}'
            )
        )

    botones.append(InlineKeyboardButton('↩ Nueva consulta', callback_data='nueva_consulta'))

    return InlineKeyboardMarkup([botones]) if botones else None


MAX_INLINE = 5


def inline_ajustes(agente_actual: str = None) -> InlineKeyboardMarkup:
    agentes = [
        ('💡 DeepSeek Chat ★ recomendado', 'agente:deepseek-chat'),
        ('🧠 Gemini Pro (análisis profundo)', 'agente:gemini-pro'),
        ('⚡ Gemini Flash (rápido)', 'agente:gemini-flash'),
        ('🤖 Claude Sonnet (premium)', 'agente:claude-sonnet'),
    ]
    filas = []
    for label, data in agentes:
        prefix = '✓ ' if agente_actual and agente_actual in data else ''
        filas.append([InlineKeyboardButton(prefix + label, callback_data=data)])

    filas.append([
        InlineKeyboardButton('🗑️ Limpiar historial', callback_data='limpiar_historial'),
        InlineKeyboardButton('❌ Cerrar', callback_data='cerrar'),
    ])
    return InlineKeyboardMarkup(filas)
