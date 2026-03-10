#!/usr/bin/env python3
"""
calcular_resumen_ventas_canal.py
Calcula y actualiza resumen_ventas_facturas_canal_mes en effi_data.
PK: (mes, canal) — ventas agrupadas por canal de marketing y mes.
Se ejecuta como paso 3b del pipeline, después de calcular_resumen_ventas.py.
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

def cn(field):
    """CAST TEXT con coma decimal a DECIMAL(15,2)."""
    return f"CAST(REPLACE(COALESCE({field}, '0'), ',', '.') AS DECIMAL(15,2))"

def fval(v, default=0.0):
    return float(v) if v is not None else default

def ival(v, default=0):
    return int(v) if v is not None else default

# ─── DDL ──────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS resumen_ventas_facturas_canal_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    canal                    VARCHAR(255)  NOT NULL COMMENT 'tipo de marketing (marketing_cliente)',
    fecha_actualizacion      DATETIME,

    -- Financiero
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM precio_bruto_total',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuento_total',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (decimal 0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM precio_neto_total (sin IVA, neto de descuentos)',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuesto_total',
    fin_pct_del_mes          DECIMAL(8,4)  COMMENT 'participacion canal en total mes (decimal 0-1)',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - cto_costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'cto_utilidad_bruta / fin_ventas_netas_sin_iva (decimal 0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad',
    vol_num_facturas         INT           COMMENT 'COUNT DISTINCT numero_factura',
    vol_ticket_promedio      DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / vol_num_facturas',

    -- Clientes
    cli_clientes_activos     INT           COMMENT 'Clientes distintos con factura en el mes-canal',
    cli_clientes_nuevos      INT           COMMENT 'Clientes cuya primera factura historica es de este mes-canal',
    cli_vtas_por_cliente     DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / cli_clientes_activos',

    -- Catalogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas vendidas (cod_articulo)',

    -- Top
    top_cliente              TEXT          COMMENT 'Cliente con mayores ventas en este canal-mes',
    top_cliente_ventas       DECIMAL(15,2),
    top_producto_cod         TEXT          COMMENT 'cod_articulo del producto top en este canal-mes',
    top_producto_nombre      TEXT,
    top_producto_ventas      DECIMAL(15,2),

    -- Proyeccion (solo mes corriente, NULL si mes cerrado)
    pry_dia_del_mes          INT           COMMENT 'Dia actual del mes (solo mes corriente)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyeccion lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'pry_proyeccion_mes / ant_ventas_netas (decimal 0-1)',

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva del mismo canal-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas - ant) / ant (decimal 0-1)',

    PRIMARY KEY (mes, canal)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_canal.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    conn.commit()

    resumen = {}   # key: (mes, canal) → dict de campos

    # ── 1. Agregación principal desde detalle ─────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')                AS mes,
            COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal')  AS canal,
            SUM({cn('precio_bruto_total')})                             AS fin_ventas_brutas,
            SUM({cn('descuento_total')})                                AS fin_descuentos,
            SUM({cn('precio_bruto_total')}) - SUM({cn('descuento_total')}) AS fin_ventas_netas_sin_iva,
            SUM({cn('impuesto_total')})                                 AS fin_impuestos,
            SUM({cn('costo_manual_total')})                             AS cto_costo_total,
            SUM({cn('cantidad')})                                       AS vol_unidades,
            COUNT(DISTINCT id_numeracion)                               AS vol_num_facturas,
            COUNT(DISTINCT id_cliente)                                  AS cli_clientes_activos,
            COUNT(DISTINCT cod_articulo)                                AS cat_num_referencias
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, canal
        ORDER BY mes, canal
    """)

    for row in cursor.fetchall():
        mes, canal = row['mes'], row['canal']
        if not mes:
            continue
        resumen[(mes, canal)] = {
            'fin_ventas_brutas':        fval(row['fin_ventas_brutas']),
            'fin_descuentos':           fval(row['fin_descuentos']),
            'fin_ventas_netas_sin_iva': fval(row['fin_ventas_netas_sin_iva']),
            'fin_impuestos':            fval(row['fin_impuestos']),
            'cto_costo_total':          fval(row['cto_costo_total']),
            'vol_unidades_vendidas':    fval(row['vol_unidades']),
            'vol_num_facturas':         ival(row['vol_num_facturas']),
            'cli_clientes_activos':     ival(row['cli_clientes_activos']),
            'cat_num_referencias':      ival(row['cat_num_referencias']),
        }

    # ── 2. Clientes nuevos por (mes, canal) ───────────────────────────────────
    # Clientes cuya primera factura histórica (en cualquier canal) cae en este mes-canal
    cursor.execute("""
        SELECT mes, canal, COUNT(*) AS nuevos
        FROM (
            SELECT
                d.id_cliente,
                COALESCE(NULLIF(TRIM(d.marketing_cliente), ''), 'Sin canal') AS canal,
                DATE_FORMAT(d.fecha_creacion_factura, '%Y-%m')               AS mes
            FROM zeffi_facturas_venta_detalle d
            INNER JOIN (
                SELECT id_cliente, MIN(fecha_creacion_factura) AS primera_fecha
                FROM zeffi_facturas_venta_detalle
                WHERE vigencia_factura = 'Vigente'
                GROUP BY id_cliente
            ) p ON d.id_cliente = p.id_cliente
                AND d.fecha_creacion_factura = p.primera_fecha
            WHERE d.vigencia_factura = 'Vigente'
            GROUP BY d.id_cliente, canal, mes
        ) t
        GROUP BY mes, canal
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen:
            resumen[key]['cli_clientes_nuevos'] = ival(row['nuevos'])

    # ── 3. Top cliente por (mes, canal) ───────────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')                AS mes,
            COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal')  AS canal,
            cliente,
            SUM({cn('precio_neto_total')})                              AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, canal, cliente
        ORDER BY mes ASC, canal ASC, ventas DESC
    """)

    seen_cli = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen and key not in seen_cli:
            seen_cli.add(key)
            resumen[key]['top_cliente']        = row['cliente']
            resumen[key]['top_cliente_ventas'] = fval(row['ventas'])

    # ── 4. Top producto por (mes, canal) ──────────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')                AS mes,
            COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal')  AS canal,
            cod_articulo,
            descripcion_articulo,
            SUM({cn('precio_neto_total')})                              AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, canal, cod_articulo, descripcion_articulo
        ORDER BY mes ASC, canal ASC, ventas DESC
    """)

    seen_prod = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen and key not in seen_prod:
            seen_prod.add(key)
            resumen[key]['top_producto_cod']    = row['cod_articulo']
            resumen[key]['top_producto_nombre'] = row['descripcion_articulo']
            resumen[key]['top_producto_ventas'] = fval(row['ventas'])

    # ── 5. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Totales por mes (para fin_pct_del_mes)
    totales_mes = {}
    for (mes, canal), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    # Año anterior
    for (mes, canal) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_mes    = f'{year-1:04d}-{month:02d}'
        d           = resumen[(mes, canal)]
        prev        = resumen.get((prev_mes, canal))

        d['ant_ventas_netas'] = prev['fin_ventas_netas_sin_iva'] if prev else None
        if prev and prev.get('fin_ventas_netas_sin_iva'):
            d['ant_var_ventas_pct'] = (
                (d['fin_ventas_netas_sin_iva'] - prev['fin_ventas_netas_sin_iva'])
                / prev['fin_ventas_netas_sin_iva']
            )
        else:
            d['ant_var_ventas_pct'] = None

    # Resto de derivados
    for (mes, canal), d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)

        d['fin_pct_descuento']       = d.get('fin_descuentos', 0) / brutas if brutas else None
        d['fin_pct_del_mes']         = netas / totales_mes[mes] if totales_mes.get(mes) else None
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas if netas else None

        facturas = d.get('vol_num_facturas', 0)
        d['vol_ticket_promedio'] = netas / facturas if facturas else None

        activos = d.get('cli_clientes_activos', 0)
        d['cli_vtas_por_cliente'] = netas / activos if activos else None

        if mes == current_month:
            day_today               = today.day
            d['pry_dia_del_mes']    = day_today
            d['pry_proyeccion_mes'] = netas / day_today * days_in_month if day_today else None
            proy = d.get('pry_proyeccion_mes')
            ant  = d.get('ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 6. UPSERT ─────────────────────────────────────────────────────────────
    upsert_sql = """
        INSERT INTO resumen_ventas_facturas_canal_mes (
            mes, canal, fecha_actualizacion,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_pct_del_mes,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_facturas, vol_ticket_promedio,
            cli_clientes_activos, cli_clientes_nuevos, cli_vtas_por_cliente,
            cat_num_referencias,
            top_cliente, top_cliente_ventas,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct
        ) VALUES (
            %(mes)s, %(canal)s, %(fecha_actualizacion)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_pct_del_mes)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_facturas)s, %(vol_ticket_promedio)s,
            %(cli_clientes_activos)s, %(cli_clientes_nuevos)s, %(cli_vtas_por_cliente)s,
            %(cat_num_referencias)s,
            %(top_cliente)s, %(top_cliente_ventas)s,
            %(top_producto_cod)s, %(top_producto_nombre)s, %(top_producto_ventas)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            fin_ventas_brutas        = VALUES(fin_ventas_brutas),
            fin_descuentos           = VALUES(fin_descuentos),
            fin_pct_descuento        = VALUES(fin_pct_descuento),
            fin_ventas_netas_sin_iva = VALUES(fin_ventas_netas_sin_iva),
            fin_impuestos            = VALUES(fin_impuestos),
            fin_pct_del_mes          = VALUES(fin_pct_del_mes),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_unidades_vendidas    = VALUES(vol_unidades_vendidas),
            vol_num_facturas         = VALUES(vol_num_facturas),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cli_clientes_activos     = VALUES(cli_clientes_activos),
            cli_clientes_nuevos      = VALUES(cli_clientes_nuevos),
            cli_vtas_por_cliente     = VALUES(cli_vtas_por_cliente),
            cat_num_referencias      = VALUES(cat_num_referencias),
            top_cliente              = VALUES(top_cliente),
            top_cliente_ventas       = VALUES(top_cliente_ventas),
            top_producto_cod         = VALUES(top_producto_cod),
            top_producto_nombre      = VALUES(top_producto_nombre),
            top_producto_ventas      = VALUES(top_producto_ventas),
            pry_dia_del_mes          = VALUES(pry_dia_del_mes),
            pry_proyeccion_mes       = VALUES(pry_proyeccion_mes),
            pry_ritmo_pct            = VALUES(pry_ritmo_pct),
            ant_ventas_netas         = VALUES(ant_ventas_netas),
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct)
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, canal) in sorted(resumen.keys()):
        d = resumen[(mes, canal)]
        row = {
            'mes':                      mes,
            'canal':                    canal,
            'fecha_actualizacion':      now,
            'fin_ventas_brutas':        d.get('fin_ventas_brutas'),
            'fin_descuentos':           d.get('fin_descuentos'),
            'fin_pct_descuento':        d.get('fin_pct_descuento'),
            'fin_ventas_netas_sin_iva': d.get('fin_ventas_netas_sin_iva'),
            'fin_impuestos':            d.get('fin_impuestos'),
            'fin_pct_del_mes':          d.get('fin_pct_del_mes'),
            'cto_costo_total':          d.get('cto_costo_total'),
            'cto_utilidad_bruta':       d.get('cto_utilidad_bruta'),
            'cto_margen_utilidad_pct':  d.get('cto_margen_utilidad_pct'),
            'vol_unidades_vendidas':    d.get('vol_unidades_vendidas'),
            'vol_num_facturas':         d.get('vol_num_facturas'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cli_clientes_activos':     d.get('cli_clientes_activos'),
            'cli_clientes_nuevos':      d.get('cli_clientes_nuevos'),
            'cli_vtas_por_cliente':     d.get('cli_vtas_por_cliente'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'top_cliente':              d.get('top_cliente'),
            'top_cliente_ventas':       d.get('top_cliente_ventas'),
            'top_producto_cod':         d.get('top_producto_cod'),
            'top_producto_nombre':      d.get('top_producto_nombre'),
            'top_producto_ventas':      d.get('top_producto_ventas'),
            'pry_dia_del_mes':          d.get('pry_dia_del_mes'),
            'pry_proyeccion_mes':       d.get('pry_proyeccion_mes'),
            'pry_ritmo_pct':            d.get('pry_ritmo_pct'),
            'ant_ventas_netas':         d.get('ant_ventas_netas'),
            'ant_var_ventas_pct':       d.get('ant_var_ventas_pct'),
        }
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_canal_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
