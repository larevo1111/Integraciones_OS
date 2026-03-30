# Inventario Fisico OS — Contexto del Subproyecto

**Creado**: 2026-03-30
**Estado**: Planificacion

---

## Objetivo

Sistema para gestionar inventario fisico vs teorico de Origen Silvestre.
Reconstruir stock a cualquier fecha, capturar conteos fisicos, ajustar por OPs pendientes, detectar inconsistencias y generar informes.

---

## Tablas fuente verificadas (effi_data)

### zeffi_trazabilidad — 65,117 registros
Movimientos de inventario con vigentes + anulados (export trae TODO, sin filtro `?vigente=1`).

| Campo | Descripcion |
|---|---|
| id | ID del movimiento |
| id_articulo | ID del articulo (numerico como texto) |
| articulo | Nombre del articulo |
| transaccion | Ej: "ORDEN DE PRODUCCION: PPAL-764", "FACTURA DE VENTA: PPAL-1234" |
| tipo_de_movimiento | "Creacion de transaccion" o "Anulacion de transaccion" |
| vigencia_de_transaccion | "Transaccion vigente" (20,791) o "Transaccion anulada" (44,326) |
| cantidad | **Texto con coma decimal**. Positivo = ingreso a bodega, Negativo = egreso. Ej: "1000,00", "-23,00" |
| bodega | Nombre de la bodega |
| fecha | Timestamp. Ej: "2023-11-16 11:36:55" |
| costo | Costo unitario |
| precio | Precio de venta |
| descripcion, referencia_1, sucursal, responsable | Contexto adicional |

**Convension de signos confirmada:**
- Positivo (ingreso a bodega): 5,721 registros vigentes
- Negativo (egreso de bodega): 15,070 registros vigentes

**Tipos de transaccion vigentes (top 10):**
| Tipo | Registros |
|---|---|
| ORDEN DE PRODUCCION | 6,357 |
| FACTURA DE VENTA | 5,400 |
| TRASLADO DE INVENTARIO | 4,488 |
| REMISION DE VENTA | 2,017 |
| AJUSTE DE INVENTARIO | 1,107 |
| NOTA DE REMISION DE COMPRA | 567 |
| NOTA CREDITO DE VENTA | 320 |
| FACTURA DE COMPRA | 228 |
| ORDEN DE VENTA | 224 |
| DEVOLUCION DE VENTA | 45 |

### zeffi_inventario — 489 articulos vigentes
Stock actual por articulo con columnas de stock por bodega.
- **Stock total empresa**: 6,967 unidades
- **Valor inventario a costo promedio**: $35,795,674
- `stock_total_empresa` = suma de todas las bodegas
- Columnas individuales: `stock_bodega_principal_...`, `stock_bodega_jenifer_...`, etc.
- Todos los campos son tipo TEXT (requieren CAST)
- Incluye precios (publico, TA_B, red amigos, TA_A) y costos (manual, promedio, ultimo)

### zeffi_produccion_encabezados — OPs
| Estado | Vigencia | Cantidad |
|---|---|---|
| Generada | Vigente | **81** (estas son las que afectan inventario) |
| Generada | Anulado | 889 |
| Procesada | Vigente | 1,023 |
| Procesada | Anulado | 95 |

**81 OPs generadas vigentes** = Effi ya desconto materias primas y cargo productos terminados, pero la produccion NO se ha ejecutado fisicamente.

### zeffi_materiales — Materias primas de cada OP
- `id_orden` = mismo ID que `zeffi_produccion_encabezados.id_orden`
- `cod_material`, `descripcion_material`, `cantidad`, `costo_ud`
- `vigencia` = "Orden vigente" (no "Vigente")
- **309 lineas de materiales** en las 81 OPs generadas vigentes

### zeffi_articulos_producidos — Productos terminados de cada OP
- `id_orden` = mismo ID
- `cod_articulo`, `descripcion_articulo_producido`, `cantidad`
- `vigencia` = "Orden vigente"
- **142 lineas de articulos producidos** en las 81 OPs generadas vigentes

### zeffi_bodegas — 15 bodegas activas
| ID | Nombre | Notas |
|---|---|---|
| 1 | Principal | Bodega central — todo tipo de articulo |
| 2 | Villa de aburra | |
| 3 | Apica | |
| 4 | El Salvador | |
| 5 | Feria Santa Elena | |
| 6 | DON LUIS SAN MIGUEL | |
| 7 | LA TIERRITA | |
| 8 | Jenifer | Solo Producto Terminado "Ventas" |
| 10 | REGINALDO | |
| 13 | Desarrollo de Producto | Solo articulos de desarrollo |
| 14 | Ricardo | |
| 15 | Mercado Libre | |
| 16 | Santiago | |
| 17 | Productos No Conformes Bod PPAL | |
| 18 | FERIA CAMPESINA SAN CARLOS | |

---

## Notas tecnicas criticas

### IDs de OPs en trazabilidad
- `zeffi_produccion_encabezados.id_orden` = numerico secuencial (ej: 1985, 2088)
- `zeffi_trazabilidad.transaccion` = "ORDEN DE PRODUCCION: 2088" (ID numerico coincide)
- **Excepcion**: entre feb 2025 hubo un periodo donde usaron formato "PPAL-NNN" (718 a 761, 179 registros). Antes y despues, ID numerico puro.
- Las 81 OPs generadas vigentes SI tienen movimientos en trazabilidad con formato numerico
- Para el Modulo 2 (ajuste OPs) usamos directamente `zeffi_materiales` y `zeffi_articulos_producidos`

### Depuración de artículos para inventario físico
Reglas en `scripts/inventario/config_depuracion.json`. De 489 vigentes → **300 inventariables** (6,313 uds).
Excluidos: sin gestión stock (104), T999 obsoletos (70), POP (4), Gastos (62), T05 activos/moldes/consumibles (11), sin categoría (3).

### Cantidad en trazabilidad usa coma decimal
- Campo `cantidad` es TEXT con formato "1000,00" o "-23,00"
- Para operar: `CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,2))`

### Reconstruccion de stock a fecha
```
stock_a_fecha = stock_actual - SUM(movimientos desde fecha_objetivo+1 hasta hoy)
```
Solo considerar registros con:
- `vigencia_de_transaccion = 'Transaccion vigente'`
- `tipo_de_movimiento = 'Creacion de transaccion'`
(Ignorar anulaciones — si una transaccion se anulo, ya no es vigente)

### Ajuste por OPs generadas
```
Para cada OP con estado='Generada' AND vigencia='Vigente':
  stock_ajustado[materia_prima] += cantidad_material    (devolver lo descontado por Effi)
  stock_ajustado[prod_terminado] -= cantidad_producida  (quitar lo cargado por Effi)
```

---

## Modulos planificados

| # | Modulo | Descripcion | Estado |
|---|---|---|---|
| 1 | Foto de inventario a fecha | Reconstruir stock a cualquier fecha desde trazabilidad | Pendiente |
| 2 | Ajuste por OPs generadas | Revertir efecto de 81 OPs no ejecutadas | Pendiente |
| 3 | App de conteo fisico | PWA para captura en celular/tablet por bodega | Pendiente |
| 4 | Deteccion errores de unidades | Alertar si conteo > 100x promedio historico | Pendiente |
| 5 | Verificacion inconsistencias | Comparar fisico vs teorico, threshold 2% | Pendiente |
| 6 | Informe final | Resumen ejecutivo + inconsistencias + obsoleto | Pendiente |

---

## Documentacion relacionada

- `.agent/docs/MANUAL_EFFI_PRODUCCION_INVENTARIOS.md` — Manual completo de tablas y logicas de produccion e inventario en Effi

## Decisiones pendientes

- [ ] Stack del backend: Flask o FastAPI (o endpoint en ia_service existente?)
- [ ] Stack del frontend: modulo nuevo en sistema_gestion o app independiente?
- [ ] BD de conteos: tabla nueva en effi_data o en otra BD?
- [ ] Offline-first: localStorage o IndexedDB?
- [ ] Puerto/dominio para la app de conteo
