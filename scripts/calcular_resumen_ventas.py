#!/usr/bin/env python3
"""
calcular_resumen_ventas.py
Calcula y actualiza la tabla resumen_ventas_facturas_mes en effi_data.
Se ejecuta como paso 3 del pipeline, después de import_all.js.
"""

import sys
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
    """Convierte un valor de cursor a float."""
    return float(v) if v is not None else default

def ival(v, default=0):
    """Convierte un valor de cursor a int."""
    return int(v) if v is not None else default

# ─── Crear tabla ──────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS resumen_ventas_facturas_mes (
    mes                      VARCHAR(7)    NOT NULL PRIMARY KEY COMMENT 'YYYY-MM',
    fecha_actualizacion      DATETIME,

    -- Financiero
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM total_bruto (precio público antes de descuentos)',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuentos',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (decimal 0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal = total_bruto - descuentos, SIN IVA',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuestos (IVA — va a la DIAN, no se queda en la empresa)',
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'SUM total_neto = subtotal + IVA - retenciones (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal NCs emitidas en el mes (zeffi_notas_credito_venta_encabezados, sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - fin_devoluciones = lo que realmente se queda en la empresa',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'ventas_netas - costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'utilidad_bruta / ventas_netas (decimal 0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad en detalle',
    vol_num_facturas         INT           COMMENT 'COUNT facturas',
    vol_ticket_promedio      DECIMAL(15,2) COMMENT 'ventas_netas / num_facturas',

    -- Clientes
    cli_clientes_activos     INT           COMMENT 'Clientes distintos con factura en el mes',
    cli_clientes_nuevos      INT           COMMENT 'Clientes cuya primera factura es de este mes',
    cli_vtas_por_cliente     DECIMAL(15,2) COMMENT 'ventas_netas / clientes_activos',

    -- Cartera
    car_saldo                DECIMAL(15,2) COMMENT 'SUM pdte_de_cobro (saldo pendiente)',

    -- Catálogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas vendidas (cod_articulo)',
    cat_vtas_por_referencia  DECIMAL(15,2) COMMENT 'ventas_netas / num_referencias',
    cat_num_canales          INT           COMMENT 'Canales de marketing distintos activos',

    -- Consignación
    con_consignacion_pp      DECIMAL(15,2) COMMENT 'SUM total_neto OVs creadas (excl. errores operativos ≤1 día sin keywords)',

    -- Top
    top_canal                TEXT          COMMENT 'Canal con mayores ventas (detalle)',
    top_canal_ventas         DECIMAL(15,2),
    top_cliente              TEXT          COMMENT 'Cliente con mayores ventas (encabezado)',
    top_cliente_ventas       DECIMAL(15,2),
    top_producto_cod         TEXT          COMMENT 'cod_articulo del producto top',
    top_producto_nombre      TEXT          COMMENT 'descripcion_articulo del producto top',
    top_producto_ventas      DECIMAL(15,2),

    -- Proyección
    pry_dia_del_mes          INT           COMMENT 'Día actual del mes (solo mes corriente, NULL si mes cerrado)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyección lineal al cierre del mes (solo mes corriente)',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'proyeccion_mes / ant_ventas_netas (decimal 0-1, solo mes corriente)',

    -- Año anterior (year_ant_): mismo mes, año -1
    year_ant_ventas_netas         DECIMAL(15,2) COMMENT 'Ventas netas del mismo mes, año anterior',
    year_ant_var_ventas_pct       DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs año anterior',
    year_ant_devoluciones         DECIMAL(15,2) COMMENT 'Devoluciones del mismo mes, año anterior',
    year_ant_var_devoluciones_pct DECIMAL(8,4)  COMMENT 'Variación % devoluciones vs año anterior',
    year_ant_ingresos_netos       DECIMAL(15,2) COMMENT 'Ingresos netos del mismo mes, año anterior',
    year_ant_var_ingresos_netos_pct DECIMAL(8,4) COMMENT 'Variación % ingresos netos vs año anterior',
    year_ant_ticket_promedio      DECIMAL(15,2) COMMENT 'Ticket promedio del mismo mes, año anterior',
    year_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs año anterior',
    year_ant_clientes_activos     INT           COMMENT 'Clientes activos del mismo mes, año anterior',
    year_ant_var_clientes_activos_pct DECIMAL(8,4) COMMENT 'Variación % clientes activos vs año anterior',
    year_ant_clientes_nuevos      INT           COMMENT 'Clientes nuevos del mismo mes, año anterior',
    year_ant_var_clientes_nuevos_pct DECIMAL(8,4) COMMENT 'Variación % clientes nuevos vs año anterior',
    year_ant_consignacion_pp      DECIMAL(15,2) COMMENT 'Consignación PP del mismo mes, año anterior',
    year_ant_var_consignacion_pct DECIMAL(8,4)  COMMENT 'Variación % consignación vs año anterior',
    year_ant_costo_total          DECIMAL(15,2) COMMENT 'Costo total del mismo mes, año anterior',
    year_ant_var_costo_total_pct  DECIMAL(8,4)  COMMENT 'Variación % costo total vs año anterior',
    year_ant_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'Margen utilidad del mismo mes, año anterior',
    year_ant_var_margen_pct       DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs año anterior',

    -- Mes anterior (mes_ant_): mes inmediatamente anterior
    mes_ant_ventas_netas          DECIMAL(15,2) COMMENT 'Ventas netas del mes inmediatamente anterior',
    mes_ant_var_ventas_pct        DECIMAL(8,4)  COMMENT 'Variación % ventas netas vs mes anterior',
    mes_ant_devoluciones          DECIMAL(15,2) COMMENT 'Devoluciones del mes anterior',
    mes_ant_var_devoluciones_pct  DECIMAL(8,4)  COMMENT 'Variación % devoluciones vs mes anterior',
    mes_ant_ingresos_netos        DECIMAL(15,2) COMMENT 'Ingresos netos del mes anterior',
    mes_ant_var_ingresos_netos_pct DECIMAL(8,4) COMMENT 'Variación % ingresos netos vs mes anterior',
    mes_ant_ticket_promedio       DECIMAL(15,2) COMMENT 'Ticket promedio del mes anterior',
    mes_ant_var_ticket_promedio_pct DECIMAL(8,4) COMMENT 'Variación % ticket promedio vs mes anterior',
    mes_ant_clientes_activos      INT           COMMENT 'Clientes activos del mes anterior',
    mes_ant_var_clientes_activos_pct DECIMAL(8,4) COMMENT 'Variación % clientes activos vs mes anterior',
    mes_ant_clientes_nuevos       INT           COMMENT 'Clientes nuevos del mes anterior',
    mes_ant_var_clientes_nuevos_pct DECIMAL(8,4) COMMENT 'Variación % clientes nuevos vs mes anterior',
    mes_ant_consignacion_pp       DECIMAL(15,2) COMMENT 'Consignación PP del mes anterior',
    mes_ant_var_consignacion_pct  DECIMAL(8,4)  COMMENT 'Variación % consignación vs mes anterior',
    mes_ant_costo_total           DECIMAL(15,2) COMMENT 'Costo total del mes anterior',
    mes_ant_var_costo_total_pct   DECIMAL(8,4)  COMMENT 'Variación % costo total vs mes anterior',
    mes_ant_margen_utilidad_pct   DECIMAL(8,4)  COMMENT 'Margen utilidad del mes anterior',
    mes_ant_var_margen_pct        DECIMAL(8,4)  COMMENT 'Diferencia en pp del margen vs mes anterior'

) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    # Migración: renombrar ant_* → year_ant_* y agregar columnas nuevas
    migration_cols = [
        # Renombrar viejas ant_* si existen
        "DROP COLUMN IF EXISTS ant_ventas_netas",
        "DROP COLUMN IF EXISTS ant_var_ventas_pct",
        "DROP COLUMN IF EXISTS ant_consignacion_pp",
        "DROP COLUMN IF EXISTS ant_var_consignacion_pct",
        # Asegurar columnas que se agregaron después del DDL original
        "ADD COLUMN IF NOT EXISTS fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal' AFTER fin_pct_descuento",
        "ADD COLUMN IF NOT EXISTS fin_ingresos_netos DECIMAL(15,2) COMMENT 'ventas_netas_sin_iva - devoluciones' AFTER fin_devoluciones",
        # year_ant_*
        "ADD COLUMN IF NOT EXISTS year_ant_ventas_netas DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ventas_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_devoluciones DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_devoluciones_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS year_ant_ingresos_netos DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS year_ant_var_ingresos_netos_pct DECIMAL(8,4)",
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
        "ADD COLUMN IF NOT EXISTS mes_ant_devoluciones DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_devoluciones_pct DECIMAL(8,4)",
        "ADD COLUMN IF NOT EXISTS mes_ant_ingresos_netos DECIMAL(15,2)",
        "ADD COLUMN IF NOT EXISTS mes_ant_var_ingresos_netos_pct DECIMAL(8,4)",
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
            cursor.execute(f"ALTER TABLE resumen_ventas_facturas_mes {col_sql}")
        except Exception:
            pass  # columna ya existe o ya fue eliminada
    conn.commit()

    resumen = {}   # mes (str 'YYYY-MM') → dict de campos

    # ── 1. Encabezados: financiero, costo, volumen de facturas, cartera ──────
    # subtotal = total_bruto - descuentos, sin IVA → base para fin_ventas_netas_sin_iva
    # devoluciones_vigentes ya NO se usa aquí (ver query de NCs más abajo)

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m')    AS mes,
            SUM({cn('total_bruto')})                   AS fin_ventas_brutas,
            SUM({cn('descuentos')})                    AS fin_descuentos,
            SUM({cn('subtotal')})                      AS fin_subtotal,
            SUM({cn('impuestos')})                     AS fin_impuestos,
            SUM({cn('total_neto')})                    AS fin_ventas_netas,
            SUM({cn('costo_manual')})                  AS cto_costo_total,
            SUM({cn('pdte_de_cobro')})                 AS car_saldo,
            COUNT(*)                                   AS vol_num_facturas,
            COUNT(DISTINCT id_cliente)                 AS cli_clientes_activos
        FROM zeffi_facturas_venta_encabezados
        GROUP BY mes
        ORDER BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if not mes:
            continue
        resumen[mes] = {
            'fin_ventas_brutas':    fval(row['fin_ventas_brutas']),
            'fin_descuentos':       fval(row['fin_descuentos']),
            'fin_subtotal':         fval(row['fin_subtotal']),   # → fin_ventas_netas_sin_iva
            'fin_impuestos':        fval(row['fin_impuestos']),
            'fin_ventas_netas':     fval(row['fin_ventas_netas']),
            'cto_costo_total':      fval(row['cto_costo_total']),
            'car_saldo':            fval(row['car_saldo']),
            'vol_num_facturas':     ival(row['vol_num_facturas']),
            'cli_clientes_activos': ival(row['cli_clientes_activos']),
        }

    # ── 2. Detalle: unidades vendidas, referencias, canales ─────────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m') AS mes,
            SUM({cn('cantidad')})                        AS vol_unidades,
            COUNT(DISTINCT cod_articulo)                 AS cat_num_referencias,
            COUNT(DISTINCT marketing_cliente)            AS cat_num_canales
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes not in resumen:
            continue
        resumen[mes]['vol_unidades_vendidas'] = fval(row['vol_unidades'])
        resumen[mes]['cat_num_referencias']   = ival(row['cat_num_referencias'])
        resumen[mes]['cat_num_canales']       = ival(row['cat_num_canales'])

    # ── 3. Clientes nuevos (primera factura histórica de cada cliente) ───────

    cursor.execute("""
        SELECT mes, COUNT(*) AS nuevos
        FROM (
            SELECT id_cliente,
                   MIN(DATE_FORMAT(fecha_de_creacion, '%Y-%m')) AS mes
            FROM zeffi_facturas_venta_encabezados
            GROUP BY id_cliente
        ) primeras
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen:
            resumen[mes]['cli_clientes_nuevos'] = ival(row['nuevos'])

    # ── 4. Devoluciones — Notas Crédito emitidas en el mes (sin IVA) ─────────
    # IMPORTANTE: se usa zeffi_notas_credito_venta_encabezados (afectan facturas).
    # NO usar zeffi_devoluciones_venta_encabezados (afectan remisiones, no facturas).
    # Se toma el campo `subtotal` (= total_bruto NC - descuentos NC), sin IVA.
    # Agrupado por fecha_de_creacion de la NC (cuándo se emitió, no cuándo fue la factura).

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            SUM({cn('subtotal')})                   AS fin_devoluciones
        FROM zeffi_notas_credito_venta_encabezados
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen:
            resumen[mes]['fin_devoluciones'] = fval(row['fin_devoluciones'])

    # ── 5. Top canal de marketing por mes ────────────────────────────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m')        AS mes,
            COALESCE(NULLIF(TRIM(marketing_cliente), ''), 'Sin canal') AS canal,
            SUM({cn('precio_neto_total')})                      AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, canal
        ORDER BY mes ASC, ventas DESC
    """)

    seen_canal = set()
    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen and mes not in seen_canal:
            seen_canal.add(mes)
            resumen[mes]['top_canal']        = row['canal']
            resumen[mes]['top_canal_ventas'] = fval(row['ventas'])

    # ── 6. Top cliente por mes ────────────────────────────────────────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            cliente,
            SUM({cn('total_neto')})                 AS ventas
        FROM zeffi_facturas_venta_encabezados
        GROUP BY mes, cliente
        ORDER BY mes ASC, ventas DESC
    """)

    seen_cli = set()
    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen and mes not in seen_cli:
            seen_cli.add(mes)
            resumen[mes]['top_cliente']        = row['cliente']
            resumen[mes]['top_cliente_ventas'] = fval(row['ventas'])

    # ── 7. Top producto por mes ───────────────────────────────────────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_creacion_factura, '%Y-%m') AS mes,
            cod_articulo,
            descripcion_articulo,
            SUM({cn('precio_neto_total')})               AS ventas
        FROM zeffi_facturas_venta_detalle
        WHERE vigencia_factura = 'Vigente'
        GROUP BY mes, cod_articulo, descripcion_articulo
        ORDER BY mes ASC, ventas DESC
    """)

    seen_prod = set()
    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen and mes not in seen_prod:
            seen_prod.add(mes)
            resumen[mes]['top_producto_cod']    = row['cod_articulo']
            resumen[mes]['top_producto_nombre'] = row['descripcion_articulo']
            resumen[mes]['top_producto_ventas'] = fval(row['ventas'])

    # ── 8. Consignación PP (OVs creadas, excluir error operativo) ────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            SUM({cn('total_neto')})                 AS con_consignacion_pp
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
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen:
            resumen[mes]['con_consignacion_pp'] = fval(row['con_consignacion_pp'])

    # ── 9. Derivados calculados en Python ─────────────────────────────────────

    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

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

    # Campos a comparar para resumen MES (más completo)
    CAMPOS_COMP_MES = [
        # (nombre_destino, campo_fuente, es_margen, var_nombre_override)
        ('ventas_netas',      'fin_ventas_netas',        False, 'ventas'),
        ('devoluciones',      'fin_devoluciones',        False),
        ('ingresos_netos',    'fin_ingresos_netos',      False),
        ('ticket_promedio',   'vol_ticket_promedio',      False),
        ('clientes_activos',  'cli_clientes_activos',     False),
        ('clientes_nuevos',   'cli_clientes_nuevos',      False),
        ('consignacion_pp',   'con_consignacion_pp',      False, 'consignacion'),
        ('costo_total',       'cto_costo_total',          False),
        ('margen_utilidad_pct','cto_margen_utilidad_pct',  True),
    ]

    # Año anterior (year_ant_) — mismo mes, año -1
    for mes in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_year   = f'{year-1:04d}-{month:02d}'
        d           = resumen[mes]
        prev        = resumen.get(prev_year)
        calc_comparativo(d, prev, 'year_ant', CAMPOS_COMP_MES)

    # Mes anterior (mes_ant_) — mes inmediatamente anterior
    for mes in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        if month == 1:
            prev_m = f'{year-1:04d}-12'
        else:
            prev_m = f'{year:04d}-{month-1:02d}'
        d    = resumen[mes]
        prev = resumen.get(prev_m)
        calc_comparativo(d, prev, 'mes_ant', CAMPOS_COMP_MES)

    # Resto de derivados
    for mes, d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas  = d.get('fin_ventas_netas', 0)
        bruto  = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)
        subtot = d.get('fin_subtotal', 0)
        devol  = d.get('fin_devoluciones', 0.0)

        # fin_pct_descuento
        d['fin_pct_descuento'] = (
            d.get('fin_descuentos', 0) / bruto if bruto else None
        )

        # fin_ventas_netas_sin_iva = subtotal de facturas
        d['fin_ventas_netas_sin_iva'] = subtot

        # fin_ingresos_netos = subtotal - NCs del mes (sin IVA)
        d['fin_ingresos_netos'] = subtot - devol

        # cto_
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas if netas else None

        # vol_ticket_promedio
        facturas = d.get('vol_num_facturas', 0)
        d['vol_ticket_promedio'] = netas / facturas if facturas else None

        # cli_vtas_por_cliente
        activos = d.get('cli_clientes_activos', 0)
        d['cli_vtas_por_cliente'] = netas / activos if activos else None

        # cat_vtas_por_referencia
        refs = d.get('cat_num_referencias', 0)
        d['cat_vtas_por_referencia'] = netas / refs if refs else None

        # pry_ — solo se calcula para el mes en curso; meses cerrados quedan NULL
        if mes == current_month:
            day_today               = today.day
            d['pry_dia_del_mes']    = day_today
            d['pry_proyeccion_mes'] = (
                netas / day_today * days_in_month if day_today else None
            )
            proy = d.get('pry_proyeccion_mes')
            ant  = d.get('year_ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 10. UPSERT ────────────────────────────────────────────────────────────

    # Construir UPSERT dinámicamente con todas las columnas del dict
    COLS_BASE = [
        'mes', 'fecha_actualizacion',
        'fin_ventas_brutas', 'fin_descuentos', 'fin_pct_descuento',
        'fin_ventas_netas_sin_iva', 'fin_impuestos', 'fin_ventas_netas',
        'fin_devoluciones', 'fin_ingresos_netos',
        'cto_costo_total', 'cto_utilidad_bruta', 'cto_margen_utilidad_pct',
        'vol_unidades_vendidas', 'vol_num_facturas', 'vol_ticket_promedio',
        'cli_clientes_activos', 'cli_clientes_nuevos', 'cli_vtas_por_cliente',
        'car_saldo',
        'cat_num_referencias', 'cat_vtas_por_referencia', 'cat_num_canales',
        'con_consignacion_pp',
        'top_canal', 'top_canal_ventas',
        'top_cliente', 'top_cliente_ventas',
        'top_producto_cod', 'top_producto_nombre', 'top_producto_ventas',
        'pry_dia_del_mes', 'pry_proyeccion_mes', 'pry_ritmo_pct',
    ]

    # Generar columnas de comparativo dinámicamente
    COMP_NAMES_MES = [
        'ventas_netas', 'var_ventas_pct',
        'devoluciones', 'var_devoluciones_pct',
        'ingresos_netos', 'var_ingresos_netos_pct',
        'ticket_promedio', 'var_ticket_promedio_pct',
        'clientes_activos', 'var_clientes_activos_pct',
        'clientes_nuevos', 'var_clientes_nuevos_pct',
        'consignacion_pp', 'var_consignacion_pct',
        'costo_total', 'var_costo_total_pct',
        'margen_utilidad_pct', 'var_margen_pct',
    ]
    COLS_COMP = []
    for prefix in ('year_ant', 'mes_ant'):
        for name in COMP_NAMES_MES:
            COLS_COMP.append(f'{prefix}_{name}')

    ALL_COLS = COLS_BASE + COLS_COMP

    col_list   = ', '.join(ALL_COLS)
    val_list   = ', '.join(f'%({c})s' for c in ALL_COLS)
    update_list = ', '.join(f'{c} = VALUES({c})' for c in ALL_COLS if c != 'mes')

    upsert_sql = f"""
        INSERT INTO resumen_ventas_facturas_mes ({col_list})
        VALUES ({val_list})
        ON DUPLICATE KEY UPDATE {update_list}
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for mes in sorted(resumen.keys()):
        d = resumen[mes]
        row = {'mes': mes, 'fecha_actualizacion': now}
        for c in ALL_COLS:
            if c not in row:
                row[c] = d.get(c)
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_mes — {len(resumen)} meses actualizados')


if __name__ == '__main__':
    main()
