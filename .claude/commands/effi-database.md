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
| BD Hostinger | `u768061575_os_integracion` (SSH tunnel) |

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

Tablas de datos Effi: prefijo `zeffi_` (39 tablas BASE TABLE). Más 1 tabla analítica propia y 2 vistas sin prefijo.

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

### Tabla analítica propia (calculada por el pipeline)

| Tabla | Descripción |
|---|---|
| `resumen_ventas_facturas_mes` | Resumen mensual de ventas (38 campos: fin_, cto_, vol_, cli_, car_, cat_, con_, top_, pry_, ant_). PK = `mes` VARCHAR(7) 'YYYY-MM'. Paso 3a del pipeline. |
| `resumen_ventas_facturas_canal_mes` | Resumen mensual de ventas por canal de marketing (29 campos). PK = `(mes, canal)`. Canal = `marketing_cliente` del detalle, NULLs normalizados a `'Sin canal'`. Paso 3b del pipeline. `fin_ventas_netas_sin_iva` = `precio_bruto_total - descuento_total` (correcto, sin IVA). Los `top_ventas` y `fin_impuestos` incluyen IVA. SUM por mes de `fin_pct_del_mes` = 1.0 ± 0.0002 (redondeo DECIMAL). |

### Vistas SQL (sin prefijo)

| Vista | Descripción |
|---|---|
| `vbase_ventas_mes` | Base para cálculo de ventas por mes |
| `vista_ventas_por_mes` | Ventas agrupadas por mes (JOIN facturas + clientes) |

---

## Estructura de tablas

Todas las tablas `zeffi_*` tienen:
- `_pk` BIGINT AUTO_INCREMENT PRIMARY KEY (columna interna)
- Todas las demás columnas son TEXT
- Charset: utf8mb4 / utf8mb4_unicode_ci

### Gotchas de esquema — campos críticos en tablas de ventas

> **CRÍTICO para no cometer errores al consultar.**

#### `zeffi_facturas_venta_encabezados`
- **NO tiene columna `vigencia`** — el export de Effi ya filtra solo vigentes (`?vigente=1`). No intentar `WHERE vigencia = 'Vigente'`.
- Campo fecha: `fecha_de_creacion` (DATETIME como TEXT, e.g. `'2025-01-25 10:02:19'`)
- Identificador cliente: `id_cliente` con prefijo `'CC '` o `'NIT '` (e.g. `'NIT 900982270'`)
- Campos numéricos con coma decimal: `total_neto`, `descuentos`, `costo_manual`, `pdte_de_cobro`, etc. → castear con `CAST(REPLACE(COALESCE(campo, '0'), ',', '.') AS DECIMAL(15,2))`

#### `zeffi_facturas_venta_detalle`
- **`referencia` = NULL** en la mayoría de registros — usar `cod_articulo` para identificar productos
- `descripcion_articulo` = nombre legible del producto. **⚠️ NO existe columna `nombre_articulo`** — error frecuente al escribir queries o endpoints.
- **⚠️ NO existe columna `id_item`** — no usarla en ORDER BY ni SELECT.
- **⚠️ Campo fecha = `fecha_creacion_factura`** (NO `fecha_de_creacion`). Diferencia con encabezados: los encabezados usan `fecha_de_creacion`, el detalle usa `fecha_creacion_factura`. Confundirlos da 0 resultados.
- `fecha_creacion_factura` y `vigencia_factura` duplican el encabezado → no se requiere JOIN para queries mensuales
- `precio_neto_total` = **INCLUYE IVA** (precio_bruto - descuento + impuesto). Para obtener valor SIN IVA usar `precio_bruto_total - descuento_total`. NUNCA usar `precio_neto_total` como "sin IVA" — es un nombre engañoso.
- `id_numeracion` = número/código de la factura en esta tabla (NO existe columna `numero_factura`). En el ERP se muestra con label "No Fac".
- `marketing_cliente` = canal de venta (e.g. `'1.3. Mercado Saludable'`). NULL o vacío → normalizar como `'Sin canal'`
- `id_cliente` = formato `'CC 74084937'` o `'NIT 900982270'` (con prefijo tipo doc). Para JOIN con `zeffi_clientes.numero_de_identificacion` usar: `SUBSTRING_INDEX(d.id_cliente, ' ', -1)`.

#### `zeffi_remisiones_venta_detalle`
- **⚠️ Campo fecha = `fecha_creacion`** (sin `_de_` ni `_factura`). Diferente a los encabezados (`fecha_de_creacion`) y al detalle de facturas (`fecha_creacion_factura`). Confundirlos da error de columna.
- `tipo_de_marketing_cliente` = canal de venta en detalle de remisiones (diferente a facturas que usa `marketing_cliente`).

#### `zeffi_ordenes_venta_encabezados`
- `vigencia` puede ser `'Vigente'` (en consignación activa) o `'Anulada'` (liquidada o error)
- Para consignación, excluir errores operativos: OVs anuladas en ≤1 día sin keywords de liquidación
  (ver skill `/effi-negocio` sección 3 para la heurística completa)

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

---

## Verificaciones obligatorias de tablas analíticas

> Ejecutar siempre que se cree o modifique un script de resumen. Comparar con fuente directa.

### V1 — Financiero vs fuente (canal_mes vs detalle)
```sql
SELECT r.mes, LEFT(r.canal,30) AS canal,
       r.fin_ventas_netas_sin_iva AS r_netas,
       ROUND(SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2))
             - CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))),2) AS v_netas,
       ROUND(r.fin_ventas_netas_sin_iva -
             SUM(CAST(REPLACE(COALESCE(d.precio_bruto_total,'0'),',','.') AS DECIMAL(15,2))
             - CAST(REPLACE(COALESCE(d.descuento_total,'0'),',','.') AS DECIMAL(15,2))),2) AS diff
FROM resumen_ventas_facturas_canal_mes r
JOIN zeffi_facturas_venta_detalle d
    ON DATE_FORMAT(d.fecha_creacion_factura,'%Y-%m') = r.mes
    AND COALESCE(NULLIF(TRIM(d.marketing_cliente),''),'Sin canal') = r.canal
    AND d.vigencia_factura = 'Vigente'
WHERE r.mes IN ('2026-02','2026-01','2025-12','2025-09','2025-06')
GROUP BY r.mes, r.canal, r.fin_ventas_netas_sin_iva
ORDER BY r.mes DESC, r.fin_ventas_netas_sin_iva DESC LIMIT 20;
-- Esperado: diff = 0.00 en todos
```

### V2 — Consistencia cruzada: SUM(canal_mes) debe igualar resumen_mes
```sql
SELECT m.mes,
       m.fin_ventas_netas_sin_iva        AS m_netas,
       ROUND(SUM(c.fin_ventas_netas_sin_iva),2) AS c_netas,
       m.fin_ventas_brutas               AS m_brutas,
       ROUND(SUM(c.fin_ventas_brutas),2) AS c_brutas,
       m.cto_costo_total                 AS m_costo,
       ROUND(SUM(c.cto_costo_total),2)   AS c_costo,
       m.vol_unidades_vendidas           AS m_unid,
       ROUND(SUM(c.vol_unidades_vendidas),2) AS c_unid,
       ROUND(m.fin_ventas_netas_sin_iva - SUM(c.fin_ventas_netas_sin_iva),2) AS diff_netas,
       ROUND(m.cto_costo_total          - SUM(c.cto_costo_total),2)          AS diff_costo
FROM resumen_ventas_facturas_mes m
JOIN resumen_ventas_facturas_canal_mes c ON c.mes = m.mes
WHERE m.mes IN ('2026-02','2026-01','2025-12','2025-09','2025-06','2025-03','2025-01')
GROUP BY m.mes, m.fin_ventas_netas_sin_iva, m.fin_ventas_brutas, m.cto_costo_total, m.vol_unidades_vendidas
ORDER BY m.mes DESC;
-- Esperado: diff_netas y diff_costo ≤ 0.30 (solo redondeo DECIMAL)
-- ALERTA si diff > 1.00: revisar bug en join o cálculo de netas
```

### V3 — Porcentajes suman 1.0 por mes
```sql
SELECT mes, ROUND(SUM(fin_pct_del_mes),4) AS suma_pct, COUNT(*) AS canales
FROM resumen_ventas_facturas_canal_mes
GROUP BY mes ORDER BY mes;
-- Esperado: suma_pct entre 0.9998 y 1.0002
```

### V4 — pry_ solo populado en mes corriente
```sql
SELECT mes, COUNT(*) AS filas,
       SUM(CASE WHEN pry_dia_del_mes IS NULL THEN 1 ELSE 0 END) AS pry_null,
       SUM(CASE WHEN pry_dia_del_mes IS NOT NULL THEN 1 ELSE 0 END) AS pry_ok
FROM resumen_ventas_facturas_canal_mes
GROUP BY mes ORDER BY mes;
-- Esperado: pry_null = filas en todos los meses cerrados; pry_ok > 0 solo en mes corriente
```

### V5 — resumen_mes: financiero vs fuente directa (encabezados)
```sql
SELECT m.mes,
       m.fin_ventas_brutas AS r_brutas,
       ROUND(SUM(CAST(REPLACE(COALESCE(e.total_bruto,'0'),',','.') AS DECIMAL(15,2))),2) AS v_brutas,
       ROUND(m.fin_ventas_brutas -
             SUM(CAST(REPLACE(COALESCE(e.total_bruto,'0'),',','.') AS DECIMAL(15,2))),2) AS diff
FROM resumen_ventas_facturas_mes m
JOIN zeffi_facturas_venta_encabezados e
    ON DATE_FORMAT(e.fecha_de_creacion,'%Y-%m') = m.mes
WHERE m.mes IN ('2026-02','2026-01','2025-12','2025-09','2025-06')
GROUP BY m.mes, m.fin_ventas_brutas
ORDER BY m.mes DESC;
-- Esperado: diff = 0.00
```

### V6 — con_consignacion_pp cliente_mes vs OVs fuente directa
```sql
SELECT
  r.mes, r.id_cliente, r.cliente,
  r.con_consignacion_pp AS r_con,
  ROUND(SUM(CAST(REPLACE(COALESCE(o.total_neto,'0'),',','.') AS DECIMAL(15,2))),2) AS src_con,
  ROUND(r.con_consignacion_pp -
        SUM(CAST(REPLACE(COALESCE(o.total_neto,'0'),',','.') AS DECIMAL(15,2))),2) AS diff
FROM resumen_ventas_facturas_cliente_mes r
JOIN zeffi_ordenes_venta_encabezados o
  ON o.id_cliente = r.id_cliente
  AND DATE_FORMAT(o.fecha_de_creacion,'%Y-%m') = r.mes
WHERE r.con_consignacion_pp IS NOT NULL
AND NOT (
    o.vigencia = 'Anulada'
    AND DATEDIFF(COALESCE(o.fecha_de_anulacion, o.fecha_de_creacion), o.fecha_de_creacion) <= 1
    AND LOWER(COALESCE(o.observacion_de_anulacion,''))
        NOT REGEXP 'liquidac|remis|convertid|retiro|devolu|no vendi|no se entreg'
)
GROUP BY r.mes, r.id_cliente, r.cliente, r.con_consignacion_pp
HAVING diff != 0
ORDER BY r.mes DESC, r.con_consignacion_pp DESC
LIMIT 20;
-- Esperado: 0 filas (ninguna diferencia)
```

---

## BD espocrm — Tablas clave

### Tabla `contact`
Entidad principal del CRM. Columnas custom (además de las estándar EspoCRM):
```
numero_identificacion VARCHAR(100)
tipo_identificacion   VARCHAR(255)  -- enum texto
tipo_persona          VARCHAR(255)  -- "Física (natural)" / "Jurídica (moral)"
tipo_cliente          VARCHAR(255)  -- enum: Común, Fiel, Desertor, Mayorista, Importador, Industrial
tipo_de_marketing     VARCHAR(255)  -- enum dinámico (sync desde zeffi_tipos_marketing)
tarifa_precios        VARCHAR(255)  -- enum dinámico (sync desde zeffi_tarifas_precios)
forma_pago            VARCHAR(100)
vendedor_effi         VARCHAR(255)  -- enum dinámico (DISTINCT de vendedores en Effi)
ciudad_id             VARCHAR(17)   -- FK → ciudad.id
fuente                VARCHAR(255)  -- "CRM" (manual) o "Effi" (importado)
enviado_a_effi        TINYINT(1)    -- 0=pendiente, 1=ya importado a Effi
```

### Tabla `ciudad`
Catálogo de 12,237 ciudades cargado desde plantilla Effi.
```
id            VARCHAR(17)  PK (formato EspoCRM)
name          VARCHAR(200) nombre ciudad
id_effi       INT          UNIQUE — ID numérico en Effi (para la plantilla de import)
departamento  VARCHAR(150)
pais          VARCHAR(100)
deleted       TINYINT(1)
```
Consultar ciudad por nombre:
```sql
SELECT id, name, id_effi, departamento, pais
FROM ciudad WHERE LOWER(name) LIKE '%medell%' AND deleted=0;
```

### Tabla `crm_contactos` (Hostinger)
Mirror de EspoCRM contact en `u768061575_os_integracion`. Se actualiza en paso 6d.
480 contactos. Columnas: id, nombre_completo, first/last_name, numero_identificacion,
tipo_identificacion, tipo_persona, email, telefono, address_*, ciudad, departamento,
pais, tipo_de_marketing, tipo_cliente, tarifa_precios, forma_pago, vendedor_effi,
fuente, enviado_a_effi, descripcion.

### Queries útiles de EspoCRM

```bash
# Contactos pendientes de enviar a Effi (fuente=CRM, no enviados)
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT first_name, last_name, numero_identificacion, tipo_de_marketing, fuente, enviado_a_effi
FROM contact WHERE fuente='CRM' AND (enviado_a_effi=0 OR enviado_a_effi IS NULL) AND deleted=0;" 2>/dev/null

# Ver distribución fuente/enviado
mysql -u osadmin -pEpist2487. espocrm -e "
SELECT fuente, enviado_a_effi, COUNT(*) FROM contact WHERE deleted=0 GROUP BY 1,2;" 2>/dev/null
```

### V7 — cli_clientes_nuevos canal_mes vs fuente directa
```sql
SELECT c.mes, c.canal, c.cli_clientes_nuevos AS r_nuevos, COUNT(*) AS src_nuevos,
       c.cli_clientes_nuevos - COUNT(*) AS diff
FROM resumen_ventas_facturas_canal_mes c
JOIN (
  SELECT d.id_cliente,
         COALESCE(NULLIF(TRIM(d.marketing_cliente),''),'Sin canal') AS canal,
         DATE_FORMAT(d.fecha_creacion_factura,'%Y-%m') AS mes
  FROM zeffi_facturas_venta_detalle d
  INNER JOIN (
    SELECT id_cliente, MIN(fecha_creacion_factura) AS primera_fecha
    FROM zeffi_facturas_venta_detalle WHERE vigencia_factura='Vigente'
    GROUP BY id_cliente
  ) p ON d.id_cliente = p.id_cliente AND d.fecha_creacion_factura = p.primera_fecha
  WHERE d.vigencia_factura='Vigente'
  GROUP BY d.id_cliente, canal, mes
) src ON src.mes = c.mes AND src.canal = c.canal
GROUP BY c.mes, c.canal, c.cli_clientes_nuevos
HAVING diff != 0
ORDER BY c.mes DESC;
-- Esperado: 0 filas (ninguna diferencia)
```
