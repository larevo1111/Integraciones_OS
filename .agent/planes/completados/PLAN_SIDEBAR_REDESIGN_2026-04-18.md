# Plan: Reconstrucción Sidebar sobre Quasar — Sistema de Gestión OS

**Estado**: ✅ Completado — 2026-04-18 (v2.7.0)
**Fecha:** 2026-04-18
**Enfoque:** Reconstruir desde cero sobre componentes Quasar (QDrawer, QList, QItem)
**Referentes:** Linear.app (estructura + spacing) + Kommo/HubSpot (popover colapsada)
**Objetivo:** Sidebar limpia, compacta, sin duplicación, funcional en desktop (expandida/colapsada) y mobile (tab bar + drawer)

---

## Por qué reconstruir (no parchar)

1. **Duplicación 5S**: el drawer mobile es copia del sidebar desktop (~200 líneas duplicadas). Cualquier cambio va en 2 lugares.
2. **No usa Quasar**: layout completo es HTML/CSS custom cuando Quasar tiene QDrawer con mini-mode, responsive automático, overlay mobile built-in.
3. **CSS inflado**: 300+ líneas de CSS custom para lo que Quasar resuelve con clases utilitarias.
4. **Collapsed mode roto**: chevrons visibles, items no centrados, sin popover.

## Referentes visuales (capturas de Santi)

### Linear.app (desktop light + mobile)
- Sidebar ~180px, items 32px alto, gap 8px ícono-texto
- Secciones colapsables: "Workspace ▼", "Your teams ▼" con chevron inline
- Item activo = fondo azul claro sutil
- Labels de sección: uppercase, 11px, gris, letter-spacing +0.08em
- Dividers: 1px, margin 4px 12px
- Mobile: drawer lateral, mismo contenido

### Kommo (colapsada + expandida)
- **Colapsada (~48px)**: solo íconos centrados, al hover → POPOVER FLOTANTE a la derecha con subitems
- Popover tiene: título sección + buscador + lista items
- **Expandida (~180px)**: items con ícono + texto + chevron si tiene subitems
- Footer: Ajustes, Ayuda, Usuario

### HubSpot
- Mismo patrón popover colapsada que Kommo

---

## Arquitectura nueva — QLayout

```
QLayout (view="lHh LpR lFf")
├── QDrawer (side="left", v-model, :mini="miniState", :width="240", :mini-width="56",
│            bordered, :breakpoint="768")
│   ├── Header: logo + nombre + botón colapsar
│   ├── QScrollArea (flex: 1)
│   │   └── QList
│   │       ├── QExpansionItem "Mis Tareas" (con QTooltip en mini)
│   │       │   └── subitems: proyectos + etiquetas (QItem cada uno)
│   │       ├── QExpansionItem "Equipo"
│   │       │   └── subitems: proyectos + etiquetas
│   │       ├── QSeparator
│   │       ├── QItem "Jornadas" (con QTooltip en mini)
│   │       ├── QItemLabel header "TABLAS"
│   │       ├── QItem "Proyectos" / "Dificultades" / "Compromisos" / "Ideas"
│   │       └── QSeparator
│   └── Footer: tema toggle + usuario + versión
│
├── QHeader (v-if mobile)
│   └── QToolbar: hamburger + título + búsqueda
│
├── QPageContainer
│   └── QPage
│       ├── JornadaHeader
│       └── router-view
│
└── QFooter (v-if mobile, class="bottom-tab-bar")
    └── 5 tabs: Tareas, Equipo, Jornadas, Proyectos, Más
```

**Ventajas clave:**
- UN solo QDrawer = desktop + mobile. Quasar maneja el breakpoint automáticamente.
- `mini-mode` nativo = sidebar colapsada sin CSS custom.
- QExpansionItem = acordeones nativos con animación incluida.
- QTooltip = tooltips en mini mode sin CSS ::after.
- QMenu = popover flotante al hover en mini mode.

---

## Diseño definido (sin cambios respecto al anterior)

### Desktop expandida (~240px)
```
┌──────────────────────────┐
│ 🌿 OS Gestión        ◁  │  logo + nombre + botón colapsar
├──────────────────────────┤
│ ▸ ✓ Mis Tareas          │  QExpansionItem → subitems
│ ▸ 👥 Equipo              │  QExpansionItem → subitems
│ ─────────────────────── │  QSeparator
│ ⏱ Jornadas              │  QItem
│ TABLAS                   │  QItemLabel header
│ 📁 Proyectos             │  QItem
│ ⚠ Dificultades           │
│ ✓ Compromisos            │
│ 💡 Ideas                 │
│ ─────────────────────── │
│ 🌙 Modo claro            │
│ 👤 SYSOP  v2.7.0  OS    │
└──────────────────────────┘
```

### Desktop colapsada (~56px)
```
┌──────┐
│  🌿  │  solo logo centrado
│  ▷   │  botón expandir
├──────┤
│  ✓   │ → QTooltip "Mis Tareas" + QMenu popover subitems
│  👥  │ → QTooltip "Equipo" + QMenu popover subitems
│  ──  │
│  ⏱   │ → QTooltip "Jornadas"
│  📁  │ → QTooltip "Proyectos"
│  ⚠   │ → QTooltip "Dificultades"
│  ✓   │ → QTooltip "Compromisos"
│  💡  │ → QTooltip "Ideas"
│  ──  │
│  🌙  │
│  👤  │
└──────┘
```

### Popover en colapsada (QMenu anchor="top end" al hover)
```
┌──────┐┌──────────────────────┐
│  ✓   ││ Mis Tareas           │
│      ││ ──────────────────── │
│      ││   • Proyecto Alpha   │
│      ││   • Proyecto Beta    │
│      ││ ──────────────────── │
│      ││   ⚠ Dificultad X    │
│      ││   ✓ Compromiso Y    │
│      ││ ──────────────────── │
│      ││   🏷 Etiqueta Z     │
└──────┘└──────────────────────┘
```

### Mobile (< 768px)
```
┌────────────────────────────────┐
│ ☰  Mis Tareas          🔍     │  QHeader + QToolbar
│ [Todas] [Hoy] [En curso] ...  │
│ + Agregar una tarea...         │
│ [contenido]                    │
├────────────────────────────────┤
│ 📋   👥   ⏱   📁   ≡         │  QFooter bottom tab bar
│ Tareas Equipo Jorn Proy Más   │
└────────────────────────────────┘

"Más" → abre QDrawer overlay con navegación completa
```

---

## Pasos de implementación

### Fase 1 — Estructura QLayout (eliminar duplicación)
- [ ] Reemplazar `<div class="gestion-layout">` por `<q-layout>`
- [ ] Reemplazar `<aside class="sidebar">` por `<q-drawer>` con `:mini="miniState"`
- [ ] Reemplazar topbar custom por `<q-header>` con `<q-toolbar>` (solo mobile via `v-if="$q.screen.lt.md"`)
- [ ] Reemplazar bottom-tab-bar por `<q-footer>` (solo mobile)
- [ ] Reemplazar `<div class="page-body">` por `<q-page-container>` + `<q-page>`
- [ ] **Eliminar drawer mobile duplicado** (Teleport + drawer-overlay + drawer-panel completo)
- [ ] Verificar: desktop muestra sidebar, mobile muestra header + footer + drawer overlay
- [ ] Screenshot desktop + mobile → verificar

### Fase 2 — Contenido sidebar con QList
- [ ] Reemplazar nav items custom por `<q-item>` con `<q-item-section avatar>` + `<q-item-section>`
- [ ] Reemplazar acordeones custom (Mis Tareas, Equipo) por `<q-expansion-item>`
- [ ] Reemplazar `.sidebar-separator` por `<q-separator>`
- [ ] Reemplazar `.sidebar-section-label` por `<q-item-label header>`
- [ ] Items proyecto/etiqueta dentro de expansion items
- [ ] Botones hover (check, ⋮) en QItemSection side
- [ ] Verificar: acordeones abren/cierran, items clickeables, navegación funciona

### Fase 3 — Mini mode (colapsada)
- [ ] Activar `mini-mode` en QDrawer
- [ ] Agregar `<q-tooltip>` a cada QItem principal (visible solo en mini)
- [ ] Expansion items en mini: mostrar solo ícono
- [ ] Botón toggle colapsar/expandir funcional
- [ ] Verificar: colapsada muestra solo íconos centrados, tooltips al hover

### Fase 4 — Popover flotante en colapsada
- [ ] Crear componente `SidebarPopover.vue` (o usar QMenu inline)
- [ ] Al hover en "Mis Tareas" (mini mode) → QMenu aparece a la derecha con subitems
- [ ] Al hover en "Equipo" (mini mode) → QMenu con subitems equipo
- [ ] Items del popover: proyectos con dot color + nombre + count
- [ ] Click en item del popover → navega y cierra
- [ ] Verificar: popover aparece/desaparece limpio, posición correcta

### Fase 5 — Spacing y estilos Linear
- [ ] Item height: 32px (como Linear)
- [ ] Gap ícono-texto: 8px
- [ ] Padding horizontal items: 8px (margin 0 4px)
- [ ] Section labels: 11px uppercase, weight 600, letter-spacing +0.08em
- [ ] Dividers: margin 4px 12px
- [ ] Active state: fondo `var(--bg-row-selected)` sutil
- [ ] Hover: fondo `var(--bg-row-hover)`
- [ ] Font: 13px weight 400, active 500
- [ ] Iconos: 16px, opacity modulada (0.5 → 0.85)
- [ ] Verificar: comparar visualmente con screenshot Linear

### Fase 6 — Mobile perfecto
- [ ] Bottom tab bar en QFooter: 5 tabs con iconos + labels
- [ ] "Más" abre QDrawer overlay
- [ ] QDrawer mobile = mismo contenido que desktop (ya no hay duplicación)
- [ ] Pull-to-refresh sigue funcionando
- [ ] Verificar 390x844: tab bar, drawer, navegación completa

### Fase 7 — Limpiar CSS muerto
- [ ] Eliminar de app.scss: `.sidebar` custom, `.drawer-overlay`, `.drawer-panel`, `.bottom-nav` (old), todas las reglas `.sidebar.collapsed` custom
- [ ] Eliminar de MainLayout.vue scoped: reglas que ya no aplican
- [ ] Verificar que no quedan clases CSS huérfanas
- [ ] Build: `cd sistema_gestion/app && npx quasar build`
- [ ] Version bump a v2.7.0

### Fase 8 — Verificación final
- [ ] Screenshot desktop expandida → comparar con Linear
- [ ] Screenshot desktop colapsada → verificar tooltips y popover
- [ ] Screenshot mobile 390x844 → tab bar + drawer
- [ ] Screenshot mobile drawer abierto → navegación completa
- [ ] Testear modo claro desktop + mobile
- [ ] Testear navegación: cada item lleva a la ruta correcta
- [ ] Testear filtro proyecto desde sidebar → TareasPage filtra
- [ ] Testear menú ⋮ en proyectos → editar, ver tabla, archivar, eliminar
- [ ] Testear etiquetas → editar nombre/color inline
- [ ] Testear ProyectoPanel → se abre desde sidebar y drawer

---

## Archivos a modificar

| Archivo | Acción |
|---|---|
| `sistema_gestion/app/src/layouts/MainLayout.vue` | **Reescribir template** — QLayout + QDrawer + QHeader + QFooter. Script setup se mantiene igual. |
| `sistema_gestion/app/src/css/app.scss` | **Eliminar** ~300 líneas de sidebar/drawer/bottom-nav custom. Mantener variables CSS, estilos de tareas, modales, etc. |
| `sistema_gestion/app/src/components/SidebarPopover.vue` | **Crear** — popover para mini mode (si no se resuelve con QMenu inline) |

## Archivos que NO se tocan

- Rutas (router)
- Stores (authStore, jornadaStore)
- Pages (TareasPage, EquipoPage, etc.)
- Componentes (TareaPanel, ProyectoPanel, JornadaHeader, etc.)
- server.js (API)

---

## Reglas de ejecución

1. **LEER código existente** antes de cada edición
2. **Testear con Chrome DevTools** después de CADA fase (screenshot desktop + mobile)
3. **Un commit por fase** con version bump
4. **5S**: una operación = una función. No duplicar. No sobre-ingeniería.
5. **Quasar primero**: si Quasar tiene un componente para eso, usarlo. CSS custom solo para brand colors y detalles finales.
6. **Mantener toda la funcionalidad**: acordeones, proyectos, etiquetas, menú ⋮, edición inline, completar, pull-to-refresh, búsqueda rápida.

---

## Notas técnicas

- QDrawer `mini-mode` cambia automáticamente el ancho sin CSS transition custom
- QDrawer con `:breakpoint="768"` cambia a overlay automáticamente en mobile
- `$q.screen.lt.md` para condicionar header/footer mobile
- QExpansionItem tiene prop `icon` y `label` que se muestran automáticamente en modo normal
- En mini mode, QExpansionItem colapsa a solo el ícono — necesitamos QTooltip + QMenu para el popover
- El footer del sidebar (usuario + tema) se puede hacer con QItem en la parte inferior del QList
