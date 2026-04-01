"""
Calcula inventario teórico a una fecha de corte.

Fórmula:
  stock_teorico = stock_effi_hoy
                  - movimientos_netos_post_corte (trazabilidad)
                  + materiales_OPs_generadas_al_corte
                  - productos_OPs_generadas_al_corte

Uso:
  python3 scripts/inventario/calcular_inventario_teorico.py --fecha 2026-03-31
"""
import argparse
import pymysql
from datetime import date, datetime
import json

DB_INV = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')
DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')


def query(db_config, sql, params=None):
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
    conn.close()
    return rows


def execute_many(db_config, sql, data):
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cur:
        cur.executemany(sql, data)
        conn.commit()
        affected = cur.rowcount
    conn.close()
    return affected


def parse_decimal(val):
    """Convierte texto con coma decimal a float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace(',', '.') or 0)


def obtener_stock_actual():
    """Lee stock total empresa de zeffi_inventario por artículo."""
    rows = query(DB_EFFI, """
        SELECT id,
               nombre,
               CAST(REPLACE(COALESCE(stock_total_empresa, '0'), ',', '.') AS DECIMAL(12,2)) AS stock
        FROM zeffi_inventario
        WHERE vigencia = 'Vigente'
    """)
    return {r['id']: {'nombre': r['nombre'], 'stock': float(r['stock'])} for r in rows}


def obtener_trazabilidad_post_corte(fecha_corte):
    """Suma neta de movimientos post-corte por artículo."""
    rows = query(DB_EFFI, """
        SELECT id_articulo,
               SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS neto
        FROM zeffi_trazabilidad
        WHERE fecha > %s
        GROUP BY id_articulo
    """, (f"{fecha_corte} 23:59:59",))
    return {r['id_articulo']: float(r['neto']) for r in rows}


def obtener_ops_generadas_al_corte(fecha_corte):
    """Lista IDs de OPs con estado 'Generada' al corte.

    Lógica:
    1. Actualmente 'Generada' → seguro estaba generada al corte (si fue creada antes)
    2. Actualmente 'Procesada' pero tiene registro en cambios_estado de 'Procesada'
       DESPUÉS del corte → estaba generada al corte
    3. Actualmente 'Procesada' sin registro en cambios_estado → NO incluir
       (zeffi_cambios_estado no captura todos los cambios, hay OPs procesadas
       sin registro, y no podemos asumir que estaban generadas)
    """
    corte_ts = f"{fecha_corte} 23:59:59"
    rows = query(DB_EFFI, """
        SELECT e.id_orden
        FROM zeffi_produccion_encabezados e
        WHERE e.vigencia = 'Vigente'
          AND e.fecha_de_creacion <= %s
          AND (
            -- Caso 1: Actualmente generada → seguro estaba generada al corte
            e.estado = 'Generada'
            OR
            -- Caso 2: Actualmente procesada, pero el cambio a 'Procesada' fue
            -- DESPUÉS del corte → al corte estaba generada
            (
              e.estado = 'Procesada'
              AND EXISTS (
                SELECT 1 FROM zeffi_cambios_estado ce
                WHERE ce.id_orden = e.id_orden
                  AND ce.nuevo_estado = 'Procesada'
                  AND ce.f_cambio_de_estado > %s
              )
            )
          )
    """, (corte_ts, corte_ts))
    return [r['id_orden'] for r in rows]


def obtener_materiales_ops(ops_ids):
    """Suma de materiales por artículo para las OPs dadas."""
    if not ops_ids:
        return {}
    placeholders = ','.join(['%s'] * len(ops_ids))
    rows = query(DB_EFFI, f"""
        SELECT cod_material,
               SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS total
        FROM zeffi_materiales
        WHERE id_orden IN ({placeholders})
          AND vigencia = 'Orden vigente'
        GROUP BY cod_material
    """, tuple(ops_ids))
    return {r['cod_material']: float(r['total']) for r in rows}


def obtener_productos_ops(ops_ids):
    """Suma de productos por artículo para las OPs dadas."""
    if not ops_ids:
        return {}
    placeholders = ','.join(['%s'] * len(ops_ids))
    rows = query(DB_EFFI, f"""
        SELECT cod_articulo,
               SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS total
        FROM zeffi_articulos_producidos
        WHERE id_orden IN ({placeholders})
          AND vigencia = 'Orden vigente'
        GROUP BY cod_articulo
    """, tuple(ops_ids))
    return {r['cod_articulo']: float(r['total']) for r in rows}


def calcular(fecha_corte):
    """Ejecuta el cálculo completo y guarda en inv_teorico."""
    print(f"[Inventario Teórico] Calculando para fecha de corte: {fecha_corte}")

    # Paso 1: Stock actual
    stock = obtener_stock_actual()
    print(f"  Stock actual: {len(stock)} artículos")

    # Paso 2: Trazabilidad post-corte
    traz = obtener_trazabilidad_post_corte(fecha_corte)
    print(f"  Movimientos post-corte: {len(traz)} artículos con movimiento")

    # Paso 3: OPs generadas al corte
    ops = obtener_ops_generadas_al_corte(fecha_corte)
    print(f"  OPs generadas al corte: {len(ops)}")

    # Paso 4: Materiales y productos
    materiales = obtener_materiales_ops(ops)
    productos = obtener_productos_ops(ops)
    print(f"  Materiales a devolver: {len(materiales)} artículos")
    print(f"  Productos a quitar: {len(productos)} artículos")

    # Paso 5: Calcular stock teórico por artículo
    # Recoger todos los IDs de artículo posibles
    todos_ids = set(stock.keys())
    todos_ids.update(traz.keys())
    todos_ids.update(materiales.keys())
    todos_ids.update(productos.keys())

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ops_json = json.dumps(ops)
    filas = []

    for art_id in todos_ids:
        s = stock.get(art_id, {})
        stock_effi = s.get('stock', 0)
        nombre = s.get('nombre', f'Artículo {art_id}')
        ajuste_traz = traz.get(art_id, 0)
        ajuste_mat = materiales.get(art_id, 0)
        ajuste_prod = productos.get(art_id, 0)

        teorico = stock_effi - ajuste_traz + ajuste_mat - ajuste_prod

        filas.append((
            fecha_corte, str(art_id), nombre,
            stock_effi, ajuste_traz, ajuste_mat, ajuste_prod,
            teorico, len(ops), ops_json, ahora
        ))

    # Paso 6: Guardar (UPSERT)
    if filas:
        conn = pymysql.connect(**DB_INV)
        with conn.cursor() as cur:
            # Limpiar registros previos para esta fecha
            cur.execute("DELETE FROM inv_teorico WHERE fecha_corte = %s", (fecha_corte,))
            cur.executemany("""
                INSERT INTO inv_teorico
                    (fecha_corte, cod_articulo, nombre_articulo,
                     stock_effi, ajuste_trazabilidad, ajuste_ops_materiales, ajuste_ops_productos,
                     stock_teorico, ops_generadas_count, ops_incluidas, calculado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, filas)
            conn.commit()
        conn.close()

    # Paso 7: Actualizar inventario_teorico en inv_conteos
    actualizar_conteos(fecha_corte)

    print(f"  Guardados: {len(filas)} artículos en inv_teorico")
    print(f"[OK] Cálculo completado a las {ahora}")
    return {
        'articulos': len(filas),
        'ops_generadas': len(ops),
        'mov_post_corte': len(traz),
        'materiales_ajustados': len(materiales),
        'productos_ajustados': len(productos),
        'calculado_en': ahora
    }


def actualizar_conteos(fecha_corte):
    """Actualiza inventario_teorico en inv_conteos con los datos calculados."""
    # Leer lo calculado
    teoricos = query(DB_INV, """
        SELECT cod_articulo, stock_teorico
        FROM inv_teorico
        WHERE fecha_corte = %s
    """, (fecha_corte,))

    if not teoricos:
        return

    conn = pymysql.connect(**DB_INV)
    with conn.cursor() as cur:
        for t in teoricos:
            cur.execute("""
                UPDATE inv_conteos
                SET inventario_teorico = %s,
                    diferencia = CASE
                        WHEN inventario_fisico IS NOT NULL THEN inventario_fisico - %s
                        ELSE NULL
                    END
                WHERE fecha_inventario = %s AND id_effi = %s
            """, (t['stock_teorico'], t['stock_teorico'], fecha_corte, t['cod_articulo']))
        conn.commit()
        print(f"  Conteos actualizados con stock teórico")
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calcular inventario teórico a fecha de corte')
    parser.add_argument('--fecha', default=str(date.today()), help='Fecha de corte YYYY-MM-DD')
    args = parser.parse_args()
    calcular(args.fecha)
