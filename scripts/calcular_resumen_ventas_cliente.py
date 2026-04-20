#!/usr/bin/env python3
"""
calcular_resumen_ventas_cliente.py
Calcula y actualiza resumen_ventas_facturas_cliente_mes en effi_data.
PK: (mes, id_cliente) — ventas agrupadas por cliente y mes.
Se ejecuta como paso 3c del pipeline, después de calcular_resumen_ventas_canal.py.
"""

import os, sys
import datetime
from calendar import monthrange
import mysql.connector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local
DB = dict(**cfg_local(), database='effi_data')

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
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva + impuestos (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal NCs del cliente-mes (sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva - devoluciones',

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

    -- Año anterior (year_ant_): mismo cliente-mes, año -1
    year_ant_ventas_netas         DECIMAL(15,2) COMMENT 'Ventas netas del mismo cliente-mes, año anterior',
    year_ant_var_ventas_pct       DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs año anterior',
    year_ant_ticket_promedio      DECIMAL(15,2) COMMENT 'Ticket promedio del mismo cliente-mes, año anterior',
    year_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs año anterior',
    year_ant_consignacion_pp      DECIMAL(15,2) COMMENT 'Consignación PP del mismo cliente-mes, año anterior',
    year_ant_var_consignacion_pct DECIMAL(8,4)  COMMENT 'Variación % consignación vs año anterior',
    year_ant_costo_total          DECIMAL(15,2) COMMENT 'Costo total del mismo cliente-mes, año anterior',
    year_ant_var_costo_total_pct  DECIMAL(8,4)  COMMENT 'Variación % costo total vs año anterior',
    year_ant_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo cliente-mes, año anterior',
    year_ant_var_margen_pct       DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs año anterior',

    -- Mes anterior (mes_ant_): mismo cliente, mes inmediatamente anterior
    mes_ant_ventas_netas          DECIMAL(15,2) COMMENT 'Ventas netas del mismo cliente, mes anterior',
    mes_ant_var_ventas_pct        DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs mes anterior',
    mes_ant_ticket_promedio       DECIMAL(15,2) COMMENT 'Ticket promedio del mismo cliente, mes anterior',
    mes_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs mes anterior',
    mes_ant_consignacion_pp       DECIMAL(15,2) COMMENT 'Consignación PP del mismo cliente, mes anterior',
    mes_ant_var_consignacion_pct  DECIMAL(8,4)  COMMENT 'Variación % consignación vs mes anterior',
    mes_ant_costo_total           DECIMAL(15,2) COMMENT 'Costo total del mismo cliente, mes anterior',
    mes_ant_var_costo_total_pct   DECIMAL(8,4)  COMMENT 'Variación % costo total vs mes anterior',
    mes_ant_margen_utilidad_pct   DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo cliente, mes anterior',
    mes_ant_var_margen_pct        DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs mes anterior',

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
    # Migración: eliminar viejas ant_* y agregar year_ant_* + mes_ant_*
    migration_cols = [
        "DROP COLUMN IF EXISTS ant_ventas_netas",
        "DROP COLUMN IF EXISTS ant_var_ventas_pct",
        "DROP COLUMN IF EXISTS ant_consignacion_pp",
        "DROP COLUMN IF EXISTS ant_var_consignacion_pct",
        # fin_ventas_netas, fin_devoluciones, fin_ingresos_netos
        "ADD COLUMN IF NOT EXISTS fin_ventas_netas DECIMAL(15,2) AFTER fin_impuestos",
        "ADD COLUMN IF NOT EXISTS fin_devoluciones DECIMAL(15,2) AFTER fin_ventas_netas",
        "ADD COLUMN IF NOT EXISTS fin_ingresos_netos DECIMAL(15,2) AFTER fin_devoluciones",
        # year_ant_*
        "ADD COLUMN IF NOT EXISTS year_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_ticket_promedio DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ticket_promedio_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_consignacion_pp DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_consignacion_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_costo_total DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_costo_total_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_margen_utilidad_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_margen_pct DECIMAL(8,4)",
        # mes_ant_*
        "ADD COLUMN IF NOT EXISTS mes_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_ticket_promedio DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_ticket_promedio_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_consignacion_pp DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_consignacion_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_costo_total DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_costo_total_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_margen_utilidad_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_margen_pct DECIMAL(8,4)",
    ]
    for col_sql in migration_cols:
        try:
            cursor.execute(f"ALTER TABLE resumen_ventas_facturas_cliente_mes {col_sql}")
        except Exception:
            pass
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

    # ── 4b. Devoluciones (NCs) por cliente ──────────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            id_cliente,
            SUM({cn('subtotal')})                    AS devolucion
        FROM zeffi_notas_credito_venta_encabezados
        WHERE (fecha_de_anulacion IS NULL OR TRIM(fecha_de_anulacion) = '')
        GROUP BY mes, id_cliente
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['id_cliente'])
        if key in resumen:
            resumen[key]['fin_devoluciones'] = fval(row['devolucion'])

    # ── 5. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

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

    # Campos a comparar para resumen CLIENTE (sin devoluciones ni ingresos_netos)
    CAMPOS_COMP_CLIENTE = [
        # (nombre_destino, campo_fuente, es_margen, var_nombre_override)
        ('ventas_netas',       'fin_ventas_netas_sin_iva', False, 'ventas'),
        ('ticket_promedio',    'vol_ticket_promedio',      False),
        ('consignacion_pp',    'con_consignacion_pp',      False, 'consignacion'),
        ('costo_total',        'cto_costo_total',          False),
        ('margen_utilidad_pct','cto_margen_utilidad_pct',   True),
    ]

    # Año anterior (year_ant_) — mismo cliente-mes, año -1
    for (mes, id_cli) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_year_mes = f'{year-1:04d}-{month:02d}'
        d    = resumen[(mes, id_cli)]
        prev = resumen.get((prev_year_mes, id_cli))
        calc_comparativo(d, prev, 'year_ant', CAMPOS_COMP_CLIENTE)

    # Mes anterior (mes_ant_) — mes inmediatamente anterior
    for (mes, id_cli) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        if month == 1:
            prev_month = f'{year-1:04d}-12'
        else:
            prev_month = f'{year:04d}-{month-1:02d}'
        d    = resumen[(mes, id_cli)]
        prev = resumen.get((prev_month, id_cli))
        calc_comparativo(d, prev, 'mes_ant', CAMPOS_COMP_CLIENTE)

    # Resto de derivados
    for (mes, id_cli), d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)

        devol  = d.get('fin_devoluciones', 0.0)
        impues = d.get('fin_impuestos', 0)
        d['fin_ventas_netas']        = netas + impues
        d['fin_devoluciones']        = devol
        d['fin_ingresos_netos']      = netas - devol
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
            ant  = d.get('year_ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 6. UPSERT ─────────────────────────────────────────────────────────────

    COLS_BASE = [
        '_key', 'mes', 'id_cliente', 'fecha_actualizacion',
        'cliente', 'ciudad', 'departamento', 'canal', 'vendedor',
        'fin_ventas_brutas', 'fin_descuentos', 'fin_pct_descuento',
        'fin_ventas_netas_sin_iva', 'fin_impuestos',
        'fin_ventas_netas', 'fin_devoluciones', 'fin_ingresos_netos',
        'cto_costo_total', 'cto_utilidad_bruta', 'cto_margen_utilidad_pct',
        'vol_unidades_vendidas', 'vol_num_facturas', 'vol_ticket_promedio',
        'cat_num_referencias',
        'top_producto_cod', 'top_producto_nombre', 'top_producto_ventas',
        'con_consignacion_pp',
        'cli_es_nuevo',
        'pry_dia_del_mes', 'pry_proyeccion_mes', 'pry_ritmo_pct',
    ]

    # Generar columnas de comparativo dinámicamente
    COMP_NAMES_CLIENTE = [
        'ventas_netas', 'var_ventas_pct',
        'ticket_promedio', 'var_ticket_promedio_pct',
        'consignacion_pp', 'var_consignacion_pct',
        'costo_total', 'var_costo_total_pct',
        'margen_utilidad_pct', 'var_margen_pct',
    ]
    COLS_COMP = []
    for prefix in ('year_ant', 'mes_ant'):
        for name in COMP_NAMES_CLIENTE:
            COLS_COMP.append(f'{prefix}_{name}')

    ALL_COLS = COLS_BASE + COLS_COMP

    col_list    = ', '.join(ALL_COLS)
    val_list    = ', '.join(f'%({c})s' for c in ALL_COLS)
    update_list = ', '.join(f'{c} = VALUES({c})' for c in ALL_COLS if c != '_key')

    upsert_sql = f"""
        INSERT INTO resumen_ventas_facturas_cliente_mes ({col_list})
        VALUES ({val_list})
        ON DUPLICATE KEY UPDATE {update_list}
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, id_cli) in sorted(resumen.keys()):
        d = resumen[(mes, id_cli)]
        row = {
            '_key':                f'{mes}|{id_cli}',
            'mes':                 mes,
            'id_cliente':          id_cli,
            'fecha_actualizacion': now,
        }
        for c in ALL_COLS:
            if c not in row:
                row[c] = d.get(c)
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_cliente_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
