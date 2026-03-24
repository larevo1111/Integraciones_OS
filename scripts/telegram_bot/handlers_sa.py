"""
handlers_sa.py — Handlers de Telegram para el Super Agente.
Responsabilidad: procesar mensajes y callbacks del Super Agente en el bot.
Usado por: telegram_bot/bot.py
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

log = logging.getLogger('os_ia_bot')


async def manejar_superagente(update: Update, sa_mod, tabla_mod,
                               inline_datos_fn, inline_solo_nuevo_fn, reply_kb_fn,
                               sesion: dict, nombre: str, nivel: int,
                               empresa: str, pregunta: str):
    """Procesa una pregunta en modo Super Agente y responde al usuario."""
    user     = update.effective_user
    resultado = sa_mod.consultar(
        pregunta=pregunta, usuario_id=str(user.id),
        nombre_usuario=nombre, nivel=nivel, empresa=empresa,
    )

    if not resultado.get('ok'):
        await update.message.reply_text(
            f'😔 {resultado.get("error","Error en el Super Agente.")}',
            reply_markup=reply_kb_fn(nivel)
        )
        return

    tipo = resultado['tipo']

    if tipo == 'tabla':
        data     = resultado['contenido']
        res_fake = {'ok': True, 'respuesta': data.get('texto', ''),
                    'datos': data.get('filas', []), 'columnas': data.get('columnas', []),
                    'titulo': data.get('titulo', '')}
        info = tabla_mod.procesar_tabla(res_fake, pregunta, empresa)
        kb   = inline_datos_fn(info['token'], info['n_filas']) if info['token'] else inline_solo_nuevo_fn()
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
            f'⚙️ {data.get("mensaje_usuario","Necesito un cambio de código/estructura.")}\n'
            '_Solicitud enviada a Santiago._',
            parse_mode=ParseMode.MARKDOWN, reply_markup=reply_kb_fn(nivel)
        )
        kb_apr = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Aprobar', callback_data=f'sa_aprobar:{user.id}'),
            InlineKeyboardButton('❌ Rechazar', callback_data=f'sa_rechazar:{user.id}'),
        ]])
        texto = (
            f'🔧 <b>Super Agente — Solicitud de aprobación</b>\n\n'
            f'<b>Qué:</b> {data.get("descripcion","")}\n'
            f'<b>Causa raíz:</b> {data.get("causa_raiz","")}\n'
            f'<b>Cambio propuesto:</b>\n<code>{data.get("cambio_propuesto","")}</code>\n\n'
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
            parse_mode=ParseMode.MARKDOWN, reply_markup=reply_kb_fn(nivel)
        )
    except Exception:
        await update.message.reply_text(str(resultado['contenido']), reply_markup=reply_kb_fn(nivel))


async def handle_sa_callback(query, user, nivel: int, nombre: str):
    """Procesa los callbacks sa_aprobar / sa_rechazar."""
    if nivel < 7:
        await query.answer('Solo nivel 7 puede aprobar cambios.', show_alert=True)
        return

    data         = query.data
    accion       = 'aprobado' if data.startswith('sa_aprobar:') else 'rechazado'
    solicitante  = data.split(':', 1)[1]
    emoji        = '✅' if accion == 'aprobado' else '❌'

    try:
        await query.edit_message_text(
            query.message.text + f'\n\n{emoji} <b>{accion.upper()}</b> por {nombre}',
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    try:
        await query.get_bot().send_message(
            chat_id=solicitante,
            text=f'{emoji} Santiago {accion} el cambio de código solicitado.'
        )
    except Exception as e:
        log.warning(f'No se pudo notificar al solicitante {solicitante}: {e}')
