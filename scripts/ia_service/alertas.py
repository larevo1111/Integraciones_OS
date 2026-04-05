"""
Notificaciones y alertas de gasto del servicio de IA.
Envía alertas a Telegram cuando el gasto supera umbrales.
"""
import os
import time
import requests as _requests
from .config import get_local_conn


def notificar(mensaje: str):
    """Envía una alerta al bot de notificaciones del sistema. Falla silenciosamente."""
    try:
        token    = os.getenv('TELEGRAM_NOTIF_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id  = os.getenv('TELEGRAM_NOTIF_CHAT_ID')
        if not token or not chat_id:
            return
        _requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'HTML'},
            timeout=5
        )
    except Exception:
        pass


_alertas_enviadas = {}  # clave → timestamp último envío (anti-spam 1h)


def verificar_gasto_y_notificar(empresa: str, costo_llamada: float):
    """Verifica gasto diario y por hora — notifica si supera umbrales."""
    try:
        ahora = time.time()
        conn  = get_local_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(costo_usd),0) AS total FROM ia_logs "
                "WHERE empresa=%s AND DATE(created_at)=CURDATE()", (empresa,)
            )
            gasto_dia = float(cur.fetchone()['total'])
            cur.execute(
                "SELECT COALESCE(SUM(costo_usd),0) AS total FROM ia_logs "
                "WHERE empresa=%s AND created_at >= NOW() - INTERVAL 1 HOUR", (empresa,)
            )
            gasto_hora = float(cur.fetchone()['total'])
        conn.close()

        def _alerta_si(clave, condicion, msg):
            ultimo = _alertas_enviadas.get(clave, 0)
            if condicion and (ahora - ultimo) > 3600:
                notificar(msg)
                _alertas_enviadas[clave] = ahora

        _alerta_si('gasto_dia_2',  gasto_dia  >= 2.0,
            f"💸 <b>Gasto Gemini alto hoy</b>: ${gasto_dia:.2f} USD (~COP {gasto_dia*4200:,.0f})\n"
            f"Límite sugerido: $2 USD/día. Revisa si hay uso excesivo.")
        _alerta_si('gasto_hora_05', gasto_hora >= 0.5,
            f"⚡ <b>Gasto elevado última hora</b>: ${gasto_hora:.2f} USD\n"
            f"Posible pico de consultas o bucle de llamadas.")
    except Exception:
        pass
