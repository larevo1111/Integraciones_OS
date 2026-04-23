# Plan: Libro de Recetas de Producción

**Creado**: 2026-04-22
**Owner**: Santi (dirección) + Claude Code (ejecución + validación)
**Estado**: Plan acordado — pendiente de arrancar Fase 1

---

## Objetivo

Construir un libro maestro con **una receta por cada artículo producido** desde 2025-01-01 hasta hoy, para dejar de deducir recetas a mano cada vez que se genera una OP. Fuente de verdad = **OPs vigentes de Effi**. Cero invención.

## Universo (verificado 2026-04-22)

- **108 productos distintos** producidos desde 2025-01-01
- **743 OPs vigentes** en ese rango
- **427 puras** (57%) / **316 multi-producto** (43%)

Distribución por nº de OPs históricas por producto:

| Rango | Productos | Dificultad | Tratamiento |
|---|---|---|---|
| ≥10 OPs | 45 | Fácil | Script estadístico suficiente, validación liviana |
| 5-9 OPs | 17 | Media | Script + verificación manual |
| 3-4 OPs | 19 | Media-alta | Script + razonamiento sobre nombres |
| 2 OPs | 6 | Alta | Razonamiento manual + simulación |
| 1 OP | 21 | Alta | Razonamiento manual + heurística del nombre |

**Santi insiste**: la clasificación arriba es orientativa. Lo que importa es que YO revise cada una con método, no que el script resuelva solo.

---

## Qué es una receta (definición precisa de Santi)

Una receta describe **lo que figura literalmente en una OP para producir ese artículo**. Sin encadenar. Sin inventar.

- Una tableta **empacada** (cod 320) tiene receta con: tableta sin empacar (cod 480) + caja (412) + bolsa + insumos.
- Una tableta **sin empacar** (cod 480) tiene receta con: cobertura templada (581) + frutos secos.
- Una **cobertura templada** (cod 581) tiene receta con: cobertura 73% sin templar (319) + manteca cacao templada (485).

Cada producto que figure como producido en una OP vigente desde 2025 en adelante tiene **su propia receta independiente**. La "cadena" no se persiste — si alguien quiere encadenar, lo hace en la UI consumiendo 3 recetas.

---

## Principios (del CLAUDE.md del proyecto)

1. **Cero invención**: toda cantidad/costo/precio sale de BD o de Santi.
2. **5S**: una operación = una función. No duplicar lógica entre scripts.
3. **Simple ante todo**: menos abstracción, menos tablas, menos columnas. Lo mínimo que funcione.
4. **Reusar**: el script `sugerir_receta.py` ya resuelve el 70% — no lo reinvento, lo envuelvo.
5. **Alcance mínimo**: solo tabla + scripts + UI simple. Nada más.

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│  BD VPS: inventario_produccion_effi (existente)              │
│  ├─ prod_recetas              (cabecera)                     │
│  ├─ prod_recetas_materiales                                  │
│  ├─ prod_recetas_productos     (incluye el principal)        │
│  └─ prod_recetas_costos                                      │
└──────────────────────────────────────────────────────────────┘
                   ▲
                   │ persiste
                   │
┌──────────────────────────────────────────────────────────────┐
│  scripts/produccion/libro_recetas/                           │
│  ├─ dossier_producto.py       Dossier por producto           │
│  │                            (OPs, materiales, nombres,     │
│  │                            candidatos a receta)           │
│  ├─ construir_receta.py       Usa sugerir_receta +           │
│  │                            enriquecimiento (costos        │
│  │                            actualizados, precio venta)    │
│  ├─ simular_op.py             Aplica receta a cantidad X,    │
│  │                            compara contra última OP real  │
│  ├─ persistir_receta.py       INSERT/UPDATE en VPS           │
│  └─ listar_universo.py        108 productos + estado         │
└──────────────────────────────────────────────────────────────┘
                   ▲
                   │ consume
                   │
┌──────────────────────────────────────────────────────────────┐
│  UI (Fase final): inv.oscomunidad.com /recetas               │
│  • Lista (OsDataTable) de 108 recetas                        │
│  • Detalle con materiales/costos/co-productos editables      │
│  • Botón "generar OP desde receta" → JSON para import        │
└──────────────────────────────────────────────────────────────┘
```

---

## Esquema BD (simple, 4 tablas)

```sql
CREATE TABLE prod_recetas (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  cod_articulo          VARCHAR(20) NOT NULL UNIQUE,  -- 1 receta por producto
  nombre                VARCHAR(255) NOT NULL,
  patron                ENUM('lote_fijo','escalable') NOT NULL,
  cantidad_lote_std     DECIMAL(14,4) NULL,           -- NULL si es escalable
  confianza             ENUM('alta','media','baja') NOT NULL,
  estado                ENUM('borrador','validada') NOT NULL DEFAULT 'borrador',
  n_ops_analizadas      INT NOT NULL DEFAULT 0,
  ops_referencia        TEXT NULL,                     -- CSV de id_orden
  notas_analisis        TEXT NULL,                     -- razonamiento mío (auditoría)
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  validated_at          DATETIME NULL,
  INDEX (estado), INDEX (confianza)
);

CREATE TABLE prod_recetas_materiales (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  receta_id             INT NOT NULL,
  cod_material          VARCHAR(20) NOT NULL,
  nombre                VARCHAR(255) NOT NULL,
  cantidad_por_lote     DECIMAL(14,4) NOT NULL,        -- si lote_fijo
  ratio_por_unidad      DECIMAL(14,6) NOT NULL,        -- si escalable
  costo_unit_snapshot   DECIMAL(14,2) NOT NULL,        -- costo_manual al guardar
  n_ops_aparece         INT NOT NULL,
  FOREIGN KEY (receta_id) REFERENCES prod_recetas(id) ON DELETE CASCADE
);

CREATE TABLE prod_recetas_productos (
  -- El producto principal + co-productos que consistentemente salen en esas OPs
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  receta_id             INT NOT NULL,
  cod_articulo          VARCHAR(20) NOT NULL,
  nombre                VARCHAR(255) NOT NULL,
  es_principal          TINYINT NOT NULL DEFAULT 0,
  cantidad_por_lote     DECIMAL(14,4) NOT NULL,
  ratio_por_unidad      DECIMAL(14,6) NOT NULL,
  precio_min_venta_snapshot DECIMAL(14,2) NOT NULL,
  n_ops_aparece         INT NOT NULL,
  FOREIGN KEY (receta_id) REFERENCES prod_recetas(id) ON DELETE CASCADE
);

CREATE TABLE prod_recetas_costos (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  receta_id             INT NOT NULL,
  tipo_costo_id         INT NOT NULL,       -- referencia a zeffi_costos_produccion
  nombre                VARCHAR(255) NOT NULL,
  cantidad_por_lote     DECIMAL(14,4) NOT NULL,
  costo_unit            DECIMAL(14,2) NOT NULL,
  FOREIGN KEY (receta_id) REFERENCES prod_recetas(id) ON DELETE CASCADE
);
```

**Notas del esquema**:
- `estado` solo tiene 2 valores (`borrador`/`validada`) — simple. Una receta en `borrador` no se puede usar para generar OPs; `validada` sí.
- Sin versioning al inicio (decisión Santi). Si cambia un costo, se regenera el snapshot. Si cambian cantidades, se actualiza in-place y queda el razonamiento en `notas_analisis`.
- `cantidad_por_lote` + `ratio_por_unidad` conviven: el campo `patron` dice cuál es el que se usa. El otro se guarda por trazabilidad.

---

## Orden metódico de trabajo

### Antes de nada — preparación (Fase 1)

1. Crear las 4 tablas en `inventario_produccion_effi` del VPS.
2. Construir `listar_universo.py`: imprime los 108 productos con:
   - cod, nombre, n_ops, última OP (fecha), familia sugerida (derivada del nombre).
3. Construir `dossier_producto.py`: para un cod_articulo, imprime:
   - Las últimas N OPs vigentes con su cantidad producida
   - Por cada OP: todos los materiales (cod, nombre, cantidad, costo)
   - Por cada OP: todos los co-productos (cod, nombre, cantidad, precio)
   - Por cada OP: costos de producción
   - Nombres de materiales parseados: detectar `"Etiqueta miel 630gr"` → tag `etiqueta_miel_630g`
   - Nombres de co-productos parseados: detectar peso/volumen del nombre (`640gr`, `500cc`, etc.)
4. Construir `simular_op.py`: dada una receta (en BD o stub), produce el JSON equivalente al que espera `import_orden_produccion.js` para una cantidad X, y lo diffea contra la última OP real.

### Proceso por producto (Fases 2-N, una por familia)

Agrupar los 108 productos por **familia** (clustering por nombre):

| Familia | Ejemplos | Patrón típico |
|---|---|---|
| Mieles | Miel Os 150g/640g/1000g, Miel Apica 180g, Chocomiel 250cc | OPs multi-producto — mismo granel, distintas presentaciones |
| Chocolates de mesa | Chocolate mesa OS 250g, 500g | Lote fijo por molde |
| Cremas de maní | Crema maní 130g/230g/500g/1kg | OPs multi-producto — mismo granel |
| Tabletas 73% | 50g puro/nibs/mac/maní/almendra — empacada y sin empacar | Lote fijo por molde |
| Coberturas | 319 sin templar, 581 templada, manteca 485 | Lote fijo |
| Nibs y cacao | Nibs 100g, 500g, 1kg, licor cacao, etc. | Variado |
| Propóleo | 150g, 265g | Envasado simple |
| Polen | 80g, 150g, 320g | Envasado simple |
| Infusiones | Cacao+polen+menta 200g | Mezclas |
| Otros | Lo que no entre arriba | Case by case |

**Por cada familia** seguir el bucle:

1. **Listar productos** de la familia con `listar_universo.py --familia mieles`.
2. **Elegir el primero** (el que más OPs tiene — señal más fuerte).
3. Correr `dossier_producto.py <cod>` y **leerlo completo**.
4. Aplicar razonamiento:
   - ¿Es lote fijo o escalable? (el script sugiere; yo confirmo)
   - ¿El nombre del producto tiene gramos/ml? → ratio obvio contra material principal.
   - ¿Hay etiqueta específica? (nombre de material contiene `"630g"`, `"150g"`, etc.) → asociarla.
   - ¿Hay envase específico? (500cc para miel 640g, 750cc para miel 1000g). Confirmar con las OPs.
   - ¿Las OPs multi-producto repiten el mismo ratio de materiales? Ignorar co-productos, mirar solo los insumos específicos de este producto.
   - **OPs recientes pesan más** que antiguas (si hay discrepancia, preferir las recientes).
5. **Armar receta propuesta** (materiales + costos + co-productos + precio venta).
6. **Simular** con `simular_op.py <cod> <cantidad>` y comparar contra la última OP real del producto.
7. Si diferencia <5% por material → aceptar. Si >5% → investigar (¿merma? ¿OP mala?).
8. **Persistir** en BD con estado=`borrador` y `notas_analisis` con el razonamiento.
9. Cuando la familia está completa, promover todas a `validada`.
10. **Aprender para la familia**: actualizar `.claude/skills/produccion-recetas/SKILL.md` con los patrones nuevos (ej: "envases 500cc para miel 640g"). Las siguientes familias heredan el aprendizaje.

### Orden sugerido de familias (de más fácil a más difícil)

1. **Coberturas** (pocas, fundamentales, ya validadas en OPs 2191/2194/2195) → banco de pruebas.
2. **Tabletas 73%** (lote fijo claro, ya en la skill).
3. **Propóleo + Polen** (envasado simple, 1 material principal + etiqueta + envase).
4. **Mieles** (mayor dificultad — OPs multi-producto, patrones de envase por peso).
5. **Cremas de maní** (similar a mieles).
6. **Chocolates mesa, cacao, nibs** (variado).
7. **Infusiones + otros** (case by case).

---

## Criterios de "receta válida"

Una receta pasa a `validada` cuando:

1. Tiene al menos **1 material** definido con cantidad y costo.
2. Tiene el **producto principal** con cantidad_por_lote y `precio_min_venta_snapshot` > 0.
3. `simular_op.py` genera un JSON que, comparado contra la **última OP vigente real** de ese producto:
   - Materiales: diferencia <5% en cantidad (excepto mermas documentadas).
   - Productos: cantidades coinciden exactas.
   - Costos: diferencia <10% en cantidad/costo_unit (M.O. varía por tamaño de lote).
4. `notas_analisis` tiene al menos 1 párrafo explicando el razonamiento (qué OPs se usaron, qué patrones se detectaron, qué dudas quedaron).
5. Si la receta tiene dudas no resueltas → se queda en `borrador` hasta consultar con Santi.

---

## Registro de razonamiento (auditoría)

Cada receta guarda en `notas_analisis` (markdown corto, <500 chars):

```
OPs analizadas: 2195, 2194, 2191 (últimas 3 vigentes)
Patrón: lote_fijo, 136 unid por lote.
Ratio cobertura: 5.585kg / 136 = 41g por tableta (coincide con 50g − 10g nibs).
Material distintivo: Nibs cacao cod 178 — ratio 0.735%.
Etiqueta: no presente en histórico (hereda de caja 412).
Dudas: ninguna.
Simulación OP 500 unid: 20.5kg cob + 3.7kg nibs → coincide con proyección lineal.
```

Esto es AUDITABLE — cualquiera (humano o IA) puede volver a validar la decisión leyendo las mismas OPs.

---

## Criterio de "listo para UI"

No se arranca la UI hasta que:
- **100% de los 108 productos tienen receta** (aunque sea `borrador`).
- **≥80% están `validada`**.
- El script `simular_op.py` funciona para cualquier receta sin errores.
- Los criterios §"receta válida" están documentados y respetados.

---

## UI (Fase final, post-recetas)

Ubicación: nuevo menú **Recetas** en el sidebar de `inv.oscomunidad.com` (la app React que ya está corriendo en puerto 9600 y que el otro agente está terminando de migrar).

Vistas:

1. **Lista** (`/recetas`):
   - OsDataTable con columnas: cod, producto, familia, patrón, confianza, estado, n_ops_ref, última actualización.
   - Filtros: familia, estado, confianza.
   - Buscador por cod o nombre.

2. **Detalle** (`/recetas/:cod`):
   - Cabecera: nombre + patrón + confianza + botones (editar / validar / regenerar / generar OP).
   - Tabs: **Materiales** / **Productos (principal + co)** / **Costos producción** / **Notas + OPs referencia**.
   - Edición inline con `q-input` / Quasar stylings que ya tenemos.

3. **Botón "Generar OP"**:
   - Pide cantidad al usuario.
   - Aplica patrón (multiplica por lote o ratio) y arma el JSON.
   - Lo envía a `scripts/import_orden_produccion.js` (ya operativo).
   - Reporta `OP_CREADA:NNNN`.

**5S aplicado** a la UI: una vista, un detalle, un botón por acción. Sin dashboards ni gráficos innecesarios.

---

## Criterios de Done (global)

- [ ] 4 tablas creadas en VPS y backupeadas.
- [ ] 5 scripts auxiliares funcionando y probados (`listar_universo`, `dossier_producto`, `construir_receta`, `simular_op`, `persistir_receta`).
- [ ] 108 recetas persistidas (mínimo en `borrador`).
- [ ] ≥80% en estado `validada`.
- [ ] Cada receta con `notas_analisis` y con OPs de referencia.
- [ ] UI con lista + detalle + botón generar OP.
- [ ] Documentación actualizada: `.agent/contextos/produccion.md`, `.claude/skills/produccion-recetas/SKILL.md` con patrones aprendidos (envases, etiquetas, mermas).

---

## Riesgos / Gotchas conocidos

1. **OPs multi-producto** (43% del total): el script se confunde. → mitigado con razonamiento manual + heurística del nombre.
2. **Precios que cambian** en Effi (cada X meses). → snapshot en la receta. Job nocturno actualiza snapshots (si cambió, alerta Telegram).
3. **Mermas** no documentadas: la suma de materiales no siempre iguala al peso producido. → tolerancia 5% en simulación.
4. **Etiquetas que no aparecen en histórico** (ej: cajas con etiqueta preimpresa). → documentar en `notas_analisis`, no inventar material.
5. **Co-productos inconsistentes**: a veces la OP de miel 640g incluye también miel 150g y otras no. → el script lo detecta por el umbral 60% (info['cantidades'] >= recetas_uso * 0.6). Si está por debajo, no se incluye.

---

## Próximo paso concreto

**Fase 1 (próxima sesión, duración estimada ~1h):**
1. Crear las 4 tablas en VPS (migration SQL + verificar).
2. Construir `listar_universo.py` → listar los 108 productos agrupados por familia.
3. Construir `dossier_producto.py` → que dado un cod devuelva toda la info de sus OPs.

Después de Fase 1, arrancar por familia **Coberturas** (Fase 2) como banco de pruebas. Si sale bien, sigo con Tabletas, y desde ahí se escala.
