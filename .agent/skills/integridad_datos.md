# Skill: Verificación de Integridad de Datos

> Aplica a CUALQUIER tabla o vista resumen generada desde una tabla fuente.
> Ejecutar SIEMPRE al crear o modificar un script de agregación/resumen antes de dar la tarea por terminada.

---

## Principio fundamental

Una tabla resumen es correcta si y solo si:
1. Sus totales coinciden exactamente con la tabla fuente (sin pérdida ni duplicación de datos)
2. Una muestra manual de registros individuales es coherente con los datos originales
3. Los campos derivados (porcentajes, promedios, máximos) son matemáticamente consistentes

---

## CHECK 1 — Muestreo manual (7–8 registros)

Selecciona 7–8 registros concretos de la tabla resumen. Para cada uno:
- Busca en la tabla fuente los registros que lo conforman
- Suma/calcula manualmente los campos numéricos clave
- Compara con el valor en la tabla resumen

**SQL ejemplo** (tabla resumen agrupada por canal):
```sql
-- 1. Ver un registro del resumen
SELECT canal, fin_ventas_netas, vol_num_facturas
FROM resumen_ventas_facturas_canal_mes
WHERE mes = '2026-03' AND canal = 'Distribuidores';

-- 2. Verificar contra la fuente original
SELECT SUM(fin_ventas_netas) AS total_fuente, COUNT(*) AS num_facturas
FROM resumen_ventas_facturas_mes_staging  -- o la tabla fuente real
WHERE mes = '2026-03' AND canal = 'Distribuidores';
-- Debe dar igual (o diff ≤ 0.30 por redondeo DECIMAL)
```

**Criterio de aprobación:** diff = 0 (o ≤ 0.30 si hay redondeo DECIMAL acumulado en muchos registros).

---

## CHECK 2 — Suma total de columnas numéricas (THE BIG CHECK)

Para cada campo numérico importante:
- Suma TODOS los valores en la tabla resumen
- Suma el mismo campo en la tabla fuente para el mismo período
- Deben coincidir

**SQL template:**
```sql
-- Suma en la tabla resumen (ej: por canal)
SELECT SUM(fin_ventas_netas) AS total_resumen
FROM resumen_ventas_facturas_canal_mes
WHERE mes BETWEEN '2025-01' AND '2026-03';

-- Suma en la tabla fuente / tabla de mayor granularidad
SELECT SUM(fin_ventas_netas) AS total_fuente
FROM resumen_ventas_facturas_mes
WHERE mes BETWEEN '2025-01' AND '2026-03';

-- Deben ser iguales (diff = 0 o ≤ redondeo acumulado)
```

**Aplica especialmente cuando:**
- Se hizo una nueva agrupación (por canal, cliente, producto)
- Se cambiaron fórmulas de cálculo
- Se modificó el filtro de filas incluidas

---

## CHECK 3 — Consistencia entre tablas de distinta granularidad

Si tienes una jerarquía de tablas resumen (mes → canal×mes → cliente×mes), los totales deben ser consistentes entre niveles.

```sql
-- Ejemplo: SUM(canal_mes) debe = total de resumen_mes para el mismo período
SELECT
  m.mes,
  m.fin_ventas_netas AS total_mes,
  SUM(c.fin_ventas_netas) AS sum_canal,
  m.fin_ventas_netas - SUM(c.fin_ventas_netas) AS diff
FROM resumen_ventas_facturas_mes m
JOIN resumen_ventas_facturas_canal_mes c ON c.mes = m.mes
GROUP BY m.mes, m.fin_ventas_netas
HAVING ABS(diff) > 0.30
ORDER BY m.mes;
-- Si devuelve filas → hay inconsistencia entre niveles
```

---

## CHECK 4 — Unicidad de clave primaria

No debe haber duplicados en la PK o combinación única de la tabla.

```sql
-- Detectar duplicados en PK compuesta (mes + canal)
SELECT mes, canal, COUNT(*) AS n
FROM resumen_ventas_facturas_canal_mes
GROUP BY mes, canal
HAVING n > 1;
-- Debe devolver 0 filas
```

---

## CHECK 5 — Porcentajes y participaciones

Si la tabla tiene campos `_pct` que representan participación de un total, deben sumar 1.0 (±0.01 por redondeo) por período/grupo.

```sql
-- fin_pct_del_mes debe sumar 1.0 por cada mes
SELECT mes, SUM(fin_pct_del_mes) AS total_pct
FROM resumen_ventas_facturas_canal_mes
GROUP BY mes
HAVING ABS(total_pct - 1.0) > 0.01;
-- Debe devolver 0 filas
```

---

## CHECK 6 — Campos derivados: verificación de fórmula

Si hay campos calculados (margen, participación, variación), verificar que la fórmula es correcta en una muestra.

```sql
-- Ejemplo: margen = (ventas - costo) / ventas
SELECT
  mes, fin_ventas_netas, cto_costo_total, cto_margen_utilidad_pct,
  ROUND((fin_ventas_netas - cto_costo_total) / NULLIF(fin_ventas_netas,0), 4) AS margen_calculado,
  ROUND(cto_margen_utilidad_pct - (fin_ventas_netas - cto_costo_total) / NULLIF(fin_ventas_netas,0), 4) AS diff
FROM resumen_ventas_facturas_mes
ORDER BY mes DESC LIMIT 5;
-- diff debe ser 0 o ≈0 en todos los registros
```

---

## CHECK 7 — Campos comparativos (year_ant / mes_ant)

Para columnas `year_ant_X` o `mes_ant_X`:
- `year_ant_X` del período actual debe ser igual a `X` del mismo mes del año anterior
- `mes_ant_X` del período actual debe ser igual a `X` del mes inmediatamente anterior

```sql
-- year_ant_ventas_netas de 2026-03 debe = fin_ventas_netas de 2025-03
SELECT
  a.mes AS mes_actual,
  a.year_ant_ventas_netas AS year_ant_en_actual,
  b.fin_ventas_netas AS ventas_año_anterior,
  a.year_ant_ventas_netas - b.fin_ventas_netas AS diff
FROM resumen_ventas_facturas_mes a
JOIN resumen_ventas_facturas_mes b ON b.mes = DATE_FORMAT(DATE_SUB(a.mes, INTERVAL 1 YEAR), '%Y-%m')
ORDER BY a.mes DESC LIMIT 5;
-- diff debe ser 0 en todos los casos

-- mes_ant_ventas_netas de 2026-03 debe = fin_ventas_netas de 2026-02
SELECT
  a.mes AS mes_actual,
  a.mes_ant_ventas_netas AS mes_ant_en_actual,
  b.fin_ventas_netas AS ventas_mes_anterior,
  a.mes_ant_ventas_netas - b.fin_ventas_netas AS diff
FROM resumen_ventas_facturas_mes a
JOIN resumen_ventas_facturas_mes b ON b.mes = DATE_FORMAT(DATE_SUB(CONCAT(a.mes,'-01'), INTERVAL 1 MONTH), '%Y-%m')
ORDER BY a.mes DESC LIMIT 5;
-- diff debe ser 0
```

---

## CHECK 8 — Ausencia de NULLs inesperados

Campos que siempre deben tener valor no deben tener NULLs. Campos que solo aplican en condiciones específicas (ej: variaciones cuando no hay período anterior) pueden tener NULL válido.

```sql
-- Verificar NULLs en campos que siempre deben tener valor
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN fin_ventas_netas IS NULL THEN 1 ELSE 0 END) AS nulls_ventas,
  SUM(CASE WHEN cto_costo_total IS NULL THEN 1 ELSE 0 END) AS nulls_costo
FROM resumen_ventas_facturas_mes;
-- nulls_* debe ser 0 para campos críticos
```

---

## Checklist de ejecución

Al terminar de crear/modificar un script de resumen, ejecutar en orden:

- [ ] **CHECK 1** — Muestreo manual (7–8 registros) vs fuente → diff = 0
- [ ] **CHECK 2** — Suma total de columnas numéricas vs fuente → diff = 0 (o ≤ 0.30 redondeo)
- [ ] **CHECK 3** — Consistencia entre niveles de granularidad → 0 filas con diff > 0.30
- [ ] **CHECK 4** — Unicidad de PK → 0 duplicados
- [ ] **CHECK 5** — Porcentajes suman 1.0 por período → 0 filas con diff > 0.01
- [ ] **CHECK 6** — Campos derivados coherentes con fórmula → diff ≈ 0
- [ ] **CHECK 7** — Comparativos year_ant/mes_ant correctos → diff = 0 (si aplica)
- [ ] **CHECK 8** — Sin NULLs inesperados en campos críticos

**No se puede dar la tarea por terminada si algún check falla.**
