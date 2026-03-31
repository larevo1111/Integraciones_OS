"""
Calcula rangos esperados y grupos por artículo.
Detecta unidad del nombre, grupo (MP/PP/PT/INS/DS) cruzando con OPs.

Grupos:
  MP  = Materia Prima (se consume, no se produce)
  PP  = Producto en Proceso (ha sido producido en una OP)
  PT  = Producto Terminado (categoría TPT.xx, listo para venta)
  INS = Insumos (categoría T03.xx, empaques)
  DS  = Desarrollo (categoría DESARROLLO DE PRODUCTO)

Uso: python3 calcular_rangos.py
"""
import re, pymysql

DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')
DB_INV = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')


def detectar_unidad(nombre):
    """Detecta la unidad de medida del nombre del artículo."""
    n = nombre.upper()

    if re.search(r'\bX\s*KG\b|\bKG\b|\bX\s*KILO\b|\bKILO\b|\bKL\b', n):
        return 'KG', 1000
    if re.search(r'\bGRS?\b|\bGRAMOS?\b|\b\d+\s*GRS?\b|\b\d+\s*G\b', n):
        return 'GRS', None
    if re.search(r'\bLT\b|\bLITRO\b|\bLTS\b|\bX\s*LT\b', n):
        return 'LT', 1000
    if re.search(r'\bML\b|\bMILILITROS?\b', n):
        return 'ML', None
    if re.search(r'\bUNIDAD\b|\bUND\b|\bX\s*UND\b', n):
        return 'UND', None

    return 'UND', None


def calcular_rango_por_unidad(unidad, stock_actual):
    """Calcula rangos razonables según la unidad."""
    if unidad in ('KG', 'LT'):
        return (0.1, max(200, stock_actual * 3))
    else:
        return (1, max(500, stock_actual * 3))


def detectar_grupo(articulo_id, nombre, categoria, ids_producidos):
    """Determina el grupo del artículo.

    Grupos:
      MP  = Materia Prima
      PP  = Producto en Proceso (producido en OPs)
      PT  = Producto Terminado (TPT.xx)
      INS = Insumos (T03.xx)
      DS  = Desarrollo (DESARROLLO DE PRODUCTO)
      DES = Desperdicio
      NM  = No Matriculado
    """
    nom = (nombre or '').upper()
    cat = (categoria or '').upper()

    # Desperdicio
    if 'DESPERDICIO' in nom or 'DESPERDI' in nom:
        return 'DES'
    # No matriculado
    if cat.startswith('NO MATRICULADO') or (articulo_id or '').startswith('NM-'):
        return 'NM'
    # Producto terminado
    if cat.startswith('TPT'):
        return 'PT'
    # Insumos
    if cat.startswith('T03'):
        return 'INS'
    # Desarrollo
    if 'DESARROLLO' in cat:
        return 'DS'
    # Producto en proceso (producido en OPs)
    if articulo_id in ids_producidos:
        return 'PP'
    # Materia prima
    return 'MP'


def main():
    conn_effi = pymysql.connect(**DB_EFFI, cursorclass=pymysql.cursors.DictCursor)
    with conn_effi.cursor() as cur:
        # Artículos
        cur.execute("""
            SELECT id, nombre, categoria,
                   CAST(REPLACE(COALESCE(stock_total_empresa,'0'), ',', '.') AS DECIMAL(12,2)) AS stock
            FROM zeffi_inventario
            WHERE vigencia = 'Vigente'
            ORDER BY nombre
        """)
        articulos = cur.fetchall()

        # IDs producidos en OPs (para detectar PP)
        cur.execute("""
            SELECT DISTINCT cod_articulo
            FROM zeffi_articulos_producidos
            WHERE vigencia = 'Orden vigente'
        """)
        ids_producidos = {r['cod_articulo'] for r in cur.fetchall()}
    conn_effi.close()

    # Generar rangos + grupos
    rangos = []
    for a in articulos:
        unidad, factor = detectar_unidad(a['nombre'])
        stock = float(a['stock'] or 0)
        rango_min, rango_max = calcular_rango_por_unidad(unidad, stock)
        grupo = detectar_grupo(a['id'], a['nombre'], a['categoria'], ids_producidos)
        rangos.append((
            a['id'], a['nombre'], grupo, unidad, rango_min, rango_max, stock, factor
        ))

    # Guardar
    conn_inv = pymysql.connect(**DB_INV)
    with conn_inv.cursor() as cur:
        cur.execute("TRUNCATE TABLE inv_rangos")
        cur.executemany("""
            INSERT INTO inv_rangos (id_effi, nombre, grupo, unidad, rango_min, rango_max, promedio, factor_error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, rangos)
        conn_inv.commit()
    conn_inv.close()

    # Stats
    grupos = {}
    unidades = {}
    for r in rangos:
        g, u = r[2], r[3]
        grupos[g] = grupos.get(g, 0) + 1
        unidades[u] = unidades.get(u, 0) + 1

    print(f"Rangos generados: {len(rangos)} artículos")
    print(f"\nGrupos:")
    for g, n in sorted(grupos.items(), key=lambda x: -x[1]):
        nombres = {'MP': 'Materia Prima', 'PP': 'Producto en Proceso', 'PT': 'Producto Terminado', 'INS': 'Insumos', 'DS': 'Desarrollo', 'DES': 'Desperdicio', 'NM': 'No Matriculado'}
        print(f"  {g} ({nombres.get(g, g)}): {n}")
    print(f"\nUnidades:")
    for u, n in sorted(unidades.items(), key=lambda x: -x[1]):
        print(f"  {u}: {n}")


if __name__ == '__main__':
    main()
