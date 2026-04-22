# Plan: Unificar Inventario dentro de App de Producción (React/Refine)

**Creado**: 2026-04-22
**Estado**: En curso — 85% completado (Fases 1-11 listas, faltan 12-14)
**Owner**: Santi + Claude Code

---

## Contexto

Movemos el módulo de inventario (que vivía en Vue 3 en `inventario/frontend/`) a la app de producción (React + Refine + Shadcn + Tailwind v4) ubicada en `produccion/`. Objetivo: unificar ambos módulos en una sola app bajo `inv.oscomunidad.com`.

**Razón**: simplificar infraestructura (1 frontend, 1 stack, 1 dominio), habilitar componentes compartidos (OsDataTable), y preparar el módulo Catálogo nuevo.

**Regla crítica**: port **1:1** del Vue — mismo sidebar, mismos modales, mismas tablas con mismas columnas, mismos botones, mismos colores. Sólo cambia el stack. NO inventar mejoras.

---

## Arquitectura final esperada

```
inv.oscomunidad.com  →  puerto 9600 (FastAPI os-produccion-api)
                         ├─ sirve frontend React construido en produccion/dist/
                         ├─ endpoints /api/produccion/*  (nativos)
                         ├─ endpoints /api/solicitudes/*  (nativos)
                         ├─ endpoints /api/articulos  (nativos)
                         ├─ endpoints /api/auth/*  (nativos)
                         └─ proxy /api/inventario/*  →  puerto 9401 (temporal)

BD:  MariaDB en VPS Contabo (94.72.115.156)
     Base única: inventario_produccion_effi
     - 10 tablas inv_* (inventario físico)
     - 3 tablas prod_* (solicitudes, grupos, logs)
```

**Fase final** (Fase 10): fusionar el backend FastAPI de `inventario/api.py` dentro de `produccion/api.py` y desactivar `os-inventario-api.service`.

---

## Sidebar: estructura final

```
├─ Vista general       (/)
├─ Solicitudes         (/solicitudes)       ← producción
├─ Calendario          (/calendario)        ← placeholder
├─ Recetas             (/recetas)           ← placeholder
├─ Inventarios         ← expandible
│   ├─ Inventarios     (/inventarios)       ← aside fechas + vista completa por fecha
│   └─ Catálogo        (/catalogo)          ← NUEVO: tabla productos con stock
└─ Configuración       (/config)            ← placeholder
```

**`/inventarios`** = clon del `App.vue` Vue original: aside con fechas + header + toolbar + tabs Conteo/Gestión/Costos + vista. Todas las acciones viven adentro, no en el sidebar.

**`/catalogo`** = único NUEVO: tabla simple con `OsDataTable` estándar.

---

## ✅ Completado

### FASE 1 — Base de la app unificada
- [x] Sidebar con submenu expandible (estado persistido en localStorage)
- [x] Ruta `/inventarios/:fecha?` y `/catalogo`
- [x] Layout principal con auth guard

### FASE 2 — Auth Google OAuth
- [x] `lib/auth.js` store (localStorage + eventos)
- [x] `lib/api.js` interceptor Bearer JWT + auto-logout 401
- [x] `pages/login.jsx` con `@react-oauth/google`
- [x] `AuthGuard` en App.jsx
- [x] Avatar + nombre + nivel + logout en sidebar

### FASE 3 — Backend auth
- [x] `/api/auth/google` en `scripts/produccion/api.py`
- [x] `/api/auth/me`
- [x] `require_auth` dependency
- [x] Valida id_token contra Google, busca en `sys_usuarios` Hostinger, emite JWT 7 días
- [x] `scripts/produccion/.env` con GOOGLE_CLIENT_ID + JWT_SECRET (gitignored)
- [x] Systemd `os-produccion-api.service` con Environment PATH correcto para subprocess (claude, opencode)

### FASE 4 — Proxy backend
- [x] `/api/inventario/*` proxy a `:9401` vía httpx en `api.py`
- [x] Funciona con GET/POST/PUT/PATCH/DELETE

### FASE 5 — Páginas de inventario clonadas del Vue
- [x] `InventariosLayoutPage` — aside fechas + header + toolbar + tabs
- [x] `TablaConteo` — clon 1:1 del OsDataTable.vue (inputs editables, stepper +/-, badges diff, status dots, menu por fila)
- [x] `NuevoInventarioModal` — Completo/Parcial con sugerir artículos
- [x] `CatalogoPage` (nuevo) con OsDataTable estándar
- [x] CSS copiado del Vue (640 líneas) → `src/styles/inventario.css`
- [x] Material Icons cargado en index.html

### FASE 6 — DNS
- [x] `inv.oscomunidad.com` apunta al puerto 9600 (nueva React) — forzado con `cloudflared tunnel route dns -f`
- [x] Puerto 9401 (Vue viejo) sigue corriendo por si hay rollback

### FASE 7 — Migración BD local → VPS
- [x] Backup local `/home/osserver/Proyectos_Antigravity/backups/{os_inventario,os_produccion}/2026-04-22_090926.sql`
- [x] Creada BD `inventario_produccion_effi` en VPS con 13 tablas
- [x] 7 scripts Python de inventario migrados a usar `cfg_inventario()` helper
- [x] Endpoint `/api/auth/google`, logger, api.py actualizados
- [x] Backends de producción e inventario corriendo con BD VPS

### Testing E2E hecho
- [x] CRUD solicitudes contra VPS
- [x] Sugerir receta algoritmo + agente IA end-to-end
- [x] Grupos de OP (compatibilidad por granel común)
- [x] Logs escritos en VPS (`prod_logs`)
- [x] API inventario responde (`/fechas`, `/bodegas/todas`, `/articulos`)
- [x] Scripts CLI: `generar_informe.py` (PDF), `analisis_ia_inventario.py` (PDF ejecutivo), `depurar_inventario.py` (495 filas insertadas OK)
- [x] Visual del inventario React idéntico al Vue

---

## ✅ Completado (continuación)

### FASE 8 — Acciones del aside (commit 52f0d19)
- [x] ConfirmModal componente reutilizable (variantes default/warn/danger + requiredText)
- [x] Cerrar conteo + Reabrir conteo (lock / lock_open)
- [x] Cerrar inventario completo (verified, warn amarillo)
- [x] Reiniciar conteos (rojo, requiere escribir "REINICIAR")
- [x] Eliminar inventario (rojo)
- [x] Calcular teórico con title dinámico ("Recalcular teórico (fecha)")

### FASE 9 — Modales por fila + FAB (commit 4c76704)
- [x] NotaModal — editar/agregar nota
- [x] Tomar foto — input file capture="environment" sin modal
- [x] FotoVerModal — lightbox para ver foto subida
- [x] AsignarModal — buscar Effi + comparación de unidades + POST /asignar
- [x] AgregarModal — 3 tabs (Buscar / Excluidos / No matriculado)
- [x] FAB de agregar artículo en esquina inferior derecha

### FASE 10 — Vista Gestión (commit cda076b — versión inicial)
- [x] VistaGestion con sub-tabs Dashboard / Auditoría OPs
- [x] Dashboard: KPIs (valor teórico/físico/impacto/con dif)
- [x] Severidad cards (críticas/significativas/menores) clickeables como filtro
- [x] Filtros estado (pendientes/analizados/justificadas/req. ajuste)
- [x] Tabla de artículos con diferencias

### FASE 11 — Vista Costos (commit cda076b)
- [x] Tabla con valorización completa
- [x] Filtro por nombre/código + totales en header

---

## 🔄 Pendiente

### FASE 10b — Vista Gestión avanzada
- [ ] Modal detalle por artículo (form causa/estado/observaciones + evidencias)
- [ ] Botón Análisis IA con polling /gestion/analizar + /gestion/analisis-estado
- [ ] Botón Informe (PDF inline)
- [ ] Sub-tab Auditoría OPs completa (tabla + filtros inclusión/sospecha/revisión + modal detalle + marcar revisadas)
- [ ] Acordeones por grupo en lista de artículos

### FASE 12 — Toolbar acciones
- [ ] Botón **Sync Effi** en el toolbar (con spinner + mensaje de estado)
- [ ] Botón **Escanear** código de barras

### FASE 13 — Testing riguroso
- [ ] Login real con cuenta Google de Santi en `inv.oscomunidad.com`
- [ ] Crear un conteo físico completo: verificar que persiste en VPS
- [ ] Ajuste inline con stepper +/- y validar que diferencia se calcula
- [ ] Sync Effi E2E (Playwright corriendo desde systemd service)
- [ ] Mobile/responsive en celular real (Jenifer cuenta con celular en bodega)
- [ ] Comparación visual lado-a-lado: `inv-old.oscomunidad.com` (Vue) vs `inv.oscomunidad.com` (React)

### FASE 14 — Deprecación app vieja
- [ ] Fusionar `scripts/inventario/api.py` dentro de `scripts/produccion/api.py` (eliminar proxy)
- [ ] Borrar `inventario/frontend/` (Vue)
- [ ] Desactivar `os-inventario-api.service`
- [ ] Quitar ruta `inv-old.oscomunidad.com` de cloudflared
- [ ] Actualizar docs en `.agent/manuales/inventario_fisico_manual.md`
- [ ] Drop de las BDs locales `os_inventario` y `os_produccion` (backups ya existen)

---

## Archivos clave creados/modificados

**Nuevos** (React):
- `produccion/src/pages/inventarios-layout.jsx` — layout principal
- `produccion/src/pages/catalogo.jsx` — página nueva
- `produccion/src/pages/login.jsx` — auth
- `produccion/src/components/inventario/tabla-conteo.jsx` — tabla editable
- `produccion/src/components/inventario/nuevo-inventario-modal.jsx`
- `produccion/src/styles/inventario.css` — CSS del Vue portado
- `produccion/src/lib/auth.js`
- `scripts/produccion/.env` — secrets (gitignored)

**Modificados**:
- `produccion/src/components/sidebar.jsx` — submenu expandible
- `produccion/src/App.jsx` — rutas + AuthGuard
- `produccion/src/lib/api.js` — interceptor Bearer
- `produccion/index.html` — Material Icons + Inter font
- `scripts/produccion/api.py` — auth + proxy inventario
- `scripts/produccion/logger.py` — usa inventario() helper del VPS
- `scripts/inventario/api.py` + 6 scripts CLI — cfg_inventario() helper
- `scripts/lib/db_conn.py` + `lib/db_conn.js` — función `inventario()` + `cfg_inventario()`
- `integracion_conexionesbd.env` — bloque DB_INVENTARIO_*
- `/etc/systemd/system/os-produccion-api.service` — PATH con ~/.local/bin y ~/.nvm
- `/etc/cloudflared/config.yml` — inv.oscomunidad.com → :9600

**Eliminados** (páginas mal puestas):
- `produccion/src/pages/inventarios-{lista,excluidos,observaciones,ops-revisar,catalogo,sync-effi,analisis-ia,informes}.jsx`

---

## Gotchas encontrados y resueltos

1. **DB `os_produccion` creada sin consultar** → movida a `inventario_produccion_effi` en VPS. Regla en memoria `feedback_no_bds_nuevas.md`.
2. **systemd service sin PATH** → subprocess a `claude`/`opencode` retornaba stdout vacío en 9ms. Fix: `Environment="PATH=/home/osserver/.local/bin:..."`. Regla en memoria `feedback_systemd_path.md`.
3. **`inv.oscomunidad.com` daba 502** tras el swap → se solucionó con `cloudflared tunnel route dns -f` para forzar actualización del CNAME.
4. **Archivos SCP con mismo nombre** → `mysqldump` de ambas BDs tenían `${STAMP}.sql` → el segundo sobreescribía al primero. Fix: nombres únicos `inv_dump.sql` vs `prod_dump.sql`.
5. **Cronometro bug** → `cron_total.ms` accedido dentro del `with` antes de `__exit__`. Fix: método `elapsed_ms()`.

---

## Cómo continuar desde cero en otra sesión

1. Leer este archivo completo
2. Verificar que los servicios estén activos:
   ```bash
   sudo systemctl status os-produccion-api os-inventario-api cloudflared
   ```
3. URL de prueba: https://inv.oscomunidad.com (con `?v=N` si cachea)
4. Token de test para saltarse login:
   ```bash
   cd /home/osserver/Proyectos_Antigravity/Integraciones_OS
   python3 -c "import jwt, time
   SECRET = [l.split('=',1)[1].strip() for l in open('scripts/produccion/.env') if l.startswith('JWT_SECRET=')][0]
   print(jwt.encode({'email':'larevo1111@gmail.com','nombre':'Santiago','nivel':7,'exp':int(time.time())+86400}, SECRET, algorithm='HS256'))
   "
   # → pegar en localStorage con key 'produccion_jwt'
   ```
5. Retomar por la Fase 8 (Acciones del aside)

---

## Commits relevantes en main

- `7f6a36e` feat(produccion): agente IA + agrupación de solicitudes + logs detallados
- `326b755` feat: migrar inventario+produccion a VPS (BD inventario_produccion_effi)
- `9d46ab0` feat(produccion): migrar 8 páginas de inventario a stack React (antes del feedback de simplificar)
- `d02983f` feat(produccion): clon 1:1 del módulo inventario Vue → React (simplificado después del feedback)
