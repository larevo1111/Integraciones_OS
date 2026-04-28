---
name: inventario-inconsistencias
description: Metodología para detectar y diagnosticar inconsistencias en el inventario de Effi (stocks negativos, descuadres, materiales faltantes, esterilización sin OP). Usar cuando hay stock negativo, descuadres entre teórico y físico, OPs que fallan por falta de stock, o análisis previo a un cierre de inventario. Triggers - inventario negativo, stock negativo, descuadre, inconsistencia, faltante, esterilización sin OP, trazabilidad articulo, analizar inventario, causa raíz.
---

# inventario-inconsistencias — Detectar descuadres en Effi

Skill metodológico para encontrar Y explicar inconsistencias en el inventario. Complementa:
- `inventario-fisico` (procesos del conteo físico)
- `effi-database` (esquema de tablas)
- `effi-tecnico` (integración HTTP)
- `integridad-datos` (verificación de datos resumen)

## 1. Tipos de inconsistencia (taxonomía)

| Tipo | Descripción | Cómo detectar | Acción |
|---|---|---|---|
| **A. Esterilización sin OP** | Envase esterilizado consumido sin haberse "producido" del normal | Stock < 0, sin compras NI producciones | Crear OPs de esterilización (input: envase normal, output: esterilizado) |
| **B. Ajuste negativo sin ingreso** | Conteo físico menor al teórico (corrección legítima) | Ajuste de inventario negativo grande | Aceptar (refleja realidad). Ver dónde se perdió el material |
| **C. Sobreconsumo OPs** | Más OPs consumieron que compras | Σ OPs(-) > Σ compras + Σ ajustes | Comprar urgente, o anular OP exceso |
| **D. Compra no registrada** | Material físicamente está pero falta factura/remisión | Físico > teórico + nota "no contado" | Registrar factura/remisión retroactiva |
| **E. Articulo eliminado con conteo** | Item anulado en Effi pero aún tiene conteo activo | `id NOT IN (zeffi_inventario)` o `vigencia != Vigente` | Excluir del conteo, mover qty a cod sustituto |
| **F. Cod equivocado** | Conteo asignado a cod que ya no se usa | OP histórica del cod hace >6 meses | Mover qty al cod actual (observación oficial) |
| **G. Pérdida real** | Robos, mermas, derrames | Diferencia consistente sin explicación | Aceptar, documentar, mejorar control |

## 2. Detección — query base

```python
# Stock negativo en bodega Principal (vigentes)
SELECT id, nombre,
       CAST(REPLACE(stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,3)) AS stock,
       costo_manual
FROM zeffi_inventario
WHERE vigencia='Vigente'
  AND CAST(REPLACE(stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,3)) < 0
ORDER BY stock ASC
```

## 3. Trazabilidad por artículo

`zeffi_trazabilidad` registra TODOS los movimientos. Cols clave:
- `id_articulo` (cod)
- `transaccion` (ej: `ORDEN DE PRODUCCIÓN: 2215`, `AJUSTE DE INVENTARIO: 364`, `NOTA DE REMISIÓN DE COMPRA: 463`, `REMISIÓN DE VENTA: 2320`)
- `tipo_de_movimiento` (siempre `Creación de transacción` para activos)
- `vigencia_de_transaccion` (`Transacción vigente` vs `Transacción anulada`)
- `cantidad` (positiva = ingreso, negativa = salida)
- `bodega` (Principal / Apica / etc)
- `fecha`

**Validación**: `Σ cantidad WHERE vigencia='Transacción vigente' AND bodega='X'` = stock actual en bodega X.

```python
# Sumar movimientos vigentes de un cod en bodega Principal
SELECT SUM(CAST(REPLACE(REPLACE(cantidad,'.',''),',','.') AS DECIMAL(12,3))) AS total
FROM zeffi_trazabilidad
WHERE id_articulo=:cod
  AND vigencia_de_transaccion='Transacción vigente'
  AND bodega='Principal'
```

Esto **siempre** debe coincidir con `zeffi_inventario.stock_bodega_principal_sucursal_principal` para ese cod. Si no coincide, hay corrupción de datos en Effi (raro).

## 4. Clasificación automática

Para cada cod negativo, agrupar movimientos por tipo y aplicar reglas:

```python
compras  = Σ NOTA DE REMISIÓN DE COMPRA + Σ FACTURA DE COMPRA  (positivos)
ops_pos  = Σ ORDEN DE PRODUCCIÓN cantidad>0  (productos producidos)
ops_neg  = Σ ORDEN DE PRODUCCIÓN cantidad<0  (materiales consumidos)
ventas   = Σ REMISIÓN DE VENTA + Σ FACTURA DE VENTA  (negativos)
ajustes  = Σ AJUSTE DE INVENTARIO  (positivos o negativos)

# Reglas de clasificación
if compras < 0.01 and ops_pos < 0.01:
    causa = "A. Esterilización sin OP" if 'esteril' in nombre.lower() else "Item nunca recibido ni producido"
elif compras > 0 and abs(ops_neg) > compras * 1.5:
    causa = "C. Sobreconsumo OPs"
elif ajustes < -10:
    causa = "B. Ajuste negativo grande"
else:
    causa = "Análisis manual"
```

## 5. Patrones conocidos en OS (vigentes 2026-04)

### A. Esterilización sin OP — el más común
**Síntoma**: cods 552 (750cc), 553 (110cc), 554 (230cc), 555 (500cc), 556 (50cc) con stock negativo.
**Causa raíz**: el equipo esteriliza el envase UNICOR pero NO crea una OP que documente:
- Materiales: 1× envase normal (cod 85/86/87/88/232)
- Producto: 1× envase esterilizado (cod 552/553/554/555/556)
**Solución**: crear OP de esterilización por cada lote esterilizado. Mientras no se haga, los esterilizados quedan negativos.

### B. Etiquetado sin OP
**Síntoma**: etiquetas con stock negativo (262, 263, 290, 291, 298).
**Causa raíz**: alguien pega etiquetas sin que la OP de empacado tenga la etiqueta como material.
**Solución**: incluir las etiquetas en TODAS las recetas de productos terminados.

### C. Compras tardías
**Síntoma**: materiales clave (cacao, maní, miel) en negativo después de OPs.
**Causa raíz**: se produjo con stock bajo, la compra entró días después en Effi.
**Solución**: registrar compras DEL MISMO DÍA, usar fecha de remisión real (no fecha de captura).

### D. Maquila externa no contabilizada
**Síntoma**: ALMENDRA DE CACAO KL (cod 55), MANTECA DE CACAO (193) en negativo.
**Causa raíz**: el material está en maquila externa (Chocofruts, Bakau, etc.) pero NO se ingresó al inventario teórico.
**Solución**: agregar bodega "MAQUILA" a Effi, hacer trazabilidad explícita.

### E. Cod sustitutos (eliminados)
**Síntoma**: cods 358 (NIBS SF), 279 (CHOC 100% TABLETAS), 334 (DEGUSTACION CREMA MANI) con conteo pero sin existir en Effi.
**Causa raíz**: el cod fue anulado en Effi pero el conteo histórico permanece.
**Solución**: excluir del inventario + mover qty al cod sustituto (ver observaciones oficiales).

## 6. Reporte automatizable

Plantilla de output para cada cod negativo:

```
COD 553 | Envase 110cc esteril | stock -82 | $-123,000 impacto

📜 Trazabilidad (últimos 90 días):
  Compras:    +0
  OPs +:      +0  (esterilizaciones formales)
  OPs -:    -100  (consumido en OPs de mieles)
  Ajustes:   +18  (correcciones manuales)
  ───────────────
  Stock teórico = -82 ✓ coincide

🔍 Causa: A. Esterilización sin OP
🛠️  Acción sugerida:
  - Crear OP de esterilización: 100 cod 86 (110cc UNICOR) → 100 cod 553 (esteril)
  - Definir proceso: cada vez que se esteriliza, crear OP
  - Costo de mano de obra: ~$X por unidad (a calcular)
```

## 7. Workflow recomendado (preventivo)

**Antes de cada inventario físico**:
1. Correr query de stock negativo
2. Para cada negativo, ejecutar diagnóstico (§4)
3. Generar lista de acciones (compras pendientes, OPs de esterilización, registros faltantes)
4. Ejecutar acciones ANTES de iniciar el conteo
5. Recalcular teórico (`POST /api/inventario/calcular-teorico`)

**Durante el inventario**:
- Marcar items "no contados" (ej: maquila externa) con razón clara
- Documentar hallazgos en `inv_observaciones` (tipo: `hallazgo`, `error_conteo`, `correccion_costo`)

**Al cerrar inventario**:
- Excluir items eliminados de Effi (no aparecen en `zeffi_inventario` o `vigencia != 'Vigente'`)
- Aplicar correcciones documentadas en observaciones (mover qty entre cods, etc.)
- Cerrar con `POST /api/inventario/cerrar-inventario`

## 8. Consultas SQL útiles (copiar-pegar)

### 8.1 Stock negativo
```sql
SELECT id, nombre,
       CAST(REPLACE(stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,3)) AS stock,
       costo_manual
FROM zeffi_inventario
WHERE vigencia='Vigente'
  AND CAST(REPLACE(stock_bodega_principal_sucursal_principal,',','.') AS DECIMAL(12,3)) < 0
ORDER BY stock ASC;
```

### 8.2 Trazabilidad de un cod (últimas 20 movimientos)
```sql
SELECT fecha, transaccion, tipo_de_movimiento, vigencia_de_transaccion, cantidad, bodega
FROM zeffi_trazabilidad
WHERE id_articulo='XXX'
  AND vigencia_de_transaccion='Transacción vigente'
ORDER BY fecha DESC LIMIT 20;
```

### 8.3 Items inventariados que no existen en Effi (para excluir)
```sql
SELECT c.fecha_inventario, c.id_effi, c.nombre, c.inventario_fisico, c.excluido
FROM inv_conteos c
LEFT JOIN os_integracion.zeffi_inventario e ON e.id = c.id_effi
WHERE c.fecha_inventario = 'YYYY-MM-DD'
  AND c.id_effi NOT LIKE 'NM-%'
  AND (e.id IS NULL OR e.vigencia != 'Vigente');
```

### 8.4 Productos sin compras pero con consumo en OPs
```sql
SELECT m.cod_material, COUNT(DISTINCT m.id_orden) ops_consumieron,
       SUM(CAST(REPLACE(m.cantidad,',','.') AS DECIMAL(12,3))) total_consumido
FROM zeffi_materiales m
JOIN zeffi_produccion_encabezados e ON e.id_orden=m.id_orden
WHERE m.vigencia='Orden vigente' AND e.vigencia='Vigente' AND e.fecha_de_creacion >= '2026-01-01'
GROUP BY m.cod_material
HAVING total_consumido > 0
ORDER BY total_consumido DESC;
-- comparar con compras del mismo cod para detectar sobreconsumo
```

## 9. Acciones automatizables a futuro

| Acción | Complejidad | Beneficio |
|---|---|---|
| **Alerta diaria de stock negativo** | Baja | Detectar al día siguiente, no al cierre |
| **Auto-OP de esterilización** | Media | El equipo solo confirma cantidades |
| **Validar OP antes de crear** (stock suficiente) | Media | Evitar negativos por OPs nuevas |
| **Reporte mensual de inconsistencias** | Baja | Histórico para auditoría |
| **Sincronizar maquilas como bodegas Effi** | Alta | Trazabilidad real de material en proceso |

## 10. Anti-patrones

❌ **Crear OPs sin verificar stock previo**: el endpoint `crear-op-effi` actualmente NO valida stock. Permite stock negativo. Considerar agregar `--validar-stock` opcional.
❌ **Ignorar items con `vigencia != Vigente`**: pueden seguir teniendo movimientos. Filtrar siempre en queries.
❌ **Confundir CC del usuario con ID interno** (ver `effi-tecnico` §4).
❌ **Hacer ajustes manuales sin auditar**: SIEMPRE registrar en `inv_observaciones` la razón.
❌ **Asumir que stock 0 = OK**: a veces es 0 porque se eliminó el item, otras porque está agotado. Verificar `vigencia`.

## 11. Checklist preflight inventario

- [ ] Stock negativo: ≤ 5 items críticos pendientes
- [ ] Esterilizaciones del mes documentadas con OPs
- [ ] Compras del mes capturadas en Effi (no pendientes)
- [ ] Maquilas externas con conteo manual disponible
- [ ] Items anulados Effi excluidos de últimos inventarios
- [ ] Costos manuales actualizados en Effi (revisar discrepancias inv vs Effi)
- [ ] Recálculo de teórico ejecutado el día del corte

## 12. Histórico de hallazgos OS (referencia)

Inventarios analizados:
- **31-mar-2026**: 314 items, 187 con dif, pérdida -$4.1M. Causas principales: maquila no contada (118 kg almendra cacao), esterilización sin OP, NIBS contado en cod equivocado (358 → 178).
- **20-abr-2026**: 33 items parciales, 31 con dif (verificación de stocks bajos).
- **22-abr-2026**: 495 items en curso (al momento de escribir este skill).
