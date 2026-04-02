# Plan: Función recargar() global — Sistema Gestión OS

**Fecha**: 2026-04-01
**Objetivo**: Que al crear/editar/eliminar items o tareas, los datos se refresquen sin navegar ni perder el estado visual.
**Commit antes del cambio**: `959273e` (feat: multi-responsable)

---

## Principio

- `recargar()` solo recarga datos, NUNCA cambia ruta/filtros/scroll/panel
- Cada componente recarga sus propios datos + llama `recargar()` del sidebar
- Si algo sale mal, revertir a commit `959273e`

---

## Archivos a modificar

### 1. MainLayout.vue
**Qué**: Exponer `recargar()` via `provide`
**Cómo**: 
- `provide('recargarSidebar', cargarProyectos)` — ya existe `cargarProyectos()`
- NO tocar: rutas, acordeones, panelVisible, drawerOpen

### 2. ItemsTablePage.vue
**Qué**: Después de crear/editar/eliminar, recargar tabla + sidebar
**Funciones afectadas**:
- `onGuardado(p)` — línea ~159: después de push/update al array, llamar `recargarSidebar()`
- `onEliminado(p)` — línea ~169: después de filter, llamar `recargarSidebar()`
**NO tocar**: filtros, panel, cargar(), cargarDatos()

### 3. TareasPage.vue
**Qué**: Después de operaciones bulk y cambios de estado, recargar sidebar
**Funciones afectadas**:
- `_postBulk(ids)` — ya recarga tareas, agregar `recargarSidebar()`
- `cambiarEstado(tarea, nuevoEstado)` — si hay, agregar recarga
- `eliminarMulti()` — ya llama `_postBulk`, no necesita cambio extra
**NO tocar**: filtros, selección, scroll, tareaSeleccionada

### 4. ProyectoPanel.vue
**Qué**: Después de crear tarea dentro del proyecto, recargar sidebar
**Funciones afectadas**:
- `crearTareaEnProyecto()` — ya recarga `cargarTareas()`, agregar `recargarSidebar()`
**NO tocar**: form, tareaAbierta, mostrarFormTarea

---

## Lo que NO se toca

- Router (routes.js, index.js)
- AuthStore
- Componentes: TareaItem, TareaPanel, ResponsablesSelector, EtiquetasSelector, ProyectoSelector, etc.
- CSS
- server.js (API)

---

## Verificación

Después de implementar, verificar:
1. Crear proyecto desde sidebar → aparece en sidebar + tabla sin recargar
2. Crear dificultad desde sidebar → aparece en sidebar + tabla
3. Editar proyecto desde tabla → sidebar refleja cambio
4. Eliminar proyecto desde tabla → desaparece de sidebar
5. Crear tarea dentro de proyecto → conteo de tareas se actualiza en sidebar
6. Multi-selección bulk → sidebar no se rompe
7. Filtros activos se mantienen después de cada operación
8. Panel abierto no se cierra al recargar
9. Ruta no cambia en ningún caso

---

## Rollback

Si hay bugs graves: `git revert HEAD` o `git reset --hard 959273e`
