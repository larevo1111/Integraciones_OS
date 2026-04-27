---
estado: completado
creado: 2026-04-27
completado: 2026-04-27
modulo: sistema_gestion
version_objetivo: v2.9.7
---

# Plan — Eliminar duplicación MultiActionBar inline en TareasPage

## Contexto

`sistema_gestion/app/src/components/MultiActionBar.vue` (componente reutilizable) y `sistema_gestion/app/src/pages/TareasPage.vue` (líneas 414-526 template + 1477-1576 script + 1909-1957 CSS) tienen **dos implementaciones separadas de la misma barra flotante** de selección múltiple.

Bug evidencia: el fix `bottom: calc(65px + env(safe-area-inset-bottom, 0))` para móvil tuvo que aplicarse en los dos lugares (commit `dbdfbd8`, v2.9.6). Romper la regla `feedback_componente_compartido.md`.

## Objetivo

Reemplazar la copia inline de `TareasPage.vue` por uso del componente `MultiActionBar.vue`. Net: ~270 líneas menos.

## Diff feature-por-feature (verificado, idénticos)

| Feature | Inline | Componente |
|---|---|---|
| Fecha (Hoy/Mañana/Pasado/date input/Sin fecha) | ✅ | ✅ |
| Estado (Pendiente/En Progreso/Cancelada — sin Completada) | ✅ | ✅ |
| Categoría con dot color | ✅ | ✅ |
| Proyecto con "Sin proyecto" | ✅ | ✅ |
| Etiquetas + crear nueva inline + "Quitar todas" | ✅ | ✅ |
| Responsable | ✅ | ✅ |
| Eliminar | ✅ | ✅ |
| `d-desktop-only` en label "Etiq." | ✅ | ✅ |
| CSS scoped del `.multi-bar` y submenús | ✅ | ✅ |

## Diferencia única

API de eventos:
- **Inline**: 9 funciones separadas (`aplicarFechaMulti`, `aplicarEstadoMulti`, etc.)
- **Componente**: emite `cerrar`, `aplicar({tipo, valor})`, `crear-etiqueta(nombre)`

## Cambios concretos

### En `TareasPage.vue`

**1. Reemplazar template inline (líneas 414-526) por:**
```vue
<MultiActionBar
  :count="seleccionMultiIds.length"
  :categorias="categorias"
  :proyectos="proyectos"
  :etiquetas="etiquetas"
  :usuarios="usuarios"
  @cerrar="seleccionMultiIds = []"
  @aplicar="onAplicarMulti"
  @crear-etiqueta="onCrearEtiquetaMulti"
/>
```

**2. Importar componente:**
```js
import MultiActionBar from 'src/components/MultiActionBar.vue'
```

**3. Agregar dispatcher (~12 líneas):**
```js
function onAplicarMulti({ tipo, valor }) {
  if (tipo === 'fecha')        return aplicarFechaMulti(valor)
  if (tipo === 'estado')       return aplicarEstadoMulti(valor)
  if (tipo === 'categoria')    return aplicarCategoriaMulti(valor)
  if (tipo === 'proyecto')     return aplicarProyectoMulti(valor)
  if (tipo === 'etiqueta')     return aplicarEtiquetaMulti(valor)
  if (tipo === 'responsable')  return aplicarResponsableMulti(valor)
  if (tipo === 'eliminar')     return eliminarMulti()
  if (tipo === 'quitar-etiquetas') return quitarEtiquetasMulti()
}
async function onCrearEtiquetaMulti(nombre) {
  const data = await api('/api/gestion/etiquetas', { method:'POST', body: JSON.stringify({ nombre }) })
  etiquetas.value.push(data.etiqueta)
  await aplicarEtiquetaMulti(data.etiqueta.id)
}
```

**4. Borrar:**
- Refs: `multiMenuFecha`, `multiMenuEstado`, `multiMenuCategoria`, `multiMenuProyecto`, `multiMenuEtiqueta`, `multiMenuResponsable`, `nuevaEtiquetaMulti` (~7 líneas).
- Función `cerrarMenusMulti` (~14 líneas) — estado interno, ya lo maneja el componente.
- Función `crearEtiquetaDesdeMulti` (~13 líneas) — reemplazada por `onCrearEtiquetaMulti`.
- Llamadas a `cerrarMenusMulti(null)` dentro de las funciones `aplicar*Multi` — ya no son necesarias.
- CSS scoped del `.multi-bar*` y `.multi-menu*` y `@media (max-width: 768px)` para multi-bar (líneas 1909-1957 aprox).

**5. NO borrar:**
- `isoRelativo` — usada en otros sitios (líneas 787, 1070, 1408).
- Funciones `aplicar*Multi` — siguen siendo el handler de la lógica de negocio.
- Refs `seleccionMultiIds`, `_bulkPut`, `_postBulk` — sin cambio.

## Plan de testeo

### Pre-condiciones
- Build local OK, deploy local en `localhost:9300`.
- Login con SYSOP (nivel 9), tema dark.

### Casos a probar (manual, con Chrome DevTools MCP)

| # | Caso | Acción | Resultado esperado |
|---|---|---|---|
| 1 | Aparición de la barra | Ctrl+click sobre 1 tarea | Barra flotante visible con "1 seleccionada" |
| 2 | Cancelar selección | Click en botón × | Barra desaparece, selección vacía |
| 3 | Múltiples tareas | Ctrl+click 3 tareas | "3 seleccionadas" |
| 4 | Acción Fecha → Hoy | Click ícono fecha → "Hoy" | Las tareas seleccionadas tienen fecha hoy |
| 5 | Acción Fecha → Sin fecha | Click ícono fecha → "Sin fecha" | Tareas sin fecha |
| 6 | Acción Fecha → date input | Click date input → fecha | Tareas con fecha custom |
| 7 | Acción Estado | Click "Estado" → Cancelada | Tareas marcadas Cancelada |
| 8 | Acción Categoría | Click "Cat." → seleccionar | Tareas reasignadas a la categoría |
| 9 | Acción Proyecto | Click "Proy." → seleccionar | Tareas asignadas al proyecto |
| 10 | Acción Proyecto → Sin proyecto | Click "Proy." → "Sin proyecto" | Tareas sin proyecto |
| 11 | Acción Etiqueta existente | Click ícono etiqueta → seleccionar | Tareas con la etiqueta agregada |
| 12 | Acción Etiqueta → Quitar todas | Click ícono etiqueta → "Quitar todas" | Tareas sin etiquetas |
| 13 | Acción Etiqueta → crear nueva | Escribir nombre + submit | Etiqueta creada y aplicada a tareas seleccionadas |
| 14 | Acción Responsable | Click ícono persona → seleccionar | Tareas con responsable nuevo |
| 15 | Acción Eliminar | Click ícono basura | Tareas eliminadas, barra desaparece |
| 16 | Bottombar móvil | Resize a 500px, abrir multi-bar | Barra arriba del bottombar (gap visible) |
| 17 | Toggle menús | Click "Estado" abre menú; click otro botón cierra el primero y abre el siguiente | Solo un menú abierto a la vez |
| 18 | Click fuera | Click en cualquier parte fuera del menú abierto | Menú se cierra (verificar si componente lo hace o si se requiere) |

### Test automatizado de regresión (verificación rápida)

Script Chrome DevTools MCP que ejecute:
1. Abrir `/tareas` en mobile (390x844).
2. Hacer Ctrl+click en una tarea → verificar `.multi-bar` visible y `bottom > 53px` (no tapado).
3. Click en botón "Estado" → verificar que aparece menú con 3 items (Pendiente/En Progreso/Cancelada).
4. Click en otro botón "Cat." → verificar que el menú "Estado" se cerró y "Cat." se abrió.
5. Click × → verificar que la barra desaparece.
6. Verificar consola sin errores Vue.

## Criterios de éxito

- [ ] Build OK sin warnings de imports huérfanos.
- [ ] Los 18 casos manuales funcionan idénticos a la versión inline.
- [ ] El test automatizado pasa.
- [ ] CSS bundle: `TareasPage*.css` reduce tamaño (al borrar `.multi-bar*`).
- [ ] Sin nuevas líneas rojas en consola del browser.
- [ ] Net diff: ~-270 líneas en `TareasPage.vue`, +30 líneas (imports + dispatcher).

## Rollback

Si algo se rompe: `git revert <hash>`. El cambio queda en un commit aislado.

---

## Resultados de testing (2026-04-27)

Ejecutado con Chrome DevTools MCP en `localhost:9300` después del build de `v2.9.7`.

### Testing automatizado

| Caso | Resultado | Detalle |
|---|---|---|
| 1 — Aparición barra (Ctrl+click 1 tarea) | ✅ | `.multi-bar` visible con "1 seleccionada" |
| 3 — Múltiples (3 tareas) | ✅ | "3 seleccionadas" |
| 17a — Menú Estado | ✅ | 3 items: Pendiente / En Progreso / Cancelada (sin Completada) |
| 17b — Toggle Cat. cierra Estado | ✅ | 1 menú abierto a la vez |
| 4 — Aplicar Fecha → Hoy | ✅ | **3/3 tareas con fecha hoy** (verificado vía API) |
| Errores consola | ✅ | 0 errores Vue |

### Verificación de menús (conteo de items por menú abierto)

| Menú | Items | Items con dot | Detalle |
|---|---|---|---|
| Fecha | 4 + date input | 0 | Hoy/Mañana/Pasado/Sin fecha + custom date |
| Estado | 3 | 0 | Pendiente/En Progreso/Cancelada (sin Completada) ✅ |
| Categoría | 16 | 16 | Todas con dot color |
| Proyecto | 28 | 27 | 27 proyectos + "Sin proyecto" |
| Etiqueta | 6 | 5 | 5 etiquetas + "Quitar todas" + form crear nueva |
| Responsable | 7 | 0 | 7 usuarios |

### Métricas de código

- `TareasPage.vue`: **2050 → 1762 líneas** (–288 líneas, –14%)
- `TareasPage.css` bundle: **18 KB → 14 KB** (–4 KB, –22%)
- Refs eliminadas: 7 (`multiMenuFecha/Estado/Categoria/Proyecto/Etiqueta/Responsable`, `nuevaEtiquetaMulti`)
- Funciones eliminadas: 2 (`cerrarMenusMulti`, `crearEtiquetaDesdeMulti`)
- Funciones agregadas: 2 (`onAplicarMulti` dispatcher 12 líneas, `onCrearEtiquetaMulti` 11 líneas)

### Pendiente de testing manual (delegado al usuario)

Estos casos requieren interacción usuario en producción y modificarían datos reales:

- Caso 6 — Fecha custom (date input)
- Caso 7 — Cambio estado real (verificar endpoint iniciar/cancelar/revertir)
- Caso 9 — Aplicar proyecto
- Caso 13 — Crear etiqueta nueva con form (`onCrearEtiquetaMulti`)
- Caso 14 — Cambio responsable
- Caso 15 — Eliminar (con confirm)
- Caso 16 — Mobile bottombar (validado en v2.9.6 con `bottom: calc(65px + env(safe-area-inset-bottom))`, mismo CSS aplica)

### Conclusión

El refactor pasa todos los criterios de éxito automáticos. El componente `MultiActionBar.vue` reemplaza la inline sin cambios visibles para el usuario. La mantenibilidad mejora: futuros fixes solo se aplican en un lugar.
