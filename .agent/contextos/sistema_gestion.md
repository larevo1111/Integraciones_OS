# Contexto: Sistema Gestión OS
**Actualizado**: 2026-03-23

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

## Próximas fases pendientes

- [ ] Módulos secundarios: Dificultades, Ideas, Pendientes, Informes
- [ ] Push notifications FCM (Fase 4)
- [ ] APK Android (Fase 4)

## Skill de referencia

`.agent/skills/sistema_gestion.md` — skill disponible como `/sistema-gestion`
Detalle completo del módulo: `.agent/docs/sistema_gestion_tareas.md` (o `MEMORY.md` → sistema_gestion_tareas.md)
