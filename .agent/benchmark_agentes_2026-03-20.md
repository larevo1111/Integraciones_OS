# Benchmark de Agentes IA — Origen Silvestre
**Fecha:** 2026-03-20 18:36
**Agentes SQL testados:** gemini-flash, gemini-flash-lite, groq-llama, gpt-oss-120b, cerebras-llama
**Agentes respuesta testados:** gemini-flash, gemini-flash-lite, groq-llama, gpt-oss-120b, cerebras-llama

---
## FASE 1 — Generación de SQL

| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |
|---|---|---|---|---|---|
| SQL-01 | Ventas mes actual | OK / 2f / 12655ms | OK / 2f / 14299ms | OK / 2f / 20614ms | OK / 2f / 16072ms | OK / 2f / 16098ms |
| SQL-02 | Top canales febrero | OK / 2f / 14786ms | OK / 2f / 13294ms | OK / 2f / 26067ms | OK / 2f / 17993ms | OK / 2f / 18747ms |
| SQL-03 | Producto más vendido | OK / 2f / 12498ms | OK / 2f / 11437ms | OK / 2f / 17683ms | OK / 2f / 15917ms | OK / 2f / 14553ms |
| SQL-04 | Cartera vencida | OK / 2f / 19088ms | OK / 2f / 9302ms | OK / 2f / 15307ms | OK / 2f / 14752ms | OK / 2f / 15763ms |
| SQL-05 | Stock inventario | OK / 2f / 11225ms | NO_SQL / 2f / 4658ms | OK / 2f / 13229ms | OK / 2f / 12821ms | OK / 2f / 12378ms |
| SQL-06 | Órdenes producción vigentes | OK / 2f / 10887ms | OK / 2f / 12333ms | OK / 2f / 12979ms | OK / 2f / 12496ms | OK / 2f / 12767ms |
| SQL-07 | Remisiones pendientes | OK / 2f / 14698ms | OK / 2f / 9631ms | OK / 2f / 16342ms | OK / 2f / 16209ms | OK / 2f / 16620ms |
| SQL-08 | Consignación activa | OK / 2f / 10597ms | OK / 2f / 28373ms | OK / 2f / 24040ms | OK / 2f / 24473ms | OK / 2f / 24632ms |
| SQL-09 | Comparativo año anterior | OK / 2f / 26436ms | OK / 2f / 13462ms | OK / 2f / 25255ms | OK / 2f / 24532ms | OK / 2f / 25254ms |
| SQL-10 | Margen por canal | OK / 2f / 15969ms | OK / 2f / 10380ms | OK / 2f / 24140ms | OK / 2f / 29148ms | OK / 2f / 22652ms |
| SQL-11 | Clientes nuevos | NO_SQL / 2f / 6067ms | NO_SQL / 2f / 7187ms | OK / 2f / 17644ms | OK / 2f / 17981ms | OK / 2f / 18204ms |
| SQL-12 | Compras materia prima | OK / 2f / 26341ms | OK / 2f / 14073ms | OK / 2f / 14714ms | ERROR / 0f / 14700ms | OK / 2f / 14279ms |

### Latencia y costo promedio — SQL

| Agente | Latencia prom (ms) | Costo total USD | SQL OK% |
|---|---|---|---|
| gemini-flash | 15104 | $0.066032 | 92% |
| gemini-flash-lite | 12369 | $0.060965 | 83% |
| groq-llama | 19001 | $0.064738 | 100% |
| gpt-oss-120b | 18091 | $0.06196 | 92% |
| cerebras-llama | 17662 | $0.059814 | 100% |

### SQL generados por query y agente


#### SQL-01 — Ventas mes actual
**Pregunta:** ¿Cuánto vendimos en total este mes de marzo 2026?

**gemini-flash** (OK / 2 filas / 12655ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**gemini-flash-lite** (OK / 2 filas / 14299ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**groq-llama** (OK / 2 filas / 20614ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**gpt-oss-120b** (OK / 2 filas / 16072ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```
**cerebras-llama** (OK / 2 filas / 16098ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
  fin_devoluciones,
  fin_ingresos_netos
FROM resumen_ventas_facturas_mes
WHERE mes = '2026-03';
```

#### SQL-02 — Top canales febrero
**Pregunta:** ¿Cuál fue el top 3 de canales de venta en febrero 2026 por valor neto?

**gemini-flash** (OK / 2 filas / 14786ms):
```sql
SELECT
  COALESCE(NULLIF(canal, ''), 'Sin clasificar') AS canal_de_venta,
  fin_ventas_netas_sin_iva AS ventas_netas_sin_iva
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
  AND canal IS NOT NULL
  AND canal != ''
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**gemini-flash-lite** (OK / 2 filas / 13294ms):
```sql
SELECT
  canal,
  SUM(fin_ventas_netas_sin_iva) AS valor_neto
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
GROUP BY canal
ORDER BY valor_neto DESC
LIMIT 3;
```
**groq-llama** (OK / 2 filas / 26067ms):
```sql
SELECT
  canal,
  fin_ventas_netas_sin_iva AS valor_neto_sin_iva,
  fin_pct_del_mes AS participacion_pct
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**gpt-oss-120b** (OK / 2 filas / 17993ms):
```sql
SELECT
    canal,
    fin_ventas_netas_sin_iva AS valor_neto_sin_iva,
    fin_pct_del_mes AS porcentaje_del_total,
    vol_num_facturas AS numero_facturas,
    cli_clientes_activos AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-02'
    AND fin_ventas_netas_sin_iva > 0
ORDER BY fin_ventas_netas_sin_iva DESC
LIMIT 3;
```
**cerebras-llama** (OK / 2 filas / 18747ms):
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

#### SQL-03 — Producto más vendido
**Pregunta:** ¿Cuál fue el producto más vendido en unidades durante 2025?

**gemini-flash** (OK / 2 filas / 12498ms):
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
**gemini-flash-lite** (OK / 2 filas / 11437ms):
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
**groq-llama** (OK / 2 filas / 17683ms):
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
**gpt-oss-120b** (OK / 2 filas / 15917ms):
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
**cerebras-llama** (OK / 2 filas / 14553ms):
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

#### SQL-04 — Cartera vencida
**Pregunta:** ¿Cuánto hay en cartera vencida actualmente y cuáles son los 5 clientes con más deuda?

**gemini-flash** (OK / 2 filas / 19088ms):
```sql
SELECT
  tercero AS cliente,
  id_tercero AS id_cliente,
  SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
FROM zeffi_cuentas_por_cobrar
WHERE estado_cxc = 'Pendiente de cobro en mora'
GROUP BY tercero, id_tercero
ORDER BY deuda_en_mora DESC
LIMIT 5;
```
**gemini-flash-lite** (OK / 2 filas / 9302ms):
```sql
SELECT
  tercero AS cliente,
  id_tercero AS id_cliente,
  SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
FROM zeffi_cuentas_por_cobrar
WHERE estado_cxc = 'Pendiente de cobro en mora'
GROUP BY tercero, id_tercero
ORDER BY deuda_en_mora DESC
LIMIT 5;
```
**groq-llama** (OK / 2 filas / 15307ms):
```sql
SELECT
  tercero AS cliente,
  id_tercero AS id_cliente,
  SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
FROM zeffi_cuentas_por_cobrar
WHERE estado_cxc = 'Pendiente de cobro en mora'
GROUP BY tercero, id_tercero
ORDER BY deuda_en_mora DESC
LIMIT 5;
```
**gpt-oss-120b** (OK / 2 filas / 14752ms):
```sql
SELECT
  tercero AS cliente,
  id_tercero AS id_cliente,
  SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
FROM zeffi_cuentas_por_cobrar
WHERE estado_cxc = 'Pendiente de cobro en mora'
GROUP BY tercero, id_tercero
ORDER BY deuda_en_mora DESC
LIMIT 5;
```
**cerebras-llama** (OK / 2 filas / 15763ms):
```sql
SELECT
  tercero AS cliente,
  id_tercero AS id_cliente,
  SUM(CAST(saldo_en_mora AS DECIMAL(15,2))) AS deuda_en_mora
FROM zeffi_cuentas_por_cobrar
WHERE estado_cxc = 'Pendiente de cobro en mora'
GROUP BY tercero, id_tercero
ORDER BY deuda_en_mora DESC
LIMIT 5;
```

#### SQL-05 — Stock inventario
**Pregunta:** ¿Cuánto stock tenemos actualmente de productos terminados?

**gemini-flash** (OK / 2 filas / 11225ms):
```sql
SELECT
  SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
  AND vigencia = 'Vigente';
```
**gemini-flash-lite** (NO_SQL / 2 filas / 4658ms):
```sql
(sin SQL)
```
**groq-llama** (OK / 2 filas / 13229ms):
```sql
SELECT
  SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
  AND vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 12821ms):
```sql
SELECT
  SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
  AND vigencia = 'Vigente';
```
**cerebras-llama** (OK / 2 filas / 12378ms):
```sql
SELECT
  SUM(CAST(stock_total_empresa AS DECIMAL(15,2))) AS stock_total_productos_terminados
FROM zeffi_inventario
WHERE categoria IN ('TPT.01. VENTA AGROECOLOGICOS VARIOS', 'TPT.02. VENTA OTROS')
  AND vigencia = 'Vigente';
```

#### SQL-06 — Órdenes producción vigentes
**Pregunta:** ¿Cuántas órdenes de producción están vigentes y cuál es su valor total?

**gemini-flash** (OK / 2 filas / 10887ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**gemini-flash-lite** (OK / 2 filas / 12333ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**groq-llama** (OK / 2 filas / 12979ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 12496ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```
**cerebras-llama** (OK / 2 filas / 12767ms):
```sql
SELECT
  COUNT(id_orden) AS numero_ordenes_vigentes,
  SUM(CAST(total_precios_de_venta AS DECIMAL(15,2))) AS valor_total_ordenes_vigentes
FROM zeffi_produccion_encabezados
WHERE vigencia = 'Vigente';
```

#### SQL-07 — Remisiones pendientes
**Pregunta:** ¿Cuánto hay en remisiones pendientes de facturar y cuántas son?

**gemini-flash** (OK / 2 filas / 14698ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**gemini-flash-lite** (OK / 2 filas / 9631ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**groq-llama** (OK / 2 filas / 16342ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**gpt-oss-120b** (OK / 2 filas / 16209ms):
```sql
SELECT
  COUNT(id_remision) AS numero_remisiones_pendientes,
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_pendiente_sin_iva
FROM zeffi_remisiones_venta_encabezados
WHERE estado_remision = 'Pendiente de facturar'
  AND fecha_de_anulacion IS NULL;
```
**cerebras-llama** (OK / 2 filas / 16620ms):
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

**gemini-flash** (OK / 2 filas / 10597ms):
```sql
SELECT
  SUM(CAST(subtotal AS DECIMAL(15,2))) AS valor_consignacion_activa
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**gemini-flash-lite** (OK / 2 filas / 28373ms):
```sql
SELECT
  COUNT(*) AS num_ordenes_consignacion,
  SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_neto_consignacion,
  SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_bruto_consignacion
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**groq-llama** (OK / 2 filas / 24040ms):
```sql
SELECT
  COUNT(*) AS num_ordenes,
  SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
  SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_total_bruto
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**gpt-oss-120b** (OK / 2 filas / 24473ms):
```sql
SELECT
    COUNT(*) AS num_ordenes,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
    SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_total_bruto
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```
**cerebras-llama** (OK / 2 filas / 24632ms):
```sql
SELECT
    COUNT(*) AS num_ordenes,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS valor_total_neto,
    SUM(CAST(total_bruto AS DECIMAL(15,2))) AS valor_total_bruto
FROM zeffi_ordenes_venta_encabezados
WHERE vigencia = 'Vigente';
```

#### SQL-09 — Comparativo año anterior
**Pregunta:** ¿Cómo van las ventas de enero-marzo 2026 vs el mismo período de 2025?

**gemini-flash** (OK / 2 filas / 26436ms):
```sql
SELECT
  SUM(CASE WHEN mes BETWEEN '2026-01' AND '2026-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_netas_sin_iva_2026,
  SUM(CASE WHEN mes BETWEEN '2025-01' AND '2025-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) AS ventas_netas_sin_iva_2025,
  (SUM(CASE WHEN mes BETWEEN '2026-01' AND '2026-03' THEN fin_ventas_netas_sin_iva ELSE 0 END) - SUM(CASE WHEN mes BETWEEN '2025-01' AND '2025-03' THEN fin_ventas_netas_sin_iva ELSE 0 END)) / NULLIF(SUM(CASE WHEN mes BETWEEN '2025-01' AND '2025-
```
**gemini-flash-lite** (OK / 2 filas / 13462ms):
```sql
SELECT
  mes,
  fin_ventas_netas_sin_iva AS ventas_netas_2026,
  year_ant_ventas_netas AS ventas_netas_2025,
  year_ant_var_ventas_pct AS variacion_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2026-01', '2026-02', '2026-03')
ORDER BY mes;
```
**groq-llama** (OK / 2 filas / 25255ms):
```sql
SELECT
    mes,
    fin_ventas_netas_sin_iva AS ventas_netas_sin_iva,
    fin_devoluciones,
    fin_ingresos_netos,
    cto_costo_total,
    cto_utilidad_bruta,
    ROUND(cto_margen_utilidad_pct * 100, 2) AS margen_pct,
    vol_num_facturas,
    cli_clientes_activos
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2025-01', '2025-02', '2025-03', '2026-01', '2026-02', '2026-03')
ORDER BY mes DESC;
```
**gpt-oss-120b** (OK / 2 filas / 24532ms):
```sql
SELECT
    '2025' AS periodo,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(fin_devoluciones) AS devoluciones,
    SUM(fin_ingresos_netos) AS ingresos_netos,
    SUM(vol_num_facturas) AS num_facturas,
    SUM(cli_clientes_activos) AS clientes_activos,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2025-01', '2025-02', '2025-03')
UNION ALL
SELECT
    '2026' AS periodo,
    SUM(fin_ventas_netas_sin_iva) A
```
**cerebras-llama** (OK / 2 filas / 25254ms):
```sql
SELECT
    '2025' AS año,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(fin_devoluciones) AS devoluciones,
    SUM(fin_ingresos_netos) AS ingresos_netos,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct
FROM resumen_ventas_facturas_mes
WHERE mes IN ('2025-01', '2025-02', '2025-03')
UNION ALL
SELECT
    '2026' AS año,
    SUM(fin_ventas_netas_sin_iva) AS ven
```

#### SQL-10 — Margen por canal
**Pregunta:** ¿Cuál es el margen promedio de cada canal de venta en los últimos 3 meses?

**gemini-flash** (OK / 2 filas / 15969ms):
```sql
SELECT
  COALESCE(NULLIF(canal, ''), 'Sin clasificar') AS canal_de_venta,
  ROUND(SUM(cto_utilidad_bruta) / NULLIF(SUM(fin_ventas_netas_sin_iva), 0) * 100, 1) AS margen_promedio_pct
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), '%Y-%m')
GROUP BY canal_de_venta
ORDER BY margen_promedio_pct DESC;
```
**gemini-flash-lite** (OK / 2 filas / 10380ms):
```sql
SELECT
  canal,
  ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```
**groq-llama** (OK / 2 filas / 24140ms):
```sql
SELECT
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    COUNT(*) AS meses_con_datos,
    SUM(fin_ventas_netas_sin_iva) AS ventas_totales_sin_iva,
    SUM(cto_costo_total) AS costo_total,
    SUM(cto_utilidad_bruta) AS utilidad_total
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
ORDER BY margen_p
```
**gpt-oss-120b** (OK / 2 filas / 29148ms):
```sql
SELECT
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```
**cerebras-llama** (OK / 2 filas / 22652ms):
```sql
SELECT
    canal,
    ROUND(AVG(cto_margen_utilidad_pct) * 100, 2) AS margen_promedio_pct,
    SUM(fin_ventas_netas_sin_iva) AS ventas_netas_sin_iva,
    SUM(vol_num_facturas) AS numero_facturas,
    SUM(cli_clientes_activos) AS clientes_activos
FROM resumen_ventas_facturas_canal_mes
WHERE mes >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 MONTH), '%Y-%m')
    AND mes <= DATE_FORMAT(CURDATE(), '%Y-%m')
    AND fin_ventas_netas_sin_iva > 0
GROUP BY canal
ORDER BY margen_promedio_pct DESC;
```

#### SQL-11 — Clientes nuevos
**Pregunta:** ¿Cuántos clientes nuevos compraron por primera vez en lo que va del 2026?

**gemini-flash** (NO_SQL / 2 filas / 6067ms):
```sql
(sin SQL)
```
**gemini-flash-lite** (NO_SQL / 2 filas / 7187ms):
```sql
(sin SQL)
```
**groq-llama** (OK / 2 filas / 17644ms):
```sql
SELECT COUNT(DISTINCT id_cliente) AS clientes_nuevos_2026
FROM zeffi_facturas_venta_encabezados
WHERE YEAR(fecha_de_creacion) = 2026
  AND fecha_de_anulacion IS NULL
  AND id_cliente NOT IN (
    SELECT DISTINCT id_cliente
    FROM zeffi_facturas_venta_encabezados
    WHERE YEAR(fecha_de_creacion) < 2026
      AND fecha_de_anulacion IS NULL
  );
```
**gpt-oss-120b** (OK / 2 filas / 17981ms):
```sql
SELECT COUNT(DISTINCT id_cliente) AS clientes_nuevos_2026
FROM zeffi_facturas_venta_encabezados
WHERE YEAR(fecha_de_creacion) = 2026
  AND fecha_de_anulacion IS NULL
  AND id_cliente NOT IN (
    SELECT DISTINCT id_cliente
    FROM zeffi_facturas_venta_encabezados
    WHERE YEAR(fecha_de_creacion) < 2026
      AND fecha_de_anulacion IS NULL
  );
```
**cerebras-llama** (OK / 2 filas / 18204ms):
```sql
SELECT COUNT(DISTINCT id_cliente) AS clientes_nuevos_2026
FROM zeffi_facturas_venta_encabezados
WHERE YEAR(fecha_de_creacion) = 2026
  AND fecha_de_anulacion IS NULL
  AND id_cliente NOT IN (
    SELECT DISTINCT id_cliente
    FROM zeffi_facturas_venta_encabezados
    WHERE YEAR(fecha_de_creacion) < 2026
      AND fecha_de_anulacion IS NULL
  );
```

#### SQL-12 — Compras materia prima
**Pregunta:** ¿Cuánto hemos comprado en materia prima en lo que va del 2026?

**gemini-flash** (OK / 2 filas / 26341ms):
```sql
SELECT
  SUM(CAST(fcd.precio_bruto_total AS DECIMAL(15,2)) - CAST(fcd.descuento_total AS DECIMAL(15,2))) AS total_comprado_materia_prima_sin_iva
FROM zeffi_facturas_compra_detalle fcd
JOIN zeffi_facturas_compra_encabezados fce
  ON fcd.id_factura = fce.id_numeracion
JOIN zeffi_inventario zi
  ON fcd.cod_articulo = zi.cod_barras
JOIN zeffi_categorias_articulos zca
  ON zi.categoria = zca.nombre
WHERE DATE_FORMAT(fce.fecha_de_creacion, '%Y') = '2026'
  AND fce.fecha_de_anulacion IS NULL
  AND zca.
```
**gemini-flash-lite** (OK / 2 filas / 14073ms):
```sql
SELECT
  SUM(CAST(fc.subtotal AS DECIMAL(15, 2))) AS total_compras_materia_prima_sin_iva
FROM zeffi_facturas_compra_encabezados fc
JOIN zeffi_facturas_compra_detalle fcd
  ON fc.id_numeracion = fcd.id_factura
WHERE
  DATE_FORMAT(fc.fecha_de_creacion, '%Y') = '2026' AND fc.fecha_de_anulacion IS NULL
  AND (
    fcd.id_tipo_de_egreso LIKE 'T01%' OR fcd.id_tipo_de_egreso LIKE 'T01.03%' OR fcd.id_tipo_de_egreso LIKE 'T01.04%' OR fcd.id_tipo_de_egreso LIKE 'T01.05%' OR fcd.id_tipo_de_egreso LIKE 'T01
```
**groq-llama** (OK / 2 filas / 14714ms):
```sql
SELECT
    SUM(CAST(fc.total_neto AS DECIMAL(15,2))) AS total_compras_neto,
    SUM(CAST(fc.subtotal AS DECIMAL(15,2))) AS total_compras_sin_iva,
    COUNT(*) AS num_facturas_compra
FROM zeffi_facturas_compra_encabezados fc
WHERE YEAR(fc.fecha_de_creacion) = 2026
    AND fc.fecha_de_anulacion IS NULL;
```
**gpt-oss-120b** (ERROR / 0 filas / 14700ms):
```sql
SELECT
    SUM(CAST(fc.total_neto AS DECIMAL(15,2))) AS total_compras_neto,
    SUM(CAST(fc.subtotal AS DECIMAL(15,2))) AS total_compras_sin_iva,
    COUNT(*) AS num_facturas_compra
FROM zeffi_facturas_compra_encabezados fc
WHERE YEAR(fc.fecha_de_creacion) = 2026
    AND fc.fecha_de_anulacion IS NULL
    AND fc.id_numeracion IN (
        SELECT DISTINCT fcd.id_factura
        FROM zeffi_facturas_compra_detalle fcd
        JOIN zeffi_categorias_articulos ca ON fcd.categoria_articulo = ca.nombre
 
```
> ⚠️ Error: Error ejecutando SQL: (1054, "Unknown column 'fcd.categoria_articulo' in 'ON'")
**cerebras-llama** (OK / 2 filas / 14279ms):
```sql
SELECT
    COUNT(*) AS numero_facturas_compra,
    SUM(CAST(total_neto AS DECIMAL(15,2))) AS total_compras_con_iva,
    SUM(CAST(subtotal AS DECIMAL(15,2))) AS total_compras_sin_iva
FROM zeffi_facturas_compra_encabezados
WHERE YEAR(fecha_de_creacion) = 2026
    AND fecha_de_anulacion IS NULL;
```

---
## FASE 2 — Calidad de Respuesta

| Query | Descripción | gemini-flash | gemini-flash-lite | groq-llama | gpt-oss-120b |
|---|---|---|---|---|---|
| SQL-01 | Ventas mes actual | OK / 9480ms | OK / 8091ms | OK / 10840ms | OK / 17034ms | OK / 18688ms |
| SQL-02 | Top canales febrero | OK / 9783ms | OK / 8305ms | OK / 9711ms | OK / 20683ms | OK / 19518ms |
| SQL-03 | Producto más vendido | OK / 9566ms | OK / 7150ms | OK / 10559ms | OK / 16494ms | OK / 14293ms |
| SQL-04 | Cartera vencida | OK / 12582ms | OK / 7622ms | OK / 14632ms | OK / 21316ms | OK / 22179ms |
| SQL-05 | Stock inventario | CORTA / 7593ms | CORTA / 7585ms | CORTA / 8870ms | OK / 13205ms | OK / 13796ms |
| SQL-06 | Órdenes producción vigentes | OK / 8523ms | OK / 7677ms | OK / 9408ms | OK / 13789ms | OK / 15372ms |
| CONV-01 | Estrategia precio | OK / 15265ms | OK / 2897ms | OK / 13131ms | OK / 2937ms | OK / 2370ms |
| CONV-02 | Redacción email | OK / 4283ms | OK / 2058ms | OK / 3733ms | OK / 4434ms | OK / 1323ms |
| CONV-03 | Explicación sistema | OK / 6419ms | OK / 10790ms | OK / 5026ms | OK / 5299ms | OK / 1912ms |

### Latencia y costo promedio — Respuesta

| Agente | Latencia prom (ms) | Costo total USD | Resp OK% |
|---|---|---|---|
| gemini-flash | 9277 | $0.032049 | 89% |
| gemini-flash-lite | 6908 | $0.013415 | 89% |
| groq-llama | 9546 | $0.026646 | 89% |
| gpt-oss-120b | 12799 | $0.066656 | 100% |
| cerebras-llama | 12161 | $0.03766 | 100% |

### Respuestas completas por query y agente


#### SQL-01 — Ventas mes actual
**Pregunta:** ¿Cuánto vendimos en total este mes de marzo 2026?

**gemini-flash** (OK / 9480ms):
> ¡Hola!

Para este mes de marzo de 2026, las ventas facturadas van así:

*   **Ventas netas sin IVA:** $8,667,799.00
*   **Devoluciones:** $1,894,618.00
*   **Ingresos netos (después de devoluciones):** $6,773,181.00

Es importante notar que las devoluciones han sido significativas este mes.
**gemini-flash-lite** (OK / 8091ms):
> Este mes de marzo de 2026, vendimos un total de **$8,667,799.00** en ventas netas sin IVA.

Tuvimos **$1,894,618.00** en devoluciones, lo que resulta en unos ingresos netos de **$6,773,181.00** para el mes.
**groq-llama** (OK / 10840ms):
> ¡Hola!

Para el mes de **marzo de 2026**, las ventas facturadas de Origen Silvestre fueron las siguientes:

*   **Ventas netas sin IVA**: $8,667,799.00
*   **Devoluciones (Notas Crédito)**: $1,894,618.00
*   **Ingresos netos (después de devoluciones)**: $6,773,181.00

Es importante notar que hubo una cantidad considerable de devoluciones este mes, lo que impactó los ingresos netos finales.
**gpt-oss-120b** (OK / 17034ms):
> Según los datos del mes de marzo de 2026:

**Ventas netas (sin IVA):** $8.667.799  
**Devoluciones:** $1.894.618  
**Ingresos netos finales:** $6.773.181

**Interpretación:** Las ventas fueron sólidas, pero las devoluciones representan un 22% del total de ventas netas, lo que es un porcentaje significativo. Es importante revisar qué productos o clientes están generando estas devoluciones para entender si hay un patrón que podamos corregir.
**cerebras-llama** (OK / 18688ms):
> Según los datos disponibles para marzo de 2026:

**Ventas netas sin IVA:** $8.667.799  
**Devoluciones:** $1.894.618  
**Ingresos netos:** $6.773.181

**Interpretación:**  
Las ventas netas del mes fueron de $8,7 millones, pero hubo devoluciones significativas por $1,9 millones (aproximadamente el 22% de las ventas). Esto deja unos ingresos netos reales de $6,8 millones.

Es un dato que llama la atención por el alto volumen de devoluciones. Sería bueno revisar qué productos o clientes están generando tantas devoluciones este mes.


#### SQL-02 — Top canales febrero
**Pregunta:** ¿Cuál fue el top 3 de canales de venta en febrero 2026 por valor neto?

**gemini-flash** (OK / 9783ms):
> ¡Hola!

Analizando las ventas de febrero de 2026, los 3 canales con mayor valor neto sin IVA fueron:

```
Canal                                        | Ventas Netas sin IVA
---------------------------------------------|---------------------
1.5. Mercados, agropecuarias, Fruvers, etc.  | $2,993,795.00
1.3. Mercado Saludable                       | $2,789,454.00
1.7. Restaurantes, tiendas, reposterías, etc.| $1,498,235.00
```
**gemini-flash-lite** (OK / 8305ms):
> Claro, aquí tienes el top 3 de canales de venta para febrero de 2026, ordenados por valor neto:

| Canal                                              | Ventas Netas Sin IVA |
| :------------------------------------------------- | :------------------- |
| 1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc | $2,993,795.00        |
| 1.3. Mercado Saludable                             | $2,789,454.00        |
| 1.7. Restaurantes, tiendas, reposterias y cafes afines | $1,498,235.00        |
**groq-llama** (OK / 9711ms):
> ¡Hola!

En **febrero de 2026**, los 3 canales de venta con mayor valor neto sin IVA fueron:

```
Canal                                                    | Ventas Netas sin IVA
---------------------------------------------------------|--------------------
1.5. Mercados, agropecuarias, Fruvers, graneros, plazas  | $2,993,795.00
1.3. Mercado Saludable                                   | $2,789,454.00
1.7. Restaurantes, tiendas, reposterias y cafes afines   | $1,498,235.00
```
**gpt-oss-120b** (OK / 20683ms):
> Según los datos de febrero de 2026, el **top 3 de canales de venta por valor neto** (ventas sin IVA) fue el siguiente:

| # | Canal | Ventas Netas (sin IVA) |
|---|---|---|
| 1 | **1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc** | $2.993.795 |
| 2 | **1.3. Mercado Saludable** | $2.789.454 |
| 3 | **1.7. Restaurantes, tiendas, reposterías y cafés afines** | $1.498.235 |

**Interpretación:**  
Los canales **minoristas físicos** dominaron las ventas en febrero. El canal de **mercados y agropecuarias** lideró con una ventaja cercana a los $200 mil sobre el segundo lugar, lo que refleja una fuerte presencia en puntos de venta de alimentos frescos y locales. El **Mercado Saludable** y los **restaurantes/cafés** completan el podio, mostrando que la distribución a través de tiendas 
**cerebras-llama** (OK / 19518ms):
> Según los datos de febrero 2026, el **top 3 de canales de venta por valor neto** (ventas netas sin IVA) fue:

| Canal | Ventas netas sin IVA |
|-------|----------------------|
| **1.5. Mercados, agropecuarias, Fruvers, graneros, plazas merc** | $2.993.795 |
| **1.3. Mercado Saludable** | $2.789.454 |
| **1.7. Restaurantes, tiendas, reposterías y cafés afines** | $1.498.235 |

**Interpretación:**  
Los canales minoristas de **mercados y agropecuarias** lideraron las ventas en febrero, seguidos de cerca por el **Mercado Saludable**. Los restaurantes y cafés afines completan el podio, pero con una brecha considerable respecto a los dos primeros. Esto refleja la fuerza de los puntos de venta tradicionales y especializados en productos naturales durante ese mes.


#### SQL-03 — Producto más vendido
**Pregunta:** ¿Cuál fue el producto más vendido en unidades durante 2025?

**gemini-flash** (OK / 9566ms):
> ¡Hola!

Durante el año 2025, el producto más vendido en unidades fue:

```
Producto                         | Unidades Vendidas
---------------------------------|------------------
Tableta Chocolate 73p 50 grs CPM | 563
```
**gemini-flash-lite** (OK / 7150ms):
> El producto más vendido en unidades durante 2025 fue la **Tableta Chocolate 73p 50 grs CPM**, con un total de **563.00 unidades** vendidas.
**groq-llama** (OK / 10559ms):
> ¡Hola!

Durante el año **2025**, el producto más vendido en unidades fue:

```
Producto                         | Unidades Vendidas
---------------------------------|-------------------
Tableta Chocolate 73p 50 grs CPM | 563
```
**gpt-oss-120b** (OK / 16494ms):
> Según los datos de 2025, el producto más vendido en unidades fue:

**Tableta Chocolate 73p 50 grs CPM**  
**Total de unidades vendidas:** 563

Este producto de chocolate de 50 gramos fue claramente el de mayor rotación, lo que sugiere una alta demanda por su formato pequeño, accesible y de consumo rápido.
**cerebras-llama** (OK / 14293ms):
> Según los datos disponibles, el **producto más vendido en unidades durante 2025** fue:

**Tableta Chocolate 73p 50 grs CPM**  
**Total de unidades vendidas:** 563

**Interpretación:**  
Este producto de chocolate fue claramente el más popular en volumen durante el año, con más de 500 unidades vendidas. Es un dato interesante que muestra la fuerte demanda por este formato específico de tableta de chocolate.


#### SQL-04 — Cartera vencida
**Pregunta:** ¿Cuánto hay en cartera vencida actualmente y cuáles son los 5 clientes con más deuda?

**gemini-flash** (OK / 12582ms):
> ¡Hola!

Con los datos que tengo, puedo darte el detalle de los 5 clientes con más deuda en mora. Sin embargo, no tengo el dato del total de la cartera vencida, solo el de estos clientes específicos.

Aquí te muestro los 5 clientes con mayor deuda vencida:

```
Cliente                                  | Deuda en Mora
-----------------------------------------|--------------
INKAMPO - PORRAS ESLAVA KATHY ELIZABETH  | $715,713.00
COMERCIALIZADORA RAGESCO S.A.S. MERCANDU | $603,960.00
KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE | $450,065.00
Nuestro - Giraldo Giraldo Maria Paula    | $352,039.00
EUDANY HINCAPIE FINCA EL REFUGIO FRESAS  | $296,544.00
```
**gemini-flash-lite** (OK / 7622ms):
> ¡Claro! Actualmente, la cartera vencida suma un total de **$2,418,321.00**.

Aquí están los 5 clientes con mayor deuda en mora:

| Cliente                                                                 | Deuda en Mora |
| :---------------------------------------------------------------------- | :------------ |
| INKAMPO - PORRAS ESLAVA KATHY ELIZABETH                                 | $715,713.00   |
| COMERCIALIZADORA RAGESCO S.A.S. MERCANDU                                | $603,960.00   |
| KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA                         | $450,065.00   |
| Nuestro - Giraldo Giraldo Maria Paula                                   | $352,039.00   |
| EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN                         | $296,544.00   |
**groq-llama** (OK / 14632ms):
> ¡Hola!

Actualmente, la **cartera vencida total** de Origen Silvestre asciende a **$3,271,454.00**.

Los 5 clientes con mayor deuda vencida son:

```
Cliente                                         | ID Cliente       | Deuda en Mora
------------------------------------------------|------------------|---------------
INKAMPO - PORRAS ESLAVA KATHY ELIZABETH         | CC: 1102857179   | $715,713.00
COMERCIALIZADORA RAGESCO S.A.S. MERCANDU        | NIT: 811032480   | $603,960.00
KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA | NIT: 66963651    | $450,065.00
Nuestro - Giraldo Giraldo Maria Paula           | NIT: 1038416695  | $352,039.00
EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN | CC: 43477471     | $296,544.00
```

Es importante hacer seguimiento a estos clientes para recuperar esos sald
**gpt-oss-120b** (OK / 21316ms):
> Según los datos actuales de cartera vencida:

**Total de cartera vencida:** $3.271.454

**Top 5 clientes con mayor deuda en mora:**

| Cliente | ID | Deuda en mora |
|---|---|---|
| **INKAMPO - PORRAS ESLAVA KATHY ELIZABETH** | CC: 1102857179 | $715.713 |
| **COMERCIALIZADORA RAGESCO S.A.S. MERCANDU** | NIT: 811032480 | $603.960 |
| **KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA** | NIT: 66963651 | $450.065 |
| **Nuestro - Giraldo Giraldo Maria Paula** | NIT: 1038416695 | $352.039 |
| **EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN** | CC: 43477471 | $296.544 |

**Interpretación:**  
La cartera vencida total es de **$3.27 millones**. El cliente **INKAMPO** concentra la mayor deuda individual, con más de $715 mil, lo que representa cerca del **22%** del total vencido. Los cinco cliente
**cerebras-llama** (OK / 22179ms):
> Según los datos de cartera vencida:

**Total de cartera vencida actualmente:** $3.271.454

**Top 5 clientes con mayor deuda en mora:**

| Cliente | ID | Deuda en mora |
|---------|----|---------------|
| **INKAMPO - PORRAS ESLAVA KATHY ELIZABETH** | CC: 1102857179 | $715.713 |
| **COMERCIALIZADORA RAGESCO S.A.S. MERCANDU** | NIT: 811032480 | $603.960 |
| **KAKAW CHOCOLATERIA DE TAZA. OSORIO DUQUE YOANNA** | NIT: 66963651 | $450.065 |
| **Nuestro - Giraldo Giraldo Maria Paula** | NIT: 1038416695 | $352.039 |
| **EUDANY HINCAPIE FINCA EL REFUGIO FRESAS EL PLAN** | CC: 43477471 | $296.544 |

**Interpretación:**  
La cartera vencida total es de $3,27 millones, concentrada principalmente en estos cinco clientes que acumulan $2,42 millones (aproximadamente el 74% del total). El cliente **INKAMPO


#### SQL-05 — Stock inventario
**Pregunta:** ¿Cuánto stock tenemos actualmente de productos terminados?

**gemini-flash** (CORTA / 7593ms):
> ¡Hola!

Actualmente, el stock total de productos terminados que tenemos es de **1,098 unidades**.
**gemini-flash-lite** (CORTA / 7585ms):
> Tenemos un total de **1,098.00 unidades** en stock de productos terminados.
**groq-llama** (CORTA / 8870ms):
> ¡Hola!

Actualmente, tenemos un total de **1,098 unidades** en stock de productos terminados.
**gpt-oss-120b** (OK / 13205ms):
> Según los datos actuales del inventario, tenemos **1.098 unidades** de productos terminados disponibles en total.

Este stock incluye todos los artículos listos para la venta, clasificados en las categorías de productos terminados del sistema.
**cerebras-llama** (OK / 13796ms):
> Según los datos disponibles, el **stock total actual de productos terminados** es:

**1.098 unidades**

**Interpretación:**  
Este es el inventario total de productos listos para la venta (categorías TPT.01 y TPT.02) sumado de todas las bodegas. Es un nivel de inventario que permite atender la demanda actual, aunque sería bueno cruzar este dato con las ventas promedio mensuales para evaluar si es suficiente o si hay exceso de stock en algún producto específico.


#### SQL-06 — Órdenes producción vigentes
**Pregunta:** ¿Cuántas órdenes de producción están vigentes y cuál es su valor total?

**gemini-flash** (OK / 8523ms):
> ¡Hola!

Actualmente tenemos **1,089 órdenes de producción vigentes**, y su valor total asciende a **$3,706,220,397.00**.
**gemini-flash-lite** (OK / 7677ms):
> Actualmente, hay **1,089 órdenes de producción vigentes**, con un valor total de **$3,706,220,397.00**.
**groq-llama** (OK / 9408ms):
> ¡Hola!

Actualmente, Origen Silvestre tiene **1,089 órdenes de producción vigentes**.

El valor total de estas órdenes de producción activas asciende a **$3,706,220,397.00**.
**gpt-oss-120b** (OK / 13789ms):
> Según los datos actuales del sistema:

**Órdenes de producción vigentes:** 1.089  
**Valor total de las órdenes vigentes:** $3.706.220.397

**Interpretación:**  
Hay un volumen significativo de producción en curso, con más de mil órdenes activas y un valor total que supera los **$3.700 millones**. Esto indica una cartera de producción muy amplia, que podría incluir desde órdenes pequeñas hasta proyectos de gran escala. Es importante revisar la distribución de estas órdenes por estado, encargado o tipo de producto para priorizar recursos y asegurar su cumplimiento.
**cerebras-llama** (OK / 15372ms):
> Según los datos disponibles:

**Órdenes de producción vigentes:** 1.089  
**Valor total de las órdenes:** $3.706.220.397

**Interpretación:**  
Hay un volumen muy alto de órdenes de producción activas (más de mil), con un valor total que supera los $3.700 millones. Esto indica una cartera de producción significativa en curso, lo que podría representar una alta capacidad de fabricación planificada o, posiblemente, órdenes que han quedado abiertas sin cerrar. Sería recomendable revisar la distribución de estas órdenes por estado y antigüedad para priorizar su procesamiento.


#### CONV-01 — Estrategia precio
**Pregunta:** ¿Qué diferencia hay entre la tarifa distribuidor y la tarifa pública en OS?

**gemini-flash** (OK / 15265ms):
> ¡Hola!

La diferencia principal entre la "Tarifa Pública" y lo que podríamos llamar "Tarifa de Distribuidor" en Origen Silvestre radica en el cliente al que están dirigidas y las condiciones asociadas:

```
Tarifa                  | Descripción
------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Precio Publico Sugerido | Es el precio estándar para clientes directos y el público general. Es la tarifa base para todos los productos.
Tarifas por Volumen     | No existe una única "Tarifa Distribuidor" con un nombre específico. Los distribuidores, al ser generalmente "Negocios Aliados" o "Mayoristas", acceden a tarifas con descuentos por
**gemini-flash-lite** (OK / 2897ms):
> ¡Hola! Entiendo que quieres saber la diferencia entre la tarifa de distribuidor y la tarifa pública en Origen Silvestre.

En OS, manejamos 6 listas de precios. La principal diferencia radica en el volumen de compra y el tipo de cliente al que se aplican:

*   **Precio Público Sugerido:** Esta es la tarifa estándar para clientes directos y el público en general.
*   **Tarifa de Distribuidor:** Esta tarifa se aplica a clientes que compran en volúmenes mayores y suelen ser negocios aliados. Tenemos varias tarifas dentro de esta categoría, que varían según el volumen de compra:
    *   "+ de 400.000 en compras" (negocios aliados clasificación B)
    *   "+ de 800.000 en compras" (negocios aliados clasificación A)
    *   "+ de 1.600.000 en compras" (negocios aliados clasificación A top)

En re
**groq-llama** (OK / 13131ms):
> ¡Hola!

La principal diferencia entre la tarifa pública y lo que se considera una "tarifa de distribuidor" en Origen Silvestre radica en el cliente al que están dirigidas y el nivel de descuento que ofrecen.

Aquí te explico las diferencias:

```
Tarifa                     | Descripción                                                                                                | Nivel de Precio
---------------------------|------------------------------------------------------------------------------------------------------------|----------------
Precio Publico Sugerido    | Es el precio estándar y más alto, dirigido a clientes directos y al público general.                       | Más alto (precio base)
Tarifas para Distribuidores| Son un conjunto de tarifas con descuentos progresivos, 
**gpt-oss-120b** (OK / 2937ms):
> ¡Hola! 👋 En Origen Silvestre manejamos distintas listas de precios según el tipo de cliente y su volumen de compras. Aquí tienes la diferencia clave entre la **tarifa pública** y la **tarifa de distribuidor**:

```
Tarifa                | A quién se aplica                     | Característica principal
----------------------|---------------------------------------|-------------------------------
Precio Público Sugerido| Clientes directos (personas naturales) | Precio base sin descuento, usado para el público general
Tarifa Distribuidor   | Negocios aliados / mayoristas          | Descuentos por volumen (≥ $200 k, $400 k, $800 k, $1.6 M) según historial de compras
```

**Detalles**

* **Precio Público Sugerido**  
  * Es la lista estándar que ves en la columna `precio_precio_publico_sugerid
**cerebras-llama** (OK / 2370ms):
> La tarifa distribuidor y la tarifa pública en OS son dos de las tasas de precio disponibles para los clientes.

La **tarifa pública** es la tasa de precio


#### CONV-02 — Redacción email
**Pregunta:** Redacta un mensaje corto de WhatsApp para avisar a un cliente que su pedido está listo para despacho.

**gemini-flash** (OK / 4283ms):
> ¡Claro! Aquí tienes una opción corta y directa:

---

¡Hola [Nombre del Cliente]! 👋 Tenemos una excelente noticia: tu pedido #XXXX ya está listo para ser despachado. Te avisaremos cuando esté en camino. ¡Gracias por tu compra!

---
*(Recuerda reemplazar "[Nombre del Cliente]" y "#XXXX" con los datos correspondientes.)*
**gemini-flash-lite** (OK / 2058ms):
> ¡Hola! 👋 Tu pedido de Origen Silvestre ya está listo y preparado para ser despachado. ¡Pronto lo tendrás contigo! 😊
**groq-llama** (OK / 3733ms):
> ¡Claro! Aquí tienes una opción:

---

¡Hola [Nombre del cliente]! 👋

Te escribimos de Origen Silvestre para contarte que tu pedido ya está listo y a punto de salir para despacho. ¡Pronto lo tendrás contigo! 📦

Gracias por tu compra. 😊
**gpt-oss-120b** (OK / 4434ms):
> ¡Hola [Nombre del cliente]! 👋

Tu pedido en Origen Silvestre ya está listo para ser despachado. 📦✨

En breve nos pondremos en contacto contigo para coordinar la entrega.

¡Gracias por tu compra!
**cerebras-llama** (OK / 1323ms):
> "¡Atención! Su pedido ha sido preparado y está listo para su despacho. Le estamos enviando la información de seguimiento en este momento, por favor revise su correo electrónico para más detalles."


#### CONV-03 — Explicación sistema
**Pregunta:** ¿Qué tipos de consulta puedes hacer y cuáles requieren ir a la base de datos?

**gemini-flash** (OK / 6419ms):
> No necesito generar SQL para responder a esta pregunta, ya que se refiere a mis propias capacidades y no a datos de la base de datos de Origen Silvestre.

Puedo manejar los siguientes tipos de consulta:

*   **analisis_datos**: Preguntas sobre datos del negocio (ventas, compras, inventario, producción, cartera). **Estas requieren ir a la base de datos** para generar SQL y ejecutarlo.
*   **conversacion**: Preguntas estratégicas, planes, conceptos. Respondo sin SQL.
*   **redaccion**: Redactar textos, emails, descripciones. Respondo sin SQL.
*   **aprendizaje**: Cuando el equipo me enseña nueva lógica de negocio. Respondo sin SQL (guardo la información).
*   **busqueda_web**: Preguntas sobre información externa al negocio. Respondo sin SQL (busco en internet).
*   **generacion_imagen**: Cre
**gemini-flash-lite** (OK / 10790ms):
> ¡Hola! 👋 Como asistente de IA de Origen Silvestre, puedo manejar varios tipos de consultas. Aquí te los presento de forma clara:

```
Tipo de consulta          | Descripción                                                                 | ¿Requiere BD?
--------------------------|-----------------------------------------------------------------------------|----------------
analisis_datos            | Preguntas sobre ventas, compras, inventario, producción, cartera, etc.     | ✅ Sí (genera SQL)
conversacion              | Preguntas estratégicas, planes, conceptos, explicaciones del negocio       | ❌ No
redaccion                 | Redactar textos, emails, descripciones, mensajes                          | ❌ No
aprendizaje               | Cuando el equipo me enseña nueva lógica de negocio (la
**groq-llama** (OK / 5026ms):
> ¡Hola! Con gusto te explico los tipos de consulta que puedo manejar y cuáles de ellos requieren acceso a la base de datos:

```
Tipo de Consulta   | Descripción                                                                       | ¿Requiere Base de Datos?
-------------------|-----------------------------------------------------------------------------------|-------------------------
analisis_datos     | Preguntas sobre datos del negocio (ventas, compras, inventario, producción, cartera)| Sí (genera SQL y ejecuta)
conversacion       | Preguntas estratégicas, planes, conceptos                                          | No
redaccion          | Redactar textos, emails, descripciones                                            | No
aprendizaje        | Cuando el equipo me enseña nueva lógica d
**gpt-oss-120b** (OK / 5299ms):
> No necesito generar SQL para responder a esta pregunta, ya que se refiere a mis propias capacidades y lógica interna.

Puedo manejar los siguientes tipos de consulta:

*   **analisis_datos:** Preguntas sobre datos del negocio (ventas, compras, inventario, producción, cartera). **Estas consultas SÍ requieren ir a la base de datos** para generar SQL y ejecutarlo.
*   **conversacion:** Preguntas estratégicas, planes, conceptos. Estas se responden sin necesidad de acceder a la base de datos.
*   **redaccion:** Redactar textos, emails, descripciones. Estas se responden sin necesidad de acceder a la base de datos.
*   **aprendizaje:** Cuando el equipo me enseña nueva lógica de negocio. Esto se guarda en mi memoria y no requiere acceso a la base de datos para la respuesta en sí.
*   **busqueda_we
**cerebras-llama** (OK / 1912ms):
> Como asistente de IA de Origen Silvestre, puedo realizar diferentes tipos de consulta, incluyendo:

1. **Analisis_datos**: Preguntas sobre datos del negocio, como:
 * Ventas, compras, inventario, producción, cartera
 * Ejecutar SQL en la base de datos para obtener información específica
 * Requiere ir a la base de datos para obtener los datos preciso

2. **Conversacion**: Preguntas estratégicas, planes, conceptos
 * No requiere ir a la base de datos, pero puede utilizar conocimientos previos para dar una mejor respuesta

3. **Redaccion**: Redactar textos, emails, descripciones
 * No requiere ir a la base de datos

4. **Aprendizaje**: Cuando el equipo me enseña nueva lógica de negocio
 * No requiere ir a la base de datos, pero se almacena en mi memoria para futuras consultas

5. **Busqueda_
