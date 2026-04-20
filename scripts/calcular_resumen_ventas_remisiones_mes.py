#!/usr/bin/env python3
"""
calcular_resumen_ventas_remisiones_mes.py
Calcula y actualiza la tabla resumen_ventas_remisiones_mes en effi_data.
Paso 4a del pipeline — paralelo a resumen_ventas_facturas_mes pero para remisiones.

Incluye:
  - Estado "Pendiente de facturar": remisiones activas, aún no convertidas a factura
  - Estado "Anulado" con observacion_de_anulacion LIKE 'Remisión convertida a factura de venta%'

Excluye:
  - Estado "Anulado" verdadero (precios, errores operativos, etc.)

Notas técnicas:
  - Encabezados: formato coma decimal + punto miles → usa cn() con REPLACE
  - Detalle: números planos → usa cn_det() con CAST directo
  - fin_ventas_netas_sin_iva = subtotal (total_bruto - descuentos, sin IVA)
  - fin_ventas_netas = total_neto (incluye IVA — gotcha igual que facturas)
  - fin_devoluciones: de zeffi_devoluciones_venta_encabezados (devoluciones de remisiones)
  - rem_pendientes / rem_facturadas: conteos actuales (pueden cambiar con el tiempo)
  - Sin con_consignacion_pp (OVs no tienen relación con remisiones)
"""

import os
import sys
import datetime
from calendar import monthrange
import mysql.connector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cfg_local
DB = dict(**cfg_local(), database='effi_data')

# ─── Utilidades ───────────────────────────────────────────────────────────────

def cn(field):
    """CAST TEXT con coma decimal a DECIMAL(15,2) — para encabezados."""
    return f"CAST(REPLACE(COALESCE({field}, '0'), ',', '.') AS DECIMAL(15,2))"

def cn_det(field):
    """CAST TEXT plano a DECIMAL(15,2) — para detalle (sin formato coma)."""
    return f"CAST(NULLIF(TRIM({field}), '') AS DECIMAL(15,2))"

def fval(v, default=0.0):
    return float(v) if v is not None else default

def ival(v, default=0):
    return int(v) if v is not None else default

# ─── Filtros SQL ──────────────────────────────────────────────────────────────

# Para queries sobre solo encabezados
FILTRO_ENC = """(
    estado_remision = 'Pendiente de facturar'
    OR observacion_de_anulacion LIKE 'Remisi\u00f3n convertida a factura de venta%'
)"""

# Para queries con JOIN encabezados (e) + detalle (d)
FILTRO_ENC_JOIN = """(
    e.estado_remision = 'Pendiente de facturar'
    OR e.observacion_de_anulacion LIKE 'Remisi\u00f3n convertida a factura de venta%'
)"""

# ─── DDL ──────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS resumen_ventas_remisiones_mes (
    mes                      VARCHAR(7)    NOT NULL PRIMARY KEY COMMENT 'YYYY-MM',
    fecha_actualizacion      DATETIME,

    -- Financiero
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM total_bruto (precio público antes de descuentos)',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuentos',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (decimal 0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal = total_bruto - descuentos, SIN IVA',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuestos (IVA)',
    fin_ventas_netas         DECIMAL(15,2) COMMENT 'SUM total_neto (incluye IVA)',
    fin_devoluciones         DECIMAL(15,2) COMMENT 'SUM subtotal zeffi_devoluciones_venta emitidas en el mes (sin IVA)',
    fin_ingresos_netos       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - fin_devoluciones',

    -- Costo y utilidad
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total (detalle)',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'fin_ventas_netas - cto_costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'utilidad_bruta / fin_ventas_netas (decimal 0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad (detalle)',
    vol_num_remisiones       INT           COMMENT 'COUNT remisiones válidas (encabezados)',
    vol_ticket_promedio      DECIMAL(15,2) COMMENT 'fin_ventas_netas / vol_num_remisiones',

    -- Clientes
    cli_clientes_activos     INT           COMMENT 'Clientes distintos con remisión en el mes',
    cli_clientes_nuevos      INT           COMMENT 'Clientes cuya primera remisión histórica es de este mes',
    cli_vtas_por_cliente     DECIMAL(15,2) COMMENT 'fin_ventas_netas / cli_clientes_activos',

    -- Cartera
    car_saldo                DECIMAL(15,2) COMMENT 'SUM pdte_de_cobro (saldo pendiente de cobro)',

    -- Catálogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas (cod_articulo)',
    cat_vtas_por_referencia  DECIMAL(15,2) COMMENT 'fin_ventas_netas / cat_num_referencias',
    cat_num_canales          INT           COMMENT 'Canales de marketing distintos activos',

    -- Remisiones — estado actual
    rem_pendientes           INT           COMMENT 'Remisiones en estado Pendiente de facturar (actuales)',
    rem_facturadas           INT           COMMENT 'Remisiones convertidas a factura (actuales)',
    rem_pct_facturadas       DECIMAL(8,4)  COMMENT 'rem_facturadas / total_remisiones (decimal 0-1)',

    -- Top
    top_canal                TEXT          COMMENT 'Canal con mayores ventas (tipo_de_marketing_cliente detalle)',
    top_canal_ventas         DECIMAL(15,2),
    top_cliente              TEXT          COMMENT 'Cliente con mayores ventas (encabezado)',
    top_cliente_ventas       DECIMAL(15,2),
    top_producto_cod         TEXT          COMMENT 'cod_articulo del producto top',
    top_producto_nombre      TEXT          COMMENT 'descripcion_articulo del producto top',
    top_producto_ventas      DECIMAL(15,2),

    -- Proyección (solo mes corriente)
    pry_dia_del_mes          INT           COMMENT 'Día actual del mes (NULL si mes cerrado)',
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyección lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'proyeccion_mes / ant_ventas_netas (decimal 0-1)',

    -- Año anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas del mismo mes año anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas_netas - ant) / ant (decimal, no pct)'

) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_remisiones_mes.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)

    cursor.execute(DDL)
    conn.commit()

    resumen = {}  # mes (str 'YYYY-MM') → dict de campos

    # ── 1. Encabezados: financiero, volumen, clientes, cartera, rem_estados ──

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m')                       AS mes,
            SUM({cn('total_bruto')})                                      AS fin_ventas_brutas,
            SUM({cn('descuentos')})                                       AS fin_descuentos,
            SUM({cn('subtotal')})                                         AS fin_subtotal,
            SUM({cn('impuestos')})                                        AS fin_impuestos,
            SUM({cn('total_neto')})                                       AS fin_ventas_netas,
            SUM({cn('pdte_de_cobro')})                                    AS car_saldo,
            COUNT(*)                                                       AS vol_num_remisiones,
            COUNT(DISTINCT id_cliente)                                    AS cli_clientes_activos,
            SUM(CASE WHEN estado_remision = 'Pendiente de facturar'
                     THEN 1 ELSE 0 END)                                   AS rem_pendientes,
            SUM(CASE WHEN estado_remision = 'Anulado'
                     THEN 1 ELSE 0 END)                                   AS rem_facturadas
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
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
            'fin_subtotal':         fval(row['fin_subtotal']),
            'fin_impuestos':        fval(row['fin_impuestos']),
            'fin_ventas_netas':     fval(row['fin_ventas_netas']),
            'car_saldo':            fval(row['car_saldo']),
            'vol_num_remisiones':   ival(row['vol_num_remisiones']),
            'cli_clientes_activos': ival(row['cli_clientes_activos']),
            'rem_pendientes':       ival(row['rem_pendientes']),
            'rem_facturadas':       ival(row['rem_facturadas']),
        }

    # ── 2. Detalle (JOIN encabezados): unidades, costo, referencias, canales ─

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(e.fecha_de_creacion, '%Y-%m')                    AS mes,
            SUM({cn_det('d.cantidad')})                                   AS vol_unidades,
            SUM({cn_det('d.costo_manual_total')})                         AS cto_costo_total,
            COUNT(DISTINCT d.cod_articulo)                                AS cat_num_referencias,
            COUNT(DISTINCT COALESCE(
                NULLIF(TRIM(d.tipo_de_marketing_cliente), ''), 'Sin canal'
            ))                                                            AS cat_num_canales
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes not in resumen:
            continue
        resumen[mes]['vol_unidades_vendidas'] = fval(row['vol_unidades'])
        resumen[mes]['cto_costo_total']       = fval(row['cto_costo_total'])
        resumen[mes]['cat_num_referencias']   = ival(row['cat_num_referencias'])
        resumen[mes]['cat_num_canales']       = ival(row['cat_num_canales'])

    # ── 3. Clientes nuevos (primera remisión histórica de cada cliente) ──────

    cursor.execute(f"""
        SELECT mes, COUNT(*) AS nuevos
        FROM (
            SELECT id_cliente,
                   MIN(DATE_FORMAT(fecha_de_creacion, '%Y-%m')) AS mes
            FROM zeffi_remisiones_venta_encabezados
            WHERE {FILTRO_ENC}
            GROUP BY id_cliente
        ) primeras
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen:
            resumen[mes]['cli_clientes_nuevos'] = ival(row['nuevos'])

    # ── 4. Devoluciones de remisiones (zeffi_devoluciones_venta_encabezados) ─

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(fecha_de_creacion, '%Y-%m') AS mes,
            SUM({cn('subtotal')})                   AS fin_devoluciones
        FROM zeffi_devoluciones_venta_encabezados
        GROUP BY mes
    """)

    for row in cursor.fetchall():
        mes = row['mes']
        if mes in resumen:
            resumen[mes]['fin_devoluciones'] = fval(row['fin_devoluciones'])

    # ── 5. Top canal por mes ──────────────────────────────────────────────────

    cursor.execute(f"""
        SELECT
            DATE_FORMAT(e.fecha_de_creacion, '%Y-%m')                    AS mes,
            COALESCE(NULLIF(TRIM(d.tipo_de_marketing_cliente), ''),
                     'Sin canal')                                         AS canal,
            SUM({cn_det('d.precio_neto_total')})                         AS ventas
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
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
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
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
            DATE_FORMAT(e.fecha_de_creacion, '%Y-%m') AS mes,
            d.cod_articulo,
            d.descripcion_articulo,
            SUM({cn_det('d.precio_neto_total')})      AS ventas
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
        GROUP BY mes, d.cod_articulo, d.descripcion_articulo
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

    # ── 8. Derivados calculados en Python ─────────────────────────────────────

    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    # Año anterior
    for mes in sorted(resumen.keys()):
        year, month = map(int, mes.split('-'))
        prev_mes    = f'{year-1:04d}-{month:02d}'
        d           = resumen[mes]
        prev        = resumen.get(prev_mes)

        d['ant_ventas_netas'] = prev['fin_ventas_netas'] if prev else None

        if prev and prev.get('fin_ventas_netas'):
            d['ant_var_ventas_pct'] = (
                (d['fin_ventas_netas'] - prev['fin_ventas_netas'])
                / prev['fin_ventas_netas']
            )
        else:
            d['ant_var_ventas_pct'] = None

    # Resto de derivados
    for mes, d in resumen.items():
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        netas  = d.get('fin_ventas_netas', 0)
        bruto  = d.get('fin_ventas_brutas', 0)
        subtot = d.get('fin_subtotal', 0)
        costo  = d.get('cto_costo_total', 0)
        devol  = d.get('fin_devoluciones', 0.0)
        total  = d.get('vol_num_remisiones', 0)
        pend   = d.get('rem_pendientes', 0)
        fact   = d.get('rem_facturadas', 0)

        # Financiero
        d['fin_pct_descuento']        = (d.get('fin_descuentos', 0) / bruto) if bruto else None
        d['fin_ventas_netas_sin_iva'] = subtot
        d['fin_ingresos_netos']       = subtot - devol

        # Costo
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = (netas - costo) / netas if netas else None

        # Volumen
        remisiones = d.get('vol_num_remisiones', 0)
        d['vol_ticket_promedio'] = netas / remisiones if remisiones else None

        # Clientes
        activos = d.get('cli_clientes_activos', 0)
        d['cli_vtas_por_cliente'] = netas / activos if activos else None

        # Catálogo
        refs = d.get('cat_num_referencias', 0)
        d['cat_vtas_por_referencia'] = netas / refs if refs else None

        # Remisiones estado
        d['rem_pct_facturadas'] = fact / total if total else None

        # Proyección — solo mes corriente
        if mes == current_month:
            day_today               = today.day
            d['pry_dia_del_mes']    = day_today
            d['pry_proyeccion_mes'] = (netas / day_today * days_in_month) if day_today else None
            proy = d.get('pry_proyeccion_mes')
            ant  = d.get('ant_ventas_netas')
            d['pry_ritmo_pct'] = proy / ant if (proy is not None and ant) else None
        else:
            d['pry_dia_del_mes']    = None
            d['pry_proyeccion_mes'] = None
            d['pry_ritmo_pct']      = None

    # ── 9. UPSERT ─────────────────────────────────────────────────────────────

    upsert_sql = """
        INSERT INTO resumen_ventas_remisiones_mes (
            mes, fecha_actualizacion,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_ventas_netas,
            fin_devoluciones, fin_ingresos_netos,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_remisiones, vol_ticket_promedio,
            cli_clientes_activos, cli_clientes_nuevos, cli_vtas_por_cliente,
            car_saldo,
            cat_num_referencias, cat_vtas_por_referencia, cat_num_canales,
            rem_pendientes, rem_facturadas, rem_pct_facturadas,
            top_canal, top_canal_ventas,
            top_cliente, top_cliente_ventas,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct
        ) VALUES (
            %(mes)s, %(fecha_actualizacion)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_ventas_netas)s,
            %(fin_devoluciones)s, %(fin_ingresos_netos)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_remisiones)s, %(vol_ticket_promedio)s,
            %(cli_clientes_activos)s, %(cli_clientes_nuevos)s, %(cli_vtas_por_cliente)s,
            %(car_saldo)s,
            %(cat_num_referencias)s, %(cat_vtas_por_referencia)s, %(cat_num_canales)s,
            %(rem_pendientes)s, %(rem_facturadas)s, %(rem_pct_facturadas)s,
            %(top_canal)s, %(top_canal_ventas)s,
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
            fin_ventas_netas         = VALUES(fin_ventas_netas),
            fin_devoluciones         = VALUES(fin_devoluciones),
            fin_ingresos_netos       = VALUES(fin_ingresos_netos),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_unidades_vendidas    = VALUES(vol_unidades_vendidas),
            vol_num_remisiones       = VALUES(vol_num_remisiones),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cli_clientes_activos     = VALUES(cli_clientes_activos),
            cli_clientes_nuevos      = VALUES(cli_clientes_nuevos),
            cli_vtas_por_cliente     = VALUES(cli_vtas_por_cliente),
            car_saldo                = VALUES(car_saldo),
            cat_num_referencias      = VALUES(cat_num_referencias),
            cat_vtas_por_referencia  = VALUES(cat_vtas_por_referencia),
            cat_num_canales          = VALUES(cat_num_canales),
            rem_pendientes           = VALUES(rem_pendientes),
            rem_facturadas           = VALUES(rem_facturadas),
            rem_pct_facturadas       = VALUES(rem_pct_facturadas),
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
            ant_var_ventas_pct       = VALUES(ant_var_ventas_pct)
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
            'vol_num_remisiones':       d.get('vol_num_remisiones'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cli_clientes_activos':     d.get('cli_clientes_activos'),
            'cli_clientes_nuevos':      d.get('cli_clientes_nuevos'),
            'cli_vtas_por_cliente':     d.get('cli_vtas_por_cliente'),
            'car_saldo':                d.get('car_saldo'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'cat_vtas_por_referencia':  d.get('cat_vtas_por_referencia'),
            'cat_num_canales':          d.get('cat_num_canales'),
            'rem_pendientes':           d.get('rem_pendientes'),
            'rem_facturadas':           d.get('rem_facturadas'),
            'rem_pct_facturadas':       d.get('rem_pct_facturadas'),
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
        }
        cursor.execute(upsert_sql, row)

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_remisiones_mes — {len(resumen)} meses actualizados')


if __name__ == '__main__':
    main()
