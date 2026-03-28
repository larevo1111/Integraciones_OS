# PLAN: Dificultades, Compromisos y unificación de Proyectos

**Fecha**: 2026-03-27
**Estado**: Aprobado — pendiente de ejecución
**Módulo**: sistema_gestion

---

## Visión

Unificar Proyectos, Dificultades y Compromisos en una sola tabla `g_proyectos` con campo `tipo`. Para el usuario son cosas separadas (sidebar agrupado, páginas tabla distintas), pero comparten la misma estructura de datos. Agregar editor TipTap para contenido rico y panel lateral para edición (reemplaza el modal popup actual).

---

## Estructura de datos

### Tabla unificada: g_proyectos

Una sola tabla para los 3 tipos. Se agrega el campo `tipo` para distinguirlos. Los registros actuales quedan como `tipo='proyecto'` automáticamente.

```sql
ALTER TABLE g_proyectos
  ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'proyecto' AFTER empresa;
-- Valores: 'proyecto', 'dificultad', 'compromiso', 'idea'
```

### Estructura completa de la tabla (campos existentes + nuevo)

| Campo | Tipo | Existe? | Uso |
|---|---|---|---|
| id | INT PK AUTO | ✅ ya | PK |
| empresa | VARCHAR(50) | ✅ ya | Multi-tenant |
| **tipo** | **VARCHAR(20) NOT NULL DEFAULT 'proyecto'** | **🆕 NUEVO** | **'proyecto', 'dificultad', 'compromiso', 'idea'** |
| nombre | VARCHAR(80) | ✅ ya | Título visible en tabla y sidebar |
| descripcion | TEXT | ✅ ya | **Contenido TipTap (HTML) — label "Desarrollo" en el UI para todos los tipos** |
| color | VARCHAR(20) | ✅ ya | Color del dot en sidebar |
| estado | VARCHAR(20) | ✅ ya | **Valores distintos según tipo (ver abajo)** |
| prioridad | VARCHAR(20) | ✅ ya | Baja, Media, Alta, Urgente |
| categoria_id | INT FK → g_categorias | ✅ ya | Mismas 13 categorías de tareas |
| fecha_estimada_fin | DATE NULL | ✅ ya | Fecha estimada de resolución |
| fecha_finalizacion_real | DATE NULL | ✅ ya | Fecha real de cierre |
| responsables | M:N → g_proyectos_responsables | ✅ ya | Quién(es) están a cargo |
| etiquetas | M:N → g_etiquetas_proyectos | ✅ ya | Etiquetas asociadas |
| usuario_creador | VARCHAR | ✅ ya | Auditoría — quién creó |
| usuario_ult_modificacion | VARCHAR | ✅ ya | Auditoría — última edición |
| fecha_creacion | TIMESTAMP | ✅ ya | Auditoría — cuándo se creó |
| fecha_ult_modificacion | TIMESTAMP | ✅ ya | Auditoría — última modificación |

### Valores de `estado` según `tipo`

| Tipo | Valores de estado | Default al crear |
|---|---|---|
| proyecto | Activo, Completado, Archivado | Activo |
| dificultad | Abierta, En progreso, Resuelta, Cerrada | Abierta |
| compromiso | Pendiente, En progreso, Cumplido, Cancelado | Pendiente |
| idea | Nueva, En evaluación, Aprobada, Descartada | Nueva |

### Relación con tareas

Las tareas ya tienen `proyecto_id` (FK → g_proyectos). **No se toca g_tareas.** Una tarea se asocia a un proyecto, dificultad o compromiso exactamente igual: asignando su `proyecto_id`. Para el usuario la UX es la misma — el ProyectoSelector muestra los 3 tipos agrupados.

### Migración

No hay migración de datos — todos los registros actuales en g_proyectos quedan automáticamente como `tipo='proyecto'` por el DEFAULT.

---

## Cambios en Backend (server.js)

### Endpoints existentes — adaptar

| Endpoint | Cambio |
|---|---|
| `GET /api/gestion/proyectos` | Agregar query param `?tipo=proyecto\|dificultad\|compromiso`. Default: todos. Filtrar `WHERE tipo = ?` |
| `POST /api/gestion/proyectos` | Aceptar `tipo` en body. Default 'proyecto'. Validar valores de `estado` según `tipo` |
| `PUT /api/gestion/proyectos/:id` | Sin cambios (ya acepta estado libre). Validar estado según tipo |
| `DELETE /api/gestion/proyectos/:id` | Sin cambios |

### Validación de estado por tipo (en POST y PUT)

```javascript
const ESTADOS_POR_TIPO = {
  proyecto:    ['Activo', 'Completado', 'Archivado'],
  dificultad:  ['Abierta', 'En progreso', 'Resuelta', 'Cerrada'],
  compromiso:  ['Pendiente', 'En progreso', 'Cumplido', 'Cancelado'],
}
```

El GET de proyectos para el sidebar debe retornar el campo `tipo` en la respuesta.

---

## Cambios en Frontend

### Fase 1 — TipTap (dependencia nueva)

Instalar en `sistema_gestion/app/`:
```bash
npm install @tiptap/vue-3 @tiptap/starter-kit @tiptap/extension-link @tiptap/extension-placeholder
```

Crear componente reutilizable:

**`src/components/TipTapEditor.vue`**
- Props: `modelValue` (HTML string), `placeholder`, `editable` (default true)
- Emits: `update:modelValue` (debounce 1s)
- Extensiones: StarterKit (bold, italic, headings h2/h3, bullet/ordered lists, code, blockquote), Link, Placeholder
- Sin toolbar visible — slash commands `/` para insertar (heading, lista, quote, separador)
- O mini-toolbar flotante al seleccionar texto (bold, italic, link, code)
- Estilos dark mode con variables CSS del manual existente
- Altura mínima: 120px, crece con contenido

### Fase 2 — ProyectoPanel (reemplaza ProyectoModal)

**`src/components/ProyectoPanel.vue`** — panel lateral derecho

**Desktop**: panel fijo derecho (ancho ~400px), sobre el contenido, con overlay
**Mobile**: bottom sheet (como JornadaDetallePopup)

**Estructura del panel:**
```
┌─────────────────────────────────┐
│ [×]  Nueva dificultad    [···] │ ← header: close + título tipo + menú
├─────────────────────────────────┤
│                                 │
│ [Título editable - textarea]    │
│                                 │
│ Status      [● Abierta    ▾]   │ ← chips/dropdown, quick-edit inline
│ Prioridad   [  Alta       ▾]   │
│ Categoría   [  Producción ▾]   │
│ Responsable [ Jennifer    ▾]   │
│ Proyecto    [  (ninguno)  ▾]   │ ← solo para dificultad/compromiso: opcionalmente asociar a un proyecto
│ Fecha est.  [ 2026-04-15    ]  │
│ Etiquetas   [tag1] [tag2] [+]  │
│                                 │
│ ── Desarrollo ──────────────── │
│ [TipTap editor - rich text]    │
│                                 │
│                                 │
│ ── Tareas vinculadas (3) ───── │
│   ○ Buscar proveedor alt.      │
│   ○ Negociar precios           │
│   ○ Ajustar recetas            │
│   [+ Vincular tarea]           │
│                                 │
│ creado por jen · 25 mar 2026   │
│ editado por san · hace 2h      │
└─────────────────────────────────┘
```

**Propiedades quick-edit inline** (como Notion):
- Click en el valor → se vuelve editable (dropdown, input, chips)
- Guardar al blur o al seleccionar — `PUT /api/gestion/proyectos/:id`
- Feedback visual: el campo brilla brevemente al guardar (transition)

**Sección "Tareas vinculadas":**
- Muestra tareas que tienen `proyecto_id = este_item.id`
- Botón "+ Vincular tarea" → dropdown autocomplete de tareas existentes → `PUT /api/gestion/tareas/:id` con `proyecto_id`
- Click en tarea → navega a `/tareas` filtrado

**Sección "Desarrollo":**
- TipTapEditor con placeholder "Describe la situación, documenta el progreso..."
- Auto-save con debounce (1-2s tras dejar de escribir) → `PUT /api/gestion/proyectos/:id` con `{ descripcion: html }`

**El panel se abre desde:**
1. Sidebar: `[+]` de cada sección → panel en modo crear (tipo pre-seteado)
2. Sidebar: menú `⋮` → "Editar" → panel en modo editar
3. Página tabla: click en fila → panel en modo editar
4. ProyectoSelector: "Nuevo proyecto/dificultad/compromiso" → panel en modo crear

### Fase 3 — Sidebar (MainLayout.vue)

Reemplazar la sección actual de "Proyectos" por 3 secciones:

```html
<!-- PROYECTOS -->
<div class="sidebar-section">
  <div class="sidebar-section-label">
    <span>Proyectos</span>
    <button class="btn-icon-tiny" @click="abrirPanel('proyecto')">+</button>
  </div>
  <div v-for="p in proyectosTipo('proyecto')" ...> <!-- mismo template actual --> </div>
</div>

<!-- DIFICULTADES -->
<div class="sidebar-section">
  <div class="sidebar-section-label">
    <span>Dificultades</span>
    <button class="btn-icon-tiny" @click="abrirPanel('dificultad')">+</button>
  </div>
  <div v-for="p in proyectosTipo('dificultad')" ...> <!-- mismo template --> </div>
</div>

<!-- COMPROMISOS -->
<div class="sidebar-section">
  <div class="sidebar-section-label">
    <span>Compromisos</span>
    <button class="btn-icon-tiny" @click="abrirPanel('compromiso')">+</button>
  </div>
  <div v-for="p in proyectosTipo('compromiso')" ...> <!-- mismo template --> </div>
</div>

<!-- Completados (los 3 tipos juntos) -->
<div class="completados-wrap">...</div>
```

**`proyectosTipo(tipo)`**: computed que filtra `proyectos.value.filter(p => p.tipo === tipo)`.

**Menú `⋮` de cada item** — agregar opción:
- Editar → abre ProyectoPanel
- **Ver tabla** → navega a `/dificultades`, `/pendientes` o `/tareas?tab=proyectos` según tipo
- Archivar
- Eliminar

**Eliminar `ProyectoModal`** del MainLayout. Reemplazar por `ProyectoPanel`.

**Completados**: El acordeón muestra los completados/resueltos/cumplidos de los 3 tipos, con un indicador visual del tipo (icono o label sutil).

### Fase 4 — ProyectoSelector (en formulario de tareas)

Adaptar `ProyectoSelector.vue` para mostrar agrupado por tipo:

```
Sin asignar

── Proyectos ──────────────────
  ● Rediseño web
  ● Lanzamiento Q2

── Dificultades ───────────────
  ● Proveedor dejó de surtir

── Compromisos ────────────────
  ● Cotización cliente ABC

─────────────────────────────
+ Nuevo proyecto
+ Nueva dificultad
+ Nuevo compromiso
```

**Cambios:**
- `cargarProyectos()` ya trae todos — agrupar en el template con headers
- La búsqueda filtra en los 3 grupos
- Los 3 botones "Nuevo..." abren el ProyectoPanel con tipo pre-seteado
- El `modelValue` sigue siendo `proyecto_id` (INT) — sin cambios en g_tareas

### Fase 5 — Páginas tabla

Las rutas ya existen en routes.js pero las páginas no están creadas. Crear:

**`src/pages/DificultadesPage.vue`**
- GestionTable con columnas: título, status (badge color), prioridad, categoría, responsable, fecha_estimada, tareas (count)
- Filtros: status (Abierta/En progreso/Resuelta/Cerrada), prioridad, categoría
- Click en fila → abre ProyectoPanel en modo edición
- Botón "Nueva dificultad" arriba → abre ProyectoPanel con tipo='dificultad'
- API: `GET /api/gestion/proyectos?tipo=dificultad`

**`src/pages/PendientesPage.vue`** (Compromisos)
- Misma estructura que DificultadesPage pero con `tipo=compromiso`
- Status: Pendiente, En progreso, Cumplido, Cancelado

**`src/pages/ProyectosPage.vue`** (opcional — para "Ver tabla" desde sidebar)
- Misma estructura con `tipo=proyecto`
- Status: Activo, Completado, Archivado

**Nota**: Las 3 páginas son prácticamente idénticas. Se puede crear un componente base reutilizable `ItemsTablePage.vue` que reciba `tipo` como prop y adapte columnas/filtros/labels.

### Fase 6 — Rutas

Actualizar `routes.js`:
```javascript
{ path: 'dificultades', component: () => import('pages/DificultadesPage.vue') },
{ path: 'pendientes',   component: () => import('pages/PendientesPage.vue') },
{ path: 'proyectos',    component: () => import('pages/ProyectosPage.vue') },
```

Eliminar rutas de detalle (`/dificultades/:id`, `/pendientes/:id`, etc.) — el detalle se abre en panel lateral, no en página separada.

Eliminar rutas de Ideas e Informes por ahora (no son parte de esta fase).

### Fase 7 — Mobile

**Sidebar (drawer mobile):**
- Agregar las 3 secciones (Proyectos, Dificultades, Compromisos) al drawer
- Los items del sidebar llevan a filtro de tareas
- Los links de las secciones (Dificultades, Pendientes) llevan a las páginas tabla

**ProyectoPanel:**
- En mobile (≤768px): bottom sheet (como JornadaDetallePopup)
- Scroll interno para el contenido largo (TipTap)
- Propiedades en layout de 1 columna
- TipTap con altura mínima reducida (80px)

**Páginas tabla:**
- GestionTable ya es responsive (scroll horizontal)
- Click en fila → bottom sheet con ProyectoPanel

---

## Navegación — sidebar desktop completo

```
── Tareas ──────────────────────
  📋 Mis Tareas                  → /tareas
  👥 Equipo                      → /equipo
  🕐 Jornadas                   → /jornadas

── Proyectos ──────────── [+] ──
  ● Rediseño web            (3)  → /tareas?proyecto_id=X
  ● Lanzamiento Q2          (5)  → /tareas?proyecto_id=Y

── Dificultades ─────────  [+] ──
  ● Proveedor X              (2) → /tareas?proyecto_id=Z
  ● Bug facturación           (1) → /tareas?proyecto_id=W

── Compromisos ──────────  [+] ──
  ● Cotización ABC            (1) → /tareas?proyecto_id=V

  ▸ Completados (4)

── Tablas ──────────────────────
  📁 Proyectos                   → /proyectos
  ⚠️ Dificultades                → /dificultades
  📌 Compromisos                 → /pendientes
```

---

## Orden de implementación

| # | Tarea | Dependencia |
|---|---|---|
| 1 | ALTER TABLE g_proyectos + adaptar endpoints backend | — |
| 2 | Instalar TipTap + crear TipTapEditor.vue | — |
| 3 | Crear ProyectoPanel.vue (reemplaza ProyectoModal) | 2 |
| 4 | Adaptar MainLayout sidebar (3 secciones + completados) | 1, 3 |
| 5 | Adaptar ProyectoSelector (agrupado por tipo) | 1 |
| 6 | Crear página tabla reutilizable (DificultadesPage, PendientesPage, ProyectosPage) | 1, 3 |
| 7 | Actualizar rutas + limpiar rutas/componentes obsoletos | 6 |
| 8 | Mobile (drawer + bottom sheet + responsive) | 3, 4, 6 |
| 9 | Build + QA + commit | todo |

**Pasos 1 y 2 son independientes — se pueden hacer en paralelo.**

---

## Archivos afectados

### Nuevos
- `src/components/TipTapEditor.vue`
- `src/components/ProyectoPanel.vue`
- `src/pages/DificultadesPage.vue`
- `src/pages/PendientesPage.vue`
- `src/pages/ProyectosPage.vue`

### Modificados
- `api/server.js` — endpoints de proyectos (filtro por tipo, validación estado)
- `src/layouts/MainLayout.vue` — sidebar 3 secciones, eliminar ProyectoModal, agregar ProyectoPanel
- `src/components/ProyectoSelector.vue` — agrupar por tipo + 3 botones crear
- `src/router/routes.js` — ajustar rutas

### Eliminados
- `src/components/ProyectoModal.vue` — reemplazado por ProyectoPanel
- `src/pages/DetalleDificultadPage.vue` — no usado (panel lateral)
- `src/pages/DetalleIdeaPage.vue` — no usado
- `src/pages/DetallePendientePage.vue` — no usado
- `src/pages/DetalleInformePage.vue` — no usado
- `src/pages/IdeasPage.vue` — no es parte de esta fase
- `src/pages/InformesPage.vue` — no es parte de esta fase

---

## Fuera de alcance (fase futura)

- Ideas y Hechos (otro tipo en g_proyectos o módulo separado — definir con Santi)
- Informes / Actas (definir estructura con Santi)
- Notificaciones push FCM
- APK Android (Capacitor)
