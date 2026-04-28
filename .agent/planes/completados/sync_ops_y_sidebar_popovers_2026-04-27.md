---
estado: completado
creado: 2026-04-27
completado: 2026-04-27
modulo: sistema_gestion
version_objetivo: v2.10.0
---

# Plan — Botón "Sincronizar OPs Effi" + Sidebar nivel 3 como popover flotante

## Tarea 1 — Botón "Sincronizar Effi" en `/ops-tabla`

### Backend
Endpoint nuevo `POST /api/gestion/ops/sync` (`sistema_gestion/api/server.js`):
- Permisos: `requireAuth` (todos los usuarios autenticados)
- **Lock**: archivo `/tmp/sync_ops_effi.lock` con timestamp. Si existe y `< 10 min` → 409 "Sync en curso". Si > 10 min → asume huérfano, elimina y continúa.
- Response: **Server-Sent Events** (`Content-Type: text/event-stream`).
- Spawn: `python3 scripts/refresh_effi_produccion.py` con cwd = repo root.
- Cada línea de stdout (que el script ya emite como JSON `{paso, msg, ok}`) → `data: <json>\n\n` al cliente.
- Al cerrar el proceso: `event: end\ndata: {ok, code}\n\n` y `res.end()`. Borra el lock.
- stderr → `console.error` (debug en servidor) sin contaminar el stream.

### Frontend (`OpTablePage.vue`)
Botón pequeño en `<template #toolbar>` al lado del search input:
```vue
<q-btn flat dense no-caps size="sm" :disable="sincronizando" @click="sincronizarEffi">
  <span class="material-icons q-mr-xs" :class="{ 'spin-ico': sincronizando }" style="font-size:14px">sync</span>
  {{ sincronizando ? 'Sincronizando...' : 'Sincronizar Effi' }}
</q-btn>
```

Estado:
- `sincronizando: ref(false)`
- Click → `q-dialog` confirmación → fetch SSE → notify "ongoing" persistente con caption del paso actual → al cerrar SSE: notify positiva o negativa → `await cargar()` para refrescar tabla.

CSS: usar `.spin-ico` que ya existe en `TareaMetaChips.vue` (animation `spin 1s linear infinite`). Lo agrego en estilos scoped de OpTablePage.

### Edge cases
- Si el cliente cierra la conexión SSE: el proceso Python sigue (el server no lo mata). Próxima conexión recibe el "Sync en curso" hasta que termine o pasen 10 min.
- Si el script falla en una fase: emite `{ok: false, ...}`, el frontend muestra notify negativa con el mensaje.

---

## Tarea 2 — Sidebar nivel 3 como popover flotante (en `MainLayout.vue`)

### Estructura actual

```
Mis Tareas (q-expansion-item)              [Nivel 1]
├── Proyectos (sub-section + acordeón)     [Nivel 2]
│   ├── Proyecto A                         [Nivel 3] — sale a popover
│   └── Proyecto B                         [Nivel 3]
├── Dificultades (sub-section)             [Nivel 2]
│   └── ...
├── Compromisos
├── Ideas
├── Órdenes de producción
└── Etiquetas
```

### Estructura objetivo (en desktop ≥768px)

```
Mis Tareas (q-expansion-item)              [Nivel 1] — sin cambios
├── Proyectos (q-item con popover)         [Nivel 2] — al hover abre popover lateral
│      ↓ popover flotante
│      ┌─────────────────────────────┐
│      │ Proyectos              [+]  │
│      │ ● Proyecto A         3      │
│      │ ● Proyecto B         5      │
│      └─────────────────────────────┘
├── Dificultades (q-item con popover)
└── ...
```

### Implementación

1. **Computed `isDesktop`** en MainLayout: `computed(() => $q.screen.gt.sm)` (≥md).
2. **Para cada sub-section** (Proyectos, Dificultades, Compromisos, Ideas, OPs, Etiquetas dentro de `Mis Tareas`):
   - **Desktop**: `<q-item>` clickeable con `<q-menu>` adentro (anchor right, self left, offset 8px). Trigger: hover (`@mouseenter`/`@mouseleave` con timeout 180ms igual al mini-mode actual).
   - **Mobile**: mantener el `acordeonAbierto` con expand vertical (sin cambios).
3. **Popover (q-menu)**: muestra el mismo contenido que hoy se renderiza vertical (proyectos con dot+nombre+count, OPs, etiquetas, etc) — solo cambia el contenedor.
4. **Aplicar a las dos secciones de nivel 1** (`Mis Tareas` y `Equipo`).

### Reusar componente
Para evitar duplicar el contenido en 12 lugares (6 sub-secciones × 2 modos × 2 secciones nivel 1), extraer **el contenido de la lista nivel 3 a una función render única** o un sub-componente. Decisión: **función render `renderItemsNivel3(items, opciones)`** dentro de MainLayout para no crear archivo nuevo.

Revisión: realmente el código ya está "duplicado" para Mis Tareas vs Equipo (comparten estructura, distintos datasets). El refactor se enfoca en **cambiar el wrapper (acordeón vertical → popover lateral en desktop)** sin tocar la estructura del item interno.

### Mobile (sin cambios)
En mobile (`!isDesktop`):
- `acordeonAbierto[clave]` true → render lista vertical inline (igual que ahora).
- Popover NO se renderiza.

### Mini mode (sidebar colapsado 64px en desktop)
Ya tiene popovers funcionales (líneas 172+ y 369+ de MainLayout). Mantener tal cual.

---

## Tarea 3 — Limpieza 5S

Tras el refactor:
- Eliminar refs `acordeonAbierto[clave]` que ya no se usen en desktop (mantener para mobile).
- Verificar que no quede CSS huérfano `.sidebar-sub-section`, `.sidebar-sub-header`, `.sidebar-empty` si dejan de usarse.
- `MainLayout.vue` ahora 1900+ líneas — si crece >2200 evaluar extraer un sub-componente. Aplazar.

---

## Plan de testeo

### Pre
- Build OK, deploy local en `localhost:9300`.
- Login SYSOP, tema dark.

### Tests automatizados (Chrome DevTools MCP)

#### Sincronización OPs
| # | Caso | Verificación |
|---|---|---|
| S1 | Click botón "Sincronizar Effi" | dialog visible, mensaje correcto |
| S2 | Cancelar dialog | sin acción, botón vuelve a idle |
| S3 | Confirmar | botón cambia a "Sincronizando..." con ícono `spin-ico` |
| S4 | Endpoint responde con SSE | notify "ongoing" muestra paso actual |
| S5 | Lock activo (segunda llamada inmediata) | response 409 "Sync en curso" |
| S6 | Sync termina OK | notify positivo + tabla recargada |
| S7 | Cancelar mid-flight (cerrar tab) | proceso Python continúa hasta terminar (verificable via lock) |

#### Sidebar popovers (desktop, viewport 1280x800)
| # | Caso | Verificación |
|---|---|---|
| P1 | Hover sobre "Proyectos" (en Mis Tareas) | aparece popover lateral con lista de proyectos |
| P2 | Click en proyecto | navega + cierra popover |
| P3 | Hover sobre "Etiquetas" | aparece popover con etiquetas + edit inline |
| P4 | Hover sobre OPs | aparece popover con OPs |
| P5 | Mover mouse fuera | popover se cierra tras 180ms |
| P6 | Botón "+" dentro popover | abre TareaForm (sin cerrar popover) |

#### Sidebar mobile (viewport 390x844 emulated)
| # | Caso | Verificación |
|---|---|---|
| M1 | Drawer abierto | acordeón vertical funciona como antes |
| M2 | Click en "Proyectos" sub-section | expand/collapse vertical (no popover) |
| M3 | Click en proyecto | navega + cierra drawer mobile |

### Errores a observar
- Sin warnings Vue en consola.
- Sin glitch visual al pasar de mobile (stretch) a desktop (popover).

---

## Versión

`v2.10.0` (incluye una feature nueva visible + refactor estructural significativo del sidebar — bump minor, no patch).

## Cambios de infraestructura

Ninguno. Todo dentro del repo + VPS ya configurado (Playwright + scripts + BDs locales).
