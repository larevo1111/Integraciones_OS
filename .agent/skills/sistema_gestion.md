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

### E12 — Filtro "Hoy" muestra tareas de ayer después de las 7 PM (timezone)
**Causa**: `new Date().toISOString().slice(0,10)` devuelve fecha en UTC. A las 7 PM Colombia (UTC-5 = medianoche UTC) ya devuelve la fecha del día siguiente, rompiendo el filtro.
**Síntoma**: Tareas de "hoy" aparecen en la vista "Ayer". Vista "Hoy" vacía.
**Solución**: Usar fecha local del navegador:
```js
function _localISO(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
function hoyISO()    { return _localISO(new Date()) }
function mananaISO() { const d = new Date(); d.setDate(d.getDate()+1); return _localISO(d) }
function isoRelativo(dias) { const d = new Date(); d.setDate(d.getDate() + dias); return _localISO(d) }
```
**Regla**: NUNCA usar `.toISOString()` para fechas de filtro. SIEMPRE usar `_localISO()`.

### E13 — Círculo de estado desalineado (aparece arriba del centro)
**Causa**: El botón `.btn-add-sub-solo` (↳ "Agregar subtarea") en TareaItem.vue estaba en el flujo de columna del `.estado-col`. Aunque invisible (`opacity: 0`), añadía 12px de altura al `estado-col`, haciendo que el círculo (14px) quedara encima del centro en lugar de alineado con el título.
**Cálculo**: `estado-col` = 14px círculo + 12px botón = 26px. Centrado en 32px row → top 3px. Círculo center = 10px. Texto center = 16px. Desplazamiento = 6px arriba.
**Solución**: Hacer `.btn-add-sub-solo` `position: absolute` (igual que `.sub-controls`):
```css
.btn-add-sub-solo {
  position: absolute;
  top: 100%; left: 50%; transform: translateX(-50%);
  /* resto de propiedades igual */
}
```
**Regla**: TODO elemento dentro de `.estado-col` que no sea el círculo principal DEBE ser `position: absolute` para no afectar el flujo. Si se agregan más controles debajo del círculo en el futuro, hacerlos absolutos.
**¿Por qué reaparece?**: `.btn-add-sub-solo` fue añadido en un commit POSTERIOR al fix de alineación original (`c5d2074`). Cada vez que se agrega contenido al `estado-col` sin hacer `position:absolute`, el bug reaparece.

### E14 — Cronómetro salta a 1 minuto al iniciar (ROUND vs FLOOR)
**Causa**: Los 3 endpoints que cierran sesiones de cronómetro usaban `ROUND(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)`. Una sesión de 30-59 segundos se redondeaba a 1 minuto. En la siguiente sesión, `tiempo_real_min = 1`, y la fila del cronómetro arrancaba mostrando "01:00".
**Afectado**: `/iniciar`, `/detener`, `/completar` — todos en server.js.
**Solución**: Cambiar `ROUND` por `FLOOR` en los 3 queries:
```sql
SET fin = ?, duracion_min = FLOOR(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)
```
Así, sesiones < 60 segundos acumulan 0 minutos. El tiempo se pierde para el acumulado pero el display MM:SS en vivo es siempre correcto.

### E15 — Multi-selección no incluía tarea activa en el panel al Ctrl+click
**Causa**: Al hacer Ctrl+click en una tarea diferente de la que estaba abierta en el panel, solo se seleccionaba la nueva tarea. La tarea del panel quedaba fuera aunque visualmente el usuario esperaría que "entrar en modo multi" la incluyera.
**Solución**: En `onSeleccionarMulti()` de TareasPage, cuando `seleccionMultiIds.length === 0` (primera selección) y hay un panel abierto con una tarea diferente, auto-incluir la tarea del panel:
```js
function onSeleccionarMulti(tarea) {
  const idx = seleccionMultiIds.value.indexOf(tarea.id)
  if (idx === -1) {
    if (seleccionMultiIds.value.length === 0 && tareaSeleccionada.value && tareaSeleccionada.value.id !== tarea.id) {
      seleccionMultiIds.value.push(tareaSeleccionada.value.id)  // incluir la del panel
    }
    seleccionMultiIds.value.push(tarea.id)
    tareaSeleccionada.value = null  // cerrar panel al entrar en modo multi
  } else {
    seleccionMultiIds.value.splice(idx, 1)
  }
}
```

### E16 — Vista no actualiza tras bulk actions
**Causa**: Las bulk actions llamaban `onTareaActualizada()` para cada tarea. Esta función solo mueve tareas entre arrays locales (`tareas` y `completadas`). Las vistas filtradas (hoy/mañana/semana) dependen de `fecha_limite`, por lo que mover tareas entre arrays sin recargar no refleja el cambio en el filtro activo.
**Solución**: Después de cualquier bulk action, llamar `cargarTareas()` (recarga completa desde servidor con el filtro activo):
```js
async function _postBulk(ids) {
  if (tareaSeleccionada.value && ids.includes(tareaSeleccionada.value.id)) tareaSeleccionada.value = null
  seleccionMultiIds.value = []
  await cargarTareas()
}
```

### E17 — Click fuera no desactivaba multi-selección
**Causa**: No había listener para clicks fuera del área de tareas.
**Solución**: `document.addEventListener('click', onDocumentClick, true)` en capture phase. Registrar en `onMounted`, remover en `onUnmounted`. Si click fuera de `.tarea-item` y `.multi-bar` → `seleccionMultiIds.value = []`.
**Importante**: usar capture phase (`true`) para interceptar antes de que otros handlers paren la propagación.

### E18 — tiempo_real_min no se resetea al revertir Completada → Pendiente
**Causa**: Doble falla:
1. Frontend: `if (tiempo_real_min)` era falsy para `0` → nunca enviaba el 0 al backend
2. Backend: no borraba las sesiones `g_tarea_tiempo` — al próximo `/detener` sumaba las sesiones viejas
**Solución**: 3 cambios coordinados:
1. `_aplicarEstado`: cambiar `if (tiempo_real_min)` → `if (tiempo_real_min != null)` — permite enviar 0
2. `cambiarEstado`: cuando `tarea.estado === 'Completada' && nextEstado === 'Pendiente'` → `tiempoReset = 0`
3. `server.js` PUT: cuando `estado === 'Pendiente' && tiempo_real_min === 0` → `DELETE FROM g_tarea_tiempo WHERE tarea_id = ?`
**Regla**: Si en el futuro hay otro campo booleano/numérico que puede ser `0` o `false`, usar `!= null` como guard, nunca `if(valor)`.

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

### Componentes nuevos
| Componente | Archivo | Propósito | Condición de visibilidad |
|---|---|---|---|
| ProyectoSelector | `components/ProyectoSelector.vue` | Dropdown simple para seleccionar/crear proyecto | Siempre |
| EtiquetasSelector | `components/EtiquetasSelector.vue` | Multi-select para etiquetas con chips | Siempre |
| ResponsablesSelector | `components/ResponsablesSelector.vue` | Multi-select para usuarios (emails) | Siempre |
| OpSelector | `components/OpSelector.vue` | Busca OPs Effi por número o artículo | `categoria.es_produccion = 1` |
| RemisionSelector | `components/RemisionSelector.vue` | Busca remisiones de venta por ID o cliente | `categoria.es_empaque = 1` |
| PedidoSelector | `components/PedidoSelector.vue` | Busca cotizaciones (pedidos) por ID o cliente | `categoria.es_empaque = 1` |

### Patrón selector de documentos Effi (OpSelector / RemisionSelector / PedidoSelector)
Todos siguen el mismo patrón. Propiedades comunes:
- Input con búsqueda debounced 250ms + dropdown `position: fixed` via Teleport
- Tag cuando tiene valor: `núm + descripción/cliente` + 2 botones hover al hacer hover
- Botón 1: `open_in_new` → abre en Effi (link `<a target="_blank">`)
- Botón 2: `picture_as_pdf` → llama endpoint backend que corre script Playwright y devuelve PDF
- Limpiar con botón `close`

**URLs Effi para abrir en nueva pestaña:**
- OP: `https://effi.com.co/app/orden_produccion?id={id}`  (NO /app/orden_produccion/{id})
- Remisión: `https://effi.com.co/app/remision_v?id={id}`
- Pedido/Cotización: `https://effi.com.co/app/cotizacion?id={id}&id={id}` (doble id — así lo requiere Effi)

**Scripts Playwright PDF:**
- `scripts/get_op_pdf.js` — navega a URL base + aplica filtros manualmente
- `scripts/get_remision_pdf.js` — navega DIRECTAMENTE a `remision_v?id={id}` (más robusto)
- `scripts/get_pedido_pdf.js` — navega DIRECTAMENTE a `cotizacion?id={id}&id={id}` (más robusto)
- ⚠️ **REGLA PDF scripts**: usar URL directa con ID, no placeholder de input. El placeholder es frágil si Effi cambia el texto de la interfaz.

**Endpoints PDF backend (server.js):**
```
GET /api/gestion/op/:id/pdf        — requireAuth, execFile get_op_pdf.js
GET /api/gestion/remision/:id/pdf  — requireAuth, execFile get_remision_pdf.js
GET /api/gestion/pedido/:id/pdf    — requireAuth, execFile get_pedido_pdf.js
```
Todos: timeout 90s, Content-Type application/pdf, limpian /tmp tras pipe.

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

## 11. Multi-selección — patrón completo

### Activación
- **Desktop**: Ctrl+click (o Meta+click en Mac) en cualquier TareaItem
- **Mobile**: Long press 500ms en cualquier TareaItem
- Ambos emiten `'seleccionar-multi'` al padre (TareasPage)

### Lógica de selección (TareasPage.onSeleccionarMulti)
```js
function onSeleccionarMulti(tarea) {
  const idx = seleccionMultiIds.value.indexOf(tarea.id)
  if (idx === -1) {
    // REGLA: si es la primera selección y hay panel abierto con otra tarea → auto-incluir la del panel
    if (seleccionMultiIds.value.length === 0 && tareaSeleccionada.value && tareaSeleccionada.value.id !== tarea.id) {
      seleccionMultiIds.value.push(tareaSeleccionada.value.id)
    }
    seleccionMultiIds.value.push(tarea.id)
    tareaSeleccionada.value = null  // cerrar panel al entrar en modo multi
  } else {
    seleccionMultiIds.value.splice(idx, 1)  // toggle: desmarcar si ya estaba
  }
}
```
**Por qué auto-incluir**: Si el usuario tiene la tarea A abierta en el panel y hace Ctrl+click en tarea B, la intención es seleccionar AMBAS. Sin esto, A queda huérfana.

### Implementación en TareaItem.vue
```js
// Ctrl+click → emit seleccionar-multi
function onItemClick(e) {
  if (e.ctrlKey || e.metaKey) { e.stopPropagation(); emit('seleccionar-multi', props.tarea); return }
  emit('click', props.tarea)
}
// Long press 500ms → emit seleccionar-multi
let longPressTimer = null
function onTouchStart() {
  longPressTimer = setTimeout(() => { longPressTimer = null; emit('seleccionar-multi', props.tarea) }, 500)
}
function onTouchEnd()  { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null } }
function onTouchMove() { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null } }
```
Template root div requiere: `@click="onItemClick" @touchstart.passive="onTouchStart" @touchend="onTouchEnd" @touchmove.passive="onTouchMove" @touchcancel="onTouchEnd"`

### Estilos de selección
```css
.tarea-item.multi-sel {
  background: rgba(59, 130, 246, 0.07) !important;
  outline: 1px solid rgba(59, 130, 246, 0.3);
  outline-offset: -1px;
}
```
Prop en TareaItem: `:seleccionada-multi="seleccionMultiIds.includes(t.id)"`
Clase en template: `:class="{ ..., 'multi-sel': seleccionadaMulti }"`

### Floating action bar
Teleport to body, `position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%)`. Visible solo cuando `seleccionMultiIds.length > 0`.
- **X** → limpiar selección (`seleccionMultiIds.value = []`)
- **Fecha**: Hoy / Mañana / Pasado mañana / Sin fecha / input date personalizado
- **Estado**: Pendiente / En Progreso / Completada / Cancelada
- **Categoría**: lista con dot de color de cada categoría
- **Proyecto**: lista con dot de color + "Sin proyecto" (null)
- **Eliminar**: DELETE bulk con confirmación

### Refresh después de bulk actions
**SIEMPRE** llamar `cargarTareas()` (NO `onTareaActualizada`):
```js
async function _postBulk(ids) {
  if (tareaSeleccionada.value && ids.includes(tareaSeleccionada.value.id)) tareaSeleccionada.value = null
  seleccionMultiIds.value = []
  await cargarTareas()  // recarga con filtro activo — sin esto las vistas filtradas no se actualizan
}
```

### Deselección al click fuera
```js
// onMounted:
document.addEventListener('click', onDocumentClick, true)   // capture phase
// onUnmounted:
document.removeEventListener('click', onDocumentClick, true)

function onDocumentClick(e) {
  if (!seleccionMultiIds.value.length) return
  if (!e.target.closest('.tarea-item') && !e.target.closest('.multi-bar')) {
    seleccionMultiIds.value = []; cerrarMenusMulti(null)
  }
}
```
**Capture phase es obligatorio** — algunos elementos usan `@click.stop` que impediría el evento en bubble phase.

### Click en tarea cuando modo multi activo
```js
function seleccionar(tarea) {
  if (seleccionMultiIds.value.length > 0) { onSeleccionarMulti(tarea); return }  // toggle en vez de abrir panel
  tareaSeleccionada.value = tareaSeleccionada.value?.id === tarea.id ? null : tarea
}
```

---

## 12. Cascada de estados (backend server.js)

Cuando se actualiza el estado de una tarea padre via PUT o POST /completar, el backend ejecuta un UPDATE adicional en subtareas:
```js
// Después del UPDATE principal de la tarea padre:
if (estado === 'Completada') {
  await db.gestion.query(
    `UPDATE g_tareas SET estado='Completada', fecha_fin_real=COALESCE(fecha_fin_real, NOW()), usuario_ult_modificacion=?
     WHERE parent_id=? AND empresa=? AND estado NOT IN ('Completada','Cancelada')`,
    [req.usuario.email, req.params.id, req.empresa]
  )
} else if (estado === 'Cancelada') {
  await db.gestion.query(
    `UPDATE g_tareas SET estado='Cancelada', usuario_ult_modificacion=?
     WHERE parent_id=? AND empresa=? AND estado NOT IN ('Completada','Cancelada')`,
    [req.usuario.email, req.params.id, req.empresa]
  )
} else if (estado === 'Pendiente') {
  await db.gestion.query(
    `UPDATE g_tareas SET estado='Pendiente', fecha_fin_real=NULL, usuario_ult_modificacion=?
     WHERE parent_id=? AND empresa=? AND estado NOT IN ('Cancelada')`,
    [req.usuario.email, req.params.id, req.empresa]
  )
}
```
**Regla cascada**: Completada/Cancelada → subtareas que NO están ya en ese estado. Pendiente → subtareas que NO están Canceladas (las canceladas quedan canceladas).
**Aplica en**: PUT `/tareas/:id` (por estado) Y POST `/tareas/:id/completar`.

---

## 13. Cronómetro — flujo completo y gotchas críticos

### Arquitectura
- **g_tarea_tiempo**: tabla de sesiones (tarea_id, usuario, inicio DATETIME, fin DATETIME, duracion_min INT)
- **g_tareas.cronometro_activo**: calculado en SELECT (`COUNT(*) WHERE fin IS NULL`)
- **g_tareas.cronometro_inicio**: calculado en SELECT (subquery `SELECT inicio WHERE fin IS NULL`)
- **g_tareas.tiempo_real_min**: columna persistente, acumulado de todas las sesiones cerradas

### Endpoints cronómetro (server.js)
```
POST /iniciar   → cierra sesión abierta (si hay), inserta nueva sesión, estado→'En Progreso'
POST /detener   → cierra sesión abierta con FLOOR(segundos/60), recalcula tiempo_real_min, estado→'Pendiente'
POST /completar → cierra sesión abierta, usa tiempo_real_min del body si viene, marca estado='Completada'
```
**⚠️ CRÍTICO — usar FLOOR no ROUND**:
```sql
SET fin = ?, duracion_min = FLOOR(TIMESTAMPDIFF(SECOND, inicio, ?) / 60)
```
`ROUND` redondea sesiones de 30+ segundos a 1 minuto, causando que el cronómetro arranque en "01:00" en la siguiente sesión. `FLOOR` solo cuenta minutos completos.

### Display en TareaItem.vue (chip en lista)
```js
// Calcula MM:SS total = (tiempo_real_min acumulado + segundos actuales)
function calcularTiempo() {
  const ini   = parseInicio(props.tarea.cronometro_inicio)
  const base  = (props.tarea.tiempo_real_min || 0) * 60  // minutos acumulados → segundos
  const extra = Math.max(0, Math.floor((Date.now() - ini.getTime()) / 1000))  // segundos sesión actual
  const total = base + extra
  const m = Math.floor(total / 60); const s = total % 60
  tiempoCronometro.value = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}
// Parsear cronometro_inicio respetando timezone Colombia
function parseInicio(str) {
  if (!str) return null
  if (str.includes('Z') || str.includes('+') || str.includes('-', 10)) return new Date(str)
  return new Date(str.replace(' ', 'T') + '-05:00')  // MySQL datetime sin zona → Colombia UTC-5
}
```
**Comportamiento**: el chip muestra TIEMPO TOTAL acumulado (sesiones previas + sesión actual). Si la tarea tiene 5 minutos acumulados, arranca el cronómetro en "05:00" — esto ES correcto por diseño.

### Timezone — regla fundamental
- **Servidor**: mysql2 con `timezone: 'local'` (Colombia UTC-5). `new Date()` en Node → MySQL lo guarda en hora Colombia.
- **Retorno API**: mysql2 serializa DATETIME → JavaScript Date → JSON → ISO string con 'Z' (UTC).
- **Cliente**: `parseInicio` detecta 'Z' → `new Date(str)` (UTC correcto). Si es string sin zona (viejo dato) → añade `-05:00`.
- **Filtros de fecha**: NUNCA `toISOString()`. Siempre `_localISO(new Date())` para obtener fecha local Colombia.

### Auto-start desde check (TareasPage.cambiarEstado)
```js
await _aplicarEstado(tarea, 'En Progreso', null)
// Guard 1: solo si panel NO tiene esta tarea (evita double-start con watcher de TareaPanel)
// Guard 2: solo si cronómetro no está ya corriendo
if (nextEstado === 'En Progreso' && !tarea.cronometro_activo && tareaSeleccionada.value?.id !== tarea.id) {
  try {
    const data = await api(`/api/gestion/tareas/${tarea.id}/iniciar`, { method: 'POST' })
    if (data?.tiempo?.inicio) {
      const idx = tareas.value.findIndex(t => t.id === tarea.id)
      if (idx !== -1) tareas.value[idx] = { ...tareas.value[idx], cronometro_activo: 1, cronometro_inicio: data.tiempo.inicio }
    }
  } catch (e) { console.error(e) }
}
```

### Auto-start desde watcher (TareaPanel.vue)
```js
watch(() => props.tarea?.estado, (nuevo, viejo) => {
  if (nuevo === 'En Progreso' && viejo !== 'En Progreso') cronometroRef.value?.iniciar()
})
```
Solo activo mientras el panel ESTÁ montado. Si el panel no está abierto, no dispara.

### Popup al completar (TareasPage)
```js
function _minutosActuales(tarea) {
  let min = tarea.tiempo_real_min || 0
  if (tarea.cronometro_activo && tarea.cronometro_inicio) {
    const ini = _parseColombia(tarea.cronometro_inicio)
    if (ini) min += Math.max(0, Math.floor((Date.now() - ini.getTime()) / 60000))
  }
  return min
}
```
Pre-llena el modal con `_minutosActuales(tarea)`. "Cancelar" cierra sin completar. "Confirmar" guarda tiempo y marca Completada.
