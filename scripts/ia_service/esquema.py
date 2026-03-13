"""
Genera el schema de tablas para inyectar al LLM como contexto.
Lee de ia_esquemas (por tema) via conector.py.
Mantiene compatibilidad con el fallback legacy (conexión directa a Hostinger).
"""
import time
from .config import get_local_conn

# Caché legacy para compatibilidad (tema=None → set completo)
_cache_legacy = {'ddl': None, 'ts': 0}
_CACHE_TTL = 3600


def obtener_ddl(forzar: bool = False, tablas: list = None,
                tema_id: int = None, empresa: str = 'ori_sil_2') -> str:
    """
    Devuelve el schema para inyectar al LLM.

    - Si tema_id está presente: usa ia_esquemas (conector.py) — camino principal.
    - Si no: fallback al set completo legacy (compatibilidad).

    Args:
        forzar:   Ignorar caché.
        tablas:   Lista de tablas específicas (solo en modo legacy).
        tema_id:  ID del tema activo. Preferido.
        empresa:  Empresa activa.
    """
    if tema_id:
        from .conector import obtener_schema_tema
        if forzar:
            from .conector import sincronizar_schema, _cache_schema
            _cache_schema.pop(tema_id, None)
            sincronizar_schema(tema_id, empresa)
        return obtener_schema_tema(tema_id, empresa)

    # ── Fallback legacy ────────────────────────────────────────────────
    global _cache_legacy
    if not forzar and _cache_legacy['ddl'] and (time.time() - _cache_legacy['ts']) < _CACHE_TTL:
        return _cache_legacy['ddl']

    # Obtener el primer esquema disponible de la empresa (tema general o el primero)
    conn = get_local_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.* FROM ia_esquemas e
                JOIN ia_temas t ON t.id = e.tema_id
                WHERE e.empresa = %s AND e.activo = 1 AND t.slug = 'general'
                LIMIT 1
            """, (empresa,))
            esquema = cur.fetchone()

        if esquema and esquema.get('ddl_auto'):
            notas = esquema.get('notas_manuales', '') or ''
            resultado = esquema['ddl_auto']
            if notas:
                resultado += f"\n\nNOTAS DE NEGOCIO:\n{notas}"
            _cache_legacy = {'ddl': resultado, 'ts': time.time()}
            return resultado

    finally:
        conn.close()

    # Último fallback: conexión directa a Hostinger (comportamiento original)
    return _obtener_ddl_directo(tablas)


def _obtener_ddl_directo(tablas: list = None) -> str:
    """Fallback final: lee DDL directo de Hostinger (comportamiento original)."""
    from .config import get_hostinger_conn

    TABLAS_RELEVANTES = [
        'resumen_ventas_facturas_mes', 'resumen_ventas_facturas_canal_mes',
        'resumen_ventas_facturas_cliente_mes', 'resumen_ventas_facturas_producto_mes',
        'resumen_ventas_remisiones_mes', 'resumen_ventas_remisiones_canal_mes',
        'resumen_ventas_remisiones_cliente_mes', 'resumen_ventas_remisiones_producto_mes',
        'zeffi_clientes', 'zeffi_facturas_venta_encabezados',
        'zeffi_facturas_venta_detalle', 'zeffi_remisiones_venta_encabezados', 'crm_contactos',
    ]
    tablas_a_usar = tablas or TABLAS_RELEVANTES
    conn = None
    partes = []
    try:
        conn = get_hostinger_conn()
        with conn.cursor() as cur:
            for tabla in tablas_a_usar:
                try:
                    cur.execute(f"SHOW COLUMNS FROM `{tabla}`")
                    cols = cur.fetchall()
                    lineas = [f"  {c['Field']} {c['Type']}" for c in cols]
                    partes.append(f"tabla: {tabla}\n" + "\n".join(lineas))
                except Exception:
                    partes.append(f"tabla: {tabla}\n  -- no disponible")
        return "\n\n".join(partes)
    except Exception as e:
        return f"-- Error obteniendo esquema: {e}\n"
    finally:
        if conn:
            conn.close()
