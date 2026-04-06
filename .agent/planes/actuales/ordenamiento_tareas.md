# Plan: Sistema de Ordenamiento de Tareas

## Contexto
Las tareas actualmente no tienen un orden definido. Al crear una nueva tarea se pierde "por allá abajo". Necesitamos un sistema profesional de ordenamiento.

## Decisiones ya tomadas con Santi
- **Orden por defecto**: más reciente primero
- **Campo `orden`**: INT en `g_tareas`, método de gaps (como Linear, Trello, Jira)
- **Nueva tarea**: `MAX(orden) + 10000` → aparece primero
- **ORDER BY**: `orden DESC` (el número más alto = primero)
- **Cada tarea tiene un valor único** → no necesita tiebreaker
- **Drag & drop**: al arrastrar, calcular midpoint entre vecinos. Solo actualiza 1 fila
- **Rebalanceo**: cuando gap < 1, recalcular todos con step 10000 (raro que pase)
- **Criterios de ordenamiento** (pestaña "Ordenar"): Manual (default), Fecha creación, Fecha estimada, Prioridad, Categoría, Proyecto, Alfabético
- **Los criterios son vistas temporales** → NO tocan el campo `orden`
- **Drag & drop solo funciona en modo "Manual"**
- **Librería sugerida**: SortableJS (~10kb, funciona con Vue 3 y touch/mobile)

## Pasos de implementación

### Paso 1: Migración BD
- Agregar campo `orden INT NOT NULL DEFAULT 0` a `g_tareas` en Hostinger (`u768061575_os_gestion`)
- Migración inicial: asignar valores basados en `created_at` — la más reciente recibe el número más alto
- SQL: `SET @i = 0; UPDATE g_tareas SET orden = (@i := @i + 10000) ORDER BY created_at ASC;`

### Paso 2: Backend — Crear/ordenar tareas
- POST /tareas (crear): calcular `MAX(orden) + 10000` y asignarlo
- GET /tareas: cambiar ORDER BY a `t.orden DESC`
- Nuevo endpoint PUT /tareas/reordenar: recibe `{ tareaId, ordenNuevo }` — actualiza el campo
- Nuevo endpoint POST /tareas/rebalancear: recalcula todos los `orden` con gaps de 10000

### Paso 3: Backend — Ordenar por criterio
- GET /tareas acepta param `ordenar_por` = manual|fecha_creacion|fecha_estimada|prioridad|categoria|proyecto|alfabetico
- Cada criterio mapea a su ORDER BY correspondiente en SQL
- `manual` (default) usa `t.orden DESC`

### Paso 4: Frontend — Selector de orden
- En la pestaña/botón "Ordenar" que ya existe, agregar las opciones de criterio
- Guardar preferencia en localStorage
- Enviar `ordenar_por` como query param a la API

### Paso 5: Frontend — Drag & drop
- Instalar SortableJS (vue.draggable.next o directo)
- Habilitar drag solo cuando orden = "Manual"
- Al soltar: calcular midpoint, llamar PUT /tareas/reordenar
- Si gap < 1: llamar POST /tareas/rebalancear y recargar

### Paso 6: Testing
- Crear tarea → aparece primero
- Arrastrar tarea → se mueve y persiste
- Cambiar criterio → vista cambia, campo orden no se altera
- Volver a manual → orden manual preservado
- Filtro proyecto + orden → funciona combinado

## Estado
- [ ] Paso 1: Migración BD
- [ ] Paso 2: Backend crear/ordenar
- [ ] Paso 3: Backend criterios
- [ ] Paso 4: Frontend selector
- [ ] Paso 5: Frontend drag & drop
- [ ] Paso 6: Testing
