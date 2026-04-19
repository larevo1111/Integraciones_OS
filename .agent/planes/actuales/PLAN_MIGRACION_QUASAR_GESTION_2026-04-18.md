# Plan: Migración del Módulo de Gestión a Componentes Quasar + Rediseño UX estilo Linear

**Fecha creación:** 2026-04-18
**Última actualización:** 2026-04-19 — reordenado para priorizar rediseño UX (Fase 1) antes de componentes base
**Enfoque:** 5S japonesa — consolidar, reusar, simplificar
**Objetivo:** Eliminar HTML crudo, migrar todo a componentes Quasar y rediseñar el flujo de crear/editar tareas estilo Linear. Sin tocar funcionalidad.
**Versión destino:** v2.8.0 (fin del proceso)

---

## Principios rectores (no negociables)

1. **Cero cambios funcionales de negocio**. Ningún endpoint, ningún store, ninguna ruta, ningún comportamiento de datos. Solo HTML/CSS/UX.
2. **5S estricto**: si hay 3 componentes parecidos, se consolida en 1. Si hay CSS duplicado, se borra. Si hay 2 UIs para la misma acción, se unifica.
3. **Reusar antes de crear**. Antes de cada migración verificar si ya existe un QComponent o un componente base nuestro que sirva.
4. **Cada fase se prueba desktop + mobile** con Chrome DevTools MCP antes de cerrar la fase.
5. **Una fase = un commit** con version bump.
6. **No avanzar si hay regresión visual o funcional**. Si algo se rompe se revierte.
7. **Documentar en el plan cada checkbox marcado** — `[x] YYYY-MM-DD`.

---

## Principios técnicos

- **Quasar components en vez de HTML crudo**: `<q-btn>` en vez de `<button>`, `<q-input>` en vez de `<input>`, `<q-dialog>` en vez de `<div class="modal-overlay">`, `<q-menu>` en vez de `Teleport + div.dropdown`, `<q-select>` en vez de `<select>`.
- **Clases responsive Quasar** (`lt-md`, `gt-sm`, `col-xs-12 col-md-6`) en vez de `@media (max-width: 768px)`.
- **IME móvil correcto**: nunca `@keydown.enter` en inputs. Siempre `<q-form @submit.prevent>` o submit button.
- **CSS scoped mínimo**: solo colores/detalles que Quasar no cubre. El layout SIEMPRE con clases Quasar.
- **Sin ocultar funcionalidad con `hideX` props**. Los componentes base exponen slots, no flags booleanos.
- **No abstraer prematuramente**: crear `BaseX` solo cuando hay 2+ usos reales. No inventar componentes base que "algún día servirán".

---

## Inventario rápido (auditoría 2026-04-18)

- **32 archivos Vue** / **12,523 líneas** totales
- **Solo 2 archivos usan Quasar** hoy: MainLayout.vue (ya migrado) + EtiquetasSelector.vue (parcial)
- **DOS UIs para crear tarea** (QuickAdd inline + FAB → TareaForm modal) ← deuda UX crítica
- **7 selectores casi idénticos** (OpSelector, PedidoSelector, RemisionSelector, ProyectoSelector, CategoriaSelector, ResponsablesSelector, EtiquetasSelector)
- **3 paneles casi idénticos** (ProyectoPanel, TareaPanel, JornadaDetallePopup) con campos en filas verticales (no estilo Linear)
- **11 componentes con Teleport + overlay custom** = 11 mini-dialogs reinventados
- **17 archivos con media queries hardcoded**
- **7 archivos con `@keydown.enter`** (violan IME móvil)

---

## Fase 1 — Rediseño flujo crear tarea estilo Linear (EMPEZAMOS AQUÍ)

**Objetivo:** eliminar la duplicación QuickAdd + FAB/TareaForm, dejando UNA sola UI estilo Linear con chips compactos.

### Decisiones tomadas

- **Eliminar QuickAdd** de TareasPage (input siempre visible + fila de chips de categorías + selectores apilados)
- **Rediseñar TareaForm.vue** como modal estilo Linear:
  - Título grande arriba (autofocus)
  - Descripción opcional (textarea liviano)
  - Fila de **chips compactos** (MetaChip): Estado · Prioridad · Categoría · Fecha · Responsable · Proyecto · Etiquetas · Doc (OP/Pedido/Remisión según categoría)
  - Cada chip muestra valor actual si está asignado, ícono gris si vacío
  - Click en chip → `<q-menu>` con opciones → seleccionar cierra popover
- **Mismo modal en desktop y móvil**. En desktop: centered dialog. En móvil: `<q-dialog position="bottom">` bottom sheet.
- **Atajo teclado "N"** abre el modal en desktop (opcional también "C" para "crear")
- **Botón "Nueva tarea"** en la topbar de TareasPage (desktop) + FAB "+" (móvil, como hoy pero abre el modal rediseñado)

### Archivos a crear

| Componente | Ubicación | Propósito |
|---|---|---|
| `MetaChip.vue` | `components/base/MetaChip.vue` | Chip compacto con ícono + valor + `<q-menu>` slot para opciones |

### Archivos a editar

| Archivo | Cambio |
|---|---|
| `TareaForm.vue` | Rediseño completo → `<q-dialog>` + MetaChips |
| `TareasPage.vue` | Quitar bloque QuickAdd (~200 líneas de template + CSS), agregar botón "Nueva tarea" en topbar (desktop), mantener FAB (móvil) pero redirigido al nuevo modal |
| `ProyectoPanel.vue` | (se mantiene igual en esta fase — se rediseña en Fase 6) |

### Checklist

**MetaChip.vue:**
- [ ] Wrapper sobre `<q-chip clickable dense>` + `<q-menu>` interno
- [ ] Props: `icon`, `label`, `value`, `color`, `placeholder`
- [ ] Slots: `menu` (contenido del popover), `display` (custom del chip si hace falta)
- [ ] Emits: `update:modelValue`
- [ ] Si `value` → muestra label con valor. Si no → muestra placeholder gris con solo el ícono
- [ ] Al abrir menu: auto-focus del input/lista dentro

**TareaForm rediseñado:**
- [ ] Reemplazar `<div class="form-overlay is-sheet">` por `<q-dialog v-model position="standard">` desktop / `position="bottom"` móvil (reactivo a `$q.screen.lt.md`)
- [ ] Título → `<q-input borderless autofocus>` font-size grande
- [ ] Descripción → `<q-input type="textarea" borderless>` opcional
- [ ] Fila de MetaChips (Estado, Prioridad, Categoría, Fecha, Responsable, Proyecto, Etiquetas)
- [ ] Chip de Doc (OP/Pedido/Remisión) **dinámico según categoría**:
  - Si cat=Producción → chip "OP" con `OpSelector` inline en popover
  - Si cat=Empaque → chips "Remisión" y "Pedido" con selectores inline
  - Si otra cat → no aparece
- [ ] Botones Enter (guardar) + Esc (cerrar). Opcional botones Guardar/Cancelar visibles
- [ ] **Sin `@keydown.enter`** — usar `<q-form @submit.prevent>`
- [ ] Validación: título vacío bloquea Enter (`:rules`)

**TareasPage.vue:**
- [ ] Eliminar todo el bloque `<div class="quickadd-wrap">` + state (`qaActivo`, `qaTitulo`, `qaCatId`, etc.)
- [ ] Eliminar CSS scoped de `.quickadd-*`
- [ ] Agregar `<q-btn color="primary" icon="add" label="Nueva tarea">` en topbar (desktop) que abre TareaForm
- [ ] Mantener FAB móvil pero ahora abre TareaForm rediseñado
- [ ] Agregar listener atajo **N** en desktop (key="n" + no input activo) → abre TareaForm

### Verificación Fase 1

**Desktop (1440×900):**
- [ ] Click botón "Nueva tarea" → modal centrado aparece
- [ ] Focus automático en título
- [ ] Tipear título + Enter → tarea creada con categoría por defecto o IA sugerida
- [ ] Click chip "Prioridad" → popover con opciones → seleccionar Alta → chip muestra "🟠 Alta"
- [ ] Click chip "Fecha" → `<q-date>` en popover → seleccionar → chip muestra "📅 20 Abr"
- [ ] Click chip "Categoría" Producción → aparece chip "OP" nuevo en la fila
- [ ] Tecla "N" (fuera de inputs) → abre modal
- [ ] ESC cierra sin guardar
- [ ] Click fuera cierra

**Móvil (390×844):**
- [ ] FAB "+" abre bottom sheet con el modal
- [ ] Bottom sheet se desliza desde abajo
- [ ] Chips se ven compactos, scroll horizontal si no caben
- [ ] Teclado IME al escribir título no corta palabras al submit
- [ ] Selector responsable en mobile: `<q-menu>` a pantalla completa
- [ ] Swipe down o botón "×" cierra

**Regresión:**
- [ ] Todas las tareas creadas antes siguen apareciendo igual en la lista
- [ ] TareaItem de la lista NO cambia visualmente
- [ ] Panel lateral (TareaPanel) al clickear tarea NO cambia (se hace en Fase 6)

### Commit Fase 1

- Mensaje: `feat(gestion): rediseño flujo crear tarea estilo Linear - MetaChip + TareaForm unificado (elimina QuickAdd)`
- Version bump: **v2.7.5**
- Ahorro estimado: **~600 líneas** (QuickAdd ~200 + TareaForm refactor ~150 + CSS ~250)

---

## Fase 2 — Componentes base compartidos restantes

**Objetivo:** extraer los componentes base `BaseSelector` y `BasePanel` una vez que Fase 1 validó el patrón con MetaChip y el q-dialog inline.

**Nota:** **NO se crea `BaseDialog`** — después de Fase 1 vemos si hace falta. Si `<q-dialog>` directo sigue siendo suficiente, lo dejamos sin abstracción (principio: no abstraer antes de tener 2+ usos reales).

### Archivos a crear

| Componente | Ubicación | Reemplaza |
|---|---|---|
| `BaseSelector.vue` | `components/base/BaseSelector.vue` | Lógica común de los 7 selectores |
| `BasePanel.vue` | `components/base/BasePanel.vue` | Paneles laterales (ProyectoPanel, TareaPanel, JornadaDetallePopup) |

### Checklist

- [ ] Crear `BaseSelector.vue`
  - Wrapper sobre `<q-select>` + `<q-menu>`
  - Props: `modelValue`, `options`, `label`, `multiple`, `searchable`, `clearable`, `dense`, `loading`
  - Slots: `option`, `selected`, `empty`, `header`, `footer`
  - Emits: `update:modelValue`, `search`, `create`
  - IME-safe: `<q-form @submit.prevent>` internamente
- [ ] Crear `BasePanel.vue`
  - Wrapper sobre `<q-drawer side="right" overlay :width="440">` desktop / `<q-dialog position="bottom">` mobile
  - Props: `modelValue`, `title`, `canDelete`, `loading`
  - Slots: `header`, `body`, `footer`, `chips` (fila de MetaChips arriba estilo Linear)
  - Emits: `update:modelValue`, `save`, `delete`

### Verificación Fase 2

- [ ] Crear página test temporal `PruebaBase.vue` que instancia BaseSelector y BasePanel
- [ ] Chrome DevTools desktop + móvil: abrir/cerrar, test focus trap, test ESC
- [ ] Borrar `PruebaBase.vue` antes del commit

### Commit Fase 2

- Mensaje: `feat(gestion): componentes base BaseSelector + BasePanel`
- Version bump: **v2.7.6**

---

## Fase 3 — Consolidar 3 selectores de documentos en `DocumentoSelector`

**Objetivo:** fusionar OpSelector, PedidoSelector y RemisionSelector en un solo componente con prop `tipo`.

### Análisis previo

Los 3 son 90% idénticos. Solo difieren en endpoint API y campos del resultado.

### Archivos

| Acción | Archivo |
|---|---|
| Crear | `components/DocumentoSelector.vue` |
| Borrar | `components/OpSelector.vue` |
| Borrar | `components/PedidoSelector.vue` |
| Borrar | `components/RemisionSelector.vue` |
| Editar | `TareaForm.vue` — reemplazar imports (el chip "Doc" usará DocumentoSelector adentro del popover) |
| Editar | `TareaPanel.vue` — reemplazar imports |

### Checklist

- [ ] Crear `DocumentoSelector.vue` usando `BaseSelector` (Fase 2)
  - Prop `tipo`: `'op' | 'pedido' | 'remision'`
  - Endpoint dinámico según tipo
  - PDF viewer inline + link a Effi
- [ ] Reemplazar usos en `TareaForm.vue` (dentro del chip Doc)
- [ ] Reemplazar usos en `TareaPanel.vue`
- [ ] Borrar los 3 archivos viejos

### Verificación Fase 3

- [ ] Desktop: crear tarea con OP, Pedido, Remisión (cada flujo)
- [ ] Móvil: selector en modal funciona
- [ ] IME móvil correcto

### Commit Fase 3

- Mensaje: `refactor(gestion): consolidar Op/Pedido/Remision en DocumentoSelector`
- Version bump: **v2.7.7**
- Ahorro: ~700 líneas

---

## Fase 4 — Selectores de entidades a `q-select`

**Objetivo:** migrar CategoriaSelector, ProyectoSelector, ResponsablesSelector, EtiquetasSelector.

### Archivos

| Archivo | Cambio |
|---|---|
| `CategoriaSelector.vue` | Reescribir con `<q-select>` (single-select simple) |
| `ProyectoSelector.vue` | Reescribir con `<q-select>` con grupos por tipo + slot "Nuevo proyecto" |
| `ResponsablesSelector.vue` | Reescribir con `<q-select multiple use-chips>` |
| `EtiquetasSelector.vue` | Reescribir con `<q-select multiple use-chips>` + crear etiqueta inline |

### Checklist (por componente — ver plan original para detalles completos)

- [ ] CategoriaSelector → `<q-select>` con color dot + nombre
- [ ] ProyectoSelector → `<q-select>` con grupos + botón "+ Nuevo proyecto"
- [ ] ResponsablesSelector → `<q-select multiple use-chips>` con avatar
- [ ] EtiquetasSelector → `<q-select multiple>` + color picker inline

### Verificación Fase 4

- [ ] Cada selector testado desktop + móvil
- [ ] Búsqueda funciona
- [ ] Multi-select chips se ven bien
- [ ] Keyboard nav (flechas, Enter, Esc)
- [ ] Touch móvil no cierra dropdown al seleccionar

### Commit Fase 4

- Mensaje: `refactor(gestion): selectores entidades a q-select`
- Version bump: **v2.7.8**

---

## Fase 5 — Modales simples (PausaDialog, FiltroPersonalizado)

**Objetivo:** migrar los 2 modales más aislados a `<q-dialog>`.

### Archivos

- `PausaDialog.vue` — overlay custom → `<q-dialog>`, inputs time → `<q-time>`, tipos → `<q-option-group>`, botones → `<q-btn>`
- `FiltroPersonalizado.vue` — overlay custom → `<q-dialog>`, multi-selects → `<q-select multiple>`, date range → `<q-input type="date">` × 2, checkboxes → `<q-checkbox>`

### Verificación Fase 5

- [ ] PausaDialog: iniciar pausa, seleccionar tipos, observación, guardar. Desktop + móvil
- [ ] FiltroPersonalizado: combinar filtros, limpiar, aplicar. Desktop + móvil
- [ ] ESC cierra sin guardar, click-outside cierra

### Commit Fase 5

- Mensaje: `refactor(gestion): PausaDialog + FiltroPersonalizado a q-dialog`
- Version bump: **v2.7.9**

---

## Fase 6 — Paneles laterales estilo Linear (chips arriba)

**Objetivo:** migrar los 3 paneles a `BasePanel` + aplicar patrón Linear (MetaChips arriba, no filas de labels).

### Archivos

- `ProyectoPanel.vue` (835 líneas)
- `TareaPanel.vue` (791 líneas)
- `JornadaDetallePopup.vue` (784 líneas)

### Checklist por panel

**TareaPanel (el más importante):**
- [ ] Envolver en `BasePanel`
- [ ] Título editable → `<q-input borderless>` (autosize)
- [ ] **Fila de MetaChips** (reusa los de Fase 1): Estado, Prioridad, Categoría, Fecha, Responsable, Proyecto, Etiquetas, Doc
- [ ] Descripción → `<q-input type="textarea">` o TipTap (si se queda)
- [ ] Cronómetro → lógica igual, botones → `<q-btn>`
- [ ] Subtareas → `<q-list>` + `<q-item>`
- [ ] Modal "Completar tarea" → `<q-dialog>`

**ProyectoPanel:**
- [ ] Envolver en `BasePanel`
- [ ] Fila de MetaChips: Estado, Prioridad, Categoría, Fecha objetivo, Responsable, Color
- [ ] TipTap editor → mantener
- [ ] Botones → `<q-btn>`

**JornadaDetallePopup:**
- [ ] Envolver en `BasePanel`
- [ ] Timeline de pausas → `<q-timeline>`
- [ ] Inputs hora → `<q-input type="time">`
- [ ] Sección admin → `<q-expansion-item>`

### Verificación Fase 6

- [ ] Cada panel desktop + móvil (bottom sheet)
- [ ] Edición inline vía MetaChip funciona (click chip → popover → cambiar → cierra → actualizado)
- [ ] Apertura desde sidebar, desde lista, desde tabla
- [ ] Confirmación eliminar (`<q-dialog>`)
- [ ] Paneles anidados (ProyectoPanel abre TareaPanel): z-index limpio
- [ ] Drag handle móvil funciona

### Commit Fase 6

- Mensaje: `refactor(gestion): paneles laterales estilo Linear con MetaChips`
- Version bump: **v2.7.10**
- Ahorro: ~500 líneas CSS + UX coherente con Fase 1

---

## Fase 7 — MultiActionBar a `<q-btn-group>` + `<q-menu>`

**Objetivo:** migrar la barra de acciones múltiples.

### Archivo

- `components/MultiActionBar.vue`

### Checklist

- [ ] Wrapper → `<q-toolbar>` o `row q-gutter-sm`
- [ ] Cada botón-menú → `<q-btn icon><q-menu>...</q-menu></q-btn>`
- [ ] Menús reusan los componentes de Fases 3-4 (CategoriaSelector, ProyectoSelector, etc.)
- [ ] Botón Eliminar → `<q-btn color="negative">` + confirm dialog

### Verificación Fase 7

- [ ] Selección múltiple (Ctrl+click desktop, long press móvil)
- [ ] Cada acción masiva
- [ ] Eliminar masivo con confirm
- [ ] Desktop + móvil

### Commit Fase 7

- Mensaje: `refactor(gestion): MultiActionBar a q-btn-group + q-menu`
- Version bump: **v2.7.11**

---

## Fase 8 — Páginas pequeñas (Login/Equipo/ItemsTable/Calendario)

**Objetivo:** migrar 4 páginas pequeñas a Quasar.

### Archivos

- `LoginPage.vue` (126 líneas) — `<q-page>` + `<q-card>`
- `EquipoPage.vue` (343 líneas) — `<q-page>` + date range + tabla
- `ItemsTablePage.vue` (242 líneas) — toolbar Quasar + tabla
- `CalendarioPage.vue` (371 líneas) — `<q-date>` nativo con slots `day`

### Verificación Fase 8

- [ ] Login: OAuth Google + selector empresa
- [ ] Equipo: filtro fechas, click fila → detalle
- [ ] ItemsTable: cada tipo (proyecto/dificultad/compromiso/idea)
- [ ] Calendario: navegación, click día, crear tarea desde día

### Commit Fase 8

- Mensaje: `refactor(gestion): páginas pequeñas a Quasar`
- Version bump: **v2.7.12**

---

## Fase 9 — TareasPage (la más grande, 2016 líneas)

**Objetivo:** migrar la página principal en sub-fases.

**NOTA:** El QuickAdd YA se eliminó en Fase 1. Esta fase se enfoca en toolbar, grupos, lista y TareaItem.

### Sub-fases

**9.1 Toolbar y filtros (~200 líneas):**
- [ ] Chips filtros → `<q-chip clickable selected>`
- [ ] Dropdown Ordenar → `<q-btn-dropdown>`
- [ ] Botón agrupar → `<q-btn-dropdown>`
- [ ] Barra secundaria → `<q-toolbar>`

**9.2 Grupos y lista (~400 líneas):**
- [ ] Group headers → layout Quasar (`row items-center`)
- [ ] Accordion atrasadas → `<q-expansion-item>`
- [ ] Accordion completadas → `<q-expansion-item>`

**9.3 TareaItem (componente separado, ~400 líneas):**
- [ ] Fila → `<q-item>` + `<q-item-section>`
- [ ] Checkbox custom (mantener círculo custom, es bueno)
- [ ] Drag handle → `<q-icon name="drag_indicator">`
- [ ] Meta chips ya son buenos — solo verificar CSS coherente con Fase 1
- [ ] Cronómetro inline → `<q-btn>` para controles

**9.4 Modales restantes (~300 líneas):**
- [ ] Modal completar tiempo → `<q-dialog>`
- [ ] Dropdown Ordenar teleport → `<q-menu>`
- [ ] Bottom sheets → `<q-dialog position="bottom">`

### Verificación Fase 9 (por sub-fase)

Después de cada sub-fase:
- [ ] Chrome DevTools desktop: filtros, agrupación, ordenamiento
- [ ] Chrome DevTools móvil: gestos, bottom sheets
- [ ] Crear tarea (ya usa modal nuevo de Fase 1)
- [ ] Multi-selección → MultiActionBar
- [ ] Cronómetro auto-start al marcar check
- [ ] Subtareas funcionan
- [ ] Drag & drop NO se rompe

### Commits Fase 9

- Uno por sub-fase
- Versions: **v2.7.13 → v2.7.16**

---

## Fase 10 — OsDataTable (tabla oficial, 1086 líneas)

**Objetivo:** evaluar y decidir — ¿migrar a `<q-table>` o mantener custom?

### Decisión

- **Opción A**: migrar a `<q-table>` con slots. Ganamos virtualización, sorting nativo, selection, pagination. Perdemos filtros custom popup, subtotales, exportación — hay que re-implementar.
- **Opción B**: mantener custom pero migrar internamente HTML crudo a componentes Quasar (botones → `<q-btn>`, popups → `<q-menu>`, inputs filtro → `<q-input>`).

**Recomendación**: Opción B — menos riesgo, mismo resultado visual. Decidir con Santi al llegar a esta fase.

### Checklist (Opción B)

- [ ] Toolbar: `<button class="toolbar-btn">` → `<q-btn>`
- [ ] Popups columna: Teleport custom → `<q-menu>`
- [ ] Inputs filtro → `<q-input>`
- [ ] Selección → `<q-checkbox>`
- [ ] Skeleton loading → `<q-skeleton>`
- [ ] Mantener `<table>` con CSS original

### Verificación Fase 10

- [ ] Tabla Jornadas (EquipoPage): filtros, subtotales, exportación
- [ ] Tabla Items (ItemsTablePage): cada tipo
- [ ] Todas las features built-in funcionan

### Commit Fase 10

- Mensaje: `refactor(gestion): OsDataTable controles internos a Quasar`
- Version bump: **v2.7.17**

---

## Fase 11 — Componentes pequeños + limpieza final

**Objetivo:** pulir restantes y cerrar migración.

### Archivos

- `JornadaHeader.vue` (422 líneas)
- `JornadaPopover.vue` (130 líneas)
- `ToastUndo.vue` (151 líneas) — evaluar usar `Notify.create({ actions })`
- `EstadoBadge.vue`, `PrioridadIcon.vue`, `Cronometro.vue`, `CronoDisplay.vue` — triviales

### Checklist

- [ ] JornadaHeader: botones → `<q-btn>`, popover → `<q-menu>`
- [ ] JornadaPopover: confirmaciones → `<q-dialog>`
- [ ] ToastUndo → `Notify.create({ actions: [...] })`
- [ ] Badges/Icons: mínimos si son decorativos

### Limpieza final

- [ ] Auditar `app.scss`: borrar CSS sin uso
- [ ] Auditar cada `<style scoped>`: reducir
- [ ] Buscar `@keydown.enter` en todo el repo — cero ocurrencias
- [ ] Buscar `@media (max-width` — reducir a <5 casos justificados
- [ ] Buscar `<button class=` — cero
- [ ] Buscar `<input type="text"` (sin Quasar) — cero
- [ ] Actualizar CLAUDE.md: confirmar que gestión cumple regla Quasar
- [ ] Actualizar `.agent/contextos/sistema_gestion.md`

### Commit Fase 11

- Mensaje: `refactor(gestion): limpieza final migración Quasar + UX Linear v2.8.0`
- Version bump: **v2.8.0** (mayor)

---

## Resumen de fases (reordenado 2026-04-19)

| Fase | Enfoque | Versión | Líneas netas (estim) |
|---|---|---|---|
| **1** | **Rediseño flujo crear tarea (MetaChip + TareaForm unificado + elimina QuickAdd)** | **v2.7.5** | **-600** |
| 2 | BaseSelector + BasePanel | v2.7.6 | +0 (inversión) |
| 3 | DocumentoSelector consolidado | v2.7.7 | -700 |
| 4 | Selectores entidades a q-select | v2.7.8 | -300 |
| 5 | PausaDialog + FiltroPersonalizado | v2.7.9 | -150 |
| 6 | Paneles laterales estilo Linear | v2.7.10 | -500 |
| 7 | MultiActionBar | v2.7.11 | -100 |
| 8 | Páginas pequeñas | v2.7.12 | -200 |
| 9 | TareasPage (4 sub-fases) | v2.7.13 → v2.7.16 | -300 |
| 10 | OsDataTable (Opción B) | v2.7.17 | -100 |
| 11 | Limpieza final | v2.8.0 | -200 |
| **Total** | ~30 archivos | | **~-3,150 líneas** |

**Reducción estimada**: 25% del código del módulo + eliminación de duplicación UX (QuickAdd vs FAB/TareaForm) + eliminación de 3 componentes selector duplicados.

---

## Protocolo de verificación por fase

Cada fase termina con este checklist obligatorio:

### Desktop (Chrome DevTools MCP, 1440×900)
- [ ] Build sin errores (`npm run deploy` desde `app/`)
- [ ] Navegar a todas las rutas — ninguna rompe
- [ ] Probar flujos principales
- [ ] Consola sin errores
- [ ] Modo oscuro + modo claro
- [ ] Screenshot de verificación

### Mobile (Chrome DevTools MCP, 390×844)
- [ ] Bottom tab bar visible
- [ ] Drawer abre/cierra
- [ ] Modales como bottom sheet
- [ ] Teclado IME no corta palabras
- [ ] Touch gestures funcionan
- [ ] Screenshot de verificación

### Regresión
- [ ] Funcionalidad previa intacta
- [ ] Performance no degradado
- [ ] Dark/light mode sin hardcoded colors nuevos

### Git
- [ ] Commit con version bump
- [ ] Push a main
- [ ] Marcar fase `[x] YYYY-MM-DD`
- [ ] Actualizar `.agent/contextos/sistema_gestion.md` si aplica

---

## Reglas absolutas durante la migración

1. **No tocar** `server.js`, `db.js`, stores (`authStore`, `jornadaStore`), routes (`routes.js`), services (`api.js`, `fecha.js`).
2. **No tocar** scripts Python.
3. **No modificar** schema de BD.
4. **No cambiar** URLs de API.
5. **Sí permitido** ajustar imports en componentes afectados.
6. **Sí permitido** crear composables nuevos en `src/composables/` si simplifica.
7. **No abstraer prematuramente** — crear Base* solo con 2+ usos reales.

---

## Protocolo de avance entre fases

- **Santi decide cuándo avanzar**. Sin cadencia ni timeline.
- Claude Code ejecuta UNA fase completa y la testea (desktop + móvil).
- Al terminar, reporta resultado y espera aprobación.
- Santi revisa en la app real. Aprobado → siguiente fase. Falla → corregir antes de avanzar.
- Cada fase cerrada: `[x] YYYY-MM-DD`.
- No empezar fase N+1 sin cerrar N.

---

## Riesgos identificados

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Usuarios acostumbrados a QuickAdd extrañan la UI inline | Media | El modal nuevo es igual de rápido (atajo N + focus auto + Enter crea) |
| Regresión visual sutil | Alta | Screenshots antes/después en cada fase |
| MetaChip popover se sale del viewport móvil | Media | `<q-menu>` maneja auto-placement, probar en mobile |
| Estado modales anidados rompe | Media | QDialog maneja z-index, probar panel→subpanel |
| QSelect lento con muchas opciones | Baja | `virtual-scroll` prop |
| Break de v-model en selectores consolidados | Media | Tests exhaustivos Fase 3-4 |

---

## Criterio de éxito final (v2.8.0)

- [ ] **Una sola UI para crear tarea** (Fase 1 ya lo logra)
- [ ] Cero `<button>` en código fuente (excepto `type="button"` dentro de QForm)
- [ ] Cero `<input>` nativo (excepto casos justificados)
- [ ] Cero `<div class="modal-overlay">` custom
- [ ] Cero `Teleport + div.dropdown` custom
- [ ] Cero `@keydown.enter` en inputs
- [ ] Máximo 5 media queries custom (casos específicos justificados)
- [ ] CSS scoped en componentes: ≤30 líneas promedio
- [ ] `app.scss` reducido en ≥300 líneas adicionales
- [ ] Pruebas manuales pasan desktop + móvil
- [ ] Módulo cumple 100% regla CLAUDE.md "OBLIGATORIO usar componentes Quasar"

---

## Documentación relacionada

- `.claude/skills/quasar-layout/SKILL.md` — reglas de uso de Quasar
- `CLAUDE.md` §UI/Layout — regla absoluta
- `sistema_gestion/MANUAL_DISENO_HIBRIDO.md` — variables CSS y patrones visuales
- `.agent/planes/completados/PLAN_SIDEBAR_REDESIGN_2026-04-18.md` — ejemplo migración (MainLayout)
- Referencia visual Linear.app (screenshots compartidos por Santi 2026-04-19)
