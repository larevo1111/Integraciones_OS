---
description: "Carga el contexto completo del Sistema de Gestión OS (Tareas, Jornadas, Proyectos)."
---

# Skill: Sistema de Gestión OS — Origen Silvestre

> Leer antes de crear o modificar cualquier componente, endpoint o tabla del sistema de gestión.
> Contexto profundo: `.agent/contextos/sistema_gestion.md`
> Reglas de diseño: `sistema_gestion/REGLAS_APP.md`
> Acta de decisiones: `sistema_gestion/ACTA_APLICACION.md`

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Vue 3 + Quasar 2 (SPA), dev puerto 9301 |
| API | Express.js, puerto 9300 |
| Systemd | `os-gestion.service` |
| URL | gestion.oscomunidad.com (Cloudflare tunnel) |
| Auth | Google OAuth (GSI renderButton) + JWT doble |

### BD — 3 pools independientes (Hostinger)

| Pool | BD | Usuario | Uso |
|---|---|---|---|
| `poolGestion` | `u768061575_os_gestion` | `u768061575_os_gestion` | Tablas propias (g_*) |
| `poolComunidad` | `u768061575_os_comunidad` | `u768061575_ssierra047` | READ ONLY — usuarios (sys_usuarios) |
| `poolIntegracion` | `u768061575_os_integracion` | `u768061575_osserver` | READ ONLY — OPs, remisiones, pedidos |

**Contraseña**: `Epist2487.` (todas iguales)
**SSH tunnel**: `u768061575@109.106.250.195:65002` con key `~/.ssh/sos_erp`

---

## Tablas implementadas (BD os_gestion)

| Tabla | Descripción |
|---|---|
| `g_categorias` | 13 seeds: Ventas, Producción, Logística, etc. Campos `es_produccion`, `es_empaque` |
| `g_tareas` | Central: título, estado, prioridad, categoría, proyecto, responsable, `id_op`, `id_remision`, `id_pedido`, `tiempo_estimado_min`, `tiempo_real_min` |
| `g_tarea_tiempo` | Sesiones de cronómetro: inicio, fin, duración, pausas |
| `g_perfiles` | 5 roles: Director, Comercial, Producción, Logística, Sistemas |
| `g_categorias_perfiles` | Junction categorías↔perfiles |
| `g_proyectos` | Tabla unificada: campo `tipo` = proyecto / dificultad / compromiso / idea |
| `g_proyectos_responsables` | Múltiples responsables por proyecto |
| `g_etiquetas` | Tags por empresa |
| `g_etiquetas_tareas` | Junction etiquetas↔tareas |
| `g_etiquetas_proyectos` | Junction etiquetas↔proyectos |
| `g_jornadas` | Check-in/check-out con hora editable + hora registro (auditoría UTC) |
| `g_jornada_pausas` | Pausas por jornada |
| `g_jornada_pausa_tipos` | Catálogo: Almuerzo, Desayuno, Pausa Activa, Imprevisto |
| `g_usuarios_config` | Config por usuario: tema dark/light, token FCM |

---

## Rutas / páginas

| Ruta | Componente | Propósito |
|---|---|---|
| `/login` | `LoginPage.vue` | Auth Google OAuth + selección empresa |
| `/tareas` | `TareasPage.vue` (soloMias=true) | Tareas del usuario: QuickAdd, filtros, cronómetro |
| `/equipo` | `TareasPage.vue` (soloMias=false) | Tareas del equipo completo |
| `/jornadas` | `EquipoPage.vue` | Jornadas laborales del equipo |
| `/proyectos-tabla` | `ItemsTablePage.vue` (tipo='proyecto') | Proyectos |
| `/dificultades` | `ItemsTablePage.vue` (tipo='dificultad') | Dificultades |
| `/compromisos` | `ItemsTablePage.vue` (tipo='compromiso') | Compromisos |
| `/ideas` | `ItemsTablePage.vue` (tipo='idea') | Ideas |

---

## Endpoints API principales

### Auth
```
POST /api/auth/google              — Login con token Google
POST /api/auth/seleccionar_empresa — Paso 2: elige empresa → JWT final
GET  /api/auth/me                  — Datos del usuario actual
```

### Tareas
```
GET    /api/gestion/tareas            — Lista (?filtro=hoy|manana|semana&estado=&categoria_id=&proyecto_id=)
POST   /api/gestion/tareas            — Crear
PUT    /api/gestion/tareas/:id        — Editar
POST   /api/gestion/tareas/:id/completar — Completar (con tiempo_real_min)
POST   /api/gestion/tareas/:id/iniciar   — Iniciar cronómetro
PUT    /api/gestion/tareas/:id/pausar    — Pausar cronómetro
DELETE /api/gestion/tareas/:id        — Eliminar
```

### Jornadas
```
GET  /api/gestion/jornadas/hoy       — Jornada actual del usuario
POST /api/gestion/jornadas/iniciar   — Check-in
PUT  /api/gestion/jornadas/:id/finalizar  — Check-out
PUT  /api/gestion/jornadas/:id/reabrir    — Reabrir (máx 1h)
PUT  /api/gestion/jornadas/:id/editar     — Editar hora (usuario)
PUT  /api/gestion/jornadas/:id/editar-admin — Editar hora (admin, sin restricción)
GET  /api/gestion/jornadas/equipo    — Lista equipo (?desde=&hasta=)
POST /api/gestion/jornadas/:id/pausas — Agregar pausa
GET  /api/gestion/tipos-pausa        — Catálogo tipos pausa
```

### Proyectos (tabla unificada)
```
GET    /api/gestion/proyectos         — Lista (?tipo=proyecto|dificultad|compromiso|idea&estado=)
GET    /api/gestion/proyectos/:id     — Detalle
POST   /api/gestion/proyectos         — Crear
PUT    /api/gestion/proyectos/:id     — Editar
DELETE /api/gestion/proyectos/:id     — Eliminar
```

### Documentos Effi (read-only desde os_integracion)
```
GET /api/gestion/ops                     — OPs vigentes no procesadas
GET /api/gestion/op/:id                  — Detalle OP
GET /api/gestion/op/:id/pdf              — PDF de la OP (Playwright)
GET /api/gestion/remisiones              — Buscar remisiones
GET /api/gestion/remision/:id/pdf        — PDF remisión
GET /api/gestion/pedidos                 — Buscar cotizaciones/pedidos
GET /api/gestion/pedido/:id/pdf          — PDF pedido
```

### Otros
```
GET/POST/PUT/DELETE /api/gestion/etiquetas   — CRUD etiquetas
GET /api/gestion/usuarios                     — Lista usuarios empresa
GET /api/gestion/categorias                   — Categorías de tareas
```

---

## Componentes Vue clave

| Componente | Propósito |
|---|---|
| `TareasPage.vue` | QuickAdd inline (desktop), filtros, agrupación, multi-selección |
| `TareaItem.vue` | Fila de tarea: checkbox, prioridad, cronómetro, badges |
| `TareaForm.vue` | Formulario completo (modal desktop, bottom-sheet móvil) |
| `TareaPanel.vue` | Panel lateral derecho (500px desktop) |
| `EquipoPage.vue` | Tabla jornadas con GestionTable |
| `GestionTable.vue` | Tabla estándar dark-mode (equivalente a OsDataTable del ERP) |
| `ItemsTablePage.vue` | Tabla reutilizable para proyectos/dificultades/compromisos/ideas |
| `ProyectoPanel.vue` | Panel lateral: quick-edit, TipTap editor, sub-panel tarea |
| `OpSelector.vue` | Autocomplete OPs vigentes: busca por número/descripción |
| `RemisionSelector.vue` | Autocomplete remisiones: busca por número/cliente |
| `PedidoSelector.vue` | Autocomplete cotizaciones: busca por número/cliente |
| `EtiquetasSelector.vue` | Multi-select chips + botón agregar |
| `ProyectoSelector.vue` | Selector de proyecto activo |

---

## Reglas de diseño obligatorias (R01-R10)

| Regla | Resumen |
|---|---|
| R01 | Cada tipo de campo → siempre el mismo componente |
| R02 | Dropdowns con Teleport + posición fija |
| R03 | Multi-select: chips + botón agregar dashed |
| R04 | Icono calendario visible en dark mode |
| R05 | Prioridad = 4 chips pill (Urgente/Alta/Media/Baja), NUNCA select |
| R06 | Solo proyectos activos en selectores |
| R07 | Estados proyecto: Activo, Archivado, Completado |
| R08 | Endpoints: `/api/gestion/*` NUNCA `/api/*` |
| R09 | Acento verde `#00C853`, NO violeta |
| R10 | Dark mode primero — probar dark antes que light |

**Colores prioridad**: Urgente `#ef4444`, Alta `#f59e0b`, Media `#6b7280`, Baja `#374151`

---

## Gotchas técnicos

- **JWT 2 pasos**: primer token temporal (tipo='temporal') → seleccionar empresa → token final (tipo='final'). Todos los endpoints verifican `tipo==='final'`.
- **Timezone filtros**: usar `_localISO` helpers (`hoyISO`, `mananaISO`, `isoRelativo`), NUNCA `toISOString().slice(0,10)`.
- **Cronómetro**: FLOOR para duración (no ROUND). Si tarea se completa con cronómetro activo, se detiene y se suma.
- **Cascada estados**: completar padre → todas las subtareas pasan a Completada. Reabrir padre → subtareas vuelven a estado original.
- **Multi-selección**: Ctrl+click desktop, long-press 500ms móvil. Floating action bar con acciones bulk.
- **Gap jornada**: 6 horas entre check-out y nuevo check-in. Turno nocturno busca jornada de ayer si cruza medianoche.
- **Hora editable vs registro**: `hora_inicio` (editable por usuario) ≠ `hora_inicio_registro` (UTC automático, auditoría).
- **3 pools MySQL**: NUNCA mezclar. Usuarios siempre de `poolComunidad`, datos gestión de `poolGestion`, OPs de `poolIntegracion`.

---

## Build y deploy

```bash
# Build frontend
cd /home/osserver/Proyectos_Antigravity/Integraciones_OS/sistema_gestion/app
npx quasar build
# Output: sistema_gestion/app/dist/spa/ → copiado por script a sistema_gestion/api/public/

# Reiniciar API
sudo systemctl restart os-gestion.service

# Logs
journalctl -u os-gestion -f
```

---

## Archivos clave

| Archivo | Propósito |
|---|---|
| `sistema_gestion/api/server.js` | Express API + rutas + auth middleware |
| `sistema_gestion/app/src/router/routes.js` | Rutas Vue |
| `sistema_gestion/app/src/pages/` | Páginas Vue |
| `sistema_gestion/app/src/components/` | Componentes reutilizables |
| `sistema_gestion/ACTA_APLICACION.md` | Registro de decisiones de diseño |
| `sistema_gestion/REGLAS_APP.md` | Reglas R01-R10 |
| `.agent/contextos/sistema_gestion.md` | Contexto profundo del módulo |
