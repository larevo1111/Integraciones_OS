# Plan: Rediseño Sidebar — Sistema de Gestión OS

**Fecha:** 2026-04-18
**Referentes:** Nielsen Norman Group, Linear.app, HubSpot, Kommo
**Objetivo:** Sidebar limpia, compacta, funcional en desktop (expandida/colapsada) y mobile (tab bar + drawer)

---

## Estado actual

### Ya implementado ✅
- [x] Bottom tab bar mobile — 5 tabs (Tareas, Equipo, Jornadas, Proyectos, Más) — v2.6.0
- [x] Modo claro funcional en mobile (fix toggleTema) — v2.6.0
- [x] Logo OS reemplaza la G verde — v2.5.8
- [x] Sidebar colapsada oculta acordeones/subitems/labels de sección — v2.6.1
- [x] data-tooltip en 7 nav-items (Mis Tareas, Equipo, Jornadas, Proyectos, Dificultades, Compromisos, Ideas) — v2.6.1
- [x] CSS para tooltips ::after en sidebar colapsada — v2.6.1
- [x] Botón de colapsar visible en header del sidebar — devuelto v2.6.1
- [x] Referentes UX documentados en MANIFESTO (Nielsen, Linear, HubSpot)

### ⚠️ ANTES DE EMPEZAR: limpiar código ensuciado en v2.6.1

**Problemas en app.scss:**
- `.sidebar-collapse-btn` está DUPLICADO (líneas ~283 y ~341) — eliminar duplicado
- Líneas ~312-317: CSS de collapsed oculta `.sidebar-section-label`, `.sidebar-section-indented`, `.sidebar-acordeon-header` — esto ROMPE la sidebar expandida (label TABLAS desaparece). Estas reglas solo deben aplicar en `.sidebar.collapsed`, verificar que NO afectan la expandida.
- CSS de tooltip `::after` (línea ~321) — funcional, puede quedarse pero verificar

**Problemas en MainLayout.vue:**
- `data-tooltip` en nav-items — está bien, no rompe nada
- Botón `.sidebar-collapse-btn` — verificar que muestra `>` cuando colapsada y `<` cuando expandida

**Lo que NO tocar:**
- Bottom tab bar (`.bottom-tab-bar` + `.btab`) — funciona, dejar
- Logo OS — funciona, dejar

**Pasos:**
- [ ] Eliminar duplicado de `.sidebar-collapse-btn` en app.scss
- [ ] Verificar que las reglas `.sidebar.collapsed .sidebar-section-label { display: none }` etc. SOLO aplican dentro de `.sidebar.collapsed` (no en expandida)
- [ ] Testear sidebar expandida: label TABLAS visible, acordeones funcionan
- [ ] Testear sidebar colapsada: solo íconos, sin texto cortado
- [ ] Testear bottom tab bar en mobile
- [ ] Testear botón colapsar/expandir (< / >)

### Pendiente ❌
- [ ] **Spacing visiblemente más compacto** — items de 30px → 28px min-height, secciones con menos padding, que se NOTE la diferencia. Referente: Linear usa ~32px por item, 4-8px entre secciones.
- [ ] **Popover flotante para subitems en colapsada** — cuando el sidebar está colapsado y el usuario hace hover sobre un ícono que tiene subitems (Mis Tareas, Equipo), aparece un panel flotante a la derecha con los subitems (Proyectos, Dificultades, Compromisos, Ideas, Etiquetas). Referente: Kommo/HubSpot (imagen enviada por Santi).
- [ ] **Drawer mobile: spacing compacto** — aplicar el mismo spacing compacto al drawer que se abre desde "Más" en el tab bar.
- [ ] **Verificar sidebar colapsada visualmente** — testear con Chrome DevTools que se vea limpia, sin texto cortado, solo íconos centrados.
- [ ] **Verificar tooltips** — testear que al hover en cada ícono en colapsada aparece el tooltip con el nombre.
- [ ] **Testear todo en desktop Y mobile** — desktop expandida, desktop colapsada (con tooltip y popover), mobile tab bar, mobile drawer.

---

## Diseño definido

### Desktop — Sidebar expandida
```
┌──────────────────────────┐
│ 🌿 OS Gestión        ◁  │  ← logo + nombre + botón colapsar
├──────────────────────────┤
│ ▸ ✓ Mis Tareas          │  ← acordeón con subitems (proyectos, etiquetas)
│ ▸ 👥 Equipo              │  ← acordeón con subitems
│ ─────────────────────── │
│ ⏱ Jornadas              │
│ TABLAS                   │
│ 📁 Proyectos             │
│ ⚠ Dificultades           │
│ ✓ Compromisos            │
│ 💡 Ideas                 │
│ ─────────────────────── │
│ 🌙 Modo claro            │
│ 👤 Santiago  v2.6.1  OS  │
└──────────────────────────┘
Spacing: 28-30px por item, 4-8px entre secciones
```

### Desktop — Sidebar colapsada
```
┌────┐
│ 🌿 │  ← solo logo
│ ▷  │  ← botón expandir
├────┤
│ ✓  │ → hover: tooltip "Mis Tareas" + popover con subitems
│ 👥 │ → hover: tooltip "Equipo" + popover con subitems
│ ── │
│ ⏱  │ → hover: tooltip "Jornadas"
│ 📁 │ → hover: tooltip "Proyectos"
│ ⚠  │ → hover: tooltip "Dificultades"
│ ✓  │ → hover: tooltip "Compromisos"
│ 💡 │ → hover: tooltip "Ideas"
│ ── │
│ 🌙 │
│ 👤 │
└────┘
Ancho: 48px (var(--sidebar-collapsed))
```

### Popover flotante (en colapsada, al hover sobre Mis Tareas o Equipo)
```
┌────┐┌──────────────────────┐
│ ✓  ││ Mis Tareas           │
│    ││ ──────────────────── │
│    ││ ▸ Proyectos (3)      │
│    ││ ▸ Dificultades (7)   │
│    ││ ▸ Compromisos (2)    │
│    ││ ▸ Ideas (4)          │
│    ││ ▸ Etiquetas          │
└────┘└──────────────────────┘
```

### Mobile
```
┌────────────────────────────────┐
│ ☰  Mis Tareas          🔍     │  ← topbar
│ [Todas] [Hoy] [En curso] ...  │
│ + Agregar una tarea...         │
│ [contenido]                    │
├────────────────────────────────┤
│ 📋   👥   ⏱   📁   ≡         │  ← bottom tab bar (HECHO ✅)
│ Tareas Equipo Jorn Proy Más   │
└────────────────────────────────┘

"Más" abre drawer con: Dificultades, Compromisos, Ideas, Modo claro, Cerrar sesión
```

---

## Reglas de implementación

1. **LEER código existente** antes de cada edición
2. **Testear con Chrome DevTools** cada cambio (desktop + mobile)
3. **No quitar funcionalidad** sin permiso — si algo funciona, no tocarlo
4. **Version bump** en cada deploy
5. **Referentes:** Nielsen Norman Group → Linear → HubSpot/Kommo

---

## Notas
- El popover flotante es el cambio más complejo — necesita un componente Vue con posicionamiento absoluto
- El spacing es CSS puro — rápido
- No tocar lógica de rutas ni componentes de página
