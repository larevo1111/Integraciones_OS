# Plan: Sistema de Gestión OS
**Estado**: 🟡 En construcción — Fase 1: BD ✅ completa
**Fecha inicio**: 2026-03-16
**URL destino**: gestion.oscomunidad.com
**Directorio**: `Integraciones_OS/sistema_gestion/`

---

## Objetivo
App de gestión de tareas y conocimiento del equipo — complemento anclado al ERP OS. Reemplaza Notion. Corre en web y Android (Capacitor). >5 usuarios. Multi-empresa.

---

## Arquitectura de BDs

| BD | Acceso | Propósito |
|---|---|---|
| `u768061575_os_comunidad` | READ ONLY | Usuarios, empresas (sys_usuarios, sys_empresa, sys_usuarios_empresas) |
| `u768061575_os_gestion` | READ/WRITE | Datos propios del módulo (tablas g_*) |
| `u768061575_os_integracion` | READ ONLY | OPs de producción (zeffi_produccion_encabezados) |

**Conexión**: SSH tunnel `~/.ssh/sos_erp` → `109.106.250.195:65002` → MySQL 3306
**Credenciales BD gestion**: user=`u768061575_os_gestion`, pass=`Epist2487.`

## Convención de campos (=SOS_ERP `u768061575_os_comunidad`)
- Auditoria: `usuario_creador`, `usuario_ult_modificacion`, `fecha_creacion` (DATETIME), `fecha_ult_modificacion` (DATETIME)
- Estado: VARCHAR(50) con valores en español con mayúscula ('Pendiente', 'Activo', etc.) — NO ENUM
- PK operacional: `id` INT AUTO_INCREMENT
- FK empresa: `empresa` VARCHAR(50) → referencia a `sys_empresa.uid`
- Prioridad: VARCHAR(50) — 'Baja', 'Media', 'Alta', 'Urgente' (todas las tablas excepto g_informes)

---

## Schema BD `u768061575_os_gestion`

### g_usuarios_config
Config personal del usuario dentro del módulo de gestión.
```sql
CREATE TABLE g_usuarios_config (
  email                    VARCHAR(255) NOT NULL,
  tema                     VARCHAR(10) DEFAULT 'dark',
  token_fcm                TEXT,
  perfil                   VARCHAR(50) DEFAULT NULL,         -- ref a g_perfiles.nombre
  usuario_ult_modificacion VARCHAR(255),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
**Propósito**: config específica del módulo de gestión por usuario. NO duplica sys_usuarios — solo guarda tema, FCM token, perfil activo. El perfil filtra qué categorías ve el usuario en el sidebar y formularios.

### g_perfiles
Perfiles/roles de la app de gestión (define qué categorías ve cada usuario).
```sql
CREATE TABLE g_perfiles (
  id                       INT NOT NULL AUTO_INCREMENT,
  nombre                   VARCHAR(100) NOT NULL,
  descripcion              VARCHAR(300) DEFAULT NULL,
  es_admin                 TINYINT(1) DEFAULT 0,
  activo                   TINYINT(1) DEFAULT 1,
  orden                    INT DEFAULT 0,
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Seed perfiles:**
| Perfil | es_admin | Categorías que ve |
|---|---|---|
| Director | 1 | Todas (13 categorías) |
| Comercial | 0 | Ventas, Cartera, Logistica, Administrativo, Informes, Contenido_y_Marca, Reuniones, Varios |
| Produccion | 0 | Produccion, Logistica, Mantenimiento, Orden_y_Aseo, Empaque |
| Logistica | 0 | Logistica, Mantenimiento, Orden_y_Aseo, Empaque |
| Sistemas | 0 | Administrativo, Sistemas, Mantenimiento, Varios |

### g_categorias_perfiles
Junction table muchos-a-muchos: perfil ↔ categoría.
```sql
CREATE TABLE g_categorias_perfiles (
  id           INT NOT NULL AUTO_INCREMENT,
  perfil_id    INT NOT NULL,
  categoria_id INT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_perfil_categoria (perfil_id, categoria_id),
  CONSTRAINT fk_cp_perfil    FOREIGN KEY (perfil_id)    REFERENCES g_perfiles (id) ON DELETE CASCADE,
  CONSTRAINT fk_cp_categoria FOREIGN KEY (categoria_id) REFERENCES g_categorias (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### g_categorias
Catálogo global de categorías de tareas (sin empresa — aplican a todo el sistema).
```sql
CREATE TABLE g_categorias (
  id                       INT NOT NULL AUTO_INCREMENT,
  nombre                   VARCHAR(100) NOT NULL,
  color                    VARCHAR(20) NOT NULL,
  icono                    VARCHAR(50) DEFAULT NULL,
  es_produccion            TINYINT(1) DEFAULT 0,
  activa                   TINYINT(1) DEFAULT 1,
  orden                    INT DEFAULT 0,
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### g_tareas
Entidad central del módulo.
```sql
CREATE TABLE g_tareas (
  id                       INT NOT NULL AUTO_INCREMENT,
  empresa                  VARCHAR(50) NOT NULL,
  titulo                   VARCHAR(300) NOT NULL,
  descripcion              LONGTEXT DEFAULT NULL,
  categoria_id             INT NOT NULL,
  estado                   VARCHAR(50) DEFAULT 'Pendiente',
  prioridad                VARCHAR(50) DEFAULT 'Media',
  responsable              VARCHAR(255) DEFAULT NULL,        -- email (default = usuario_creador)
  fecha_limite             DATE DEFAULT NULL,               -- fecha única simple (frontend: "¿Para cuándo?")
  fecha_inicio_estimada    DATETIME DEFAULT NULL,           -- avanzado: rango estimado
  fecha_fin_estimada       DATETIME DEFAULT NULL,           -- = fecha_inicio_estimada si no se separa
  fecha_inicio_real        DATETIME DEFAULT NULL,           -- se llena al completar
  fecha_fin_real           DATETIME DEFAULT NULL,           -- se llena al completar
  id_op                    VARCHAR(50) DEFAULT NULL,        -- OP Effi (solo es_produccion=1)
  tiempo_real_min          INT DEFAULT 0,                   -- suma total del cronómetro (autoritativo)
  tiempo_estimado_min      INT DEFAULT NULL,                -- estimado manual
  notas                    TEXT DEFAULT NULL,
  usuario_creador          VARCHAR(255) NOT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  KEY idx_empresa (empresa),
  KEY idx_responsable (empresa, responsable),
  KEY idx_fecha (empresa, fecha_limite),
  KEY idx_estado (empresa, estado),
  CONSTRAINT fk_tarea_categoria FOREIGN KEY (categoria_id) REFERENCES g_categorias (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Lógica de fechas (UX simplificada):**
- El usuario solo elige una fecha ("¿Para cuándo?") → se guarda en `fecha_limite` Y en `fecha_fin_estimada` = `fecha_inicio_estimada`
- Usuarios avanzados pueden separar inicio/fin estimado
- Al completar la tarea → popup pregunta tiempo real → se llena `fecha_fin_real` = NOW(), `fecha_inicio_real` si no estaba

### g_tarea_tiempo
Registros del cronómetro por tarea (sesiones individuales de trabajo).
```sql
CREATE TABLE g_tarea_tiempo (
  id             INT NOT NULL AUTO_INCREMENT,
  tarea_id       INT NOT NULL,
  usuario        VARCHAR(255) DEFAULT NULL,
  inicio         DATETIME NOT NULL,
  fin            DATETIME DEFAULT NULL,
  duracion_min   INT DEFAULT NULL,               -- calculado al detener (fin - inicio)
  fecha_creacion DATETIME DEFAULT NOW(),
  PRIMARY KEY (id),
  KEY idx_tarea (tarea_id),
  CONSTRAINT fk_tiempo_tarea FOREIGN KEY (tarea_id) REFERENCES g_tareas (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Flujo cronómetro:**
```
INICIAR   → INSERT g_tarea_tiempo(inicio=NOW(), fin=NULL), estado='En Progreso'
DETENER   → UPDATE g_tarea_tiempo SET fin=NOW(), duracion_min=(fin-inicio)
             UPDATE g_tareas SET tiempo_real_min = (SELECT SUM(duracion_min) FROM g_tarea_tiempo WHERE tarea_id=?)
CONTINUAR → INSERT nuevo registro, timer sigue
COMPLETAR → cierra registro abierto + UPDATE estado='Completada', fecha_fin_real=NOW()
```
`g_tarea_tiempo` es invisible al usuario — solo botón Start/Stop. `tiempo_real_min` en `g_tareas` es el valor final editable.

### g_dificultades
Banco de dificultades y estrategias.
```sql
CREATE TABLE g_dificultades (
  id                       INT NOT NULL AUTO_INCREMENT,
  empresa                  VARCHAR(50) NOT NULL,
  titulo                   VARCHAR(300) NOT NULL,
  descripcion              LONGTEXT DEFAULT NULL,
  estrategia               LONGTEXT DEFAULT NULL,
  categoria                VARCHAR(100) DEFAULT NULL,
  estado                   VARCHAR(50) DEFAULT 'Abierta',
  prioridad                VARCHAR(50) DEFAULT 'Media',
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  KEY idx_empresa (empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### g_ideas_hechos
Ideas nuevas y hechos relevantes.
```sql
CREATE TABLE g_ideas_hechos (
  id                       INT NOT NULL AUTO_INCREMENT,
  empresa                  VARCHAR(50) NOT NULL,
  titulo                   VARCHAR(300) NOT NULL,
  tipo                     VARCHAR(20) NOT NULL,             -- 'Idea' | 'Hecho'
  prioridad                VARCHAR(50) DEFAULT 'Media',
  descripcion              LONGTEXT DEFAULT NULL,
  categoria                VARCHAR(100) DEFAULT NULL,
  es_contenido             TINYINT(1) DEFAULT 0,            -- activa campos de contenido
  pilar_contenido          VARCHAR(200) DEFAULT NULL,       -- solo si es_contenido=1
  tipo_contenido           VARCHAR(100) DEFAULT NULL,       -- solo si es_contenido=1
  fecha                    DATE DEFAULT NULL,
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  KEY idx_empresa (empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Campos de contenido** (visibles solo si `es_contenido=1`):
- `pilar_contenido`: pilar estratégico de contenido de la empresa
- `tipo_contenido`: formato del contenido (Reel, Post, Blog, etc.)

### g_pendientes
Pendientes y compromisos del equipo.
```sql
CREATE TABLE g_pendientes (
  id                       INT NOT NULL AUTO_INCREMENT,
  empresa                  VARCHAR(50) NOT NULL,
  titulo                   VARCHAR(300) NOT NULL,
  descripcion              LONGTEXT DEFAULT NULL,
  categoria                VARCHAR(100) DEFAULT NULL,
  responsable              VARCHAR(255) DEFAULT NULL,
  estado                   VARCHAR(50) DEFAULT 'Pendiente',
  prioridad                VARCHAR(50) DEFAULT 'Media',
  fecha_limite             DATE DEFAULT NULL,
  fecha_completado         DATETIME DEFAULT NULL,
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  KEY idx_empresa (empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### g_informes
Informes semanales y mensuales del equipo. (sin campo prioridad — es documentación)
```sql
CREATE TABLE g_informes (
  id                       INT NOT NULL AUTO_INCREMENT,
  empresa                  VARCHAR(50) NOT NULL,
  nombre                   VARCHAR(300) NOT NULL,
  tipo                     VARCHAR(20) NOT NULL,             -- 'Semanal' | 'Mensual'
  fecha_informe            DATE DEFAULT NULL,
  contenido                LONGTEXT DEFAULT NULL,
  usuario_creador          VARCHAR(255) DEFAULT NULL,
  usuario_ult_modificacion VARCHAR(255) DEFAULT NULL,
  fecha_creacion           DATETIME DEFAULT NOW(),
  fecha_ult_modificacion   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  KEY idx_empresa (empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Seed — 13 categorías
```sql
INSERT INTO g_categorias (nombre, color, icono, es_produccion, orden, usuario_creador) VALUES
('Ventas',            '#2979FF', 'point_of_sale',          0,  1, 'sistema'),
('Cartera',           '#00BCD4', 'account_balance',        0,  2, 'sistema'),
('Produccion',        '#FF6D00', 'precision_manufacturing', 1,  3, 'sistema'),
('Logistica',         '#8BC34A', 'local_shipping',         0,  4, 'sistema'),
('Administrativo',    '#9C27B0', 'admin_panel_settings',   0,  5, 'sistema'),
('Informes',          '#607D8B', 'bar_chart',              0,  6, 'sistema'),
('Contenido_y_Marca', '#E91E63', 'campaign',               0,  7, 'sistema'),
('Sistemas',          '#7C4DFF', 'computer',               0,  8, 'sistema'),
('Mantenimiento',     '#FF9800', 'build',                  0,  9, 'sistema'),
('Orden_y_Aseo',      '#4CAF50', 'cleaning_services',      0, 10, 'sistema'),
('Reuniones',         '#03A9F4', 'groups',                 0, 11, 'sistema'),
('Varios',            '#795548', 'category',               0, 12, 'sistema'),
('Empaque',           '#009688', 'inventory_2',            0, 13, 'sistema');
```

---

## Usuarios del sistema (Origen Silvestre)
Del ERP `u768061575_os_comunidad.sys_usuarios` — empresa `Ori_Sil_2`:
| Email | Nombre | Nivel | Perfil sugerido |
|---|---|---|---|
| larevo1111@gmail.com | Santiago | 9 | Director |
| jennifercanogarcia@gmail.com | Jennifer Cano | 5 | Comercial |
| amaragonzalez21valen@gmail.com | Deivy Gonzales | 3 | Produccion |
| doblessas@gmail.com | Doble S | 3 | Produccion |
| rialgar82@gmail.com | Ricardo Garcia | 3 | Produccion |
| ssierra047@gmail.com | - | 7 | Sistemas |

---

## Checklist de construcción

### PASO PREVIO ✅ (Santi lo hizo)
- [x] P.1 Crear BD `u768061575_os_gestion` en cPanel Hostinger
- [x] P.2 Usuario `u768061575_os_gestion` con ALL PRIVILEGES
- [x] P.3 Remote access habilitado

### Fase 1 — Base de datos ✅ COMPLETA
- [x] 1.1 Verificar conexión SSH → `u768061575_os_gestion`
- [x] 1.2 Crear 8 tablas operativas: g_usuarios_config, g_categorias, g_tareas, g_tarea_tiempo, g_dificultades, g_ideas_hechos, g_pendientes, g_informes
- [x] 1.3 Seed 13 categorías
- [x] 1.4 Crear tablas de perfiles: g_perfiles + g_categorias_perfiles
- [x] 1.5 Seed 5 perfiles con sus categorías (Director, Comercial, Produccion, Logistica, Sistemas)
- [x] 1.6 Ajustes de schema: prioridad en todas las tablas, campos de contenido en ideas, fechas reales/estimadas en tareas, responsable en tareas y pendientes

### Fase 2 — API Express (9300)
- [ ] 2.1 Crear `sistema_gestion/api/` — init npm + dependencias
- [ ] 2.2 `db.js` — SSH tunnel + 3 pools (comunidad/gestion/integracion)
- [ ] 2.3 `server.js` — auth Google OAuth (leyendo sys_usuarios) + JWT 2 pasos
- [ ] 2.4 Endpoints: auth + usuarios + tareas + cronómetro + OP lookup
- [ ] 2.5 Endpoints: dificultades, ideas, pendientes, informes
- [ ] 2.6 systemd `os-gestion.service` — puerto 9300
- [ ] 2.7 Cloudflare — agregar gestion.oscomunidad.com

### Fase 3 — Frontend Vue + Quasar
- [ ] 3.1 Init Quasar con Capacitor en `sistema_gestion/app/`
- [ ] 3.2 app.scss — variables del manual + verde #00C853
- [ ] 3.3 LoginPage.vue — Google OAuth, mobile-first
- [ ] 3.4 MainLayout.vue — sidebar colapsable (íconos/expandido) + drawer mobile
- [ ] 3.5 FiltrosChips.vue — Hoy/Mañana/Ayer/Semana/Mis tareas/Pendientes
- [ ] 3.6 TareaItem.vue + EstadoBadge.vue — fila compacta Linear
- [ ] 3.7 TareasPage.vue — lista agrupada por categoría + panel lateral derecho
- [ ] 3.8 TareaForm.vue — modal crear/editar + TipTap + OpLookup
- [ ] 3.9 Cronometro.vue — start/stop/complete tiempo real
- [ ] 3.10 EquipoPage.vue — vista del equipo
- [ ] 3.11 Módulos secundarios: Dificultades, Ideas, Pendientes, Informes
- [ ] 3.12 Build y deploy

### Fase 4 — Android + Push
- [ ] 4.1 Firebase project "os-gestion" + google-services.json
- [ ] 4.2 Push backend (firebase-admin) + frontend (@capacitor/push-notifications)
- [ ] 4.3 APK firmado + link de descarga

---

## Notas técnicas importantes
- `sys_usuarios.Email` — columna con E mayúscula (gotcha SQL: usar backticks)
- `sys_empresa.uid` = `Ori_Sil_2` (mayúsculas, diferente a ia_service_os que es `ori_sil_2`)
- Estados en español con mayúscula: 'Pendiente', 'En Progreso', 'Completada', 'Cancelada'
- Prioridades en español con mayúscula: 'Baja', 'Media', 'Alta', 'Urgente'
- Tipos de ideas: 'Idea', 'Hecho'
- Tipos de informes: 'Semanal', 'Mensual'
- Estados dificultades: 'Abierta', 'En Proceso', 'Resuelta'
- Sidebar web: colapsable (solo íconos ↔ íconos + nombre), 64px colapsado / 240px expandido
- Acento: `#00C853` verde OS (reemplaza el violeta del ERP en esta app)
- Auth: Google OAuth → leer sys_usuarios (comunidad) → JWT 2 pasos (igual patrón ia-admin)
- Puerto API: 9300 (9100=ERP, 9200=ia-admin)
- Jennifer email correcto: jennifercanogarcia@gmail.com (NO jen@origensilvestre.com)
- Cronómetro: invisible al usuario → solo Start/Stop → tiempo_real_min es el valor final
- Categorías filtradas por perfil: un usuario Produccion NO ve Ventas, Cartera, etc.
- Director (es_admin=1) configura los perfiles desde un módulo admin
