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
Reglas en `scripts/inventario/config_depuracion.json`. De 489 vigentes → **300 inventariables**.
Excluidos (189): sin gestión stock (104), T999 obsoletos (70), T05 activos/moldes/consumibles (11), POP (4).
Script: `scripts/inventario/depurar_inventario.py` → guarda en `os_inventario.inv_articulos`.

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

## Infraestructura implementada

### App web — `inv.oscomunidad.com`
App independiente de conteo de inventario físico. Separada de sistema_gestion.

- **Frontend**: Vue 3 + Vite (sin Quasar). Diseño OS dark mode, responsive web+móvil.
- **Backend**: FastAPI (Python) en puerto 9401. Systemd: `os-inventario-api.service`.
- **Auth**: Google OAuth (mismo Client ID que gestión) → JWT compartido con gestión.
- **Subdominio**: `inv.oscomunidad.com` → cloudflared → localhost:9401.

### BD `os_inventario` (MariaDB local)

| Tabla | Descripción | Registros |
|---|---|---|
| `inv_conteos` | Conteos por artículo+bodega+fecha. Una fila por cada combinación. | ~500/inventario |
| `inv_rangos` | Unidad, grupo (MP/PP/PT/INS/DS), rango min/max, factor_error por artículo | 489 |
| `inv_auditorias` | Historial de cambios: conteo, edición, nota, foto. Quién, cuándo, valor anterior/nuevo. | acumulativa |

### Grupos de artículos (campo `grupo` en `inv_rangos`)

| Grupo | Nombre | Lógica de clasificación | Artículos |
|---|---|---|---|
| **MP** | Materia Prima | T01.xx que NO aparece en `zeffi_articulos_producidos` | 190 |
| **PP** | Producto en Proceso | Cualquier artículo producido en una OP (cruce con `zeffi_articulos_producidos`) | 45 |
| **PT** | Producto Terminado | Categoría TPT.xx (venta directa) | 80 |
| **INS** | Insumos | Categoría T03.xx (envases, tapas, etiquetas, bolsas, cajas) | 142 |
| **DS** | Desarrollo | Categoría DESARROLLO DE PRODUCTO (no en producción aún) | 32 |

### Unidades (campo `unidad` en `inv_rangos`)

| Unidad | Detección | Artículos | Error típico |
|---|---|---|---|
| **KG** | Nombre contiene KG, KILO, KL | 71 | Poner gramos (x1000) |
| **GRS** | Nombre contiene GRS, GRAMOS, G | 198 | — |
| **UND** | Sin unidad en nombre, o explícito | 218 | — |
| **LT** | Nombre contiene LT, LITRO | 2 | Poner ml (x1000) |

### Validación de rango (detección errores de unidades)

- Cada artículo tiene `rango_min` y `rango_max` en `inv_rangos` (calculados de stock histórico)
- `factor_error`: 1000 para KG y LT (error kg↔g, lt↔ml)
- Al ingresar valor fuera de rango: modal de alerta con sugerencia de corrección
- **0 siempre permitido** (no dispara alerta)
- Decimales: acepta punto y coma como separador. Input `type="text"` con `inputmode="decimal"`
- Si usuario confirma valor fuera de rango: se guarda pero queda en auditoría

### Scripts

| Script | Descripción |
|---|---|
| `scripts/inventario/config_depuracion.json` | Reglas de exclusión (patrones SQL LIKE) |
| `scripts/inventario/depurar_inventario.py` | Clasifica artículos y genera filas por bodega en `inv_conteos` |
| `scripts/inventario/calcular_rangos.py` | Genera `inv_rangos` (unidad, grupo, rangos) cruzando con OPs |
| `scripts/inventario/api.py` | FastAPI backend (puerto 9401). Sirve API + frontend estático |

### Archivos frontend

| Archivo | Descripción |
|---|---|
| `inventario/frontend/src/App.vue` | Componente único: login, tabla, filtros, modales |
| `inventario/frontend/src/styles.css` | Variables CSS del design system OS |
| `inventario/static/` | Build de producción (servido por FastAPI) |
| `inventario/fotos/` | Fotos capturadas durante conteo |

### Funcionalidades implementadas

- Login con Google OAuth (mismo sistema que gestión)
- Tabla con popups de filtro/ordenamiento por columna (patrón GestionTable)
- Chips de filtro: Todos/Pendientes/Contados/Diferencias
- Chips de bodega: solo las que tienen stock + botón (+) para más bodegas
- Panel lateral retráctil para seleccionar entre inventarios (fechas)
- Stepper +/- para ajuste rápido de conteo
- Tags de grupo (MP/PP/PT/INS/DS) y unidad (KG/GRS/UND/LT) por artículo
- Validación de rango con alerta y sugerencia de corrección
- Mini menú (⋮) con: Agregar nota / Tomar foto / Ver foto
- Auditoría completa: cada conteo, edición, nota y foto queda registrado
- Responsive: desktop, tablet, móvil

## Decisiones tomadas

- [x] BD: `os_inventario` (MariaDB local)
- [x] Depuración: Python puro (reglas deterministas en JSON)
- [x] Backend: FastAPI (Python) en puerto 9401
- [x] Frontend: Vue 3 + Vite, app independiente (NO dentro de sistema_gestion)
- [x] Auth: Google OAuth, JWT compartido con gestión
- [x] Dominio: `inv.oscomunidad.com`
- [x] Grupos: MP/PP/PT/INS/DS (detectados automáticamente cruzando con OPs)
- [x] Validación unidades: determinista (sin IA), rangos en tabla `inv_rangos`

## Pendiente

- [ ] Offline-first (Service Worker, IndexedDB)
- [ ] Módulo 1: Foto de inventario a fecha (reconstrucción desde trazabilidad)
- [ ] Módulo 2: Ajuste por OPs generadas (81 OPs vigentes no ejecutadas)
- [ ] Módulo 5: Verificación inconsistencias (comparar físico vs teórico)
- [ ] Módulo 6: Informe final
