# Manual Effi — Produccion e Inventarios

Documentacion de como funcionan los modulos de produccion e inventario en Effi,
sus tablas en effi_data, y las logicas de negocio relevantes.

**Creado**: 2026-03-30

---

## 1. Inventario (zeffi_inventario)

### Que es
Foto del stock actual de todos los articulos de la empresa. Effi exporta una tabla plana
con el stock desglosado por bodega en columnas individuales.

### Tabla: `zeffi_inventario` — 489 articulos vigentes

| Campo | Tipo | Descripcion |
|---|---|---|
| id | TEXT | ID del articulo en Effi |
| cod_barras | TEXT | Codigo de barras (pocos lo tienen) |
| nombre | TEXT | Nombre completo del articulo |
| referencia | TEXT | Referencia interna |
| tipo_de_articulo | TEXT | Clasificacion Effi (ver tipos abajo) |
| categoria | TEXT | Categoria contable/operativa (ver categorias abajo) |
| marca | TEXT | Marca del articulo |
| vigencia | TEXT | "Vigente" o "Anulado" |
| costo_manual | TEXT | Costo asignado manualmente |
| costo_promedio | TEXT | Costo promedio ponderado (calculado por Effi) |
| ultimo_costo | TEXT | Ultimo costo de compra |
| gestion_de_stock | TEXT | Si/No — si Effi gestiona stock de este articulo |
| stock_minimo | TEXT | Stock minimo configurado |
| stock_optimo | TEXT | Stock optimo configurado |
| stock_total_empresa | TEXT | **Suma de stock en todas las bodegas** |
| stock_bodega_X_sucursal_principal | TEXT | Stock en cada bodega individual |
| precio_precio_publico | TEXT | Precio publico |
| precio_ta_b | TEXT | Precio tarifa B |
| precio_red_amigos_1_ano | TEXT | Precio red de amigos |
| precio_ta_a | TEXT | Precio tarifa A |
| precio_impuesto_X | TEXT | Impuesto de cada precio |
| de_utilidad_precio_X | TEXT | % utilidad de cada precio |

**Todos los campos son tipo TEXT** — requieren CAST para operar numericamente.
Los numeros usan coma decimal (ej: "1000,00"). Parsear con `REPLACE(campo, ',', '.')`.

### Tipos de articulo
| Tipo | Cantidad |
|---|---|
| Producto en proceso | 193 |
| Materia prima | 192 |
| Servicio | 78 |
| Activo fijo (Propiedad, planta y equipo) | 21 |
| Producto terminado | 5 |

**Nota importante**: La mayoria de productos de venta estan clasificados como "Producto en proceso"
en Effi, NO como "Producto terminado". Esto es porque en Effi el tipo "Producto terminado" se
refiere a articulos que salen automaticamente de una formula de produccion, y Origen Silvestre
clasifica la mayoria manualmente. La **categoria** es mas util para identificar el tipo real.

### Categorias con stock > 0
| Categoria | Tipo real |
|---|---|
| TPT.01. VENTA AGROECOLOGICOS VARIOS | Producto terminado de venta |
| T01.03. AGROECOLOGICOS GRAL | Materia prima agroecologica |
| T03.21. ETIQUETAS ADESIVAS | Insumo de empaque |
| T05.02. A.F. MOLDES | Activo fijo |
| T03.03. ENVASES ECOLOGICOS | Insumo de empaque |
| T03.41. CAJAS | Insumo de empaque |
| T03.01. ENVASES Y TAPAS | Insumo de empaque |
| T03.31. BOLSAS PLASTICAS | Insumo de empaque |
| T999. PRODUCTOS QUE NO SE USAN | Obsoleto |
| T05.06. CONSUMIBLES PRODUCCION Y VENTAS | Consumible |
| T01.04. CACAO/CAFE ALMENDRAS ECOLOGICO | Materia prima |
| DESARROLLO DE PRODUCTO | Desarrollo |
| T01.30. OTROS PRODUCTOS AGROECOLOGICOS | Materia prima |
| TPT.02. VENTA OTROS | Producto terminado otro |

### Columnas de stock por bodega
Cada bodega tiene su propia columna con formato:
`stock_bodega_{nombre_normalizado}_sucursal_principal`

Ejemplo: `stock_bodega_principal_sucursal_principal`, `stock_bodega_jenifer_sucursal_principal`

### Export: `export_inventario.js`
- URL: `https://effi.com.co/app/articulo` (sin filtro — trae todos)
- Marca todos los checkboxes del modal de export (precios + bodegas)
- Usa mecanismo de notificaciones para descargar (no download directo)
- Salida: `/exports/inventario/inventario_YYYY-MM-DD.xlsx`

---

## 2. Trazabilidad de Inventario (zeffi_trazabilidad)

### Que es
Registro de **todos los movimientos** que afectan el stock de articulos. Cada vez que un
documento (factura, OP, traslado, ajuste, etc.) modifica el inventario, se crea una o mas
lineas en trazabilidad. Es la base para reconstruir stock a cualquier fecha.

### Tabla: `zeffi_trazabilidad` — 65,117 registros

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id | TEXT | ID secuencial del movimiento | "65083" |
| id_articulo | TEXT | ID del articulo afectado | "317" |
| articulo | TEXT | Nombre del articulo | "NIBS DE CACAO ORGANICO OS 100 GRS" |
| descripcion | TEXT | Descripcion (generalmente = articulo) | idem |
| transaccion | TEXT | **Tipo de documento + ID** | "ORDEN DE PRODUCCION: 2088" |
| tipo_de_movimiento | TEXT | Tipo de registro | "Creacion de transaccion" o "Anulacion de transaccion" |
| vigencia_de_transaccion | TEXT | Estado del movimiento | "Transaccion vigente" o "Transaccion anulada" |
| referencia_1 | TEXT | Info adicional del documento | "Cliente: INKAMPO - PORRAS..." (en facturas) o NULL |
| sucursal | TEXT | Siempre "Principal" | "Principal" |
| bodega | TEXT | Bodega afectada | "Principal", "Jenifer", etc. |
| cantidad | TEXT | **Cantidad con signo, coma decimal** | "6,00" (ingreso) o "-23,00" (egreso) |
| costo | TEXT | Costo unitario del movimiento | "24000,0000" |
| precio | TEXT | Precio de venta (0 si no aplica) | "0,00" o "13127,00" |
| fecha | TEXT | Timestamp del movimiento | "2026-03-28 22:54:25" |
| responsable | TEXT | Quien registro el movimiento | "Jennifer Alexandra Cano Garcia (origensilvestre.col@gmail.com)" |

### Campo `transaccion` — formato y logica

El campo `transaccion` contiene el **tipo de documento origen** y su **ID**, separados por ": ".
Formato: `TIPO DE DOCUMENTO: ID`

| Tipo de documento | Formato ID | Ejemplo | Movimientos vigentes |
|---|---|---|---|
| ORDEN DE PRODUCCION | numerico (antes: PPAL-NNN) | "ORDEN DE PRODUCCION: 2088" | 6,357 |
| FACTURA DE VENTA | numerico | "FACTURA DE VENTA: 906" | 5,400 |
| TRASLADO DE INVENTARIO | numerico | "TRASLADO DE INVENTARIO: 517" | 4,488 |
| REMISION DE VENTA | numerico | "REMISION DE VENTA: 1" | 2,017 |
| AJUSTE DE INVENTARIO | numerico | "AJUSTE DE INVENTARIO: 356" | 1,107 |
| NOTA DE REMISION DE COMPRA | numerico | "NOTA DE REMISION DE COMPRA: 145" | 567 |
| NOTA CREDITO DE VENTA | numerico | "NOTA CREDITO DE VENTA: 1" | 320 |
| FACTURA DE COMPRA | numerico | "FACTURA DE COMPRA: 1" | 228 |
| ORDEN DE VENTA | numerico | "ORDEN DE VENTA: 703" | 224 |
| DEVOLUCION DE VENTA | numerico | "DEVOLUCION DE VENTA: 1" | 45 |
| ENTREGA DE ALQUILER | numerico | "ENTREGA DE ALQUILER: 2" | 31 |
| NOTA DEBITO DE VENTA | PPAL-NNN o numerico | "NOTA DEBITO DE VENTA: PPAL-1" | 3 |
| DEVOLUCION DE COMPRA | numerico | | 2 |
| DEVOLUCION DE ALQUILER | numerico | | 1 |
| DOC SOPORTE NO OBLIGADOS | numerico | | 1 |

**Nota sobre IDs PPAL-:** Entre feb 2025 y feb 2025 hubo un periodo breve donde Effi uso
el formato "PPAL-NNN" para OPs (718 a 761, 179 registros). Antes y despues usa ID numerico
puro. El ID en trazabilidad **SI corresponde** al id_orden de `zeffi_produccion_encabezados`
(excepto en ese periodo PPAL-).

Para extraer el ID numerico:
```sql
CAST(REPLACE(REPLACE(SUBSTRING(transaccion, INSTR(transaccion, ':')+2), 'PPAL-', ''), ' ', '') AS UNSIGNED)
```

### Convencion de signos
- **Positivo** = ingreso a bodega (compra, produccion de PT, devolucion, ajuste positivo)
- **Negativo** = egreso de bodega (venta, consumo MP en produccion, traslado de salida, ajuste negativo)
- Confirmado: 5,721 positivos + 15,070 negativos en movimientos vigentes

### Vigencia y anulaciones
- `vigencia_de_transaccion = 'Transaccion vigente'` → movimiento activo, afecta stock
- `vigencia_de_transaccion = 'Transaccion anulada'` → movimiento revertido, NO afecta stock

Cuando se anula una transaccion, Effi genera 2 registros en trazabilidad:
1. La "Creacion de transaccion" original queda marcada como "Transaccion anulada"
2. Se agrega una "Anulacion de transaccion" con el signo invertido, tambien "Transaccion anulada"

**Para reconstruir stock, usar SOLO registros con:**
- `vigencia_de_transaccion = 'Transaccion vigente'`
- `tipo_de_movimiento = 'Creacion de transaccion'`

### Traslados en trazabilidad
Un traslado genera **2 lineas** por articulo:
1. Egreso de bodega origen (cantidad negativa)
2. Ingreso a bodega destino (cantidad positiva)

Ejemplo — Traslado 517 (1 Chocomiel de "No Conformes" a "Principal"):
- Linea 1: bodega="Productos No Conformes", cantidad="-1,00"
- Linea 2: bodega="Principal", cantidad="1,00"

### Ordenes de Produccion en trazabilidad
Una OP genera **multiples lineas** por articulo:
- Materias primas: cantidad **negativa** (salen de bodega)
- Productos terminados: cantidad **positiva** (entran a bodega)

Ejemplo — OP 2088 (Nibs de cacao):
- NIBS DE CACAO X KG LT: -1.40 (materia prima consumida)
- Bolsas, etiquetas: -1 a -6 c/u (insumos consumidos)
- NIBS DE CACAO 100 GRS: +6.00 (producto terminado)
- NIBS DE CACAO 200 GRS: +4.00 (producto terminado)

### Export: `export_trazabilidad.js`
- URL: `https://effi.com.co/app/trazabilidad_inventario?sucursal=1`
- **Sin filtro `?vigente=1`** → trae vigentes Y anulados (necesario para trazabilidad completa)
- Salida: `/exports/trazabilidad/trazabilidad_YYYY-MM-DD.xlsx`

---

## 3. Ordenes de Produccion

Las OPs en Effi representan procesos de transformacion: se consumen materias primas + insumos
y se producen articulos terminados. Los datos se distribuyen en **5 tablas**:

### Logica de negocio — como se programa una OP en OS

**Flujo real en la empresa**: para programar produccion de un articulo, se busca una OP HISTORICA
del mismo articulo y se **replica** la receta. Esto implica que existen "plantillas" de receta
embebidas en las OPs pasadas.

**Verificado empiricamente (2026-04-21) con 5 productos recurrentes**:

| Producto | Cod | Patron | Detalle |
|---|---|---|---|
| Cobertura 73% | 319 | **Lote fijo 4kg** | 7 materiales en cantidades identicas en 5 de 5 OPs 2026. Siempre 4kg, M.O. 2.35h |
| Tableta 73% Macadamia | 482 | **Lote fijo 25-30 uds** | 1.05kg cobertura + 0.45kg macadamia produce entre 25-30 tabletas (rinde varia) |
| Tableta 73% Almendra | 483 | **Lote fijo similar** | 0.95kg cobertura + 0.41kg almendras → ~16 unidades |
| Nibs 100g | 317 | **Escalable por unidad** | 0.1kg nibs + 1 bolsa + 2 etiquetas por unidad producida (ratio exacto en 6 OPs) |
| Miel 640g | 15 | **Escalable por unidad** | 0.64kg miel + 1 envase + 2 etiquetas por unidad (ratio exacto en 4 OPs) |
| Chocolate Mesa Moldeado 93 | Co-producto | **OP produce 93 + 73 simultaneamente** | 8kg nibs rinde 4kg moldeado + 4kg bloque 24H |

**Dos grandes patrones de receta**:

1. **Lote fijo**: cantidades de materiales son FIJAS. Producir mas = mas lotes, no mas insumos por lote.
   - Cobertura 73%: siempre 4kg con 2.30+0.70+0.40+0.35+0.12+0.01+0.64 kg de materiales
   - Tabletas CPM: lote estandar de ~25-30 tabletas con materiales fijos
   - M.O. (horas) es tambien fija por lote

2. **Escalable por unidad**: cantidad de materiales = cantidad producida x ratio fijo.
   - Nibs, etiquetas, envases, tapas: 1:1 con unidades producidas
   - Miel x 640g: 0.64 kg miel por unidad

**Co-productos y desperdicios registrados**:
Algunas OPs tienen multiples productos principales (ej: Moldeado + Bloque 24H juntos).
Otras incluyen articulos tipo "DESPERDICO - ..." como producto secundario para balancear
el consumo vs la produccion real (ej: 0.80kg desperdicio al producir 16 tabletas).

**OPs mixtas (empacado)**:
Algunas OPs procesan multiples formatos en un solo proceso. Ejemplo OP 2077 (mar-26) produjo
Miel 150g + 275g + 640g + 1000g simultaneamente desde los formatos "SIN ETIQUETAR" usando
un costo aparte "ENVASADO MIEL APICA (INCLUYE F)" x 241 unidades.

**Implicaciones para programar OPs via script** (`import_orden_produccion.js`):

1. Para replicar: buscar la ultima OP del articulo donde ese articulo sea el UNICO producto
   (o donde este presente) y copiar materiales exactos.
2. Para escalar: identificar si es lote fijo o escalable:
   - Si cantidad producida varia pero materiales son identicos entre OPs → lote fijo
   - Si cantidad producida y materiales escalan proporcionalmente → escalable
3. Siempre agregar M.O. (costo de produccion) — en OS siempre "M.O. HORA ORIGEN SILVESTRE" a $7000/h
4. Si hay dos productos producidos en OPs historicas, incluir ambos (co-productos).
5. Revisar si hay desperdicio registrado, incluirlo proporcionalmente.



### 3.1. Encabezados — `zeffi_produccion_encabezados`

**Total**: 2,088 OPs (1,104 vigentes, 984 anuladas)

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id_orden | TEXT | ID unico de la OP (numerico) | "2088" |
| sucursal | TEXT | Siempre "Principal" | "Principal" |
| bodega | TEXT | Bodega donde se ejecuta | "Principal" |
| nombre_encargado | TEXT | Persona que ejecuta | "Deivy Andres Gonzalez Gutierrez" |
| id_encargado | TEXT | Identificacion con prefijo tipo | "CC: 74084937" |
| tipo_encargado | TEXT | Relacion con la empresa | "Empleado." o "Cliente." o "Proveedor." |
| nombre_tercero | TEXT | Tercero asociado (opcional) | NULL |
| id_tercero | TEXT | ID tercero (opcional) | NULL |
| tipo_tercero | TEXT | Tipo tercero (opcional) | NULL |
| activo_productivo | TEXT | Maquina/equipo utilizado | NULL (no se usa actualmente) |
| fecha_inicial | TEXT | Fecha inicio programada | "2026-03-28 00:00:00" |
| fecha_final | TEXT | Fecha fin programada | "2026-03-28 00:00:00" |
| total_precios_de_venta | TEXT | Valor total a precio de venta de los PT | "132738,0" |
| costo_de_materiales | TEXT | Costo total de materias primas | "46267,1" |
| otros_costos_de_produccion | TEXT | Mano de obra + servicios externos | "11200,0" |
| beneficio_neto | TEXT | = total_precios - costo_materiales - otros_costos | "75270,9" |
| observacion | TEXT | Notas libres (que se produce, lote) | "Nibs de cacao 100g Y 200G\nLOTE" |
| estado | TEXT | **Estado actual de la OP** | "Generada" o "Procesada" |
| vigencia | TEXT | Si la OP esta activa o anulada | "Vigente" o "Anulado" |
| fecha_de_creacion | TEXT | Cuando se creo en Effi | "2026-03-28 22:54:25" |
| responsable_de_creacion | TEXT | Quien la creo | "Jennifer Alexandra Cano Garcia (...)" |
| fecha_de_anulacion | TEXT | Cuando se anulo (si aplica) | NULL |
| responsable_de_anulacion | TEXT | Quien la anulo | NULL |

### Estados de una OP

| Estado | Vigencia | Cantidad | Significado |
|---|---|---|---|
| **Generada** | **Vigente** | **81** | OP creada, Effi ya desconto MP y cargo PT en inventario, pero la produccion NO se ejecuto fisicamente |
| Generada | Anulado | 889 | OP generada pero luego anulada (se revierten los movimientos de inventario) |
| Procesada | Vigente | 1,023 | OP completada: la produccion SI se ejecuto, inventario refleja la realidad |
| Procesada | Anulado | 95 | OP procesada pero luego anulada |

**El ciclo de vida de una OP es:**
```
Generada (Vigente) → Procesada (Vigente)    [flujo normal]
Generada (Vigente) → Generada (Anulado)     [se cancela antes de producir]
Procesada (Vigente) → Procesada (Anulado)   [se reversa despues de producir]
```

**Impacto critico en inventario:**
Cuando una OP pasa a estado "Generada", Effi **inmediatamente**:
1. Descuenta las materias primas del stock (como si se hubieran consumido)
2. Suma los productos terminados al stock (como si ya estuvieran producidos)

Pero la produccion **aun no ha ocurrido**. Esto genera una discrepancia entre el
inventario teorico de Effi y el inventario fisico real.

### Export: `export_produccion_encabezados.js`
- URL: `https://effi.com.co/app/orden_produccion`
- Trae todas las OPs (vigentes + anuladas, generadas + procesadas)
- Salida: `/exports/produccion/encabezados_prod/produccion_encabezados_YYYY-MM-DD.xlsx`

---

### 3.2. Materiales (Materias Primas) — `zeffi_materiales`

Detalle de los materiales/insumos consumidos en cada OP.

**Total**: ~4,497 lineas (309 en OPs generadas vigentes)

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id_orden | TEXT | ID de la OP (= encabezados.id_orden) | "2088" |
| sucursal | TEXT | "Principal" | |
| bodega | TEXT | Bodega de donde sale el material | "Principal" |
| nombre_encargado | TEXT | = encabezados.nombre_encargado | |
| id_encargado | TEXT | = encabezados.id_encargado | |
| tipo_encargado | TEXT | = encabezados.tipo_encargado | |
| cod_material | TEXT | ID del articulo consumido | "178" |
| descripcion_material | TEXT | Nombre del material | "NIBS DE CACAO X KG LT" |
| categoria | TEXT | Categoria del material | "T01.03. AGROECOLOGICOS GRAL" |
| referencia | TEXT | Referencia (raro que se use) | NULL |
| lote | TEXT | Lote del material (raro) | NULL |
| serie | TEXT | Serie (no se usa) | NULL |
| cantidad | TEXT | Cantidad consumida (coma decimal) | "1,40" |
| costo_ud | TEXT | Costo unitario | "24000,0000" |
| observacion_de_orden | TEXT | = encabezados.observacion | |
| vigencia | TEXT | Estado del material en la OP | "Orden vigente" u "Orden anulada" |
| responsable | TEXT | Quien registro | |
| fecha_creacion | TEXT | Cuando se creo | |

**Atencion**: El campo `vigencia` en materiales usa valores distintos a otras tablas:
- `"Orden vigente"` (no "Vigente")
- `"Orden anulada"` (no "Anulado")

**Categorias de materiales mas frecuentes:**
| Categoria | Lineas |
|---|---|
| T01.03. AGROECOLOGICOS GRAL | 1,739 (materias primas base) |
| T03.21. ETIQUETAS ADESIVAS | 1,146 (etiquetas) |
| T03.01. ENVASES Y TAPAS | 642 (envases) |
| T03.03. ENVASES ECOLOGICOS | 293 (envases eco) |
| T03.31. BOLSAS PLASTICAS | 196 (bolsas) |

### Export
Exportado por `export_produccion_reportes.js` → "Reporte de materiales"
Salida: `/exports/produccion/materiales/materiales_YYYY-MM-DD.xlsx`

---

### 3.3. Articulos Producidos — `zeffi_articulos_producidos`

Detalle de los productos terminados que salen de cada OP.

**Total**: ~1,860 lineas (142 en OPs generadas vigentes)

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id_orden | TEXT | ID de la OP | "2088" |
| sucursal | TEXT | "Principal" | |
| bodega | TEXT | Bodega donde entra el PT | "Principal" |
| cod_articulo | TEXT | ID del articulo producido | "317" |
| descripcion_articulo_producido | TEXT | Nombre del PT | "NIBS DE CACAO ORGANICO OS 100 GRS" |
| categoria | TEXT | Categoria del PT | "TPT.01. VENTA AGROECOLOGICOS VARIOS" |
| referencia | TEXT | Referencia | NULL |
| lote | TEXT | Lote asignado | NULL |
| serie | TEXT | Serie | NULL |
| cantidad | TEXT | Cantidad producida (coma decimal) | "6,00" |
| precio_minimo_ud | TEXT | Precio minimo de venta | "10795,00" |
| observacion_orden | TEXT | = encabezados.observacion | |
| vigencia | TEXT | "Orden vigente" u "Orden anulada" | |
| responsable | TEXT | Quien registro | |
| fecha_creacion | TEXT | Cuando se creo | |

**Categorias de articulos producidos mas frecuentes:**
| Categoria | Lineas |
|---|---|
| TPT.01. VENTA AGROECOLOGICOS VARIOS | 1,303 (productos de venta) |
| T01.03. AGROECOLOGICOS GRAL | 448 (intermedios) |
| DESARROLLO DE PRODUCTO | 44 |

### Export
Exportado por `export_produccion_reportes.js` → "Reporte de articulos producidos"
Salida: `/exports/produccion/articulos_producidos/articulos_producidos_YYYY-MM-DD.xlsx`

---

### 3.4. Cambios de Estado — `zeffi_cambios_estado`

Registro historico de cuando una OP cambia de estado (tipicamente Generada → Procesada).

**Total**: 1,156 registros

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id_orden | TEXT | ID de la OP | "1991" |
| nuevo_estado | TEXT | Estado al que cambio | "Procesada" |
| observacion_estado | TEXT | Nota del cambio (raro) | NULL |
| f_cambio_de_estado | TEXT | Fecha/hora del cambio | "2026-02-17 03:40:46" |
| responsable_cambio_de_estado | TEXT | Quien cambio el estado | |
| bodega, nombre_encargado, etc. | TEXT | Datos repetidos del encabezado | |
| total_precios_de_venta | TEXT | Valores al momento del cambio | |
| costo_de_materiales | TEXT | | |
| otros_costos_de_produccion | TEXT | | |
| beneficio_neto | TEXT | | |
| vigencia | TEXT | "Vigente" o "Anulado" | |

**Uso principal**: Saber **cuando** se proceso realmente una OP (fecha real de produccion
vs fecha de creacion). Util para reconstruccion historica.

### Export
Exportado por `export_produccion_reportes.js` → "Reporte de cambios de estado"
Salida: `/exports/produccion/cambios_estado/cambios_estado_YYYY-MM-DD.xlsx`

---

### 3.5. Otros Costos de Produccion — `zeffi_otros_costos`

Costos adicionales asociados a cada OP (mano de obra, servicios externos, transporte).

**Total**: 1,175 registros

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| id_orden | TEXT | ID de la OP | "2088" |
| costo_de_produccion | TEXT | Tipo de costo + unidad | "M.O. HORA ORIGEN SILVESTRE (Hora)" |
| cantidad | TEXT | Cantidad (horas, kilos, etc.) | "1,60" |
| costo_ud | TEXT | Costo unitario | "7000,0000" |
| vigencia | TEXT | "Orden vigente" u "Orden anulada" | |
| fecha_inicio | TEXT | Desde cuando aplica | |
| fecha_fin | TEXT | Hasta cuando aplica | |
| fecha_creacion | TEXT | Cuando se registro | |

### Catalogo de costos — `zeffi_costos_produccion`

Tabla catalogo (15 items) con los tipos de costo disponibles:

| ID | Nombre |
|---|---|
| 1 | REFINADO CACAO 24H CHOCOFRUTS |
| 2 | PREPARACION CHOCOMIEL CHOCOFRUTS |
| 3 | DESCASCARILLADO CACAO CHOCOFRUTS |
| 4 | TOSTADO CACAO CHOCOFRUTS |
| 5 | FILTRADO MIEL APICA |
| 6 | REFINADO Y ENMOLDADO HECTOR BAKAU |
| 7 | OBTENCION NIBS DE CACAO X KG INTAL |
| 8 | ENVASADO MIEL APICA (INCLUYE FILTRADO) |
| 9 | LICOR DE CACAO INTAL (incluye tostion y descascarillado) |
| 10 | TEMPERADO Y EMPACADO MOLDE - 100G |
| 11 | TEMPERADO Y EMPACADO MOLDE 100 Y 250 G |
| 12 | TEMPERADO Y EMPACADO MOLDE + 250G |
| 13 | M.O. HORA ORIGEN SILVESTRE |
| 14 | TOSTADO Y DESCASCARILLADO ARBOL DE CACAO KILO 4800 |
| 15 | TRANSPORTE BUCARAMANGA X KILO |

### Export
- Otros costos por OP: `export_produccion_reportes.js` → "Reporte de otros costos de produccion"
  Salida: `/exports/produccion/otros_costos/otros_costos_YYYY-MM-DD.xlsx`
- Catalogo: `export_costos_produccion.js`
  URL: `https://effi.com.co/app/mantenimiento_tablas/costo_produccion`
  Salida: `/exports/costos_produccion/costos_produccion_YYYY-MM-DD.xlsx`

---

## 4. Ajustes de Inventario (zeffi_ajustes_inventario)

Registros de ajustes manuales al inventario (entradas o salidas por conteo fisico,
mermas, correcciones, etc.).

**Total**: 356 (313 vigentes, 43 anulados)

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| codigo | TEXT | ID del ajuste | "1" |
| sucursal | TEXT | "Principal" | |
| bodega | TEXT | Bodega ajustada | "Principal" |
| articulos | TEXT | Resumen de articulos | "2 - Generico" |
| vigencia | TEXT | "Vigente" o "Anulado" | |
| fecha_de_creacion | TEXT | Timestamp | "2023-11-16 11:36:55" |
| responsable_de_creacion | TEXT | Quien lo hizo | |
| fecha_de_anulacion | TEXT | Si se anulo | NULL |
| responsable_de_anulacion | TEXT | Quien anulo | NULL |

**Nota**: Esta tabla es un **resumen por ajuste** (1 fila = 1 ajuste, puede incluir N articulos).
El detalle articulo por articulo esta en `zeffi_trazabilidad` con transaccion "AJUSTE DE INVENTARIO: X".

### Export: `export_ajustes_inventario.js`
- URL: `https://effi.com.co/app/ajuste_inventario` (sin filtro)
- Salida: `/exports/ajustes_inventario/ajustes_inventario_YYYY-MM-DD.xlsx`

---

## 5. Traslados de Inventario (zeffi_traslados_inventario)

Movimientos de articulos entre bodegas.

**Total**: 517 (415 vigentes, 102 anulados)

| Campo | Tipo | Descripcion | Ejemplo |
|---|---|---|---|
| codigo | TEXT | ID del traslado | "1" |
| sucursal_de_origen | TEXT | Sucursal origen | "Principal" |
| bodega_de_origen | TEXT | Bodega origen | "Apica" |
| sucursal_de_destino | TEXT | Sucursal destino | "Principal" |
| bodega_de_destino | TEXT | Bodega destino | "El Salvador" |
| articulos | TEXT | Resumen | "MIEL OS PLASTICO 500grs y 2 conceptos mas" |
| observacion | TEXT | Nota libre | "se llevo donde dario lo de apica" |
| vigencia | TEXT | "Vigente" o "Anulado" | |

**Nota**: Igual que ajustes, esta tabla es **resumen por traslado**. El detalle articulo por
articulo esta en `zeffi_trazabilidad` con transaccion "TRASLADO DE INVENTARIO: X".

### Export: `export_traslados_inventario.js`
- URL: `https://effi.com.co/app/traslado_inventario` (sin filtro)
- Salida: `/exports/traslados_inventario/traslados_inventario_YYYY-MM-DD.xlsx`

---

## 6. Bodegas (zeffi_bodegas)

15 bodegas activas, todas en sucursal "Principal".

| ID | Nombre | Uso principal |
|---|---|---|
| 1 | Principal | Bodega central — todo tipo de articulo (MP, insumos, PT) |
| 2 | Villa de aburra | Punto de venta externo |
| 3 | Apica | Proveedor/aliado (miel) |
| 4 | El Salvador | Punto de venta externo |
| 5 | Feria Santa Elena | Punto de venta feria |
| 6 | DON LUIS SAN MIGUEL | Proveedor/aliado |
| 7 | LA TIERRITA | Proveedor/aliado |
| 8 | Jenifer | Producto terminado de venta (gestion Jenifer) |
| 10 | REGINALDO | Punto de venta/aliado |
| 13 | Desarrollo de Producto | Articulos en desarrollo |
| 14 | Ricardo | Punto de venta/aliado |
| 15 | Mercado Libre | Canal de venta online |
| 16 | Santiago | Inventario personal Santiago |
| 17 | Productos No Conformes Bod PPAL | Productos defectuosos o no conformes |
| 18 | FERIA CAMPESINA SAN CARLOS | Punto de venta feria |

### Bodegas con mayor movimiento (trazabilidad vigente)
| Bodega | Movimientos |
|---|---|
| Principal | 14,868 |
| Jenifer | 4,996 |
| Feria Santa Elena | 518 |
| Desarrollo de Producto | 107 |
| Ricardo | 95 |
| REGINALDO | 66 |

### Export: `export_bodegas.js`
- URL: `https://effi.com.co/app/mantenimiento_tablas/bodega`

---

## 7. Relaciones entre tablas

```
zeffi_produccion_encabezados (id_orden)
  ├── zeffi_materiales (id_orden)           → MP/insumos consumidos
  ├── zeffi_articulos_producidos (id_orden) → PT generados
  ├── zeffi_otros_costos (id_orden)         → M.O. y servicios
  └── zeffi_cambios_estado (id_orden)       → historial Generada→Procesada

zeffi_trazabilidad (transaccion = "TIPO: id_orden")
  ├── refleja movimientos de OPs
  ├── refleja movimientos de facturas, remisiones, ajustes, traslados
  └── campo id_articulo = inventario.id

zeffi_inventario (id)
  └── foto actual del stock por bodega

zeffi_ajustes_inventario (codigo)
  └── resumen por ajuste (detalle en trazabilidad)

zeffi_traslados_inventario (codigo)
  └── resumen por traslado (detalle en trazabilidad)

zeffi_costos_produccion (id)
  └── catalogo de tipos de costo → referenciado por zeffi_otros_costos.costo_de_produccion
```

---

## 8. Logica de reconstruccion de stock a fecha

### Formula
```
stock_bodega_fecha = stock_actual_bodega - SUM(movimientos desde fecha_objetivo+1 hasta hoy)
```

### Filtros para la query de trazabilidad
```sql
WHERE vigencia_de_transaccion = 'Transacción vigente'
  AND tipo_de_movimiento = 'Creación de transacción'
  AND bodega = ?
  AND fecha > ?   -- desde el dia siguiente a la fecha objetivo
```

### Parseo de cantidad
```sql
CAST(REPLACE(cantidad, ',', '.') AS DECIMAL(12,4))
```

### Ejemplo
Si quiero saber el stock de "Miel Os Vidrio 640 grs" en bodega "Principal" al 28 de febrero:
```sql
stock_28feb = stock_actual_principal
            - SUM(cantidad WHERE fecha > '2026-02-28 23:59:59')
```
Si entre marzo 1 y hoy se vendieron 10 unidades (cantidad=-10 en trazabilidad):
```
stock_28feb = stock_actual - (-10) = stock_actual + 10
```

---

## 9. Logica de ajuste por OPs generadas

### Problema
Las 81 OPs en estado "Generada" + vigencia "Vigente" ya movieron el inventario en Effi,
pero la produccion NO se ejecuto. El inventario fisico NO refleja estos movimientos.

### Ajuste
```
Para cada OP con estado='Generada' AND vigencia='Vigente':

  -- Devolver materias primas (Effi las desconto pero fisicamente siguen ahi)
  stock_ajustado[cod_material] += cantidad_material

  -- Quitar productos terminados (Effi los sumo pero fisicamente no existen)
  stock_ajustado[cod_articulo] -= cantidad_producida
```

### Fuente de datos
```sql
-- Materiales a devolver
SELECT cod_material, SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,4))) AS total
FROM zeffi_materiales m
JOIN zeffi_produccion_encabezados pe ON m.id_orden = pe.id_orden
WHERE pe.estado = 'Generada' AND pe.vigencia = 'Vigente' AND m.vigencia = 'Orden vigente'
GROUP BY cod_material;

-- Productos terminados a quitar
SELECT cod_articulo, SUM(CAST(REPLACE(cantidad,',','.') AS DECIMAL(12,4))) AS total
FROM zeffi_articulos_producidos ap
JOIN zeffi_produccion_encabezados pe ON ap.id_orden = pe.id_orden
WHERE pe.estado = 'Generada' AND pe.vigencia = 'Vigente' AND ap.vigencia = 'Orden vigente'
GROUP BY cod_articulo;
```
