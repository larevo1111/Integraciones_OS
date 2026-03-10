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
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas * 100',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal = total_bruto - descuentos, SIN IVA',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuestos (IVA — va a la DIAN, no se queda en la empresa)',
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'SUM total_neto = subtotal + IVA - retenciones (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal NCs emitidas en el mes (zeffi_notas_credito_venta_encabezados, sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - fin_devoluciones = lo que realmente se queda en la empresa',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'ventas_netas - costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'utilidad_bruta / ventas_netas * 100',

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
    pry_dia_del_mes          INT           COMMENT 'Día actual (mes corriente) o último día (meses pasados)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyección lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'proyeccion_mes / ant_ventas_netas * 100',

    -- Año anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'ventas_netas del mismo mes año anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas_netas - ant) / ant * 100',
    ant_consignacion_pp      DECIMAL(15,2) COMMENT 'consignacion_pp del mismo mes año anterior',
    ant_var_consignacion_pct DECIMAL(8,4)  COMMENT '(consignacion_pp - ant) / ant * 100'

) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    # Agregar columnas nuevas si la tabla ya existía sin ellas
    cursor.execute("""
        ALTER TABLE resumen_ventas_facturas_mes
          ADD COLUMN IF NOT EXISTS fin_ventas_netas_sin_iva DECIMAL(15,2)
              COMMENT 'SUM subtotal = total_bruto - descuentos, SIN IVA'
              AFTER fin_pct_descuento,
          ADD COLUMN IF NOT EXISTS fin_ingresos_netos DECIMAL(15,2)
              COMMENT 'fin_ventas_netas_sin_iva - fin_devoluciones = lo que se queda en la empresa'
              AFTER fin_devoluciones
    """)
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
            id_cliente,
            SUM({cn('total_neto')})                 AS ventas
        FROM zeffi_facturas_venta_encabezados
        GROUP BY mes, id_cliente
        ORDER BY mes ASC, ventas DESC
    """)

    seen_cli = set()
    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen and mes not in seen_cli:
            seen_cli.add(mes)
            resumen[mes]['top_cliente']        = row['id_cliente']
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

    # Año anterior (ant_) — requiere datos de todos los meses cargados
    for mes in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_mes    = f'{year-1:04d}-{month:02d}'
        d           = resumen[mes]
        prev        = resumen.get(prev_mes)

        d['ant_ventas_netas']    = prev['fin_ventas_netas']    if prev else None
        d['ant_consignacion_pp'] = prev.get('con_consignacion_pp') if prev else None

        if prev and prev['fin_ventas_netas']:
            d['ant_var_ventas_pct'] = (
                (d['fin_ventas_netas'] - prev['fin_ventas_netas'])
                / prev['fin_ventas_netas'] * 100
            )
        else:
            d['ant_var_ventas_pct'] = None

        prev_con = (prev or {}).get('con_consignacion_pp')
        cur_con  = d.get('con_consignacion_pp')
        if prev_con:
            d['ant_var_consignacion_pct'] = (
                ((cur_con or 0) - prev_con) / prev_con * 100
            )
        else:
            d['ant_var_consignacion_pct'] = None

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
            d.get('fin_descuentos', 0) / bruto * 100 if bruto else None
        )

        # fin_ventas_netas_sin_iva = subtotal de facturas
        d['fin_ventas_netas_sin_iva'] = subtot

        # fin_ingresos_netos = subtotal - NCs del mes (sin IVA)
        d['fin_ingresos_netos'] = subtot - devol

        # cto_
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas * 100 if netas else None

        # vol_ticket_promedio
        facturas = d.get('vol_num_facturas', 0)
        d['vol_ticket_promedio'] = netas / facturas if facturas else None

        # cli_vtas_por_cliente
        activos = d.get('cli_clientes_activos', 0)
        d['cli_vtas_por_cliente'] = netas / activos if activos else None

        # cat_vtas_por_referencia
        refs = d.get('cat_num_referencias', 0)
        d['cat_vtas_por_referencia'] = netas / refs if refs else None

        # pry_
        if mes == current_month:
            day_today              = today.day
            d['pry_dia_del_mes']   = day_today
            d['pry_proyeccion_mes'] = (
                netas / day_today * days_in_month if day_today else None
            )
        else:
            d['pry_dia_del_mes']    = days_in_month
            d['pry_proyeccion_mes'] = netas

        proy = d.get('pry_proyeccion_mes')
        ant  = d.get('ant_ventas_netas')
        d['pry_ritmo_pct'] = (
            proy / ant * 100 if (proy is not None and ant) else None
        )

    # ── 10. UPSERT ────────────────────────────────────────────────────────────

    upsert_sql = """
        INSERT INTO resumen_ventas_facturas_mes (
            mes, fecha_actualizacion,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_ventas_netas,
            fin_devoluciones, fin_ingresos_netos,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_facturas, vol_ticket_promedio,
            cli_clientes_activos, cli_clientes_nuevos, cli_vtas_por_cliente,
            car_saldo,
            cat_num_referencias, cat_vtas_por_referencia, cat_num_canales,
            con_consignacion_pp,
            top_canal, top_canal_ventas,
            top_cliente, top_cliente_ventas,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct,
            ant_consignacion_pp, ant_var_consignacion_pct
        ) VALUES (
            %(mes)s, %(fecha_actualizacion)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_ventas_netas)s,
            %(fin_devoluciones)s, %(fin_ingresos_netos)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_facturas)s, %(vol_ticket_promedio)s,
            %(cli_clientes_activos)s, %(cli_clientes_nuevos)s, %(cli_vtas_por_cliente)s,
            %(car_saldo)s,
            %(cat_num_referencias)s, %(cat_vtas_por_referencia)s, %(cat_num_canales)s,
            %(con_consignacion_pp)s,
            %(top_canal)s, %(top_canal_ventas)s,
            %(top_cliente)s, %(top_cliente_ventas)s,
            %(top_producto_cod)s, %(top_producto_nombre)s, %(top_producto_ventas)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s,
            %(ant_consignacion_pp)s, %(ant_var_consignacion_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            fin_ventas_brutas        = VALUES(fin_ventas_brutas),
            fin_descuentos           = VALUES(fin_descuentos),
            fin_pct_descuento        = VALUES(fin_pct_descuento),
            fin_ventas_netas_sin_iva = VALUES(fin_ventas_netas_sin_iva),
            fin_impuestos            = VALUES(fin_impuestos),
            fin_ventas_netas         = VALUES(fin_ventas_netas),
            fin_devoluciones         = VALUES(fin_devoluciones),
            fin_ingresos_netos       = VALUES(fin_ingresos_netos),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_unidades_vendidas    = VALUES(vol_unidades_vendidas),
            vol_num_facturas         = VALUES(vol_num_facturas),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cli_clientes_activos     = VALUES(cli_clientes_activos),
            cli_clientes_nuevos      = VALUES(cli_clientes_nuevos),
            cli_vtas_por_cliente     = VALUES(cli_vtas_por_cliente),
            car_saldo                = VALUES(car_saldo),
            cat_num_referencias      = VALUES(cat_num_referencias),
            cat_vtas_por_referencia  = VALUES(cat_vtas_por_referencia),
            cat_num_canales          = VALUES(cat_num_canales),
            con_consignacion_pp      = VALUES(con_consignacion_pp),
            top_canal                = VALUES(top_canal),
            top_canal_ventas         = VALUES(top_canal_ventas),
            top_cliente              = VALUES(top_cliente),
            top_cliente_ventas       = VALUES(top_cliente_ventas),
            top_producto_cod         = VALUES(top_producto_cod),
            top_producto_nombre      = VALUES(top_producto_nombre),
            top_producto_ventas      = VALUES(top_producto_ventas),
            pry_dia_del_mes          = VALUES(pry_dia_del_mes),
            pry_proyeccion_mes       = VALUES(pry_proyeccion_mes),
            pry_ritmo_pct            = VALUES(pry_ritmo_pct),
            ant_ventas_netas         = VALUES(ant_ventas_netas),
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct),
            ant_consignacion_pp      = VALUES(ant_consignacion_pp),
            ant_var_consignacion_pct = VALUES(ant_var_consignacion_pct)
    """

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for mes in sorted(resumen.keys()):
        d = resumen[mes]
        row = {
            'mes':                      mes,
            'fecha_actualizacion':      now,
            'fin_ventas_brutas':        d.get('fin_ventas_brutas'),
            'fin_descuentos':           d.get('fin_descuentos'),
            'fin_pct_descuento':        d.get('fin_pct_descuento'),
            'fin_ventas_netas_sin_iva': d.get('fin_ventas_netas_sin_iva'),
            'fin_impuestos':            d.get('fin_impuestos'),
            'fin_ventas_netas':         d.get('fin_ventas_netas'),
            'fin_devoluciones':         d.get('fin_devoluciones'),
            'fin_ingresos_netos':       d.get('fin_ingresos_netos'),
            'cto_costo_total':          d.get('cto_costo_total'),
            'cto_utilidad_bruta':       d.get('cto_utilidad_bruta'),
            'cto_margen_utilidad_pct':  d.get('cto_margen_utilidad_pct'),
            'vol_unidades_vendidas':    d.get('vol_unidades_vendidas'),
            'vol_num_facturas':         d.get('vol_num_facturas'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cli_clientes_activos':     d.get('cli_clientes_activos'),
            'cli_clientes_nuevos':      d.get('cli_clientes_nuevos'),
            'cli_vtas_por_cliente':     d.get('cli_vtas_por_cliente'),
            'car_saldo':                d.get('car_saldo'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'cat_vtas_por_referencia':  d.get('cat_vtas_por_referencia'),
            'cat_num_canales':          d.get('cat_num_canales'),
            'con_consignacion_pp':      d.get('con_consignacion_pp'),
            'top_canal':                d.get('top_canal'),
            'top_canal_ventas':         d.get('top_canal_ventas'),
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
            'ant_consignacion_pp':      d.get('ant_consignacion_pp'),
            'ant_var_consignacion_pct': d.get('ant_var_consignacion_pct'),
        }
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_facturas_mes — {len(resumen)} meses actualizados')


if __name__ == '__main__':
    main()
