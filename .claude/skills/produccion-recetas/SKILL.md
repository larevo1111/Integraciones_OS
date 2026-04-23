---
name: produccion-recetas
description: Cómo construir recetas correctas para crear órdenes de producción (OPs) en Effi. Triggers - orden de producción, OP, receta, tableta, cobertura, templada, frutos secos, macadamia, almendra, mani, nibs, empacar, sin empacar, manteca, cacao, moldería, lote.
---

# Skill — Construcción de recetas de producción (Origen Silvestre)

Cómo armar una OP correcta en Effi: **cantidades físicas** (receta), **costos** (materiales), **precios** (producidos), **flujo de OPs en cadena** y **ejecución con el script**.

## Regla cero

**NUNCA inventar cantidades, costos o precios**. Cada valor debe salir de:
- **BD `effi_data`** (catálogo + histórico de OPs vigentes), o
- **Confirmación explícita de Santi**.

Si no podés confirmar un valor desde la BD, **detenete y preguntá**. Inventar (aunque sea "redondeando" o "siendo conservador") rompe reportes contables y genera OPs a anular.

---

## 1. Costos y precios — fuente de verdad

Validado con las OPs correctas 2191/2194/2195 (2026-04-22). Los valores que Effi pre-llena al crear OP manual vienen de acá:

| Campo del JSON | Tabla / columna | Notas |
|---|---|---|
| `materiales[].costo` | `zeffi_inventario.costo_manual` | Effi pre-llena con este valor. **Nunca** usar `costo_promedio` ni `ultimo_costo`. |
| `articulos_producidos[].precio` | Último `zeffi_articulos_producidos.precio_minimo_ud` del mismo cod en OPs vigentes | El catálogo `precio_minimo_de_venta` está en **0** para casi todo. Effi lo guarda internamente en una tabla que **no exportamos** pero el valor actual coincide siempre con la última OP vigente. |
| `otros_costos[].costo` | Manual / acordado con Santi | Ej: mano de obra (REFINADO CACAO 24H CHOCOFRUTS) se paga por hora. |

### Queries listas para copiar/pegar

**Costos de materiales** (catálogo):
```sql
SELECT id AS cod, nombre, costo_manual
FROM zeffi_inventario
WHERE id IN ('319','485','581','196','114','508','178','412','480','481','482','483','484')
  AND vigencia='Vigente'
ORDER BY CAST(id AS UNSIGNED);
```

**Precios de productos producidos** (último valor vigente, descartando OPs propias malas):
```sql
SELECT cod_articulo,
       MAX(descripcion_articulo_producido) AS descripcion,
       SUBSTRING_INDEX(GROUP_CONCAT(precio_minimo_ud ORDER BY fecha_creacion DESC), ',', 1) AS ultimo_precio,
       MAX(fecha_creacion) AS ultima_fecha
FROM zeffi_articulos_producidos
WHERE cod_articulo IN ('480','481','482','483','484','320','493','494','495','496','581')
  AND vigencia='Orden vigente'
  AND CAST(REPLACE(precio_minimo_ud, ',', '') AS DECIMAL(18,4)) > 100
GROUP BY cod_articulo
ORDER BY CAST(cod_articulo AS UNSIGNED);
```

### Tabla de referencia confirmada (2026-04-22)

| Cod | Producto | `costo_manual` (mat) | Último `precio_minimo_ud` (prod) |
|---|---|---|---|
| 319 | Cobertura 73% sin templar | $43,432 | — |
| 485 | Manteca cacao templada | $50,000 | — |
| 581 | Cobertura 73% templada | $43,432 | $43,432 (no hay histórico bueno → usar `costo_manual`) |
| 196 | Macadamia tostada | $100,000 | — |
| 114 | Maní sin cáscara | $17,000 | — |
| 508 | Almendras tostadas | $42,000 | — |
| 178 | Nibs cacao | $24,000 | — |
| 412 | Caja chocolate oscuro | $1,000 | — |
| 480-484 | Tabletas sin empacar | $5,200 | **$8,900** |
| 320, 493-496 | Tabletas empacadas | — | **$10,529** |

**Nota**: el precio histórico **cambia en el tiempo** (Effi actualiza el valor internamente cada X meses). Por eso hay que consultar la BD cada vez — no hardcodear.

### Anti-patrones
❌ Inventar el precio "redondeando" o "siendo conservador" → distorsiona Total venta / Beneficio neto.
❌ Usar `costo_promedio` o `ultimo_costo` del catálogo en lugar de `costo_manual`.
❌ Asumir que `precio_minimo_de_venta` del catálogo tiene el valor correcto (está en 0 para casi todo).

---

## 1.bis Heurística de sentido común — el nombre del producto dice la receta

**Antes de hacer ninguna query, leé el nombre**. En OS los nombres de productos envasados incluyen el peso/volumen en gramos o ml. Ese número **es la cantidad del material principal por unidad**.

### Ejemplos directos

| Nombre del producto | Peso en nombre | Material principal por unidad |
|---|---|---|
| Miel Os Vidrio **640 grs** | 640 g | **0.640 kg** de miel x kilo |
| Miel Os Vidrio **1000 grs** | 1000 g | **1.000 kg** de miel x kilo |
| Miel Os Vidrio **150 grs** | 150 g | **0.150 kg** de miel x kilo |
| Tableta Chocolate 73% **x 50grs** | 50 g | **0.050 kg** de cobertura (puro) — o cobertura + inclusión según mezcla §3 |
| CHOCOMIEL OS **250cc** | 250 ml | ≈ 0.250 kg / L de chocomiel granel |
| MIEL APICA X **180 GR** | 180 g | 0.180 kg de miel apica granel |

### Cómo aplicarlo

1. **Leé el nombre del producto** y extraé el número con su unidad (`g`, `grs`, `gramos`, `kg`, `kilo`, `cc`, `ml`).
2. Convertí a **kg** (o L, si es líquido).
3. Esa es la cantidad por unidad del **material principal**.
4. **Para descubrir CUÁL material principal**: mirá las OPs históricas del producto y agrupá por `cod_material`. El más usado es el material principal. Suele ser obvio por el nombre (`Miel ...` → busca un material `MIEL ... x KILO`; `Cobertura ...` → `COBERTURA ... x KILO`).
5. Para los **insumos secundarios** (envases, etiquetas, cajas) → consultá OPs históricas, son 1:1 por unidad producida.

### Por qué esta heurística importa

`sugerir_receta.py` actualmente descarta OPs con co-productos (mixtas). Pero las mieles, chocolates, etc. casi SIEMPRE se producen mezcladas en una sola OP (por eficiencia). Resultado: el script encuentra 1 OP "pura" y sugiere mal.

**Con la heurística del nombre no necesitás "OPs puras"**:
- 640 grs → siempre 0.640 kg de miel granel, no importa con qué se mezcló
- Las OPs mixtas SIRVEN para confirmar (verificá que la suma de pesos cuadre con la miel total usada)

### Regla 3 de 5 (validación)

Aún con la heurística, validá tomando **5 OPs vigentes** del producto. Si **3 o más** confirman el ratio (peso del nombre = kg de material principal por unidad), está confirmado. Si menos → sospechar y preguntar.

```sql
-- Validar 1:1 contra histórico de un producto
-- Para cada OP, calcular: kg_miel_total / suma(peso_de_nombres × cantidad_producida)
-- Debería dar ~1.00 si la heurística aplica
```

---

## 2. Cantidades — metodología de 5 pasos

### Paso 1 — Identificar la versión MÁS BÁSICA del producto

Muchos productos tienen 2-3 versiones en Effi:
- **"sin empacar"** — producto base recién hecho. Contiene la receta CRUDA (cobertura + frutos secos, etc.)
- **"empacado"** — base + caja / etiqueta / bolsa.
- **"templado"** — versión templada de coberturas (proceso adicional).

**SIEMPRE arranca por la versión sin empacar** — ahí está la receta real. La empacada solo agrega caja.

```sql
-- PRIMERO buscar versión sin empacar:
SELECT id, nombre FROM zeffi_inventario
WHERE vigencia='Vigente'
  AND nombre LIKE '%nibs%'
  AND nombre LIKE '%sin empacar%';
-- → cod 484 = "Tableta Chocolate 73% con Nibs x 50grs CPM (sin empacar)"

-- LUEGO la versión empacada (solo agrega caja):
SELECT id, nombre FROM zeffi_inventario
WHERE vigencia='Vigente'
  AND nombre LIKE '%nibs%'
  AND nombre NOT LIKE '%sin empacar%';
-- → cod 496 = "Tableta Chocolate 73p con Nibs 50 grs CPM"
```

### Paso 2 — Traer las últimas OPs vigentes que produjeron esa versión

```sql
SELECT ap.id_orden, e.fecha_de_creacion, ap.cantidad
FROM zeffi_articulos_producidos ap
JOIN zeffi_produccion_encabezados e ON e.id_orden = ap.id_orden
WHERE ap.cod_articulo = '484'              -- el "sin empacar"
  AND ap.vigencia = 'Orden vigente'
  AND e.vigencia = 'Vigente'
ORDER BY e.fecha_de_creacion DESC LIMIT 5;
```

### Paso 3 — Para cada OP, traer materiales y calcular el ratio

```sql
SELECT cod_material, descripcion_material, cantidad
FROM zeffi_materiales WHERE id_orden = '2162' AND vigencia = 'Orden vigente';
```

Ej: 24 tabletas con nibs (1.2 kg producidos):
- Cobertura 319: 1.00 kg
- Nibs 178: 0.25 kg
- Ratio nibs sobre peso final: 0.25 / 1.20 = **20%** ← sale del cálculo, NO te lo inventas

### Paso 4 — CORROBORAR con al menos 2 OPs distintas

Una sola OP puede tener errores de captura. **Mínimo 2 OPs con el mismo ratio** para confianza alta. Si difieren:
- Investigá la discrepancia (¿merma? ¿OP de prueba?)
- Pregúntale a Santi antes de actuar

### Paso 5 — Escalar al pedido nuevo + verificar suma

Aplicá los porcentajes al pedido. **La suma de materiales debe igualar el peso del producto producido** (descontando merma).

---

## 3. Porcentajes confirmados — TABLETAS 50g

Validados por la metodología arriba en múltiples OPs:

| Tableta | Cobertura | Inclusión | Por unidad (50g) | OPs ref. |
|---|---|---|---|---|
| **Chocolate puro** | 100% | — | 50g cobertura | 2033, 2065 |
| **Macadamia** | 70% | 30% macadamia | 35g cob + 15g mac | 2064, 2174 |
| **Maní** | 70% | 30% maní | 35g cob + 15g maní | 2063 |
| **Almendra** | 70% | 30% almendra | 35g cob + 15g alm | 2062 |
| **Nibs** | 80% | 20% nibs | 40g cob + 10g nibs | 2162 |

**Regla resumen**:
- Frutos secos (maní, macadamia, almendra) = **30% inclusión / 70% cobertura** = **15g + 35g por tableta**
- Nibs = **20% inclusión / 80% cobertura** = **10g + 40g por tableta**
- Chocolate puro = **100% cobertura** = **50g por tableta**

**Cálculo rápido para un pedido**:
```
inclusión_total (kg) = (N_tabletas_frutosecos × 0.015) + (N_tabletas_nibs × 0.010)
cobertura_total (kg) = N_total × 0.050  −  inclusión_total
```

Ejemplo: 50 puro + 30 mac + 30 mani + 11 alm + 15 nibs (= 136 tabletas)
- Inclusión = (30+30+11) × 0.015 + 15 × 0.010 = 1.065 + 0.150 = **1.215 kg**
- Cobertura = 136 × 0.050 − 1.215 = 6.800 − 1.215 = **5.585 kg**

---

## 4. Capacidad de moldería — restricción al pedido

**La moldería es el límite real de producción**. Cada lote de tabletas usa N moldes con M tabletas cada uno. Caso típico: 34 moldes × 4 tabletas = **136 tabletas máximo por OP**.

Cuando Santi dice "tengo X kg para tabletas":
- X kg es el **peso TOTAL del producto final** (cobertura + inclusión juntos).
- Para saber cuánta cobertura templada necesitás: **`cobertura = X_total − sum(inclusiones)`**.

Ejemplo:
- Pedido: 50 puro + 30 mac + 30 maní + 11 alm + 15 nibs = 136 tabletas × 50g = 6.8 kg total
- Inclusiones: 30×15g (mac) + 30×15g (mani) + 11×15g (alm) + 15×10g (nibs) = 1.215 kg
- **Cobertura templada necesaria: 6.8 − 1.215 = 5.585 kg**

---

## 5. Cobertura templada vs sin templar — 4 productos similares

Cuidado con confundirlos:

| Cod | Nombre | Uso |
|---|---|---|
| 193 | MANTECA DE CACAO X KG | Sin templar — se usa para producir cobertura 73% (cod 319) |
| 485 | MANTECA DE CACAO **TEMPLADA** X KG | Templada — solo para método de siembra |
| 319 | COBERTURA CHOCOLATE 73% OS X KILO | Base sin templar — se produce por lote fijo de 4 kg |
| 581 | COBERTURA CHOCOLATE 73% OS X KILO **- TEMPLADA** | Templada (siembra) — es lo que va en las tabletas de chocolatería |

### Cómo se produce cobertura templada (cod 581) — método siembra
- Material 1: cobertura sin templar cod **319** (~93%)
- Material 2: manteca de cacao **templada** cod **485** (~7%)
- Producto: cod **581** templada (suma de los 2 insumos)
- Ej: 7.9 kg cod 319 + 0.6 kg cod 485 → 8.5 kg cod 581

El ratio inclusión/cobertura (30% frutos secos, 20% nibs) **NO cambia** al usar cobertura templada vs sin templar.

---

## 6. Flujo de OPs en cadena — SIEMPRE en OPs separadas

**Regla**: NUNCA combinar producción + empacado en una sola OP. Origen Silvestre lo hace SIEMPRE en OPs separadas.

### Caso A — 2 OPs (tabletas sin cobertura templada en cadena)

```
OP #1  consume cobertura sin templar (319) + frutos secos  →  produce tabletas sin empacar (480-484)
  ↓
OP #2  consume tabletas sin empacar + cajas (412)          →  produce tabletas empacadas (320, 493-496)
```

### Caso B — 3 OPs (con cobertura templada)

```
OP #1  consume cobertura 319 + manteca templada 485  →  produce cobertura templada 581
  ↓
OP #2  consume 581 + frutos secos                    →  produce tabletas sin empacar (480-484)
  ↓
OP #3  consume tabletas sin empacar + cajas 412      →  produce tabletas empacadas (320, 493-496)
```

### Mapeo sin empacar → empacada

| Sin empacar | Empacada | Sabor |
|---|---|---|
| 480 | 320 | Chocolate puro |
| 481 | 494 | Maní |
| 482 | 493 | Macadamia |
| 483 | 495 | Almendra |
| 484 | 496 | Nibs |

### Insumos de empacado
- **Caja**: cod **412** CAJA CHOCOLATE OSCURO 73Pgm X UND (1 por tableta, a veces +1-6 de reserva)
- **Etiquetas (533-538)**: NO aparecen en materiales históricos. Probable que vengan preimpresas en la caja. Si dudás, preguntá antes de agregar.

---

## 7. Caso real ejecutado — OPs 2191, 2194, 2195 (2026-04-22)

Las 3 OPs correctas en Effi (después de corregir bugs previos). Referencia canónica:

### OP 2191 — Cobertura templada (8.5 kg)
| | |
|---|---|
| Materiales | 7.9 kg cod **319** @ $43,432 + 0.6 kg cod **485** @ $50,000 |
| Producto | 8.5 kg cod **581** @ $43,432 |
| Otros costos | 2h mano de obra @ $7,000 (puesto con `tipo_costo_id=1` por error — debió ser **13** = M.O. HORA) |
| Costo materiales | $373,113 |
| Observación | "Cobertura templada para tabletas — método siembra" |

### OP 2194 — Tabletas sin empacar (136 unid)
| | |
|---|---|
| Materiales | 5.585 kg **581** @ $43,432 + 0.450 kg **196** @ $100,000 + 0.450 kg **114** @ $17,000 + 0.165 kg **508** @ $42,000 + 0.150 kg **178** @ $24,000 |
| Productos | 50 × **480** + 30 × **482** + 30 × **481** + 11 × **483** + 15 × **484** (todos @ $8,900) |
| Otros costos | 1h mano de obra @ $7,000 |
| Costo materiales | $306,175 · Venta total $1,210,400 · Beneficio 286% |

### OP 2195 — Tabletas empacadas (136 unid)
| | |
|---|---|
| Materiales | 50 × **480** + 30 × **482** + 30 × **481** + 11 × **483** + 15 × **484** (todos @ $5,200) + 136 cajas **412** @ $1,000 |
| Productos | 50 × **320** + 30 × **493** + 30 × **494** + 11 × **495** + 15 × **496** (todos @ $10,529) |
| Otros costos | 4.5h mano de obra @ $7,000 |
| Costo materiales | $843,200 · Venta total $1,431,944 · Beneficio 63% |

---

## 8. Cómo crear las OPs — flujo operativo

1. **Diseñar las recetas** siguiendo §2 (cantidades) + §1 (costos/precios).
2. **Generar JSONs** en `/tmp/ops_produccion/opN_*.json` con el formato del script.
3. **Ejecutar en orden** (cada OP toma 60-90s):
   ```bash
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op1_cobertura_templada.json
   # → reporta OP_CREADA:NNNN
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op2_tabletas_sin_empacar.json
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op3_tabletas_empacadas.json
   ```
4. **Estado final**: Generada. Deivy/Jenifer las pasan a Procesada y Validada manualmente desde Effi. **NO automatizar esos pasos**.

### Formato del JSON

```json
{
  "sucursal_id": 1,
  "bodega_id": 1,
  "fecha_inicio": "2026-04-22",
  "fecha_fin": "2026-04-22",
  "encargado": "74084937",
  "tercero": "",
  "observacion": "texto descriptivo",
  "materiales": [
    { "cod_articulo": "319", "cantidad": 7.9, "costo": 43432, "lote": "", "serie": "" }
  ],
  "articulos_producidos": [
    { "cod_articulo": "581", "cantidad": 8.5, "precio": 43432, "lote": "", "serie": "" }
  ],
  "otros_costos": [
    { "tipo_costo_id": 1, "cantidad": 2, "costo": 7000 }
  ]
}
```

**Encargados habituales**:
- Deivy Andres Gonzalez Gutierrez — CC `74084937`
- Laura — CC `1017206760`
- Jenifer Alexandra Cano Garcia — NIT `1128457413`

### Convención de observaciones

La observación es texto libre que aparece en la lista de OPs. **Debe ser auto-descriptiva** para que Deivy/Jenifer entiendan el contexto sin abrir el detalle.

**Formato sugerido**:
- **OP de cobertura templada**: `"Cobertura templada para tabletas — método siembra"`
- **OP de tabletas sin empacar**: `"Tabletas 73% sin empacar — N puro + N mac + N mani + N alm + N nibs"` (desglose por sabor)
- **OP de tabletas empacadas**: `"Empacado tabletas 73% — TOTAL unid (N puro + N mac + ...)"`
- **OP de envasado / mezcla**: `"Envasado [producto] — N unidades de [presentación]"`

Reglas:
- Sin emojis (Effi no los renderiza bien en algunas vistas).
- Máximo ~150 caracteres (Effi trunca en la lista).
- Idioma: español, en minúsculas excepto siglas/nombres propios.
- Si la OP es parte de una cadena (ej: 3 OPs ligadas), mencionarlo opcionalmente: `"... — paso 2/3 de cadena tabletas 22-abr"`.

### Lotes y series — regla clara

Effi asigna automáticamente lote y serie del stock disponible **al pasar la OP a Procesada**. Por eso:

| Escenario | Qué poner en JSON |
|---|---|
| Caso normal (95% de las veces) | `"lote": ""` y `"serie": ""` — Effi elige del FIFO del stock |
| Santi pide un lote específico (ej: usar lote 2150 que está por vencer) | `"lote": "2150"` y `"serie": ""` |
| Producto serializado (raro en OS) | `"serie": "ABC123"` |

**Importante**: NO inventar números de lote. Si dudás, dejar vacío. Santi o Jenifer lo editan después en Effi si hace falta.

### Otros costos — mano de obra y procesos

Las OPs llevan "otros costos" (mano de obra, transporte, procesos puntuales). El catálogo de tipos vive en `zeffi_costos_produccion`. **El costo unitario NO está en el catálogo** — viene de la práctica histórica del equipo (verificar contra OPs reales en `zeffi_otros_costos`).

#### Tipos de costo más usados (validados contra histórico)

| `tipo_costo_id` | Nombre | Unidad | Costo histórico | Veces usado |
|---|---|---|---|---|
| **13** | **M.O. HORA ORIGEN SILVESTRE** | hora | **$7,000** | **690** ← el más común |
| 14 | TOSTADO Y DESCASCARILLADO ARBOL DE CACAO | kg | $4,800 | 10 |
| 15 | TRANSPORTE BUCARAMANGA X KILO | kg | $2,200 | 11 |
| 8 | ENVASADO MIEL APICA (INCLUYE FILTRADO) | unidad | $500-$679 | 8 |
| 7 | OBTENCIÓN NIBS DE CACAO X KG INTAL | kg | $4,845 | 5 |
| 9 | LICOR DE CACAO INTAL (incluye tostión y descascarillado) | kg | $13,695 | 1 |
| 6 | REFINADO Y ENMOLDADO HECTOR BAKAU | kg | $15,000 | 1 |

⚠️ **NO confundir** `id=1` (REFINADO CACAO 24H CHOCOFRUTS) con `id=13` (M.O. HORA). Para producción de tabletas y procesos generales **siempre usar id=13** — es el que corresponde a mano de obra. Las OPs 2191/2194/2195 quedaron con id=1 por error (monto correcto pero categoría mal); en futuras OPs usar id=13.

#### Cómo calcular `cantidad` (horas) — para mano de obra

| Tipo de OP | Horas típicas |
|---|---|
| Cobertura templada (siembra, hasta 10 kg) | 2 h |
| Tabletas sin empacar (hasta 136 unid) | 1 h |
| Empacado tabletas (136 unid) | 4.5 h |

Si el volumen cambia mucho, escalá proporcional. Si dudás, preguntá.

#### Queries útiles

```sql
-- Catálogo completo de tipos de costo
SELECT id, nombre FROM zeffi_costos_produccion WHERE vigencia='Vigente' ORDER BY CAST(id AS UNSIGNED);

-- Costo histórico real por tipo (lo que el equipo escribe en OPs)
SELECT costo_de_produccion,
       SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT costo_ud ORDER BY costo_ud DESC SEPARATOR '|'), '|', 5) AS costos_distintos,
       COUNT(*) AS veces
FROM zeffi_otros_costos
WHERE vigencia='Orden vigente'
GROUP BY costo_de_produccion
ORDER BY veces DESC LIMIT 15;
```

---

## 9. Cómo funciona el script (para debug futuro)

**Ubicación**: `scripts/import_orden_produccion.js`. Automatiza Playwright sobre `https://effi.com.co/app/orden_produccion`.

### Lógica clave — apuntar a la ÚLTIMA fila

Effi mantiene IDs duplicados en el form (`#articulo_CRM` aparece varias veces tras agregar materiales). El script usa las clases de fila:

| Tipo | Clase de la fila | `name=` del input artículo |
|---|---|---|
| Material | `.filaMateriales` | `articuloM[]` |
| Producido | `.filaProducidos` | `articuloP[]` |
| Costo | `.filaCostos` | `costo_produccion[]` |

Helpers internos:
- `buscarArticulo(page, 'M' | 'P', codArticulo)` — abre el modal desde la lupa de la última fila.
- `llenarUltimaFila(page, 'M' | 'P', datos)` — llena cantidad/costo/lote/serie en la última fila.
- `llenarUltimoCosto(page, datos)` — análogo para costos.

Luego del submit, limpia **solo la última fila vacía** de cada sección (no todas las vacías — eso rompía antes).

### Bug histórico — ya arreglado (commit a75da13)

**Síntoma**: cada OP creada solo tenía el **último** material y el **último** producto del JSON.

**Causa**: el script usaba `document.querySelector('#articulo_CRM')` que devuelve siempre el **primer** match, pero al hacer click en "Agregar material" Effi **duplica el id**. El loop sobreescribía la fila anterior en cada iteración.

**Fix**: apuntar a la ÚLTIMA fila `.filaMateriales` / `.filaProducidos` / `.filaCostos` en cada iteración usando `querySelectorAll(...)[length-1]`.

**Lección**: al automatizar un form HTML que permite múltiples filas, **nunca** confiar en el `id` (puede duplicarse). Usar clases CSS o selectors posicionales.

---

## 10. Anti-patrones — qué NO hacer

### De receta / cantidades
❌ Asumir el ratio de un producto basado en otro similar sin verificar en BD
❌ Ignorar la versión "sin empacar" y mirar solo la empacada (la receta cruda no está ahí)
❌ Sumar manteca templada (485) a cobertura sin templar (319) — los procesos son distintos
❌ Olvidar restar el peso de las inclusiones cuando el límite es el peso total final
❌ Usar 1 sola OP como referencia única (puede tener error de captura)
❌ Crear una OP sin antes consultar las 5-10 últimas OPs vigentes del producto

### De costos / precios
❌ Inventar el precio "redondeando" o "siendo conservador"
❌ Usar `costo_promedio` o `ultimo_costo` del catálogo cuando debe ser `costo_manual`
❌ Asumir que `precio_minimo_de_venta` del catálogo tiene valor (está en 0)
❌ Hardcodear precios — Effi los actualiza internamente cada X meses, hay que consultar

### De flujo
❌ Combinar producción + empacado en una sola OP (OS siempre separa)
❌ Pasar manualmente OPs a Procesada/Validada — eso lo hacen Deivy/Jenifer

### De script
❌ Usar `document.querySelector('#id')` en forms con filas repetidas (ids se duplican)
❌ "Limpiar filas vacías" eliminando TODAS las vacías — solo la última de cada sección

---

## 11. Cómo registrar el aprendizaje

Cuando descubras un nuevo producto, ratio o anomalía:
1. Agregar cod nuevo a `sa_produccion/context/catalogo_productos.md`
2. Agregar nueva lógica a `sa_produccion/context/logica_negocio.md`
3. Si la receta está validada por Santi → `sa_produccion/context/recetas_validadas.md`
4. Si fue un caso difícil → `sa_produccion/aprendizaje/casos_resueltos.md`
5. **Si descubrís un bug del script o un cambio de UI en Effi** → actualizar §9 de esta skill y el script correspondiente.

---

## 12. Libro de Recetas — infraestructura 2026-04-22

**Ubicación**: BD VPS `inventario_produccion_effi` → 4 tablas: `prod_recetas`, `prod_recetas_materiales`, `prod_recetas_productos`, `prod_recetas_costos`.

**UI**: `inv.oscomunidad.com/recetas` (lista) y `/recetas/:cod` (detalle editable).

**Scripts**: `scripts/produccion/libro_recetas/`:
- `listar_universo.py [--familia X] [--resumen] [--pendientes]`
- `dossier_producto.py <cod> [--n_ops N]` — detalle completo de OPs históricas
- `construir_receta.py <cod>` — receta propuesta (usa motor de atribución)
- `simular_op.py <cod>` — aplica receta a la última OP real y diffea
- `persistir_receta.py <cod> [--estado ...] [--notas ...]` — INSERT/UPDATE
- `persistir_todas.py` — itera todos los pendientes
- `override_receta.py` — módulo para overrides manuales (YO lo uso cuando el motor falla)
- `sugerir_atribuido.py` — variante del algoritmo que ATRIBUYE materiales por OP multi-producto

### Atribución multi-producto (clave)

**Problema**: las OPs con varios productos producidos hacen que el script estándar mezcle materiales de otros productos en la receta.

**Solución** (en `sugerir_atribuido.py`):
1. **Afinidad semántica**: materiales con tokens específicos (`mani`, `macadamia`, `nibs`, etc.) que NO aparecen en el nombre del principal pero sí en otro producido → descartar.
2. **Match por cantidad**: si `cantidad_material ≈ cantidad_principal (±5%)` → 100% al principal; si coincide con otro producido → 0%.
3. **Share uniforme**: el resto se distribuye por `cant_principal / cant_total`.

Este motor acierta en >80% de casos. El 20% restante requiere override manual.

### Patrones de envase-peso (derivados al procesar el libro)

**Densidad por familia** (confirmada empíricamente):

| Producto | Densidad |
|---|---|
| Miel | ~1.28 g/ml |
| Propóleo | ~1.30 g/ml |
| Chocomiel | ~1.10 g/ml |
| Polen | ~0.65 g/ml (menos denso) |

**Mapeo envase estándar por presentación**:

| Peso/vol | Envase vidrio | Cod |
|---|---|---|
| 50cc | MB50H 50cc | **232** |
| 110cc | R mb110h 110cc | **86** |
| 130cc | R 4186-2465 130cc | **135** (crema maní) |
| 230cc | R 2670 230cc | **87** |
| 500cc | R 1263 500cc | **88** |
| 750cc | R 1264 750cc | **85** |
| Bolsa doy pack | PET flex transparente | **332** |
| Bolsa flex up 450g | 160x240 | **100** |
| Bolsa flex up pequeña | PET coext metalizado | **143** |

**Etiquetas por presentación**: cada peso tiene su etiqueta específica (ej: Etiqueta Miel 640 = cod 262). La etiqueta tapa 90 ("Origen Silvestre tapa") va en casi todos los envasados con tapa.

### Cómo identificar envase correcto cuando una OP es multi-producto

Query SQL clave:
```sql
SELECT p.cod_articulo, m.cod_material,
       SUM(CASE WHEN CAST(REPLACE(p.cantidad,',','.') AS DECIMAL(10,2))
                   = CAST(REPLACE(m.cantidad,',','.') AS DECIMAL(10,2)) THEN 1 ELSE 0 END) matches
FROM zeffi_articulos_producidos p
JOIN zeffi_materiales m ON m.id_orden=p.id_orden
WHERE p.cod_articulo = :cod AND m.cod_material IN (:envases_candidatos)
  AND p.vigencia='Orden vigente' AND m.vigencia='Orden vigente'
GROUP BY p.cod_articulo, m.cod_material
HAVING matches >= 3
ORDER BY matches DESC;
```

Si `matches >= 3` para un envase específico → ese es el envase del producto (1:1 entre cantidad de envase y cantidad producida).

### Estados de receta

- `borrador` — generada automáticamente, revisión pendiente. NO se debe usar para generar OPs.
- `validada` — revisada y confirmada. Lista para generar OPs desde la UI.

### Cobertura lograda (2026-04-22)

108 productos con receta, 72 validadas (67%). Los 36 en borrador son:
- Variantes de 1-2 OPs (infusionadas, DS, bombones rellenos)
- Productos con composición compleja que requieren razonamiento específico (chocobeetal, mix frutos secos, panal)
- Graneles intermedios que Santi debe confirmar (chocomiel 346, extracto vainilla 134)

El sistema permite consultar/editar desde la UI — ideal para que yo (o Santi) complete estos 36 con razonamiento caso por caso.
