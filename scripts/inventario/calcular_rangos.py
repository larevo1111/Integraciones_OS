"""
Calcula rangos esperados por artículo para detección de errores de unidades.
Detecta la unidad del nombre del artículo y establece min/max razonables.

Uso: python3 calcular_rangos.py
"""
import re, pymysql

DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')
DB_INV = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')


def detectar_unidad(nombre):
    """Detecta la unidad de medida del nombre del artículo."""
    n = nombre.upper()

    # KG / Kilo
    if re.search(r'\bX\s*KG\b|\bKG\b|\bX\s*KILO\b|\bKILO\b|\bKL\b', n):
        return 'KG', 1000  # error típico: poner gramos en vez de kg

    # Gramos
    if re.search(r'\bGRS?\b|\bGRAMOS?\b|\b\d+\s*GRS?\b|\b\d+\s*G\b', n):
        return 'UND', None  # productos empacados en gramos = se cuentan por unidad

    # Litros
    if re.search(r'\bLT\b|\bLITRO\b|\bLTS\b|\bX\s*LT\b', n):
        return 'LT', 1000  # error típico: poner ml en vez de lt

    # ML
    if re.search(r'\bML\b|\bMILILITROS?\b', n):
        return 'UND', None  # empacados en ml = por unidad

    # Unidad explícita
    if re.search(r'\bUNIDAD\b|\bUND\b|\bX\s*UND\b', n):
        return 'UND', None

    # Por defecto: unidad (la mayoría de empacados se cuentan por unidad)
    return 'UND', None


def calcular_rango_por_unidad(unidad, stock_actual):
    """Calcula rangos razonables según la unidad."""
    if unidad == 'KG':
        # Productos a granel en kilos
        return (0.1, max(200, stock_actual * 3))
    elif unidad == 'LT':
        return (0.1, max(200, stock_actual * 3))
    else:
        # UND: productos empacados, siempre enteros
        return (1, max(500, stock_actual * 3))


def main():
    # Obtener artículos inventariables
    conn_effi = pymysql.connect(**DB_EFFI, cursorclass=pymysql.cursors.DictCursor)
    with conn_effi.cursor() as cur:
        cur.execute("""
            SELECT id, nombre,
                   CAST(REPLACE(COALESCE(stock_total_empresa,'0'), ',', '.') AS DECIMAL(12,2)) AS stock
            FROM zeffi_inventario
            WHERE vigencia = 'Vigente'
            ORDER BY nombre
        """)
        articulos = cur.fetchall()
    conn_effi.close()

    # Generar rangos
    rangos = []
    for a in articulos:
        unidad, factor = detectar_unidad(a['nombre'])
        stock = float(a['stock'] or 0)
        rango_min, rango_max = calcular_rango_por_unidad(unidad, stock)
        rangos.append((
            a['id'], a['nombre'], unidad, rango_min, rango_max, stock, factor
        ))

    # Guardar
    conn_inv = pymysql.connect(**DB_INV)
    with conn_inv.cursor() as cur:
        cur.execute("TRUNCATE TABLE inv_rangos")
        cur.executemany("""
            INSERT INTO inv_rangos (id_effi, nombre, unidad, rango_min, rango_max, promedio, factor_error)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, rangos)
        conn_inv.commit()
    conn_inv.close()

    # Stats
    unidades = {}
    for r in rangos:
        u = r[2]
        unidades[u] = unidades.get(u, 0) + 1

    print(f"Rangos generados: {len(rangos)} artículos")
    for u, n in sorted(unidades.items(), key=lambda x: -x[1]):
        print(f"  {u}: {n}")


if __name__ == '__main__':
    main()
