# Plan: Rediseño meta TareaItem — estilo TickTick

**Estado**: ✅ APROBADO por Santi (sesión 2026-03-17)

## Objetivo

Restructurar la zona meta (derecha) de cada fila de tarea para que sea compacta y legible:

```
[estado][cat-dot][subtareas?][título ..................][cat-txt 9px][fecha 10px][dur 11px][+]
```

**Quitar de la fila:**
- `PrioridadIcon` — ya está en el panel de detalle, en la fila recarga visualmente
- Avatar `<img>` responsable — confuso ("SP"), ya está en panel de detalle

**Mantener / agregar en meta:**
- Cronómetro activo (si tarea en progreso) — útil y visible
- Categoría nombre (abreviado, 9px, gris tenue) — `tarea.categoria_nombre` ya viene de la API
- Duración real (`tiempo_real_min`, 11px) — dato importante, un poco más visible
- Fecha límite (10px) — roja si vencida
- Botón `+` subtarea en hover (con title="Agregar subtarea")

## Contexto del problema

En la sesión anterior se implementaron cambios parciales:
- ✅ `duracionDisplay` computed agregada
- ✅ Avatar reducido a size=16
- ✅ "Mañana" → "Mañ"
- ❌ PrioridadIcon NO fue eliminada
- ❌ Avatar img NO fue eliminada
- ❌ Categoría nombre NO fue agregada

Resultado: "SP Mañ" sigue visible y feo. No coincide con el diseño TickTick pedido.

## Checklist de implementación

- [ ] 1. `TareaItem.vue` template — quitar `PrioridadIcon` y avatar img de `.tarea-meta`
- [ ] 2. `TareaItem.vue` template — agregar span `.tarea-cat-txt` con `tarea.categoria_nombre`
- [ ] 3. `TareaItem.vue` script — quitar import de `PrioridadIcon` si no se usa en otro lado
- [ ] 4. `app.scss` — agregar `.tarea-cat-txt` (9px, --text-tertiary, truncado)
- [ ] 5. Build: `cd sistema_gestion/app && npx quasar build`
- [ ] 6. Copy: `cp -r dist/spa/* ../api/public/`
- [ ] 7. Restart service + commit + push

## Layout final esperado (por fila)

```
[○] [●cat] [▶0/2] Título de la tarea............. [Ventas] [Hoy] [1h30] [+]
                                                    9px gris  10px  11px  hover
```

## Tareas para Antigravity (QA visual)
- [ ] Screenshot de fila normal, fila con subtareas, fila con cronómetro activo
- [ ] Verificar en mobile que la meta no se corta mal
- [ ] Reportar en QA_REGISTRO.md si algo no coincide con el diseño pedido
