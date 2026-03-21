# Benchmark de Agentes IA — Origen Silvestre
**Fecha:** 2026-03-20 19:27
**Agentes SQL testados:** gemini-flash, gemini-flash-lite, groq-llama, gpt-oss-120b, cerebras-llama
**Agentes respuesta testados:** gemini-flash, gemini-flash-lite, groq-llama, gpt-oss-120b, cerebras-llama

---
## FASE 1 — Generación de SQL

| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |
|---|---|---|---|---|---|
| SQL-01 | Ventas mes actual | OK / 2f / 10674ms | OK / 2f / 10039ms | OK / 2f / 17998ms | OK / 2f / 19816ms | OK / 2f / 17604ms |
| SQL-02 | Top canales febrero | OK / 2f / 9630ms | OK / 2f / 9232ms | OK / 2f / 17907ms | OK / 2f / 20396ms | OK / 2f / 19431ms |
| SQL-03 | Producto más vendido | OK / 2f / 10124ms | OK / 2f / 8922ms | OK / 2f / 17823ms | OK / 2f / 17823ms | OK / 2f / 19296ms |
| SQL-04 | Cartera vencida | OK / 2f / 11366ms | OK / 2f / 8982ms | OK / 2f / 16613ms | OK / 2f / 18287ms | OK / 2f / 17712ms |
| SQL-05 | Stock inventario | OK / 2f / 7640ms | NO_SQL / 2f / 4257ms | OK / 2f / 12419ms | OK / 2f / 17184ms | OK / 2f / 14826ms |
| SQL-06 | Órdenes producción vigentes | OK / 2f / 8566ms | OK / 2f / 7171ms | OK / 2f / 12527ms | OK / 2f / 13487ms | OK / 2f / 13716ms |
| SQL-07 | Remisiones pendientes | OK / 2f / 9471ms | OK / 2f / 9740ms | OK / 2f / 16548ms | OK / 2f / 21254ms | OK / 2f / 17191ms |
| SQL-08 | Consignación activa | OK / 2f / 11047ms | OK / 2f / 14579ms | OK / 2f / 19435ms | OK / 2f / 18746ms | OK / 2f / 20517ms |
| SQL-09 | Comparativo año anterior | OK / 2f / 17260ms | OK / 2f / 14188ms | OK / 2f / 26080ms | OK / 2f / 26333ms | OK / 2f / 39352ms |
| SQL-10 | Margen por canal | OK / 2f / 11011ms | OK / 2f / 10530ms | OK / 2f / 24209ms | OK / 2f / 21417ms | OK / 2f / 23968ms |
| SQL-11 | Clientes nuevos | NO_SQL / 2f / 5626ms | NO_SQL / 2f / 6219ms | OK / 2f / 17109ms | NO_SQL / 2f / 6297ms | OK / 2f / 19308ms |
| SQL-12 | Compras materia prima | OK / 2f / 21178ms | OK / 2f / 8666ms | OK / 2f / 13779ms | OK / 2f / 14052ms | ERROR / 0f / 15951ms |
| SQL-13 | Top 5 productos más rentables | OK / 2f / 11188ms | OK / 2f / 8786ms | OK / 2f / 16968ms | OK / 2f / 17495ms | OK / 2f / 18278ms |
| SQL-14 | Evolución mensual ventas 6 meses | OK / 2f / 12908ms | OK / 2f / 10966ms | OK / 2f / 20846ms | OK / 2f / 21109ms | OK / 2f / 25175ms |
| SQL-15 | Clientes que compraron este año pero no  | OK / 2f / 13293ms | OK / 2f / 8535ms | OK / 2f / 18841ms | OK / 2f / 18787ms | OK / 2f / 19384ms |
| SQL-16 | Canal más rentable vs año anterior | OK / 2f / 13973ms | OK / 2f / 10308ms | NO_SQL / 0f / 31584ms | OK / 2f / 27009ms | OK / 2f / 25666ms |
| SQL-17 | Productos sin movimiento | OK / 2f / 11277ms | OK / 2f / 27007ms | OK / 2f / 24113ms | OK / 2f / 33121ms | OK / 2f / 27121ms |
| SQL-18 | Ticket promedio por canal | OK / 2f / 12704ms | OK / 2f / 10944ms | OK / 2f / 23533ms | OK / 2f / 27127ms | OK / 2f / 25076ms |

### Latencia y costo promedio — SQL

| Agente | Latencia prom (ms) | Costo total USD | SQL OK% |
|---|---|---|---|
| gemini-flash | 11608 | $0.095655 | 94% |
| gemini-flash-lite | 10504 | $0.097104 | 89% |
| groq-llama | 19352 | $0.091768 | 94% |
| gpt-oss-120b | 19986 | $0.096209 | 94% |
| cerebras-llama | 21087 | $0.096129 | 94% |

### SQL generados por query y agente


#### SQL-01 — Ventas mes actual
**Pregunta:** ¿Cuánto vendimos en total este mes de marzo 2026?

**gemini-flash** (OK / 2 filas / 10674ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**gemini-flash-lite** (OK / 2 filas / 10039ms):
```sql
SELECT
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**groq-llama** (OK / 2 filas / 17998ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**gpt-oss-120b** (OK / 2 filas / 19816ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 1) AS margen_pct
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**cerebras-llama** (OK / 2 filas / 17604ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 1) AS margen_promedio_pct
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03'
```

#### SQL-02 — Top canales febrero
**Pregunta:** ¿Cuál fue el top 3 de canales de venta en febrero 2026 por valor neto?

**gemini-flash** (OK / 2 filas / 9630ms):
```sql
SELECT
  canal,
  fin_ventas_netas_sin_iva
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**gemini-flash-lite** (OK / 2 filas / 9232ms):
```sql
SELECT
  canal,
  fin_ventas_netas_sin_iva
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**groq-llama** (OK / 2 filas / 17907ms):
```sql
SELECT
  canal,
  fin_ventas_netas_sin_iva AS valor_neto_sin_iva,
  fin_pct_del_mes AS participacion_porcentual
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**gpt-oss-120b** (OK / 2 filas / 20396ms):
```sql
SELECT
    canal,
    fin_ventas_netas_sin_iva AS valor_neto_sin_iva,
    fin_pct_del_mes AS porcentaje_del_mes,
    vol_num_facturas AS numero_facturas,
    cli_clientes_activos AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
    AND fin_ventas_netas_sin_iva > 0
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**cerebras-llama** (OK / 2 filas / 19431ms):
```sql
SELECT 
    canal,
    fin_ventas_netas_sin_iva AS valor_neto,
    vol_num_facturas AS numero_facturas,
    cli_clientes_activos AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
    AND fin_ventas_netas_sin_iva > 0
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```

#### SQL-03 — Producto más vendido
**Pregunta:** ¿Cuál fue el producto más vendido en unidades durante 2025?

**gemini-flash** (OK / 2 filas / 10124ms):
```sql
SELECT
  nombre AS nombre_del_producto,
  SUM(CAST(vol_unidades_vendidas AS DECIMAL(15,2))) AS total_unidades_vendidas
FROM resumen_ventas_facturas_producto_mes
WHERE mes LIKE '2025-%'
GROUP BY nombre
ORDER BY total_unidades_vendidas DESC
LIMIT 1;
```
**gemini-flash-lite** (OK / 2 filas / 8922ms):
```sql
SELECT
  d.descripcion_articulo,
  SUM(CAST(d.cantidad AS DECIMAL(15,2))) AS unidades_vendidas
FROM zeffi_facturas_venta_detalle d
WHERE DATE_FORMAT(d.fecha_creacion_factura, '%Y') = '2025'
  AND d.vigencia_factura = 'Vigente'
GROUP BY d.cod_articulo, d.descripcion_articulo
ORDER BY unidades_vendidas DESC
LIMIT 1;
```
**groq-llama** (OK / 2 filas / 17823ms):
```sql
SELECT
  d.cod_articulo,
  d.descripcion_articulo,
  SUM(CAST(d.cantidad AS DECIMAL(15,2))) AS unidades_vendidas
FROM zeffi_facturas_venta_detalle d
WHERE DATE_FORMAT(d.fecha_creacion_factura, '%Y') = '2025'
  AND d.vigencia_factura = 'Vigente'
GROUP BY d.cod_articulo, d.descripcion_articulo
ORDER BY unidades_vendidas DESC
LIMIT 1;
```
**gpt-oss-120b** (OK / 2 filas / 17823ms):
```sql
SELECT
    d.cod_articulo,
    d.descripcion_articulo,
    SUM(CAST(d.cantidad AS DECIMAL(15,2))) AS unidades_vendidas
FROM zeffi_facturas_venta_detalle d
WHERE d.vigencia_factura = 'Vigente'
    AND DATE_FORMAT(d.fecha_creacion_factura, '%Y') = '2025'
GROUP BY d.cod_articulo, d.descripcion_articulo
ORDER BY unidades_vendidas DESC
LIMIT 1;
```
**cerebras-llama** (OK / 2 filas / 19296ms):
```sql
SELECT
    d.cod_articulo,
    d.descripcion_articulo,
    SUM(CAST(d.cantidad AS DECIMAL(15,2))) AS unidades_vendidas,
    SUM(CAST(d.precio_bruto_total AS DECIMAL(15,2)) - CAST(d.descuento_total AS DECIMAL(15,2))) AS ventas_netas_sin_iva
FROM zeffi_facturas_venta_detalle d
JOIN zeffi_facturas_venta_encabezados e ON d.id_numeracion = e.id_numeracion
WHERE YEAR(DATE(e.fecha_de_creacion)) = 2025
    AND e.fecha_de_anulacion IS NULL
    AND d.vigencia_factura = 'Vigente'
GROUP BY d.cod_articulo, d
```

#### SQL-04 — Cartera vencida
**Pregunta:** ¿Cuánto hay en cartera vencida actualmente y cuáles son los 5 clientes con más deuda?

**gemini-flash** (OK / 2 filas / 11366ms):
```sql
SELECT
  (SELECT SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) FROM zeffi_cuentas_por_cobrar WHERE estado_cxc = 'Pendiente de cobro en mora') AS total_cartera_vencida,
  t.tercero AS cliente,
  t.id_tercero AS id_cliente,
  t.deuda_en_mora
FROM (
  SELECT
    tercero,
    id_tercero,
    SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
  FROM zeffi_cuentas_por_cobrar
  WHERE estado_cxc = 'Pendiente de cobro en mora'
  GROUP BY tercero, id_tercero
  ORDER BY deuda_en_mora DESC
  LIMIT 5
) A
```
**gemini-flash-lite** (OK / 2 filas / 8982ms):
```sql
SELECT
  (SELECT SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) FROM zeffi_cuentas_por_cobrar WHERE estado_cxc = 'Pendiente de cobro en mora') AS total_cartera_vencida,
  t.tercero AS cliente,
  t.id_tercero AS id_cliente,
  t.deuda_en_mora
FROM (
  SELECT
    tercero,
    id_tercero,
    SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
  FROM zeffi_cuentas_por_cobrar
  WHERE estado_cxc = 'Pendiente de cobro en mora'
  GROUP BY tercero, id_tercero
  ORDER BY deuda_en_mora DESC
  LIMIT 5
) A
```
**groq-llama** (OK / 2 filas / 16613ms):
```sql
SELECT
  (SELECT SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) FROM zeffi_cuentas_por_cobrar WHERE estado_cxc = 'Pendiente de cobro en mora') AS total_cartera_vencida,
  t.tercero AS cliente,
  t.id_tercero AS id_cliente,
  t.deuda_en_mora
FROM (
  SELECT
    tercero,
    id_tercero,
    SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
  FROM zeffi_cuentas_por_cobrar
  WHERE estado_cxc = 'Pendiente de cobro en mora'
  GROUP BY tercero, id_tercero
  ORDER BY deuda_en_mora DESC
  LIMIT 5
) A
```
**gpt-oss-120b** (OK / 2 filas / 18287ms):
```sql
SELECT
  (SELECT SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) FROM zeffi_cuentas_por_cobrar WHERE estado_cxc = 'Pendiente de cobro en mora') AS total_cartera_vencida,
  t.tercero AS cliente,
  t.id_tercero AS id_cliente,
  t.deuda_en_mora
FROM (
  SELECT
    tercero,
    id_tercero,
    SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
  FROM zeffi_cuentas_por_cobrar
  WHERE estado_cxc = 'Pendiente de cobro en mora'
  GROUP BY tercero, id_tercero
  ORDER BY deuda_en_mora DESC
  LIMIT 5
) A
```
**cerebras-llama** (OK / 2 filas / 17712ms):
```sql
SELECT
  (SELECT SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) FROM zeffi_cuentas_por_cobrar WHERE estado_cxc = 'Pendiente de cobro en mora') AS total_cartera_vencida,
  t.tercero AS cliente,
  t.id_tercero AS id_cliente,
  t.deuda_en_mora
FROM (
  SELECT
    tercero,
    id_tercero,
    SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
  FROM zeffi_cuentas_por_cobrar
  WHERE estado_cxc = 'Pendiente de cobro en mora'
  GROUP BY tercero, id_tercero
  ORDER BY deuda_en_mora DESC
  LIMIT 5
) A
```

#### SQL-05 — Stock inventario
**Pregunta:** ¿Cuánto stock tenemos actualmente de productos terminados?

**gemini-flash** (OK / 2 filas / 7640ms):
```sql
SELECT
  SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
  AND vigencia = 'Vigente';
```
**gemini-flash-lite** (NO_SQL / 2 filas / 4257ms):
```sql
(sin SQL)
```
**groq-llama** (OK / 2 filas / 12419ms):
```sql
SELECT
    SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
    AND vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 17184ms):
```sql
SELECT 
    COUNT(*) AS cantidad_productos_terminados,
    SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_unidades,
    SUM(CAST(stock_total_empresa AS DECIMAL(15,2)) * CAST(costo_promedio AS DECIMAL(15,2))) AS valor_total_costo_promedio
FROM zeffi_inventario 
WHERE vigencia = 'Vigente'
    AND categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
    AND gestion_de_stock = 'Sí'
    AND CAST(stock_total_empresa AS DECIMAL(15,2)) > 0;
```
**cerebras-llama** (OK / 2 filas / 14826ms):
```sql
SELECT 
    SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados,
    COUNT(*) AS cantidad_productos_terminados
FROM zeffi_inventario 
WHERE vigencia = 'Vigente'
    AND categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
    AND CAST(stock_total_empresa AS DECIMAL(15,2)) > 0;
```

#### SQL-06 — Órdenes producción vigentes
**Pregunta:** ¿Cuántas órdenes de producción están vigentes y cuál es su valor total?

**gemini-flash** (OK / 2 filas / 8566ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**gemini-flash-lite** (OK / 2 filas / 7171ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**groq-llama** (OK / 2 filas / 12527ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 13487ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**cerebras-llama** (OK / 2 filas / 13716ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```

#### SQL-07 — Remisiones pendientes
**Pregunta:** ¿Cuánto hay en remisiones pendientes de facturar y cuántas son?

**gemini-flash** (OK / 2 filas / 9471ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**gemini-flash-lite** (OK / 2 filas / 9740ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**groq-llama** (OK / 2 filas / 16548ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**gpt-oss-120b** (OK / 2 filas / 21254ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**cerebras-llama** (OK / 2 filas / 17191ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```

#### SQL-08 — Consignación activa
**Pregunta:** ¿Cuánto valor hay en consignación activa (órdenes de venta vigentes)?

**gemini-flash** (OK / 2 filas / 11047ms):
```sql
SELECT
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_consignacion_sin_iva,
  SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_consignacion_total
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**gemini-flash-lite** (OK / 2 filas / 14579ms):
```sql
SELECT
  SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_consignacion_activa
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**groq-llama** (OK / 2 filas / 19435ms):
```sql
SELECT
  COUNT(*) AS num_ordenes,
  SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
  SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_total_bruto
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 18746ms):
```sql
SELECT
    COUNT(*) AS numero_ordenes,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
    SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_total_bruto,
    SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_subtotal_sin_iva
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente'
    AND fecha_de_anulacion IS NULL;
```
**cerebras-llama** (OK / 2 filas / 20517ms):
```sql
SELECT 
    COUNT(*) AS numero_ordenes,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
    SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_sin_iva
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```

#### SQL-09 — Comparativo año anterior
**Pregunta:** ¿Cómo van las ventas de enero-marzo 2026 vs el mismo período de 2025?

**gemini-flash** (OK / 2 filas / 17260ms):
```sql
SELECT
  SUBSTRING(mes, 1, 4) AS anio,
  SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
  SUM(fin_devoluciones) AS devoluciones,
  SUM(fin_ingresos_netos) AS ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03', '2025-01', '2025-02', '2025-03')
GROUP BY anio
ORDER BY anio DESC;
```
**gemini-flash-lite** (OK / 2 filas / 14188ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos,
  mes_ant_ventas_netas,
  mes_ant_var_ventas_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03', '2025-01', '2025-02', '2025-03')
ORDER BY mes DESC;
```
**groq-llama** (OK / 2 filas / 26080ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 1) AS margen_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2025-01', '2025-02', '2025-03', '2026-01', '2026-02', '2026-03')
ORDER BY mes DESC;
```
**gpt-oss-120b** (OK / 2 filas / 26333ms):
```sql
SELECT
    '2025' AS periodo,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(fin_devoluciones) AS devoluciones,
    SUM(fin_ingresos_netos) AS ingresos_netos,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 1) AS margen_promedio_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2025-01', '2025-02', '2025-03')
UNION ALL
SELECT
    '2026' AS periodo,
    SUM(fin_ventas_netas_sin_iva
```
**cerebras-llama** (OK / 2 filas / 39352ms):
```sql
SELECT
    '2025 (ene-mar)' AS periodo,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(fin_devoluciones) AS devoluciones,
    SUM(fin_ingresos_netos) AS ingresos_netos,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos,
    CASE 
        WHEN SUM(vol_num_facturas) > 0 
        THEN SUM(fin_ventas_netas_sin_iva) / SUM(vol_num_facturas)
        ELSE 0
    END AS ticket_promedio,
    SUM(cto_costo_total) AS costo_total,
    SUM(cto_u
```

#### SQL-10 — Margen por canal
**Pregunta:** ¿Cuál es el margen promedio de cada canal de venta en los últimos 3 meses?

**gemini-flash** (OK / 2 filas / 11011ms):
```sql
SELECT
  canal,
  ROUND(AVG(cto_margen_utilidad_pct) * 100, 1) AS margen_promedio_pct
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN (
  DATE_FORMAT(CURDATE(), '%Y-%m'),
  DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m'),
  DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), '%Y-%m')
)
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```
**gemini-flash-lite** (OK / 2 filas / 10530ms):
```sql
SELECT
  canal,
  ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```
**groq-llama** (OK / 2 filas / 24209ms):
```sql
SELECT
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    COUNT(DISTINCT mes) AS meses_con_datos,
    SUM(fin_ventas_netas_sin_iva) AS ventas_totales_sin_iva
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
HAVING SUM(fin_ventas_netas_sin_iva) > 0
ORDER BY margen_promedio_pct DESC;
```
**gpt-oss-120b** (OK / 2 filas / 21417ms):
```sql
SELECT
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```
**cerebras-llama** (OK / 2 filas / 23968ms):
```sql
SELECT 
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_totales,
    SUM(cto_utilidad_bruta) AS utilidad_bruta_total,
    SUM(vol_num_facturas) AS total_facturas
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```

#### SQL-11 — Clientes nuevos
**Pregunta:** ¿Cuántos clientes nuevos compraron por primera vez en lo que va del 2026?

**gemini-flash** (NO_SQL / 2 filas / 5626ms):
```sql
(sin SQL)
```
**gemini-flash-lite** (NO_SQL / 2 filas / 6219ms):
```sql
(sin SQL)
```
**groq-llama** (OK / 2 filas / 17109ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente) AS clientes_nuevos_2026
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```
**gpt-oss-120b** (NO_SQL / 2 filas / 6297ms):
```sql
(sin SQL)
```
**cerebras-llama** (OK / 2 filas / 19308ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente) AS clientes_nuevos_2026
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```

#### SQL-12 — Compras materia prima
**Pregunta:** ¿Cuánto hemos comprado en materia prima en lo que va del 2026?

**gemini-flash** (OK / 2 filas / 21178ms):
```sql
SELECT
  SUM(CAST(fcd.precio_bruto_total AS DECIMAL(15,2)) - CAST(fcd.descuento_total AS DECIMAL(15,2))) AS total_comprado_materia_prima_sin_iva
FROM zeffi_facturas_compra_detalle fcd
JOIN zeffi_facturas_compra_encabezados fce ON fcd.id_factura = fce.id_numeracion
JOIN zeffi_inventario zi ON fcd.cod_articulo = zi.cod_barras
JOIN zeffi_categorias_articulos zca ON zi.categoria = zca.nombre
WHERE DATE_FORMAT(fce.fecha_de_creacion, '%Y') = '2026'
  AND fce.fecha_de_anulacion IS NULL
  AND fcd.vigenc
```
**gemini-flash-lite** (OK / 2 filas / 8666ms):
```sql
SELECT
  SUM(CAST(fcd.precio_neto_total AS DECIMAL(15,2))) AS total_compras_materia_prima
FROM zeffi_facturas_compra_detalle fcd
JOIN zeffi_facturas_compra_encabezados fce ON fcd.id_factura = fce.id_numeracion
JOIN zeffi_categorias_articulos ca ON fcd.cod_articulo = ca.id
WHERE DATE_FORMAT(fce.fecha_de_creacion, '%Y') = '2026'
  AND (ca.nombre LIKE 'T01%' OR ca.nombre LIKE 'T03%');
```
**groq-llama** (OK / 2 filas / 13779ms):
```sql
SELECT
    COUNT(*) AS num_facturas_compra,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS total_compras_neto,
    SUM(CAST(subtotal AS DECIMAL(15,2))) AS total_compras_sin_iva
FROM zeffi_facturas_compra_encabezados
WHERE DATE_FORMAT(fecha_de_creacion, '%Y') = '2026'
    AND fecha_de_anulacion IS NULL;
```
**gpt-oss-120b** (OK / 2 filas / 14052ms):
```sql
SELECT
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS total_compras_neto,
    SUM(CAST(subtotal AS DECIMAL(15,2))) AS total_compras_sin_iva,
    COUNT(*) AS numero_facturas
FROM zeffi_facturas_compra_encabezados
WHERE DATE_FORMAT(fecha_de_creacion, '%Y') = '2026'
    AND fecha_de_anulacion IS NULL;
```
**cerebras-llama** (ERROR / 0 filas / 15951ms):
```sql
SELECT
    SUM(CAST(fc.subtotal AS DECIMAL(15,2))) AS compras_materia_prima_sin_iva,
    SUM(CAST(fc.total_neto AS DECIMAL(15,2))) AS compras_materia_prima_con_iva,
    COUNT(DISTINCT fc.id_numeracion) AS num_facturas_compra
FROM zeffi_facturas_compra_encabezados fc
JOIN zeffi_facturas_compra_detalle fcd ON fc.id_numeracion = fcd.id_factura
JOIN zeffi_categorias_articulos ca ON fcd.categoria_articulo = ca.nombre
WHERE DATE_FORMAT(fc.fecha_de_creacion, '%Y') = '2026'
    AND fc.fecha_de_anulacion
```
> ⚠️ Error: Error ejecutando SQL: (1054, "Unknown column 'fcd.categoria_articulo' in 'ON'")

#### SQL-13 — Top 5 productos más rentables
**Pregunta:** ¿Cuáles son los 5 productos con mayor margen bruto en lo que va del 2026?

**gemini-flash** (OK / 2 filas / 11188ms):
```sql
SELECT
  nombre AS nombre_producto,
  ROUND(AVG(CAST(cto_margen_utilidad_pct AS DECIMAL(15,2))) * 100, 1) AS margen_bruto_promedio_pct
FROM resumen_ventas_facturas_producto_mes
WHERE mes LIKE '2026-%'
GROUP BY cod_articulo, nombre
ORDER BY margen_bruto_promedio_pct DESC
LIMIT 5;
```
**gemini-flash-lite** (OK / 2 filas / 8786ms):
```sql
SELECT
  d.cod_articulo,
  d.descripcion_articulo,
  SUM(CAST(d.utilidad_total_costo_promedio AS DECIMAL(15,2))) AS margen_bruto_total,
  ROUND(AVG(CAST(d.utilidad_total_costo_promedio AS DECIMAL(15,2))) / AVG(CAST(d.precio_bruto_total AS DECIMAL(15,2)) - CAST(d.descuento_total AS DECIMAL(15,2))) * 100, 2) AS margen_promedio_pct
FROM zeffi_facturas_venta_detalle d
WHERE DATE_FORMAT(d.fecha_creacion_factura, '%Y') = '2026'
  AND d.vigencia_factura = 'Vigente'
GROUP BY d.cod_articulo, d.descripcio
```
**groq-llama** (OK / 2 filas / 16968ms):
```sql
SELECT
    cod_articulo,
    nombre,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_bruto_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_totales_sin_iva,
    SUM(vol_unidades_vendidas) AS unidades_vendidas
FROM resumen_ventas_facturas_producto_mes
WHERE mes >= '2026-01'
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY cod_articulo, nombre
HAVING SUM(fin_ventas_netas_sin_iva) > 0
ORDER BY margen_bruto_promedio_pct DESC
LIMIT 5;
```
**gpt-oss-120b** (OK / 2 filas / 17495ms):
```sql
SELECT
    cod_articulo,
    nombre,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(vol_unidades_vendidas) AS unidades_vendidas,
    SUM(cto_utilidad_bruta) AS utilidad_bruta_total
FROM resumen_ventas_facturas_producto_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY cod_articulo, nombre
HAVING SUM(fin_ventas_netas_sin_iva) > 0
ORDER BY margen_promedio_pct 
```
**cerebras-llama** (OK / 2 filas / 18278ms):
```sql
SELECT 
    cod_articulo,
    nombre,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_totales,
    SUM(cto_utilidad_bruta) AS utilidad_bruta_total,
    SUM(vol_unidades_vendidas) AS unidades_vendidas
FROM resumen_ventas_facturas_producto_mes
WHERE mes >= '2026-01'
    AND fin_ventas_netas_sin_iva > 0
GROUP BY cod_articulo, nombre
HAVING margen_promedio_pct IS NOT NULL
ORDER BY margen_promedio_pct DESC
LIMIT 5;
```

#### SQL-14 — Evolución mensual ventas 6 meses
**Pregunta:** Dame la evolución mes a mes de ventas netas en los últimos 6 meses

**gemini-flash** (OK / 2 filas / 12908ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m')
ORDER BY mes ASC;
```
**gemini-flash-lite** (OK / 2 filas / 10966ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m')
ORDER BY mes DESC;
```
**groq-llama** (OK / 2 filas / 20846ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 1) AS margen_pct
FROM resumen_ventas_facturas_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m')
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
ORDER BY mes DESC;
```
**gpt-oss-120b** (OK / 2 filas / 21109ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 1) AS margen_promedio_pct
FROM resumen_ventas_facturas_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m')
ORDER BY mes DESC
```
**cerebras-llama** (OK / 2 filas / 25175ms):
```sql
SELECT 
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    vol_num_facturas,
    cli_clientes_activos,
    ROUND(cto_margen_utilidad_pct * 100, 2) AS margen_pct
FROM resumen_ventas_facturas_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), '%Y-%m')
ORDER BY mes DESC
```

#### SQL-15 — Clientes que compraron este año pero no el pasado
**Pregunta:** ¿Cuántos clientes compraron en 2026 pero no compraron nada en 2025?

**gemini-flash** (OK / 2 filas / 13293ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente)
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```
**gemini-flash-lite** (OK / 2 filas / 8535ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente)
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```
**groq-llama** (OK / 2 filas / 18841ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente) AS clientes_2026_no_2025
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```
**gpt-oss-120b** (OK / 2 filas / 18787ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente) AS clientes_2026_no_2025
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```
**cerebras-llama** (OK / 2 filas / 19384ms):
```sql
SELECT
  COUNT(DISTINCT f2026.id_cliente) AS clientes_2026_no_2025
FROM zeffi_facturas_venta_encabezados f2026
WHERE DATE_FORMAT(f2026.fecha_de_creacion, '%Y') = '2026'
  AND f2026.fecha_de_anulacion IS NULL
  AND f2026.id_cliente NOT IN (
    SELECT DISTINCT f2025.id_cliente
    FROM zeffi_facturas_venta_encabezados f2025
    WHERE DATE_FORMAT(f2025.fecha_de_creacion, '%Y') = '2025'
      AND f2025.fecha_de_anulacion IS NULL
  );
```

#### SQL-16 — Canal más rentable vs año anterior
**Pregunta:** ¿Qué canal tuvo el mayor crecimiento en ventas comparando enero-marzo 2026 vs enero-marzo 2025?

**gemini-flash** (OK / 2 filas / 13973ms):
```sql
SELECT
  canal,
  SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva_2026,
  SUM(year_ant_ventas_netas) AS ventas_netas_sin_iva_2025,
  ROUND(
    (SUM(fin_ventas_netas_sin_iva) - SUM(year_ant_ventas_netas)) / NULLIF(SUM(year_ant_ventas_netas), 0) * 100,
    2
  ) AS crecimiento_porcentaje
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03')
GROUP BY canal
ORDER BY crecimiento_porcentaje DESC
LIMIT 1;
```
**gemini-flash-lite** (OK / 2 filas / 10308ms):
```sql
SELECT
  canal,
  SUM(CASE WHEN mes LIKE '2026-%' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2026,
  SUM(CASE WHEN mes LIKE '2025-%' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2025,
  (SUM(CASE WHEN mes LIKE '2026-%' THEN fin_ventas_netas_sin_iva ELSE 0 END) - SUM(CASE WHEN mes LIKE '2025-%' THEN fin_ventas_netas_sin_iva ELSE 0 END)) AS diferencia_ventas,
  CASE
    WHEN SUM(CASE WHEN mes LIKE '2025-%' THEN fin_ventas_netas_sin_iva ELSE 0 END) = 0 THEN NULL
    ELSE ((SUM(CASE 
```
**groq-llama** (NO_SQL / 0 filas / 31584ms):
```sql
(sin SQL)
```
> ⚠️ Error: Error generando SQL: HTTP 429: {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkjheyawe8w9je7jzq4j91n4` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99438, Requested 36501. Please try again in 8h37m31.296s. Need more tokens? Upgrade to Dev Tier today at h
**gpt-oss-120b** (OK / 2 filas / 27009ms):
```sql
SELECT
    canal,
    SUM(CASE WHEN mes IN ('2025-01', '2025-02', '2025-03') THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2025,
    SUM(CASE WHEN mes IN ('2026-01', '2026-02', '2026-03') THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2026,
    SUM(CASE WHEN mes IN ('2026-01', '2026-02', '2026-03') THEN fin_ventas_netas_sin_iva ELSE 0 END) -
    SUM(CASE WHEN mes IN ('2025-01', '2025-02', '2025-03') THEN fin_ventas_netas_sin_iva ELSE 0 END) AS crecimiento_absoluto,
    CASE 
        W
```
**cerebras-llama** (OK / 2 filas / 25666ms):
```sql
SELECT 
    canal,
    SUM(CASE WHEN mes BETWEEN '2026-01' AND '2026-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2026,
    SUM(CASE WHEN mes BETWEEN '2025-01' AND '2025-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_2025,
    SUM(CASE WHEN mes BETWEEN '2026-01' AND '2026-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) -
    SUM(CASE WHEN mes BETWEEN '2025-01' AND '2025-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS crecimiento_absoluto,
    CASE 
        WHEN SUM(CASE WHEN m
```

#### SQL-17 — Productos sin movimiento
**Pregunta:** ¿Qué productos tienen stock en inventario pero no han tenido venta en los últimos 60 días?

**gemini-flash** (OK / 2 filas / 11277ms):
```sql
SELECT
  i.cod_barras AS codigo_articulo,
  i.nombre AS nombre_articulo,
  CAST(i.stock_total_empresa AS DECIMAL(15,2)) AS stock_actual
FROM zeffi_inventario i
WHERE CAST(i.stock_total_empresa AS DECIMAL(15,2)) > 0
  AND i.vigencia = 'Vigente'
  AND i.categoria IN ("TPT.01. VENTA AGROECOLOGICOS VARIOS", "TPT.02. VENTA OTROS")
  AND i.cod_barras NOT IN (
    SELECT DISTINCT d.cod_articulo
    FROM zeffi_facturas_venta_detalle d
    WHERE DATE(d.fecha_creacion_factura) >= DATE_SUB(CURDATE(), INTER
```
**gemini-flash-lite** (OK / 2 filas / 27007ms):
```sql
SELECT
  i.nombre AS nombre_producto,
  i.referencia,
  i.stock_total_empresa,
  MAX(fvd.fecha_creacion_factura) AS ultima_venta
FROM zeffi_inventario i
LEFT JOIN zeffi_facturas_venta_detalle fvd
  ON i.id = fvd.cod_articulo
WHERE
  i.gestion_de_stock = 'Sí' AND CAST(i.stock_total_empresa AS DECIMAL(15, 2)) > 0
  AND i.vigencia = 'Vigente'
GROUP BY
  i.id,
  i.nombre,
  i.referencia,
  i.stock_total_empresa
HAVING
  MAX(fvd.fecha_creacion_factura) IS NULL OR STR_TO_DATE(MAX(fvd.fecha_creacion_fa
```
**groq-llama** (OK / 2 filas / 24113ms):
```sql
SELECT 
    i.cod_barras AS codigo_articulo,
    i.nombre,
    i.referencia,
    i.categoria,
    i.marca,
    CAST(i.stock_total_empresa AS DECIMAL(15,2)) AS stock_total,
    i.gestion_de_stock,
    i.stock_minimo,
    i.stock_optimo,
    MAX(f.fecha_creacion_factura) AS ultima_venta_fecha
FROM zeffi_inventario i
LEFT JOIN (
    SELECT DISTINCT cod_articulo, fecha_creacion_factura 
    FROM zeffi_facturas_venta_detalle 
    WHERE vigencia_factura = 'Vigente'
        AND DATE(fecha_creacion_fact
```
**gpt-oss-120b** (OK / 2 filas / 33121ms):
```sql
SELECT 
    i.cod_barras AS codigo,
    i.nombre,
    i.referencia,
    i.categoria,
    i.marca,
    CAST(i.stock_total_empresa AS DECIMAL(15,2)) AS stock_total,
    CAST(i.costo_promedio AS DECIMAL(15,2)) AS costo_promedio,
    CAST(i.precio_precio_publico_sugerido AS DECIMAL(15,2)) AS precio_publico
FROM zeffi_inventario i
WHERE i.vigencia = 'Vigente'
    AND CAST(i.stock_total_empresa AS DECIMAL(15,2)) > 0
    AND i.cod_barras NOT IN (
        SELECT DISTINCT d.cod_articulo
        FROM zeff
```
**cerebras-llama** (OK / 2 filas / 27121ms):
```sql
SELECT 
    i.cod_barras AS codigo,
    i.nombre,
    i.referencia,
    i.categoria,
    i.marca,
    CAST(i.stock_total_empresa AS DECIMAL(15,2)) AS stock_total,
    i.gestion_de_stock,
    i.stock_minimo,
    i.stock_optimo,
    MAX(f.fecha_creacion_factura) AS ultima_venta_fecha
FROM zeffi_inventario i
LEFT JOIN zeffi_facturas_venta_detalle f ON i.cod_barras = f.cod_articulo 
    AND f.vigencia_factura = 'Vigente'
    AND f.fecha_creacion_factura >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
WHERE 
```

#### SQL-18 — Ticket promedio por canal
**Pregunta:** ¿Cuál es el ticket promedio de venta por canal en febrero y marzo 2026?

**gemini-flash** (OK / 2 filas / 12704ms):
```sql
SELECT
  mes,
  canal,
  vol_ticket_promedio
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-02', '2026-03')
ORDER BY mes ASC, canal ASC;
```
**gemini-flash-lite** (OK / 2 filas / 10944ms):
```sql
SELECT
  canal,
  SUM(fin_ventas_netas_sin_iva) / SUM(vol_num_facturas) AS ticket_promedio
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-02', '2026-03')
GROUP BY canal
ORDER BY ticket_promedio DESC;
```
**groq-llama** (OK / 2 filas / 23533ms):
```sql
SELECT
    canal,
    mes,
    vol_ticket_promedio AS ticket_promedio,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    vol_num_facturas AS numero_facturas
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-02', '2026-03')
    AND fin_ventas_netas_sin_iva > 0
ORDER BY mes, canal;
```
**gpt-oss-120b** (OK / 2 filas / 27127ms):
```sql
SELECT
    canal,
    SUM(CASE WHEN mes = '2026-02' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_febrero,
    SUM(CASE WHEN mes = '2026-02' THEN vol_num_facturas ELSE 0 END) AS facturas_febrero,
    CASE 
        WHEN SUM(CASE WHEN mes = '2026-02' THEN vol_num_facturas ELSE 0 END) > 0
        THEN SUM(CASE WHEN mes = '2026-02' THEN fin_ventas_netas_sin_iva ELSE 0 END) / 
             SUM(CASE WHEN mes = '2026-02' THEN vol_num_facturas ELSE 0 END)
        ELSE 0
    END AS ticket_promedio_
```
**cerebras-llama** (OK / 2 filas / 25076ms):
```sql
SELECT 
    canal,
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    vol_num_facturas,
    ROUND(fin_ventas_netas_sin_iva / NULLIF(vol_num_facturas, 0), 2) AS ticket_promedio
FROM resumen_ventas_facturas_canal_mes
WHERE mes IN ('2026-02', '2026-03')
    AND fin_ventas_netas_sin_iva > 0
    AND vol_num_facturas > 0
ORDER BY canal, mes DESC;
```

---
## FASE 2 — Calidad de Respuesta

| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |
|---|---|---|---|---|---|
| SQL-01 | Ventas mes actual | OK / 10993ms | OK / 7140ms | OK / 12396ms | OK / 20566ms | OK / 11598ms |
| SQL-02 | Top canales febrero | OK / 10004ms | OK / 10935ms | OK / 12261ms | OK / 23459ms | OK / 12133ms |
| SQL-03 | Producto más vendido | OK / 10400ms | OK / 10354ms | OK / 10986ms | OK / 18434ms | OK / 11702ms |
| SQL-04 | Cartera vencida | OK / 11597ms | OK / 9432ms | OK / 11791ms | OK / 23689ms | OK / 12375ms |
| SQL-05 | Stock inventario | CORTA / 7768ms | CORTA / 8370ms | CORTA / 10625ms | OK / 16224ms | OK / 10580ms |
| SQL-06 | Órdenes producción vigentes | OK / 8446ms | CORTA / 8588ms | OK / 9676ms | OK / 15996ms | OK / 9346ms |
| CONV-01 | Estrategia precio | OK / 7324ms | OK / 3870ms | OK / 9928ms | OK / 3385ms | OK / 6397ms |
| CONV-02 | Redacción email | OK / 4780ms | OK / 2692ms | OK / 5023ms | OK / 6259ms | OK / 5854ms |
| CONV-03 | Explicación sistema | OK / 4974ms | OK / 3842ms | OK / 5675ms | OK / 16721ms | OK / 6767ms |
| CONV-04 | Redacción propuesta comercial | OK / 6088ms | OK / 2876ms | OK / 6480ms | OK / 9158ms | OK / 6427ms |
| CONV-05 | Análisis estratégico | OK / 19716ms | OK / 6483ms | OK / 13732ms | OK / 26508ms | OK / 14047ms |

### Latencia y costo promedio — Respuesta

| Agente | Latencia prom (ms) | Costo total USD | Resp OK% |
|---|---|---|---|
| gemini-flash | 9571 | $0.043819 | 92% |
| gemini-flash-lite | 7235 | $0.020597 | 85% |
| groq-llama | 9957 | $0.042823 | 92% |
| gpt-oss-120b | 16675 | $0.090057 | 100% |
| cerebras-llama | 10062 | $0.043192 | 100% |

### Respuestas completas por query y agente


#### SQL-01 — Ventas mes actual
**Pregunta:** ¿Cuánto vendimos en total este mes de marzo 2026?

**gemini-flash** (OK / 10993ms):
> ¡Hola!

Para este mes de marzo de 2026, las ventas netas sin IVA ascienden a **$8,667,799.00**.

Es importante tener en cuenta que hemos tenido **$1,894,618.00** en devoluciones. Por lo tanto, los ingresos netos reales del mes, después de considerar las devoluciones, son de **$6,773,181.00**.
**gemini-flash-lite** (OK / 7140ms):
> ¡Hola! Claro, te doy el resumen de ventas de marzo 2026:

*   **Ventas netas sin IVA:** $8,667,799.00
*   **Devoluciones:** $1,894,618.00
*   **Ingresos netos:** $6,773,181.00

Esto significa que, después de descontar las devoluciones, los ingresos reales de marzo fueron de $6,773,181.00.
**groq-llama** (OK / 12396ms):
> ¡Hola!

Para el mes de **marzo de 2026**, las ventas totales de Origen Silvestre fueron las siguientes:

*   **Ventas netas sin IVA:** $8,667,799.00
*   **Devoluciones:** $1,894,618.00
*   **Ingresos netos (después de devoluciones):** $6,773,181.00

Como puedes ver, las devoluciones tuvieron un impacto significativo este mes.
**gpt-oss-120b** (OK / 20566ms):
> Según los datos de marzo 2026:

**Ventas netas sin IVA:** $8.667.799  
**Devoluciones:** $1.894.618  
**Ingresos netos:** $6.773.181

**Interpretación:**  
Las ventas netas del mes fueron de **$8,7 millones**, pero hubo devoluciones por **$1,9 millones**, lo que deja unos ingresos netos de **$6,8 millones**. Las devoluciones representan un 22 % del total vendido, un porcentaje alto que convendría revisar para entender si hay algún patrón (productos, clientes o canales específicos) que esté generando tantas devoluciones.
**cerebras-llama** (OK / 11598ms):
> ¡Hola! Con gusto te doy el resumen de ventas de marzo de 2026 hasta la fecha.

Las **ventas netas sin IVA** de marzo de 2026 han sido de **$8.667.799**.

Sin embargo, hemos tenido **devoluciones** por **$1.894.618**.

Esto significa que los **ingresos netos reales** para el mes de marzo de 2026 son de **$6.773.181**.

Es importante tener en cuenta el impacto de las devoluciones en el ingreso final.


#### SQL-02 — Top canales febrero
**Pregunta:** ¿Cuál fue el top 3 de canales de venta en febrero 2026 por valor neto?

**gemini-flash** (OK / 10004ms):
> ¡Hola!

Con gusto te comparto el top 3 de canales de venta por valor neto sin IVA para febrero de 2026:

```
Canal                                         | Ventas Netas sin IVA
----------------------------------------------|---------------------
1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc | $2,993,795.00
1.3. Mercado Saludable                        | $2,789,454.00
1.7. Restaurantes, tiendas, reposterias y cafes afines | $1,498,235.00
```

Como puedes ver, los mercados y tiendas saludables fueron los canales más fuertes en febrero. Es interesante notar cómo los restaurantes y cafés también tuvieron una participación significativa.

¿Te gustaría analizar algún otro canal o período?
**gemini-flash-lite** (OK / 10935ms):
> ¡Claro! Aquí tienes el top 3 de canales de venta en febrero 2026 por valor neto, según los datos que tengo:

| Canal                                             | Ventas Netas sin IVA |
| :------------------------------------------------ | :------------------- |
| 1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc | $2,993,795.00        |
| 1.3. Mercado Saludable                            | $2,789,454.00        |
| 1.7. Restaurantes, tiendas, reposterias y cafes afines | $1,498,235.00        |

Estos fueron los canales que generaron más ingresos netos sin IVA durante febrero.
**groq-llama** (OK / 12261ms):
> ¡Hola!

Claro, aquí tienes el top 3 de canales de venta por valor neto sin IVA para **febrero de 2026**:

```
Canal                                            | Ventas Netas sin IVA
-------------------------------------------------|---------------------
1.5. Mercados, agropecuarias, Fruvers, graneros  | $2,993,795.00
1.3. Mercado Saludable                           | $2,789,454.00
1.7. Restaurantes, tiendas, reposterias y cafes  | $1,498,235.00
```
**gpt-oss-120b** (OK / 23459ms):
> Según los datos de febrero 2026, el **top 3 de canales de venta por valor neto** (ventas netas sin IVA) fue:

| Canal | Ventas netas sin IVA |
|-------|----------------------|
| **1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc** | $2.993.795 |
| **1.3. Mercado Saludable** | $2.789.454 |
| **1.7. Restaurantes, tiendas, reposterías y cafés afines** | $1.498.235 |

**Interpretación:**  
El canal **minorista de mercados y agropecuarias (1.5)** lideró con casi **$3 millones**, seguido muy de cerca por **Mercado Saludable (1.3)** con **$2,8 millones**. Ambos representan el grueso de las ventas minoristas de OS en ese mes. El tercer lugar lo ocupan **restaurantes y tiendas afines (1.7)** con **$1,5 millones**, mostrando una base diversa de clientes del sector gastronómico.

Estos tr
**cerebras-llama** (OK / 12133ms):
> ¡Claro que sí! Con gusto te comparto el top 3 de canales de venta por valor neto sin IVA para febrero de 2026:

```
Canal                                               | Ventas Netas sin IVA
----------------------------------------------------|---------------------
1.5. Mercados, agropecuarias, Fruvers, graneros     | $2.993.795
1.3. Mercado Saludable                              | $2.789.454
1.7. Restaurantes, tiendas, reposterias y cafes afines | $1.498.235
```

Como puedes ver, los mercados y agropecuarias fueron nuestro canal más fuerte en febrero, seguidos de cerca por los mercados saludables. Los restaurantes y cafés también tuvieron una participación importante.


#### SQL-03 — Producto más vendido
**Pregunta:** ¿Cuál fue el producto más vendido en unidades durante 2025?

**gemini-flash** (OK / 10400ms):
> ¡Hola!

El producto más vendido en unidades durante 2025 fue la **Tableta Chocolate 73p 50 grs CPM**, con un total de **563 unidades** vendidas.
**gemini-flash-lite** (OK / 10354ms):
> ¡Hola! El producto más vendido en unidades durante 2025 fue:

*   **Tableta Chocolate 73p 50 grs CPM** con **563 unidades** vendidas.
**groq-llama** (OK / 10986ms):
> ¡Hola!

Según los datos que tengo, el producto más vendido en unidades durante el año **2025** fue:

*   **Tableta Chocolate 73p 50 grs CPM** con **563 unidades** vendidas.
**gpt-oss-120b** (OK / 18434ms):
> Según los datos de 2025, el **producto más vendido en unidades** fue:

**Tableta Chocolate 73p 50 grs CPM** → **563 unidades**

**Interpretación:**  
Este producto de chocolate de 50 gramos fue claramente el de mayor rotación. Su formato pequeño, accesible y de consumo rápido lo convierte en un artículo de alta demanda constante, probablemente muy popular entre clientes directos y en puntos de venta minoristas.
**cerebras-llama** (OK / 11702ms):
> ¡Claro! Con los datos que tengo, el producto más vendido en unidades durante 2025 fue:

```
Producto                         | Unidades Vendidas
---------------------------------|------------------
Tableta Chocolate 73p 50 grs CPM | 563
```

La **Tableta Chocolate 73p 50 grs CPM** fue nuestro producto estrella en 2025, con un total de **563 unidades** vendidas. ¡Se ve que a nuestros clientes les encanta este chocolate!


#### SQL-04 — Cartera vencida
**Pregunta:** ¿Cuánto hay en cartera vencida actualmente y cuáles son los 5 clientes con más deuda?

**gemini-flash** (OK / 11597ms):
> ¡Hola!

Actualmente, tenemos un total de **$3,271,454.00** en cartera vencida.

Aquí te presento a los 5 clientes con la mayor deuda en mora:

```
Cliente                                       | Deuda en Mora
----------------------------------------------|--------------
INKAMPO - PORRAS ESLAVA KATHY ELIZABETH       | $715,713.00
COMERCIALIZADORA RAGESCO S.A.S. MERCANDU      | $603,960.00
KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA | $450,065.00
Nuestro - Giraldo Giraldo Maria Paula         | $352,039.00
EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN | $296,544.00
```

Es importante darle seguimiento a estos clientes para recuperar esos saldos. ¿Te gustaría que revisemos los días de mora de alguno en particular, o el historial de pagos?
**gemini-flash-lite** (OK / 9432ms):
> ¡Hola! Claro, te doy el detalle de la cartera vencida:

Actualmente, la **cartera vencida total es de $3,271,454.00**.

Los 5 clientes con mayor deuda en mora son:

| Cliente                                                              | Deuda en Mora |
| :------------------------------------------------------------------- | :------------ |
| INKAMPO - PORRAS ESLAVA KATHY ELIZABETH                              | $715,713.00   |
| COMERCIALIZADORA RAGESCO S.A.S. MERCANDU                               | $603,960.00   |
| KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA                        | $450,065.00   |
| Nuestro - Giraldo Giraldo Maria Paula                                | $352,039.00   |
| EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN                        | $296,544.00   |

Esper
**groq-llama** (OK / 11791ms):
> ¡Hola!

Con gusto te doy el estado de la cartera vencida. Es un tema importante al que debemos ponerle atención.

Actualmente, el **total de cartera vencida es de $3,271,454.00**.

Los 5 clientes con mayor deuda en mora son:

```
Cliente                                         | Deuda en Mora
------------------------------------------------|---------------
INKAMPO - PORRAS ESLAVA KATHY ELIZABETH         | $715,713.00
COMERCIALIZADORA RAGESCO S.A.S. MERCANDU        | $603,960.00
KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA | $450,065.00
Nuestro - Giraldo Giraldo Maria Paula           | $352,039.00
EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN | $296,544.00
```
**gpt-oss-120b** (OK / 23689ms):
> Según los datos actuales de cartera vencida:

**Total de cartera vencida:** **$3.271.454**

**Top 5 clientes con mayor deuda en mora:**

| Cliente | ID | Deuda en mora |
|---------|----|---------------|
| **INKAMPO - PORRAS ESLAVA KATHY ELIZABETH** | CC: 1102857179 | **$715.713** |
| **COMERCIALIZADORA RAGESCO S.A.S. MERCANDU** | NIT: 811032480 | **$603.960** |
| **KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA** | NIT: 66963651 | **$450.065** |
| **Nuestro - Giraldo Giraldo Maria Paula** | NIT: 1038416695 | **$352.039** |
| **EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN** | CC: 43477471 | **$296.544** |

**Interpretación:**  
La cartera vencida total es de **$3,27 millones**. El cliente con mayor deuda en mora es **INKAMPO** con **$715 mil**, que representa casi el 22% del total venci
**cerebras-llama** (OK / 12375ms):
> ¡Hola! Con gusto te doy la información sobre la cartera vencida.

Actualmente, tenemos un total de **$3.271.454** en cartera vencida.

Aquí tienes los 5 clientes con la mayor deuda en mora:

```
Cliente                                         | Deuda en Mora
------------------------------------------------|--------------
INKAMPO - PORRAS ESLAVA KATHY ELIZABETH         | $715.713
COMERCIALIZADORA RAGESCO S.A.S. MERCANDU        | $603.960
KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA | $450.065
Nuestro - Giraldo Giraldo Maria Paula           | $352.039
EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN | $296.544
```

Es importante que hagamos un seguimiento cercano a estos clientes para recuperar esos valores.


#### SQL-05 — Stock inventario
**Pregunta:** ¿Cuánto stock tenemos actualmente de productos terminados?

**gemini-flash** (CORTA / 7768ms):
> ¡Hola!

Actualmente, tenemos un stock total de **1,099 unidades** de productos terminados.
**gemini-flash-lite** (CORTA / 8370ms):
> ¡Hola! Actualmente tenemos **1,099.00 unidades** en stock de productos terminados.
**groq-llama** (CORTA / 10625ms):
> ¡Hola!

Actualmente, tenemos un total de **1,099.00 unidades** de productos terminados en stock.
**gpt-oss-120b** (OK / 16224ms):
> Según los datos actuales del inventario, tenemos **1.099 unidades** de productos terminados listos para la venta.

**Interpretación:**  
Este stock total incluye todos los artículos clasificados como productos terminados (categorías "TPT.01. VENTA AGROECOLOGICOS VARIOS" y "TPT.02. VENTA OTROS") y vigentes en el sistema. Es un buen punto de partida para evaluar la capacidad de despacho inmediato y planificar reposiciones o promociones.
**cerebras-llama** (OK / 10580ms):
> ¡Hola! Con gusto te doy el dato del stock actual de productos terminados.

Actualmente, tenemos un total de **1.099 unidades** de productos terminados en stock.


#### SQL-06 — Órdenes producción vigentes
**Pregunta:** ¿Cuántas órdenes de producción están vigentes y cuál es su valor total?

**gemini-flash** (OK / 8446ms):
> ¡Hola!

Actualmente, tenemos **1,089 órdenes de producción vigentes**.

El valor total de estas órdenes de producción activas asciende a **$3,706,220,397.00**.

Es una cifra bastante importante que representa todo lo que tenemos en proceso. ¿Te gustaría ver el detalle de alguna de estas órdenes o de algún producto en particular?
**gemini-flash-lite** (CORTA / 8588ms):
> ¡Hola! Tenemos 1,089 órdenes de producción vigentes, con un valor total de $3,706,220,397.00.
**groq-llama** (OK / 9676ms):
> ¡Hola!

Actualmente, tenemos **1,089 órdenes de producción vigentes**.

El valor total de estas órdenes de producción en curso es de **$3,706,220,397.00**.
**gpt-oss-120b** (OK / 15996ms):
> Según los datos actuales de producción:

**Órdenes de producción vigentes:** **1.089**  
**Valor total de las órdenes vigentes:** **$3.706.220.397**

**Interpretación:**  
Hay un volumen muy alto de órdenes de producción activas (más de mil), con un valor total que supera los **$3.700 millones**. Esto indica una cartera de producción muy amplia y de alto valor, lo que sugiere una capacidad operativa significativa o una acumulación de órdenes pendientes de procesar. Sería útil revisar la distribución por estado (ej. "Generada" vs. "Procesada") para entender cuántas están realmente en proceso y cuántas ya están terminadas.
**cerebras-llama** (OK / 9346ms):
> ¡Claro! Con gusto te doy el detalle de las órdenes de producción vigentes.

Actualmente, tenemos **1.089 órdenes de producción vigentes**, con un valor total de **$3.706.220.397**.

Es un volumen considerable de producción en curso, lo que indica una operación activa en nuestras plantas.


#### CONV-01 — Estrategia precio
**Pregunta:** ¿Qué diferencia hay entre la tarifa distribuidor y la tarifa pública en OS?

**gemini-flash** (OK / 7324ms):
> ¡Hola!

En Origen Silvestre, la diferencia principal entre la tarifa pública y las tarifas para distribuidores radica en el tipo de cliente al que están dirigidas y el nivel de precios que ofrecen:

```
Tarifa                  | Descripción
------------------------|----------------------------------------------------------
Precio Público Sugerido | Es el precio estándar, aplicado a clientes directos y al público general. Es la tarifa más alta.
Tarifas para Distribuidores | Son precios preferenciales y más bajos, asignados a negocios aliados y distribuidores. Estas tarifas varían según el volumen de compras históricas del cliente, como "+ de 200.000 en compras", "+ de 400.000 en compras", etc.
```

En resumen, la tarifa pública es para el consumidor final, mientras que las tarifas para dist
**gemini-flash-lite** (OK / 3870ms):
> ¡Hola! Claro, te explico la diferencia entre la tarifa de distribuidor y la tarifa pública en Origen Silvestre.

La principal diferencia radica en el **nivel de precios** y el **tipo de cliente** al que están dirigidas:

*   **Tarifa Pública Sugerida:** Esta es la tarifa estándar y más alta. Está pensada para clientes directos, el público general, y aquellos que compran al por menor sin un volumen significativo.
*   **Tarifa Distribuidor:** El término "distribuidor" no es una tarifa específica en sí misma, sino que se relaciona con las tarifas de mayor volumen. En OS, las tarifas que aplican para volúmenes de compra más altos, que podrían ser las que usaría un distribuidor o un negocio aliado importante, son:
    *   "+ de 400.000 en compras"
    *   "+ de 800.000 en compras"
    *   "+ de
**groq-llama** (OK / 9928ms):
> ¡Hola! Con gusto te explico la diferencia entre la tarifa pública y las tarifas que aplican a los distribuidores en Origen Silvestre.

En OS, la "tarifa pública" se refiere a nuestro **"Precio Publico Sugerido"**. Esta es la tarifa estándar para clientes directos y el público general.

Por otro lado, la "tarifa distribuidor" no es una única tarifa con ese nombre, sino que los distribuidores (que son clasificados como "Negocios aliados") se benefician de tarifas con descuentos progresivos, las cuales se asignan según su volumen de compra histórico. Estas tarifas ofrecen precios más favorables que el "Precio Publico Sugerido".

Aquí te presento las diferencias principales:

```
Tarifa                 | Descripción                                                                 | Aplicación p
**gpt-oss-120b** (OK / 3385ms):
> ¡Hola! 😊 En Origen Silvestre hay dos conceptos clave de precios que suelen generar dudas:

| Concepto | Qué es | A quién se aplica | Cómo se muestra en la factura |
|----------|--------|-------------------|------------------------------|
| **Precio Público Sugerido** | Es la tarifa base, sin descuentos especiales. | Clientes directos (personas naturales) y el público en general. | Columna **precio_precio_publico_sugerido**. |
| **Tarifa Distribuidor** (las tarifas “+ de 200 k”, “+ de 400 k”, “+ de 800 k”, “+ de 1.6 M”) | Son precios con descuento por volumen o por ser miembro/aliado. Cuanto mayor el historial de compras, mayor el descuento. | Distribuidores, mayoristas y aliados estratégicos (según su categoría A, B o C) o miembros OS. | Cada una tiene su propia columna, por ejemplo **prec
**cerebras-llama** (OK / 6397ms):
> ¡Hola! Con gusto te explico la diferencia entre lo que comúnmente se conoce como "tarifa distribuidor" y la "tarifa pública" en Origen Silvestre.

La "tarifa pública" se refiere a nuestro **"Precio Publico Sugerido"**, que es el precio estándar para clientes directos y el público general.

Por otro lado, lo que llamas "tarifa distribuidor" no es un nombre oficial de una única tarifa, sino que generalmente se refiere a las **tarifas especiales para clientes con un alto volumen de compras**, como los negocios aliados (que pueden incluir distribuidores). Estas tarifas ofrecen precios más competitivos que el "Precio Publico Sugerido", y se asignan según el volumen histórico de compra del cliente.

Aquí te muestro las tarifas relevantes para entender esta distinción:

```
Tarifa oficial        


#### CONV-02 — Redacción email
**Pregunta:** Redacta un mensaje corto de WhatsApp para avisar a un cliente que su pedido está listo para despacho.

**gemini-flash** (OK / 4780ms):
> ¡Claro! Aquí tienes una opción corta y directa para WhatsApp:

---

¡Hola [Nombre del Cliente]! 👋 Tenemos una excelente noticia: tu pedido de Origen Silvestre ya está listo y en camino para despacho. ¡Pronto lo tendrás contigo! ✨ Gracias por tu compra.
**gemini-flash-lite** (OK / 2692ms):
> ¡Hola [Nombre del cliente]! 👋

Buenas noticias, tu pedido está listo para ser despachado. Te avisaremos tan pronto como salga en ruta. ¡Gracias por tu compra! 😊
**groq-llama** (OK / 5023ms):
> ¡Claro! Aquí tienes una opción corta y directa:

"¡Hola [Nombre del Cliente]! 👋 Te informamos que tu pedido de OS ya está listo para despacho. ¡Pronto lo tendrás contigo!"
**gpt-oss-120b** (OK / 6259ms):
> ¡Hola [Nombre del cliente]! 😊

Te informamos que tu pedido de Origen Silvestre ya está listo para ser despachado. 🚚

En breve nos pondremos en contacto contigo para coordinar la entrega.

¡Gracias por tu confianza!

Saludos,
El equipo de Origen Silvestre
**cerebras-llama** (OK / 5854ms):
> ¡Claro! Aquí tienes un mensaje corto y amigable para WhatsApp:

---

**Opción 1 (Directa):**

¡Hola [Nombre del Cliente]! 👋 Queremos avisarte que tu pedido ya está listo y preparado para despacho. ¡Pronto estará en camino! ✨

---

**Opción 2 (Con número de pedido, si aplica):**

¡Hola [Nombre del Cliente]! Tu pedido #XXXXX ya está listo para ser despachado. ¡Pronto lo recibirás! 😊

---


#### CONV-03 — Explicación sistema
**Pregunta:** ¿Qué tipos de consulta puedes hacer y cuáles requieren ir a la base de datos?

**gemini-flash** (OK / 4974ms):
> ¡Hola! Claro, puedo manejar varios tipos de consultas. Aquí te detallo cuáles son y cuáles requieren acceso a la base de datos:

```
Tipo de Consulta      | Requiere Base de Datos | Descripción
----------------------|------------------------|----------------------------------------------------------
analisis_datos        | Sí                     | Preguntas sobre ventas, compras, inventario, producción, cartera. Genera y ejecuta SQL.
conversacion          | No                     | Preguntas estratégicas, planes, conceptos.
redaccion             | No                     | Redactar textos, emails, descripciones.
aprendizaje           | No                     | Cuando me enseñas nueva lógica de negocio.
busqueda_web          | No                     | Preguntas sobre información externa al n
**gemini-flash-lite** (OK / 3842ms):
> ¡Hola! Puedo ayudarte con varios tipos de consultas. Aquí te explico cuáles son y cuáles necesitan acceder a la base de datos:

*   **Análisis de datos:** Consultas sobre ventas, compras, inventario, producción, cartera, etc. **Estas sí requieren ir a la base de datos** para obtener la información.
*   **Conversación:** Preguntas estratégicas, planes, conceptos generales. **No requieren ir a la base de datos**, respondo basándome en mi conocimiento general.
*   **Redacción:** Ayudo a redactar textos, correos, descripciones, etc. **No requieren ir a la base de datos**.
*   **Aprendizaje:** Cuando me enseñas nueva lógica de negocio. **No requieren ir a la base de datos**, guardo la información en mi memoria.
*   **Búsqueda web:** Preguntas sobre información externa a Origen Silvestre. **No r
**groq-llama** (OK / 5675ms):
> ¡Hola! Con gusto te explico los tipos de consultas que puedo manejar y cuáles de ellas interactúan con la base de datos de Origen Silvestre.

Aquí te presento los tipos de consulta y si requieren acceso a la base de datos:

```
Tipo de consulta     | Descripción                                                                 | ¿Requiere BD?
---------------------|-----------------------------------------------------------------------------|----------------
Análisis de datos    | Preguntas sobre ventas, compras, inventario, producción, cartera, etc.      | Sí (genera SQL)
Conversación         | Preguntas estratégicas, planes, conceptos generales del negocio.           | No
Redacción            | Generación de textos, emails, descripciones.                                | No
Aprendizaje     
**gpt-oss-120b** (OK / 16721ms):
> ¡Hola! 😊 Puedo ayudarte con varios tipos de consultas, y sí, algunas requieren acceder a la base de datos de Origen Silvestre para obtener información precisa y actualizada.

### Tipos de consulta que manejo:

| Tipo de consulta | ¿Qué incluye? | ¿Requiere BD? |
|---|---|---|
| **Análisis de datos** | Ventas, remisiones, cotizaciones, cartera, inventario, producción, compras, KPIs, tendencias, comparativos históricos. | **Sí** – genero y ejecuto SQL en la BD para obtener datos reales. |
| **Conversación** | Preguntas estratégicas, planes, conceptos del negocio, dudas operativas, explicaciones de procesos. | **No** – respondo con base en mi conocimiento del negocio y lógica aprendida. |
| **Redacción** | Textos para WhatsApp, emails, descripciones de productos, informes narrativos, comunica
**cerebras-llama** (OK / 6767ms):
> ¡Hola! Con gusto te explico los tipos de consulta que puedo manejar y cuáles de ellas interactúan con la base de datos:

```
Tipo de consulta      | Descripción                                                                  | ¿Requiere base de datos?
----------------------|------------------------------------------------------------------------------|-------------------------
Análisis de datos     | Preguntas sobre ventas, compras, inventario, producción, cartera, etc.       | Sí (genera y ejecuta SQL)
Conversación          | Preguntas estratégicas, planes, conceptos o aclaraciones.                     | No
Redacción             | Crear textos, emails o descripciones.                                        | No
Aprendizaje           | Cuando me enseñas nueva lógica de negocio, reglas o c


#### CONV-04 — Redacción propuesta comercial
**Pregunta:** Redacta un párrafo corto de propuesta comercial para un negocio nuevo interesado en nuestros chocolates, destacando calidad y origen natural.

**gemini-flash** (OK / 6088ms):
> ¡Claro! Aquí tienes una propuesta comercial corta para WhatsApp:

---

¡Hola! En Origen Silvestre, le invitamos a integrar en su negocio nuestros chocolates premium. Elaborados con cacao 100% natural y cultivado de forma sostenible, garantizamos una experiencia de sabor auténtico y bienestar, respaldada por la calidad superior y el origen responsable que sus clientes valorarán. ¡Conectemos para explorar esta deliciosa oportunidad!
**gemini-flash-lite** (OK / 2876ms):
> ¡Claro! Aquí tienes una propuesta comercial corta, enfocada en la calidad y el origen natural de nuestros chocolates, ideal para un nuevo negocio interesado:

"En Origen Silvestre, nos especializamos en chocolates que deleitan el paladar y nutren el cuerpo, elaborados con cacao agroecológico y miel pura de nuestras montañas. Cada tableta es un testimonio de nuestro compromiso con la calidad, la sostenibilidad y el bienestar, ofreciendo una experiencia de sabor auténtica y saludable que cautivará a tus clientes y diferenciará tu negocio."
**groq-llama** (OK / 6480ms):
> ¡Claro! Aquí tienes una propuesta comercial corta y atractiva para un negocio nuevo interesado en nuestros chocolates:

"Descubre la línea de chocolates de Origen Silvestre, donde la calidad superior se une a la pureza de la naturaleza. Elaborados con cacao 100% natural y orgánico, cultivado de forma agroecológica en las montañas de San Carlos, Antioquia, nuestros productos ofrecen una experiencia de sabor inigualable y auténtico bienestar, libres de conservantes y químicos. Incorpora a tu negocio la excelencia de un chocolate que tus clientes valorarán por su origen y sus beneficios."
**gpt-oss-120b** (OK / 9158ms):
> ¡Hola! Con mucho gusto te ayudo con esa propuesta comercial. Aquí tienes un párrafo conciso y persuasivo:

---

En Origen Silvestre elaboramos chocolates premium a partir de cacao 100% natural, cultivado de forma agroecológica en las montañas vírgenes de San Carlos, Antioquia. Nuestro proceso artesanal preserva la pureza y los nutrientes del grano, ofreciendo un sabor intenso y auténtico, libre de conservantes y químicos. Más que un producto, entregamos una experiencia de origen consciente: deliciosa, saludable y con un impacto positivo desde la tierra hasta tu negocio.

---

¿Te gustaría que lo adapte para incluir algún beneficio específico para distribuidores, como los descuentos por volumen o la flexibilidad en pedidos?
**cerebras-llama** (OK / 6427ms):
> ¡Claro! Aquí tienes un párrafo corto de propuesta comercial para un negocio nuevo, destacando la calidad y el origen natural de nuestros chocolates:

---

"En Origen Silvestre, le invitamos a descubrir nuestros chocolates, una propuesta de valor única para su negocio. Elaborados con cacao 100% natural y orgánico, cultivado de forma agroecológica y sostenible, nuestros productos garantizan una calidad superior y un sabor excepcional. Son libres de conservantes y químicos, ofreciendo a sus clientes no solo un placer delicioso, sino también un aporte nutritivo y de bienestar, alineado con la creciente demanda por opciones saludables y auténticas."

---


#### CONV-05 — Análisis estratégico
**Pregunta:** Dado que nuestro canal mayorista creció más que el minorista este año, ¿qué riesgos o oportunidades debería considerar el equipo comercial?

**gemini-flash** (OK / 19716ms):
> ¡Hola! Es una excelente señal que el canal mayorista esté creciendo más. Este cambio en la dinámica comercial presenta tanto oportunidades para escalar el negocio como riesgos que el equipo debe gestionar cuidadosamente.

Aquí te presento los riesgos y oportunidades que el equipo comercial de Origen Silvestre debería considerar:

```
Tipo          | Aspecto a Considerar
--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
**gemini-flash-lite** (OK / 6483ms):
> ¡Hola! Es una excelente pregunta y un punto clave para la estrategia comercial. Dado el crecimiento del canal mayorista por encima del minorista, aquí te presento algunos riesgos y oportunidades que el equipo comercial debería considerar:

```
Riesgo/Oportunidad | Descripción
--------------------|------------
Riesgo: Dilución de Marca | Un crecimiento rápido en el canal mayorista puede significar que nuestros productos lleguen a más puntos de venta, pero si no se gestiona adecuadamente, puede haber una pérdida de control sobre cómo se presenta la marca al consumidor final. Esto podría afectar la percepción de calidad y el posicionamiento premium que buscamos.
Oportunidad: Mayor Alcance y Penetración de Mercado | El crecimiento mayorista implica que nuestros productos están llegando a un pú
**groq-llama** (OK / 13732ms):
> ¡Hola! Es una excelente observación que el canal mayorista esté creciendo más que el minorista. Esta dinámica presenta tanto riesgos como oportunidades importantes que el equipo comercial de Origen Silvestre debería considerar.

Aquí te presento un análisis de los puntos clave a tener en cuenta:

```
Aspecto          | Riesgos a considerar                                        | Oportunidades a aprovechar
-------------------|-------------------------------------------------------------|--------------------------------------------------------------------------------------
Dependencia      | Mayor dependencia de un menor número de cuentas grandes.   | Mayor alcance geográfico y volumen de ventas con menos esfuerzo directo.
                   | La pérdida de un mayorista impacta significativ
**gpt-oss-120b** (OK / 26508ms):
> Analizando el crecimiento del canal mayorista frente al minorista, hay **riesgos y oportunidades** estratégicos que el equipo comercial debe considerar:

---

### 🚨 **Riesgos a gestionar**
| Riesgo | Impacto potencial | Acción sugerida |
|--------|-------------------|-----------------|
| **Dependencia de pocos clientes** | Mayoristas suelen ser menos numerosos pero de mayor volumen; perder uno afecta significativamente las ventas. | Diversificar la cartera mayorista y fortalecer relaciones con cláusulas de compromiso. |
| **Presión sobre márgenes** | Los mayoristas negocian descuentos más altos; si no se controla, puede reducir rentabilidad. | Revisar política de precios por canal (distribuidor vs. minorista) y asegurar que los descuentos estén alineados con volúmenes sostenibles. |
| **Ex
**cerebras-llama** (OK / 14047ms):
> ¡Hola! Es una excelente observación que el canal mayorista haya crecido más que el minorista este año. Esto presenta tanto desafíos como grandes oportunidades para el equipo comercial de Origen Silvestre, especialmente considerando el plan estratégico y los puntos de partida actuales.

Aquí te presento los principales riesgos y oportunidades que el equipo comercial debería considerar:

### Riesgos

```
Riesgo                       | Descripción para el equipo comercial
-----------------------------|-----------------------------------------------------------------------------------------------------------------------
Sobrecarga operativa         | El equipo comercial, ya sobrecargado, podría enfrentar una mayor presión para gestionar pedidos de mayor volumen, lo que podría afectar la eficie
