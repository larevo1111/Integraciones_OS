"""
Constructores de teclados para el bot.
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ── Reply keyboard — siempre visible en el fondo ─────────────────────────────
# Versión estática para contextos sin nivel (ej: pantalla de auth)
REPLY_KB = ReplyKeyboardMarkup(
    [['📊 Ventas hoy', '📈 Este mes', '⚙️ Ajustes']],
    resize_keyboard=True,
    input_field_placeholder='Escribe tu pregunta...'
)


def reply_kb(nivel: int = 1) -> ReplyKeyboardMarkup:
    """Keyboard dinámico — nivel 5+ ve el botón Actualizar datos."""
    filas = [['📊 Ventas hoy', '📈 Este mes', '⚙️ Ajustes']]
    if nivel >= 5:
        filas.append(['🔄 Actualizar datos'])
    return ReplyKeyboardMarkup(
        filas,
        resize_keyboard=True,
        input_field_placeholder='Escribe tu pregunta...'
    )

MAX_INLINE = 5

# Todos los agentes seleccionables: (label, callback_data, nivel_minimo)
AGENTES = [
    ('⚡ Gemini Flash ★ recomendado', 'agente:gemini-flash',  1),
    ('🧪 GPT-OSS 120B (análisis)',    'agente:gpt-oss-120b',  1),
    ('💡 DeepSeek Chat (económico)',  'agente:deepseek-chat', 1),
    ('🧠 Gemini Pro (premium)',       'agente:gemini-pro',    6),
    ('🤖 Claude Sonnet (premium)',    'agente:claude-sonnet', 6),
]


def inline_ajustes(agente_actual: str = None, nivel: int = 1) -> InlineKeyboardMarkup:
    """
    Menú de selección de agente filtrado por nivel del usuario.
    Agentes premium (nivel 6+) solo se muestran a quienes tienen acceso.
    """
    filas = []
    for label, data, nivel_min in AGENTES:
        if nivel < nivel_min:
            continue
        prefix = '✓ ' if agente_actual and agente_actual in data else ''
        filas.append([InlineKeyboardButton(prefix + label, callback_data=data)])

    filas.append([
        InlineKeyboardButton('🗑️ Limpiar historial', callback_data='limpiar_historial'),
        InlineKeyboardButton('❌ Cerrar', callback_data='cerrar'),
    ])
    return InlineKeyboardMarkup(filas)


def inline_respuesta(token: str = None, n_filas: int = 0) -> InlineKeyboardMarkup | None:
    botones = []
    if token and n_filas > MAX_INLINE:
        botones.append(
            InlineKeyboardButton(
                f'📋 Ver tabla ({n_filas} filas)',
                web_app=WebAppInfo(url=f'https://menu.oscomunidad.com/bot/tabla?token={token}')
            )
        )
    botones.append(InlineKeyboardButton('↩ Nueva consulta', callback_data='nueva_consulta'))
    return InlineKeyboardMarkup([botones]) if botones else None


def teclado_compartir_telefono() -> ReplyKeyboardMarkup:
    """Teclado que le pide al usuario compartir su número de teléfono."""
    from telegram import KeyboardButton
    return ReplyKeyboardMarkup(
        [[KeyboardButton('📱 Compartir mi número', request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
