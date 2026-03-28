"""
Formateador de tablas para Telegram.
- ≤2 filas: tabla ASCII inline en el chat.
- >2 filas: SIEMPRE genera token + botón "Ver tabla completa" (mini app).
"""
import uuid, json
from db import guardar_tabla_temp

TABLA_BASE_URL = 'https://menu.oscomunidad.com/bot/tabla'
MAX_FILAS_INLINE = 2   # >2 filas → SIEMPRE botón "Ver tabla completa"


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


def _fila_valor(fila, idx: int, col: str):
    """Extrae valor de una fila sea lista o dict."""
    if isinstance(fila, dict):
        return fila.get(col, '')
    if isinstance(fila, list) and idx < len(fila):
        return fila[idx]
    return ''


def _tabla_texto(columnas: list, filas: list, titulo: str = '') -> str:
    """Genera tabla monoespaciada para Telegram (code block)."""
    if not filas:
        return '_Sin datos_'

    # Calcular anchos de columna
    anchos = [max(len(str(c)), max((len(_formatear_valor(_fila_valor(f, i, c))) for f in filas), default=0))
              for i, c in enumerate(columnas)]
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
        vals = [_formatear_valor(_fila_valor(f, i, c)) for i, c in enumerate(columnas)]
        lines.append(fila_txt(vals))
        lines.append(sep)
    lines[-1] = bot

    tabla_str = '\n'.join(lines)
    encabezado = f'*{titulo}*\n' if titulo else ''
    return f'{encabezado}```\n{tabla_str}\n```'


def _limpiar_tablas_texto(texto: str) -> str:
    """Elimina tablas del texto del LLM: markdown (pipes), Unicode box-drawing y bloques de código con tablas."""
    import re
    # Caracteres de dibujo de tabla Unicode
    BOX_CHARS = '┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬'
    tiene_pipes = '|' in texto
    tiene_box = any(c in texto for c in BOX_CHARS)
    if not tiene_pipes and not tiene_box:
        return texto
    # Eliminar bloques de código que contengan tablas (pipes o box-drawing)
    texto = re.sub(r'```[^\n]*\n[^`]*```', '', texto, flags=re.DOTALL)
    # Filtrar líneas de tabla
    lineas = texto.split('\n')
    limpias = []
    for linea in lineas:
        stripped = linea.strip()
        # Línea de tabla markdown: empieza y termina con |
        if stripped.startswith('|') and stripped.endswith('|'):
            continue
        # Separador markdown tipo :--- | ---:
        if re.match(r'^[\s|:\-]+$', stripped) and '|' in stripped:
            continue
        # Línea con box-drawing characters (tabla Unicode)
        if any(c in stripped for c in BOX_CHARS):
            continue
        limpias.append(linea)
    resultado = '\n'.join(limpias).strip()
    resultado = re.sub(r'\n{3,}', '\n\n', resultado)
    return resultado


def _filas_validas(filas: list) -> list:
    """Filtra filas vacías o nulas."""
    result = []
    for f in filas:
        if isinstance(f, list):
            if any(v not in (None, '', 0) for v in f):
                result.append(f)
        elif isinstance(f, dict):
            if any(v not in (None, '', 0) for v in f.values()):
                result.append(f)
    return result


def procesar_tabla(resultado: dict, pregunta: str, empresa: str = 'ori_sil_2') -> dict:
    """
    Procesa respuesta del ia_service para Telegram.
    - Limpia tablas markdown (pipes) del texto del LLM SIEMPRE.
    - ≤2 filas: tabla ASCII inline en el chat.
    - >2 filas: genera token + botón "Ver tabla completa" (mini app).
    """
    tabla   = resultado.get('tabla')
    texto   = (resultado.get('respuesta') or '').strip()
    n_filas = 0
    token   = None

    # Limpiar tablas markdown del LLM SIEMPRE (con o sin datos estructurados)
    texto = _limpiar_tablas_texto(texto)

    if tabla and isinstance(tabla, dict):
        columnas = tabla.get('columnas', [])
        filas    = _filas_validas(tabla.get('filas', []))
        n_filas  = len(filas)

        if n_filas > 0:
            titulo_tabla = tabla.get('titulo', '')

            if n_filas <= MAX_FILAS_INLINE:
                # 1-2 filas: el LLM ya formateó con viñetas, NO agregar tabla ASCII.
                # Solo si el LLM no incluyó datos, generar viñetas nosotros.
                if not any(c.lower() in texto.lower() for c in columnas[:2]):
                    vinetas = []
                    for f in filas:
                        for i, c in enumerate(columnas):
                            v = _formatear_valor(_fila_valor(f, i, c))
                            vinetas.append(f"• *{c}*: {v}")
                    texto = f"{texto}\n\n" + '\n'.join(vinetas) if texto else '\n'.join(vinetas)
            else:
                # >2 filas: SIEMPRE botón "Ver tabla completa"
                token = str(uuid.uuid4())
                guardar_tabla_temp(token, pregunta, columnas, filas, empresa)

    return {
        'texto':       texto,
        'tiene_tabla': n_filas > 0,
        'token':       token,
        'n_filas':     n_filas,
    }
