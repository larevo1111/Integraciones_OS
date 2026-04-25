---
estado: ✅ APROBADO — listo para Fase 1 (pendiente de arrancar)
creado: 2026-04-24
aprobado: 2026-04-24
modulo: sistema_gestion
version_objetivo: v2.9.0 → v2.9.x
depende_de: v2.8.7 (Detalles de Producción en panel de tarea)
---

# Plan — Módulo "Órdenes de Producción" en app Gestión

## Resumen ejecutivo

Nuevo módulo en `sistema_gestion` que replica el patrón del módulo **Proyectos** pero para **Órdenes de Producción (OPs)**. La OP es un "mini proyecto" que agrupa N tareas. Los tiempos y consumos reales se consolidan **a nivel OP** (no tarea).

Cambios principales:
1. **Reducir** `DetallesProduccion.vue` del panel de tarea: queda solo-lectura. Se quitan tiempos, observaciones manuales y botones Procesar/Validar.
2. **Agregar** sección "Órdenes de producción" al sidebar (Mis Tareas + Equipo + tabla independiente).
3. **Crear** ficha de OP (`OpPanel`) con cabecera + materiales/productos reales + tiempos consolidados automáticos + observaciones + Procesar/Validar.
4. **Agregar** campo `categoria_produccion_id` a cada tarea vinculada a OP (Alistamiento, Templado, etc.).
5. **Crear tabla `g_op_tiempos`** que al validar una OP snapshotea los segundos totales por categoría, para análisis histórico.

---

## 1. Estado actual verificado

### Sistema Gestión (v2.8.7)
- Sidebar con patrón Proyectos: [MainLayout.vue:40-395](../../../sistema_gestion/app/src/layouts/MainLayout.vue).
- Tabla Proyectos: [ItemsTablePage.vue](../../../sistema_gestion/app/src/pages/ItemsTablePage.vue) con `OsDataTable`. Click → `ProyectoPanel`.
- `g_tareas.id_op VARCHAR(50)` ya lo setea `OpSelector`.

### Detalles de Producción actual (a desmantelar parcialmente)
- Componente: [DetallesProduccion.vue](../../../sistema_gestion/app/src/components/DetallesProduccion.vue).
- Endpoints en [server.js:1369-1750](../../../sistema_gestion/api/server.js): quedará solo el GET reducido.
- Tabla `g_tarea_produccion_lineas` → se **DROPEA** (datos viejos descartados — Q13).
- `g_tareas`: columnas `tiempo_alistamiento_min`, `tiempo_produccion_min`, `tiempo_empaque_min`, `tiempo_limpieza_min`, `id_op_original` → **eliminar**.

### Fuente de OPs (solo lectura)
BD `os_integracion` en VPS (94.72.115.156):
- `zeffi_produccion_encabezados` — 2213 filas. Estados: `Generada` (968), `Procesada` (1243), `Validado` (2). Vigencia: `Vigente` (1158) / `Anulado` (1055).
- `zeffi_articulos_producidos` — productos (cod_articulo, cantidad, precio_minimo_ud).
- `zeffi_materiales` — materiales (cod_material, cantidad, costo_ud).

Columnas relevantes de `zeffi_produccion_encabezados`: `id_orden`, `estado`, `vigencia`, `nombre_encargado`, `id_encargado` (formato `CC: 1128457413`), `fecha_inicial`, `fecha_final`, `fecha_de_creacion`, `observacion`, `sucursal`, `bodega`.

### Mapeo usuarios Effi ↔ Gestión (Q3 verificado)
`sys_usuarios` (Hostinger) tiene `num_id VARCHAR(50)` → hoy todos en NULL excepto los que actualicemos. 7 usuarios activos legítimos (el 8º, maskedaltfivem, ya fue eliminado 2026-04-24 por intrusión — ver sección §12).

**Cédulas confirmadas por Santi**:

| Email | Cédula | Nombre Effi |
|---|---|---|
| ssierra047@gmail.com (Santiago) | **3506889** | — |
| jennifercanogarcia@gmail.com | 1128457413 | Jenifer Alexandra Cano Garcia |
| amaragonzalez21valen@gmail.com (Deivy) | 74084937 | Deivy Andres Gonzalez Gutierrez |
| lauramarcela758@gmail.com | 1017206760 | LAURA MARCELA ECHAVARRIA PATIÑO |
| rialgar82@gmail.com | 3502398759 | Ricardo Garcia |
| larevo1111@gmail.com, doblessas@gmail.com | **no mapear** | no activos en Effi |

**Pendiente**: Santi dijo "las demás no importan" — se interpretan como no mapeables. Si alguno aparece luego como encargado de Effi, se amplía el mapeo.

---

## 2. Decisiones cerradas (todas confirmadas por Santi 2026-04-24)

| # | Decisión |
|---|---|
| Q1 | `categoria_produccion_id INT NULL` en `g_tareas` + tabla seed `g_categorias_produccion` (12 filas) |
| Q2 | Sidebar muestra OPs en estado Generada **y** Procesada (omite Validado + Anulada) |
| Q3 | UPDATE `sys_usuarios.num_id` con cédulas confirmadas (5 usuarios) |
| Q4 | Columna `articulos` = string compuesto separado por comas |
| Q5 | Nueva `g_op_lineas` (materiales+productos real a nivel OP) + **nueva `g_op_tiempos`** (snapshot segundos totales por categoría al validar) |
| Q6 | Nueva `g_op_detalle` (obs lote + sellos procesar/validar + op_anterior) — separada de Q5 |
| Q7 | Botón "+ agregar material no previsto" en ficha OP, **solo si estado=Generada** |
| Q8 | Procesar: `nivel ≥ 3` · Validar: `nivel ≥ 5` |
| Q9 | Observación OP nueva = `LOTE X · Validó · Reportó · Creada/Procesada/Validada · Tiempos · Obs orig` |
| Q10 | Al validar: anular en Effi → crear nueva (Playwright) → UPDATE `g_tareas SET id_op = id_nueva` → guardar `op_anterior` en `g_op_detalle` de la nueva |
| Q11 | Ficha OP muestra TODAS las tareas vinculadas (sin filtro de responsable) |
| Q12 | Sidebar "Mis" filtra id_op+responsable=yo · "Equipo" filtra solo id_op |
| Q13 | `g_tarea_produccion_lineas` se DROPEA, datos viejos se descartan (no migrar) |

### Detalle — responsable de la OP (Q3 aclaración Santi)
- En la tabla y ficha: el **`nombre_encargado`** de la OP en Effi (el que figura allá).
- Las tareas tienen sus propios responsables (los de Gestión, independientes).
- **Al validar**, el responsable de la OP nueva se puede cambiar por el del validador (ver `g_op_detalle.responsable_validado`).

### Detalle — snapshot de tiempos al validar (Q5 ampliado)
- Mientras la OP está Generada/Procesada → tiempos se calculan **al vuelo** con `SUM(duracion_cronometro_seg) GROUP BY categoria_produccion_id` sobre `g_tareas` (cifras vivas, siguen moviendo).
- **Al validar** → se congela un snapshot en `g_op_tiempos` (una fila por categoría con segundos > 0). A partir de ahí la ficha lee de esa tabla.
- La clave `(id_op, empresa, categoria_produccion_id)` garantiza no duplicar.
- Los totales van también a la observación de la nueva OP en Effi (ver §6.2).

---

## 3. Diseño de datos — BD `os_gestion` (VPS)

### 3.1 Tabla seed: categorías de producción

```sql
CREATE TABLE g_categorias_produccion (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE,
  orden  INT NOT NULL DEFAULT 0,
  activa TINYINT(1) NOT NULL DEFAULT 1
);

INSERT INTO g_categorias_produccion (nombre, orden) VALUES
  ('Alistamiento',   1),
  ('Templado',       2),
  ('Enmoldado',      3),
  ('Empaque',        4),
  ('Etiquetado',     5),
  ('Sellado',        6),
  ('Esterilización', 7),
  ('Pasteurización', 8),
  ('Encordonado',    9),
  ('Loteado',       10),
  ('Limpieza',      11),
  ('Otra',          99);
```

### 3.2 Tabla de líneas materiales/productos (a nivel OP)

```sql
CREATE TABLE g_op_lineas (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  id_op            VARCHAR(50) NOT NULL,
  empresa          VARCHAR(64) NOT NULL,
  tipo             ENUM('material','producto') NOT NULL,
  cod_articulo     VARCHAR(50) NOT NULL,
  descripcion      VARCHAR(500),
  unidad           VARCHAR(20),
  cantidad_teorica DECIMAL(12,3),
  cantidad_real    DECIMAL(12,3),
  costo_unit       DECIMAL(14,2),
  precio_unit      DECIMAL(14,2),
  es_no_previsto   TINYINT(1) DEFAULT 0,
  usuario_ult_modificacion VARCHAR(255),
  fecha_ult_modificacion   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unq_op_tipo_cod (id_op, empresa, tipo, cod_articulo),
  INDEX idx_op (id_op, empresa)
);
```

### 3.3 Tabla de tiempos consolidados (snapshot al validar)

```sql
CREATE TABLE g_op_tiempos (
  id_op                    VARCHAR(50) NOT NULL,
  empresa                  VARCHAR(64) NOT NULL,
  categoria_produccion_id  INT NOT NULL,
  segundos_totales         INT NOT NULL DEFAULT 0,
  fecha_totalizacion       DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_op, empresa, categoria_produccion_id),
  INDEX idx_cat (categoria_produccion_id),
  FOREIGN KEY (categoria_produccion_id) REFERENCES g_categorias_produccion(id)
);
```

### 3.4 Tabla de detalle OP (1 fila por OP)

```sql
CREATE TABLE g_op_detalle (
  id_op                   VARCHAR(50) NOT NULL,
  empresa                 VARCHAR(64) NOT NULL,
  observaciones_lote      TEXT NULL,
  procesado_por           VARCHAR(255) NULL,
  procesado_en            DATETIME NULL,
  validado_por            VARCHAR(255) NULL,
  validado_en             DATETIME NULL,
  op_anterior             VARCHAR(50) NULL,       -- si esta OP viene de validación
  responsable_validado    VARCHAR(255) NULL,      -- email, puede cambiar al validar
  fecha_creacion_detalle  DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_modificacion  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id_op, empresa)
);
```

### 3.5 Alter `g_tareas`

```sql
-- Nueva columna FK
ALTER TABLE g_tareas ADD COLUMN categoria_produccion_id INT NULL;
ALTER TABLE g_tareas ADD INDEX idx_categoria_produccion (categoria_produccion_id);

-- Eliminar columnas obsoletas
ALTER TABLE g_tareas DROP COLUMN tiempo_alistamiento_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_produccion_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_empaque_min;
ALTER TABLE g_tareas DROP COLUMN tiempo_limpieza_min;
ALTER TABLE g_tareas DROP COLUMN id_op_original;  -- ahora vive en g_op_detalle.op_anterior
```

### 3.6 DROP tabla vieja (Q13)

```sql
DROP TABLE g_tarea_produccion_lineas;
```

### 3.7 Update cédulas en Hostinger (Q3)

```sql
-- Solo los 5 mapeables confirmados
UPDATE sys_usuarios SET num_id='3506889'     WHERE Email='ssierra047@gmail.com';
UPDATE sys_usuarios SET num_id='1128457413'  WHERE Email='jennifercanogarcia@gmail.com';
UPDATE sys_usuarios SET num_id='74084937'    WHERE Email='amaragonzalez21valen@gmail.com';
UPDATE sys_usuarios SET num_id='1017206760'  WHERE Email='lauramarcela758@gmail.com';
UPDATE sys_usuarios SET num_id='3502398759'  WHERE Email='rialgar82@gmail.com';
```

---

## 4. Endpoints API

### 4.1 Nuevos — OPs
```
GET  /api/gestion/op                        — listar (?estado=&vigencia=&q=&desde=&hasta=)
                                              Fuente: zeffi_produccion_encabezados ∪ g_op_detalle
                                              Columnas: id_orden, estado, vigencia, nombre_encargado,
                                              fecha_creacion, articulos (comp.), procesado/validado
GET  /api/gestion/op/:id                     — detalle:
                                              { cabecera, materiales[], productos[],
                                                tiempos[{categoria, segundos}],
                                                tareas_vinculadas[], detalle }
                                              Tiempos: si hay g_op_tiempos → leer de ahí;
                                                        si no → calcular al vuelo sobre g_tareas.
PUT  /api/gestion/op/:id/detalle             — obs_lote + responsable_validado
PUT  /api/gestion/op/:id/lineas/:lineaId     — cantidad_real
POST /api/gestion/op/:id/lineas              — línea no prevista (solo si estado=Generada)
DELETE /api/gestion/op/:id/lineas/:lineaId   — borrar no prevista
POST /api/gestion/op/:id/procesar            — nivel ≥ 3
POST /api/gestion/op/:id/validar             — nivel ≥ 5
```

### 4.2 Categorías de producción
```
GET /api/gestion/categorias-produccion       — 12 seeds
```

### 4.3 Ajuste `GET /api/gestion/tareas`
- Incluir `categoria_produccion_id` y `categoria_produccion_nombre`.
- Aceptar filtro `?op_id=X`.

### 4.4 Endpoints a eliminar
- `PUT  /api/gestion/tareas/:id/produccion/tiempos`
- `POST /api/gestion/tareas/:id/produccion/procesar`
- `POST /api/gestion/tareas/:id/produccion/validar`
- `GET  /api/gestion/tareas/:id/produccion` → reducir: retorna materiales/productos desde `g_op_lineas` en modo readonly.

---

## 5. Frontend — cambios por componente

### 5.1 `DetallesProduccion.vue` (reducir)
- Quitar inputs de tiempos.
- Quitar textarea observaciones.
- Quitar botones Procesar/Validar + modales.
- Materiales y productos: readonly. Mostrar desde `g_op_lineas`.
- Link "Editar en la OP" que abre `OpPanel`.
- Mantener chip de estado OP.

### 5.2 `OpPanel.vue` (nuevo — 500px desktop / bottom-sheet móvil)

**7 bloques**:

1. **Cabecera** (readonly): `id_orden`, artículo principal, chip de estado, `fecha_de_creacion`, `nombre_encargado`.
2. **Materiales** (tabla editable): `Material | Est. | Real | Costo U | Subtotal`. Autosave 800ms. Botón **"+ agregar material no previsto"** solo visible si `estado = Generada`.
3. **Artículos producidos** (tabla editable): `Artículo | Est. | Real | Precio U | Subtotal`.
4. **Tiempos consolidados** (tabla readonly): `Categoría | Tiempo (hh:mm:ss)`. Si OP validada → lee `g_op_tiempos`; si no → calcula al vuelo.
5. **Tareas vinculadas** (lista): `fecha · responsable · título · categoría_produccion · cron · estado`. Click → `TareaPanel` embebido con ← Volver.
6. **Observaciones del lote** (textarea): autosave 1s.
7. **Acciones**: `[Procesar]` (nivel ≥ 3) y `[Validar]` (nivel ≥ 5). Modales dark. 503+retry si Playwright.

### 5.3 `OpTablePage.vue` (nuevo)
Columnas:
1. `estado` (chip con colores; orden prioriza Generada)
2. `id_orden`
3. `nombre_encargado`
4. `articulos` (compuesto comas, truncado con tooltip)
5. `fecha_de_creacion`
6. `vigencia` (chip chico)

Orden default SQL:
```sql
ORDER BY FIELD(estado,'Generada','Procesada','Validado','Anulada'), fecha_de_creacion DESC
```
Click fila → `OpPanel`.

### 5.4 `MainLayout.vue` — sidebar

**Mis Tareas** (acordeón superior):
```
▸ Órdenes de producción (5)
    [🟢 Generada]   OP 2180 · 3 mis tareas
    [🟠 Procesada]  OP 2181 · 1 mi tarea
```
Fuente: OPs con ≥ 1 tarea del usuario actual. Click → `/tareas?op_id=X`.

**Equipo** (acordeón): mismo patrón sin filtro de responsable. Click → `/equipo?op_id=X`.

**Tablas** (sección inferior): link "Órdenes de producción" → `/ops-tabla`.

### 5.5 `TareasPage.vue`
`watch($route.query.op_id)` → refetch con filtro, análogo a `proyecto_id`.

### 5.6 `TareaForm.vue` + `TareaPanel.vue`
Selector `categoria_produccion_id` (chips pill). Solo visible si `tarea.id_op` seteado. Obligatorio al guardar.

### 5.7 `src/router/routes.js`
```js
{ path: 'ops-tabla', component: () => import('pages/OpTablePage.vue') }
```

---

## 6. Backend — lógica especial

### 6.1 Tiempos consolidados (GET /api/gestion/op/:id)

```js
async function tiemposConsolidados(idOp, empresa) {
  // Si hay snapshot (OP validada) → usar eso
  const [snapshot] = await db.gestion.query(
    `SELECT cp.nombre AS categoria, ot.segundos_totales AS segundos
     FROM g_op_tiempos ot
     JOIN g_categorias_produccion cp ON cp.id = ot.categoria_produccion_id
     WHERE ot.id_op = ? AND ot.empresa = ?
     ORDER BY cp.orden`,
    [idOp, empresa]
  )
  if (snapshot.length) return { fuente: 'snapshot', tiempos: snapshot }

  // Si no → calcular al vuelo
  const [vivo] = await db.gestion.query(
    `SELECT cp.nombre AS categoria,
            COALESCE(SUM(t.duracion_cronometro_seg),0) AS segundos
     FROM g_tareas t
     LEFT JOIN g_categorias_produccion cp ON cp.id = t.categoria_produccion_id
     WHERE t.id_op = ? AND t.empresa = ?
     GROUP BY cp.id, cp.nombre
     HAVING segundos > 0
     ORDER BY cp.orden`,
    [idOp, empresa]
  )
  return { fuente: 'vivo', tiempos: vivo }
}
```
Frontend convierte `segundos` → `hh:mm:ss`.

### 6.2 Procesar OP (POST /api/gestion/op/:id/procesar)

```
1. Validar nivel ≥ 3 (desde JWT).
2. Observacion = "Procesado por <nombre> (OS Gestión)".
3. execFile cambiar_estado_orden_produccion.js(id_op, 'Procesada', observacion).
4. UPDATE o INSERT en g_op_detalle: procesado_por, procesado_en = NOW().
5. UPDATE staging zeffi_produccion_encabezados SET estado='Procesada'.
6. Responder OK.
```

### 6.3 Validar OP (POST /api/gestion/op/:id/validar) — flujo completo

```
1. Validar nivel ≥ 5.
2. Cargar metadata OP original (zeffi_produccion_encabezados).
3. Cargar g_op_lineas + g_op_detalle.observaciones_lote + g_op_detalle.procesado_en.
4. Calcular tiempos consolidados (§6.1, modo vivo).
5. Armar observación nueva (Q9):
     LOTE <id_original> · Validó: <nombre> · Reportó: <nombre_encargado_effi>
     Creada: <fecha_orig> · Procesada: <procesado_en> · Validada: <AHORA>
     Tiempos: Templado 4h0m · Enmoldado 45m · ...
     Obs orig: <observaciones_lote + observacion_effi>
6. Playwright: anular_orden_produccion.js(id_original, observacion).
7. Playwright: import_orden_produccion.js(json con reales) → capturar OP_CREADA:<id_nueva>.
8. Playwright: cambiar_estado_orden_produccion.js(id_nueva, 'Validado', observacion).
9. UPDATE g_tareas SET id_op=<id_nueva> WHERE id_op=<id_original>.
10. INSERT INTO g_op_detalle (id_nueva):
      op_anterior=<id_original>, validado_por, validado_en=NOW(),
      observaciones_lote=<copia>, responsable_validado=<opcional>.
11. Copiar g_op_lineas al id_nueva (nuevas filas con id_op=<id_nueva>, cantidad_real=cantidad_teorica=lo reportado).
12. Calcular tiempos consolidados sobre <id_nueva> (ahora las tareas apuntan ahí)
    → INSERT INTO g_op_tiempos una fila por categoría con segundos > 0.
13. UPDATE staging: original → Anulada/Anulado; insertar nueva en staging con Validado/Vigente.
14. Responder { id_op_anterior, id_op_nueva }.
```

---

## 7. Fases de ejecución

### Fase 0 — Prerrequisito de seguridad
Antes de tocar schema: ver §12 y confirmar con Santi que el bloqueo de la cuenta atacante está completo y el vector de entrada cerrado.

### Fase 1 — Schema + datos iniciales
1. Backup `os_gestion` (VPS) y `u768061575_os_comunidad` (Hostinger).
2. Crear `g_categorias_produccion` (+ seeds), `g_op_lineas`, `g_op_tiempos`, `g_op_detalle`.
3. ALTER `g_tareas`: +`categoria_produccion_id`, −4 `tiempo_*`, −`id_op_original`.
4. DROP `g_tarea_produccion_lineas`.
5. UPDATE `sys_usuarios.num_id` con las 5 cédulas confirmadas.

### Fase 2 — Backend: endpoints OP
1. `GET /api/gestion/op` y `/api/gestion/op/:id` (con lineas, tiempos, tareas, detalle).
2. `PUT/POST/DELETE` líneas + detalle.
3. `POST /procesar` y `/validar` con la lógica de §6.2 y §6.3.
4. `GET /api/gestion/categorias-produccion`.
5. Ajustar `GET /api/gestion/tareas`: incluir `categoria_produccion_*`, soportar `op_id`.
6. Borrar endpoints viejos (§4.4).

### Fase 3 — Frontend: reducir `DetallesProduccion.vue`
Solo-lectura + link "Editar en la OP".

### Fase 4 — Frontend: `OpPanel.vue`
7 bloques, reutilizando patrones de `ProyectoPanel`.

### Fase 5 — Frontend: `OpTablePage.vue` + ruta
OsDataTable con las 6 columnas, click → OpPanel.

### Fase 6 — Frontend: Sidebar
Sub-sección OP en Mis Tareas + Equipo + link en Tablas.

### Fase 7 — Frontend: TareasPage + Form/Panel
Filtro `op_id` + selector `categoria_produccion_id`.

### Fase 8 — Testing end-to-end
- Crear tarea con OP y categoría Templado → cronómetro → ficha OP muestra suma correcta (modo vivo).
- Editar real material → autosave.
- "+ agregar material no previsto" (solo Generada).
- Procesar OP desde ficha (nivel ≥ 3) → estado Procesada en Effi + chip.
- Validar OP (nivel 5) → nueva OP creada + todas las tareas migran de id_op + op_anterior guardado + `g_op_tiempos` con snapshot + observación con LOTE+fechas+tiempos.
- Abrir OP validada: tiempos vienen de snapshot (fuente='snapshot').
- Sidebar: click OP → filtra tareas. Mobile + desktop + dark + claro.

### Fase 9 — Limpieza
- Actualizar `.agent/contextos/sistema_gestion.md`, `CATALOGO_APIS.md`.
- Bump versión MainLayout a v2.9.x.
- Commit + push.

---

## 8. Archivos a crear/modificar

### Nuevos
- `sistema_gestion/app/src/components/OpPanel.vue`
- `sistema_gestion/app/src/pages/OpTablePage.vue`
- `sistema_gestion/app/src/components/CategoriaProduccionSelector.vue`
- `sistema_gestion/api/migrations/2026-04-24_modulo_op.sql`

### Modificados
- `sistema_gestion/app/src/components/DetallesProduccion.vue` — reducir
- `sistema_gestion/app/src/components/TareaForm.vue`
- `sistema_gestion/app/src/components/TareaPanel.vue`
- `sistema_gestion/app/src/pages/TareasPage.vue` — filtro `op_id`
- `sistema_gestion/app/src/layouts/MainLayout.vue`
- `sistema_gestion/app/src/router/routes.js`
- `sistema_gestion/api/server.js`

### Eliminados
- Tabla `g_tarea_produccion_lineas`
- Columnas `tiempo_*` y `id_op_original` de `g_tareas`
- Endpoints viejos en [4.4]

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| UPDATE cédulas en Hostinger toca dato sensible | Backup previo + UPDATE puntual solo a `num_id` de 5 usuarios + confirmación |
| Tareas con OP anulada en Effi | Chip gris "Anulada" en UI, no rompe carga |
| PWA cacheada llama endpoints viejos | Bump versión MainLayout fuerza refresh; endpoints viejos retornan 410 Gone |
| `categoria_produccion_id NULL` en tareas viejas con OP | Backfill opcional; obligatorio solo en UI al guardar |
| Servidor de respaldo sin Playwright | Protección 503 + retry existente (v2.8.5) se mantiene |
| Validar falla a mitad de los 3 scripts Playwright | Logs detallados en cada paso; rollback manual si la OP queda en estado inconsistente |

---

## 10. Validaciones antes de merge

- [ ] Backups de `os_gestion` y `u768061575_os_comunidad` ejecutados.
- [ ] UPDATE cédulas confirmado por Santi antes de ejecutar.
- [ ] Migración aplicada en VPS con conteos verificados.
- [ ] Fase 8 E2E pasa.
- [ ] Chrome DevTools MCP screenshots: OpPanel + OpTablePage dark/light/mobile.
- [ ] Bump versión MainLayout.
- [ ] `.agent/contextos/sistema_gestion.md` actualizado.

---

## 11. Subagentes

- Fase 1 (SQL): `feature-dev:code-architect` genera migration idempotente.
- Fase 2 (backend): subagente implementa endpoints + tests.
- Fase 4 (OpPanel): subagente genera componente Vue.
- Fase 5 (OpTablePage): subagente genera página.

---

## 12. Contexto de seguridad (2026-04-24) — NO BORRAR

### Intrusión `maskedaltfivem@gmail.com` — RESUELTA

**Identificado durante el diseño de este módulo**, al revisar usuarios de `sys_usuarios` para el mapeo de cédulas (Q3).

- Cuenta con Nivel 9 + PRODUCCION_SUPERUSUARIO + "DIRECCION GENERAL" + teléfono UK +44 7877 178402.
- Creada el 2026-04-01 16:46:30 (autoasignada 6 min después).
- Solo 3 rastros en BD (ya eliminados):
  1. `u768061575_os_comunidad.sys_usuarios` (Hostinger) — ELIMINADO.
  2. `u768061575_os_comunidad.sys_usuarios_empresas` — ELIMINADO.
  3. VPS `os_gestion.g_usuarios_config` — ELIMINADO.
- Backup previo: `/home/osserver/Proyectos_Antigravity/backups/intrusion_2026-04-01/backup_maskedalt_20260424_161055.json`.

**Alcance verificado**:
- NO tuvo shell en servidor local (SSH log 2026-04-01: solo IPs 100.89.52.63 y 172.18.0.9 Docker, 125 eventos legítimos).
- NO tuvo shell en VPS (la fila en VPS es herencia de la migración 2026-04-20).
- SÍ entró a gestion.oscomunidad.com vía Google OAuth (servidor local en ese entonces). Solo quedó config de tema "light". NO creó tareas, jornadas, proyectos.
- Santi confirmó: entró **directamente a la BD Hostinger** vía el PHP de WordPress (ya bloqueado por Santi). La validación de endpoint HTTP no aplicaba.

### Acciones post-intrusión (pendientes de otra sesión)

1. **Investigar code.oscomunidad.com** (code-server:9400 en VPS).
   - Clave nueva puesta el 2026-04-21 13:18 CEST.
   - Bind 0.0.0.0:9400 sin HTTPS (`cert: false`).
   - Pendiente: revisar logs de acceso, IPs, posibles comprometidos.

2. **Aislar Hostinger de la validación de usuarios** — propuesta de Santi:
   - Mover la fuente de verdad de usuarios a una tabla master en el VPS.
   - Gestión (y resto de apps) validan contra VPS, NO contra Hostinger.
   - Hostinger queda solo para `u768061575_os_comunidad` del ERP Effi, totalmente aislado.
   - **Pendiente**: verificar si ya existe esa tabla master en VPS. Si existe, verificar que no contenga maskedaltfivem ni otros intrusos.

3. **Revisar WP php bloqueado**: confirmar que el endpoint vulnerable está cerrado y no haya otros vectores similares.

Esto se resuelve **antes o en paralelo** a la Fase 1 del módulo OP, porque tocar `sys_usuarios` para cédulas depende de que Hostinger siga siendo fuente de verdad o no.
