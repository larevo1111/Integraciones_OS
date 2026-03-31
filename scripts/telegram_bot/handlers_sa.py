"""
handlers_sa.py — Handlers de Telegram para el Super Agente.
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
_esperando_renombrar = {}


# ── Teclado del Super Agente ─────────────────────────────────────────────────

def teclado_sa():
    """Teclado reply inferior del Super Agente."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton('📝 Nueva'), KeyboardButton('📋 Conversaciones'),
          KeyboardButton('⚙️ Ajustes')]],
        resize_keyboard=True
    )


# ── Handler principal de mensajes ────────────────────────────────────────────

async def manejar_superagente(update: Update, sa_mod, tabla_mod,
                               inline_datos_fn, inline_solo_nuevo_fn,
                               sesion: dict, nombre: str, nivel: int,
                               empresa: str, pregunta: str,
                               resultado_previo: dict = None):
    """Procesa texto en modo Super Agente."""
    from telegram.constants import ChatAction
    user = update.effective_user
    uid = str(user.id)

    # ¿Esperando renombrar?
    if uid in _esperando_renombrar:
        sesion_id = _esperando_renombrar.pop(uid)
        sa_mod.renombrar_conversacion(sesion_id, pregunta[:100])
        await update.message.reply_text(
            f'✅ Conversación renombrada a: *{pregunta[:100]}*',
            parse_mode=ParseMode.MARKDOWN, reply_markup=teclado_sa()
        )
        return

    # Si viene resultado_previo (de nueva_conversacion), usarlo directo
    if resultado_previo:
        resultado = resultado_previo
    else:
        # Consulta normal al Super Agente
        await update.effective_chat.send_action(ChatAction.TYPING)
        resultado = sa_mod.consultar(
            pregunta=pregunta, usuario_id=uid,
            nombre_usuario=nombre, nivel=nivel, empresa=empresa,
        )

    if not resultado.get('ok'):
        await update.message.reply_text(
            f'😔 {resultado.get("error", "Error en el Super Agente.")}',
            reply_markup=teclado_sa()
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
                info['texto'] + '\n\n_🦾 Super Agente_',
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            await update.message.reply_text(info['texto'], reply_markup=kb)
        return

    if tipo == 'aprobacion':
        data = resultado['contenido']
        ids7 = resultado.get('ids_nivel7', [])
        await update.message.reply_text(
            f'⚙️ {data.get("mensaje_usuario", "Necesito un cambio de código/estructura.")}\n'
            '_Solicitud enviada a Santiago._',
            parse_mode=ParseMode.MARKDOWN, reply_markup=teclado_sa()
        )
        kb_apr = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Aprobar', callback_data=f'sa_aprobar:{user.id}'),
            InlineKeyboardButton('❌ Rechazar', callback_data=f'sa_rechazar:{user.id}'),
        ]])
        texto = (
            f'🔧 <b>Super Agente — Solicitud de aprobación</b>\n\n'
            f'<b>Qué:</b> {data.get("descripcion", "")}\n'
            f'<b>Causa raíz:</b> {data.get("causa_raiz", "")}\n'
            f'<b>Cambio propuesto:</b>\n<code>{data.get("cambio_propuesto", "")}</code>\n\n'
            f'<b>Solicitado por:</b> {nombre} (nivel {nivel})'
        )
        bot_obj = update.get_bot()
        for tid in ids7:
            try:
                await bot_obj.send_message(chat_id=tid, text=texto,
                                           parse_mode=ParseMode.HTML, reply_markup=kb_apr)
            except Exception as e:
                log.warning(f'No se pudo notificar nivel7 {tid}: {e}')
        return

    # Texto plano
    try:
        await update.message.reply_text(
            str(resultado['contenido']) + '\n\n_🦾 Super Agente_',
            parse_mode=ParseMode.MARKDOWN, reply_markup=teclado_sa()
        )
    except Exception:
        await update.message.reply_text(
            str(resultado['contenido']), reply_markup=teclado_sa()
        )


# ── Listar / cambiar / renombrar / borrar ────────────────────────────────────

async def listar_conversaciones_msg(update, sa_mod, uid, empresa):
    """Muestra lista de conversaciones (llamada desde bot.py)."""
    return await _listar_conversaciones(update, sa_mod, uid, empresa)


async def _listar_conversaciones(update, sa_mod, uid, empresa):
    convs = sa_mod.listar_conversaciones(uid, empresa)
    if not convs:
        await update.message.reply_text(
            'No tenés conversaciones. Escribí una pregunta para empezar.',
            reply_markup=teclado_sa()
        )
        return

    botones = []
    for c in convs:
        marca = '● ' if c['activa'] else '○ '
        label = f'{marca}{c["nombre"]}'
        botones.append([InlineKeyboardButton(label, callback_data=f'sa_conv:{c["id"]}')])

    await update.message.reply_text(
        '📋 *Tus conversaciones*\n● = activa',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(botones)
    )


async def _mostrar_opciones_conv(query, sa_mod, sesion_id, uid, empresa):
    """Muestra opciones para una conversación seleccionada."""
    convs = sa_mod.listar_conversaciones(uid, empresa)
    conv = next((c for c in convs if c['id'] == sesion_id), None)
    if not conv:
        await query.answer('Conversación no encontrada.', show_alert=True)
        return

    botones = [
        [InlineKeyboardButton('🔄 Cambiar a esta', callback_data=f'sa_switch:{sesion_id}')],
        [InlineKeyboardButton('✏️ Renombrar', callback_data=f'sa_rename:{sesion_id}'),
         InlineKeyboardButton('🗑️ Borrar', callback_data=f'sa_delete:{sesion_id}')],
        [InlineKeyboardButton('« Volver', callback_data='sa_convlist')],
    ]
    await query.edit_message_text(
        f'📌 *{conv["nombre"]}*\n'
        f'Creada: {conv["created_at"].strftime("%d/%m %H:%M") if conv.get("created_at") else "?"}',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(botones)
    )


# ── Callback handler ────────────────────────────────────────────────────────

async def handle_sa_callback(query, user, nivel: int, nombre: str, sa_mod):
    """Procesa todos los callbacks sa_*."""
    data = query.data
    uid = str(user.id)
    empresa = 'ori_sil_2'

    # Aprobar / rechazar cambio de código
    if data.startswith('sa_aprobar:') or data.startswith('sa_rechazar:'):
        if nivel < 7:
            await query.answer('Solo nivel 7 puede aprobar.', show_alert=True)
            return
        accion = 'aprobado' if data.startswith('sa_aprobar:') else 'rechazado'
        solicitante = data.split(':', 1)[1]
        emoji = '✅' if accion == 'aprobado' else '❌'
        try:
            await query.edit_message_text(
                query.message.text + f'\n\n{emoji} {accion.upper()} por {nombre}',
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        try:
            await query.get_bot().send_message(
                chat_id=solicitante,
                text=f'{emoji} Santiago {accion} el cambio solicitado.'
            )
        except Exception as e:
            log.warning(f'No se pudo notificar solicitante {solicitante}: {e}')
        return

    # Seleccionar conversación → mostrar opciones
    if data.startswith('sa_conv:'):
        sesion_id = int(data.split(':')[1])
        await _mostrar_opciones_conv(query, sa_mod, sesion_id, uid, empresa)
        return

    # Volver a lista
    if data == 'sa_convlist':
        convs = sa_mod.listar_conversaciones(uid, empresa)
        botones = []
        for c in convs:
            marca = '● ' if c['activa'] else '○ '
            botones.append([InlineKeyboardButton(
                f'{marca}{c["nombre"]}', callback_data=f'sa_conv:{c["id"]}'
            )])
        await query.edit_message_text(
            '📋 *Tus conversaciones*\n● = activa',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(botones)
        )
        return

    # Cambiar conversación activa
    if data.startswith('sa_switch:'):
        sesion_id = int(data.split(':')[1])
        sa_mod.cambiar_conversacion(uid, empresa, sesion_id)
        convs = sa_mod.listar_conversaciones(uid, empresa)
        conv = next((c for c in convs if c['id'] == sesion_id), None)
        nombre_conv = conv['nombre'] if conv else '?'
        await query.edit_message_text(f'✅ Conversación activa: *{nombre_conv}*',
                                       parse_mode=ParseMode.MARKDOWN)
        # Mostrar historial de la conversación cargada
        if conv:
            historial = sa_mod.obtener_historial(conv['claude_session_id'])
            if historial:
                await query.message.reply_text(historial, parse_mode=ParseMode.MARKDOWN)
        return

    # Renombrar
    if data.startswith('sa_rename:'):
        sesion_id = int(data.split(':')[1])
        _esperando_renombrar[uid] = sesion_id
        await query.edit_message_text('✏️ Escribí el nuevo nombre:')
        return

    # Borrar
    if data.startswith('sa_delete:'):
        sesion_id = int(data.split(':')[1])
        nombre_borrado = sa_mod.borrar_conversacion(sesion_id, uid)
        if nombre_borrado:
            await query.edit_message_text(f'🗑️ Conversación "*{nombre_borrado}*" borrada.',
                                           parse_mode=ParseMode.MARKDOWN)
        else:
            await query.answer('No se encontró la conversación.', show_alert=True)
        return
