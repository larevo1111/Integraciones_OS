"""
Calcula inventario teórico a una fecha de corte.

Fórmula:
  stock_teorico = stock_effi_hoy
                  - movimientos_netos_post_corte (trazabilidad)
                  + materiales_OPs_generadas_al_corte
                  - productos_OPs_generadas_al_corte

TIMEZONE (IMPORTANTE — Effi usa timezones MIXTOS):
  Tabla/campo                                    | Timezone
  -----------------------------------------------|--------
  zeffi_trazabilidad.fecha                       | COT (local, igual al corte)
  zeffi_produccion_encabezados.fecha_de_creacion | COT
  zeffi_produccion_encabezados.fecha_de_anulacion| COT
  zeffi_cambios_estado.f_cambio_de_estado        | UTC (+5h respecto al corte)

  Verificación empírica:
  - zeffi_trazabilidad: horas 7-23 (nunca 0-6) → COT
  - zeffi_cambios_estado: 278 registros entre 0-6 → UTC
  - Comparación cruzada: trazabilidad de una OP y fecha_de_creacion tienen
    el mismo timestamp exacto → ambos COT.

  El offset se lee de APP_TIMEZONE del .env (default -05:00 = 5 horas).
  Solo se aplica a zeffi_cambios_estado.

DETERMINISMO:
  El cálculo debe ser inmutable: el teórico de una fecha histórica debe ser
  el mismo hoy, mañana, o en 1 año. Por eso NO se usa el estado actual de
  las OPs, sino el histórico al corte (usando zeffi_cambios_estado).

Uso:
  python3 scripts/inventario/calcular_inventario_teorico.py --fecha 2026-03-31
"""
import argparse
import os
import pymysql
import logging
from datetime import date, datetime
import json

# ─── Configuración ────────────────────────────────────────────────
DB_INV = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='os_inventario')
DB_EFFI = dict(host='127.0.0.1', user='osadmin', password='Epist2487.', database='effi_data')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'inventario_teorico.log')
ENV_FILE = os.path.join(SCRIPT_DIR, '..', '.env')


def leer_timezone_env():
    """Lee APP_TIMEZONE del .env del proyecto. Default: -05:00 (Colombia).

    Retorna: (tz_string, offset_horas_a_sumar_para_convertir_a_utc)
    Ejemplo: -05:00 → ('-05:00', 5) porque hay que sumar 5h a un timestamp COT
    para obtener el equivalente UTC.
    """
    tz = '-05:00'
    try:
        with open(ENV_FILE) as f:
            for linea in f:
                linea = linea.strip()
                if linea.startswith('APP_TIMEZONE='):
                    tz = linea.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass

    # Convertir a offset en horas: si APP_TIMEZONE=-05:00, hay que sumar 5h para ir a UTC
    try:
        signo = -1 if tz.startswith('-') else 1
        partes = tz.lstrip('+-').split(':')
        horas = int(partes[0])
        minutos = int(partes[1]) if len(partes) > 1 else 0
        # Offset del timezone local respecto a UTC (COT es -5 → -5 horas)
        offset_local = signo * (horas + minutos / 60)
        # Para convertir timestamp local a UTC: sumar el negativo del offset
        # Ejemplo: COT -05:00 → sumar 5 para ir a UTC
        offset_a_utc = -offset_local
    except Exception:
        offset_a_utc = 5

    return tz, int(offset_a_utc)


def setup_logging():
    """Configura logging a archivo + consola."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger('inv_teorico')
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)
    return logger


TIMEZONE, OFFSET_A_UTC = leer_timezone_env()
log = setup_logging()


# ─── Helpers DB ────────────────────────────────────────────────────
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


# ─── Lectura de datos ──────────────────────────────────────────────
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


def obtener_trazabilidad_post_corte(corte_ts):
    """Suma neta de movimientos post-corte por artículo.

    Las fechas de zeffi_trazabilidad están en el mismo timezone que el corte
    (APP_TIMEZONE). No se aplica offset.
    """
    rows = query(DB_EFFI, """
        SELECT id_articulo,
               SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS neto
        FROM zeffi_trazabilidad
        WHERE fecha > %s
        GROUP BY id_articulo
    """, (corte_ts,))
    return {r['id_articulo']: float(r['neto']) for r in rows}


def obtener_ops_generadas_al_corte(corte_ts):
    """Lista IDs de OPs con estado 'Generada' al corte (lógica determinística).

    Una OP se considera "Generada al corte" SI:
    1. Fue creada antes o igual al corte (fecha_de_creacion en COT <= corte)
    2. Era vigente al corte:
       - Sigue vigente hoy, O
       - Fue anulada DESPUÉS del corte (fecha_de_anulacion en COT > corte)
       Nota: las anulaciones post-corte generan movimientos reversos en
       zeffi_trazabilidad que se rebobinan automáticamente por el término 2.
    3. Su estado al corte era 'Generada':
       - No tiene ningún cambio a 'Procesada' registrado antes o igual al
         corte (zeffi_cambios_estado está en UTC, se suma OFFSET_A_UTC al corte)
       - Si zeffi_cambios_estado no tiene registros para la OP, el estado
         por defecto es 'Generada' (estado inicial)

    OJO: zeffi_cambios_estado está en UTC mientras que fecha_de_creacion y
    fecha_de_anulacion están en COT. Por eso el offset solo se aplica a
    f_cambio_de_estado.
    """
    rows = query(DB_EFFI, f"""
        SELECT e.id_orden
        FROM zeffi_produccion_encabezados e
        WHERE
          -- 1. Creada antes o igual al corte (fecha_de_creacion en COT)
          e.fecha_de_creacion <= %s
          -- 2. Era vigente al corte (fecha_de_anulacion en COT)
          AND (
            e.vigencia = 'Vigente'
            OR (e.vigencia = 'Anulado' AND e.fecha_de_anulacion > %s)
          )
          -- 3. Estado 'Generada' al corte: sin cambio a 'Procesada' antes del corte
          --    f_cambio_de_estado está en UTC → convertir corte COT a UTC sumando offset
          AND NOT EXISTS (
            SELECT 1 FROM zeffi_cambios_estado ce
            WHERE ce.id_orden = e.id_orden
              AND ce.nuevo_estado = 'Procesada'
              AND ce.f_cambio_de_estado <= DATE_ADD(%s, INTERVAL {OFFSET_A_UTC} HOUR)
          )
    """, (corte_ts, corte_ts, corte_ts))
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


# ─── Cálculo principal ─────────────────────────────────────────────
def calcular(fecha_corte, usuario=None):
    """Ejecuta el cálculo completo y guarda en inv_teorico."""
    corte_ts = f"{fecha_corte} 23:59:59"
    log.info(f"=== INICIO CÁLCULO TEÓRICO ===")
    log.info(f"Fecha corte: {fecha_corte} 23:59:59 ({TIMEZONE})")
    log.info(f"Offset a UTC (para zeffi_cambios_estado): +{OFFSET_A_UTC}h")
    log.info(f"Usuario: {usuario or 'cli'}")

    # Paso 1: Stock actual
    stock = obtener_stock_actual()
    log.info(f"Stock actual: {len(stock)} artículos")

    # Paso 2: Trazabilidad post-corte
    traz = obtener_trazabilidad_post_corte(corte_ts)
    log.info(f"Movimientos post-corte: {len(traz)} artículos con movimiento")

    # Paso 3: OPs generadas al corte
    ops = obtener_ops_generadas_al_corte(corte_ts)
    log.info(f"OPs generadas al corte: {len(ops)} → {ops}")

    # Paso 4: Materiales y productos
    materiales = obtener_materiales_ops(ops)
    productos = obtener_productos_ops(ops)
    log.info(f"Materiales a devolver: {len(materiales)} artículos")
    log.info(f"Productos a quitar: {len(productos)} artículos")

    # Paso 5: Calcular stock teórico por artículo
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

    # Paso 8: Poblar inv_ops_revisar (auditoría de OPs cerca del corte)
    n_revisar = poblar_ops_revisar(fecha_corte, ops, ahora)
    log.info(f"OPs en auditoría: {n_revisar} (preservadas revisiones manuales)")

    log.info(f"Guardados: {len(filas)} artículos en inv_teorico")
    log.info(f"=== FIN CÁLCULO TEÓRICO ({ahora}) ===")
    return {
        'articulos': len(filas),
        'ops_generadas': len(ops),
        'mov_post_corte': len(traz),
        'materiales_ajustados': len(materiales),
        'productos_ajustados': len(productos),
        'calculado_en': ahora,
        'timezone': TIMEZONE,
    }


def actualizar_conteos(fecha_corte):
    """Actualiza inventario_teorico en inv_conteos con los datos calculados."""
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
        log.info(f"Conteos actualizados con stock teórico")
    conn.close()


def poblar_ops_revisar(fecha_corte, ops_incluidas_ids, ahora):
    """Pobla inv_ops_revisar con todas las OPs creadas antes del corte que
    eran vigentes al corte (incluidas y excluidas del cálculo).

    Marca como 'sospechosa' las que tienen un evento (creación/cambio_estado/anulación)
    dentro de ±6 horas del corte. Preserva las revisiones manuales al re-poblar.
    """
    corte_ts = f"{fecha_corte} 23:59:59"
    incluidas_set = set(str(o) for o in ops_incluidas_ids)

    # Traer todas las OPs candidatas (creadas antes del corte, vigentes al corte)
    ops = query(DB_EFFI, """
        SELECT
          e.id_orden,
          e.fecha_de_creacion,
          e.fecha_de_anulacion,
          e.vigencia,
          e.observacion
        FROM zeffi_produccion_encabezados e
        WHERE e.fecha_de_creacion <= %s
          AND (
            e.vigencia = 'Vigente'
            OR (e.vigencia = 'Anulado' AND e.fecha_de_anulacion > %s)
          )
    """, (corte_ts, corte_ts))

    if not ops:
        return 0

    op_ids = [str(o['id_orden']) for o in ops]
    placeholders = ','.join(['%s'] * len(op_ids))

    # Cambios a Procesada para todas estas OPs (UTC, restamos offset para comparar con corte COT)
    cambios_rows = query(DB_EFFI, f"""
        SELECT id_orden,
               MIN(DATE_SUB(f_cambio_de_estado, INTERVAL {OFFSET_A_UTC} HOUR)) AS fecha_procesada_cot
        FROM zeffi_cambios_estado
        WHERE id_orden IN ({placeholders})
          AND nuevo_estado = 'Procesada'
        GROUP BY id_orden
    """, tuple(op_ids))
    cambios_map = {str(r['id_orden']): r['fecha_procesada_cot'] for r in cambios_rows}

    # Conteo de materiales y productos por OP
    mat_rows = query(DB_EFFI, f"""
        SELECT id_orden, COUNT(*) AS n
        FROM zeffi_materiales
        WHERE id_orden IN ({placeholders}) AND vigencia = 'Orden vigente'
        GROUP BY id_orden
    """, tuple(op_ids))
    materiales_map = {str(r['id_orden']): r['n'] for r in mat_rows}

    prod_rows = query(DB_EFFI, f"""
        SELECT id_orden, COUNT(*) AS n
        FROM zeffi_articulos_producidos
        WHERE id_orden IN ({placeholders}) AND vigencia = 'Orden vigente'
        GROUP BY id_orden
    """, tuple(op_ids))
    productos_map = {str(r['id_orden']): r['n'] for r in prod_rows}

    # Descripción: primer producto producido o material si no hay producto
    desc_rows = query(DB_EFFI, f"""
        SELECT p.id_orden, MIN(p.descripcion_articulo_producido) AS desc_prod
        FROM zeffi_articulos_producidos p
        WHERE p.id_orden IN ({placeholders}) AND p.vigencia = 'Orden vigente'
        GROUP BY p.id_orden
    """, tuple(op_ids))
    desc_prod_map = {str(r['id_orden']): r['desc_prod'] for r in desc_rows}

    desc_mat_rows = query(DB_EFFI, f"""
        SELECT m.id_orden, MIN(m.descripcion_material) AS desc_mat
        FROM zeffi_materiales m
        WHERE m.id_orden IN ({placeholders}) AND m.vigencia = 'Orden vigente'
        GROUP BY m.id_orden
    """, tuple(op_ids))
    desc_mat_map = {str(r['id_orden']): r['desc_mat'] for r in desc_mat_rows}

    # Procesar cada OP y construir filas
    corte_dt = datetime.strptime(corte_ts, '%Y-%m-%d %H:%M:%S')
    UMBRAL_MIN = 6 * 60  # 6 horas en minutos
    filas = []

    def to_dt(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        try:
            return datetime.strptime(str(v)[:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    for op in ops:
        oid = str(op['id_orden'])
        f_creacion = to_dt(op['fecha_de_creacion'])
        f_anulacion = to_dt(op['fecha_de_anulacion'])
        f_procesada = to_dt(cambios_map.get(oid))

        # Estado al corte
        if f_procesada and f_procesada <= corte_dt:
            estado_corte = 'Procesada'
            incluida = 0
        else:
            estado_corte = 'Generada'
            incluida = 1 if oid in incluidas_set else 0

        # Calcular minutos del corte (evento más cercano)
        eventos = []
        if f_creacion:
            eventos.append(int((f_creacion - corte_dt).total_seconds() / 60))
        if f_procesada:
            eventos.append(int((f_procesada - corte_dt).total_seconds() / 60))
        if f_anulacion:
            eventos.append(int((f_anulacion - corte_dt).total_seconds() / 60))

        minutos_corte = min(eventos, key=abs) if eventos else None
        sospechosa = 1 if (minutos_corte is not None and abs(minutos_corte) <= UMBRAL_MIN) else 0

        descripcion = desc_prod_map.get(oid) or desc_mat_map.get(oid) or f'OP {oid}'

        filas.append((
            fecha_corte, oid, descripcion[:255],
            f_creacion, f_anulacion, f_procesada,
            estado_corte, op['vigencia'], incluida, minutos_corte, sospechosa,
            materiales_map.get(oid, 0), productos_map.get(oid, 0),
            ahora
        ))

    # Guardar preservando revisiones manuales
    conn = pymysql.connect(**DB_INV)
    with conn.cursor() as cur:
        for f in filas:
            cur.execute("""
                INSERT INTO inv_ops_revisar
                  (fecha_corte, id_orden, descripcion, fecha_creacion, fecha_anulacion,
                   fecha_cambio_procesada, estado_al_corte, vigencia_al_corte,
                   incluida_en_calculo, minutos_del_corte, sospechosa,
                   materiales_count, productos_count, calculado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  descripcion = VALUES(descripcion),
                  fecha_creacion = VALUES(fecha_creacion),
                  fecha_anulacion = VALUES(fecha_anulacion),
                  fecha_cambio_procesada = VALUES(fecha_cambio_procesada),
                  estado_al_corte = VALUES(estado_al_corte),
                  vigencia_al_corte = VALUES(vigencia_al_corte),
                  incluida_en_calculo = VALUES(incluida_en_calculo),
                  minutos_del_corte = VALUES(minutos_del_corte),
                  sospechosa = VALUES(sospechosa),
                  materiales_count = VALUES(materiales_count),
                  productos_count = VALUES(productos_count),
                  calculado_en = VALUES(calculado_en)
            """, f)
        conn.commit()
    conn.close()

    return len(filas)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calcular inventario teórico a fecha de corte')
    parser.add_argument('--fecha', default=str(date.today()), help='Fecha de corte YYYY-MM-DD')
    parser.add_argument('--usuario', default='cli', help='Usuario que ejecuta')
    args = parser.parse_args()
    calcular(args.fecha, args.usuario)
