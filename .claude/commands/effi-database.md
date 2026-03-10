# Skill: Base de Datos effi_data (MariaDB)

Guía de acceso, consultas y patrones para trabajar con la base de datos `effi_data` en MariaDB.

---

## CRÍTICO — Por qué los comandos se cuelgan

> **NUNCA usar `mysql` sin el flag `-e`** en un contexto no interactivo.
>
> `mysql -u osadmin -pEpist2487. effi_data` sin `-e` abre un prompt interactivo
> y se queda esperando indefinidamente. Siempre pasar la query inline con `-e`.
>
> **También NUNCA poner espacio entre `-p` y la contraseña:**
> - ✅ `-pEpist2487.` (correcto — contraseña inline)
> - ❌ `-p Epist2487.` (incorrecto — espera contraseña por stdin, se cuelga)

---

## Credenciales y conexión

| Parámetro | Valor |
|---|---|
| Host (desde host) | `127.0.0.1` |
| Host (desde Docker) | `172.18.0.1` (gateway de red NocoDB) |
| Puerto | `3306` |
| Usuario | `osadmin` |
| Contraseña | `Epist2487.` |
| Base de datos principal | `effi_data` |
| Otras BDs | `espocrm`, `nocodb_meta` |

**MariaDB corre en el HOST** (systemd), NO en Docker. El puerto 3306 escucha en `0.0.0.0`.

Grants configurados:
- `osadmin@%` — acceso desde cualquier IP
- `osadmin@172.18.0.%` — acceso explícito desde contenedores Docker

---

## Comandos de consola

```bash
# Verificar que MariaDB está activo
ss -tlnp | grep 3306

# Listar tablas de effi_data
mysql -u osadmin -pEpist2487. effi_data -e "SHOW TABLES;"

# Contar filas de una tabla
mysql -u osadmin -pEpist2487. effi_data -e "SELECT COUNT(*) FROM zeffi_clientes;"

# Query con múltiples líneas (heredoc)
mysql -u osadmin -pEpist2487. effi_data 2>/dev/null <<'EOF'
SELECT tabla, COUNT(*) as filas
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'effi_data'
GROUP BY TABLE_NAME;
EOF

# Suprimir warning de contraseña en stderr
mysql -u osadmin -pEpist2487. effi_data -e "SELECT 1;" 2>/dev/null
```

---

## Tablas disponibles en effi_data

Todas las tablas tienen prefijo `zeffi_` (39 tablas BASE TABLE + 2 vistas sin prefijo).

### Tablas BASE TABLE (datos Effi)

| Tabla | Descripción |
|---|---|
| `zeffi_ajustes_inventario` | Ajustes manuales de stock |
| `zeffi_articulos_producidos` | Artículos resultado de producción |
| `zeffi_bodegas` | Catálogo de bodegas/almacenes |
| `zeffi_cambios_estado` | Historial de cambios de estado de documentos |
| `zeffi_categorias_articulos` | Árbol de categorías de productos |
| `zeffi_clientes` | Maestro de clientes |
| `zeffi_comprobantes_ingreso_detalle` | Líneas de comprobantes de ingreso |
| `zeffi_comprobantes_ingreso_encabezados` | Encabezados de comprobantes de ingreso |
| `zeffi_costos_produccion` | Costos por orden de producción |
| `zeffi_cotizaciones_ventas_detalle` | Líneas de cotizaciones |
| `zeffi_cotizaciones_ventas_encabezados` | Encabezados de cotizaciones |
| `zeffi_cuentas_por_cobrar` | CxC — facturas pendientes de cobro |
| `zeffi_cuentas_por_pagar` | CxP — facturas pendientes de pago |
| `zeffi_devoluciones_venta_detalle` | Líneas de devoluciones de venta |
| `zeffi_devoluciones_venta_encabezados` | Encabezados de devoluciones de venta |
| `zeffi_facturas_compra_detalle` | Líneas de facturas de compra |
| `zeffi_facturas_compra_encabezados` | Encabezados de facturas de compra |
| `zeffi_facturas_venta_detalle` | Líneas de facturas de venta |
| `zeffi_facturas_venta_encabezados` | Encabezados de facturas de venta (solo vigentes) |
| `zeffi_guias_transporte` | Guías de transporte/despacho |
| `zeffi_inventario` | Snapshot de inventario actual |
| `zeffi_materiales` | Materiales usados en producción |
| `zeffi_notas_credito_venta_detalle` | Líneas de notas crédito |
| `zeffi_notas_credito_venta_encabezados` | Encabezados de notas crédito |
| `zeffi_ordenes_compra_detalle` | Líneas de órdenes de compra |
| `zeffi_ordenes_compra_encabezados` | Encabezados de órdenes de compra |
| `zeffi_ordenes_venta_detalle` | Líneas de órdenes de venta |
| `zeffi_ordenes_venta_encabezados` | Encabezados de órdenes de venta |
| `zeffi_otros_costos` | Otros costos de producción |
| `zeffi_produccion_encabezados` | Encabezados de órdenes de producción |
| `zeffi_proveedores` | Maestro de proveedores |
| `zeffi_remisiones_compra_detalle` | Líneas de remisiones de compra |
| `zeffi_remisiones_compra_encabezados` | Encabezados de remisiones de compra |
| `zeffi_remisiones_venta_detalle` | Líneas de remisiones de venta |
| `zeffi_remisiones_venta_encabezados` | Encabezados de remisiones de venta |
| `zeffi_tipos_egresos` | Catálogo de tipos de egresos |
| `zeffi_tipos_marketing` | Catálogo de tipos de marketing |
| `zeffi_traslados_inventario` | Traslados entre bodegas |
| `zeffi_trazabilidad` | Trazabilidad de lotes/series |

### Vistas SQL (sin prefijo)

| Vista | Descripción |
|---|---|
| `vbase_ventas_mes` | Base para cálculo de ventas por mes |
| `vista_ventas_por_mes` | Ventas agrupadas por mes (JOIN facturas + clientes) |

---

## Estructura de tablas

Todas las tablas tienen:
- `_pk` BIGINT AUTO_INCREMENT PRIMARY KEY (columna interna)
- Todas las demás columnas son TEXT
- Charset: utf8mb4 / utf8mb4_unicode_ci

```bash
# Ver columnas de una tabla
mysql -u osadmin -pEpist2487. effi_data -e "DESCRIBE zeffi_clientes;" 2>/dev/null

# Ver primeras filas
mysql -u osadmin -pEpist2487. effi_data -e "SELECT * FROM zeffi_clientes LIMIT 3;" 2>/dev/null
```

---

## Conexión desde Python

```python
import mysql.connector

conn = mysql.connector.connect(
    host="127.0.0.1",   # desde host
    # host="172.18.0.1",  # desde contenedor Docker
    port=3306,
    user="osadmin",
    password="Epist2487.",
    database="effi_data"
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM zeffi_clientes")
print(cursor.fetchone())
conn.close()
```

---

## Conexión desde Node.js

```js
const mysql = require('mysql2/promise');
const conn = await mysql.createConnection({
  host: '127.0.0.1',  // desde host
  // host: 'host.docker.internal',  // desde contenedor playwright
  port: 3306,
  user: 'osadmin',
  password: 'Epist2487.',
  database: 'effi_data',
  charset: 'utf8mb4',
});
```

---

## Desde Docker — host correcto según contenedor

| Contenedor | Host a usar | Red Docker |
|---|---|---|
| `playwright` | `host.docker.internal` | bridge (extra_hosts configurado) |
| `nocodb` / `n8n` | `172.18.0.1` | red interna `antigravity_default` |
| Cualquier otro | `172.17.0.1` (bridge default) | bridge default |

> Si la conexión se cuelga desde Docker, verificar en qué red está el contenedor:
> `docker inspect <contenedor> | grep -A5 Networks`

---

## Actualización de datos

El pipeline corre automáticamente cada 2h (Lun–Sab 06:00–20:00) vía systemd.

```bash
# Forzar actualización manual completa (export + import)
python3 /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/orquestador.py --forzar

# Solo import (si los exports ya están frescos)
node /home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/import_all.js

# Ver logs del pipeline
journalctl -u effi-pipeline -f
# o
tail -f /home/osserver/Proyectos_Antigravity/Integraciones_OS/logs/pipeline.log
```
