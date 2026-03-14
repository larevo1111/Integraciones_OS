"""
Formateador de tablas para Telegram.
- Modo texto (≤5 filas): tabla monoespaciada inline.
- Modo mini app (>5 filas): genera token y devuelve URL.
"""
import uuid, json
from db import guardar_tabla_temp

TABLA_BASE_URL = 'https://menu.oscomunidad.com/bot/tabla'
MAX_FILAS_INLINE = 5


def _formatear_valor(v) -> str:
    if v is None:
        return '—'
    if isinstance(v, float):
        if v >= 1_000_000:
            return f'${v/1_000_000:.1f}M'
        if v >= 1_000:
            return f'${v:,.0f}'
        return f'{v:.2f}'
    return str(v)


def _tabla_texto(columnas: list, filas: list, titulo: str = '') -> str:
    """Genera tabla monoespaciada para Telegram (MarkdownV2 code block)."""
    if not filas:
        return '_Sin datos_'

    # Calcular anchos de columna
    anchos = [max(len(str(c)), max((len(_formatear_valor(f.get(c, ''))) for f in filas), default=0))
              for c in columnas]
    anchos = [min(a, 20) for a in anchos]  # máx 20 chars por col

    sep   = '┼'.join('─' * (a + 2) for a in anchos)
    sep   = f'├{sep}┤'
    top   = '┬'.join('─' * (a + 2) for a in anchos)
    top   = f'┌{top}┐'
    bot   = '┴'.join('─' * (a + 2) for a in anchos)
    bot   = f'└{bot}┘'

    def fila_txt(vals):
        celdas = [f' {str(v)[:a]:<{a}} ' for v, a in zip(vals, anchos)]
        return '│' + '│'.join(celdas) + '│'

    header = fila_txt(columnas)
    sep2   = '╪'.join('═' * (a + 2) for a in anchos)
    sep2   = f'╞{sep2}╡'

    lines = [top, header, sep2]
    for f in filas:
        vals = [_formatear_valor(f.get(c, '')) for c in columnas]
        lines.append(fila_txt(vals))
        lines.append(sep)
    lines[-1] = bot

    tabla_str = '\n'.join(lines)
    encabezado = f'*{titulo}*\n' if titulo else ''
    return f'{encabezado}```\n{tabla_str}\n```'


def procesar_tabla(resultado: dict, pregunta: str, empresa: str = 'ori_sil_2') -> dict:
    """
    Analiza el resultado de ia_service y devuelve:
    {
      'texto': str,          — mensaje formateado para Telegram
      'tiene_tabla': bool,
      'token': str|None,     — token para Mini App si >5 filas
      'n_filas': int,
    }
    """
    tabla  = resultado.get('tabla')
    n_filas = 0
    token   = None
    texto   = resultado.get('respuesta', '') or ''

    if tabla and isinstance(tabla, dict):
        columnas = tabla.get('columnas', [])
        filas    = tabla.get('filas', [])
        n_filas  = len(filas)

        if 0 < n_filas <= MAX_FILAS_INLINE:
            texto = _tabla_texto(columnas, filas)
        elif n_filas > MAX_FILAS_INLINE:
            # Mostrar preview de 3 filas + botón Mini App
            texto_prev = _tabla_texto(columnas, filas[:3], titulo=f'Vista previa — {n_filas} filas')
            token = str(uuid.uuid4())
            guardar_tabla_temp(token, pregunta, columnas, filas, empresa)
            texto = texto_prev

    return {
        'texto':      texto,
        'tiene_tabla': n_filas > 0,
        'token':      token,
        'n_filas':    n_filas,
    }
