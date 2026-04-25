# Guía de Programación de Producción — Origen Silvestre

**Última actualización**: 2026-04-24
**Objetivo**: que cualquier agente lea este documento y pueda ayudar a Santi a programar órdenes de producción (OPs) correctamente.

---

## 1. Regla fundamental — cómo funciona una receta

**La suma de materiales (contenido) = peso/unidades del producto producido.**

Es una regla de 3 simple. Si produces 25 frascos de Miel 640g:
- 25 × 0.640 kg = **16.0 kg** de miel como material
- 25 envases, 25 etiquetas, 25 etiquetas tapa

Si produces 8.3 kg de Crema de Maní:
- Los materiales (maní + vainilla + miel + sal) deben sumar **≈ 8.3 kg**
- No 12 kg, no 5 kg. El peso del producto = la suma de lo que le metes.

**Materiales de contenido** (suman peso): la materia prima — miel, maní, cobertura, polen, etc.
**Materiales de empaque** (no suman peso): envases, etiquetas, cajas, bolsas — van 1:1 por unidad producida.

---

## 2. Flujo completo — del pedido a la OP creada

Cuando Santi dice "programar X unidades de [producto]":

### Paso 1 — Buscar la receta

```
Buscar en prod_recetas (BD inventario_produccion_effi) el cod_articulo.
Si existe → usarla como base.
Si no existe → consultar últimas 3 OPs vigentes del producto para deducirla.
```

### Paso 2 — Consultar últimas 3 OPs vigentes

Siempre verificar contra el histórico real. Esto confirma que la receta no cambió.

```sql
-- En BD os_integracion (VPS)
SELECT a.id_orden, e.fecha_de_creacion, a.cantidad as producido
FROM zeffi_articulos_producidos a
JOIN zeffi_produccion_encabezados e ON e.id_orden = a.id_orden
WHERE a.cod_articulo = '<COD>' AND e.vigencia = 'Vigente'
ORDER BY CAST(a.id_orden AS UNSIGNED) DESC LIMIT 3;

-- Para cada OP, ver materiales:
SELECT cod_material, descripcion_material, cantidad, costo_ud
FROM zeffi_materiales WHERE id_orden = '<OP_ID>' ORDER BY _pk;
```

### Paso 3 — Generar PREVIEW y mostrarlo a Santi

Mostrar una tabla clara:

```
┌─────────────────────────────────────────────────────────┐
│  PREVIEW — 25 unidades Miel Os Vidrio 640 grs (cod 15) │
├────────────────────────┬────────┬──────────┬────────────┤
│ Material               │ Cant.  │ Costo ud │ Subtotal   │
├────────────────────────┼────────┼──────────┼────────────┤
│ MIEL FILT. EL CARMEN   │ 16.00  │ $22,000  │ $352,000   │
│ Envase 500cc ESTERIL.  │ 25     │ $2,055   │ $51,375    │
│ Etiqueta Miel 640      │ 25     │ $300     │ $7,500     │
│ Etiqueta tapa OS       │ 25     │ $390     │ $9,750     │
├────────────────────────┼────────┼──────────┼────────────┤
│ TOTAL MATERIALES       │        │          │ $420,625   │
├────────────────────────┼────────┼──────────┼────────────┤
│ M.O. Hora OS (2.5h)   │ 2.5    │ $7,000   │ $17,500    │
├────────────────────────┼────────┼──────────┼────────────┤
│ TOTAL COSTO            │        │          │ $438,125   │
│ VENTA (25 × $21,324)   │        │          │ $533,100   │
│ BENEFICIO NETO         │        │          │ $94,975    │
│ MARGEN                 │        │          │ 17.8%      │
└────────────────────────┴────────┴──────────┴────────────┘

Receta basada en: OP 2204 (2026-04-24), OP 2202 (2026-04-23)
Encargado: Deivy Andres Gonzalez Gutierrez (CC 74084937)
Observación: "Envasado Miel Os Vidrio 640g — 25 unidades"
```

### Paso 4 — Esperar confirmación de Santi

- Si dice **OK** → crear la OP (paso 5)
- Si dice **cambiar algo** (ej: "usa miel cruda no filtrada") → actualizar el preview Y actualizar la receta en BD
- Si dice **la receta está mal** → corregir en `prod_recetas_materiales` y regenerar

### Paso 5 — Crear la OP vía Playwright

Generar el JSON y ejecutar el script:

```bash
node scripts/import_orden_produccion.js /tmp/ops_produccion/op_miel_640g.json
# → Reporta OP_CREADA:NNNN
```

### Paso 6 — Reportar

Decirle a Santi: "OP NNNN creada. [link a Effi si aplica]"

---

## 3. Materiales vigentes — tabla actualizada (2026-04-24)

### Mieles (material principal)

| Cod | Material | $/kg | Uso |
|---|---|---|---|
| **586** | MIEL FILTRADA Y PASTEURIZADA EL CARMEN | **$22,000** | **Envasado actual** — la que va en frascos vidrio |
| 373 | MIEL FILTRADA Y PASTEURIZADA x KILO | $16,500 | Miel panal, recetas viejas. Todavía vigente para panal |
| 342 | MIEL OS CARMEN X KILO | $15,000 | Materia prima cruda. Se filtra/pasteuriza → produce art 586 |
| 53 | MIEL SAN MIGUEL CRUDA x KILO | $16,000 | Otra fuente de miel cruda. Usada en crema de maní |

### Envases — SIEMPRE ESTERILIZADOS (desde 2026-04-24)

| Tamaño | Cod NUEVO (esterilizado) | $ | Cod VIEJO (no usar) | Para qué producto |
|---|---|---|---|---|
| 750cc | **552** | $2,705 | ~~85~~ | Miel 1000g |
| 500cc | **555** | $2,055 | ~~88~~ | Miel 640g |
| 230cc | **554** | $1,560 | ~~87~~ | Miel 275g, Propóleo 265g, Polen 150g, Crema maní 230g |
| 110cc | **553** | $1,500 | ~~86~~ | Miel 150g, Propóleo 150g, Polen 80g, Crema maní 130g |

### Etiquetas (1:1 por unidad producida)

| Cod | Etiqueta | $ | Producto |
|---|---|---|---|
| 263 | Etiqueta Miel 1000 | $300 | Miel Os Vidrio 1000g |
| 262 | Etiqueta Miel 640 | $300 | Miel Os Vidrio 640g |
| 291 | Etiqueta Miel 275 | $300 | Miel Os Vidrio 275g |
| 290 | Etiqueta Miel 150 | $300 | Miel Os Vidrio 150g |
| 298 | Etiqueta Propóleo 150 | $300 | Propóleo OS 150g |
| 299 | Etiqueta Propóleo 265 | $300 | Propóleo OS 265g |
| 300 | Etiqueta Propóleo 600 | $300 | Propóleo OS 600g |
| 295 | Etiqueta Polen 80 | $300 | Polen OS 80g |
| 296 | Etiqueta Polen 150 | $300 | Polen OS 150g |
| 301 | Etiqueta Crema Maní 130 | $300 | Crema Maní OS 130g |
| 302 | Etiqueta Crema Maní 230 | $300 | Crema Maní OS 230g |
| 264 | Etiqueta Crema Maní 500 | $300 | Crema Maní OS 500g |
| 90 | Etiqueta Origen Silvestre tapa | $390 | **TODOS** los envasados con tapa |

### Otros materiales frecuentes

| Cod | Material | $/kg o $/ud |
|---|---|---|
| 114 | MANI SIN CASCARA TOSTADO X KILO | $17,000 |
| 134 | Extracto de Vainilla en Miel OS x Kilo | $73,725 |
| 500 | SAL MARINA GRANO FINO SIN REFINAR X KG | $8,900 |
| 147 | PROPOLEO APICA X KILO | $17,850 |
| 146 | POLEN APICA X KILO | $48,500 |
| 261 | ALMENDRA DE CACAO TOSTADA X KILO | $25,000 |
| 178 | NIBS DE CACAO X KG LT | $24,000 |
| 319 | COBERTURA CHOCOLATE 73% OS X KILO | $43,432 |
| 485 | MANTECA DE CACAO TEMPLADA X KG | $50,000 |
| 581 | COBERTURA CHOCOLATE 73% TEMPLADA X KILO | $43,432 |
| 412 | CAJA CHOCOLATE OSCURO 73Pgm X UND | $1,000 |

---

## 4. Costos y precios — de dónde sacarlos

### Costo de materiales

```sql
-- SIEMPRE usar costo_manual del catálogo (BD os_integracion)
SELECT id AS cod, nombre, costo_manual
FROM zeffi_inventario
WHERE id = '<COD_MATERIAL>' AND vigencia='Vigente';
```

**NUNCA** usar `costo_promedio` ni `ultimo_costo`. Effi pre-llena el campo con `costo_manual`.

### Precio de venta del producido

```sql
-- Último precio_minimo_ud de OPs vigentes (BD os_integracion)
SELECT precio_minimo_ud
FROM zeffi_articulos_producidos
WHERE cod_articulo = '<COD_PRODUCTO>'
  AND vigencia = 'Orden vigente'
ORDER BY fecha_creacion DESC LIMIT 1;
```

El campo `precio_minimo_de_venta` del catálogo está en **0** para casi todo. No usarlo.

### Mano de obra

| tipo_costo_id | Nombre | $/hora | Uso |
|---|---|---|---|
| **13** | M.O. HORA ORIGEN SILVESTRE | **$7,000** | El más común — producción general |
| 14 | TOSTADO Y DESCASCARILLADO ARBOL DE CACAO | $4,800/kg | Proceso externo |
| 15 | TRANSPORTE BUCARAMANGA X KILO | $1,200/kg | Envíos |

**Siempre usar tipo_costo_id = 13** para mano de obra general. NUNCA id=1 (ese es "REFINADO CACAO").

---

## 5. Recetas de referencia (OPs de Santi del 2026-04-24)

Estas son las OPs más recientes y correctas. Úsalas como modelo.

### Mieles envasadas (OP 2204 — referencia principal)

Produce: 6×1000g + 12×640g + 12×275g + 12×150g = 42 frascos
- Miel: **FILTRADA EL CARMEN (586)** — 6×1.0 + 12×0.64 + 12×0.275 + 12×0.15 = **18.78 kg**
- Envases: 6×**552**(750cc) + 12×**555**(500cc) + 12×**554**(230cc) + 12×**553**(110cc)
- Etiquetas: 6×263 + 12×262 + 12×291 + 12×290 + 42×**90**(tapa)

### Propóleo envasado (OP 2198)

Produce: 24×150g + 24×265g + 6×600g = 54 frascos
- Propóleo: **APICA (147)** — 24×0.15 + 24×0.265 + 6×0.60 = **13.56 kg**
- Envases: 24×**553** + 24×**554** + 6×**555**
- Etiquetas: 24×298 + 24×299 + 6×300 + 54×90

### Polen envasado (OP 2205)

Produce: 12×80g + 12×150g = 24 frascos
- Polen: **APICA (146)** — 12×0.08 + 12×0.15 = **2.76 kg**
- Envases: 12×**553** + 12×**554**
- Etiquetas: 12×295 + 12×296 + 24×90

### Nibs cacao envasados (OP 2199)

Produce: 24 unidades de 100g
- Nibs: **(178)** — 24×0.1 = **2.40 kg**
- Bolsa: 24×332 (doy pack 10x18)
- Etiquetas: 24×331 (delantera) + 24×530 (trasera)

### Almendra cacao envasada (OP 2210)

Produce: 12×100g + 8×200g = 20 unidades
- Almendra: **(261)** — 12×0.1 + 8×0.2 = **2.80 kg**
- Bolsa 100g: 12×332 (doy pack), Bolsa 200g: 8×143 (flex up metalizada)
- Etiquetas: 12×330+12×539 (100g del+tras) + 8×310+8×549 (200g del+tras)

### Chocolates (OP 2208 — Bombones)

Produce: 12 unidades de 250g
- Chocolate moldeado: **(93)** — 12×0.25 = **3.00 kg** a $35,420/kg
- Bolsa: 12×143 (flex up metalizada)
- Etiquetas: 12×283 (delantera) + 12×528 (trasera)

### Crema de Maní x kilo (referencia: OP 2028)

Produce: 8.3 kg
- Maní tostado (114): **8.3 kg** — ratio 1:1 con producido
- Vainilla en miel (134): 0.32 kg
- Miel filtrada (373): 0.64 kg
- Sal marina (500): 0.06 kg

**NOTA**: en OPs recientes de miel envasada, Santi usa la 586 (filtrada EL CARMEN). Para crema de maní la última OP correcta (2028) usa 373. Verificar siempre con las últimas 3 OPs.

---

## 6. Flujo de OPs en cadena

NUNCA combinar producción + empacado en una sola OP. OS separa siempre.

### Ejemplo: tabletas de chocolate (3 OPs)

```
OP #1 → Cobertura templada
  Materiales: cob sin templar (319) + manteca templada (485)
  Produce: cobertura templada (581)

OP #2 → Tabletas sin empacar
  Materiales: cob templada (581) + frutos secos
  Produce: tabletas sin empacar (480-484)

OP #3 → Empacado
  Materiales: tabletas sin empacar + cajas (412)
  Produce: tabletas empacadas (320, 493-496)
```

### Mapeo sin empacar → empacada

| Sin empacar | Empacada | Sabor |
|---|---|---|
| 480 | 320 | Chocolate puro (100% cobertura, 50g/ud) |
| 481 | 494 | Maní (70% cob + 30% maní, 35g+15g) |
| 482 | 493 | Macadamia (70% cob + 30% mac, 35g+15g) |
| 483 | 495 | Almendra (70% cob + 30% alm, 35g+15g) |
| 484 | 496 | Nibs (80% cob + 20% nibs, 40g+10g) |

---

## 7. Formato del JSON para el script

```json
{
  "sucursal_id": 1,
  "bodega_id": 1,
  "fecha_inicio": "2026-04-24",
  "fecha_fin": "2026-04-24",
  "encargado": "74084937",
  "tercero": "",
  "observacion": "Envasado Miel Os Vidrio 640g — 25 unidades",
  "materiales": [
    { "cod_articulo": "586", "cantidad": 16.0, "costo": 22000, "lote": "", "serie": "" },
    { "cod_articulo": "555", "cantidad": 25, "costo": 2055, "lote": "", "serie": "" },
    { "cod_articulo": "262", "cantidad": 25, "costo": 300, "lote": "", "serie": "" },
    { "cod_articulo": "90",  "cantidad": 25, "costo": 390, "lote": "", "serie": "" }
  ],
  "articulos_producidos": [
    { "cod_articulo": "15", "cantidad": 25, "precio": 21324, "lote": "", "serie": "" }
  ],
  "otros_costos": [
    { "tipo_costo_id": 13, "cantidad": 2.5, "costo": 7000 }
  ]
}
```

### Encargados habituales

| Nombre | Cédula (campo `encargado` del JSON) |
|---|---|
| Deivy Andres Gonzalez Gutierrez | `74084937` |
| Laura Echavarria | `1017206760` |
| Jenifer Alexandra Cano Garcia | `1128457413` |

### Observación

Formato: `"[Tipo] [Producto] — [cantidad] unidades [detalle opcional]"`
- Máximo 150 caracteres
- Sin emojis
- Español, minúsculas excepto siglas

### Lotes y series

Dejar vacío (`""`) salvo que Santi pida uno específico. Effi asigna automáticamente al procesar.

---

## 8. Script de Playwright — ejecución

```bash
# Ubicación del script
node scripts/import_orden_produccion.js /tmp/ops_produccion/mi_op.json

# El script:
# 1. Abre https://effi.com.co/app/orden_produccion
# 2. Llena el formulario con los datos del JSON
# 3. Click en Guardar
# 4. Reporta en stdout: OP_CREADA:NNNN
# 5. Toma ~60-90 segundos
```

**Pre-requisito**: Playwright debe tener sesión activa en Effi. Si falla con error de login, hay que iniciar sesión manualmente primero.

**Ejecución**: siempre desde la raíz del repo:
```bash
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS
node scripts/import_orden_produccion.js <ruta_json>
```

---

## 9. Actualización de recetas

Si Santi corrige algo en el preview:

### Actualizar en BD

Las recetas viven en `inventario_produccion_effi` (VPS):
- `prod_recetas` — cabecera (cod_articulo, nombre, familia, patrón, etc.)
- `prod_recetas_materiales` — ingredientes (receta_id, cod_material, cantidad_por_lote, costo_unit_snapshot)
- `prod_recetas_productos` — productos generados (receta_id, cod_articulo, cantidad_por_lote, precio_min_venta_snapshot)
- `prod_recetas_costos` — costos de producción (receta_id, nombre, cantidad_por_lote, costo_unit)

### Ejemplo: cambiar la miel de una receta

```sql
-- 1. Encontrar el receta_id
SELECT id FROM prod_recetas WHERE cod_articulo = '15';  -- Miel 640g → id = X

-- 2. Actualizar el material
UPDATE prod_recetas_materiales
SET cod_material = '586', nombre = 'MIEL FILTRADA Y PASTEURIZADA EL CARMEN',
    costo_unit_snapshot = 22000
WHERE receta_id = X AND cod_material = '53';  -- viejo = miel cruda

-- 3. Marcar la receta como actualizada
UPDATE prod_recetas SET updated_at = NOW(), notas_analisis = CONCAT(notas_analisis, '\n2026-04-24: cambio miel 53→586 por indicación Santi')
WHERE id = X;
```

### Principio clave

Si Santi dice "eso está mal, debería ser X":
1. Corregir el preview inmediatamente
2. Actualizar la receta en BD para que la próxima vez salga bien
3. Si no existe receta → crearla con estado `borrador`, luego Santi la valida

---

## 10. Anti-patrones — lo que NUNCA hacer

| NUNCA | Por qué |
|---|---|
| Inventar cantidades o precios | Rompe reportes contables. Todo sale de BD o de Santi |
| Usar `costo_promedio` o `ultimo_costo` | Effi usa `costo_manual`. Diferente valor |
| Asumir que `precio_minimo_de_venta` del catálogo tiene valor | Está en 0 para casi todo |
| Combinar producción + empacado en 1 OP | OS siempre separa en OPs distintas |
| Usar envases NO esterilizados (85, 86, 87, 88) | Desde 2026-04-24 solo esterilizados (552-555) |
| Usar miel CRUDA (53) para envasado | Usar FILTRADA EL CARMEN (586) para frascos |
| Poner tipo_costo_id=1 para mano de obra | Es id=13 (M.O. HORA OS). id=1 es REFINADO CACAO |
| Crear OP sin mostrar preview a Santi | Siempre preview primero, confirmar, luego crear |
| Clonar una OP sin verificar que es correcta | Las OPs pueden tener errores. Verificar vs últimas 3 |
| Dejar lote/serie inventados | Dejar vacío. Effi asigna al procesar |

---

## 11. Consultas útiles para el agente

### Buscar un producto por nombre

```sql
SELECT id, nombre, costo_manual FROM zeffi_inventario
WHERE vigencia='Vigente' AND nombre LIKE '%miel%640%'
ORDER BY CAST(id AS UNSIGNED);
```

### Ver receta existente

```sql
SELECT r.*, rm.cod_material, rm.nombre as mat_nombre, rm.cantidad_por_lote, rm.costo_unit_snapshot
FROM prod_recetas r
JOIN prod_recetas_materiales rm ON rm.receta_id = r.id
WHERE r.cod_articulo = '15'
ORDER BY rm.cantidad_por_lote DESC;
```

### Últimas 3 OPs vigentes de un producto

```sql
SELECT a.id_orden, e.fecha_de_creacion, a.cantidad,
       m.cod_material, m.descripcion_material, m.cantidad as mat_qty, m.costo_ud
FROM zeffi_articulos_producidos a
JOIN zeffi_produccion_encabezados e ON e.id_orden = a.id_orden
JOIN zeffi_materiales m ON m.id_orden = a.id_orden
WHERE a.cod_articulo = '<COD>' AND e.vigencia = 'Vigente'
  AND CAST(a.id_orden AS UNSIGNED) IN (
    SELECT CAST(id_orden AS UNSIGNED) FROM zeffi_articulos_producidos
    WHERE cod_articulo = '<COD>' AND vigencia = 'Orden vigente'
    ORDER BY CAST(id_orden AS UNSIGNED) DESC LIMIT 3
  )
ORDER BY CAST(a.id_orden AS UNSIGNED) DESC, m._pk;
```

### Costo actual de un material

```sql
SELECT id, nombre, costo_manual FROM zeffi_inventario
WHERE id = '<COD>' AND vigencia='Vigente';
```

### Precio actual de un producto producido

```sql
SELECT cod_articulo, precio_minimo_ud, fecha_creacion
FROM zeffi_articulos_producidos
WHERE cod_articulo = '<COD>' AND vigencia = 'Orden vigente'
ORDER BY fecha_creacion DESC LIMIT 1;
```

---

## 12. Conexiones a BD

El agente debe usar los helpers centralizados del proyecto:

**Python**:
```python
from lib import integracion, inventario
# integracion() → BD os_integracion (tablas zeffi_*, fuente de verdad)
# inventario()  → BD inventario_produccion_effi (tablas prod_recetas_*)
```

**Las tablas zeffi_* están en os_integracion. Las tablas prod_* están en inventario_produccion_effi. Son BDs distintas.**

---

## Apéndice — Cómo se creó este documento

Basado en:
- OPs correctas de Santi: 2198, 2199, 2202, 2203, 2204, 2205, 2207, 2208, 2209, 2210 (2026-04-23/24)
- Error corregido: OP 2111 de crema de maní (mala) vs OP 2028 (correcta)
- Cambios de materiales: miel 586 EL CARMEN, envases esterilizados 552-555
- Skill detallado: `.claude/skills/produccion-recetas/SKILL.md`
