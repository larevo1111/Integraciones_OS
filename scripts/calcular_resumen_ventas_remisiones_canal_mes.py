#!/usr/bin/env python3
"""
calcular_resumen_ventas_remisiones_canal_mes.py
Calcula y actualiza resumen_ventas_remisiones_canal_mes en effi_data (staging).
PK: (mes, canal) — remisiones agrupadas por canal de marketing y mes.
Paso 4b del pipeline.

Canal: tipo_de_markting del encabezado (typo de Effi — campo correcto)
Incluye: 'Pendiente de facturar' + convertidas a factura
Excluye: anuladas verdaderas
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
    """CAST TEXT con coma decimal a DECIMAL(15,2) — encabezados."""
    return f"CAST(REPLACE(COALESCE({field}, '0'), ',', '.') AS DECIMAL(15,2))"

def cn_det(field):
    """CAST TEXT plano a DECIMAL(15,2) — detalle."""
    return f"CAST(NULLIF(TRIM({field}), '') AS DECIMAL(15,2))"

def fval(v, default=0.0):
    return float(v) if v is not None else default

def ival(v, default=0):
    return int(v) if v is not None else default

def pct(v, limit=999.9999):
    """Normaliza porcentaje decimal: NULL si es None o fuera de rango DECIMAL(8,4)."""
    if v is None:
        return None
    return v if abs(v) <= limit else None

# ─── Filtros SQL ──────────────────────────────────────────────────────────────

FILTRO_ENC = """(
    estado_remision = 'Pendiente de facturar'
    OR observacion_de_anulacion LIKE 'Remisi\u00f3n convertida a factura de venta%'
)"""

FILTRO_ENC_JOIN = """(
    e.estado_remision = 'Pendiente de facturar'
    OR e.observacion_de_anulacion LIKE 'Remisi\u00f3n convertida a factura de venta%'
)"""

# ─── DDL ──────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS resumen_ventas_remisiones_canal_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    canal                    VARCHAR(255)  NOT NULL COMMENT 'tipo_de_markting del encabezado (typo de Effi)',
    fecha_actualizacion      DATETIME,

    -- Financiero (de encabezados)
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM total_bruto',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuentos',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal (total_bruto - descuentos, sin IVA)',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuestos',
    fin_pct_del_mes          DECIMAL(8,4)  COMMENT 'participacion canal en total mes (0-1)',

    -- Costo (de detalle)
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva - cto_costo_total',
    cto_margen_utilidad_pct  DECIMAL(8,4)  COMMENT 'cto_utilidad_bruta / fin_ventas_netas_sin_iva (0-1)',

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad (detalle)',
    vol_num_remisiones       INT           COMMENT 'COUNT DISTINCT id_remision',
    vol_ticket_promedio      DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / vol_num_remisiones',

    -- Clientes
    cli_clientes_activos     INT           COMMENT 'Clientes distintos con remision en el mes-canal',
    cli_clientes_nuevos      INT           COMMENT 'Clientes cuya primera remision historica es de este mes-canal',
    cli_vtas_por_cliente     DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva / cli_clientes_activos',

    -- Catalogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas (cod_articulo)',

    -- Estado de remisiones (dinamico)
    rem_pendientes           INT           COMMENT 'Remisiones aun Pendiente de facturar',
    rem_facturadas           INT           COMMENT 'Remisiones convertidas a factura',
    rem_pct_facturadas       DECIMAL(8,4)  COMMENT 'rem_facturadas / total (0-1)',

    -- Top
    top_cliente              TEXT          COMMENT 'Cliente con mas ventas en este canal-mes',
    top_cliente_ventas       DECIMAL(15,2),
    top_producto_cod         TEXT          COMMENT 'cod_articulo top',
    top_producto_nombre      TEXT,
    top_producto_ventas      DECIMAL(15,2),

    -- Proyeccion (solo mes corriente, NULL si mes cerrado)
    pry_dia_del_mes          INT,
    pry_proyeccion_mes       DECIMAL(15,2) COMMENT 'Proyeccion lineal al cierre del mes',
    pry_ritmo_pct            DECIMAL(8,4)  COMMENT 'proyeccion / ant_ventas_netas (0-1)',

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva mismo canal-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4)  COMMENT '(ventas - ant) / ant (0-1)',

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, canal)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_canal (mes, canal)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_remisiones_canal_mes.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(DDL)
    cursor.execute("ALTER TABLE resumen_ventas_remisiones_canal_mes ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes")
    conn.commit()

    resumen = {}   # key: (mes, canal)

    # ── 1. Financiero + estado desde encabezados ──────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(fecha_de_creacion, 7)                                      AS mes,
            COALESCE(NULLIF(TRIM(tipo_de_markting), ''), 'Sin canal')       AS canal,
            SUM({cn('total_bruto')})                                        AS fin_ventas_brutas,
            SUM({cn('descuentos')})                                         AS fin_descuentos,
            SUM({cn('subtotal')})                                           AS fin_ventas_netas_sin_iva,
            SUM({cn('impuestos')})                                          AS fin_impuestos,
            COUNT(DISTINCT id_remision)                                     AS vol_num_remisiones,
            COUNT(DISTINCT id_cliente)                                      AS cli_clientes_activos,
            SUM(estado_remision = 'Pendiente de facturar')                  AS rem_pendientes,
            SUM(observacion_de_anulacion
                LIKE 'Remisi\u00f3n convertida a factura de venta%')        AS rem_facturadas
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
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
            'vol_num_remisiones':       ival(row['vol_num_remisiones']),
            'cli_clientes_activos':     ival(row['cli_clientes_activos']),
            'rem_pendientes':           ival(row['rem_pendientes']),
            'rem_facturadas':           ival(row['rem_facturadas']),
        }

    # ── 2. Volumen + costo + referencias desde detalle ────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            COALESCE(NULLIF(TRIM(e.tipo_de_markting), ''), 'Sin canal')     AS canal,
            SUM({cn_det('d.cantidad')})                                     AS vol_unidades,
            SUM({cn_det('d.costo_manual_total')})                           AS cto_costo_total,
            COUNT(DISTINCT d.cod_articulo)                                  AS cat_num_referencias
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
        GROUP BY mes, canal
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen:
            resumen[key]['vol_unidades_vendidas'] = fval(row['vol_unidades'])
            resumen[key]['cto_costo_total']       = fval(row['cto_costo_total'])
            resumen[key]['cat_num_referencias']   = ival(row['cat_num_referencias'])

    # ── 3. Clientes nuevos por (mes, canal) ───────────────────────────────────
    cursor.execute(f"""
        SELECT mes, canal, COUNT(*) AS nuevos
        FROM (
            SELECT
                e.id_cliente,
                COALESCE(NULLIF(TRIM(e.tipo_de_markting), ''), 'Sin canal') AS canal,
                LEFT(e.fecha_de_creacion, 7)                                AS mes
            FROM zeffi_remisiones_venta_encabezados e
            INNER JOIN (
                SELECT id_cliente, MIN(fecha_de_creacion) AS primera_fecha
                FROM zeffi_remisiones_venta_encabezados
                WHERE {FILTRO_ENC}
                GROUP BY id_cliente
            ) p ON e.id_cliente = p.id_cliente
                AND e.fecha_de_creacion = p.primera_fecha
            WHERE {FILTRO_ENC_JOIN}
            GROUP BY e.id_cliente, canal, mes
        ) t
        GROUP BY mes, canal
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen:
            resumen[key]['cli_clientes_nuevos'] = ival(row['nuevos'])

    # ── 4. Top cliente por (mes, canal) ───────────────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(fecha_de_creacion, 7)                                      AS mes,
            COALESCE(NULLIF(TRIM(tipo_de_markting), ''), 'Sin canal')       AS canal,
            cliente,
            SUM({cn('subtotal')})                                           AS ventas
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
        GROUP BY mes, canal, cliente
        ORDER BY mes, canal, ventas DESC
    """)

    seen_cli = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen and key not in seen_cli:
            seen_cli.add(key)
            resumen[key]['top_cliente']        = row['cliente']
            resumen[key]['top_cliente_ventas'] = fval(row['ventas'])

    # ── 5. Top producto por (mes, canal) ──────────────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            COALESCE(NULLIF(TRIM(e.tipo_de_markting), ''), 'Sin canal')     AS canal,
            d.cod_articulo,
            d.descripcion_articulo,
            SUM({cn_det('d.precio_bruto_total')} - {cn_det('d.descuento_total')}) AS ventas
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
        GROUP BY mes, canal, d.cod_articulo, d.descripcion_articulo
        ORDER BY mes, canal, ventas DESC
    """)

    seen_prod = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['canal'])
        if key in resumen and key not in seen_prod:
            seen_prod.add(key)
            resumen[key]['top_producto_cod']    = row['cod_articulo']
            resumen[key]['top_producto_nombre'] = row['descripcion_articulo']
            resumen[key]['top_producto_ventas'] = fval(row['ventas'])

    # ── 6. Derivados ──────────────────────────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    totales_mes = {}
    for (mes, canal), d in resumen.items():
        totales_mes[mes] = totales_mes.get(mes, 0.0) + d.get('fin_ventas_netas_sin_iva', 0.0)

    for (mes, canal) in sorted(resumen.keys()):
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        prev_mes      = f'{year-1:04d}-{month:02d}'
        d             = resumen[(mes, canal)]
        prev          = resumen.get((prev_mes, canal))

        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)
        rem_p  = d.get('rem_pendientes', 0)
        rem_f  = d.get('rem_facturadas', 0)

        d['fin_pct_descuento']       = pct(d.get('fin_descuentos', 0) / brutas if brutas else None)
        d['fin_pct_del_mes']         = pct(netas / totales_mes[mes] if totales_mes.get(mes) else None)
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = pct((netas - costo) / netas if netas else None)
        remisiones = d.get('vol_num_remisiones', 0)
        d['vol_ticket_promedio']     = netas / remisiones if remisiones else None
        activos = d.get('cli_clientes_activos', 0)
        d['cli_vtas_por_cliente']    = netas / activos if activos else None
        total_rem = rem_p + rem_f
        d['rem_pct_facturadas']      = pct(rem_f / total_rem if total_rem else None)

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

    # ── 7. UPSERT ─────────────────────────────────────────────────────────────
    upsert_sql = """
        INSERT INTO resumen_ventas_remisiones_canal_mes (
            _key, mes, canal, fecha_actualizacion,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos, fin_pct_del_mes,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_remisiones, vol_ticket_promedio,
            cli_clientes_activos, cli_clientes_nuevos, cli_vtas_por_cliente,
            cat_num_referencias,
            rem_pendientes, rem_facturadas, rem_pct_facturadas,
            top_cliente, top_cliente_ventas,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct
        ) VALUES (
            %(_key)s, %(mes)s, %(canal)s, %(fecha_actualizacion)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s, %(fin_pct_del_mes)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_remisiones)s, %(vol_ticket_promedio)s,
            %(cli_clientes_activos)s, %(cli_clientes_nuevos)s, %(cli_vtas_por_cliente)s,
            %(cat_num_referencias)s,
            %(rem_pendientes)s, %(rem_facturadas)s, %(rem_pct_facturadas)s,
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
            vol_num_remisiones       = VALUES(vol_num_remisiones),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cli_clientes_activos     = VALUES(cli_clientes_activos),
            cli_clientes_nuevos      = VALUES(cli_clientes_nuevos),
            cli_vtas_por_cliente     = VALUES(cli_vtas_por_cliente),
            cat_num_referencias      = VALUES(cat_num_referencias),
            rem_pendientes           = VALUES(rem_pendientes),
            rem_facturadas           = VALUES(rem_facturadas),
            rem_pct_facturadas       = VALUES(rem_pct_facturadas),
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
        cursor.execute(upsert_sql, {
            '_key':                     f'{mes}|{canal}',
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
            'vol_num_remisiones':       d.get('vol_num_remisiones'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cli_clientes_activos':     d.get('cli_clientes_activos'),
            'cli_clientes_nuevos':      d.get('cli_clientes_nuevos'),
            'cli_vtas_por_cliente':     d.get('cli_vtas_por_cliente'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'rem_pendientes':           d.get('rem_pendientes'),
            'rem_facturadas':           d.get('rem_facturadas'),
            'rem_pct_facturadas':       d.get('rem_pct_facturadas'),
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
        })

    conn.commit()
    cursor.close()
    conn.close()

    print(f'✅ resumen_ventas_remisiones_canal_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
