# Contexto: Sistema Gestión OS
**Actualizado**: 2026-04-29
**Versión actual**: v2.10.20

## Propósito

App de tareas y conocimiento del equipo. Reemplaza Notion.
Web activa en gestion.oscomunidad.com + Android futuro (Capacitor).

## Infraestructura

| Recurso | Detalle |
|---|---|
| URL | gestion.oscomunidad.com |
| Puerto API | 9300 |
| Systemd | `os-gestion.service` |
| Directorio | `sistema_gestion/` |
| Build prod | `cd sistema_gestion/app && npm run build && rsync -a --delete dist/pwa/ ../api/public/` (modo PWA, NO `npx quasar build`) |
| Dev frontend | `cd sistema_gestion/app && npx quasar dev` (puerto 9301) |
| Manual diseño | `sistema_gestion/MANUAL_DISENO_HIBRIDO.md` |
| Hosting | **VPS Contabo 94.72.115.156** — DNS apunta al VPS desde 2026-04-20 |

### Deploy a VPS
1. `npm run build` local + rsync a `api/public/` + commit + push
2. SSH al VPS: `git pull` + `systemctl restart os-gestion.service`
3. Sudo del VPS sin password sobre `osserver` no está configurado — usar sudoers o root via `sshpass -p '<pwd>' ssh root@94.72.115.156`

## Credenciales BD (3 pools centralizados)

**Desde 2026-04-20**: los 3 pools se leen via `lib/db_conn.js` desde `integracion_conexionesbd.env` en la raíz del repo. Nada hardcoded.

| Pool | BD | Servidor | Usuario |
|---|---|---|---|
| `db.comunidad` | `u768061575_os_comunidad` | Hostinger (sigue ahí) | `u768061575_ssierra047` |
| `db.gestion`   | `os_gestion` | **VPS Contabo** | `os_gestion` |
| `db.integracion` | `os_integracion` | **VPS Contabo** | `os_integracion` |

Pool `comunidad` usa SSH tunnel a Hostinger (puerto 65002, key `sos_erp`). Pools `gestion` e `integracion` usan SSH tunnel al VPS (puerto 22, key `id_ed25519`, user `osserver`). Timezone nativo del MariaDB VPS = `-05:00`.

## Tablas en `os_gestion` (VPS Contabo)

| Tabla | Descripción |
|---|---|
| `g_categorias` | Categoría principal de tarea (16 activas + Informes desactivada). Color, ícono, orden, `es_produccion`, `es_empaque`. Cambios 2026-04-29: insertada **Desarrollo_de_producto** (id 17, orden 10), renombrada Reuniones → **Reuniones_e_informes** (id 11), desactivada Informes (id 6) — fusionada con Reuniones |
| `g_categorias_produccion` | Sub-categorías de tarea cuando categoría principal es Producción (Alistamiento, Templado, Enmoldado, Desenmoldado, Empaque, Etiquetado, Sellado, Esterilización, Pasteurización, Encordonado, Loteado, Limpieza, Otra). 2026-04-29: agregadas **Produccion** (id 14, orden 1) y **Desenmoldado** (id 13, orden 4) |
| `g_tareas` | Tareas. Duraciones 5S: `duracion_usuario_seg` (confirmada por usuario al completar), `duracion_cronometro_seg` (raw del crono), `duracion_sistema_seg` (fecha_fin_real - fecha_inicio_real). `crono_inicio` (DATETIME, NULL=pausado). Vinculación: `id_op` (OP actual), `id_op_original` (OP previa antes de validar), `categoria_produccion_id`. Tiempos manuales: `tiempo_alistamiento_min`, `tiempo_produccion_min`, `tiempo_empaque_min`, `tiempo_limpieza_min` |
| `g_op_detalle` | **Una fila por OP** (UPSERT por `id_op`+`empresa`). `observaciones_lote`, `procesado_por`, `procesado_en`, `validado_por`, `validado_en`, `op_anterior`, `responsable_validado` |
| `g_op_lineas` | Materiales/productos REALES de una OP (después de validar). `tipo` enum('material','producto'), `cod_articulo`, `descripcion`, `unidad`, `cantidad_teorica`, `cantidad_real`, `costo_unit`, `precio_unit`, `es_no_previsto` |
| `g_op_tiempos` | **Snapshot de tiempos consolidados por OP × categoria_produccion** (`segundos_totales`). Se llena al validar OP O al editar manualmente desde OpPanel (nivel ≥5). Si está vacío para una OP, los tiempos se calculan al vuelo desde `g_tareas.duracion_usuario_seg` (modo "vivo") |
| `g_tarea_produccion_lineas` | (Legacy 2026-04-21) Líneas materiales/productos por tarea. Reemplazado en gran parte por `g_op_lineas` que es por OP, no por tarea |
| `g_tarea_tiempo` | Legacy — ya no se consulta. Las duraciones viven en `g_tareas` directamente |
| `g_usuarios_config` | Configuración por usuario |
| `g_perfiles` | Perfiles de usuario |
| `g_categorias_perfiles` | Relación categorías-perfiles |
| `g_proyectos` | Items unificados: proyectos, dificultades, compromisos, ideas (campo `tipo`) |
| `g_proyectos_responsables` | Relación proyectos-usuarios |
| `g_etiquetas` | Etiquetas de la empresa |
| `g_etiquetas_tareas` | Relación etiquetas-tareas |
| `g_etiquetas_proyectos` | Relación etiquetas-proyectos |

### Tabla auxiliar en `os_integracion` (VPS)
| Tabla | Descripción |
|---|---|
| `unidades_articulos` | **Nueva (2026-04-21)** — 490 filas con `cod_articulo` + `unidad` (UND/KG/GRS/etc). Copia de `inv_rangos` de `os_inventario` local para lookup desde VPS. Se usa en el endpoint `/produccion` para mostrar unidad al lado del estimado/real |

## Feature: Detalles de Producción (2026-04-23, v2.8.5)

Sección "Detalles de producción" dentro del panel de tarea. Se renderiza solo si `categoria.es_produccion = 1` **y** `tarea.id_op` vinculado.

### Componentes
- [DetallesProduccion.vue](../../sistema_gestion/app/src/components/DetallesProduccion.vue) — acordeón con 3 bloques: OP vinculada, Materiales+Productos (tabla con Teórico/Real), Tiempos (4 inputs + total).
- [services/numero.js](../../sistema_gestion/app/src/services/numero.js) — helpers `parseDecimal()` (acepta coma y punto) y `fmtNum()` (formato es-CO).

### Endpoints (backend)
- `GET /api/gestion/tareas/:id/produccion` — devuelve materiales, productos, tiempos. Siembra automática desde Effi si no hay líneas locales. Detecta cambio de OP (si los `cod_articulo` de las líneas locales no coinciden con los de la OP actual en Effi, re-siembra — solo si no hay `cantidad_real` guardada aún, para no perder datos del usuario).
- `PUT /api/gestion/tareas/:id/produccion/lineas/:lineaId` — actualiza `cantidad_real` de una línea.
- `PUT /api/gestion/tareas/:id/produccion/tiempos` — actualiza los 4 tiempos.
- `POST /api/gestion/tareas/:id/produccion/procesar` — cambia estado de la OP a **Procesada** en Effi. Permisos: responsable de la tarea o nivel ≥ responsable. Observación auto-generada: `"Reportó: <nombre> (OS Gestión)"`. Refleja el cambio al instante en `zeffi_produccion_encabezados` (staging) para que el UI vea `Procesada` sin esperar el pipeline.
- `POST /api/gestion/tareas/:id/produccion/validar` — solo nivel ≥ 5. Flujo completo encadenado (~2-3 min):
  1. Anular OP original con observación.
  2. Crear OP nueva con cantidades reales (JSON construido desde `g_tarea_produccion_lineas.cantidad_real` + metadata copiada de la OP original).
  3. Capturar `OP_CREADA:<id>` del stdout de `import_orden_produccion.js`.
  4. Cambiar estado de la nueva OP a **Validado**.
  5. Actualizar `g_tareas.id_op` (nueva) + `id_op_original` (anterior).
  6. Reflejar en staging: vieja → Anulada, nueva → Validado.

### Scripts Playwright utilizados
- `scripts/anular_orden_produccion.js` (existente)
- `scripts/import_orden_produccion.js` (modificado — ahora imprime `OP_CREADA:<id>` en stdout)
- `scripts/cambiar_estado_orden_produccion.js` (nuevo — estados Generada/Procesada/Validado)

### Protección 503 + retry
Los endpoints `/procesar` y `/validar` verifican al arranque si el server tiene Playwright + session.json. Si no (p. ej. servidor de respaldo sin playwright), devuelven `503 {retry:true}` y el frontend (`services/api.js`) reintenta automáticamente hasta 5 veces. Útil para setups multi-server donde solo uno tiene Playwright.

### UX
- Chip de estado junto al ID de OP: Generada (gris), Procesada (naranja), Validado (verde), Anulada (gris oscuro).
- Si `tarea.id_op_original` → texto chico gris "OP orig: xxxx".
- Botón "Procesar" se deshabilita si OP ya está Procesada o Validado.
- Botón "Validar" solo visible para `auth.usuario.nivel >= 5`.
- Modales de confirmación con `dark: true` (contraste correcto en oscuro y claro).
- Inputs `filled` de Quasar con `--bg-row-hover` para contraste en dark mode del proyecto.
- Decimal tolerante: `3,8` y `3.8` equivalen (frontend normaliza con `.replace(',', '.')` antes de enviar).

## Auth Google OAuth + JWT multi-empresa

- Google Sign-In (GSI) `renderButton` → ID token → backend
- JWT doble: temporal (si >1 empresa) → selección empresa → JWT final con `empresa_activa`
- Router guard decodifica `JWT payload.tipo==='final'` para evitar acceso con token temporal a `/tareas`
- Tabla `sys_usuarios` en Hostinger para lookup de usuarios

## Módulo Tareas — estado completo (2026-03-23)

### Funcionalidades activas

- ✅ QuickAdd inline desktop — crear tarea rápido sin modal, con proyecto y etiquetas heredados del filtro activo
- ✅ TareaForm — bottom sheet mobile / modal desktop, category chips, fechas, prioridades, responsable, proyecto, etiquetas
- ✅ TareaPanel — panel lateral desktop: todos los campos editables inline
- ✅ Filtros: hoy/mañana/semana + FiltroPersonalizado (multi-select prioridad/categoría/etiqueta/proyecto/rango fechas)
- ✅ Multi-selección — Ctrl+click desktop + long press 500ms mobile → floating action bar (Teleport body)
  - Acciones bulk: Fecha, Estado, Categoría, Proyecto, Eliminar
- ✅ Cronómetro integrado con auto-start al hacer check → "En Progreso"
- ✅ Popup completar con tiempo real pre-llenado (base + cronómetro en vivo)
- ✅ Cascada de estados: Completar padre → subtareas Pendiente/En Progreso → Completada. Cancelar padre → Cancelada. Revertir → Pendiente
- ✅ Proyectos con CRUD completo, sidebar con lista, filtro en TareasPage
- ✅ Etiquetas con multi-select chips, crear inline
- ✅ Agrupación de tareas (por categoría/proyecto/etc.)
- ✅ OpSelector — autocomplete OPs vigentes/no procesadas, busca por número OP y artículo
- ✅ RemisionSelector — busca remisiones (`zeffi_remisiones_venta_encabezados`) por ID o cliente
- ✅ PedidoSelector — busca cotizaciones (`zeffi_cotizaciones_ventas_encabezados`) por ID o cliente
  - Ambos selectores: tag con número + cliente + 2 botones hover (abrir en Effi + Ver PDF)
  - Scripts PDF: `get_remision_pdf.js`, `get_pedido_pdf.js` (URL directa, no placeholder)
- ✅ Promise.allSettled — carga paralela tolerante a fallos
- ✅ Sidebar 240px ↔ 64px colapsado (solo icono)

### UX TickTick-style

- Badge 0/N abajo del círculo (sin chip, solo texto)
- Botón ↳ al lado del badge para subtareas
- Quick insert subtarea (× + Enter/blur)
- Spinner inputs ocultos
- Cronómetro con ⏸+■
- T.real/T.estimado en filas separadas

### Fixes técnicos aplicados

| Fix | Descripción |
|---|---|
| Timezone filtros | `hoyISO()`, `mananaISO()`, `isoRelativo()` usan `_localISO()` (fecha local del navegador, no UTC). Evita desfase después de las 7 PM Colombia |
| Alineación círculo | `.btn-add-sub-solo` ahora `position: absolute; top: 100%` (antes static, empujaba 6px arriba) |
| Cronómetro ROUND→FLOOR | `duracion_min` usa `FLOOR` (no `ROUND`). Evita que 30-59 seg redondeen a 1 min |
| Tiempo al revertir | Al revertir Completada → Pendiente: envía `tiempo_real_min: 0`, backend borra sesiones de `g_tarea_tiempo` |
| Mobile subtask btn | `btn-add-sub-solo` → `position: relative` en mobile (no absolute), opacity 0.6 (siempre visible, no depende de :hover) |
| Contraste botones | opacity base 0.4 (web), 0.65 (mobile); hover 0.8; `:active` feedback 24×24px touch target |

## Endpoints API activos

```
POST /api/auth/google                     — Google ID token → JWT
POST /api/auth/seleccionar_empresa         — JWT temporal → JWT final
GET  /api/auth/me                         — perfil usuario autenticado
GET  /api/usuarios                        — lista usuarios de la empresa
GET  /api/gestion/categorias              — 13 categorías con color e icono
GET  /api/gestion/tareas                  — filtros: ?filtro=hoy|manana|semana&estado=&categoria_id=
                                            &proyecto_id=&prioridades=Alta,Urgente&categorias=1,2
                                            &etiquetas=3,4&fecha_desde=&fecha_hasta=&fecha_hoy=YYYY-MM-DD
POST /api/gestion/tareas                  — crear tarea (acepta proyecto_id, etiquetas:[])
PUT  /api/gestion/tareas/:id              — actualizar (acepta proyecto_id, etiquetas:[]) → retorna etiquetas
POST /api/gestion/tareas/:id/completar   — completa con tiempo_real_min opcional
POST /api/gestion/tareas/:id/iniciar     — inicia cronómetro
PUT  /api/gestion/tareas/:id/pausar      — pausa cronómetro
GET  /api/gestion/proyectos              — ?tipo=&estado=. retorna tareas_pendientes, responsables, etiquetas
POST /api/gestion/proyectos              — crear {nombre, tipo, estado?, color?, ...} (valida estado vs tipo)
PUT  /api/gestion/proyectos/:id          — actualizar (valida estado vs tipo en BD antes de aplicar)
DELETE /api/gestion/proyectos/:id        — desancla tareas y elimina
GET/POST/PUT/DELETE /api/gestion/etiquetas/:id  — CRUD etiquetas por empresa
GET  /api/gestion/ops                    — OPs pendientes vigentes. Acepta ?q=
GET  /api/gestion/op/:id                 — detalle OP
GET  /api/gestion/op/:id/pdf             — PDF OP via Playwright (requireAuth)
GET  /api/gestion/remisiones             — remisiones de venta. Acepta ?q=
GET  /api/gestion/remision/:id           — detalle remisión
GET  /api/gestion/remision/:id/pdf       — PDF remisión via Playwright (requireAuth)
GET  /api/gestion/pedidos                — cotizaciones de venta. Acepta ?q=
GET  /api/gestion/pedido/:id             — detalle pedido/cotización
GET  /api/gestion/pedido/:id/pdf         — PDF pedido via Playwright (requireAuth)
```

## Módulo Jornadas — ✅ IMPLEMENTADO (2026-03-26)

Spec original: `.agent/specs/SPEC_JORNADAS.md`

Sistema de check-in/check-out de jornada laboral con pausas, turno nocturno, vista admin con tabla estándar.

### Tablas (4 + campo nuevo)
- `g_jornadas` — múltiples jornadas por día por usuario (UNIQUE eliminado). Campos: hora_inicio/hora_fin (editables) + hora_inicio_registro/hora_fin_registro (auditoría inmutable) + `observaciones TEXT NULL`
- `g_jornada_pausas` — múltiples pausas por jornada
- `g_jornada_pausa_tipos` — puente M:N
- `g_tipos_pausa` — catálogo: Almuerzo, Desayuno, Pausa Activa, Imprevisto, Otro

### Reglas de negocio implementadas
- **Múltiples jornadas/día**: solo bloquea si hay una jornada activa (hora_fin IS NULL)
- **Gap 6 horas**: tras cerrar jornada, debe esperar ≥6h antes de abrir nueva. Enforced en API + frontend con countdown
- **Reabrir**: máximo 1 hora después de cerrar (no cambió)
- **Turno nocturno**: GET /hoy busca jornada activa de ayer si cruza medianoche
- **work_date (fecha DATE)**: siempre la fecha en que INICIÓ el turno, incluso si cruza medianoche
- **Dual-timestamp**: hora_* (editable por admin) + hora_*_registro (auditoría, siempre UTC_TIMESTAMP(), nunca editable)

### Componentes
- `JornadaHeader.vue` — 3 estados (sin jornada / trabajando / pausa) + botón "Nueva Jornada" con countdown 6h
- `JornadaPopover.vue` — confirmaciones
- `PausaDialog.vue` — multiselect tipos + observaciones
- `jornadaStore.js` — estado reactivo + timer live
- **`GestionTable.vue`** — componente tabla estándar (equivalente a OsDataTable del ERP, dark mode, Material Icons, popup columna vía Teleport, filtro/orden/subtotales)
- **`JornadaDetallePopup.vue`** — modal detalle: campos jornada + pausas + sección admin (editar horas/observaciones, reabrir)
- **`EquipoPage.vue`** — vista `/jornadas` con GestionTable, filtro Desde/Hasta, botón Hoy, click → popup detalle

### Endpoints API Jornadas (10)
```
GET  /api/gestion/jornadas/hoy              — jornada activa hoy (o ayer si turno nocturno)
POST /api/gestion/jornadas/iniciar          — iniciar (valida gap 6h + no activa)
PUT  /api/gestion/jornadas/:id/finalizar    — cerrar jornada
PUT  /api/gestion/jornadas/:id/reabrir      — reabrir (max 1h)
PUT  /api/gestion/jornadas/:id/editar       — editar horas manuales
PUT  /api/gestion/jornadas/:id/editar-admin — admin: edita hora_inicio, hora_fin, observaciones (NUNCA _registro)
GET  /api/gestion/jornadas/equipo           — ?desde=&hasta= (backward compat ?fecha=). Incluye pausas array
POST /api/gestion/jornadas/:id/pausas       — iniciar/finalizar pausa
GET  /api/gestion/tipos-pausa               — catálogo tipos
POST /api/gestion/tipos-pausa               — crear tipo (admin)
```

### Infraestructura
- **SSH tunnel auto-reconnect** (`db.js`): TCP server permanente, solo sshClient se recrea al detectar `close`. Retry 5s → 15s si falla.
- **UTC_TIMESTAMP()**: SIEMPRE usar en lugar de NOW() — Hostinger MySQL corre UTC+5 pero datos se almacenan UTC.
- **Notificación jornada abierta**: `scripts/notif_jornadas_abiertas.py` — cron 8pm todos los días, SSH tunnel → Hostinger → WhatsApp individual + resumen admin por WhatsApp.
  - Jornadas: consulta `g_jornadas` en `os_gestion`
  - Usuarios/teléfonos: consulta `sys_usuarios` en `os_comunidad` (NUNCA ia_service_os)
  - WhatsApp: wa_bridge API en `localhost:3100`
  - Admin: Santiago (573022921455)

### Skill tabla estándar
`.agent/skills/tabla_estandar.md` — documenta el patrón GestionTable/OsDataTable para que siempre se construya igual.

## Módulo Proyectos/Dificultades/Compromisos/Ideas — ✅ IMPLEMENTADO (2026-03-31)

Tabla `g_proyectos` unificada con campo `tipo` (proyecto, dificultad, compromiso, idea).
Cada tipo tiene estados propios validados en backend:

| Tipo | Estados | Default |
|---|---|---|
| proyecto | Activo, Completado, Archivado | Activo |
| dificultad | Abierta, En progreso, Resuelta, Cerrada | Abierta |
| compromiso | Pendiente, En progreso, Cumplido, Cancelado | Pendiente |
| idea | Nueva, En evaluación, Aprobada, Descartada | Nueva |

### Componentes

- **ProyectoPanel** — panel lateral derecho (500px desktop, bottom sheet móvil). Campos: título, estado chips, prioridad, color, categoría, responsable, etiquetas, fecha, Desarrollo (TipTap rich text). Quick-edit: cada campo guarda al cambiar sin cerrar el panel.
- **Sub-panel tarea** — clic en tarea vinculada abre TareaPanel embebido dentro del ProyectoPanel con ← Volver.
- **ProyectoSelector** — en tareas, muestra items agrupados por tipo con botones "Nuevo...".
- **ItemsTablePage** — página tabla reutilizable con `tipo` como prop. Filtros en toolbar: estado, prioridad, categoría + botón Nuevo. GestionTable con slots para cell renderers. Vue Router `watch props.tipo` para recargar al navegar.
- **Sidebar** — 4 secciones (Proyectos, Dificultades, Compromisos, Ideas) con botones [+] y menú ⋮ (Editar, Ver tabla, Archivar, Eliminar). Sección "Tablas" con links a páginas tabla.
- **Drawer móvil** — incluye links a tablas de cada tipo.
- **TipTapEditor** — @tiptap/vue-3 + StarterKit + Link + Placeholder. Toolbar: bold, italic, h2, h3, listas, blockquote, code. Debounce 1s.

### Endpoints API

```
GET  /api/gestion/proyectos          — ?tipo=&estado= (retorna todos los tipos si sin filtro)
GET  /api/gestion/proyectos/:id      — detalle con responsables y etiquetas
POST /api/gestion/proyectos          — crear {nombre, tipo, estado?, ...} (valida estado vs tipo)
PUT  /api/gestion/proyectos/:id      — actualizar (valida estado vs tipo)
DELETE /api/gestion/proyectos/:id    — desancla tareas y elimina
PUT  /api/gestion/jornadas/:id/pausas/:pausaId/editar — editar pausa individual
```

### Archivos eliminados
ProyectoModal.vue, DetalleDificultadPage, DetalleIdeaPage, DetallePendientePage, DetalleInformePage, DificultadesPage, IdeasPage, PendientesPage, InformesPage — todos reemplazados por ProyectoPanel + ItemsTablePage.

## Próximas fases pendientes

- [x] ~~Implementar Módulo Jornadas (Fase 3.5)~~ ✅ 2026-03-26
- [x] ~~Módulo Proyectos/Dificultades/Compromisos/Ideas~~ ✅ 2026-03-31
- [x] ~~Módulo Órdenes de Producción (vista detalle, sync, tiempos)~~ ✅ 2026-04-28
- [x] ~~Auto-update PWA con banner + botón manual~~ ✅ 2026-04-27
- [ ] **Unificar `TareaForm` y `TareaPanel`** — son dos componentes con orden similar; consolidar a uno solo (modo crear/editar)
- [ ] Push notifications FCM (Fase 4)
- [ ] APK Android (Fase 4)

## Skill de referencia

`.agent/skills/sistema_gestion.md` — skill disponible como `/sistema-gestion`
Detalle completo del módulo: `.agent/docs/sistema_gestion_tareas.md` (o `MEMORY.md` → sistema_gestion_tareas.md)

---

## Sesiones 2026-04-27 al 2026-04-29 — Bloque OPs + UX/UI completo

Trabajo intensivo en 3 frentes: (1) módulo Órdenes de Producción (panel detalle, sync, tiempos consolidados editables), (2) refactor sidebar nivel 3 a popover flotante (estilo HubSpot), (3) auto-update PWA y deuda técnica menor.

### Componentes nuevos
- **`OpPanel.vue`** — panel detalle de OP que se abre desde `/ops-tabla`. Materiales + Artículos producidos (lectura) + Tiempos consolidados (editables nivel ≥5) + Tareas vinculadas + Quickadd de tarea + Observaciones del lote + botones Procesar/Validar
- **`SidebarSubSeccion.vue`** — wrapper que renderiza header + slot. Decide si mostrar acordeón vertical (mobile, anterior comportamiento) o popover flotante (desktop, nuevo)
- **`CatProduccionSelector.vue`** — chip + q-menu reusable para seleccionar sub-categoría de producción. Reemplaza markup duplicado en TareaForm, TareaPanel y OpPanel

### Endpoints nuevos backend
```
POST   /api/gestion/op/sync                     SSE — refresh Effi (Playwright + import + sync VPS).
                                                Lock /tmp/sync_ops_effi.lock, TTL 10 min, 409 si en curso
GET    /api/gestion/op/:id_op/ficha             Detalle: cabecera + materiales + productos + tiempos +
                                                tareas_vinculadas + detalle. Si NO hay snapshot en
                                                g_op_tiempos → suma duracion_usuario_seg de tareas (modo vivo)
PUT    /api/gestion/op/:id_op/tiempos           Editar tiempos consolidados (nivel ≥5).
                                                Body: { tiempos: [{categoria_produccion_id, segundos}] }
                                                DELETE+INSERT en g_op_tiempos. Filas con seg≤0 se descartan.
                                                Si lista vacía → vuelve a modo "vivo"
PUT    /api/gestion/op/:id_op/detalle           Observaciones lote + responsable validado (UPSERT)
PUT    /api/gestion/op/:id_op/lineas/:lineaId   Actualizar cantidad_real de un material/producto
POST   /api/gestion/op/:id_op/lineas            Agregar línea no prevista (solo estado=Generada)
DELETE /api/gestion/op/:id_op/lineas/:lineaId   Solo líneas no previstas
POST   /api/gestion/op/:id_op/procesar          Cambia estado OP a Procesada en Effi (Playwright)
POST   /api/gestion/op/:id_op/validar           Anula OP + crea OP nueva con reales + Validado (~3 min)
```

### Cambios en endpoints existentes
- `GET /api/gestion/op` (lista de OPs):
  - LIMIT 500 → 5000 (caben las ~2229 actuales con margen)
  - **Filtro últimos 6 meses por defecto**: `WHERE fecha_de_creacion >= DATE_SUB(NOW(), INTERVAL 6 MONTH)` excepto si cliente pasa `?desde=`
- `GET /api/gestion/ops` (selector autocomplete):
  - SELECT incluye ahora `e.fecha_de_creacion` (antes solo `fecha_final`)
  - El selector ya muestra fecha de creación, no fecha de fin programado (bug v2.10.13)
- `/api/gestion/sugerir-categoria`:
  - Pista del IA actualizada: agregadas "Reuniones e informes" y "Desarrollo de producto" con keywords

### Sidebar refactor (nivel 3 → popover flotante)
**Antes** (≤ v2.9.x): cada sub-section en Mis Tareas / Equipo era un acordeón vertical con la lista de proyectos/dificultades/etc inline.

**Ahora** (≥ v2.10.0):
- En **desktop** (sidebar full ≥768px): click en el header del nivel 2 abre `q-menu` lateral con la lista (estilo HubSpot, ver `produccion/floating-submenu` como referencia visual)
- En **mobile** (drawer overlay): click abre `q-menu` debajo del header (anchor `bottom left`, no `top right`, para que no se salga del viewport del drawer)
- En **mini-mode** (sidebar 64px): comportamiento anterior intacto (popover en el item nivel 1)
- Chevron `>` a la **derecha** del header (antes a la izquierda)
- Hover sobre el header muestra highlight pero NO abre popover (evita aperturas accidentales)
- Click toggle abre/cierra popover; click fuera cierra (q-menu lo maneja solo)

Aplicado a 6 sub-secciones × 2 contextos (Mis Tareas + Equipo): Proyectos, Dificultades, Compromisos, Ideas, Órdenes de producción, Etiquetas.

### Tabla `/ops-tabla` (`OpTablePage.vue`)
- **Botón "Sincronizar Effi"** en la toolbar — dispara SSE a `/api/gestion/op/sync`. Notify "ongoing" arriba con paso actual del script Python (Exportando inventario, Exportando OPs, Importando, Sync VPS, ...). Al terminar OK recarga la tabla. Lock evita ejecuciones simultáneas.
- **Click en fila** abre `OpPanel` (panel lateral 540px desktop / full mobile)
- **OsDataTable**: filtro de columna default cambiado de `eq` ('Igual a') → `contains` ('Contiene'). Aplica globalmente a TODAS las tablas que usan OsDataTable en el sistema

### Auto-update PWA (v2.9.8-9)
- **Banner verde arriba** "Hay una nueva versión disponible — Actualizar" cuando el SW detecta versión nueva (chequeo cada 5 min). Reemplaza el reload silencioso anterior
- **Botón "Actualizar app"** en sidebar (debajo de Modo claro). Click → dialog confirmación → unregister SW + clear caches + reload. Útil cuando el usuario quiere forzar update sin esperar
- `register-service-worker.js`: el callback `updated` ahora dispara `CustomEvent('sw-updated')` en lugar de `location.reload()` directo. MainLayout escucha y muestra el banner

### TareaForm + TareaPanel — orden unificado (v2.10.17)
Antes: TareaForm (modal Nueva Tarea) tenía orden distinto a TareaPanel (detalle de tarea). Ahora ambos siguen el mismo orden:

1. Título
2. **TareaMetaChips** (categoría + prioridad + etiquetas + fecha + responsables + proyecto)
3. OP Effi (si Producción)
4. **Cat. producción** (si Producción)
5. **Detalles producción** (acordeón, si Producción)
6. Remisión / Pedido (si Empaque)
7. Descripción

**Deuda técnica restante**: los dos componentes son archivos separados — idealmente unificarlos en un solo componente con prop `modo: crear|editar`. Pendiente.

### Tiempos consolidados editables (v2.10.19-20)
Sección "Tiempos consolidados" en OpPanel:
- **Modo vista**: tabla con `Categoría | HH:MM:SS` + total. Tag arriba: "en vivo" (calculado de tareas) o "snapshot" (manual o validación)
- **Modo edición** (toggle "Editar", solo nivel ≥5):
  - Cada fila: `[select Categoría] [_h_]h [_m_]m [×]`
  - Botón `+ agregar tiempo` al final
  - Botones `Cancelar` / `Guardar`
  - Al guardar: PUT `/op/:id/tiempos` reemplaza completo en `g_op_tiempos`. La OP entra a modo snapshot
  - Si todas las filas se borran → `g_op_tiempos` queda vacío → vuelve al modo "vivo" (recalcula desde tareas)
- Inputs `[h]` y `[m]` separados (no `HH:MM:SS` un solo input) — más cómodo en mobile, sin caracteres especiales que escribir

### Bugs fijos
| Versión | Bug |
|---|---|
| v2.9.3 | Círculo del check de tareas invisible en modo claro (`rgba(255,255,255,0.50)` sobre fondo blanco) |
| v2.9.4 | Botones Procesar/Validar tapados por bottombar móvil — `padding-bottom: calc(80px + safe-area)` |
| v2.10.6 | Multi-action bar tapada por bottombar — `bottom: calc(65px + safe-area)` |
| v2.10.8 | Papelera del TareaPanel embebido en ProyectoPanel no eliminaba (faltaba `@eliminar` listener) |
| v2.10.11 | Tabla OPs solo mostraba Generadas (LIMIT 500 cortaba antes de Procesadas) |
| v2.10.14 | OpSelector mostraba `fecha_final` (fin programado) en lugar de `fecha_de_creacion` |
| v2.10.15 | TareaForm no mostraba Cat. producción + Detalles producción al seleccionar OP (solo aparecían al editar) |
| v2.10.17 | Tiempos consolidados sumaban `duracion_cronometro_seg` (raw) — ahora suman `duracion_usuario_seg` (confirmado por usuario) |
| v2.10.18 | Banner "Sincronizando..." se quedaba pegado tras terminar (notify dismiss no se llamaba) |

### Patrones técnicos importantes
- **Build PWA OBLIGATORIO**: usar `npm run build` (alias de `quasar build -m pwa`) NO `npx quasar build` (genera SPA sin sw.js → rompe PWAs instaladas). Ver `feedback_pwa_build_command.md`
- **Bottombar móvil ~53px de alto**: cualquier elemento `position: fixed; bottom: …` en mobile debe usar `calc(>53px + env(safe-area-inset-bottom, 0))`. Cualquier panel scrollable debe tener `padding-bottom` similar al final. Documentado en skill `quasar-layout` §12
- **Service Worker auto-update**: el SW chequea cada 5 min. Ver `feedback_pwa_build_command.md` para detalles del flujo banner+manual
- **Reuso de componentes 5S**: chips, selectores, panels — siempre buscar componente existente antes de duplicar markup. Ejemplo: `CatProduccionSelector` reemplaza ~26 líneas duplicadas en 3 archivos

### Lecciones (memoria)
- `feedback_alcance_minimo.md`: cuando me piden cambio visual sutil (ej. mover una flecha), NO refactorizar HTML adyacente. Caso `SidebarSubSeccion` v2.10.2-3-4: eliminé el icon decorativo del header sin que me pidieran y rompió la sangría visual
- `feedback_pwa_build_command.md`: validar SIEMPRE que `dist/pwa/sw.js` se generó tras un build. El comando `npx quasar build` (no PWA) deja PWAs instaladas pegadas
- `feedback_componente_compartido.md`: si voy a copiar markup a 2+ lugares → extraer componente PRIMERO, no después
