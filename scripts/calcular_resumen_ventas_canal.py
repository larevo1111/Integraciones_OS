#!/usr/bin/env python3
"""
calcular_resumen_ventas_canal.py
Calcula y actualiza resumen_ventas_facturas_canal_mes en effi_data.
PK: (mes, canal) — ventas agrupadas por canal de marketing y mes.
Se ejecuta como paso 3b del pipeline, después de calcular_resumen_ventas.py.
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
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva + impuestos (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal NCs del canal-mes (sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva - devoluciones',
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
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'pry_proyeccion_mes / year_ant_ventas_netas (decimal 0-1)',

    -- Consignaciones (OVs atribuidas via id_cliente → canal historico)
    con_consignacion_pp      DECIMAL(15,2) COMMENT 'SUM total_neto OVs atribuidas al canal via id_cliente',

    -- Año anterior (year_ant_): mismo mes, año -1
    year_ant_ventas_netas         DECIMAL(15,2) COMMENT 'Ventas netas del mismo mes y canal, año anterior',
    year_ant_var_ventas_pct       DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs año anterior',
    year_ant_ticket_promedio      DECIMAL(15,2) COMMENT 'Ticket promedio del mismo mes y canal, año anterior',
    year_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs año anterior',
    year_ant_clientes_activos     INT           COMMENT 'Clientes activos del mismo mes y canal, año anterior',
    year_ant_var_clientes_activos_pct DECIMAL(8,4) COMMENT 'Variación % clientes activos vs año anterior',
    year_ant_clientes_nuevos      INT           COMMENT 'Clientes nuevos del mismo mes y canal, año anterior',
    year_ant_var_clientes_nuevos_pct DECIMAL(8,4) COMMENT 'Variación % clientes nuevos vs año anterior',
    year_ant_consignacion_pp      DECIMAL(15,2) COMMENT 'Consignación PP del mismo mes y canal, año anterior',
    year_ant_var_consignacion_pct DECIMAL(8,4)  COMMENT 'Variación % consignación vs año anterior',
    year_ant_costo_total          DECIMAL(15,2) COMMENT 'Costo total del mismo mes y canal, año anterior',
    year_ant_var_costo_total_pct  DECIMAL(8,4)  COMMENT 'Variación % costo total vs año anterior',
    year_ant_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo mes y canal, año anterior',
    year_ant_var_margen_pct       DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs año anterior',

    -- Mes anterior (mes_ant_): mes inmediatamente anterior
    mes_ant_ventas_netas          DECIMAL(15,2) COMMENT 'Ventas netas del mes anterior para este canal',
    mes_ant_var_ventas_pct        DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs mes anterior',
    mes_ant_ticket_promedio       DECIMAL(15,2) COMMENT 'Ticket promedio del mes anterior para este canal',
    mes_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs mes anterior',
    mes_ant_clientes_activos      INT           COMMENT 'Clientes activos del mes anterior para este canal',
    mes_ant_var_clientes_activos_pct DECIMAL(8,4) COMMENT 'Variación % clientes activos vs mes anterior',
    mes_ant_clientes_nuevos       INT           COMMENT 'Clientes nuevos del mes anterior para este canal',
    mes_ant_var_clientes_nuevos_pct DECIMAL(8,4) COMMENT 'Variación % clientes nuevos vs mes anterior',
    mes_ant_consignacion_pp       DECIMAL(15,2) COMMENT 'Consignación PP del mes anterior para este canal',
    mes_ant_var_consignacion_pct  DECIMAL(8,4)  COMMENT 'Variación % consignación vs mes anterior',
    mes_ant_costo_total           DECIMAL(15,2) COMMENT 'Costo total del mes anterior para este canal',
    mes_ant_var_costo_total_pct   DECIMAL(8,4)  COMMENT 'Variación % costo total vs mes anterior',
    mes_ant_margen_utilidad_pct   DECIMAL(8,4)  COMMENT 'Margen utilidad del mes anterior para este canal',
    mes_ant_var_margen_pct        DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs mes anterior',

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, canal)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_canal (mes, canal)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_canal.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    # Migración: eliminar viejas ant_* y agregar columnas nuevas
    migration_cols = [
        # Eliminar viejas ant_*
        "DROP COLUMN IF EXISTS ant_ventas_netas",
        "DROP COLUMN IF EXISTS ant_var_ventas_pct",
        "DROP COLUMN IF EXISTS ant_consignacion_pp",
        "DROP COLUMN IF EXISTS ant_var_consignacion_pct",
        # Asegurar columnas base que se agregaron después del DDL original
        "ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes",
        "ADD COLUMN IF NOT EXISTS fin_ventas_netas DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva + impuestos' AFTER fin_impuestos",
        "ADD COLUMN IF NOT EXISTS fin_devoluciones DECIMAL(15,2) COMMENT 'SUM subtotal NCs del canal-mes' AFTER fin_ventas_netas",
        "ADD COLUMN IF NOT EXISTS fin_ingresos_netos DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva - devoluciones' AFTER fin_devoluciones",
        "ADD COLUMN IF NOT EXISTS con_consignacion_pp DECIMAL(15,2) COMMENT 'SUM total_neto OVs atribuidas al canal via id_cliente' AFTER fin_pct_del_mes",
        # year_ant_*
        "ADD COLUMN IF NOT EXISTS year_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_ticket_promedio DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ticket_promedio_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_clientes_activos INT",
        "ADD COLUMN IF NOT EXISTS year_ant_var_clientes_activos_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_clientes_nuevos INT",
        "ADD COLUMN IF NOT EXISTS year_ant_var_clientes_nuevos_pct DECIMAL(8,4)",
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
        "ADD COLUMN IF NOT EXISTS mes_ant_clientes_activos INT",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_clientes_activos_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_clientes_nuevos INT",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_clientes_nuevos_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_consignacion_pp DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_consignacion_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_costo_total DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_costo_total_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_margen_utilidad_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_margen_pct DECIMAL(8,4)",
    ]
    for col_sql in migration_cols:
        try:
            cursor.execute(f"ALTER TABLE resumen_ventas_facturas_canal_mes {col_sql}")
        except Exception:
            pass  # columna ya existe o ya fue eliminada
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

    # ── 5. Mapping id_cliente → canal histórico (canal más frecuente por cliente) ─
    cursor.execute("""
        SELECT id_cliente, canal_principal
        FROM (
            SELECT id_cliente,
                   COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal') AS canal_principal,
                   ROW_NUMBER() OVER (
                       PARTITION BY id_cliente
                       ORDER BY COUNT(*) DESC
                   ) AS rn
            FROM zeffi_facturas_venta_detalle
            WHERE vigencia_factura = 'Vigente'
            GROUP BY id_cliente, COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal')
        ) t WHERE rn = 1
    """)
    canal_por_cliente = {row['id_cliente']: row['canal_principal'] for row in cursor.fetchall()}

    # ── 6. Consignaciones OV por (mes, id_cliente) → atribuir a canal ─────────
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

    con_por_canal = {}  # (mes, canal) → suma consignaciones
    for row in cursor.fetchall():
        mes_ov   = row['mes']
        if not mes_ov:
            continue
        canal_ov = canal_por_cliente.get(row['id_cliente'], 'Sin canal')
        key      = (mes_ov, canal_ov)
        con_por_canal[key] = con_por_canal.get(key, 0.0) + fval(row['con_pp'])

    # Combinar consignaciones con resumen — crear key si canal no tiene facturas ese mes
    for (mes_ov, canal_ov), con_val in con_por_canal.items():
        if (mes_ov, canal_ov) not in resumen:
            resumen[(mes_ov, canal_ov)] = {}
        resumen[(mes_ov, canal_ov)]['con_consignacion_pp'] = con_val

    # ── 6b. Devoluciones (NCs) por canal ────────────────────────────────────────
    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            id_cliente,
            SUM({cn('subtotal')})                    AS devolucion
        FROM zeffi_notas_credito_venta_encabezados
        WHERE (fecha_de_anulacion IS NULL OR TRIM(fecha_de_anulacion) = '')
        GROUP BY mes, id_cliente
    """)

    dev_por_canal = {}  # (mes, canal) → suma devoluciones
    for row in cursor.fetchall():
        mes_nc = row['mes']
        if not mes_nc:
            continue
        canal_nc = canal_por_cliente.get(row['id_cliente'], 'Sin canal')
        key = (mes_nc, canal_nc)
        dev_por_canal[key] = dev_por_canal.get(key, 0.0) + fval(row['devolucion'])

    for key, dev_val in dev_por_canal.items():
        if key in resumen:
            resumen[key]['fin_devoluciones'] = dev_val

    # ── 7. Derivados calculados en Python ─────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Totales por mes (para fin_pct_del_mes)
    totales_mes = {}
    for (mes, canal), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    # ── Helper para calcular comparativos ──────────────────────────────────────
    def calc_comparativo(d, prev, prefix, campos):
        """Calcula columnas de comparativo (year_ant_ o mes_ant_).
        campos: lista de tuplas (nombre_destino, campo_fuente, es_margen[, var_nombre])
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
                # Margen: diferencia en puntos porcentuales
                if prev_val is not None and cur_val is not None:
                    d[col_var] = cur_val - prev_val
                else:
                    d[col_var] = None
            else:
                # Variación porcentual estándar
                if prev_val:
                    v = ((cur_val or 0) - prev_val) / prev_val
                    d[col_var] = max(-9999.9999, min(9999.9999, v))
                else:
                    d[col_var] = None

    # Campos a comparar para resumen CANAL (sin devoluciones ni ingresos_netos)
    CAMPOS_COMP_CANAL = [
        # (nombre_destino, campo_fuente, es_margen, var_nombre_override)
        ('ventas_netas',       'fin_ventas_netas_sin_iva', False, 'ventas'),
        ('ticket_promedio',    'vol_ticket_promedio',      False),
        ('clientes_activos',   'cli_clientes_activos',     False),
        ('clientes_nuevos',    'cli_clientes_nuevos',      False),
        ('consignacion_pp',    'con_consignacion_pp',      False, 'consignacion'),
        ('costo_total',        'cto_costo_total',          False),
        ('margen_utilidad_pct','cto_margen_utilidad_pct',   True),
    ]

    # Año anterior (year_ant_) — mismo mes, año -1
    for (mes, canal) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_year_mes = f'{year-1:04d}-{month:02d}'
        d    = resumen[(mes, canal)]
        prev = resumen.get((prev_year_mes, canal))
        calc_comparativo(d, prev, 'year_ant', CAMPOS_COMP_CANAL)

    # Mes anterior (mes_ant_) — mes inmediatamente anterior
    for (mes, canal) in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        if month == 1:
            prev_month = f'{year-1:04d}-12'
        else:
            prev_month = f'{year:04d}-{month-1:02d}'
        d    = resumen[(mes, canal)]
        prev = resumen.get((prev_month, canal))
        calc_comparativo(d, prev, 'mes_ant', CAMPOS_COMP_CANAL)

    # Resto de derivados
    for (mes, canal), d in resumen.items():
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
            ant  = d.get('year_ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 8. UPSERT ─────────────────────────────────────────────────────────────

    COLS_BASE = [
        '_key', 'mes', 'canal', 'fecha_actualizacion',
        'fin_ventas_brutas', 'fin_descuentos', 'fin_pct_descuento',
        'fin_ventas_netas_sin_iva', 'fin_impuestos', 'fin_ventas_netas',
        'fin_devoluciones', 'fin_ingresos_netos', 'fin_pct_del_mes',
        'cto_costo_total', 'cto_utilidad_bruta', 'cto_margen_utilidad_pct',
        'vol_unidades_vendidas', 'vol_num_facturas', 'vol_ticket_promedio',
        'cli_clientes_activos', 'cli_clientes_nuevos', 'cli_vtas_por_cliente',
        'cat_num_referencias',
        'top_cliente', 'top_cliente_ventas',
        'top_producto_cod', 'top_producto_nombre', 'top_producto_ventas',
        'pry_dia_del_mes', 'pry_proyeccion_mes', 'pry_ritmo_pct',
        'con_consignacion_pp',
    ]

    # Generar columnas de comparativo dinámicamente
    COMP_NAMES_CANAL = [
        'ventas_netas', 'var_ventas_pct',
        'ticket_promedio', 'var_ticket_promedio_pct',
        'clientes_activos', 'var_clientes_activos_pct',
        'clientes_nuevos', 'var_clientes_nuevos_pct',
        'consignacion_pp', 'var_consignacion_pct',
        'costo_total', 'var_costo_total_pct',
        'margen_utilidad_pct', 'var_margen_pct',
    ]
    COLS_COMP = []
    for prefix in ('year_ant', 'mes_ant'):
        for name in COMP_NAMES_CANAL:
            COLS_COMP.append(f'{prefix}_{name}')

    ALL_COLS = COLS_BASE + COLS_COMP

    col_list    = ', '.join(ALL_COLS)
    val_list    = ', '.join(f'%({c})s' for c in ALL_COLS)
    update_list = ', '.join(f'{c} = VALUES({c})' for c in ALL_COLS if c != '_key')

    upsert_sql = f"""
        INSERT INTO resumen_ventas_facturas_canal_mes ({col_list})
        VALUES ({val_list})
        ON DUPLICATE KEY UPDATE {update_list}
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for (mes, canal) in sorted(resumen.keys()):
        d = resumen[(mes, canal)]
        row = {
            '_key':                f'{mes}|{canal}',
            'mes':                 mes,
            'canal':               canal,
            'fecha_actualizacion': now,
        }
        for c in ALL_COLS:
            if c not in row:
                row[c] = d.get(c)
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_canal_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
