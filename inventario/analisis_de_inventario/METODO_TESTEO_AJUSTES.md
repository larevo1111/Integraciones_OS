# Método de testeo de ajustes de inventario

> Procedimiento estándar para verificar que un ajuste de inventario quedó bien aplicado en Effi después de un cierre de inventario físico.

## Fórmula

```
físico_al_corte + Σ(trazabilidad post-corte, EXCLUYENDO el ajuste de regularización) = stock_actual_effi
```

- **físico_al_corte**: la cantidad contada físicamente al cierre (ej: 30-abr)
- **Σ(trazabilidad post-corte)**: suma neta de movimientos vigentes en `zeffi_trazabilidad` desde el día siguiente al corte hasta hoy (signos: ingreso +, egreso −) **EXCLUYENDO** los movimientos que sean los ajustes de regularización del cierre (ej: `AJUSTE DE INVENTARIO: 371` y `: 372` para el cierre 30-abr).
- **stock_actual_effi**: el stock que reporta `zeffi_inventario.stock_bodega_<bodega>` en este momento.

Si la igualdad se cumple → ajuste correcto.
Si no se cumple → revisar excepciones (siguiente sección) o investigar.

### Por qué se excluyen los ajustes de regularización

El físico contado representa la VERDAD al cierre. Los ajustes que aplicamos hoy para regularizar Effi (cuadrar teórico = físico) NO son movimientos físicos reales — son correcciones contables. Si los incluyéramos en Σ, estaríamos doble-contabilizando: el físico ya refleja lo que había, no hay que sumar el ajuste que justamente vino a corregir Effi.

La fórmula equivalente sin exclusión:
```
teórico_al_corte + Σ(trazabilidad post-corte INCLUIDA el ajuste) = stock_actual_effi
```
Ambas son matemáticamente idénticas — pero la primera es más útil porque permite verificar **contra la realidad física contada**, no contra el teórico (que pudo estar mal antes del ajuste).

## Por qué funciona

Antes del ajuste, Effi tiene:
```
stock_actual = teórico_corte + Σ(traza post-corte sin ajuste)
```

El ajuste lo hacemos hoy con cantidad `delta = físico_corte − teórico_corte`. Después del ajuste:
```
stock_actual_post = stock_actual + delta
                  = teórico_corte + Σ(traza sin ajuste) + delta
                  = teórico_corte + (Σ(traza sin ajuste) + delta)
                  = teórico_corte + Σ(traza incluido el ajuste)
```

Y como `delta = físico_corte − teórico_corte`:
```
stock_actual_post = físico_corte + Σ(traza incluido el ajuste)  ✓
```

## Procedimiento (3 pasos)

### Paso 1 — Calcular el delta a ajustar
Para cada artículo a ajustar:
```sql
SELECT
  c.id_effi,
  c.inventario_fisico AS fisico_corte,
  c.inventario_teorico AS teorico_corte,
  (c.inventario_fisico - c.inventario_teorico) AS delta_a_ajustar
FROM inv_conteos c
WHERE c.fecha_inventario = '<corte>'
  AND c.id_effi = '<cod>';
```
- Si `delta > 0` → **INGRESO** de `delta` unidades (Tipo 1 en plantilla Effi)
- Si `delta < 0` → **EGRESO** de `|delta|` unidades (Tipo 2 en plantilla Effi)

### Paso 2 — Aplicar el ajuste en Effi
1. Generar XLSX con cods, descripciones, tipos y cantidades.
2. Subir vía `node scripts/import_ajuste_inventario.js <bodega_id> <archivo.xlsx> "<observación>"`.
3. Capturar el id del ajuste creado (visible en logs Effi y en `zeffi_trazabilidad.transaccion = 'AJUSTE DE INVENTARIO: <id>'` tras el próximo sync).

### Paso 3 — Verificar la fórmula POST-ajuste
Después de que el sync del pipeline traiga la trazabilidad nueva (1h máximo), correr para cada cod ajustado:
```sql
-- Σ trazabilidad post-corte (INCLUYE el ajuste recién hecho)
SELECT
  id_articulo,
  SUM(CAST(REPLACE(REPLACE(cantidad,'.',''),',','.') AS DECIMAL(12,3))) AS suma_traza
FROM zeffi_trazabilidad
WHERE id_articulo = '<cod>'
  AND vigencia_de_transaccion = 'Transacción vigente'
  AND fecha > '<corte 23:59:59>'
  AND bodega = '<bodega>';

-- Stock actual Effi en la bodega
SELECT id, nombre, stock_bodega_principal_sucursal_principal
FROM zeffi_inventario
WHERE id = '<cod>';
```

**Verificar**: `físico_corte + suma_traza == stock_bodega`

Tolerancia: 0.01 unidades (redondeo decimal).

## Casos comunes donde la fórmula NO cuadra

| Síntoma | Causa probable | Acción |
|---|---|---|
| `stock_actual` mayor al esperado por el monto exacto del ajuste | El ajuste se aplicó **DOS veces** O no excluiste los ajustes en Σ | Verificar exclusión; anular ajuste duplicado si aplica |
| `stock_actual` menor al esperado | OPs/ventas posteriores no capturadas (sync pendiente) | Forzar `python3 scripts/orquestador.py --forzar` |
| Pequeñas diferencias (< 0.5%) | Decimales en cantidades reportadas con coma vs punto | Aceptable — redondeo |
| Diferencia grande sin explicación | Ajuste puesto en bodega equivocada | Verificar `bodega` en query y XLSX |
| **Cods con excepción documentada en `notas.md`** | OV/remisión/OP en zona gris del cierre | Caso especial — no aplica fórmula directa |

### Excepciones conocidas — cierre 30-abr-2026

Los siguientes cods **fallan la fórmula** pero por razones documentadas (no requieren acción):

| Cod | Razón | Detalle |
|---|---|---|
| 411, 21, 164, 187, 405 | OV #720 contabilizada doble | El xlsx (teórico_30abr) fue tomado 1-may a las 00:03, cuando OV #720 ya estaba creada — el teórico ya la descontaba. Pero `zeffi_trazabilidad.fecha = 2026-05-01 00:03:14` la cuenta como post-corte → doble conteo. Delta esperado = exactamente la cantidad descontada por OV #720 para cada cod. |
| 585, 593, 594 | Timing transformación cacao SL | OP 2252 (06-may) regularizó la transformación física que ya había ocurrido antes del 30-abr. Físico contado al 30-abr ya reflejaba almendras transformadas en nibs/cascarilla. La OP 2252 en zeffi_trazabilidad cae post-corte. |
| 85, 88 | Remisión UNICOR #479 (legítima) | La compra (04-may) fue sumada manualmente al físico del 30-abr porque pertenecía a abril. Físico = teo_anterior + UNICOR. Stock effi tras OPs/ventas posteriores. La fórmula no aplica directo pero el inventario es consistente. |
| 86, 87 | (corregido con ajuste #373) | Inicialmente clasificados como justificados UNICOR, pero el físico ya tenía la remisión sumada → el teórico fantasma anterior necesitaba ajuste. Corregido el 07-may con ajuste #373: -40 (cod 86), -28 (cod 87). |
| 403 | Cod anulado en Effi | El cod fue anulado el 29-abr en la depuración pero tenía stock físico al 30-abr. El ajuste #371 aceptó el ingreso (+55) pero el cod sigue anulado en `zeffi_inventario` → no aparece en consultas activas. **Acción**: reactivar el cod en Effi si se va a seguir usando, o aceptar que el stock queda en limbo. |

**Regla práctica**: si un cod aparece en `notas.md` o tiene `inv_gestion.estado='justificada'`, NO aplicar fórmula directa — su análisis ya es manual.

## Snippet Python para test masivo

```python
def verificar_ajuste(cod, bodega, fecha_corte):
    """Retorna (ok, esperado, real, delta) para un cod ajustado."""
    fis = q_inv("SELECT inventario_fisico FROM inv_conteos WHERE fecha_inventario=%s AND id_effi=%s AND bodega=%s",
                (fecha_corte, cod, bodega))[0]['inventario_fisico']
    suma = q_effi("""SELECT COALESCE(SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,3))),0) AS s
                       FROM zeffi_trazabilidad
                      WHERE id_articulo=%s AND bodega=%s AND vigencia_de_transaccion='Transacción vigente'
                        AND fecha > %s""", (cod, bodega, f"{fecha_corte} 23:59:59"))[0]['s']
    stock = q_effi("SELECT stock_bodega_principal_sucursal_principal AS s FROM zeffi_inventario WHERE id=%s",
                   (cod,))[0]['s']
    esperado = float(fis) + float(suma)
    real = float(str(stock).replace(',','.'))
    delta = real - esperado
    return abs(delta) < 0.01, esperado, real, delta
```

## Historial de uso

- **Inventario 2026-04-30** (primer uso formal): aplicado a 13 cods (8 requiere_ajuste + 5 negativos históricos auto-resueltos). Resultados en `inv_ajustes_historico` con `fecha_ajuste = 2026-05-07`.
