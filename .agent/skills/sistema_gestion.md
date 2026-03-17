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
GET  /api/gestion/tareas           — lista con filtros: ?filtro=hoy|manana|semana|mis&estado=&categoria_id=
POST /api/gestion/tareas           — crear tarea
PUT  /api/gestion/tareas/:id       — actualizar tarea
```

### OPs Effi (solo categorías con es_produccion=1)
```
GET  /api/gestion/ops              — OPs vigentes pendientes. Acepta ?q= (busca por id_orden o artículo)
GET  /api/gestion/op/:id           — detalle de una OP específica
```

### (Pendientes — próxima sesión)
```
POST /api/gestion/tareas/:id/iniciar   — inicia cronómetro
POST /api/gestion/tareas/:id/detener   — detiene cronómetro
POST /api/gestion/tareas/:id/completar — completa tarea
GET/POST/PUT/DELETE /api/gestion/dificultades/:id
GET/POST/PUT/DELETE /api/gestion/ideas/:id
GET/POST/PUT/DELETE /api/gestion/pendientes/:id
GET/POST/PUT/DELETE /api/gestion/informes/:id
```

---

## 5. Tablas BD `u768061575_os_gestion`

| Tabla | Propósito |
|---|---|
| `g_categorias` | 13 categorías con color, icono, es_produccion |
| `g_perfiles` | Roles de la app (Director, Comercial, Produccion, Logistica, Sistemas) |
| `g_categorias_perfiles` | Junction: qué categorías ve cada perfil |
| `g_usuarios_config` | Config por usuario (tema, FCM token, perfil) |
| `g_tareas` | Tareas centrales — empresa, titulo, estado, prioridad, responsable, id_op |
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

### Acento: verde OS
```css
--accent: #00C853;  /* ≠ ERP que usa #5E6AD2 (violeta) */
```

---

## 10. Convenciones del módulo

- Estados: `'Pendiente'`, `'En Progreso'`, `'Completada'`, `'Cancelada'` (con mayúscula, en español)
- Prioridades: `'Baja'`, `'Media'`, `'Alta'`, `'Urgente'`
- Empresa activa OS: `'Ori_Sil_2'` (con mayúsculas, igual que sys_empresa.uid)
- JWT secret: en `.env` como `JWT_SECRET` — nunca en código
- FCM: aún no implementado (Fase 4)
