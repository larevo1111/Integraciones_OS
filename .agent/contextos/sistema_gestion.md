# Contexto: Sistema Gestión OS
**Actualizado**: 2026-03-26

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
| Build prod | `cd sistema_gestion/app && npx quasar build` |
| Dev frontend | `cd sistema_gestion/app && npx quasar dev` (puerto 9301) |
| Manual diseño | `sistema_gestion/MANUAL_DISENO_HIBRIDO.md` |
| Cloudflare | Tunnel activo |

## Credenciales BD (3 pools en server.js)

| Pool | BD | Usuario | Pass |
|---|---|---|---|
| poolComunidad | `u768061575_os_comunidad` | `u768061575_ssierra047` | `Epist2487.` |
| poolGestion | `u768061575_os_gestion` | `u768061575_os_gestion` | `Epist2487.` |
| poolIntegracion | `u768061575_os_integracion` | `u768061575_osserver` | `Epist2487.` |

Hostinger NO permite compartir usuario MySQL entre BDs — cada BD tiene su propio usuario.

## Tablas en `u768061575_os_gestion`

| Tabla | Descripción |
|---|---|
| `g_categorias` | 13 seeds con color e icono. Campo `es_empaque` para categoría Empaque |
| `g_tareas` | Tareas con id_remision, id_pedido, cronómetro |
| `g_tarea_tiempo` | Sesiones de cronómetro |
| `g_usuarios_config` | Configuración por usuario |
| `g_perfiles` | Perfiles de usuario |
| `g_categorias_perfiles` | Relación categorías-perfiles |
| `g_proyectos` | Proyectos con nombre y color |
| `g_proyectos_responsables` | Relación proyectos-usuarios |
| `g_etiquetas` | Etiquetas de la empresa |
| `g_etiquetas_tareas` | Relación etiquetas-tareas |
| `g_etiquetas_proyectos` | Relación etiquetas-proyectos |

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
GET  /api/gestion/proyectos              — ?estado=Activo. retorna tareas_pendientes
POST /api/gestion/proyectos              — crear {nombre, color?}
PUT  /api/gestion/proyectos/:id          — actualizar
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

## Próximas fases pendientes

- [x] ~~Implementar Módulo Jornadas (Fase 3.5)~~ ✅ 2026-03-26
- [ ] Módulos secundarios: Dificultades, Ideas, Pendientes, Informes
- [ ] Push notifications FCM (Fase 4)
- [ ] APK Android (Fase 4)

## Skill de referencia

`.agent/skills/sistema_gestion.md` — skill disponible como `/sistema-gestion`
Detalle completo del módulo: `.agent/docs/sistema_gestion_tareas.md` (o `MEMORY.md` → sistema_gestion_tareas.md)
