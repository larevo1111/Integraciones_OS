#!/usr/bin/env python3
"""
calcular_resumen_ventas_remisiones_producto_mes.py
Calcula y actualiza resumen_ventas_remisiones_producto_mes en effi_data (staging).
PK: (mes, cod_articulo) — remisiones agrupadas por artículo y mes.
Paso 4d del pipeline.

Fuente: zeffi_remisiones_venta_detalle JOIN zeffi_remisiones_venta_encabezados
Incluye: 'Pendiente de facturar' + convertidas a factura
Excluye: anuladas verdaderas
"""

import datetime
from calendar import monthrange
import mysql.connector

DB = dict(
    host='127.0.0.1',
    port=3306,
    user='osadmin',
    password='Epist2487.',
    database='effi_data',
)

# ─── Utilidades ───────────────────────────────────────────────────────────────

def cn_det(field):
    """CAST TEXT plano a DECIMAL(15,2) — detalle."""
    return f"CAST(NULLIF(TRIM({field}), '') AS DECIMAL(15,2))"

def fval(v, default=0.0):
    return float(v) if v is not None else default

def ival(v, default=0):
    return int(v) if v is not None else default

def pct(v, limit=999.9999):
    """Normaliza porcentaje: NULL si es None o fuera de rango DECIMAL(8,4)."""
    if v is None:
        return None
    return v if abs(v) <= limit else None

# ─── Filtro SQL ───────────────────────────────────────────────────────────────

FILTRO_ENC_JOIN = """(
    e.estado_remision = 'Pendiente de facturar'
    OR e.observacion_de_anulacion LIKE 'Remisi\u00f3n convertida a factura de venta%'
)"""

# ─── DDL ──────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS resumen_ventas_remisiones_producto_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    cod_articulo             VARCHAR(100)  NOT NULL COMMENT 'Codigo articulo Effi',
    fecha_actualizacion      DATETIME,

    -- Identificacion
    descripcion_articulo     TEXT,
    categoria_articulo       TEXT,
    marca_articulo           TEXT,

    -- Financiero (de detalle)
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM precio_bruto_total',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuento_total',
    fin_pct_descuento        DECIMAL(8,4),
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'precio_bruto_total - descuento_total (sin IVA)',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuesto_total',
    fin_pct_del_mes          DECIMAL(8,4)  COMMENT 'participacion producto en total mes (0-1)',

    -- Costo
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2),
    cto_margen_utilidad_pct  DECIMAL(8,4),

    -- Volumen
    vol_cantidad             DECIMAL(15,2) COMMENT 'SUM cantidad',
    vol_num_remisiones       INT           COMMENT 'COUNT DISTINCT id_remision con este articulo',
    vol_precio_promedio      DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / vol_cantidad',

    -- Canal principal
    cat_canal_principal      VARCHAR(255)  COMMENT 'Canal con mayor ventas de este producto en el mes',

    -- Top cliente
    top_cliente              TEXT,
    top_cliente_ventas       DECIMAL(15,2),

    -- Proyeccion (solo mes corriente)
    pry_dia_del_mes          INT,
    pry_proyeccion_mes       DECIMAL(15,2),
    pry_ritmo_pct            DECIMAL(8,4),

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva mismo producto-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4),

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, cod_articulo)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_producto (mes, cod_articulo)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_remisiones_producto_mes.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(DDL)
    cursor.execute("ALTER TABLE resumen_ventas_remisiones_producto_mes ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes")
    conn.commit()

    resumen = {}   # key: (mes, cod_articulo)

    # ── 1. Agregacion desde detalle ───────────────────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            d.cod_articulo,
            MAX(d.descripcion_articulo)                                     AS descripcion_articulo,
            MAX(d.categoria_articulo)                                       AS categoria_articulo,
            MAX(d.marca_articulo)                                           AS marca_articulo,
            SUM({cn_det('d.precio_bruto_total')})                           AS fin_ventas_brutas,
            SUM({cn_det('d.descuento_total')})                              AS fin_descuentos,
            SUM({cn_det('d.precio_bruto_total')} - {cn_det('d.descuento_total')}) AS fin_ventas_netas_sin_iva,
            SUM({cn_det('d.impuesto_total')})                               AS fin_impuestos,
            SUM({cn_det('d.costo_manual_total')})                           AS cto_costo_total,
            SUM({cn_det('d.cantidad')})                                     AS vol_cantidad,
            COUNT(DISTINCT d.id_remision)                                   AS vol_num_remisiones
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
          AND d.cod_articulo IS NOT NULL AND d.cod_articulo != ''
        GROUP BY mes, d.cod_articulo
        ORDER BY mes, d.cod_articulo
    """)

    for row in cursor.fetchall():
        mes, cod = row['mes'], row['cod_articulo']
        if not mes or not cod:
            continue
        resumen[(mes, cod)] = {
            'descripcion_articulo':     row['descripcion_articulo'],
            'categoria_articulo':       row['categoria_articulo'],
            'marca_articulo':           row['marca_articulo'],
            'fin_ventas_brutas':        fval(row['fin_ventas_brutas']),
            'fin_descuentos':           fval(row['fin_descuentos']),
            'fin_ventas_netas_sin_iva': fval(row['fin_ventas_netas_sin_iva']),
            'fin_impuestos':            fval(row['fin_impuestos']),
            'cto_costo_total':          fval(row['cto_costo_total']),
            'vol_cantidad':             fval(row['vol_cantidad']),
            'vol_num_remisiones':       ival(row['vol_num_remisiones']),
        }

    # ── 2. Canal principal por (mes, cod_articulo) ────────────────────────────
    cursor.execute(f"""
        SELECT mes, cod_articulo, canal
        FROM (
            SELECT
                LEFT(e.fecha_de_creacion, 7)                                AS mes,
                d.cod_articulo,
                COALESCE(NULLIF(TRIM(e.tipo_de_markting), ''), 'Sin canal') AS canal,
                ROW_NUMBER() OVER (
                    PARTITION BY LEFT(e.fecha_de_creacion, 7), d.cod_articulo
                    ORDER BY SUM({cn_det('d.precio_bruto_total')} - {cn_det('d.descuento_total')}) DESC
                ) AS rn
            FROM zeffi_remisiones_venta_detalle d
            JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
            WHERE {FILTRO_ENC_JOIN}
              AND d.cod_articulo IS NOT NULL AND d.cod_articulo != ''
            GROUP BY LEFT(e.fecha_de_creacion, 7), d.cod_articulo, canal
        ) t WHERE rn = 1
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['cod_articulo'])
        if key in resumen:
            resumen[key]['cat_canal_principal'] = row['canal']

    # ── 3. Top cliente por (mes, cod_articulo) ────────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            d.cod_articulo,
            e.cliente,
            SUM({cn_det('d.precio_bruto_total')} - {cn_det('d.descuento_total')}) AS ventas
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
          AND d.cod_articulo IS NOT NULL AND d.cod_articulo != ''
        GROUP BY mes, d.cod_articulo, e.cliente
        ORDER BY mes, d.cod_articulo, ventas DESC
    """)

    seen = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['cod_articulo'])
        if key in resumen and key not in seen:
            seen.add(key)
            resumen[key]['top_cliente']        = row['cliente']
            resumen[key]['top_cliente_ventas'] = fval(row['ventas'])

    # ── 4. Derivados ──────────────────────────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    totales_mes = {}
    for (mes, cod), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    for (mes, cod) in sorted(resumen.keys()):
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        prev_mes      = f'{year-1:04d}-{month:02d}'
        d             = resumen[(mes, cod)]
        prev          = resumen.get((prev_mes, cod))

        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)
        cant   = d.get('vol_cantidad', 0)

        d['fin_pct_descuento']       = pct(d.get('fin_descuentos', 0) / brutas if brutas else None)
        d['fin_pct_del_mes']         = pct(netas / totales_mes[mes] if totales_mes.get(mes) else None)
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = pct((netas - costo) / netas if netas else None)
        d['vol_precio_promedio']     = netas / cant if cant else None

        d['ant_ventas_netas'] = prev.get('fin_ventas_netas_sin_iva') if prev else None
        if prev and prev.get('fin_ventas_netas_sin_iva'):
            d['ant_var_ventas_pct'] = pct(
                (netas - prev['fin_ventas_netas_sin_iva'])
                / prev['fin_ventas_netas_sin_iva']
            )
        else:
            d['ant_var_ventas_pct'] = None

        if mes == current_month:
            day_today               = today.day
            d['pry_dia_del_mes']    = day_today
            d['pry_proyeccion_mes'] = netas / day_today * days_in_month if day_today else None
            proy = d.get('pry_proyeccion_mes')
            ant  = d.get('ant_ventas_netas')
            d['pry_ritmo_pct'] = pct(proy / ant if (proy is not None and ant) else None)
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 5. UPSERT ─────────────────────────────────────────────────────────────
    upsert_sql = """
        INSERT INTO resumen_ventas_remisiones_producto_mes (
            _key, mes, cod_articulo, fecha_actualizacion,
            descripcion_articulo, categoria_articulo, marca_articulo,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_pct_del_mes,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_cantidad, vol_num_remisiones, vol_precio_promedio,
            cat_canal_principal,
            top_cliente, top_cliente_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct
        ) VALUES (
            %(_key)s, %(mes)s, %(cod_articulo)s, %(fecha_actualizacion)s,
            %(descripcion_articulo)s, %(categoria_articulo)s, %(marca_articulo)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_pct_del_mes)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_cantidad)s, %(vol_num_remisiones)s, %(vol_precio_promedio)s,
            %(cat_canal_principal)s,
            %(top_cliente)s, %(top_cliente_ventas)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            descripcion_articulo     = VALUES(descripcion_articulo),
            categoria_articulo       = VALUES(categoria_articulo),
            marca_articulo           = VALUES(marca_articulo),
            fin_ventas_brutas        = VALUES(fin_ventas_brutas),
            fin_descuentos           = VALUES(fin_descuentos),
            fin_pct_descuento        = VALUES(fin_pct_descuento),
            fin_ventas_netas_sin_iva = VALUES(fin_ventas_netas_sin_iva),
            fin_impuestos            = VALUES(fin_impuestos),
            fin_pct_del_mes          = VALUES(fin_pct_del_mes),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_cantidad             = VALUES(vol_cantidad),
            vol_num_remisiones       = VALUES(vol_num_remisiones),
            vol_precio_promedio      = VALUES(vol_precio_promedio),
            cat_canal_principal      = VALUES(cat_canal_principal),
            top_cliente              = VALUES(top_cliente),
            top_cliente_ventas       = VALUES(top_cliente_ventas),
            pry_dia_del_mes          = VALUES(pry_dia_del_mes),
            pry_proyeccion_mes       = VALUES(pry_proyeccion_mes),
            pry_ritmo_pct            = VALUES(pry_ritmo_pct),
            ant_ventas_netas         = VALUES(ant_ventas_netas),
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct)
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, cod) in sorted(resumen.keys()):
        d = resumen[(mes, cod)]
        cursor.execute(upsert_sql, {
            '_key':                     f'{mes}|{cod}',
            'mes':                      mes,
            'cod_articulo':             cod,
            'fecha_actualizacion':      now,
            'descripcion_articulo':     d.get('descripcion_articulo'),
            'categoria_articulo':       d.get('categoria_articulo'),
            'marca_articulo':           d.get('marca_articulo'),
            'fin_ventas_brutas':        d.get('fin_ventas_brutas'),
            'fin_descuentos':           d.get('fin_descuentos'),
            'fin_pct_descuento':        d.get('fin_pct_descuento'),
            'fin_ventas_netas_sin_iva': d.get('fin_ventas_netas_sin_iva'),
            'fin_impuestos':            d.get('fin_impuestos'),
            'fin_pct_del_mes':          d.get('fin_pct_del_mes'),
            'cto_costo_total':          d.get('cto_costo_total'),
            'cto_utilidad_bruta':       d.get('cto_utilidad_bruta'),
            'cto_margen_utilidad_pct':  d.get('cto_margen_utilidad_pct'),
            'vol_cantidad':             d.get('vol_cantidad'),
            'vol_num_remisiones':       d.get('vol_num_remisiones'),
            'vol_precio_promedio':      d.get('vol_precio_promedio'),
            'cat_canal_principal':      d.get('cat_canal_principal'),
            'top_cliente':              d.get('top_cliente'),
            'top_cliente_ventas':       d.get('top_cliente_ventas'),
            'pry_dia_del_mes':          d.get('pry_dia_del_mes'),
            'pry_proyeccion_mes':       d.get('pry_proyeccion_mes'),
            'pry_ritmo_pct':            d.get('pry_ritmo_pct'),
            'ant_ventas_netas':         d.get('ant_ventas_netas'),
            'ant_var_ventas_pct':       d.get('ant_var_ventas_pct'),
        })

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_remisiones_producto_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
