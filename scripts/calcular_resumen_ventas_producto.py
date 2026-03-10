#!/usr/bin/env python3
"""
calcular_resumen_ventas_producto.py
Calcula y actualiza resumen_ventas_facturas_producto_mes en effi_data.
PK: (mes, cod_articulo) — ventas agrupadas por referencia de producto y mes.
Se ejecuta como paso 3d del pipeline, después de calcular_resumen_ventas_cliente.py.
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
CREATE TABLE IF NOT EXISTS resumen_ventas_facturas_producto_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    cod_articulo             VARCHAR(100)  NOT NULL COMMENT 'cod_articulo de zeffi_facturas_venta_detalle',
    fecha_actualizacion      DATETIME,

    -- Dimensiones del producto
    nombre                   TEXT          COMMENT 'descripcion_articulo',
    categoria                TEXT          COMMENT 'categoria_articulo',
    marca                    TEXT          COMMENT 'marca_articulo',

    -- Financiero
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM precio_bruto_total',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuento_total',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (decimal 0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'precio_bruto_total - descuento_total',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuesto_total',
    fin_pct_del_mes          DECIMAL(8,4)  COMMENT 'participacion producto en total ventas mes (decimal 0-1)',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - cto_costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'cto_utilidad_bruta / fin_ventas_netas_sin_iva (decimal 0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad',
    vol_num_facturas         INT           COMMENT 'COUNT DISTINCT id_numeracion (facturas con este producto)',
    vol_precio_unitario_prom DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / vol_unidades_vendidas',

    -- Clientes
    cli_clientes_activos     INT           COMMENT 'Clientes distintos que compraron este producto el mes',

    -- Top
    top_cliente              TEXT          COMMENT 'Cliente que mas compro este producto en el mes',
    top_cliente_ventas       DECIMAL(15,2),
    top_canal                TEXT          COMMENT 'Canal con mayores ventas de este producto en el mes',
    top_canal_ventas         DECIMAL(15,2),

    -- Proyeccion (solo mes corriente, NULL si mes cerrado)
    pry_dia_del_mes          INT           COMMENT 'Dia actual del mes (solo mes corriente)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyeccion lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'pry_proyeccion_mes / ant_ventas_netas (decimal 0-1)',

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva del mismo producto-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas - ant) / ant (decimal 0-1)',
    ant_unidades             DECIMAL(15,2) COMMENT 'vol_unidades_vendidas del mismo producto-mes ano anterior',
    ant_var_unidades_pct     DECIMAL(8,4)  COMMENT '(unidades - ant) / ant (decimal 0-1)',

    PRIMARY KEY (mes, cod_articulo)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_producto.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    conn.commit()

    resumen = {}   # key: (mes, cod_articulo) → dict de campos

    # ── 1. Agregación principal desde detalle ─────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')        AS mes,
            cod_articulo,
            MAX(descripcion_articulo)                           AS nombre,
            MAX(categoria_articulo)                             AS categoria,
            MAX(marca_articulo)                                 AS marca,
            SUM({cn('precio_bruto_total')})                     AS fin_ventas_brutas,
            SUM({cn('descuento_total')})                        AS fin_descuentos,
            SUM({cn('precio_bruto_total')}) - SUM({cn('descuento_total')}) AS fin_ventas_netas_sin_iva,
            SUM({cn('impuesto_total')})                         AS fin_impuestos,
            SUM({cn('costo_manual_total')})                     AS cto_costo_total,
            SUM({cn('cantidad')})                               AS vol_unidades,
            COUNT(DISTINCT id_numeracion)                       AS vol_num_facturas,
            COUNT(DISTINCT id_cliente)                          AS cli_clientes_activos
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
          AND cod_articulo IS NOT NULL AND cod_articulo != ''
        GROUP BY mes, cod_articulo
        ORDER BY mes, cod_articulo
    """)

    for row in cursor.fetchall():
        mes, cod = row['mes'], row['cod_articulo']
        if not mes or not cod:
            continue
        resumen[(mes, cod)] = {
            'nombre':                   row['nombre'],
            'categoria':                row['categoria'],
            'marca':                    row['marca'],
            'fin_ventas_brutas':        fval(row['fin_ventas_brutas']),
            'fin_descuentos':           fval(row['fin_descuentos']),
            'fin_ventas_netas_sin_iva': fval(row['fin_ventas_netas_sin_iva']),
            'fin_impuestos':            fval(row['fin_impuestos']),
            'cto_costo_total':          fval(row['cto_costo_total']),
            'vol_unidades_vendidas':    fval(row['vol_unidades']),
            'vol_num_facturas':         ival(row['vol_num_facturas']),
            'cli_clientes_activos':     ival(row['cli_clientes_activos']),
        }

    # ── 2. Top cliente por (mes, cod_articulo) ────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m') AS mes,
            cod_articulo,
            cliente,
            SUM({cn('precio_bruto_total')}) - SUM({cn('descuento_total')}) AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
          AND cod_articulo IS NOT NULL AND cod_articulo != ''
        GROUP BY mes, cod_articulo, cliente
        ORDER BY mes ASC, cod_articulo ASC, ventas DESC
    """)

    seen_cli = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['cod_articulo'])
        if key in resumen and key not in seen_cli:
            seen_cli.add(key)
            resumen[key]['top_cliente']        = row['cliente']
            resumen[key]['top_cliente_ventas'] = fval(row['ventas'])

    # ── 3. Top canal por (mes, cod_articulo) ──────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')                AS mes,
            cod_articulo,
            COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal')  AS canal,
            SUM({cn('precio_bruto_total')}) - SUM({cn('descuento_total')}) AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
          AND cod_articulo IS NOT NULL AND cod_articulo != ''
        GROUP BY mes, cod_articulo, canal
        ORDER BY mes ASC, cod_articulo ASC, ventas DESC
    """)

    seen_canal = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['cod_articulo'])
        if key in resumen and key not in seen_canal:
            seen_canal.add(key)
            resumen[key]['top_canal']        = row['canal']
            resumen[key]['top_canal_ventas'] = fval(row['ventas'])

    # ── 4. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Totales por mes (para fin_pct_del_mes)
    totales_mes = {}
    for (mes, cod), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    # Año anterior
    for (mes, cod) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_mes    = f'{year-1:04d}-{month:02d}'
        d           = resumen[(mes, cod)]
        prev        = resumen.get((prev_mes, cod))

        d['ant_ventas_netas'] = prev.get('fin_ventas_netas_sin_iva') if prev else None
        if prev and prev.get('fin_ventas_netas_sin_iva'):
            d['ant_var_ventas_pct'] = (
                (d['fin_ventas_netas_sin_iva'] - prev['fin_ventas_netas_sin_iva'])
                / prev['fin_ventas_netas_sin_iva']
            )
        else:
            d['ant_var_ventas_pct'] = None

        d['ant_unidades'] = prev.get('vol_unidades_vendidas') if prev else None
        if prev and prev.get('vol_unidades_vendidas'):
            d['ant_var_unidades_pct'] = (
                (d['vol_unidades_vendidas'] - prev['vol_unidades_vendidas'])
                / prev['vol_unidades_vendidas']
            )
        else:
            d['ant_var_unidades_pct'] = None

    # Resto de derivados
    for (mes, cod), d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas     = d.get('fin_ventas_netas_sin_iva', 0)
        brutas    = d.get('fin_ventas_brutas', 0)
        costo     = d.get('cto_costo_total', 0)
        unidades  = d.get('vol_unidades_vendidas', 0)

        d['fin_pct_descuento']       = d.get('fin_descuentos', 0) / brutas if brutas else None
        d['fin_pct_del_mes']         = netas / totales_mes[mes] if totales_mes.get(mes) else None
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas if netas else None
        d['vol_precio_unitario_prom'] = netas / unidades if unidades else None

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

    # ── 5. UPSERT ─────────────────────────────────────────────────────────────
    upsert_sql = """
        INSERT INTO resumen_ventas_facturas_producto_mes (
            mes, cod_articulo, fecha_actualizacion,
            nombre, categoria, marca,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_pct_del_mes,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_facturas, vol_precio_unitario_prom,
            cli_clientes_activos,
            top_cliente, top_cliente_ventas,
            top_canal, top_canal_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct,
            ant_unidades, ant_var_unidades_pct
        ) VALUES (
            %(mes)s, %(cod_articulo)s, %(fecha_actualizacion)s,
            %(nombre)s, %(categoria)s, %(marca)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_pct_del_mes)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_facturas)s, %(vol_precio_unitario_prom)s,
            %(cli_clientes_activos)s,
            %(top_cliente)s, %(top_cliente_ventas)s,
            %(top_canal)s, %(top_canal_ventas)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s,
            %(ant_unidades)s, %(ant_var_unidades_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            nombre                   = VALUES(nombre),
            categoria                = VALUES(categoria),
            marca                    = VALUES(marca),
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
            vol_precio_unitario_prom = VALUES(vol_precio_unitario_prom),
            cli_clientes_activos     = VALUES(cli_clientes_activos),
            top_cliente              = VALUES(top_cliente),
            top_cliente_ventas       = VALUES(top_cliente_ventas),
            top_canal                = VALUES(top_canal),
            top_canal_ventas         = VALUES(top_canal_ventas),
            pry_dia_del_mes          = VALUES(pry_dia_del_mes),
            pry_proyeccion_mes       = VALUES(pry_proyeccion_mes),
            pry_ritmo_pct            = VALUES(pry_ritmo_pct),
            ant_ventas_netas         = VALUES(ant_ventas_netas),
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct),
            ant_unidades             = VALUES(ant_unidades),
            ant_var_unidades_pct     = VALUES(ant_var_unidades_pct)
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, cod) in sorted(resumen.keys()):
        d = resumen[(mes, cod)]
        row = {
            'mes':                      mes,
            'cod_articulo':             cod,
            'fecha_actualizacion':      now,
            'nombre':                   d.get('nombre'),
            'categoria':                d.get('categoria'),
            'marca':                    d.get('marca'),
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
            'vol_precio_unitario_prom': d.get('vol_precio_unitario_prom'),
            'cli_clientes_activos':     d.get('cli_clientes_activos'),
            'top_cliente':              d.get('top_cliente'),
            'top_cliente_ventas':       d.get('top_cliente_ventas'),
            'top_canal':                d.get('top_canal'),
            'top_canal_ventas':         d.get('top_canal_ventas'),
            'pry_dia_del_mes':          d.get('pry_dia_del_mes'),
            'pry_proyeccion_mes':       d.get('pry_proyeccion_mes'),
            'pry_ritmo_pct':            d.get('pry_ritmo_pct'),
            'ant_ventas_netas':         d.get('ant_ventas_netas'),
            'ant_var_ventas_pct':       d.get('ant_var_ventas_pct'),
            'ant_unidades':             d.get('ant_unidades'),
            'ant_var_unidades_pct':     d.get('ant_var_unidades_pct'),
        }
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_producto_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
