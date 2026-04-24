---
estado: 🟡 BORRADOR — bloqueado en preguntas abiertas
creado: 2026-04-24
modulo: sistema_gestion
version_objetivo: v2.9.0 → v2.9.x
depende_de: v2.8.7 (Detalles de Producción en panel de tarea)
---

# Plan — Módulo "Órdenes de Producción" en app Gestión

## Resumen ejecutivo

Nuevo módulo dentro de `sistema_gestion` que replica el patrón del módulo **Proyectos** pero para **Órdenes de Producción (OPs)**. La OP es un "mini proyecto" que agrupa N tareas. Los tiempos y consumos reales se consolidan **a nivel OP** (no tarea).

Cambios principales:
1. **Quitar** de `DetallesProduccion.vue` los inputs de tiempo, observaciones manuales, y los botones Procesar/Validar. Queda **solo-lectura** (OP vinculada + materiales + productos con estimado desde Effi).
2. **Agregar** sección "Órdenes de producción" al sidebar (Mis Tareas + Equipo + tabla independiente) con el mismo patrón que Proyectos.
3. **Crear** ficha de OP con cabecera + materiales/productos reales editables + tiempos consolidados (automáticos desde cronómetro de las tareas agrupados por categoría de tiempo) + observaciones del lote + acciones Procesar/Validar.
4. **Agregar** a cada tarea vinculada a una OP la **categoría de tiempo** (lista fija: Alistamiento, Limpieza, Empaque, Enmoldado, Templado, Etiquetado, Sellado, Esterilización, Pasteurización, Encordonado, Loteado, Otra).

---

## 1. Estado actual (punto de partida verificado)

### Sistema Gestión (v2.8.7)
- Sidebar ya tiene patrón de Proyectos — [MainLayout.vue:40-395](../../../sistema_gestion/app/src/layouts/MainLayout.vue): bloque "Mis Tareas" + bloque "Equipo" + sección "Tablas". Cada bloque tiene acordeón con subitems clicables que filtran tareas por `proyecto_id`.
- Tabla Proyectos independiente: [ItemsTablePage.vue](../../../sistema_gestion/app/src/pages/ItemsTablePage.vue) con `OsDataTable`. Click en fila → abre `ProyectoPanel` lateral.
- `g_tareas` tiene `id_op VARCHAR(50)` ya usado (set por `OpSelector`).

### Detalles de Producción actual (a desmantelar parcialmente)
Archivo: [DetallesProduccion.vue](../../../sistema_gestion/app/src/components/DetallesProduccion.vue)
Endpoints actuales en [server.js:1369-1750](../../../sistema_gestion/api/server.js):
- `GET  /api/gestion/tareas/:id/produccion`
- `PUT  /api/gestion/tareas/:id/produccion/lineas/:lineaId`
- `PUT  /api/gestion/tareas/:id/produccion/tiempos` ← **ELIMINAR**
- `POST /api/gestion/tareas/:id/produccion/procesar` ← **MOVER a `/op/:id/procesar`**
- `POST /api/gestion/tareas/:id/produccion/validar` ← **MOVER a `/op/:id/validar`**

Tabla `g_tarea_produccion_lineas` (por tarea) → **migrar a `g_op_lineas` (por OP)**.
`g_tareas`: columnas `tiempo_alistamiento_min`, `tiempo_produccion_min`, `tiempo_empaque_min`, `tiempo_limpieza_min`, `id_op_original` → **`id_op_original` se MANTIENE** (ahora a nivel OP), los 4 tiempos se ELIMINAN de `g_tareas`.

### Fuente de OPs (solo lectura)
BD `os_integracion` en VPS Contabo:
- `zeffi_produccion_encabezados` — 2213 filas. Estados reales: `Generada` (968), `Procesada` (1243), `Validado` (2). Vigencia: `Vigente` (1158) / `Anulado` (1055).
- `zeffi_articulos_producidos` — productos por OP (cod_articulo, cantidad, precio_minimo_ud, etc.)
- `zeffi_materiales` — materiales por OP (cod_material, cantidad, costo_ud, etc.)

**Columnas útiles en `zeffi_produccion_encabezados`**: `id_orden`, `estado`, `vigencia`, `nombre_encargado`, `id_encargado`, `nombre_tercero`, `fecha_inicial`, `fecha_final`, `fecha_de_creacion`, `responsable_de_creacion`, `observacion`, `sucursal`, `bodega`.

---

## 2. Preguntas abiertas — BLOQUEAN Fase 1

**Hay que resolver esto antes de tocar código. Si quedan ambiguas, el módulo sale mal.**

### Q1 — Categoría de tiempo vs categoría de tarea
La tarea hoy tiene `categoria_id` que apunta a `g_categorias` (Producción, Ventas, Logística, etc., 13 seeds, con flags `es_produccion`, `es_empaque`).

Ahora quieres que cada tarea vinculada a una OP lleve **obligatoriamente** una "categoría de tiempo" (Alistamiento, Limpieza, Empaque, Enmoldado, Templado, Etiquetado, Sellado, Esterilización, Pasteurización, Encordonado, Loteado, Otra).

**¿Qué prefieres?**
- **Opción A** — Campo nuevo `categoria_tiempo` (VARCHAR o FK) en `g_tareas`. Se suma al `categoria_id` existente. Solo obligatorio si `id_op IS NOT NULL`.
- **Opción B** — Tabla nueva `g_categorias_tiempo` (id, nombre, orden, activa) + FK `g_tareas.categoria_tiempo_id`. Más prolijo y preparado para hacer configurable a futuro.
- **Opción C** — Reemplazar `categoria_id` SOLO en tareas de producción: el usuario cuando categoría=Producción elige una sub-categoría de esta lista en vez de la genérica.

**Mi recomendación: Opción B** (tabla nueva, FK, se siembran las 12 categorías de tiempo iniciales). Limpio y extensible.

### Q2 — ¿Qué estados filtra el sidebar en la parte de arriba?
Escribiste: *"salen todas las Ops en estado generada, o reportada (se omiten validadas y anuladas)"*.

Los estados reales de Effi son: **Generada / Procesada / Validado / Anulada**. ¿"Reportada" = "Procesada"?

Asumo que sí. **Confirmar.**

### Q3 — Columna "Responsable" en la tabla principal de OPs
Puede ser:
- (a) `nombre_encargado` de la OP en Effi (el que creó la OP allá, ej. "CLAUDIA PATRICIA SIERRA").
- (b) El responsable de la tarea de Gestión asociada a esa OP. Pero varias tareas → varios responsables.

**¿Cuál querés en la columna? Mi default: (a) — es dato directo de Effi, no ambiguo.**

### Q4 — Columna(s) de productos en la tabla
Escribiste: *"4 columnas para los 4 principales artículos producidos **o** un campo compuesto separado por comas"*.

**¿Cuál de las dos?**
- Compuesto separado por comas → 1 columna, simple. Lo recomiendo.
- 4 columnas → ¿criterio para elegir los 4 principales (mayor cantidad, mayor precio, alfabético)?

### Q5 — Materiales/artículos reales: ¿nueva tabla `g_op_lineas`?
Hoy están en `g_tarea_produccion_lineas` ligados a `tarea_id`. El nuevo modelo los quiere a **nivel OP**.

**Plan propuesto**: crear `g_op_lineas (id, id_op, tipo, cod_articulo, descripcion, unidad, cantidad_teorica, cantidad_real, costo_unit, precio_unit, usuario_ult_modificacion, fecha_ult_modificacion)` con `UNIQUE(id_op, tipo, cod_articulo)`. **Eliminar** `g_tarea_produccion_lineas` cuando la migración esté lista. ¿OK?

### Q6 — Observaciones del lote y tiempos manuales corregidos: ¿dónde viven?
Necesito una tabla nueva para lo agregado por Gestión a nivel OP (que no está en Effi). Propongo:

```sql
CREATE TABLE g_op_detalle (
  id_op VARCHAR(50) PRIMARY KEY,
  observaciones_lote TEXT NULL,
  tiempos_override_json JSON NULL,  -- {alistamiento:120, limpieza:30,...} solo en modo corrección
  procesado_por VARCHAR(255) NULL,
  procesado_en DATETIME NULL,
  validado_por VARCHAR(255) NULL,
  validado_en DATETIME NULL,
  id_op_original VARCHAR(50) NULL,
  empresa VARCHAR(64) NOT NULL
);
```

**¿OK con este diseño?**

### Q7 — "+ agregar material no previsto"
El plan anterior (Detalles de Producción) lo descartó. Acá aparece de nuevo en la ficha de OP. **¿Va en esta versión, sí o no?**

### Q8 — Permisos Procesar / Validar
Se mantienen igual que hoy a nivel OP:
- Procesar: cualquier responsable de alguna tarea de la OP, o nivel ≥ responsable de esas tareas.
- Validar: solo nivel ≥ 5.

**¿Se mantiene? ¿O cambia ahora que el contexto es OP (ej. cualquiera del equipo de producción puede procesar)?**

### Q9 — Observación de la nueva OP al validar
Hoy genera: `"Validación OS · Reportó: X · Validó: Y · Obs OP orig: ..."`

Dijiste: *"debe quedar Lote: xxxx siendo xxxx el numero de la op original. Ejemplo: op 12, al validar se anula la 12 y se crea la 17, entonces de primero en las observaciones de la op17 debe decir: LOTE 12, y adicional las otras cosas que habíamos definido como el responsable y podemos ponerle tambien los tiempos por categoria mayores a cero"*.

Propuesta de formato:
```
LOTE 12 · Validó: Santiago Sierra · Reportó: Claudia Sierra
Tiempos: Alistamiento 30m · Templado 240m · Enmoldado 45m · Empaque 90m · Limpieza 20m
Obs orig: <observación de la OP 12>
```

**¿OK el formato, o quieres otro?**

### Q10 — Eliminar/anular OP
Escribiste: *"Si se elimina una OP, las tareas quedan con `op_id = null`"*. Pero las OPs no se eliminan desde Gestión (son de Effi). ¿Te refieres a:
- Cuando en Effi la OP se anula (vigencia=Anulado) → las tareas de Gestión que la tenían vinculada quedan con `id_op = null`? (Eso no pasa hoy. Habría que hacerlo.)
- O cuando el usuario en Gestión "desvincula" manualmente la OP de una tarea?

**Clarificar.** Yo por ahora NO automatizaría nada: si en Effi se anula, la tarea en Gestión sigue mostrando el id_op pero con chip "Anulada" (gris).

### Q11 — Tareas mostradas en la ficha de OP
*"Tareas vinculadas a esa op. Lista de las tareas con fecha, responsable, tiempo y categoría. Click en una → abre esa tarea."*

**¿Muestra tareas de todos los usuarios o solo las del usuario actual?** Mi default: todas las del equipo.

### Q12 — Vista del sidebar "Mis Tareas" / "Equipo" al clicar una OP
- En "Mis Tareas" → filtra tareas con `id_op = X` **Y** `responsable = yo`. ✅ Claro.
- En "Equipo" → filtra todas las tareas con `id_op = X`. ✅ Claro.
- Se respetan las pestañas de fecha (Hoy/Mañana/Semana) y demás filtros existentes (estado, etc.).

**¿Confirmado?**

### Q13 — ¿Qué pasa con los datos viejos en `g_tarea_produccion_lineas`?
Hay datos ya registrados. Opciones:
- (a) Migrar a `g_op_lineas` (agrupando por `id_op` de la tarea; si 2 tareas distintas reportaron realidades para la misma OP, tomar la de la tarea más reciente). Luego DROP.
- (b) Dejar ambas tablas un tiempo, datos viejos quedan muertos.

**Mi recomendación: (a), mismo commit.** Confirmar.

---

## 3. Diseño de datos — cambios en BD `os_gestion`

### 3.1 Tablas nuevas

```sql
-- Categoría de tiempo (seed inicial de 12 rows)
CREATE TABLE g_categorias_tiempo (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE,
  orden  INT NOT NULL DEFAULT 0,
  activa TINYINT(1) NOT NULL DEFAULT 1
);

INSERT INTO g_categorias_tiempo (nombre, orden) VALUES
  ('Alistamiento', 1), ('Limpieza', 2), ('Empaque', 3), ('Enmoldado', 4),
  ('Templado', 5), ('Etiquetado', 6), ('Sellado', 7), ('Esterilización', 8),
  ('Pasteurización', 9), ('Encordonado', 10), ('Loteado', 11), ('Otra', 99);

-- Líneas de materiales + productos (consolidado a nivel OP)
CREATE TABLE g_op_lineas (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  id_op           VARCHAR(50) NOT NULL,
  empresa         VARCHAR(64) NOT NULL,
  tipo            ENUM('material','producto') NOT NULL,
  cod_articulo    VARCHAR(50) NOT NULL,
  descripcion     VARCHAR(500),
  unidad          VARCHAR(20),
  cantidad_teorica DECIMAL(12,3),
  cantidad_real   DECIMAL(12,3),
  costo_unit      DECIMAL(14,2),    -- costo_ud de Effi (snapshot)
  precio_unit     DECIMAL(14,2),    -- precio_minimo_ud de Effi (snapshot, solo productos)
  es_no_previsto  TINYINT(1) DEFAULT 0,  -- agregado manualmente (no estaba en Effi)
  usuario_ult_modificacion VARCHAR(255),
  fecha_ult_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unq_op_tipo_cod (id_op, tipo, cod_articulo),
  INDEX idx_op (id_op)
);

-- Detalle OP agregado por Gestión (lo que no está en Effi)
CREATE TABLE g_op_detalle (
  id_op                   VARCHAR(50) NOT NULL,
  empresa                 VARCHAR(64) NOT NULL,
  observaciones_lote      TEXT NULL,
  tiempos_override_json   JSON NULL,
  procesado_por           VARCHAR(255) NULL,
  procesado_en            DATETIME NULL,
  validado_por            VARCHAR(255) NULL,
  validado_en             DATETIME NULL,
  id_op_original          VARCHAR(50) NULL,
  PRIMARY KEY (id_op, empresa)
);
```

### 3.2 Alter `g_tareas`

```sql
-- Agregar FK categoría de tiempo (NULL si la tarea no está vinculada a OP)
ALTER TABLE g_tareas ADD COLUMN categoria_tiempo_id INT NULL;
ALTER TABLE g_tareas ADD INDEX idx_categoria_tiempo (categoria_tiempo_id);

-- Eliminar columnas de tiempo manuales (ahora se consolidan automáticamente en la OP)
ALTER TABLE g_tareas DROP COLUMN tiempo_alistamiento_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_produccion_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_empaque_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_limpieza_min;
ALTER TABLE g_tareas DROP COLUMN id_op_original;  -- ahora vive en g_op_detalle
```

### 3.3 Migración de datos existentes

Antes del DROP en `g_tareas`:
1. Backup completo: `mysqldump os_gestion g_tareas g_tarea_produccion_lineas > backups/os_gestion/pre_op_module_{ts}.sql`
2. Migrar filas de `g_tarea_produccion_lineas` → `g_op_lineas` con UPSERT por `(id_op, tipo, cod_articulo)` (si duplicadas, tomar la de mayor `fecha_ult_modificacion`).
3. Migrar `g_tareas.id_op_original` a `g_op_detalle.id_op_original`.
4. Drop `g_tarea_produccion_lineas` después de verificar.

---

## 4. Endpoints API

### 4.1 Nuevos — OPs (a nivel OP, no tarea)
```
GET  /api/gestion/op                        — listar OPs (filtros ?estado=&vigencia=&q=&desde=&hasta=)
                                              Mezcla zeffi_produccion_encabezados con g_op_detalle.
                                              Campos: id_orden, estado, vigencia, nombre_encargado,
                                              fecha_inicial, fecha_de_creacion, articulos,
                                              procesado_por, procesado_en, validado_por, validado_en
GET  /api/gestion/op/:id                    — detalle completo:
                                              { cabecera (Effi), materiales[], productos[],
                                                tiempos_consolidados[{categoria_tiempo, minutos}],
                                                tareas_vinculadas[], detalle (g_op_detalle) }
PUT  /api/gestion/op/:id/detalle            — guardar observaciones_lote + tiempos_override_json
PUT  /api/gestion/op/:id/lineas/:lineaId    — actualizar cantidad_real (y/o costo/precio)
POST /api/gestion/op/:id/lineas             — agregar línea no prevista (si Q7=sí)
DELETE /api/gestion/op/:id/lineas/:lineaId  — eliminar línea no prevista (si Q7=sí)
POST /api/gestion/op/:id/procesar           — mover del endpoint de tarea (lógica idéntica)
POST /api/gestion/op/:id/validar            — mover del endpoint de tarea (lógica ajustada al formato Q9)
```

### 4.2 Nuevos — Categorías de tiempo
```
GET /api/gestion/categorias-tiempo          — seed de 12 filas
```

### 4.3 Ajuste en GET /api/gestion/tareas
Devolver `categoria_tiempo_id`, `categoria_tiempo_nombre`.

### 4.4 Eliminar / deprecar
- `PUT  /api/gestion/tareas/:id/produccion/tiempos` → eliminar.
- `POST /api/gestion/tareas/:id/produccion/procesar` → **redirigir 307** al equivalente de OP durante 1 release.
- `POST /api/gestion/tareas/:id/produccion/validar` → idem.

### 4.5 Simplificar
`GET /api/gestion/tareas/:id/produccion` → retorna **solo** materiales + productos desde `g_op_lineas` (ya agregados a nivel OP). El frontend de `DetallesProduccion.vue` deja de editar nada.

---

## 5. Frontend — cambios por componente

### 5.1 `DetallesProduccion.vue` — reducir a solo-lectura
- Quitar inputs de tiempos (bloque entero).
- Quitar textarea de observaciones.
- Quitar botones Procesar / Validar + sus modales de confirmación.
- Materiales y productos: solo lectura. Para editar cantidad real → **link "Editar en la OP"** que abre la ficha de OP.
- Mantener chip de estado OP (Generada / Procesada / Validado / Anulada).

### 5.2 Componente nuevo: `OpPanel.vue` (equivalente a `ProyectoPanel.vue`)
Panel lateral derecho 500px desktop, bottom-sheet móvil. Bloques:
1. **Cabecera** (readonly): `id_orden`, producto principal, estado (chip), fecha creación, nombre_encargado.
2. **Materiales** (tabla): `Material | Estimado | Real | Costo unit | Subtotal real`. Inputs de real con `parseDecimal` + autosave debounce 800ms. Botón **+ agregar material no previsto** (si Q7=sí).
3. **Artículos producidos** (tabla): `Artículo | Estimado | Real | Precio unit | Subtotal real`. Mismo patrón.
4. **Tiempos consolidados** (grid o tabla): se calcula en backend sumando `cronometro` de las tareas vinculadas agrupando por `categoria_tiempo`. Muestra `Categoría | Minutos`. Botón "modo corrección" abre inputs para override manual → guarda en `g_op_detalle.tiempos_override_json`.
5. **Tareas vinculadas** (lista): filas con `fecha | responsable | título | categoría_tiempo | cron | estado`. Click → abre `TareaPanel` embebido con ← Volver (mismo patrón que ProyectoPanel).
6. **Observaciones del lote** (textarea): autosave debounce 1s → `g_op_detalle.observaciones_lote`.
7. **Acciones**: `[Procesar]` (responsable o ≥ responsable) y `[Validar]` (nivel ≥ 5). Mismas protecciones 503 + retry.

### 5.3 `ItemsTablePage.vue` reutilizable → extender con `tipo='op'` **o** crear `OpTablePage.vue`
Decisión: **crear `OpTablePage.vue` separado** (comportamiento distinto: origen de datos es `os_integracion` no `g_proyectos`; hay columna de artículos compuesta; ordena por estado-entonces-fecha).

Columnas de la tabla (orden propuesto):
1. `estado` (chip, prioriza Generada primero)
2. `id_orden`
3. `nombre_encargado` (Responsable)
4. `articulos` (compuesto separado por comas — según Q4)
5. `fecha_de_creacion`
6. `vigencia` (chip chico)

Ordenamiento default: `FIELD(estado, 'Generada', 'Procesada', 'Validado'), fecha_de_creacion DESC`.
Click en fila → abre `OpPanel`.

### 5.4 `MainLayout.vue` — sidebar
Agregar bloque "Órdenes de Producción" al mismo nivel que "Proyectos":

**Arriba (en bloque "Mis Tareas" y "Equipo")**:
```
▸ Órdenes de producción
   ├─ OP 2180 · Chocolate 70% · Generada  [N tareas mías]
   ├─ OP 2181 · Nibs 100g · Procesada     [M]
   └─ ...
```
Click → navega a `/tareas?op_id=X` (Mis) o `/equipo?op_id=X` (Equipo). TareasPage filtra por `id_op`.

**Abajo (sección "Tablas")**:
```
[icon precision_manufacturing] Órdenes de producción    → ruta `/ops-tabla`
```

### 5.5 `TareasPage.vue` — agregar filtro por `op_id`
Equivalente a `proyecto_id`. `watch($route.query.op_id)` + backend.

### 5.6 `TareaForm.vue` + `TareaPanel.vue` — selector de categoría de tiempo
Si la tarea tiene `id_op`: mostrar selector obligatorio `categoria_tiempo_id` (chips pill, 12 opciones). Si no tiene OP: oculto.

### 5.7 Ruta nueva
`src/router/routes.js`:
```js
{ path: 'ops-tabla', component: () => import('pages/OpTablePage.vue') }
```

---

## 6. Backend — lógica especial

### 6.1 Tiempos consolidados por categoría (GET /api/gestion/op/:id)
```sql
SELECT ct.nombre AS categoria_tiempo,
       SUM(t.duracion_cronometro_seg) / 60 AS minutos
FROM g_tareas t
LEFT JOIN g_categorias_tiempo ct ON ct.id = t.categoria_tiempo_id
WHERE t.id_op = ? AND t.empresa = ?
GROUP BY ct.id, ct.nombre
ORDER BY ct.orden
```
Si hay override en `g_op_detalle.tiempos_override_json`, retorna override.

### 6.2 Observación de la OP nueva al validar (Q9)
Nueva plantilla:
```js
const tiemposStr = tiempos.filter(t => t.minutos > 0)
  .map(t => `${t.categoria_tiempo} ${t.minutos}m`).join(' · ')
const observacion = [
  `LOTE ${idOpOriginal}`,
  `Validó: ${nombreValidador}`,
  `Reportó: ${nombreReportador}`,
  tiemposStr && `Tiempos: ${tiemposStr}`,
  obsOriginal && `Obs orig: ${obsOriginal.slice(0, 200)}`
].filter(Boolean).join(' · ')
```

---

## 7. Fases de ejecución

### Fase 0 — Aclarar preguntas abiertas (Santi)
Bloquea todo lo demás. Sin respuestas a Q1–Q13, no se toca código.

### Fase 1 — Schema + migración datos
1. Backup completo BD `os_gestion` en VPS.
2. Crear `g_categorias_tiempo`, `g_op_lineas`, `g_op_detalle`.
3. ALTER `g_tareas`: agregar `categoria_tiempo_id`.
4. Migrar datos: `g_tarea_produccion_lineas` → `g_op_lineas`; `g_tareas.id_op_original` → `g_op_detalle.id_op_original`.
5. Validar conteos post-migración. DROP `g_tarea_produccion_lineas` y las 4 columnas de tiempo de `g_tareas`.

### Fase 2 — Backend: endpoints OP
1. `GET /api/gestion/op` y `GET /api/gestion/op/:id` (con materiales, productos, tiempos consolidados, tareas vinculadas, detalle).
2. `PUT` detalle + lineas. `POST/DELETE` líneas no previstas (Q7).
3. Mover `procesar` y `validar` a `/op/:id/...` con la nueva plantilla de observación.
4. Endpoint `GET /api/gestion/categorias-tiempo`.
5. Ajustar `GET /api/gestion/tareas` → devolver `categoria_tiempo_*`; soportar filtro `op_id`.
6. Endpoint 307 redirect para las rutas viejas (compat temporal).

### Fase 3 — Frontend: reducir `DetallesProduccion.vue`
Quitar inputs/botones. Link "Editar en la OP" (si hay OP).

### Fase 4 — Frontend: `OpPanel.vue`
7 bloques (ver 5.2). Reutilizar patrones de `ProyectoPanel` donde apliquen.

### Fase 5 — Frontend: `OpTablePage.vue` + ruta
OsDataTable con columnas del 5.3. Click → OpPanel.

### Fase 6 — Frontend: Sidebar en MainLayout
Sección "Órdenes de producción" en Mis Tareas + Equipo + Tablas. Carga de OPs vía `/api/gestion/op?estado_in=Generada,Procesada`.

### Fase 7 — Frontend: TareasPage + TareaForm/Panel
Filtro `op_id`. Selector `categoria_tiempo_id` visible si `id_op` seteado, obligatorio al guardar.

### Fase 8 — Testing end-to-end
- Crear tarea con OP y categoría de tiempo → cronómetro → ver suma en ficha OP.
- Abrir ficha OP → editar real de material → autosave.
- Procesar OP desde ficha (responsable) → estado pasa a Procesada en Effi + staging + chip.
- Validar OP (nivel ≥ 5) → anular + crear + estado Validado. Observación nueva: `LOTE xxxx · Validó...`.
- Sidebar: click OP → filtra tareas. Mobile + desktop + dark + claro.

### Fase 9 — Limpieza
Eliminar endpoints viejos tras confirmar que el frontend no los llama. Actualizar `.agent/contextos/sistema_gestion.md` y `CATALOGO_APIS.md`. Bump versión MainLayout.

---

## 8. Archivos a crear/modificar

### Nuevos
- `sistema_gestion/app/src/components/OpPanel.vue`
- `sistema_gestion/app/src/pages/OpTablePage.vue`
- `sistema_gestion/app/src/components/CategoriaTiempoSelector.vue`
- `sistema_gestion/api/migrations/2026-04-24_modulo_op.sql`

### Modificados
- `sistema_gestion/app/src/components/DetallesProduccion.vue` — reducir
- `sistema_gestion/app/src/components/TareaForm.vue` — selector categoría tiempo
- `sistema_gestion/app/src/components/TareaPanel.vue` — selector categoría tiempo
- `sistema_gestion/app/src/pages/TareasPage.vue` — filtro op_id
- `sistema_gestion/app/src/layouts/MainLayout.vue` — sidebar
- `sistema_gestion/app/src/router/routes.js` — ruta `/ops-tabla`
- `sistema_gestion/api/server.js` — endpoints (nuevos + deprecar viejos + filtro op_id en tareas)

### Eliminados tras validar
- Tabla `g_tarea_produccion_lineas`
- Columnas `tiempo_*` y `id_op_original` de `g_tareas`
- Endpoints viejos `/tareas/:id/produccion/tiempos`, `/procesar`, `/validar`

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Datos en `g_tarea_produccion_lineas` se pierden | Backup antes. Migración con conteos antes/después. Rollback SQL listo. |
| Usuarios con la app abierta llaman endpoints viejos | 307 redirect a los nuevos durante 1 release + bump versión MainLayout fuerza refresh PWA. |
| OPs anuladas en Effi rompen UI al cargar | Incluir `vigencia` en respuestas; frontend muestra chip gris "Anulada" sin fallar. |
| `categoria_tiempo_id NOT NULL` rompe tareas existentes sin OP | Nullable. Solo obligatorio en frontend cuando `id_op` seteado. |
| Playwright no disponible en servidor de respaldo | Ya existe protección 503 + retry del frontend (v2.8.5). Se mantiene. |

---

## 10. Tareas para Antigravity (Google Labs)

- QA visual del `OpPanel` y `OpTablePage` contra el mockup y el patrón de Proyectos. Spacing, tipografía, chips.
- Revisar que la UX del sidebar (3 niveles — OP, arriba en "Mis/Equipo" y abajo en "Tablas") no se sienta redundante.

## 11. Tareas para Subagentes (Claude)

- Fase 1 (migración SQL): `feature-dev:code-architect` prepara las sentencias + script de migración idempotente.
- Fase 2 (endpoints backend): subagente genera los 6 endpoints nuevos + ajustes al listado de tareas.
- Fase 4 (OpPanel): subagente genera el componente Vue con los 7 bloques.
- Fase 5 (OpTablePage): subagente genera la página tabla.
