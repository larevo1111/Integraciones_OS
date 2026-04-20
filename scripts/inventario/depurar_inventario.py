"""
Depurador de inventario físico.
Lee config_depuracion.json y clasifica cada artículo de zeffi_inventario
como inventariable o excluido. Genera filas por artículo+bodega en inv_conteos.

Uso: python3 depurar_inventario.py [--fecha 2026-03-30]
     Sin --fecha usa la fecha de hoy.
"""
import json, os, sys, pymysql
from datetime import date

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, 'config_depuracion.json')

import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import cfg_local
DB_EFFI = dict(**cfg_local(), database='effi_data')
DB_INV  = dict(**cfg_local(), database='os_inventario')

# Columnas de stock por bodega en zeffi_inventario → nombre limpio
BODEGAS = {
    'stock_bodega_principal_sucursal_principal': 'Principal',
    'stock_bodega_jenifer_sucursal_principal': 'Jenifer',
    'stock_bodega_santiago_sucursal_principal': 'Santiago',
    'stock_bodega_ricardo_sucursal_principal': 'Ricardo',
    'stock_bodega_mercado_libre_sucursal_principal': 'Mercado Libre',
    'stock_bodega_villa_de_aburra_sucursal_principal': 'Villa de Aburra',
    'stock_bodega_apica_sucursal_principal': 'Apica',
    'stock_bodega_el_salvador_sucursal_principal': 'El Salvador',
    'stock_bodega_feria_santa_elena_sucursal_principal': 'Feria Santa Elena',
    'stock_bodega_don_luis_san_miguel_sucursal_principal': 'Don Luis San Miguel',
    'stock_bodega_la_tierrita_sucursal_principal': 'La Tierrita',
    'stock_bodega_reginaldo_sucursal_principal': 'Reginaldo',
    'stock_bodega_desarrollo_de_producto_sucursal_principal': 'Desarrollo de Producto',
    'stock_bodega_productos_no_conformes_bod_ppal_sucursal_principal': 'Productos No Conformes',
    'stock_bodega_feria_campesina_san_carlos_sucursal_principal': 'Feria Campesina San Carlos',
}


def cargar_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def obtener_articulos():
    """Trae todos los artículos vigentes con stock desglosado por bodega."""
    cols_bodega = ', '.join(
        f"CAST(REPLACE(COALESCE({col},'0'), ',', '.') AS DECIMAL(12,2)) AS `{col}`"
        for col in BODEGAS
    )
    sql = f"""
        SELECT id, cod_barras, nombre, categoria, gestion_de_stock,
               CAST(REPLACE(COALESCE(costo_manual,'0'), ',', '.') AS DECIMAL(12,2)) AS costo_manual,
               {cols_bodega}
        FROM zeffi_inventario
        WHERE vigencia = 'Vigente'
        ORDER BY categoria, nombre
    """
    conn = pymysql.connect(**DB_EFFI)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    conn.close()
    return rows


def clasificar(articulo, config):
    """Determina si un artículo es inventariable. Retorna (excluido, razon)."""
    cat = (articulo['categoria'] or '').strip()
    gestion = (articulo['gestion_de_stock'] or '').strip()

    if config.get('excluir_sin_gestion_stock') and gestion.lower() == 'no':
        return True, 'Sin gestión de stock'

    if config.get('excluir_sin_categoria') and not cat:
        return True, 'Sin categoría asignada'

    for regla in config.get('excluir_categorias', []):
        patron = regla['patron'].replace('%', '')
        if cat.upper().startswith(patron.upper()):
            return True, regla['razon']

    return False, None


def guardar(fecha_inv, filas):
    """Inserta filas en inv_conteos para esta fecha de inventario."""
    conn = pymysql.connect(**DB_INV)
    with conn.cursor() as cur:
        # Limpiar filas previas de esta fecha (re-ejecución)
        cur.execute("DELETE FROM inv_conteos WHERE fecha_inventario = %s", (fecha_inv,))

        sql = """
            INSERT INTO inv_conteos
                (fecha_inventario, bodega, id_effi, cod_barras, nombre, categoria,
                 excluido, razon_exclusion, inventario_teorico, costo_manual, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
        """
        cur.executemany(sql, filas)
        conn.commit()
    conn.close()


def main():
    # Fecha del inventario
    fecha_inv = date.today()
    if '--fecha' in sys.argv:
        idx = sys.argv.index('--fecha')
        fecha_inv = sys.argv[idx + 1]

    config = cargar_config()
    articulos = obtener_articulos()
    print(f"Total artículos vigentes: {len(articulos)}")

    filas = []
    stats = {'inventariables': 0, 'excluidos': 0, 'filas_bodega': 0, 'razones': {}}

    for a in articulos:
        excluido, razon = clasificar(a, config)

        if excluido:
            # Excluidos: una sola fila sin bodega específica
            filas.append((
                fecha_inv, '—', a['id'], a['cod_barras'], a['nombre'],
                a['categoria'], 1, razon, None, a['costo_manual']
            ))
            stats['excluidos'] += 1
            stats['razones'][razon] = stats['razones'].get(razon, 0) + 1
        else:
            # Inventariables: una fila por cada bodega con stock > 0
            stats['inventariables'] += 1
            tiene_stock = False
            for col, nombre_bodega in BODEGAS.items():
                stock = float(a.get(col) or 0)
                if stock > 0:
                    filas.append((
                        fecha_inv, nombre_bodega, a['id'], a['cod_barras'],
                        a['nombre'], a['categoria'], 0, None,
                        stock, a['costo_manual']
                    ))
                    stats['filas_bodega'] += 1
                    tiene_stock = True

            if not tiene_stock:
                # Artículo inventariable pero sin stock en ninguna bodega
                filas.append((
                    fecha_inv, 'Principal', a['id'], a['cod_barras'],
                    a['nombre'], a['categoria'], 0, None,
                    0, a['costo_manual']
                ))
                stats['filas_bodega'] += 1

    guardar(fecha_inv, filas)

    print(f"\nInventario {fecha_inv}:")
    print(f"  Artículos inventariables: {stats['inventariables']}")
    print(f"  Artículos excluidos:      {stats['excluidos']}")
    print(f"  Filas de conteo (art+bodega): {stats['filas_bodega']}")
    print(f"  Total filas insertadas: {len(filas)}")
    print(f"\nExclusiones por razón:")
    for r, n in sorted(stats['razones'].items(), key=lambda x: -x[1]):
        print(f"  {r}: {n}")


if __name__ == '__main__':
    main()
