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
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva + impuestos (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal NCs del producto-mes (sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva - devoluciones',
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

    -- Año anterior (year_ant_): mismo producto-mes, año -1
    year_ant_ventas_netas         DECIMAL(15,2) COMMENT 'Ventas netas del mismo producto-mes, año anterior',
    year_ant_var_ventas_pct       DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs año anterior',
    year_ant_unidades             DECIMAL(15,2) COMMENT 'Unidades vendidas del mismo producto-mes, año anterior',
    year_ant_var_unidades_pct     DECIMAL(8,4)  COMMENT 'Variación % unidades vs año anterior',
    year_ant_costo_total          DECIMAL(15,2) COMMENT 'Costo total del mismo producto-mes, año anterior',
    year_ant_var_costo_total_pct  DECIMAL(8,4)  COMMENT 'Variación % costo total vs año anterior',
    year_ant_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo producto-mes, año anterior',
    year_ant_var_margen_pct       DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs año anterior',

    -- Mes anterior (mes_ant_): mismo producto, mes inmediatamente anterior
    mes_ant_ventas_netas          DECIMAL(15,2) COMMENT 'Ventas netas del mismo producto, mes anterior',
    mes_ant_var_ventas_pct        DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs mes anterior',
    mes_ant_unidades              DECIMAL(15,2) COMMENT 'Unidades vendidas del mismo producto, mes anterior',
    mes_ant_var_unidades_pct      DECIMAL(8,4)  COMMENT 'Variación % unidades vs mes anterior',
    mes_ant_costo_total           DECIMAL(15,2) COMMENT 'Costo total del mismo producto, mes anterior',
    mes_ant_var_costo_total_pct   DECIMAL(8,4)  COMMENT 'Variación % costo total vs mes anterior',
    mes_ant_margen_utilidad_pct   DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo producto, mes anterior',
    mes_ant_var_margen_pct        DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs mes anterior',

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, cod_articulo)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_producto (mes, cod_articulo)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_producto.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    cursor.execute("ALTER TABLE resumen_ventas_facturas_producto_mes ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes")

    # Migración: eliminar viejas ant_* y agregar year_ant_* + mes_ant_*
    migration_cols = [
        "DROP COLUMN IF EXISTS ant_ventas_netas",
        "DROP COLUMN IF EXISTS ant_var_ventas_pct",
        "DROP COLUMN IF EXISTS ant_unidades",
        "DROP COLUMN IF EXISTS ant_var_unidades_pct",
        # year_ant_*
        "ADD COLUMN IF NOT EXISTS fin_ventas_netas DECIMAL(15,2) AFTER fin_impuestos",
        "ADD COLUMN IF NOT EXISTS fin_devoluciones DECIMAL(15,2) AFTER fin_ventas_netas",
        "ADD COLUMN IF NOT EXISTS fin_ingresos_netos DECIMAL(15,2) AFTER fin_devoluciones",
        "ADD COLUMN IF NOT EXISTS year_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_unidades DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_unidades_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_costo_total DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_costo_total_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_margen_utilidad_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_margen_pct DECIMAL(8,4)",
        # mes_ant_*
        "ADD COLUMN IF NOT EXISTS mes_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_unidades DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_unidades_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_costo_total DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_costo_total_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_margen_utilidad_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_margen_pct DECIMAL(8,4)",
    ]
    for col_sql in migration_cols:
        try:
            cursor.execute(f"ALTER TABLE resumen_ventas_facturas_producto_mes {col_sql}")
        except Exception:
            pass

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

    # ── 3b. Devoluciones (NCs) por producto ─────────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_factura, '%Y-%m') AS mes,
            cod_articulo,
            SUM({cn('precio_bruto_total')} - {cn('descuento_total')}) AS devolucion
        FROM zeffi_notas_credito_venta_detalle
        WHERE (TRIM(COALESCE(vigencia, '')) = '' OR vigencia != 'Anulada')
        GROUP BY mes, cod_articulo
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['cod_articulo'])
        if key in resumen:
            resumen[key]['fin_devoluciones'] = fval(row['devolucion'])

    # ── 4. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Totales por mes (para fin_pct_del_mes)
    totales_mes = {}
    for (mes, cod), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    # ── Helper para calcular comparativos ──────────────────────────────────────
    def calc_comparativo(d, prev, prefix, campos):
        """Calcula columnas de comparativo (year_ant_ o mes_ant_).
        campos: lista de tuplas (nombre_destino, campo_fuente, es_margen)
        """
        for item in campos:
            nombre, fuente, es_margen = item[0], item[1], item[2]
            var_nombre = item[3] if len(item) > 3 else nombre
            col_val = f'{prefix}_{nombre}'
            col_var = f'{prefix}_var_{var_nombre}_pct' if not es_margen else f'{prefix}_var_{var_nombre.replace("margen_utilidad_pct","margen")}_pct'
            prev_val = (prev or {}).get(fuente)
            cur_val  = d.get(fuente)
            d[col_val] = prev_val if prev else None
            if es_margen:
                if prev_val is not None and cur_val is not None:
                    d[col_var] = cur_val - prev_val
                else:
                    d[col_var] = None
            else:
                if prev_val:
                    v = ((cur_val or 0) - prev_val) / prev_val
                    d[col_var] = max(-9999.9999, min(9999.9999, v))
                else:
                    d[col_var] = None

    # Campos a comparar para resumen PRODUCTO (incluye unidades, sin clientes)
    CAMPOS_COMP_PRODUCTO = [
        # (nombre_destino, campo_fuente, es_margen, var_nombre_override)
        ('ventas_netas',       'fin_ventas_netas_sin_iva', False, 'ventas'),
        ('unidades',           'vol_unidades_vendidas',    False),
        ('costo_total',        'cto_costo_total',          False),
        ('margen_utilidad_pct','cto_margen_utilidad_pct',   True),
    ]

    # Año anterior (year_ant_) — mismo producto-mes, año -1
    for (mes, cod) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_year_mes = f'{year-1:04d}-{month:02d}'
        d    = resumen[(mes, cod)]
        prev = resumen.get((prev_year_mes, cod))
        calc_comparativo(d, prev, 'year_ant', CAMPOS_COMP_PRODUCTO)

    # Mes anterior (mes_ant_) — mes inmediatamente anterior
    for (mes, cod) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        if month == 1:
            prev_month = f'{year-1:04d}-12'
        else:
            prev_month = f'{year:04d}-{month-1:02d}'
        d    = resumen[(mes, cod)]
        prev = resumen.get((prev_month, cod))
        calc_comparativo(d, prev, 'mes_ant', CAMPOS_COMP_PRODUCTO)

    # Resto de derivados
    for (mes, cod), d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas     = d.get('fin_ventas_netas_sin_iva', 0)
        brutas    = d.get('fin_ventas_brutas', 0)
        costo     = d.get('cto_costo_total', 0)
        unidades  = d.get('vol_unidades_vendidas', 0)

        devol  = d.get('fin_devoluciones', 0.0)
        impues = d.get('fin_impuestos', 0)
        d['fin_ventas_netas']        = netas + impues
        d['fin_devoluciones']        = devol
        d['fin_ingresos_netos']      = netas - devol
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
            ant  = d.get('year_ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 5. UPSERT ─────────────────────────────────────────────────────────────

    COLS_BASE = [
        '_key', 'mes', 'cod_articulo', 'fecha_actualizacion',
        'nombre', 'categoria', 'marca',
        'fin_ventas_brutas', 'fin_descuentos', 'fin_pct_descuento',
        'fin_ventas_netas_sin_iva', 'fin_impuestos',
        'fin_ventas_netas', 'fin_devoluciones', 'fin_ingresos_netos',
        'fin_pct_del_mes',
        'cto_costo_total', 'cto_utilidad_bruta', 'cto_margen_utilidad_pct',
        'vol_unidades_vendidas', 'vol_num_facturas', 'vol_precio_unitario_prom',
        'cli_clientes_activos',
        'top_cliente', 'top_cliente_ventas',
        'top_canal', 'top_canal_ventas',
        'pry_dia_del_mes', 'pry_proyeccion_mes', 'pry_ritmo_pct',
    ]

    # Generar columnas de comparativo dinámicamente
    COMP_NAMES_PRODUCTO = [
        'ventas_netas', 'var_ventas_pct',
        'unidades', 'var_unidades_pct',
        'costo_total', 'var_costo_total_pct',
        'margen_utilidad_pct', 'var_margen_pct',
    ]
    COLS_COMP = []
    for prefix in ('year_ant', 'mes_ant'):
        for name in COMP_NAMES_PRODUCTO:
            COLS_COMP.append(f'{prefix}_{name}')

    ALL_COLS = COLS_BASE + COLS_COMP

    col_list    = ', '.join(ALL_COLS)
    val_list    = ', '.join(f'%({c})s' for c in ALL_COLS)
    update_list = ', '.join(f'{c} = VALUES({c})' for c in ALL_COLS if c != '_key')

    upsert_sql = f"""
        INSERT INTO resumen_ventas_facturas_producto_mes ({col_list})
        VALUES ({val_list})
        ON DUPLICATE KEY UPDATE {update_list}
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, cod) in sorted(resumen.keys()):
        d = resumen[(mes, cod)]
        row = {
            '_key':                f'{mes}|{cod}',
            'mes':                 mes,
            'cod_articulo':        cod,
            'fecha_actualizacion': now,
        }
        for c in ALL_COLS:
            if c not in row:
                row[c] = d.get(c)
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_producto_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
