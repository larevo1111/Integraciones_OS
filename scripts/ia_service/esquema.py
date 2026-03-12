"""
Genera el DDL (esquema) de las tablas analíticas de Hostinger.
Se usa como contexto para que la IA pueda generar SQL correcto.
Se cachea en memoria mientras el servicio está corriendo.
"""
import time
from .config import get_hostinger_conn

_cache = {'ddl': None, 'ts': 0}
_CACHE_TTL = 3600  # renovar cada hora

# Tablas que la IA necesita conocer para análisis de ventas
TABLAS_RELEVANTES = [
    'resumen_ventas_facturas_mes',
    'resumen_ventas_facturas_canal_mes',
    'resumen_ventas_facturas_cliente_mes',
    'resumen_ventas_facturas_producto_mes',
    'resumen_ventas_remisiones_mes',
    'resumen_ventas_remisiones_canal_mes',
    'resumen_ventas_remisiones_cliente_mes',
    'resumen_ventas_remisiones_producto_mes',
    'zeffi_clientes',
    'zeffi_facturas_venta_encabezados',
    'zeffi_facturas_venta_detalle',
    'zeffi_remisiones_venta_encabezados',
    'crm_contactos',
]

# Anotaciones críticas (gotchas que la IA debe conocer)
_NOTAS = """
/* NOTAS CRÍTICAS PARA GENERAR SQL CORRECTO:
   1. precio_neto_total INCLUYE IVA. Para ventas netas usar: precio_bruto_total - descuento_total
   2. id_cliente en zeffi_facturas_venta_detalle tiene prefijo tipo doc (ej: "CC 74084937").
      Para JOINs con zeffi_clientes usar: SUBSTRING_INDEX(id_cliente, ' ', -1)
   3. Las tablas resumen_ventas_* tienen columna _key (PK) con formato "mes|valor".
   4. resumen_ventas_facturas_mes.mes tiene formato 'YYYY-MM' (ej: '2026-03').
   5. Para el "mes actual" usar DATE_FORMAT(CURDATE(), '%Y-%m').
   6. _pct campos son decimales 0–1 (no porcentaje). top_* contiene nombres de texto.
   7. pry_* campos son solo del mes corriente (proyecciones).
*/
"""


def obtener_ddl(forzar: bool = False) -> str:
    """
    Devuelve el DDL de las tablas relevantes para análisis.
    Usa caché en memoria con TTL de 1 hora.
    """
    global _cache

    if not forzar and _cache['ddl'] and (time.time() - _cache['ts']) < _CACHE_TTL:
        return _cache['ddl']

    conn = None
    ddl_partes = [_NOTAS]

    try:
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            for tabla in TABLAS_RELEVANTES:
                try:
                    cur.execute(f"SHOW CREATE TABLE `{tabla}`")
                    row = cur.fetchone()
                    if row:
                        create_sql = row.get('Create Table', '')
                        ddl_partes.append(f"\n-- Tabla: {tabla}\n{create_sql};\n")
                except Exception:
                    ddl_partes.append(f"\n-- Tabla {tabla}: no disponible en este momento.\n")

        ddl = '\n'.join(ddl_partes)
        _cache = {'ddl': ddl, 'ts': time.time()}
        return ddl

    except Exception as e:
        return f"-- Error obteniendo esquema: {e}\n"
    finally:
        if conn:
            conn.close()
