# Skill: Sistema Gestión OS

> **Cargar SIEMPRE antes de modificar `sistema_gestion/`.**
> App de tareas y conocimiento del equipo. Web (gestion.oscomunidad.com) + Android futuro.

---

## 1. Ubicación y servicios

| Recurso | Detalle |
|---|---|
| Directorio | `sistema_gestion/` (autónomo — api/ + app/) |
| URL pública | https://gestion.oscomunidad.com |
| Puerto API | 9300 |
| Systemd | `os-gestion.service` |
| Dev frontend | `cd sistema_gestion/app && npx quasar dev` (puerto 9301) |
| Build prod | `cd sistema_gestion/app && npx quasar build` → dist/spa/ |
| Manual diseño | `sistema_gestion/MANUAL_DISENO_HIBRIDO.md` |

```bash
systemctl status os-gestion        # estado del servicio
systemctl restart os-gestion       # reiniciar tras cambios en API
journalctl -u os-gestion -f        # logs en tiempo real
```

---

## 2. Arquitectura — 3 pools MySQL

Todos via SSH tunnel a Hostinger (`~/.ssh/sos_erp`, host `109.106.250.195:65002`).

| Pool | BD | Usuario | Acceso | Propósito |
|---|---|---|---|---|
| poolComunidad | `u768061575_os_comunidad` | `u768061575_ssierra047` | READ ONLY | Usuarios, empresas |
| poolGestion | `u768061575_os_gestion` | `u768061575_os_gestion` | READ/WRITE | Datos del módulo (g_*) |
| poolIntegracion | `u768061575_os_integracion` | `u768061575_osserver` | READ ONLY | OPs de producción |

**Contraseña**: `Epist2487.` (todas iguales)

⚠️ **Hostinger NO permite compartir usuario entre BDs** — un usuario solo puede acceder a su BD propia.
⚠️ **JOIN cross-database es imposible** — si necesitas datos de 2 BDs, hacer 2 queries en Node y combinar en JS.

---

## 3. Columnas reales en sys_* (verificadas)

### sys_usuarios (os_comunidad)
```sql
DESCRIBE sys_usuarios;
-- Columnas clave:
-- Email           VARCHAR(100) -- con E mayúscula. Usar `Email` en queries.
-- Nombre_Usuario  VARCHAR(100) -- con guiones y mayúsculas mixtas
-- Nivel_Acceso    VARCHAR(50)  -- nivel del usuario en el ERP
-- estado          VARCHAR(20)  -- 'Activo' o 'Inactivo' (minúscula en campo, mayúscula en valor)
```

### sys_empresa (os_comunidad)
```sql
DESCRIBE sys_empresa;
-- Columnas clave:
-- uid           VARCHAR(50)   -- PK, ej: 'Ori_Sil_2' (mayúsculas)
-- nombre_empresa VARCHAR(200) -- NO usar 'nombre' (no existe)
-- estado        VARCHAR(20)   -- 'Activa' (femenino, no 'Activo')
```

### sys_usuarios_empresas (os_comunidad)
```sql
DESCRIBE sys_usuarios_empresas;
-- Columnas clave:
-- usuario  VARCHAR(100) -- email del usuario
-- empresa  VARCHAR(50)  -- uid empresa
-- rol      VARCHAR(50)  -- NO usar 'perfil' (no existe en esta tabla)
-- estado   VARCHAR(20)  -- 'Activo'
```

---

## 4. Endpoints API activos

### Auth
```
POST /api/auth/google              — Google id_token → JWT
POST /api/auth/seleccionar_empresa — {empresa_uid} → JWT final con empresa_activa
GET  /api/auth/me                  — {email, nombre, empresa_activa, empresas}
```

### Usuarios y Categorías
```
GET  /api/usuarios                 — lista usuarios de la empresa activa
GET  /api/gestion/categorias       — 13 categorías {id, nombre, color, icono, es_produccion}
```

### Tareas
```
GET  /api/gestion/tareas               — lista con filtros: ?filtro=hoy|manana|semana|mis&estado=&categoria_id=&proyecto_id=
POST /api/gestion/tareas               — crear tarea (acepta proyecto_id, etiquetas:[])
PUT  /api/gestion/tareas/:id           — actualizar tarea (acepta proyecto_id, etiquetas:[]) → retorna etiquetas en response
                                         ↳ Cascada: si estado=Completada → subtareas Pendiente/En Progreso → Completada
                                         ↳ si estado=Cancelada → subtareas Pendiente/En Progreso → Cancelada
                                         ↳ si estado=Pendiente → subtareas no-Canceladas → Pendiente
POST /api/gestion/tareas/:id/completar — completa con tiempo_real_min opcional → cascada subtareas igual
POST /api/gestion/tareas/:id/iniciar   — inicia cronómetro. Cierra sesiones abiertas, inserta g_tarea_tiempo, estado→'En Progreso'
POST /api/gestion/tareas/:id/detener   — detiene cronómetro, calcula duración y acumula tiempo_real_min
```

### Proyectos
```
GET  /api/gestion/proyectos        — lista. ?estado=Activo para solo activos. retorna tareas_pendientes
POST /api/gestion/proyectos        — crear proyecto {nombre, color?}
PUT  /api/gestion/proyectos/:id    — actualizar {nombre, color, descripcion, estado}
DELETE /api/gestion/proyectos/:id  — desancla tareas (proyecto_id=NULL) y elimina
```

### Etiquetas
```
GET  /api/gestion/etiquetas        — lista etiquetas de la empresa
POST /api/gestion/etiquetas        — crear {nombre, color?}
PUT  /api/gestion/etiquetas/:id    — actualizar {nombre, color}
DELETE /api/gestion/etiquetas/:id  — elimina etiqueta y sus relaciones
```

### OPs Effi (solo categorías con es_produccion=1)
```
GET  /api/gestion/ops              — OPs vigentes pendientes. Acepta ?q= (busca por id_orden o artículo)
GET  /api/gestion/op/:id           — detalle de una OP específica
```

---

## 5. Tablas BD `u768061575_os_gestion`

| Tabla | Propósito |
|---|---|
| `g_categorias` | 13 categorías con color, icono, es_produccion |
| `g_perfiles` | Roles de la app (Director, Comercial, Produccion, Logistica, Sistemas) |
| `g_categorias_perfiles` | Junction: qué categorías ve cada perfil |
| `g_usuarios_config` | Config por usuario (tema, FCM token, perfil) |
| `g_tareas` | Tareas centrales — empresa, titulo, estado, prioridad, responsable, id_op, proyecto_id |
| `g_proyectos` | Proyectos por empresa — nombre, color, descripcion, estado (Activo/Archivado) |
| `g_proyectos_responsables` | Junction: proyectos × usuarios |
| `g_etiquetas` | Etiquetas libres por empresa — nombre, color |
| `g_etiquetas_tareas` | Junction: etiquetas × tareas |
| `g_etiquetas_proyectos` | Junction: etiquetas × proyectos |
| `g_tarea_tiempo` | Sesiones de cronómetro (inicio/fin/duración) |
| `g_dificultades` | Banco de dificultades y estrategias |
| `g_ideas_hechos` | Ideas y hechos relevantes del equipo |
| `g_pendientes` | Pendientes y compromisos |
| `g_informes` | Informes semanales/mensuales |

---

## 6. Query OPs — detalles importantes

```sql
SELECT
  pe.id_orden, pe.estado, pe.vigencia, pe.fecha_inicial, pe.fecha_final,
  GROUP_CONCAT(DISTINCT ap.descripcion_articulo SEPARATOR ', ') AS articulos
FROM zeffi_produccion_encabezados pe
LEFT JOIN zeffi_articulos_producidos ap
  ON ap.id_orden = pe.id_orden AND ap.vigencia = 'Orden vigente'  -- ← 'Orden vigente' NO 'Vigente'
WHERE pe.vigencia = 'Vigente'          -- ← encabezados sí usan 'Vigente'
  AND pe.estado != 'Procesada'
  AND (? = '' OR pe.id_orden LIKE ? OR ap.descripcion_articulo LIKE ?)
GROUP BY pe.id_orden
ORDER BY pe.fecha_final ASC
LIMIT 30
```

**⚠️ Semántica de vigencia en producción:**
- `zeffi_produccion_encabezados.vigencia = 'Vigente'` → OP activa
- `zeffi_articulos_producidos.vigencia = 'Orden vigente'` → artículo activo (distinto!)

---

## 7. Auth — flujo completo

```
1. Google id_token → POST /api/auth/google
2. Backend: GET https://oauth2.googleapis.com/tokeninfo?id_token=...
3. SELECT en sys_usuarios WHERE `Email` = ? AND estado = 'Activo'
4. SELECT en sys_usuarios_empresas JOIN sys_empresa WHERE ue.usuario=? AND ue.estado='Activo' AND e.estado='Activa'
5. Si 0 empresas → 403
6. Si 1 empresa → JWT final (tipo: 'final', empresa_activa: uid_empresa, expires: 7d)
7. Si >1 empresa → JWT temporal (tipo: 'temporal', empresas: [...], expires: 30m)
8. Frontend (paso 7): muestra selector → POST /api/auth/seleccionar_empresa → JWT final
```

**Guardado en frontend**: `localStorage.setItem('gestion_jwt', token)`

**Router guard** verifica `payload.tipo === 'final'` antes de redirigir a /tareas.

---

## 8. Errores documentados y soluciones

### E01 — Credenciales incorrectas (Access denied en os_comunidad)
**Causa**: Se usó `u768061575_osserver` para `os_comunidad` — ese usuario no tiene acceso.
**Solución**: Verificar en cPanel → MySQL Databases qué usuario tiene permisos sobre cada BD. Usuario correcto para os_comunidad es `u768061575_ssierra047`.
**Regla**: NUNCA asumir usuario MySQL en Hostinger. SIEMPRE verificar en cPanel primero.

### E02 — Columnas SQL inventadas (Unknown column 'Nombre')
**Causa**: Se usó `Nombre`, `Nivel`, `Estado` sin verificar el schema real.
**Solución**: Correr `DESCRIBE sys_usuarios` antes de escribir cualquier query contra una tabla nueva.
**Columnas reales**: `Nombre_Usuario`, `Nivel_Acceso`, `estado` (minúscula).

### E03 — sys_empresa.nombre inexistente
**Causa**: Se usó `e.nombre` asumiendo convención.
**Solución**: Columna real es `nombre_empresa`. Y `estado='Activa'` (femenino — la empresa es femenino en español).

### E04 — sys_usuarios_empresas.perfil inexistente
**Causa**: Se usó `ue.perfil`.
**Solución**: Columna real es `ue.rol`.

### E05 — Promise.all silenciaba errores parciales
**Causa**: Si `/usuarios` fallaba (cross-BD issue), `Promise.all` rechazaba todo y categorías tampoco cargaban.
**Solución**: Usar `Promise.allSettled` y verificar cada resultado individualmente.

### E06 — JOIN cross-database (Access denied)
**Causa**: Se intentó `LEFT JOIN g_usuarios_config` (os_gestion) dentro de un query en poolComunidad (os_comunidad). Cada usuario MySQL solo accede a su BD.
**Solución**: Hacer 2 queries separados y combinar en JS. O eliminar el JOIN cross-BD si no es necesario.

### E07 — Token temporal bloqueaba acceso a /tareas
**Causa**: Router redirect verificaba solo `if (token)` sin comprobar si era temporal o final.
**Solución**: Decodificar JWT: `JSON.parse(atob(token.split('.')[1]))` → si `payload.tipo === 'final'`, redirigir. Si no, borrar y quedar en login.

### E08 — vue3-google-login slot custom (credential undefined)
**Causa**: El componente `<GoogleLogin>` con slot personalizado no devuelve `credential` correctamente.
**Solución**: Usar directamente el SDK de Google con `googleSdkLoaded` y `google.accounts.id.renderButton()`. Docs: https://developers.google.com/identity/gsi/web/reference/js-reference#renderButton

### E09 — Express 5: app.get('*') PathError
**Causa**: Express 5 usa `path-to-regexp` v8 que no acepta `*` como ruta en `.get()`.
**Solución**: Reemplazar por `app.use((req, res) => { res.sendFile(...) })` al final de las rutas.

### E10 — Vue :class con guión (resta JS)
**Causa**: `{ tiene-valor: condicion }` → el guión se interpreta como resta en JS.
**Solución**: `{ 'tiene-valor': condicion }` — con comillas simples.

### E11 — @keydown.arrow-down no funciona en Vue
**Causa**: El modificador correcto para tecla flecha abajo es `.down`, no `.arrow-down`.
**Solución**: Usar `@keydown.down`, `@keydown.up`, `@keydown.enter`, `@keydown.escape`.

---

## 9. Patrones de diseño TickTick

Ver manual completo: `sistema_gestion/MANUAL_DISENO_HIBRIDO.md`

### Patrones clave
- **QuickAdd inline** (desktop): crear tarea directo en la lista sin modal
- **Bottom Sheet** (mobile): formulario desliza desde abajo, handle bar arriba, `Teleport to="body"`
- **Category Chips**: botones pill con dot de color — nunca `<select>`
- **OpSelector**: `position: relative` + dropdown absoluto con `z-index: 100`
- **Promise.allSettled**: para cargas paralelas tolerantes a fallos
- **Transiciones**: `.modal-enter-active` (opacity 150ms) + `.sheet-enter-active` (translateY cubic-bezier)
- **Prioridad chips**: 4 chips (Urgente/Alta/Media/Baja) con colores #ef4444/#f59e0b/#6b7280/#374151. El activo se resalta con `background: color+'22'` y `borderColor: color`
- **Teleport dropdown** (ProyectoSelector, EtiquetasSelector): `calcularPosicion()` con `getBoundingClientRect()` → `position: fixed` → evita clipping por overflow
- **ProyectoSelector**: dropdown con lista scrollable (`.proyecto-lista`) + botón "Nuevo proyecto" sticky al fondo siempre visible. Crea vía `ProyectoModal`. Si hay búsqueda sin coincidencia → "Crear X". Fix: endpoint usuarios = `/api/gestion/usuarios` (NO `/api/usuarios`)
- **ProyectoModal**: modal completo con paleta 10 colores, nombre, descripción, responsables (chips multi-select), etiquetas (chips), fecha estimada. Carga catálogos en `watch(modelValue)`. Usable para crear Y editar.
- **EtiquetasSelector**: multi-select chips, toggle individual, "Crear etiqueta X" si no hay match exacto
- **Sidebar colapsado** (64px): al colapsar, `sidebar-logo` queda centrado con solo el botón chevron rotado (chevron_left → chevron_right via `rotate(180deg)`) — nav-item-labels, proyectos y counters ocultos

### Componentes nuevos (desde sesión 2026-03-16)
| Componente | Archivo | Propósito |
|---|---|---|
| ProyectoSelector | `components/ProyectoSelector.vue` | Dropdown simple para seleccionar/crear proyecto |
| EtiquetasSelector | `components/EtiquetasSelector.vue` | Multi-select para etiquetas con chips |
| ResponsablesSelector | `components/ResponsablesSelector.vue` | Multi-select para usuarios (emails), igual patrón que EtiquetasSelector |

### Regla de consistencia de campos (ver REGLAS_APP.md)
- **SIEMPRE** usar los selectors existentes — nunca reimplementar inline
- Cada tipo de campo = un componente = igual en toda la app
- Reglas documentadas en `sistema_gestion/REGLAS_APP.md`

### Estados de proyecto
| Estado | Qué significa |
|---|---|
| `Activo` | En curso, aparece en selectores |
| `Archivado` | Pausado, oculto en selectores |
| `Completado` | Finalizado, guarda `fecha_finalizacion_real` |

Menú ⋮ en sidebar: Editar / Completar / Archivar / Eliminar

### Acento: verde OS
```css
--accent: #00C853;  /* ≠ ERP que usa #5E6AD2 (violeta) */
```

### CSS global — input date/time en dark mode
**REGLA**: el icono del calendario nativo no se ve en dark mode. Siempre aplicar en `app.scss`:
```css
input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.7); opacity: 0.7; cursor: pointer; }
[data-theme="light"] input[type="date"]::-webkit-calendar-picker-indicator { filter: none; opacity: 0.6; }
```
**Ya está en `app.scss` globalmente** — aplica a todos los inputs date/time/datetime-local de la app.

---

## 10. Convenciones del módulo

- Estados: `'Pendiente'`, `'En Progreso'`, `'Completada'`, `'Cancelada'` (con mayúscula, en español)
- Prioridades: `'Baja'`, `'Media'`, `'Alta'`, `'Urgente'`
- Empresa activa OS: `'Ori_Sil_2'` (con mayúsculas, igual que sys_empresa.uid)
- JWT secret: en `.env` como `JWT_SECRET` — nunca en código
- FCM: aún no implementado (Fase 4)

---

## 11. Multi-selección — patrón implementado

**Activación**: Ctrl+click (desktop) o long press 500ms (mobile) en cualquier TareaItem.
- Emite `'seleccionar-multi'` al padre (TareasPage)
- Si había tarea abierta en panel → se auto-incluye en la primera selección
- Estilos: `.tarea-item.multi-sel { background: rgba(59,130,246,0.07); outline: 1px solid rgba(59,130,246,0.3) }`

**Floating bar**: Teleport to body, posición fixed bottom. Solo visible cuando `seleccionMultiIds.length > 0`.
- X → desmarcar todo
- Fecha: Hoy / Mañana / Pasado mañana / Sin fecha / Personalizada (date input)
- Estado: Pendiente / En Progreso / Completada / Cancelada
- Categoría: lista con dot de color de cada categoría
- Proyecto: lista con dot + "Sin proyecto"
- Eliminar: DELETE con confirmación

**Refresh después de bulk**: SIEMPRE usar `cargarTareas()` (no `onTareaActualizada`). El motivo: las vistas filtradas (hoy/mañana/semana) no se actualizan si solo se hace push en array local.

**Deselección**: listener `document.addEventListener('click', fn, true)` en capture phase. Si click fuera de `.tarea-item` y `.multi-bar` → `seleccionMultiIds.value = []`.

---

## 12. Cascada de estados (backend server.js)

Cuando se actualiza el estado de una tarea padre via PUT o POST /completar:
- `Completada` → `UPDATE g_tareas SET estado='Completada', fecha_fin_real=COALESCE(...,NOW()) WHERE parent_id=? AND estado NOT IN ('Completada','Cancelada')`
- `Cancelada` → `UPDATE g_tareas SET estado='Cancelada' WHERE parent_id=? AND estado NOT IN ('Completada','Cancelada')`
- `Pendiente` → `UPDATE g_tareas SET estado='Pendiente', fecha_fin_real=NULL WHERE parent_id=? AND estado NOT IN ('Cancelada')`

---

## 13. Cronómetro — flujo completo

**Auto-start desde check** (TareasPage.cambiarEstado):
```js
// En cambiarEstado(), después de _aplicarEstado(tarea, 'En Progreso', null):
if (nextEstado === 'En Progreso' && !tarea.cronometro_activo && tareaSeleccionada.value?.id !== tarea.id) {
  const data = await api(`/api/gestion/tareas/${tarea.id}/iniciar`, { method: 'POST' })
  if (data?.tiempo?.inicio) {
    const idx = tareas.value.findIndex(t => t.id === tarea.id)
    if (idx !== -1) tareas.value[idx] = { ...tareas.value[idx], cronometro_activo: 1, cronometro_inicio: data.tiempo.inicio }
  }
}
```
- Guard `tareaSeleccionada.value?.id !== tarea.id`: evita double-start cuando el panel ya tiene la tarea y su watcher también llamaría a `iniciar`.
- Guard `!tarea.cronometro_activo`: no re-iniciar si ya estaba corriendo.

**Auto-start desde watcher** (TareaPanel.vue):
- `watch(() => props.tarea?.estado)` → si pasa a 'En Progreso' → `cronometroRef.value?.iniciar()`
- Solo se ejecuta si el panel ESTÁ montado (tarea abierta).

**Timezone**: Colombia UTC-5. `_parseColombia(str)` en TareasPage trata strings sin zona como `-05:00`. El servidor guarda con `timezone: 'local'` en mysql2 (Colombia).

**Popup al completar**:
- Pre-filled con `_minutosActuales(tarea)` = tiempo_real_min acumulado + minutos del cronómetro en vivo si activo
- "Cancelar" → cierra modal sin completar (tarea queda en estado anterior)
- "Confirmar" → guarda tiempo + marca Completada
