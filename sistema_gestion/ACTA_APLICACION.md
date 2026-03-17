# Acta de Construcción — Sistema Gestión OS

> **Propósito**: Registro definitivo de todas las decisiones de diseño, arquitectura y UX de esta aplicación.
> Cada decisión que se tome con Santi queda aquí. Es la fuente de verdad del producto.
> **Actualizar obligatoriamente** cada vez que se decida algo nuevo, se cambie algo existente o se descarte una opción.

---

## Historial de decisiones

| Fecha | Decisión |
|---|---|
| 2026-03-16 | Stack definido: Vue 3 + Quasar 2, Express 9300, Hostinger MySQL vía SSH tunnel |
| 2026-03-16 | Diseño TickTick-style: dark mode first, acento verde #00C853, densidad alta |
| 2026-03-16 | Auth: Google OAuth con GSI renderButton (no slots custom de vue3-google-login) |
| 2026-03-16 | JWT doble: temporal (>1 empresa) + final (empresa_activa) |
| 2026-03-16 | 3 pools MySQL separados — Hostinger no comparte usuarios entre BDs |
| 2026-03-16 | QuickAdd inline desktop (no modal para crear tarea rápida) |
| 2026-03-16 | TareaForm: bottom sheet en mobile, modal centrado en desktop |
| 2026-03-16 | OpSelector: solo OPs vigencia='Vigente' AND estado!='Procesada' |
| 2026-03-16 | 13 categorías globales (sin empresa) — aplican a todas las empresas |
| 2026-03-17 | **Proyectos**: campo `proyecto_id` en tareas, tabla `g_proyectos` propia |
| 2026-03-17 | **Proyectos**: NO jerarquía padre-hijo (descartado por problema de fechas en filtros diarios) |
| 2026-03-17 | **Proyectos**: tienen categoría + prioridad propias |
| 2026-03-17 | **Responsables de proyecto**: múltiples, tabla junction `g_proyectos_responsables` |
| 2026-03-17 | **Etiquetas**: sistema de tags para tareas Y proyectos, tabla `g_etiquetas` + 2 junctions |
| 2026-03-17 | **Proyectos en sidebar**: sección "PROYECTOS" con dot de color, crear inline con `+` |
| 2026-03-17 | **Detalle de proyecto**: panel/popup lateral (no página nueva) |
| 2026-03-17 | **Chip de proyecto en tarea**: badge pequeño de color en la fila |

---

## 1. Contexto general

**Nombre**: Sistema Gestión OS
**URL**: gestion.oscomunidad.com
**Propósito**: App de tareas y conocimiento del equipo (>5 personas). Reemplaza Notion.
**Plataformas**: Web + Android nativo (Capacitor — Fase 4)
**Puerto API**: 9300
**Directorio**: `Integraciones_OS/sistema_gestion/`

---

## 2. Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Vue 3 + Quasar 2 (SPA) |
| Mobile futuro | Capacitor 6 (Android) |
| API | Express.js, Node.js, puerto 9300 |
| BD propia | `u768061575_os_gestion` en Hostinger MySQL |
| BD usuarios | `u768061575_os_comunidad` (READ ONLY) |
| BD OPs | `u768061575_os_integracion` (READ ONLY) |
| Auth | Google OAuth (GSI renderButton) + JWT propio (2 pasos) |
| Conexión BD | SSH tunnel `~/.ssh/sos_erp` → `109.106.250.195:65002` |
| Systemd | `os-gestion.service` |
| Cloudflare | tunnel → gestion.oscomunidad.com |

---

## 3. Principios de diseño

### 3.1 Sistema de diseño
- **Dark mode first** — toggle por usuario guardado en `g_usuarios_config.tema`
- **Acento verde OS**: `#00C853` (≠ ERP que usa violeta `#5E6AD2`)
- **Densidad alta**: texto 13-14px, filas 44-48px, gaps 6-12px
- **Botón primario**: blanco con texto oscuro (igual que Linear)
- **Sin fondos de color** en filas normales — solo hover/seleccionado
- **Fuente**: Inter

### 3.2 Referencia visual
- Linear.app (estructura, densidad, grupos)
- TickTick (QuickAdd inline, listas con color, bottom sheet mobile)
- Manual completo: `sistema_gestion/MANUAL_DISENO_HIBRIDO.md`

### 3.3 Layout
- **Desktop**: sidebar fijo 240px + contenido principal
- **Mobile**: topbar sticky + hamburger + drawer + FAB verde bottom-right
- Breakpoint: 768px

---

## 4. Base de datos — Schema completo `u768061575_os_gestion`

### Convenciones de campos
- **Auditoría**: `usuario_creador`, `usuario_ult_modificacion`, `fecha_creacion` (DATETIME), `fecha_ult_modificacion` (DATETIME ON UPDATE)
- **Estado**: VARCHAR(50) con valores en español con mayúscula — NO ENUM (facilita agregar valores sin ALTER)
- **PK**: `id` INT AUTO_INCREMENT
- **Multi-tenant**: campo `empresa` VARCHAR(50) en todas las tablas (excepto tablas globales como `g_categorias`)
- **Prioridad**: VARCHAR(50) — 'Baja', 'Media', 'Alta', 'Urgente'

---

### g_categorias ✅ creada — seed 13 registros
Catálogo global de categorías (sin empresa — aplican a todas).

| Campo | Tipo | Notas |
|---|---|---|
| id | INT PK | |
| nombre | VARCHAR(100) | 'Ventas', 'Produccion', etc. |
| color | VARCHAR(20) | hex, ej: '#2979FF' |
| icono | VARCHAR(50) | nombre Material Icons |
| es_produccion | TINYINT(1) | si muestra campo OP al crear tarea |
| activa | TINYINT(1) | |
| orden | INT | orden en la UI |
| usuario_creador | VARCHAR(255) | |
| usuario_ult_modificacion | VARCHAR(255) | |
| fecha_creacion | DATETIME | |
| fecha_ult_modificacion | DATETIME | |

**13 categorías seed:**
```
Ventas #2979FF | Cartera #00BCD4 | Produccion #FF6D00 (es_produccion=1)
Logistica #8BC34A | Administrativo #9C27B0 | Informes #607D8B
Contenido_y_Marca #E91E63 | Sistemas #7C4DFF | Mantenimiento #FF9800
Orden_y_Aseo #4CAF50 | Reuniones #03A9F4 | Varios #795548 | Empaque #009688
```

---

### g_perfiles ✅ creada — seed 5 registros
Roles de la app de gestión (define qué categorías ve cada usuario en sidebar y formularios).

| Perfil | es_admin | Categorías |
|---|---|---|
| Director | 1 (admin) | Todas (13) |
| Comercial | 0 | Ventas, Cartera, Logistica, Administrativo, Informes, Contenido_y_Marca, Reuniones, Varios |
| Produccion | 0 | Produccion, Logistica, Mantenimiento, Orden_y_Aseo, Empaque |
| Logistica | 0 | Logistica, Mantenimiento, Orden_y_Aseo, Empaque |
| Sistemas | 0 | Administrativo, Sistemas, Mantenimiento, Varios |

---

### g_categorias_perfiles ✅ creada
Junction muchos-a-muchos: perfil ↔ categoría.

---

### g_usuarios_config ✅ creada
Config personal del usuario dentro del módulo.

| Campo | Tipo | Notas |
|---|---|---|
| email | VARCHAR(255) PK | ref a sys_usuarios.Email |
| tema | VARCHAR(10) | 'dark' / 'light' |
| token_fcm | TEXT | push notifications (Fase 4) |
| perfil | VARCHAR(50) | ref a g_perfiles.nombre |
| usuario_ult_modificacion | VARCHAR(255) | |
| fecha_ult_modificacion | DATETIME | |

---

### g_proyectos 🔲 pendiente crear
Proyectos/temas de largo plazo. Las tareas se vinculan opcionalmente a un proyecto.

**Decisión clave**: NO hay jerarquía padre-hijo entre tareas. Un proyecto es solo una etiqueta agrupadora con metadata. Las tareas mantienen sus propias fechas sin heredar del proyecto.

| Campo | Tipo | Notas |
|---|---|---|
| id | INT PK AUTO_INCREMENT | |
| empresa | VARCHAR(50) NOT NULL | multi-tenant |
| nombre | VARCHAR(200) NOT NULL | |
| descripcion | TEXT | opcional |
| color | VARCHAR(20) | hex, ej: '#7C4DFF' — para el dot en sidebar |
| categoria_id | INT | FK g_categorias (nullable) |
| prioridad | VARCHAR(50) | 'Baja', 'Media', 'Alta', 'Urgente' |
| estado | VARCHAR(50) | 'Activo', 'Pausado', 'Completado' — default 'Activo' |
| fecha_estimada_fin | DATE | opcional |
| usuario_creador | VARCHAR(255) | |
| usuario_ult_modificacion | VARCHAR(255) | |
| fecha_creacion | DATETIME | |
| fecha_ult_modificacion | DATETIME | |

---

### g_proyectos_responsables 🔲 pendiente crear
Responsables múltiples de un proyecto (junction).

| Campo | Tipo | Notas |
|---|---|---|
| id | INT PK | |
| proyecto_id | INT | FK g_proyectos ON DELETE CASCADE |
| email | VARCHAR(255) | ref a sys_usuarios.Email |
| UNIQUE | (proyecto_id, email) | sin duplicados |

---

### g_etiquetas 🔲 pendiente crear
Tags libres para tareas Y proyectos. Por empresa.

| Campo | Tipo | Notas |
|---|---|---|
| id | INT PK AUTO_INCREMENT | |
| empresa | VARCHAR(50) NOT NULL | |
| nombre | VARCHAR(100) NOT NULL | ej: 'urgente', 'bloqueado', 'esperando respuesta' |
| color | VARCHAR(20) | hex — opcional, puede ser null |
| usuario_creador | VARCHAR(255) | |
| fecha_creacion | DATETIME | |
| UNIQUE | (empresa, nombre) | sin duplicados por empresa |

---

### g_etiquetas_tareas 🔲 pendiente crear
Junction: tarea ↔ etiqueta.

| Campo | Tipo | Notas |
|---|---|---|
| tarea_id | INT | FK g_tareas ON DELETE CASCADE |
| etiqueta_id | INT | FK g_etiquetas ON DELETE CASCADE |
| PRIMARY KEY | (tarea_id, etiqueta_id) | |

---

### g_etiquetas_proyectos 🔲 pendiente crear
Junction: proyecto ↔ etiqueta.

| Campo | Tipo | Notas |
|---|---|---|
| proyecto_id | INT | FK g_proyectos ON DELETE CASCADE |
| etiqueta_id | INT | FK g_etiquetas ON DELETE CASCADE |
| PRIMARY KEY | (proyecto_id, etiqueta_id) | |

---

### g_tareas ✅ creada — agregar campo proyecto_id
Entidad central.

| Campo | Tipo | Notas |
|---|---|---|
| id | INT PK | |
| empresa | VARCHAR(50) | |
| titulo | VARCHAR(300) | |
| descripcion | LONGTEXT | TipTap en Fase futura |
| categoria_id | INT | FK g_categorias |
| **proyecto_id** | **INT nullable** | **FK g_proyectos — NUEVO** |
| estado | VARCHAR(50) | 'Pendiente', 'En Progreso', 'Completada', 'Cancelada' |
| prioridad | VARCHAR(50) | 'Baja', 'Media', 'Alta', 'Urgente' |
| responsable | VARCHAR(255) | email — 1 responsable por tarea |
| fecha_limite | DATE | "¿Para cuándo?" — campo principal de fecha |
| fecha_inicio_estimada | DATETIME | avanzado, opcional |
| fecha_fin_estimada | DATETIME | avanzado, opcional |
| fecha_inicio_real | DATETIME | se llena al iniciar cronómetro |
| fecha_fin_real | DATETIME | se llena al completar |
| id_op | VARCHAR(50) | OP Effi (solo si categoría es_produccion=1) |
| tiempo_real_min | INT | suma total del cronómetro |
| tiempo_estimado_min | INT | estimado manual opcional |
| notas | TEXT | notas rápidas |
| usuario_creador | VARCHAR(255) | |
| usuario_ult_modificacion | VARCHAR(255) | |
| fecha_creacion | DATETIME | |
| fecha_ult_modificacion | DATETIME | |

---

### g_tarea_tiempo ✅ creada
Sesiones individuales del cronómetro.

| Campo | Notas |
|---|---|
| id, tarea_id, usuario | |
| inicio (DATETIME) | al iniciar |
| fin (DATETIME) | al detener |
| duracion_min (INT) | calculado: fin - inicio |

**Flujo cronómetro:**
```
INICIAR   → INSERT g_tarea_tiempo(inicio=NOW()), estado='En Progreso'
DETENER   → UPDATE fin=NOW(), duracion_min=TIMESTAMPDIFF(MINUTE, inicio, fin)
            UPDATE g_tareas.tiempo_real_min = SUM(duracion_min) WHERE tarea_id=?
COMPLETAR → cierra registro abierto + estado='Completada', fecha_fin_real=NOW()
```

---

### g_dificultades, g_ideas_hechos, g_pendientes, g_informes ✅ creadas
Módulos secundarios. Estructura estándar con empresa + campos propios + auditoría.
Implementación UI pendiente (Fase 3).

---

## 5. UX — Módulo Tareas

### 5.1 Vista principal (TareasPage)
- Lista agrupada por **categoría** (header con dot de color de la categoría)
- Chips de filtros scrolleables arriba: Hoy | Mañana | Ayer | Esta semana | Mis tareas | Pendientes
- Agrupación alternativa por **proyecto** (pendiente implementar)

### 5.2 Fila de tarea
```
[estado] [dot-cat] [titulo ..........] [chip-proyecto?] [prioridad] [responsable] [fecha]
```
- `chip-proyecto`: pequeño badge con color del proyecto, solo si tiene proyecto asignado
- `dot-cat`: 8px, color de la categoría
- `estado`: círculo Linear-style (vacío=pendiente, check=completada, X=cancelada)
- `fecha`: roja si vencida

### 5.3 QuickAdd inline (desktop)
- Se activa desde botón "+ Nueva tarea" en topbar
- Se inserta al inicio de la lista con animación fadeIn
- Enter guarda, Escape cancela
- Campos: título (requerido) + categoría chips + proyecto (dropdown) + fecha

### 5.4 TareaForm (modal desktop / bottom sheet mobile)
- **Campos**: título, categoría (chips), proyecto (selector), OP Effi (si es_produccion), fecha_limite, responsable, prioridad, descripción, etiquetas
- Responsable: dropdown de usuarios de la empresa
- Etiquetas: selector multi-select con opción de crear nueva inline
- OP Effi: solo visible si la categoría seleccionada tiene `es_produccion=1`

---

## 6. UX — Módulo Proyectos

### 6.1 Sidebar
```
PROYECTOS
  ● App Gestión OS      ← dot con color del proyecto + nombre
  ● Página web
  ● Proceso empaque
  + Nuevo proyecto      ← inline: solo pide nombre y color
```

### 6.2 Crear proyecto rápido
- Clic en `+ Nuevo proyecto` → popup/inline en el sidebar: solo nombre + selector de color (8 colores predefinidos)
- Campos opcionales se completan después en el panel de detalle

### 6.3 Panel de detalle del proyecto
Al hacer clic en el nombre del proyecto (no en el dot):
- Abre panel lateral derecho (desktop) o bottom sheet (mobile)
- Contenido:
  - Nombre (editable inline)
  - Descripción
  - Categoría + Prioridad + Estado
  - Fecha estimada de fin
  - Responsables (multi-select de usuarios)
  - Etiquetas
  - Progreso: "N/M tareas completadas" (calculado en query)
  - Botón "Ver todas las tareas" → filtra TareasPage por este proyecto

### 6.4 Vista de tareas por proyecto
- Clic en proyecto en sidebar → misma TareasPage pero filtrada por `proyecto_id`
- Header muestra nombre del proyecto + dot de color
- Botón "← Todas las tareas" para volver

### 6.5 Chip de proyecto en la fila de tarea
```css
.chip-proyecto {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: <color-proyecto>/15;  /* color del proyecto con 15% opacidad */
  color: <color-proyecto>;
  font-weight: 500;
}
```

---

## 7. UX — Sistema de Etiquetas

### 7.1 Comportamiento
- Las etiquetas son tags libres por empresa (no globales)
- Una tarea o proyecto puede tener N etiquetas
- Se pueden crear nuevas etiquetas inline al asignar (sin salir del form)
- Ejemplos: 'bloqueado', 'esperando respuesta', 'revisión', 'Q1-2026'

### 7.2 Visualización
- En la fila de tarea: chips pequeños de color debajo/junto al título (solo si tiene etiquetas)
- En el sidebar: posible filtro por etiqueta (futura)

### 7.3 Componente EtiquetasSelector (pendiente crear)
- Multi-select con autocomplete
- Muestra etiquetas existentes de la empresa
- Opción "+ Crear '[texto]'" si no existe
- Al crear: nombre + color (opcional)

---

## 8. Auth y multi-empresa

### 8.1 Flujo completo
```
1. Google id_token → POST /api/auth/google
2. Backend valida con tokeninfo?id_token=...
3. SELECT sys_usuarios WHERE Email=? AND estado='Activo'
4. SELECT sys_usuarios_empresas JOIN sys_empresa WHERE usuario=? AND e.estado='Activa'
5. 0 empresas → 403 | 1 empresa → JWT final | >1 empresa → JWT temporal + selector
6. JWT final guardado en localStorage 'gestion_jwt'
```

### 8.2 JWT payload
```json
{
  "tipo": "final",
  "email": "usuario@gmail.com",
  "nombre": "Nombre_Usuario",
  "empresa_activa": "Ori_Sil_2",
  "iat": ..., "exp": ...
}
```

### 8.3 Router guard
Verifica `payload.tipo === 'final'` antes de permitir acceso a rutas protegidas.

---

## 9. Endpoints API

### Activos
```
POST /api/auth/google
POST /api/auth/seleccionar_empresa
GET  /api/auth/me
GET  /api/usuarios
GET  /api/gestion/categorias
GET  /api/gestion/tareas          ?filtro=hoy|manana|semana|mis&estado=&categoria_id=&proyecto_id=
POST /api/gestion/tareas
PUT  /api/gestion/tareas/:id
GET  /api/gestion/ops             ?q=
GET  /api/gestion/op/:id
```

### Pendientes
```
DELETE /api/gestion/tareas/:id
POST   /api/gestion/tareas/:id/iniciar
POST   /api/gestion/tareas/:id/detener
POST   /api/gestion/tareas/:id/completar
GET    /api/gestion/proyectos
POST   /api/gestion/proyectos
PUT    /api/gestion/proyectos/:id
DELETE /api/gestion/proyectos/:id
GET    /api/gestion/etiquetas
POST   /api/gestion/etiquetas
```

---

## 10. Decisiones descartadas (y por qué)

| Opción | Razón del descarte |
|---|---|
| Subtareas con jerarquía padre-hijo | Los filtros por fecha (Hoy/Ayer/Mañana) dejan subtareas varadas en su fecha original. Cambiarlas es engorroso diariamente. |
| AppSheet para mobile | Demasiado engorroso y limitado para Santi — descartado en etapa de evaluación. |
| vue3-google-login con slot custom | `response.credential` llega undefined. Reemplazado por GSI `renderButton`. |
| `app.get('*')` en Express 5 | `path-to-regexp` v8 no acepta wildcard. Reemplazado por `app.use()` al final. |
| JOIN cross-database en Hostinger | Cada usuario MySQL solo accede a su BD. Se hacen 2 queries separados y se combina en JS. |

---

## 11. Próximos pasos (prioridad)

### Inmediato — Schema BD
- [ ] Crear tabla `g_proyectos` en Hostinger
- [ ] Crear tabla `g_proyectos_responsables`
- [ ] Crear tabla `g_etiquetas`
- [ ] Crear tabla `g_etiquetas_tareas`
- [ ] Crear tabla `g_etiquetas_proyectos`
- [ ] ALTER TABLE `g_tareas` ADD COLUMN `proyecto_id` INT NULL FK

### Backend
- [ ] Endpoints CRUD proyectos
- [ ] Endpoint `GET /api/gestion/proyectos` (con conteo de tareas y progreso)
- [ ] Endpoints CRUD etiquetas
- [ ] Filtro `?proyecto_id=` en GET /api/gestion/tareas
- [ ] Endpoint cronómetro (iniciar/detener/completar)

### Frontend
- [ ] ProyectoSelector.vue — dropdown en TareaForm
- [ ] Sección PROYECTOS en el sidebar con dot de color
- [ ] Crear proyecto rápido inline en sidebar
- [ ] ProyectoPanel.vue — panel lateral de detalle
- [ ] EtiquetasSelector.vue — multi-select con crear inline
- [ ] Chip de proyecto en fila de tarea
- [ ] Filtros chips: Hoy / Mañana / Esta semana / Mis tareas
- [ ] TareaPanel.vue — panel lateral de detalle de tarea (desktop)
- [ ] Cronometro.vue

---

*Última actualización: 2026-03-17 — Santi + Claude Code*
