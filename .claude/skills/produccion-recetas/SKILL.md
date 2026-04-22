---
name: produccion-recetas
description: Cómo construir recetas correctas para crear órdenes de producción (OPs) en Effi. Triggers - orden de producción, OP, receta, tableta, cobertura, templada, frutos secos, macadamia, almendra, mani, nibs, empacar, sin empacar, manteca, cacao, moldería, lote.
---

# Skill: Construcción de recetas de producción (Origen Silvestre)

Esta skill te enseña la **metodología rigurosa** para construir recetas antes de crear una OP en Effi. Aplica para tabletas, envasado, mezclas, coberturas, todo.

**Regla cero**: NUNCA inventar cantidades. Toda receta debe respaldarse en al menos 2 OPs históricas vigentes (o ser confirmada explícitamente por Santi).

---

## Metodología de búsqueda — los 5 pasos

### Paso 1 — Identificar la versión MÁS BÁSICA del producto

Muchos productos tienen 2-3 versiones en Effi:
- **"sin empacar"** — el producto base recién hecho, contiene la receta CRUDA (cobertura, fruto seco, etc.)
- **"empacado"** — base + caja/etiqueta/bolsa
- **"templado"** — versión templada de coberturas (proceso adicional)

**SIEMPRE arranca por la versión sin empacar**. Ahí está la receta real de los insumos primarios. Si tu pedido es "empacar tabletas con frutos secos", combinar las recetas: receta del sin empacar + caja/etiqueta del empacado.

```sql
-- Ejemplo: receta de tableta con nibs
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

### Paso 2 — Traer las últimas N OPs vigentes que produjeron esa versión

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

Una sola OP puede tener errores de captura. **Necesitas mínimo 2 OPs con el mismo ratio** para confianza alta. Si dan distinto:
- Investiga la discrepancia (¿hubo merma? ¿OP de prueba?)
- Pregunta a Santi antes de actuar

### Paso 5 — Escalar al pedido nuevo + verificar suma

Aplica los porcentajes al pedido. **La suma de materiales debe igualar el peso del producto producido** (descontando merma).

---

## Porcentajes confirmados — TABLETAS 50g

Confirmados por la metodología arriba en OPs múltiples:

| Tableta | % cobertura | % inclusión | OPs ref. |
|---|---|---|---|
| **Chocolate puro** | 100% (50g) | — | 2033, 2065 |
| **Macadamia** | 70% (35g) | 30% macadamia (15g) | 2064, 2174 |
| **Maní** | 70% (35g) | 30% maní (15g) | 2063 |
| **Almendra** | 70% (35g) | 30% almendra (15g) | 2062 |
| **Nibs** | 80% (40g) | 20% nibs (10g) | 2162 |

**Regla resumen**:
- Frutos secos (mani, macadamia, almendra) = 30% inclusión / 70% cobertura
- Nibs = 20% inclusión / 80% cobertura
- Chocolate puro = 100% cobertura

---

## Capacidad de moldería — restricción al pedido

**La moldería es el límite real de producción**. Cada lote de tabletas usa N moldes y cada molde tiene capacidad fija (ej: 4 tabletas por molde). El máximo de tabletas por OP = moldes disponibles × tabletas/molde.

Cuando Santi te dice "tengo X kg de cobertura templada para tabletas":
- ese X kg es el **peso TOTAL del producto final** (cobertura + inclusión, no solo cobertura)
- A ese X hay que **restarle el peso de los frutos secos** para saber cuánta cobertura va

Ejemplo:
- Pedido: 50 chocolate + 30 macadamia + 30 maní + 11 almendra + 15 nibs = 136 tabletas × 50g = 6.8 kg total
- Inclusiones: 30×15g (mac) + 30×15g (mani) + 11×15g (alm) + 15×10g (nibs) = 1.215 kg
- **Cobertura templada real necesaria: 6.8 - 1.215 = 5.585 kg**

---

## Cobertura templada vs sin templar

Cuidado con los nombres en Effi (4 productos similares):

| Cod | Nombre | Uso |
|---|---|---|
| 193 | MANTECA DE CACAO X KG | Sin templar — va en producir cobertura 73% (cod 319) |
| 485 | MANTECA DE CACAO **TEMPLADA** X KG | Templada — solo para método de siembra |
| 319 | COBERTURA CHOCOLATE 73% OS X KILO | Base sin templar — receta lote fijo 4kg |
| 581 | COBERTURA CHOCOLATE 73% OS X KILO **- TEMPLADA** | Templada (siembra) — para tabletas chocolatería |

**Cómo se produce cobertura templada (cod 581) — método siembra**:
- Material 1: cobertura sin templar cod 319 (~93%)
- Material 2: manteca de cacao **templada** cod 485 (~7%)
- Producto: cod 581 templada (suma de los 2 insumos)
- Ej: 7.9 kg sin templar + 0.6 kg manteca templada → 8.5 kg templada

El ratio inclusión/cobertura (30% frutos secos, 20% nibs) **NO cambia** al usar cobertura templada.

---

## ⭐ Costos y precios — fuente de verdad

**Regla absoluta** (validada con OPs reales 2191/2194/2195 el 2026-04-22):

| Campo del JSON | De dónde sacarlo |
|---|---|
| `materiales[].costo` | **`costo_manual`** del catálogo `zeffi_inventario` |
| `articulos_producidos[].precio` | Último **`precio_minimo_ud`** de OPs vigentes del producto en `zeffi_articulos_producidos` |
| `otros_costos[].costo` | Manual / acordado con Santi |

### Por qué así
- **Materiales**: Effi pre-llena el form con `costo_manual` del catálogo. Usar otro valor distorsiona costos contables. El histórico puede tener anomalías (p.ej. cod 485 manteca templada con $45 cuando el catálogo dice $50,000 — error humano replicado).
- **Producidos**: el campo `precio_minimo_de_venta` del catálogo está en 0 para casi todo. Effi pre-llena con el último precio usado en OPs anteriores del mismo producto. Replicar ese mismo valor mantiene consistencia con reportes.

### Queries listas para copiar/pegar

```sql
-- COSTO de un material (catálogo)
SELECT id, nombre, costo_manual
FROM zeffi_inventario
WHERE id IN ('319','485','196','114','508','178','412','480','481','482','483','484')
  AND vigencia='Vigente';

-- PRECIO de un producido (último histórico vigente, descartando OPs propias defectuosas)
SELECT cod_articulo,
       SUBSTRING_INDEX(GROUP_CONCAT(precio_minimo_ud ORDER BY fecha_creacion DESC), ',', 1) AS ultimo_precio,
       MAX(fecha_creacion) AS ultima_fecha
FROM zeffi_articulos_producidos
WHERE cod_articulo IN ('480','481','482','483','484','320','493','494','495','496','581')
  AND vigencia='Orden vigente'
  AND CAST(REPLACE(precio_minimo_ud, ',', '') AS DECIMAL(18,4)) > 100
GROUP BY cod_articulo;
```

### Tabla de referencia confirmada (2026-04-22)

| Cod | Producto | Costo (mat) | Precio (prod) |
|---|---|---|---|
| 319 | Cobertura 73% sin templar | $43,432 | — |
| 485 | Manteca cacao templada | $50,000 (catálogo) | — |
| 581 | Cobertura 73% templada | $43,432 | $43,432 (no hay histórico bueno → usar costo_manual) |
| 196 | Macadamia tostada | $100,000 | — |
| 114 | Maní sin cáscara | $17,000 | — |
| 508 | Almendras tostadas | $42,000 | — |
| 178 | Nibs cacao | $24,000 | — |
| 412 | Caja chocolate oscuro | $1,000 | — |
| 480-484 | Tabletas sin empacar (como mat) | $5,200 | $8,900 |
| 320, 493-496 | Tabletas empacadas | $5,200 (no aplica) | $10,529 |

### Anti-patrón
❌ Inventar el precio "redondeando" o "siendo conservador". Eso distorsiona Total venta / Beneficio neto.
❌ Usar `costo_promedio` o `ultimo_costo` del catálogo en lugar de `costo_manual` (Effi usa el manual).

---

## Insumos de empacado tabletas

Confirmado en OPs históricas (2104, 1972, 2109):
- **Caja**: cod 412 CAJA CHOCOLATE OSCURO 73Pgm X UND (1 por tableta)
- **Etiquetas (533-538)**: NO aparecen en materiales históricos. Probable que vengan preimpresas en la caja. Si dudas, pregunta antes de inventar.

---

## Flujo real para producir tabletas empacadas — siempre 2 OPs

**Regla**: NUNCA combines producción + empacado en una sola OP. El histórico de OS lo hace SIEMPRE en 2 OPs separadas (replicar ese patrón):

### OP A — tabletas sin empacar (cods 480/481/482/483/484)
- **Materiales**: cobertura (319 sin templar o 581 templada) + frutos secos
- **Producto**: tabletas "sin empacar"

### OP B — empacado (cods 320/493/494/495/496)
- **Materiales**: tabletas sin empacar (1:1) + cajas cod 412 (1:1, a veces +1-6 reserva)
- **Producto**: tabletas empacadas

Mapeo sin empacar → empacada:
- 480 → 320 (chocolate puro)
- 481 → 494 (maní)
- 482 → 493 (macadamia)
- 483 → 495 (almendra)
- 484 → 496 (nibs)

### Si además hay que producir cobertura templada → 3 OPs en cadena

Para tabletas con cobertura templada: necesitás producir primero la cobertura templada (cod 581).

```
OP #1 → produce cobertura templada (cod 581)
   ↓
OP #2 → consume cod 581 + frutos secos → produce tabletas sin empacar
   ↓
OP #3 → consume tabletas sin empacar + cajas → produce tabletas empacadas
```

**Caso real ejecutado el 2026-04-22 (OPs 2188, 2189, 2190)**:

OP #1 — Cobertura templada (8.5 kg):
- Material: 7.9 kg cod 319 + 0.6 kg cod 485 (manteca templada)
- Produce: 8.5 kg cod 581 (templada)
- M.O.: 2 h

OP #2 — Tabletas sin empacar (136 unid = 50 puro + 30 mac + 30 mani + 11 alm + 15 nibs):
- Materiales:
  - 5.585 kg cod 581 (cobertura templada)
  - 0.450 kg cod 196 (macadamia)
  - 0.450 kg cod 114 (maní)
  - 0.165 kg cod 508 (almendras)
  - 0.150 kg cod 178 (nibs)
- Productos: 50 cod 480 + 30 cod 482 + 30 cod 481 + 11 cod 483 + 15 cod 484
- M.O.: 1 h

OP #3 — Empacado (136 unid):
- Materiales:
  - 50 cod 480 + 30 cod 482 + 30 cod 481 + 11 cod 483 + 15 cod 484 (consume todo lo de OP #2)
  - 136 cod 412 (cajas)
- Productos: 50 cod 320 + 30 cod 493 + 30 cod 494 + 11 cod 495 + 15 cod 496
- M.O.: 4.5 h

### Restricción de moldería

**La moldería es el límite real**: cada lote usa N moldes con M tabletas cada uno (caso típico: 34 moldes × 4 tab = 136 tab máximo por OP).

Cuando Santi dice "tengo X kg para tabletas", X es el **peso TOTAL del producto final** (cobertura + frutos secos juntos). Para calcular cuánta cobertura va, restar el peso de las inclusiones:

```
cobertura_templada = X_total - sum(inclusiones)
```

Ej: 6.8 kg total - (0.450 mac + 0.450 mani + 0.165 alm + 0.150 nibs) = 5.585 kg cobertura

---

## Cómo crear las OPs — flujo operativo

1. **Diseñar las recetas** siguiendo la metodología arriba (consultar OPs históricas, calcular % inclusión, validar 2+ OPs)
2. **Generar JSONs** uno por OP en `/tmp/ops_produccion/opN_*.json` siguiendo el formato de `import_orden_produccion.js`
3. **Ejecutar en orden** (cada OP toma 60-90s):
   ```bash
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op1_cobertura_templada.json
   # → reporta OP_CREADA:NNNN
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op2_tabletas_sin_empacar.json
   node scripts/import_orden_produccion.js /tmp/ops_produccion/op3_tabletas_empacadas.json
   ```
4. **Las OPs quedan en estado Generada**. Deivy/Jenifer las pasan a Procesada y Validada manualmente desde Effi cuando corresponda. NO automatizar esos pasos.
5. **Lote en JSON**: dejar `"lote":""` y `"serie":""` vacíos — Effi auto-asigna del stock disponible al procesar/validar. Si Santi quiere un número específico, lo edita en Effi.

---

## Anti-patrones — qué NO hacer

❌ Asumir el ratio de un producto basado en otro similar sin verificar
❌ Ignorar el "sin empacar" y mirar solo la versión empacada (la receta cruda no está ahí)
❌ Sumar manteca templada a cobertura sin templar (los procesos son distintos)
❌ Olvidar restar el peso de las inclusiones cuando el límite es el peso total final
❌ Usar 1 sola OP como referencia única (puede tener error de captura)
❌ Crear una OP sin antes consultar las 5-10 últimas OPs vigentes del producto

---

## Cómo registrar el aprendizaje

Cuando descubras un nuevo producto, ratio o anomalía:
1. Actualizar `sa_produccion/context/catalogo_productos.md` con el cod nuevo
2. Actualizar `sa_produccion/context/logica_negocio.md` con la nueva lógica
3. Si la receta es validada por Santi, agregar a `sa_produccion/context/recetas_validadas.md`
4. Si fue un caso difícil, registrar en `sa_produccion/aprendizaje/casos_resueltos.md`
