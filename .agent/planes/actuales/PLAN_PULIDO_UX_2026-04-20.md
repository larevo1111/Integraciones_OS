---
estado: propuesto — requiere decisiones antes de arrancar
creado: 2026-04-20
modulo: sistema_gestion
version_objetivo: v2.7.21 → v2.8.x
---

# Plan de Pulido UX — Sistema Gestión (abril 2026)

Basado en 5 observaciones de Santi post-v2.7.20. Divido en **bugs de datos** (hacer ya), **features nuevas** (hacer después) y **decisiones UX pendientes** (requieren validación antes de tocar código).

---

## Fase A — Bugs de datos críticos (prioridad 1)

### A1. Auto-pause de cronómetro al finalizar jornada
**Problema confirmado en código** ([server.js:2028-2066](sistema_gestion/api/server.js#L2028-L2066)): `PUT /jornadas/:id/finalizar` actualiza `hora_fin` pero no toca ninguna tarea en curso. Tareas con `crono_inicio IS NOT NULL` siguen acumulando segundos vía `TIMESTAMPDIFF` hasta que alguien las pause manualmente → **explica las 5–6h irreales en Sistemas**.

**Fix:**
- En `/finalizar`, antes de setear `hora_fin`: volcar delta a `duracion_cronometro_seg` e igualar `duracion_usuario_seg` para todas las tareas del usuario con `crono_inicio IS NOT NULL`. Reusar la lógica del endpoint `/pausar` ([server.js:1101-1120](sistema_gestion/api/server.js#L1101-L1120)) — extraer a helper `_pausarCronoUsuario(email, empresa)`.
- Pasar la tarea a estado "Pendiente" no — dejarla "En Progreso" pero sin crono activo (que mañana la retome si quiere).
- Notificar al frontend en la respuesta: `tareas_pausadas: [{id, titulo, segundos_recuperados}]` para que la página Jornadas muestre un toast "3 tareas pausadas automáticamente".

### A2. Auto-pause al iniciar otra tarea (misma persona)
**Problema confirmado** ([server.js:1078-1096](sistema_gestion/api/server.js#L1078-L1096)): `/iniciar` solo hace `COALESCE(crono_inicio, NOW())`. Si A ya corría y usuario inicia B, ambas acumulan tiempo en paralelo → doble contabilización.

**Fix:**
- En `/iniciar`: antes del UPDATE de la tarea objetivo, pausar todas las tareas del mismo usuario con `crono_inicio IS NOT NULL` (mismo helper `_pausarCronoUsuario`).
- **Decisión abierta**: el cronómetro hoy es por tarea, no por usuario-en-tarea. Si tarea A tiene 2 responsables y uno inicia B, se pausa para todos. Por ahora asumo ese comportamiento (más simple, coherente con el modelo actual). Si Santi quiere pausar solo para ese usuario, hay que agregar tabla `g_tarea_sesion_usuario` — es un cambio grande, lo dejo fuera de este plan.

### A3. Limpieza de datos históricos sucios
Antes de deploy de A1/A2, detectar tareas que ya tienen tiempo inflado:
```sql
SELECT id, titulo, responsable, duracion_cronometro_seg/3600 AS horas
FROM g_tareas
WHERE duracion_cronometro_seg > 28800  -- más de 8h sospechoso
  AND estado = 'En Progreso'
ORDER BY duracion_cronometro_seg DESC;
```
Revisar con Santi caso por caso y corregir manualmente o poner tope.

**Esfuerzo:** 2–3 horas. Test con Chrome DevTools MCP simulando finalizar jornada con crono activo.

---

## Fase B — Bulk actions en Atrasadas (prioridad 2)

### B1. Botón "Acciones" en el header de Atrasadas
En [TareasPage.vue:181-189](sistema_gestion/app/src/pages/TareasPage.vue#L181-L189), el header "Atrasadas 30" es solo informativo. Agregar menú:
- **Reagendar todas para hoy** → `fecha_limite = hoyLocal()` en bulk
- **Reagendar todas para mañana** → `fecha_limite = mañanaLocal()`
- **Posponer 1 semana** → `fecha_limite = fecha_limite + 7 días`
- **Archivar completadas/canceladas viejas (>30 días)** → setear `archivada = 1` (campo nuevo en `g_tareas`)
- **Marcar todas como pendientes** (si mezclan estados raros)

### B2. Endpoint bulk
`POST /api/gestion/tareas/bulk` con body `{ ids: [1,2,3], accion: 'reagendar'|'archivar'|..., params: {...} }`. Una sola transacción. Devuelve `{ afectadas: N }`.

### B3. UX
- Confirmar con modal ("¿Reagendar 30 tareas para mañana?").
- Toast undo al terminar (reusar [ToastUndo.vue](sistema_gestion/app/src/components/ToastUndo.vue)).
- Campo `archivada` oculta por defecto en queries pero accesible vía filtro "Ver archivadas".

**Esfuerzo:** 4–5 horas. Incluye migración de schema (campo `archivada BOOLEAN DEFAULT 0`).

---

## Fase C — Decisiones UX pendientes (requieren validación de Santi)

Estas NO las implemento hasta que decidas. Te dejo análisis + opciones.

### C1. Etiqueta vs Categoría — ¿se confunden?

**Estado actual:**
- **Categoría**: 1 por tarea. Define semántica operativa (Sistemas, Ventas, Producción, Empaque, Compras). Tiene color. Dispara comportamiento (Producción → OP Effi, Empaque → Remisión/Pedido).
- **Etiqueta**: N por tarea. Tags libres creados por usuario. Color manual. Sin comportamiento.

**Riesgo real**: usuario PyME puede no entender por qué "Sistemas" es categoría pero "urgente" es etiqueta. Especialmente si arma etiquetas como "producción chocolate" → se duplica con categoría.

**Opciones:**
- **a)** Mantener ambos, cambiar labels a "Área" (categoría) y "Tags" (etiqueta). Renombrar ayuda.
- **b)** Fusionar en un solo concepto "Tags" con flag `tag.es_area = true` para los que disparan comportamiento. Migración: convertir categorías actuales en tags con flag.
- **c)** Mantener como está, agregar tooltip explicativo en primera vez que se abre el panel.

→ **Pregunta Santi:** ¿qué opción? Si no decides aún, saltamos.

### C2. Descripción + Notas — ¿un solo campo?

**Estado actual:** dos textareas separados ([TareaPanel.vue:164-184](sistema_gestion/app/src/components/TareaPanel.vue#L164-L184)), ambos texto libre sin diferencia semántica.

**Análisis:**
- **Descripción** = "qué hay que hacer" (contexto del trabajo).
- **Notas** = "qué pasó haciéndolo" (bitácora).
- En tu flujo usas los dos. En PyMEs con poca madurez documentativa, el segundo queda vacío el 80% del tiempo.

**Opciones:**
- **a)** Fusionar en un solo campo "Descripción" con markdown. Pierde la semántica pero gana simplicidad.
- **b)** Mantener ambos, pero "Notas" por defecto colapsado (expandir solo si tiene contenido o si usuario clickea).
- **c)** Mantener como está.

→ **Pregunta Santi:** ¿preferís b) colapsar Notas cuando vacío? Es el menor costo y conserva el campo.

### C3. Proyecto — ¿filtro superior o campo por tarea?

**Estado actual:** `proyecto_id` es campo por tarea en el panel (chip en la fila de `TareaMetaChips`). En el sidebar, proyectos aparecen como links que filtran por `?proyecto_id=X`. Entonces ya ES filtro superior Y campo por tarea — duplicado conceptual.

**Observación Santi:** si un proyecto agrupa muchas tareas, quizá el campo por tarea es redundante.

**Opciones:**
- **a)** Filtrar por proyecto en el sidebar (ya existe) + al crear tarea dentro de un proyecto, preasignar el campo. No mostrar el chip `Proyecto` en el panel cuando venís desde un proyecto (solo aparece si cambiás de proyecto o desde "Todas"). Reduce ruido sin romper el modelo.
- **b)** Eliminar el chip y obligar a mover tareas entre proyectos vía "drag & drop" o menú contextual. Más limpio pero menos flexible.
- **c)** Convertir proyecto en una columna tipo Kanban — reset mayor del UX.

→ **Pregunta Santi:** ¿a)? Es la menos invasiva y resuelve el ruido.

---

## Orden propuesto de ejecución

1. **Ya** — Fase A (A3 primero para inventariar daño, luego A1+A2 deploy).
2. **Después** — Fase B (bulk actions).
3. **Cuando decidas C1/C2/C3** — Fase C item por item.

---

## Tareas para Antigravity (Google Labs)

- Revisar el flujo completo de cronómetro vs jornada en producción (antes/después del fix A) para validar que no hay otro camino oculto donde el crono siga acumulando.
- Análisis QA visual: captura del panel de tarea para validar que la distinción Etiqueta/Categoría es clara para un usuario nuevo.

## Tareas para Subagentes (Claude)

- Fase A: `feature-dev:code-architect` para diseñar el helper `_pausarCronoUsuario` y sus call sites.
- Fase B: tras decisión de Santi, un subagente implementa el endpoint bulk + el componente de menú.

---

## Decisiones pendientes (bloquean parte del plan)

- [ ] **C1** — Etiqueta vs Categoría: opción a/b/c
- [ ] **C2** — Descripción + Notas: opción a/b/c
- [ ] **C3** — Proyecto campo vs filtro: opción a/b/c
- [ ] **A2** — ¿Cronómetro por tarea (actual) o por usuario-en-tarea? Afecta esfuerzo ×3.

Sin estas 4 respuestas, puedo arrancar Fase A completa (salvo la decisión A2 — asumo "por tarea" salvo que digas otra cosa) y dejar B/C en espera.
