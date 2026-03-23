"""
Seguridad del servicio de IA: rate limiting, circuit breaker, verificación de límites.
"""
import math
import time
import threading
from collections import defaultdict, deque
from .config import get_local_conn


# ── Rate limiter por usuario — sliding window in-memory ──────────────────────
_rl_lock    = threading.Lock()
_rl_windows = defaultdict(lambda: {'1s': deque(), '10s': deque(), '60s': deque()})


def _limpiar_ventana(dq: deque, ventana_seg: float, ahora: float):
    while dq and (ahora - dq[0]) > ventana_seg:
        dq.popleft()


def _get_config(conn, clave: str, default):
    with conn.cursor() as cur:
        cur.execute("SELECT valor FROM ia_config WHERE clave = %s", (clave,))
        row = cur.fetchone()
    return row['valor'] if row else default


def get_config_simple(clave: str, default: str) -> str:
    """Lee un valor de ia_config sin necesitar conexión externa."""
    try:
        conn = get_local_conn()
        result = _get_config(conn, clave, default)
        conn.close()
        return result
    except Exception:
        return default


def slugs_router() -> list[str]:
    """Devuelve la cadena de agentes router en orden, desde ia_config."""
    return [
        get_config_simple('rol_router_principal',  'groq-llama'),
        get_config_simple('rol_router_suplente_1', 'cerebras-llama'),
        get_config_simple('rol_router_suplente_2', 'gemini-flash-lite'),
        get_config_simple('rol_router_suplente_3', 'gemini-flash'),
    ]


def verificar_rate_usuario(usuario_id: str, empresa: str) -> dict | None:
    """
    Sliding window rate limit por usuario.
    Devuelve None si OK, o dict {error, retry_after} si debe bloquearse.
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
        return None

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

        w['1s'].append(ahora)
        w['10s'].append(ahora)
        w['60s'].append(ahora)

    return None


def limpiar_rate_windows():
    """Elimina entradas de rate limit de usuarios inactivos (>120s sin actividad)."""
    ahora = time.monotonic()
    with _rl_lock:
        inactivos = [k for k, w in _rl_windows.items()
                     if not w['60s'] or (ahora - w['60s'][-1]) > 120]
        for k in inactivos:
            del _rl_windows[k]
    return len(inactivos)


def verificar_limites(agente_slug: str, empresa: str) -> dict | None:
    """
    Verifica 3 capas de protección antes de llamar a la API externa.
    Devuelve None si todo OK, o dict {error, capa} si hay que bloquear.
    """
    conn = get_local_conn()
    try:
        limite_costo = float(_get_config(conn, 'limite_costo_dia_usd', '0'))
        cb_errores   = int(_get_config(conn, 'circuit_breaker_errores', '5'))
        cb_ventana   = int(_get_config(conn, 'circuit_breaker_ventana_min', '10'))

        with conn.cursor() as cur:
            # CAPA 1: Costo diario global
            if limite_costo > 0:
                cur.execute(
                    "SELECT COALESCE(SUM(costo_usd), 0) AS total FROM ia_logs "
                    "WHERE empresa = %s AND DATE(created_at) = CURDATE()",
                    (empresa,)
                )
                costo_hoy = float(cur.fetchone()['total'])
                if costo_hoy >= limite_costo:
                    return {
                        'capa': 1,
                        'error': (
                            f"⛔ Límite de gasto diario alcanzado "
                            f"(${costo_hoy:.4f} / ${limite_costo:.2f} USD). "
                            f"Reinicia mañana o ajusta el límite en ia_config."
                        )
                    }

            # CAPA 2: RPD por agente
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
                        'capa': 2,
                        'error': (
                            f"⛔ Agente '{agente_slug}' alcanzó su límite diario "
                            f"({llamadas_hoy}/{rpd} llamadas). "
                            f"Usa otro agente o espera mañana."
                        )
                    }

            # CAPA 3: Circuit breaker
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
                    'capa': 3,
                    'error': (
                        f"⛔ Agente '{agente_slug}' suspendido automáticamente "
                        f"({errores_recientes} errores en los últimos {cb_ventana} min). "
                        f"Revisa el agente o espera {cb_ventana} minutos."
                    )
                }

        return None
    except Exception:
        return None
    finally:
        conn.close()


def nivel_usuario(usuario_id: str, empresa: str) -> int:
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


def mejor_agente_para_nivel(nivel: int) -> str:
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
