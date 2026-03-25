# Spec: Módulo Jornadas — Sistema Gestión OS
**Estado**: Aprobado por Santi
**Fecha**: 2026-03-24
**Módulo**: sistema_gestion/

---

## Objetivo

Sistema de registro de jornada laboral: inicio, fin y pausas del día. Header visible en todas las páginas del módulo Gestión. Funcional, limpio, sin ensuciar el diseño.

---

## 1. Base de Datos

### Convenciones (heredadas de PLAN_SISTEMA_GESTION.md)

- PK: `id` INT AUTO_INCREMENT
- FK empresa: `empresa` VARCHAR(50) → sys_empresa.uid (ej: 'Ori_Sil_2')
- Usuario: se identifica por `email` VARCHAR(255) — NO por ID numérico
- Auditoría: `usuario_creador` VARCHAR(255), `usuario_ult_modificacion` VARCHAR(255), `fecha_creacion` DATETIME DEFAULT CURRENT_TIMESTAMP, `fecha_ult_modificacion` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
- `usuario_creador` y `usuario_ult_modificacion` se llenan con `req.usuario.email` (del JWT)
- Todos los campos de hora son DATETIME (decisión de Santi)
- Cálculos (horas trabajadas, tiempo neto, etc.) se computan al vuelo — NUNCA se almacenan

### Tablas nuevas

#### `g_jornadas`
```sql
CREATE TABLE g_jornadas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa VARCHAR(50) NOT NULL,
  usuario VARCHAR(255) NOT NULL,           -- email del usuario
  fecha DATE NOT NULL,                      -- día de la jornada
  hora_inicio DATETIME,                     -- reportada por usuario (editable)
  hora_inicio_registro DATETIME,            -- auditoría: momento exacto del click (inmutable)
  hora_fin DATETIME,                        -- reportada por usuario (editable)
  hora_fin_registro DATETIME,               -- auditoría: momento exacto del click (inmutable)
  observaciones TEXT,
  usuario_creador VARCHAR(255) NOT NULL,
  usuario_ult_modificacion VARCHAR(255),
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_jornada_dia (empresa, usuario, fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `g_jornada_pausas`
```sql
CREATE TABLE g_jornada_pausas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa VARCHAR(50) NOT NULL,
  jornada_id INT NOT NULL,
  hora_inicio DATETIME,                     -- reportada (editable)
  hora_inicio_registro DATETIME,            -- auditoría (inmutable)
  hora_fin DATETIME,                        -- NULL = pausa activa
  hora_fin_registro DATETIME,
  observaciones TEXT,
  usuario_creador VARCHAR(255) NOT NULL,
  usuario_ult_modificacion VARCHAR(255),
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (jornada_id) REFERENCES g_jornadas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `g_jornada_pausa_tipos` (tabla puente M:N)
```sql
CREATE TABLE g_jornada_pausa_tipos (
  pausa_id INT NOT NULL,
  tipo_pausa_id INT NOT NULL,
  empresa VARCHAR(50) NOT NULL,
  usuario_creador VARCHAR(255) NOT NULL,
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (pausa_id, tipo_pausa_id),
  FOREIGN KEY (pausa_id) REFERENCES g_jornada_pausas(id) ON DELETE CASCADE,
  FOREIGN KEY (tipo_pausa_id) REFERENCES g_tipos_pausa(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `g_tipos_pausa`
```sql
CREATE TABLE g_tipos_pausa (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa VARCHAR(50) NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  activa TINYINT(1) DEFAULT 1,
  orden INT DEFAULT 0,
  usuario_creador VARCHAR(255) NOT NULL,
  usuario_ult_modificacion VARCHAR(255),
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_ult_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed inicial
INSERT INTO g_tipos_pausa (empresa, nombre, orden, usuario_creador) VALUES
('Ori_Sil_2', 'Almuerzo', 1, 'sistema'),
('Ori_Sil_2', 'Desayuno', 2, 'sistema'),
('Ori_Sil_2', 'Pausa Activa', 3, 'sistema'),
('Ori_Sil_2', 'Imprevisto', 4, 'sistema'),
('Ori_Sil_2', 'Otro', 5, 'sistema');
```

---

## 2. UI — JornadaHeader

### Ubicación
En `MainLayout.vue`, entre `.topbar` y `.page-body`. Visible en todas las páginas del módulo.

```html
<div class="main-content">
  <div class="topbar">...</div>
  <JornadaHeader />           <!-- NUEVO -->
  <div class="page-body">
    <router-view />
  </div>
</div>
```

### 3 Estados

#### Estado 1 — Sin jornada activa
- Izquierda: fecha actual + nombre del usuario
- Derecha: botón "Iniciar Jornada" (estilo accent)
- Al hacer click: popover de confirmación cerca del botón mostrando hora actual → confirmar/cancelar

#### Estado 2 — Trabajando
- Izquierda: hora de inicio (ej: "08:30") + timer en vivo (ej: "3h 42m")
- Derecha: botón "Pausa" + botón "Fin Jornada"
- Indicador: punto verde pulsante
- Al hacer click en Pausa: dialog con multiselect de tipos + campo observaciones
- Al hacer click en Fin: popover de confirmación con hora actual

#### Estado 3 — En pausa
- Izquierda: hora de inicio + timer (pausado, muestra tiempo acumulado antes de pausa) + etiqueta del tipo de pausa
- Derecha: botón "Reanudar"
- Indicador: punto amarillo
- Al hacer click en Reanudar: cierra la pausa, vuelve a Estado 2

### Mobile
- Compacto: solo iconos en botones, texto reducido
- Timer siempre visible

### Popover de confirmación
- Aparece anclado al botón (no modal full-screen)
- Muestra la hora actual
- 2 botones: Confirmar / Cancelar
- Se usa para: Iniciar Jornada, Fin Jornada

### Dialog de pausa
- Dialog estándar Quasar (q-dialog)
- Multiselect de tipos de pausa (chips seleccionables)
- Campo observaciones (textarea)
- Botones: Iniciar Pausa / Cancelar

---

## 3. API Endpoints

Todos con middleware `requireAuth`. Siempre filtrar por `req.empresa`.

### Jornadas

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/gestion/jornadas/hoy` | Jornada del día del usuario actual + pausas |
| `POST` | `/api/gestion/jornadas/iniciar` | Crear jornada con hora_inicio = hora_inicio_registro = NOW() |
| `PUT` | `/api/gestion/jornadas/:id/finalizar` | Llenar hora_fin = hora_fin_registro = NOW() |
| `PUT` | `/api/gestion/jornadas/:id/editar` | Editar horas reportadas (hora_inicio, hora_fin, observaciones) |
| `GET` | `/api/gestion/jornadas/historial` | Historial filtrable por usuario, rango fechas |

### Pausas

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/gestion/jornadas/:id/pausas/iniciar` | Crear pausa + asociar tipos (M:N) |
| `PUT` | `/api/gestion/jornadas/:id/pausas/:pausaId/reanudar` | Finalizar pausa (hora_fin = NOW()) |

### Tipos de pausa (admin)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/gestion/tipos-pausa` | Listar tipos activos de la empresa |
| `POST` | `/api/gestion/tipos-pausa` | Crear tipo (admin) |
| `PUT` | `/api/gestion/tipos-pausa/:id` | Editar tipo (admin) |

### Reglas de negocio

- **No se puede iniciar jornada** si ya existe una para hoy (UNIQUE constraint)
- **No se puede finalizar jornada** si hay una pausa activa (hora_fin NULL en alguna pausa)
- **Al iniciar**: `hora_inicio = hora_inicio_registro = NOW()`
- **Al finalizar**: `hora_fin = hora_fin_registro = NOW()`
- **Al editar hora reportada**: solo cambia `hora_inicio` o `hora_fin`, los campos `_registro` NUNCA se tocan
- **Visibilidad historial**: usuario ve lo suyo; niveles superiores ven inferiores; admin (nivel 7) ve todo

---

## 4. Componentes Frontend

| Componente | Archivo | Rol |
|---|---|---|
| `JornadaHeader.vue` | `components/JornadaHeader.vue` | Header con estados, botones, timer |
| `JornadaPopover.vue` | `components/JornadaPopover.vue` | Popover confirmación (iniciar/finalizar) |
| `PausaDialog.vue` | `components/PausaDialog.vue` | Dialog multiselect tipos + observaciones |
| `jornadaStore.js` | `stores/jornadaStore.js` | Estado reactivo, API calls, timer |

### jornadaStore.js

- Al montar la app: `GET /jornadas/hoy` → determina estado
- Estado derivado de datos:
  - Sin registro → Estado 1
  - `hora_inicio` existe, `hora_fin` NULL, sin pausa abierta → Estado 2
  - Pausa con `hora_fin` NULL → Estado 3
- Timer: `setInterval` cada segundo, diferencia entre `hora_inicio` y `Date.now()`, descontando pausas cerradas
- Al cambiar estado (iniciar/finalizar/pausar/reanudar): actualiza store + UI reactiva

---

## 5. Diseño visual

Sigue el manual de diseño híbrido (`sistema_gestion/MANUAL_DISENO_HIBRIDO.md`):
- Fondo: `var(--bg-secondary)` o similar al topbar
- Texto: `var(--text-primary)` / `var(--text-secondary)`
- Botones: accent para Iniciar, outline para Pausa/Fin
- Punto pulsante: verde (trabajando) / amarillo (pausa) — animación CSS
- Altura del header: ~40-48px, compacto
- Dark theme por defecto
