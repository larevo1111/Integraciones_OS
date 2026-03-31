# Plan: Inventario Teórico a Fecha de Corte

**Creado**: 2026-03-31
**Estado**: Pendiente de ejecución
**Módulos**: 1 (Foto a fecha) + 2 (Ajuste OPs generadas) del inventario físico

---

## Objetivo

Calcular el inventario teórico de Origen Silvestre a una fecha de corte específica, combinando:
1. Reconstrucción del stock desde trazabilidad (rebobinar tiempo desde hoy hasta el corte)
2. Ajuste por OPs en estado "Generada" al corte (revertir efecto de producción no ejecutada)

El resultado se guarda en `os_inventario.inv_teorico` y se muestra en la app de inventario para comparar con el conteo físico.

---

## Fórmula verificada

```
stock_teorico[articulo] =
  stock_effi_hoy[articulo]                          (zeffi_inventario, suma todas bodegas)
  − movimientos_netos_post_corte[articulo]          (zeffi_trazabilidad, fecha > corte)
  + materiales_ops_generadas[articulo]              (zeffi_materiales, OPs generadas al corte)
  − productos_ops_generadas[articulo]               (zeffi_articulos_producidos, OPs generadas al corte)
```

---

## Contexto técnico clave (verificado en BD)

### zeffi_cambios_estado — determinar estado de OP al corte

- NO registra el estado inicial. Una OP nueva empieza como "Generada" sin ningún registro.
- Para estado al corte: último `nuevo_estado` con `f_cambio_de_estado <= fecha_corte`.
- Sin registro → estado = "Generada".

### OPs generadas al corte (85 al 31/03/2026)

```sql
SELECT e.id_orden
FROM zeffi_produccion_encabezados e
WHERE e.vigencia = 'Vigente'
  AND e.fecha_de_creacion <= '{fecha_corte} 23:59:59'
  AND (
    -- Sin ningún cambio de estado antes del corte → estado inicial = Generada
    NOT EXISTS (
      SELECT 1 FROM zeffi_cambios_estado ce
      WHERE ce.id_orden = e.id_orden
        AND ce.f_cambio_de_estado <= '{fecha_corte} 23:59:59'
    )
    OR
    -- Último cambio de estado antes del corte fue "Generada"
    (
      SELECT nuevo_estado FROM zeffi_cambios_estado ce
      WHERE ce.id_orden = e.id_orden
        AND ce.f_cambio_de_estado <= '{fecha_corte} 23:59:59'
      ORDER BY ce.f_cambio_de_estado DESC, ce._pk DESC
      LIMIT 1
    ) = 'Generada'
  )
```

### Trazabilidad post-corte

```sql
SELECT
  id_articulo,
  SUM(CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))) AS movimiento_neto
FROM zeffi_trazabilidad
WHERE fecha > '{fecha_corte} 23:59:59'
GROUP BY id_articulo
```

Usar TODOS los registros — las "Anulaciones" tienen signo ya invertido y se cancelan solas.

### Materiales y productos de OPs generadas

```sql
-- Materiales (sumar al stock teórico)
SELECT cod_material, SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,2))) AS total
FROM zeffi_materiales
WHERE id_orden IN ({ops_generadas})
  AND vigencia = 'Orden vigente'
GROUP BY cod_material

-- Productos (restar del stock teórico)
SELECT cod_articulo, SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,2))) AS total
FROM zeffi_articulos_producidos
WHERE id_orden IN ({ops_generadas})
  AND vigencia = 'Orden vigente'
GROUP BY cod_articulo
```

### Campos coma-decimal — SIEMPRE limpiar

Todos los campos `cantidad` en trazabilidad, materiales y artículos_producidos son TEXT con coma.
Siempre: `CAST(REPLACE(campo, ',', '.') AS DECIMAL(12,2))`

---

## Pasos de implementación

### Paso 1 — Tabla inv_teorico en os_inventario

```sql
CREATE TABLE IF NOT EXISTS inv_teorico (
  id INT AUTO_INCREMENT PRIMARY KEY,
  fecha_corte DATE NOT NULL,
  cod_articulo VARCHAR(50) NOT NULL,
  nombre_articulo VARCHAR(255),
  stock_effi DECIMAL(12,2),
  ajuste_trazabilidad DECIMAL(12,2),
  ajuste_ops_materiales DECIMAL(12,2),
  ajuste_ops_productos DECIMAL(12,2),
  stock_teorico DECIMAL(12,2),
  ops_generadas_count INT,
  ops_incluidas TEXT,
  calculado_en DATETIME,
  UNIQUE KEY uk_corte_articulo (fecha_corte, cod_articulo)
);
```

### Paso 2 — Script Python: `scripts/inventario/calcular_inventario_teorico.py`

**Argumentos**: `--fecha YYYY-MM-DD`

**Flujo**:
1. Leer `--fecha` (o usar hoy por defecto)
2. Obtener lista de OPs generadas al corte (query §OPs generadas)
3. Obtener stock actual de `zeffi_inventario` (sumar bodegas por artículo)
4. Obtener movimientos netos post-corte de `zeffi_trazabilidad`
5. Obtener ajuste materiales de `zeffi_materiales`
6. Obtener ajuste productos de `zeffi_articulos_producidos`
7. Cruzar por `id_articulo` / `cod_articulo` (verificar que sean el mismo campo o hay que cruzar por nombre/código)
8. Calcular `stock_teorico` con la fórmula
9. Hacer UPSERT en `os_inventario.inv_teorico`
10. Log en consola: resumen (N artículos calculados, N OPs incluidas, fecha)

**Manejo de IDs**:
- `zeffi_inventario` usa `id_articulo` (numérico como texto)
- `zeffi_trazabilidad` usa `id_articulo`
- `zeffi_materiales` usa `cod_material`
- `zeffi_articulos_producidos` usa `cod_articulo`
- Verificar si `id_articulo == cod_articulo` antes de cruzar (query de validación en Paso 2)

### Paso 3 — Endpoint FastAPI

```python
@app.post("/api/inventarios/{fecha}/calcular-teorico")
async def calcular_teorico(fecha: str, usuario=Depends(require_nivel(5))):
    # Nivel 5 = supervisor+
    # Ejecutar script Python como subprocess
    # Retornar JSON con resumen del cálculo
```

### Paso 4 — Botón en frontend (App.vue)

- Mostrar solo si `nivelUsuario >= 5`
- Botón "Actualizar datos teóricos" en el panel del inventario
- Estado: idle → cargando → completado/error
- Al completar: refrescar la vista de comparación teórico vs físico

### Paso 5 — Vista de comparación en frontend

Nueva columna o sección en la tabla principal:
- `stock_teorico` del `inv_teorico` para la fecha seleccionada
- `cantidad_contada` del `inv_conteos`
- `diferencia` = stock_teorico − cantidad_contada
- Color: verde (≤2%), amarillo (2-10%), rojo (>10%)

---

## Dependencias

- `os_inventario.inv_teorico` — tabla nueva (Paso 1)
- `effi_data.zeffi_inventario` — stock actual
- `effi_data.zeffi_trazabilidad` — movimientos históricos
- `effi_data.zeffi_produccion_encabezados` — encabezados OPs
- `effi_data.zeffi_cambios_estado` — estado histórico OPs
- `effi_data.zeffi_materiales` — materiales OPs
- `effi_data.zeffi_articulos_producidos` — productos OPs

---

## Riesgos y validaciones

| Riesgo | Mitigación |
|---|---|
| `id_articulo` vs `cod_articulo` no coinciden | Query de validación cruzada antes de implementar |
| OPs anuladas después del corte no incluidas | Documentado como limitación conocida. El efecto en trazabilidad compensa parcialmente. |
| Cantidades con formato inesperado (ej: sin coma) | `REPLACE + CAST` robusto, maneja ambos separadores |
| Script corre mientras pipeline actualiza | `inv_teorico` tiene UPSERT — idempotente |

---

## Archivos a crear/modificar

| Archivo | Acción |
|---|---|
| `scripts/inventario/calcular_inventario_teorico.py` | Crear |
| `inventario/api/main.py` | Agregar endpoint POST calcular-teorico |
| `inventario/frontend/src/App.vue` | Botón + columna comparación |
| `os_inventario.inv_teorico` | Crear tabla |
