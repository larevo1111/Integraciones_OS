"""
Utilidades SQL: columnas reales, fechas máximas, cobertura de datos.
Funciones auxiliares para el retry inteligente y contexto del LLM.
"""
import re
import time
from .config import get_local_conn


_CACHE_COBERTURA: dict = {}   # {empresa: (timestamp, texto)}
_CACHE_COBERTURA_TTL = 3600  # 1 hora


def obtener_columnas_reales(sql: str) -> str:
    """
    Dado un SQL fallido, extrae las tablas con sqlglot y hace DESCRIBE
    contra la BD real (Hostinger) para obtener columnas reales.
    Si alguna tabla no existe, lo reporta y sugiere tablas válidas similares.
    """
    try:
        import sqlglot
        import sqlglot.expressions as exp
        stmts = sqlglot.parse(sql, dialect='mysql')
        tablas = set()
        for stmt in stmts:
            if stmt is None:
                continue
            for node in stmt.walk():
                if isinstance(node, exp.Table) and node.name:
                    tablas.add(node.name)
        if not tablas:
            return ''

        from .config import get_hostinger_conn
        conn = get_hostinger_conn()
        partes = []
        tablas_inexistentes = []
        with conn.cursor() as cur:
            for tabla in sorted(tablas):
                try:
                    cur.execute(f"DESCRIBE {tabla}")
                    cols = cur.fetchall()
                    nombres = [c['Field'] for c in cols]
                    partes.append(f"  {tabla}: {', '.join(nombres)}")
                except Exception:
                    tablas_inexistentes.append(tabla)
        conn.close()

        resultado = ''
        if tablas_inexistentes:
            from .esquema import _obtener_ddl_directo
            tablas_validas = _listar_tablas_validas()
            similares = _sugerir_tablas(tablas_inexistentes, tablas_validas)
            resultado += (
                'TABLAS QUE NO EXISTEN en la base de datos:\n'
                + ', '.join(tablas_inexistentes) + '\n\n'
                'Tablas disponibles que podrían ser las correctas:\n'
                + '\n'.join(f'  {s}' for s in similares) + '\n\n'
            )
        if partes:
            resultado += 'Columnas REALES de las tablas válidas:\n' + '\n'.join(partes) + '\n\n'
        return resultado
    except Exception:
        return ''


def _listar_tablas_validas() -> list[str]:
    """Devuelve la lista de tablas existentes en Hostinger."""
    try:
        from .config import get_hostinger_conn
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            cur.execute('SHOW TABLES')
            tablas = [list(row.values())[0] for row in cur.fetchall()]
        conn.close()
        return tablas
    except Exception:
        return []


def _sugerir_tablas(inexistentes: list[str], validas: list[str]) -> list[str]:
    """Sugiere tablas válidas similares a las inexistentes."""
    sugerencias = []
    for inv in inexistentes:
        # Extraer palabras clave de la tabla inexistente
        partes = inv.replace('zeffi_', '').split('_')
        for valida in validas:
            if any(p in valida for p in partes if len(p) > 3):
                sugerencias.append(valida)
    return sorted(set(sugerencias)) if sugerencias else validas[:15]


def obtener_fecha_maxima(sql: str) -> str:
    """
    Dado un SQL, detecta las tablas consultadas y obtiene la fecha máxima
    real disponible. Se usa para informar al LLM cuándo hay 0 filas.
    """
    try:
        tablas_raw = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, re.IGNORECASE)
        tablas = [t for par in tablas_raw for t in par if t]
        if not tablas:
            return ''
        cols_fecha = ['fecha_de_creacion', 'fecha', 'fecha_factura', 'fecha_remision']
        resultados = []
        conn = get_local_conn()
        with conn.cursor() as cur:
            for tabla in set(tablas):
                for col in cols_fecha:
                    try:
                        cur.execute(f"SELECT MAX({col}) AS max_fecha FROM {tabla}")
                        row = cur.fetchone()
                        if row and row.get('max_fecha'):
                            resultados.append(f"{tabla}.{col}: {row['max_fecha']}")
                            break
                    except Exception:
                        continue
        conn.close()
        if resultados:
            return f"Fechas más recientes en las tablas consultadas:\n" + '\n'.join(resultados) + '\n\n'
        return ''
    except Exception:
        return ''


def obtener_cobertura_tablas(empresa: str = 'ori_sil_2') -> str:
    """
    Calcula cobertura real de datos de las tablas principales.
    Se inyecta en el system prompt para que el modelo sepa
    con qué datos cuenta antes de razonar.
    Se cachea 1 hora.
    """
    ahora = time.time()
    if empresa in _CACHE_COBERTURA:
        ts, texto = _CACHE_COBERTURA[empresa]
        if ahora - ts < _CACHE_COBERTURA_TTL:
            return texto

    tablas_config = [
        {
            'tabla': 'zeffi_facturas_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "fecha_de_anulacion IS NULL",
            'etiqueta': 'Facturas de venta',
        },
        {
            'tabla': 'zeffi_remisiones_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "fecha_de_anulacion IS NULL",
            'etiqueta': 'Remisiones de venta',
        },
        {
            'tabla': 'zeffi_ordenes_venta_encabezados',
            'col_fecha': 'fecha_de_creacion',
            'filtro': "vigencia = 'Vigente'",
            'etiqueta': 'Órdenes activas (consignación)',
        },
    ]

    lineas = ['Cobertura de datos disponibles en la base de datos:']
    try:
        from .config import get_hostinger_conn
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            for t in tablas_config:
                try:
                    where = f"WHERE {t['filtro']}" if t['filtro'] else ''
                    cur.execute(f"""
                        SELECT
                            MIN(DATE({t['col_fecha']}))                     AS fecha_min,
                            MAX(DATE({t['col_fecha']}))                     AS fecha_max,
                            COUNT(*)                                        AS total_registros,
                            COUNT(DISTINCT DATE({t['col_fecha']}))          AS dias_con_datos
                        FROM {t['tabla']}
                        {where}
                    """)
                    row = cur.fetchone()
                    if row and row.get('fecha_max'):
                        lineas.append(
                            f"  {t['etiqueta']}: {row['fecha_min']} → {row['fecha_max']} "
                            f"({row['total_registros']:,} registros en {row['dias_con_datos']:,} días distintos)"
                        )
                except Exception:
                    pass

            try:
                cur.execute(
                    "SELECT MIN(mes) AS desde, MAX(mes) AS hasta, COUNT(*) AS n "
                    "FROM resumen_ventas_facturas_mes"
                )
                row = cur.fetchone()
                if row and row.get('hasta'):
                    lineas.append(
                        f"  Resúmenes mensuales: {row['desde']} → {row['hasta']} ({row['n']} meses)"
                    )
            except Exception:
                pass

        conn.close()
    except Exception:
        return ''

    if len(lineas) <= 1:
        return ''

    lineas.append(
        'Nota: la ausencia de datos en un día específico puede significar que ese día '
        'no hubo ventas (fin de semana, feriado, o simplemente sin actividad). '
        'En ese caso, considera consultar la semana completa o el acumulado del período.'
    )

    texto = '\n'.join(lineas)
    _CACHE_COBERTURA[empresa] = (ahora, texto)
    return texto
