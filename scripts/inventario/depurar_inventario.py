"""
Depurador de inventario físico.
Lee config_depuracion.json y clasifica cada artículo de zeffi_inventario
como inventariable o excluido, guardando el resultado en os_inventario.inv_articulos.
"""
import json, os, pymysql

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, 'config_depuracion.json')

DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')
DB_INV  = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')


def cargar_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def obtener_articulos():
    """Trae todos los artículos vigentes de effi_data."""
    conn = pymysql.connect(**DB_EFFI)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""
            SELECT id, cod_barras, nombre, referencia, categoria,
                   gestion_de_stock,
                   CAST(REPLACE(COALESCE(stock_total_empresa,'0'), ',', '.') AS DECIMAL(12,2)) AS stock_total,
                   CAST(REPLACE(COALESCE(costo_promedio,'0'), ',', '.') AS DECIMAL(12,2)) AS costo_promedio
            FROM zeffi_inventario
            WHERE vigencia = 'Vigente'
            ORDER BY categoria, nombre
        """)
        rows = cur.fetchall()
    conn.close()
    return rows


def clasificar(articulo, config):
    """Determina si un artículo es inventariable. Retorna (inventariable, razon)."""
    cat = (articulo['categoria'] or '').strip()
    gestion = (articulo['gestion_de_stock'] or '').strip()

    # Regla 1: sin gestión de stock
    if config.get('excluir_sin_gestion_stock') and gestion.lower() == 'no':
        return False, 'Sin gestión de stock'

    # Regla 2: sin categoría
    if config.get('excluir_sin_categoria') and not cat:
        return False, 'Sin categoría asignada'

    # Regla 3: categorías excluidas por patrón
    for regla in config.get('excluir_categorias', []):
        patron = regla['patron'].replace('%', '')
        if cat.upper().startswith(patron.upper()):
            return False, regla['razon']

    return True, None


def guardar(articulos_clasificados):
    """Inserta/actualiza todos los artículos en inv_articulos."""
    conn = pymysql.connect(**DB_INV)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE inv_articulos")
        sql = """
            INSERT INTO inv_articulos
                (id_effi, cod_barras, nombre, referencia, categoria,
                 gestion_de_stock, stock_total, costo_promedio,
                 inventariable, razon_exclusion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        rows = []
        for a in articulos_clasificados:
            rows.append((
                a['id'], a['cod_barras'], a['nombre'], a['referencia'],
                a['categoria'], a['gestion_de_stock'],
                a['stock_total'], a['costo_promedio'],
                a['inventariable'], a['razon_exclusion']
            ))
        cur.executemany(sql, rows)
        conn.commit()
    conn.close()


def main():
    config = cargar_config()
    articulos = obtener_articulos()
    print(f"Total artículos vigentes: {len(articulos)}")

    clasificados = []
    inv_count = 0
    exc_count = 0
    razones = {}

    for a in articulos:
        inventariable, razon = clasificar(a, config)
        a['inventariable'] = 1 if inventariable else 0
        a['razon_exclusion'] = razon
        clasificados.append(a)
        if inventariable:
            inv_count += 1
        else:
            exc_count += 1
            razones[razon] = razones.get(razon, 0) + 1

    guardar(clasificados)

    print(f"\nResultado:")
    print(f"  Inventariables: {inv_count}")
    print(f"  Excluidos:      {exc_count}")
    print(f"\nExclusiones por razón:")
    for r, n in sorted(razones.items(), key=lambda x: -x[1]):
        print(f"  {r}: {n}")


if __name__ == '__main__':
    main()
