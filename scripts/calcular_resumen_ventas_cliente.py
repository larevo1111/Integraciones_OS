#!/usr/bin/env python3
"""
calcular_resumen_ventas_cliente.py
Calcula y actualiza resumen_ventas_facturas_cliente_mes en effi_data.
PK: (mes, id_cliente) — ventas agrupadas por cliente y mes.
Se ejecuta como paso 3c del pipeline, después de calcular_resumen_ventas_canal.py.
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
CREATE TABLE IF NOT EXISTS resumen_ventas_facturas_cliente_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    id_cliente               VARCHAR(100)  NOT NULL COMMENT 'id_cliente de zeffi_facturas_venta_detalle',
    fecha_actualizacion      DATETIME,

    -- Dimensiones del cliente
    cliente                  TEXT          COMMENT 'nombre del cliente (de facturas)',
    ciudad                   TEXT          COMMENT 'ciudad del maestro zeffi_clientes',
    departamento             TEXT          COMMENT 'departamento del maestro zeffi_clientes',
    canal                    TEXT          COMMENT 'tipo_de_marketing del maestro zeffi_clientes',
    vendedor                 TEXT          COMMENT 'vendedor del maestro zeffi_clientes',

    -- Financiero
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM precio_bruto_total',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuento_total',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (decimal 0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'precio_bruto_total - descuento_total',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuesto_total',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - cto_costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'cto_utilidad_bruta / fin_ventas_netas_sin_iva (decimal 0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad',
    vol_num_facturas         INT           COMMENT 'COUNT DISTINCT id_numeracion',
    vol_ticket_promedio      DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / vol_num_facturas',

    -- Catalogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas (cod_articulo)',

    -- Top producto
    top_producto_cod         TEXT          COMMENT 'cod_articulo con mayores ventas en el mes-cliente',
    top_producto_nombre      TEXT,
    top_producto_ventas      DECIMAL(15,2),

    -- Consignaciones (OVs del cliente en el mes)
    con_consignacion_pp      DECIMAL(15,2) COMMENT 'SUM total_neto de OVs del cliente en el mes',

    -- Cliente nuevo
    cli_es_nuevo             TINYINT(1)    COMMENT '1 si es la primera factura historica del cliente',

    -- Proyeccion (solo mes corriente, NULL si mes cerrado)
    pry_dia_del_mes          INT           COMMENT 'Dia actual del mes (solo mes corriente)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyeccion lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'pry_proyeccion_mes / ant_ventas_netas (decimal 0-1)',

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva del mismo cliente-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas - ant) / ant (decimal 0-1)',
    ant_consignacion_pp      DECIMAL(15,2) COMMENT 'con_consignacion_pp del mismo cliente-mes ano anterior',
    ant_var_consignacion_pct DECIMAL(8,4)  COMMENT '(con - ant_con) / ant_con (decimal 0-1)',

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, id_cliente)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_cliente (mes, id_cliente)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_cliente.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    cursor.execute("ALTER TABLE resumen_ventas_facturas_cliente_mes ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes")
    conn.commit()

    resumen = {}   # key: (mes, id_cliente) → dict de campos

    # ── 1. Agregación principal desde detalle + JOIN maestro clientes ──────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(d.fecha_creacion_factura, '%Y-%m')  AS mes,
            d.id_cliente,
            MAX(d.cliente)                                  AS cliente,
            MAX(c.ciudad)                                   AS ciudad,
            MAX(c.departamento)                             AS departamento,
            MAX(COALESCE(NULLIF(TRIM(c.tipo_de_marketing), ''), 'Sin canal')) AS canal,
            MAX(c.vendedor)                                 AS vendedor,
            SUM({cn('d.precio_bruto_total')})               AS fin_ventas_brutas,
            SUM({cn('d.descuento_total')})                  AS fin_descuentos,
            SUM({cn('d.precio_bruto_total')}) - SUM({cn('d.descuento_total')}) AS fin_ventas_netas_sin_iva,
            SUM({cn('d.impuesto_total')})                   AS fin_impuestos,
            SUM({cn('d.costo_manual_total')})               AS cto_costo_total,
            SUM({cn('d.cantidad')})                         AS vol_unidades,
            COUNT(DISTINCT d.id_numeracion)                 AS vol_num_facturas,
            COUNT(DISTINCT d.cod_articulo)                  AS cat_num_referencias
        FROM zeffi_facturas_venta_detalle d
        LEFT JOIN zeffi_clientes c ON c.numero_de_identificacion = SUBSTRING_INDEX(d.id_cliente, ' ', -1)
        WHERE d.vigencia_factura = 'Vigente'
        GROUP BY mes, d.id_cliente
        ORDER BY mes, d.id_cliente
    """)

    for row in cursor.fetchall():
        mes, id_cli = row['mes'], row['id_cliente']
        if not mes or not id_cli:
            continue
        resumen[(mes, id_cli)] = {
            'cliente':                  row['cliente'],
            'ciudad':                   row['ciudad'],
            'departamento':             row['departamento'],
            'canal':                    row['canal'],
            'vendedor':                 row['vendedor'],
            'fin_ventas_brutas':        fval(row['fin_ventas_brutas']),
            'fin_descuentos':           fval(row['fin_descuentos']),
            'fin_ventas_netas_sin_iva': fval(row['fin_ventas_netas_sin_iva']),
            'fin_impuestos':            fval(row['fin_impuestos']),
            'cto_costo_total':          fval(row['cto_costo_total']),
            'vol_unidades_vendidas':    fval(row['vol_unidades']),
            'vol_num_facturas':         ival(row['vol_num_facturas']),
            'cat_num_referencias':      ival(row['cat_num_referencias']),
        }

    # ── 2. Cliente nuevo (primera factura histórica en este mes) ──────────────
    cursor.execute("""
        SELECT id_cliente, DATE_FORMAT(MIN(fecha_creacion_factura), '%Y-%m') AS primer_mes
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY id_cliente
    """)

    primer_mes_cliente = {row['id_cliente']: row['primer_mes'] for row in cursor.fetchall()}

    for (mes, id_cli), d in resumen.items():
        d['cli_es_nuevo'] = 1 if primer_mes_cliente.get(id_cli) == mes else 0

    # ── 3. Top producto por (mes, id_cliente) ─────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m') AS mes,
            id_cliente,
            cod_articulo,
            descripcion_articulo,
            SUM({cn('precio_neto_total')})               AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, id_cliente, cod_articulo, descripcion_articulo
        ORDER BY mes ASC, id_cliente ASC, ventas DESC
    """)

    seen_prod = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['id_cliente'])
        if key in resumen and key not in seen_prod:
            seen_prod.add(key)
            resumen[key]['top_producto_cod']    = row['cod_articulo']
            resumen[key]['top_producto_nombre'] = row['descripcion_articulo']
            resumen[key]['top_producto_ventas'] = fval(row['ventas'])

    # ── 4. Consignaciones OV por (mes, id_cliente) ────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            id_cliente,
            SUM({cn('total_neto')})                 AS con_pp
        FROM zeffi_ordenes_venta_encabezados
        WHERE NOT (
            vigencia = 'Anulada'
            AND DATEDIFF(
                    COALESCE(fecha_de_anulacion, fecha_de_creacion),
                    fecha_de_creacion
                ) <= 1
            AND LOWER(COALESCE(observacion_de_anulacion, ''))
                NOT REGEXP 'liquidac|remis|convertid|retiro|devolu|no vendi|no se entreg'
        )
        GROUP BY mes, id_cliente
    """)

    for row in cursor.fetchall():
        mes_ov, id_cli = row['mes'], row['id_cliente']
        if not mes_ov or not id_cli:
            continue
        key = (mes_ov, id_cli)
        if key in resumen:
            resumen[key]['con_consignacion_pp'] = fval(row['con_pp'])
        # Si el cliente no tiene facturas ese mes, no crear entrada solo por OV

    # ── 5. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Año anterior
    for (mes, id_cli) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_mes    = f'{year-1:04d}-{month:02d}'
        d           = resumen[(mes, id_cli)]
        prev        = resumen.get((prev_mes, id_cli))

        d['ant_ventas_netas'] = prev.get('fin_ventas_netas_sin_iva') if prev else None
        if prev and prev.get('fin_ventas_netas_sin_iva'):
            d['ant_var_ventas_pct'] = (
                (d['fin_ventas_netas_sin_iva'] - prev['fin_ventas_netas_sin_iva'])
                / prev['fin_ventas_netas_sin_iva']
            )
        else:
            d['ant_var_ventas_pct'] = None

        prev_con = (prev or {}).get('con_consignacion_pp')
        cur_con  = d.get('con_consignacion_pp')
        d['ant_consignacion_pp'] = prev_con
        if prev_con and cur_con is not None:
            d['ant_var_consignacion_pct'] = (cur_con - prev_con) / prev_con
        else:
            d['ant_var_consignacion_pct'] = None

    # Resto de derivados
    for (mes, id_cli), d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)

        d['fin_pct_descuento']       = d.get('fin_descuentos', 0) / brutas if brutas else None
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas if netas else None

        facturas = d.get('vol_num_facturas', 0)
        d['vol_ticket_promedio'] = netas / facturas if facturas else None

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
        INSERT INTO resumen_ventas_facturas_cliente_mes (
            _key, mes, id_cliente, fecha_actualizacion,
            cliente, ciudad, departamento, canal, vendedor,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_facturas, vol_ticket_promedio,
            cat_num_referencias,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            con_consignacion_pp,
            cli_es_nuevo,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct,
            ant_consignacion_pp, ant_var_consignacion_pct
        ) VALUES (
            %(_key)s, %(mes)s, %(id_cliente)s, %(fecha_actualizacion)s,
            %(cliente)s, %(ciudad)s, %(departamento)s, %(canal)s, %(vendedor)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_facturas)s, %(vol_ticket_promedio)s,
            %(cat_num_referencias)s,
            %(top_producto_cod)s, %(top_producto_nombre)s, %(top_producto_ventas)s,
            %(con_consignacion_pp)s,
            %(cli_es_nuevo)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s,
            %(ant_consignacion_pp)s, %(ant_var_consignacion_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            cliente                  = VALUES(cliente),
            ciudad                   = VALUES(ciudad),
            departamento             = VALUES(departamento),
            canal                    = VALUES(canal),
            vendedor                 = VALUES(vendedor),
            fin_ventas_brutas        = VALUES(fin_ventas_brutas),
            fin_descuentos           = VALUES(fin_descuentos),
            fin_pct_descuento        = VALUES(fin_pct_descuento),
            fin_ventas_netas_sin_iva = VALUES(fin_ventas_netas_sin_iva),
            fin_impuestos            = VALUES(fin_impuestos),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_unidades_vendidas    = VALUES(vol_unidades_vendidas),
            vol_num_facturas         = VALUES(vol_num_facturas),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cat_num_referencias      = VALUES(cat_num_referencias),
            top_producto_cod         = VALUES(top_producto_cod),
            top_producto_nombre      = VALUES(top_producto_nombre),
            top_producto_ventas      = VALUES(top_producto_ventas),
            con_consignacion_pp      = VALUES(con_consignacion_pp),
            cli_es_nuevo             = VALUES(cli_es_nuevo),
            pry_dia_del_mes          = VALUES(pry_dia_del_mes),
            pry_proyeccion_mes       = VALUES(pry_proyeccion_mes),
            pry_ritmo_pct            = VALUES(pry_ritmo_pct),
            ant_ventas_netas         = VALUES(ant_ventas_netas),
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct),
            ant_consignacion_pp      = VALUES(ant_consignacion_pp),
            ant_var_consignacion_pct = VALUES(ant_var_consignacion_pct)
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, id_cli) in sorted(resumen.keys()):
        d = resumen[(mes, id_cli)]
        row = {
            '_key':                     f'{mes}|{id_cli}',
            'mes':                      mes,
            'id_cliente':               id_cli,
            'fecha_actualizacion':      now,
            'cliente':                  d.get('cliente'),
            'ciudad':                   d.get('ciudad'),
            'departamento':             d.get('departamento'),
            'canal':                    d.get('canal'),
            'vendedor':                 d.get('vendedor'),
            'fin_ventas_brutas':        d.get('fin_ventas_brutas'),
            'fin_descuentos':           d.get('fin_descuentos'),
            'fin_pct_descuento':        d.get('fin_pct_descuento'),
            'fin_ventas_netas_sin_iva': d.get('fin_ventas_netas_sin_iva'),
            'fin_impuestos':            d.get('fin_impuestos'),
            'cto_costo_total':          d.get('cto_costo_total'),
            'cto_utilidad_bruta':       d.get('cto_utilidad_bruta'),
            'cto_margen_utilidad_pct':  d.get('cto_margen_utilidad_pct'),
            'vol_unidades_vendidas':    d.get('vol_unidades_vendidas'),
            'vol_num_facturas':         d.get('vol_num_facturas'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'top_producto_cod':         d.get('top_producto_cod'),
            'top_producto_nombre':      d.get('top_producto_nombre'),
            'top_producto_ventas':      d.get('top_producto_ventas'),
            'con_consignacion_pp':      d.get('con_consignacion_pp'),
            'cli_es_nuevo':             d.get('cli_es_nuevo', 0),
            'pry_dia_del_mes':          d.get('pry_dia_del_mes'),
            'pry_proyeccion_mes':       d.get('pry_proyeccion_mes'),
            'pry_ritmo_pct':            d.get('pry_ritmo_pct'),
            'ant_ventas_netas':         d.get('ant_ventas_netas'),
            'ant_var_ventas_pct':       d.get('ant_var_ventas_pct'),
            'ant_consignacion_pp':      d.get('ant_consignacion_pp'),
            'ant_var_consignacion_pct': d.get('ant_var_consignacion_pct'),
        }
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_cliente_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
