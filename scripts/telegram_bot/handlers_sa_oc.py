"""
handlers_sa_oc.py — Handlers de Telegram para el Super Agente OpenCode.
Menú propio: [📝 Nueva] [📋 Conversaciones] [⚙️ Ajustes]
Gestión de conversaciones: listar, cambiar, renombrar, borrar.
Usado por: telegram_bot/bot.py
"""
import logging
from telegram import (Update, InlineKeyboardMarkup, InlineKeyboardButton,
                      ReplyKeyboardMarkup, KeyboardButton)
from telegram.constants import ParseMode

log = logging.getLogger('os_ia_bot')

# Estado temporal para renombrado (usuario_id → sesion_id)
_esperando_renombrar_oc = {}


# ── Teclado del Super Agente OpenCode ────────────────────────────────────────

def teclado_saoc():
    """Teclado reply inferior del Super Agente OpenCode."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton('📝 Nueva'), KeyboardButton('📋 Conversaciones'),
          KeyboardButton('⚙️ Ajustes')]],
        resize_keyboard=True
    )


# ── Handler principal de mensajes ────────────────────────────────────────────

async def manejar_superagente_oc(update: Update, saoc_mod, tabla_mod,
                                  inline_datos_fn, inline_solo_nuevo_fn,
                                  sesion: dict, nombre: str, nivel: int,
                                  empresa: str, pregunta: str,
                                  resultado_previo: dict = None):
    """Procesa texto en modo Super Agente OpenCode."""
    from telegram.constants import ChatAction
    user = update.effective_user
    uid = str(user.id)

    # ¿Esperando renombrar?
    if uid in _esperando_renombrar_oc:
        sesion_id = _esperando_renombrar_oc.pop(uid)
        saoc_mod.renombrar_conversacion(sesion_id, pregunta[:100])
        await update.message.reply_text(
            f'✅ Conversación renombrada a: *{pregunta[:100]}*',
            parse_mode=ParseMode.MARKDOWN, reply_markup=teclado_saoc()
        )
        return

    # Si viene resultado_previo (de nueva_conversacion), usarlo directo
    if resultado_previo:
        resultado = resultado_previo
    else:
        # Consulta normal al Super Agente OpenCode
        await update.effective_chat.send_action(ChatAction.TYPING)
        resultado = saoc_mod.consultar(
            pregunta=pregunta, usuario_id=uid,
            nombre_usuario=nombre, nivel=nivel, empresa=empresa,
        )

    if not resultado.get('ok'):
        await update.message.reply_text(
            f'😔 {resultado.get("error", "Error en el Super Agente OpenCode.")}',
            reply_markup=teclado_saoc()
        )
        return

    tipo = resultado['tipo']

    if tipo == 'tabla':
        data = resultado['contenido']
        res_fake = {
            'ok': True,
            'respuesta': data.get('texto', ''),
            'tabla': {
                'columnas': data.get('columnas', []),
                'filas': data.get('filas', []),
                'titulo': data.get('titulo', ''),
            }
        }
        info = tabla_mod.procesar_tabla(res_fake, pregunta, empresa)
        kb = inline_datos_fn(info['token'], info['n_filas']) if info['token'] else inline_solo_nuevo_fn()
        try:
            await update.message.reply_text(
                info['texto'] + '\n\n_🧩 Super Agente OpenCode_',
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            await update.message.reply_text(info['texto'], reply_markup=kb)
        return

    # Texto plano
    try:
        await update.message.reply_text(
            str(resultado['contenido']) + '\n\n_🧩 Super Agente OpenCode_',
            parse_mode=ParseMode.MARKDOWN, reply_markup=teclado_saoc()
        )
    except Exception:
        await update.message.reply_text(
            str(resultado['contenido']), reply_markup=teclado_saoc()
        )


# ── Listar / cambiar / renombrar / borrar ────────────────────────────────────

async def listar_conversaciones_msg(update, saoc_mod, uid, empresa):
    """Muestra lista de conversaciones (llamada desde bot.py)."""
    return await _listar_conversaciones(update, saoc_mod, uid, empresa)


async def _listar_conversaciones(update, saoc_mod, uid, empresa):
    convs = saoc_mod.listar_conversaciones(uid, empresa)
    if not convs:
        await update.message.reply_text(
            'No tenés conversaciones. Escribí una pregunta para empezar.',
            reply_markup=teclado_saoc()
        )
        return

    botones = []
    for c in convs:
        marca = '● ' if c['activa'] else '○ '
        label = f'{marca}{c["nombre"]}'
        botones.append([InlineKeyboardButton(label, callback_data=f'saoc_conv:{c["id"]}')])

    await update.message.reply_text(
        '📋 *Tus conversaciones OpenCode*\n● = activa',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(botones)
    )


async def _mostrar_opciones_conv(query, saoc_mod, sesion_id, uid, empresa):
    """Muestra opciones para una conversación seleccionada."""
    convs = saoc_mod.listar_conversaciones(uid, empresa)
    conv = next((c for c in convs if c['id'] == sesion_id), None)
    if not conv:
        await query.answer('Conversación no encontrada.', show_alert=True)
        return

    botones = [
        [InlineKeyboardButton('🔄 Cambiar a esta', callback_data=f'saoc_switch:{sesion_id}')],
        [InlineKeyboardButton('✏️ Renombrar', callback_data=f'saoc_rename:{sesion_id}'),
         InlineKeyboardButton('🗑️ Borrar', callback_data=f'saoc_delete:{sesion_id}')],
        [InlineKeyboardButton('« Volver', callback_data='saoc_convlist')],
    ]
    await query.edit_message_text(
        f'📌 *{conv["nombre"]}*\n'
        f'Creada: {conv["created_at"].strftime("%d/%m %H:%M") if conv.get("created_at") else "?"}',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(botones)
    )


# ── Callback handler ────────────────────────────────────────────────────────

async def handle_saoc_callback(query, user, nivel: int, nombre: str, saoc_mod):
    """Procesa todos los callbacks saoc_*."""
    data = query.data
    uid = str(user.id)
    empresa = 'ori_sil_2'

    # Seleccionar conversación → mostrar opciones
    if data.startswith('saoc_conv:'):
        sesion_id = int(data.split(':')[1])
        await _mostrar_opciones_conv(query, saoc_mod, sesion_id, uid, empresa)
        return

    # Volver a lista
    if data == 'saoc_convlist':
        convs = saoc_mod.listar_conversaciones(uid, empresa)
        botones = []
        for c in convs:
            marca = '● ' if c['activa'] else '○ '
            botones.append([InlineKeyboardButton(
                f'{marca}{c["nombre"]}', callback_data=f'saoc_conv:{c["id"]}'
            )])
        await query.edit_message_text(
            '📋 *Tus conversaciones OpenCode*\n● = activa',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(botones)
        )
        return

    # Cambiar conversación activa
    if data.startswith('saoc_switch:'):
        sesion_id = int(data.split(':')[1])
        saoc_mod.cambiar_conversacion(uid, empresa, sesion_id)
        convs = saoc_mod.listar_conversaciones(uid, empresa)
        conv = next((c for c in convs if c['id'] == sesion_id), None)
        nombre_conv = conv['nombre'] if conv else '?'
        await query.edit_message_text(f'✅ Conversación activa: *{nombre_conv}*',
                                       parse_mode=ParseMode.MARKDOWN)
        return

    # Renombrar
    if data.startswith('saoc_rename:'):
        sesion_id = int(data.split(':')[1])
        _esperando_renombrar_oc[uid] = sesion_id
        await query.edit_message_text('✏️ Escribí el nuevo nombre:')
        return

    # Borrar
    if data.startswith('saoc_delete:'):
        sesion_id = int(data.split(':')[1])
        nombre_borrado = saoc_mod.borrar_conversacion(sesion_id, uid)
        if nombre_borrado:
            await query.edit_message_text(f'🗑️ Conversación "*{nombre_borrado}*" borrada.',
                                           parse_mode=ParseMode.MARKDOWN)
        else:
            await query.answer('No se encontró la conversación.', show_alert=True)
        return
