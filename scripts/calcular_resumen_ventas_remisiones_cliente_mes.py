#!/usr/bin/env python3
"""
calcular_resumen_ventas_remisiones_cliente_mes.py
Calcula y actualiza resumen_ventas_remisiones_cliente_mes en effi_data (staging).
PK: (mes, id_cliente) — remisiones agrupadas por cliente y mes.
Paso 4c del pipeline.

Canal: canal dominante del cliente en ese mes (mayor subtotal)
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
    """Normaliza porcentaje: NULL si es None o fuera de rango DECIMAL(8,4)."""
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
CREATE TABLE IF NOT EXISTS resumen_ventas_remisiones_cliente_mes (
    mes                      VARCHAR(7)    NOT NULL COMMENT 'YYYY-MM',
    id_cliente               VARCHAR(50)   NOT NULL COMMENT 'ID cliente Effi',
    fecha_actualizacion      DATETIME,

    -- Identificacion
    cliente                  TEXT          COMMENT 'Nombre del cliente',
    canal                    VARCHAR(255)  COMMENT 'Canal dominante del cliente ese mes (mayor subtotal)',

    -- Financiero (de encabezados)
    fin_ventas_brutas        DECIMAL(15,2) COMMENT 'SUM total_bruto',
    fin_descuentos           DECIMAL(15,2) COMMENT 'SUM descuentos',
    fin_pct_descuento        DECIMAL(8,4)  COMMENT 'descuentos / ventas_brutas (0-1)',
    fin_ventas_netas_sin_iva DECIMAL(15,2) COMMENT 'SUM subtotal (sin IVA)',
    fin_impuestos            DECIMAL(15,2) COMMENT 'SUM impuestos',

    -- Costo (de detalle)
    cto_costo_total          DECIMAL(15,2) COMMENT 'SUM costo_manual_total',
    cto_utilidad_bruta       DECIMAL(15,2),
    cto_margen_utilidad_pct  DECIMAL(8,4),

    -- Volumen
    vol_unidades_vendidas    DECIMAL(15,2) COMMENT 'SUM cantidad',
    vol_num_remisiones       INT           COMMENT 'COUNT DISTINCT id_remision',
    vol_ticket_promedio      DECIMAL(15,2),

    -- Catalogo
    cat_num_referencias      INT           COMMENT 'Referencias distintas (cod_articulo)',

    -- Nuevo cliente
    cli_es_nuevo             TINYINT       COMMENT '1 si es la primera remision historica del cliente',

    -- Estado de remisiones (dinamico)
    rem_pendientes           INT           COMMENT 'Remisiones aun Pendiente de facturar de este cliente-mes',
    rem_facturadas           INT           COMMENT 'Remisiones convertidas a factura',
    rem_pct_facturadas       DECIMAL(8,4),

    -- Top producto
    top_producto_cod         TEXT,
    top_producto_nombre      TEXT,
    top_producto_ventas      DECIMAL(15,2),

    -- Proyeccion (solo mes corriente)
    pry_dia_del_mes          INT,
    pry_proyeccion_mes       DECIMAL(15,2),
    pry_ritmo_pct            DECIMAL(8,4),

    -- Ano anterior
    ant_ventas_netas         DECIMAL(15,2) COMMENT 'fin_ventas_netas_sin_iva mismo cliente-mes ano anterior',
    ant_var_ventas_pct       DECIMAL(8,4),

    _key                     VARCHAR(100) NOT NULL COMMENT 'PK único: CONCAT(mes, |, id_cliente)',

    PRIMARY KEY (_key),
    UNIQUE KEY uq_mes_cliente (mes, id_cliente)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('▶ calcular_resumen_ventas_remisiones_cliente_mes.py ...')

    conn   = mysql.connector.connect(**DB)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(DDL)
    cursor.execute("ALTER TABLE resumen_ventas_remisiones_cliente_mes ADD COLUMN IF NOT EXISTS _key VARCHAR(100) NOT NULL DEFAULT '' AFTER mes")
    conn.commit()

    resumen = {}   # key: (mes, id_cliente)

    # ── 1. Financiero + nombre + estado desde encabezados ─────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(fecha_de_creacion, 7)                                      AS mes,
            id_cliente,
            MAX(cliente)                                                    AS cliente,
            SUM({cn('total_bruto')})                                        AS fin_ventas_brutas,
            SUM({cn('descuentos')})                                         AS fin_descuentos,
            SUM({cn('subtotal')})                                           AS fin_ventas_netas_sin_iva,
            SUM({cn('impuestos')})                                          AS fin_impuestos,
            COUNT(DISTINCT id_remision)                                     AS vol_num_remisiones,
            SUM(estado_remision = 'Pendiente de facturar')                  AS rem_pendientes,
            SUM(observacion_de_anulacion
                LIKE 'Remisi\u00f3n convertida a factura de venta%')        AS rem_facturadas
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
          AND id_cliente IS NOT NULL AND id_cliente != ''
        GROUP BY mes, id_cliente
        ORDER BY mes, id_cliente
    """)

    for row in cursor.fetchall():
        mes, id_cli = row['mes'], row['id_cliente']
        if not mes or not id_cli:
            continue
        resumen[(mes, id_cli)] = {
            'cliente':                  row['cliente'],
            'fin_ventas_brutas':        fval(row['fin_ventas_brutas']),
            'fin_descuentos':           fval(row['fin_descuentos']),
            'fin_ventas_netas_sin_iva': fval(row['fin_ventas_netas_sin_iva']),
            'fin_impuestos':            fval(row['fin_impuestos']),
            'vol_num_remisiones':       ival(row['vol_num_remisiones']),
            'rem_pendientes':           ival(row['rem_pendientes']),
            'rem_facturadas':           ival(row['rem_facturadas']),
        }

    # ── 2. Canal dominante por (mes, id_cliente) ──────────────────────────────
    cursor.execute(f"""
        SELECT mes, id_cliente, canal
        FROM (
            SELECT
                LEFT(fecha_de_creacion, 7)                                  AS mes,
                id_cliente,
                COALESCE(NULLIF(TRIM(tipo_de_markting), ''), 'Sin canal')   AS canal,
                ROW_NUMBER() OVER (
                    PARTITION BY LEFT(fecha_de_creacion, 7), id_cliente
                    ORDER BY SUM({cn('subtotal')}) DESC
                ) AS rn
            FROM zeffi_remisiones_venta_encabezados
            WHERE {FILTRO_ENC}
              AND id_cliente IS NOT NULL AND id_cliente != ''
            GROUP BY LEFT(fecha_de_creacion, 7), id_cliente, canal
        ) t WHERE rn = 1
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['id_cliente'])
        if key in resumen:
            resumen[key]['canal'] = row['canal']

    # ── 3. Volumen + costo + referencias desde detalle ────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            e.id_cliente,
            SUM({cn_det('d.cantidad')})                                     AS vol_unidades,
            SUM({cn_det('d.costo_manual_total')})                           AS cto_costo_total,
            COUNT(DISTINCT d.cod_articulo)                                  AS cat_num_referencias
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
          AND e.id_cliente IS NOT NULL AND e.id_cliente != ''
        GROUP BY mes, e.id_cliente
    """)

    for row in cursor.fetchall():
        key = (row['mes'], row['id_cliente'])
        if key in resumen:
            resumen[key]['vol_unidades_vendidas'] = fval(row['vol_unidades'])
            resumen[key]['cto_costo_total']       = fval(row['cto_costo_total'])
            resumen[key]['cat_num_referencias']   = ival(row['cat_num_referencias'])

    # ── 4. Primera remision por cliente (cli_es_nuevo) ────────────────────────
    cursor.execute(f"""
        SELECT id_cliente, LEFT(MIN(fecha_de_creacion), 7) AS primer_mes
        FROM zeffi_remisiones_venta_encabezados
        WHERE {FILTRO_ENC}
          AND id_cliente IS NOT NULL AND id_cliente != ''
        GROUP BY id_cliente
    """)

    primer_mes_cli = {r['id_cliente']: r['primer_mes'] for r in cursor.fetchall()}
    for (mes, id_cli), d in resumen.items():
        d['cli_es_nuevo'] = 1 if primer_mes_cli.get(id_cli) == mes else 0

    # ── 5. Top producto por (mes, id_cliente) ─────────────────────────────────
    cursor.execute(f"""
        SELECT
            LEFT(e.fecha_de_creacion, 7)                                    AS mes,
            e.id_cliente,
            d.cod_articulo,
            d.descripcion_articulo,
            SUM({cn_det('d.precio_bruto_total')} - {cn_det('d.descuento_total')}) AS ventas
        FROM zeffi_remisiones_venta_detalle d
        JOIN zeffi_remisiones_venta_encabezados e ON d.id_remision = e.id_remision
        WHERE {FILTRO_ENC_JOIN}
          AND e.id_cliente IS NOT NULL AND e.id_cliente != ''
        GROUP BY mes, e.id_cliente, d.cod_articulo, d.descripcion_articulo
        ORDER BY mes, e.id_cliente, ventas DESC
    """)

    seen = set()
    for row in cursor.fetchall():
        key = (row['mes'], row['id_cliente'])
        if key in resumen and key not in seen:
            seen.add(key)
            resumen[key]['top_producto_cod']    = row['cod_articulo']
            resumen[key]['top_producto_nombre'] = row['descripcion_articulo']
            resumen[key]['top_producto_ventas'] = fval(row['ventas'])

    # ── 6. Derivados ──────────────────────────────────────────────────────────
    today         = datetime.date.today()
    current_month = today.strftime('%Y-%m')

    for (mes, id_cli) in sorted(resumen.keys()):
        year, month   = map(int, mes.split('-'))
        days_in_month = monthrange(year, month)[1]
        prev_mes      = f'{year-1:04d}-{month:02d}'
        d             = resumen[(mes, id_cli)]
        prev          = resumen.get((prev_mes, id_cli))

        netas  = d.get('fin_ventas_netas_sin_iva', 0)
        brutas = d.get('fin_ventas_brutas', 0)
        costo  = d.get('cto_costo_total', 0)
        rem_p  = d.get('rem_pendientes', 0)
        rem_f  = d.get('rem_facturadas', 0)

        d['fin_pct_descuento']       = pct(d.get('fin_descuentos', 0) / brutas if brutas else None)
        d['cto_utilidad_bruta']      = netas - costo
        d['cto_margen_utilidad_pct'] = pct((netas - costo) / netas if netas else None)
        remisiones = d.get('vol_num_remisiones', 0)
        d['vol_ticket_promedio']     = netas / remisiones if remisiones else None
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
        INSERT INTO resumen_ventas_remisiones_cliente_mes (
            _key, mes, id_cliente, fecha_actualizacion,
            cliente, canal,
            fin_ventas_brutas, fin_descuentos, fin_pct_descuento,
            fin_ventas_netas_sin_iva, fin_impuestos,
            cto_costo_total, cto_utilidad_bruta, cto_margen_utilidad_pct,
            vol_unidades_vendidas, vol_num_remisiones, vol_ticket_promedio,
            cat_num_referencias, cli_es_nuevo,
            rem_pendientes, rem_facturadas, rem_pct_facturadas,
            top_producto_cod, top_producto_nombre, top_producto_ventas,
            pry_dia_del_mes, pry_proyeccion_mes, pry_ritmo_pct,
            ant_ventas_netas, ant_var_ventas_pct
        ) VALUES (
            %(_key)s, %(mes)s, %(id_cliente)s, %(fecha_actualizacion)s,
            %(cliente)s, %(canal)s,
            %(fin_ventas_brutas)s, %(fin_descuentos)s, %(fin_pct_descuento)s,
            %(fin_ventas_netas_sin_iva)s, %(fin_impuestos)s,
            %(cto_costo_total)s, %(cto_utilidad_bruta)s, %(cto_margen_utilidad_pct)s,
            %(vol_unidades_vendidas)s, %(vol_num_remisiones)s, %(vol_ticket_promedio)s,
            %(cat_num_referencias)s, %(cli_es_nuevo)s,
            %(rem_pendientes)s, %(rem_facturadas)s, %(rem_pct_facturadas)s,
            %(top_producto_cod)s, %(top_producto_nombre)s, %(top_producto_ventas)s,
            %(pry_dia_del_mes)s, %(pry_proyeccion_mes)s, %(pry_ritmo_pct)s,
            %(ant_ventas_netas)s, %(ant_var_ventas_pct)s
        )
        ON DUPLICATE KEY UPDATE
            fecha_actualizacion      = VALUES(fecha_actualizacion),
            cliente                  = VALUES(cliente),
            canal                    = VALUES(canal),
            fin_ventas_brutas        = VALUES(fin_ventas_brutas),
            fin_descuentos           = VALUES(fin_descuentos),
            fin_pct_descuento        = VALUES(fin_pct_descuento),
            fin_ventas_netas_sin_iva = VALUES(fin_ventas_netas_sin_iva),
            fin_impuestos            = VALUES(fin_impuestos),
            cto_costo_total          = VALUES(cto_costo_total),
            cto_utilidad_bruta       = VALUES(cto_utilidad_bruta),
            cto_margen_utilidad_pct  = VALUES(cto_margen_utilidad_pct),
            vol_unidades_vendidas    = VALUES(vol_unidades_vendidas),
            vol_num_remisiones       = VALUES(vol_num_remisiones),
            vol_ticket_promedio      = VALUES(vol_ticket_promedio),
            cat_num_referencias      = VALUES(cat_num_referencias),
            cli_es_nuevo             = VALUES(cli_es_nuevo),
            rem_pendientes           = VALUES(rem_pendientes),
            rem_facturadas           = VALUES(rem_facturadas),
            rem_pct_facturadas       = VALUES(rem_pct_facturadas),
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

    for (mes, id_cli) in sorted(resumen.keys()):
        d = resumen[(mes, id_cli)]
        cursor.execute(upsert_sql, {
            '_key':                     f'{mes}|{id_cli}',
            'mes':                      mes,
            'id_cliente':               id_cli,
            'fecha_actualizacion':      now,
            'cliente':                  d.get('cliente'),
            'canal':                    d.get('canal'),
            'fin_ventas_brutas':        d.get('fin_ventas_brutas'),
            'fin_descuentos':           d.get('fin_descuentos'),
            'fin_pct_descuento':        d.get('fin_pct_descuento'),
            'fin_ventas_netas_sin_iva': d.get('fin_ventas_netas_sin_iva'),
            'fin_impuestos':            d.get('fin_impuestos'),
            'cto_costo_total':          d.get('cto_costo_total'),
            'cto_utilidad_bruta':       d.get('cto_utilidad_bruta'),
            'cto_margen_utilidad_pct':  d.get('cto_margen_utilidad_pct'),
            'vol_unidades_vendidas':    d.get('vol_unidades_vendidas'),
            'vol_num_remisiones':       d.get('vol_num_remisiones'),
            'vol_ticket_promedio':      d.get('vol_ticket_promedio'),
            'cat_num_referencias':      d.get('cat_num_referencias'),
            'cli_es_nuevo':             d.get('cli_es_nuevo'),
            'rem_pendientes':           d.get('rem_pendientes'),
            'rem_facturadas':           d.get('rem_facturadas'),
            'rem_pct_facturadas':       d.get('rem_pct_facturadas'),
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

    print(f'✅ resumen_ventas_remisiones_cliente_mes — {len(resumen)} filas actualizadas')


if __name__ == '__main__':
    main()
