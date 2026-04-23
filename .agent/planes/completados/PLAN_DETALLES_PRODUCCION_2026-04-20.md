---
estado: ✅ COMPLETADO
creado: 2026-04-20
completado: 2026-04-23
modulo: sistema_gestion
versiones_entregadas: v2.8.0 → v2.8.5
---

## Estado: COMPLETADO 2026-04-23

Todo el plan implementado, testeado end-to-end y desplegado en producción (gestion.oscomunidad.com). 12 commits entre `58e54c8` (2026-04-21) y `021c421` (2026-04-23).

### Versiones entregadas
- **v2.8.0** — Schema + endpoints GET/PUT + componente `DetallesProduccion.vue` inicial con OP, materiales, productos, tiempos (coma/punto decimal OK).
- **v2.8.1** — Refactor layout Quasar puro, OP vinculada DENTRO del acordeón, contraste dark (q-input `filled`), botones sutiles.
- **v2.8.2** — Chip de estado (Generada/Procesada/Validado/Anulada con colores), botón "Procesar" + endpoint `/procesar`, script `cambiar_estado_orden_produccion.js`, columna `id_op_original`.
- **v2.8.3** — Botones flat/dense/size="sm" no-caps (estilo sutil).
- **v2.8.4** — Endpoint `/validar` (anular + crear con reales + cambiar estado Validado), captura `OP_CREADA:<id>` en `import_orden_produccion.js`.
- **v2.8.5** — Protección 503 si server no tiene Playwright + retry automático. Modal confirmación `dark:true`. Selector dropdown fix. `comunidad` (Hostinger) opcional al arranque. `/procesar` y `/validar` usan `req.usuario.nombre` del JWT (no dependen de comunidad).

### Tests end-to-end verificados (2026-04-22 y 23)
- OP 2183: `/procesar` vía localhost ✅
- OP 2184 → 2185: `/validar` flujo completo (anular + crear + cambio estado, 1min 10s) ✅
- OP 2197: `/procesar` vía **URL pública gestion.oscomunidad.com** ✅ (16s, tras fix DNS)
- Desktop dark/claro: chip + botones + layout ✅
- Móvil 390×844 bsheet dark/claro ✅
- Coma decimal (3,8) y punto (20.5) ambos OK ✅
- Diff en vivo (+4,5 GRS verde / -0,2 KG rojo) ✅

### Infraestructura resuelta durante la ejecución
- **Bug pool "Pool is closed"**: `db.js` cacheaba pool obsoleto tras reconexión SSH → getters dinámicos que leen del helper central en cada acceso.
- **Hostinger bloquea IP local**: SSH jump tunnel `local → VPS Contabo → Hostinger MySQL` vía `scripts/tunnel_hostinger.sh` + systemd unit `tunnel-hostinger.service`. Expone MySQL Hostinger como `127.0.0.1:3313`. COMUNIDAD en `.env` ahora usa modo `direct` a ese puerto.
- **Cloudflare DNS balanceando entre 2 tunnels**: reapuntado `gestion.oscomunidad.com` al tunnel local (único con Playwright) via `cloudflared tunnel route dns --overwrite-dns`. Hostname quitado del config del VPS.
- **Arranque robusto**: `db.js` ya no bloquea si Hostinger tarda. Reintento en background cada 15s.

### Archivos creados/modificados
- `sistema_gestion/app/src/components/DetallesProduccion.vue` (nuevo)
- `sistema_gestion/app/src/services/numero.js` (nuevo — `parseDecimal`, `fmtNum`)
- `sistema_gestion/api/server.js` (3 endpoints + helper `PLAYWRIGHT_OK`)
- `sistema_gestion/api/db.js` (getters dinámicos + comunidad opcional)
- `scripts/cambiar_estado_orden_produccion.js` (nuevo — Playwright)
- `scripts/import_orden_produccion.js` (modificado — captura `OP_CREADA:<id>` en stdout)
- `scripts/tunnel_hostinger.sh` (nuevo — SSH jump tunnel con reconexión)
- `/etc/systemd/system/tunnel-hostinger.service` (nuevo — daemon del tunnel)

### BD: migraciones aplicadas en VPS (os_gestion)
- Tabla `g_tarea_produccion_lineas` creada.
- `g_tareas`: columnas nuevas `tiempo_alistamiento_min`, `tiempo_produccion_min`, `tiempo_empaque_min`, `tiempo_limpieza_min`, `id_op_original`.
- `os_integracion.unidades_articulos`: tabla creada (490 artículos) replicada desde `os_inventario.inv_rangos` local para lookup de unidades.

### Pendiente/Descartado
- **Ventas / CRM**: no se implementó (Santi pidió esperar a que el CRM esté más adelantado).
- **Botón "+ agregar consumo" manual**: descartado (solo lo que viene de Effi).
- **Mapeo automático sucursal_id/bodega_id**: hoy hardcoded a `1 = Principal`. Si operan con otra sucursal/bodega, ampliar `sucursalIdMap` en `server.js`.

---


# Plan — Sección "Detalles de producción" en panel de tarea

Basado en [mockup ventas y produccion gestion.png](mockup%20ventas%20y%20produccion%20gestion.png). Este plan cubre **solo Producción**. Ventas queda para cuando el CRM esté más adelantado.

---

## Contexto (verificado en BD)

**Fuentes de datos existentes:**

- **OP y sus detalles** (en `os_integracion` del VPS Contabo):
  - `zeffi_produccion_encabezados` — 1 fila por OP: `id_orden`, fechas, encargado, estado, observacion.
  - `zeffi_materiales` — N filas de materiales consumidos por OP: `id_orden`, `cod_material`, `descripcion_material`, `cantidad`, `costo_ud`.
  - `zeffi_articulos_producidos` — N filas de productos generados por OP: `id_orden`, `cod_articulo`, `descripcion_articulo_producido`, `cantidad`.
- **Unidades por artículo** (en `os_inventario` local): `inv_rangos` (490 artículos) — columnas `id_effi` (= cod_articulo), `unidad`, `grupo`. Fuente canónica.
- **Vínculo tarea↔OP**: `g_tareas.id_op` ya existe (varchar, lo setea el OpSelector).

**Lo que NO existe y hay que crear:**

- Valores reales reportados por el usuario (cantidad consumida real, producida real) para cada material/producto de la OP.
- Tiempos de la actividad (alistamiento, producción, empaque, limpieza).

---

## Diseño de datos — nuevas tablas + columnas en `os_gestion`

### Tabla nueva: `g_tarea_produccion_lineas`
Una sola tabla para materiales + productos (con columna `tipo` que distingue). Más simple que dos tablas y permite reusar componente.

```sql
CREATE TABLE g_tarea_produccion_lineas (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  tarea_id        INT NOT NULL,
  tipo            ENUM('material','producto') NOT NULL,
  cod_articulo    VARCHAR(50) NOT NULL,          -- cod_material o cod_articulo según tipo
  descripcion     VARCHAR(500),                  -- snapshot del nombre al momento
  unidad          VARCHAR(20),                   -- snapshot desde inv_rangos
  cantidad_teorica DECIMAL(12,3),                -- desde Effi (zeffi_materiales.cantidad o zeffi_articulos_producidos.cantidad)
  cantidad_real   DECIMAL(12,3),                 -- NULL hasta que el usuario confirme/edite
  usuario_ult_modificacion VARCHAR(255),
  fecha_ult_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_tarea (tarea_id),
  UNIQUE KEY unq_tarea_tipo_cod (tarea_id, tipo, cod_articulo),
  FOREIGN KEY (tarea_id) REFERENCES g_tareas(id) ON DELETE CASCADE
);
```

**Lógica de llenado:** al abrir el panel de una tarea con `id_op`, si no hay filas para esa tarea, el backend las sembra copiando lo que tiene Effi (materiales + productos) con `cantidad_teorica` de Effi y `cantidad_real = NULL`. Una vez sembradas, son editables solo localmente — si Effi cambia, el usuario decide si re-sincroniza (botón "Actualizar desde OP" — fase 2, no ahora).

### Columnas nuevas en `g_tareas` (tiempos de la actividad)

```sql
ALTER TABLE g_tareas
  ADD COLUMN tiempo_alistamiento_min INT,
  ADD COLUMN tiempo_produccion_min   INT,
  ADD COLUMN tiempo_empaque_min      INT,
  ADD COLUMN tiempo_limpieza_min     INT;
-- total es calculado en frontend = suma de los 4 (no se almacena).
```

Observaciones específicas de producción: **reusar el campo `notas` existente** por ahora (no duplicar). Si después se vuelve confuso, agregamos `observaciones_produccion` separada.

---

## Endpoints API (nuevos)

- `GET /api/gestion/tareas/:id/produccion`
  - Si no existen filas en `g_tarea_produccion_lineas` para esta tarea, sembrarlas desde Effi (`zeffi_materiales` + `zeffi_articulos_producidos` filtrando por `id_orden`), uniendo `unidad` desde `inv_rangos` por `cod_articulo`.
  - Retornar `{ materiales: [...], productos: [...], tiempos: { alistamiento, produccion, empaque, limpieza } }`.
- `PUT /api/gestion/tareas/:id/produccion/lineas/:lineaId` — actualizar `cantidad_real` de una línea.
- `PUT /api/gestion/tareas/:id/produccion/tiempos` — actualizar los 4 campos de tiempo.

**Seguridad**: reusar `requireAuth` y `verificarPermisoEstado` del patrón actual.

---

## Frontend — nuevo componente `DetallesProduccion.vue`

### Ubicación en el panel
Dentro de [TareaPanel.vue](sistema_gestion/app/src/components/TareaPanel.vue), reemplazar el bloque actual "OP Effi + detalle OP" (líneas 68-83) por un acordeón "▸ Detalles de producción" que aparece solo si `esProduccion && tarea.id_op`. Contenido:

1. **OP vinculada** — OpSelector (ya existe, se mantiene).
2. **Bloque Materiales consumidos** — tabla con:
   - Columnas: `Material` | `Teórico` (valor gris pequeño) | `Real` (input numérico editable, placeholder = teórico) | `Unidad`
   - Input de cantidad real: acepta `,` y `.` como decimal (normalizar en frontend con `.replace(',', '.')` antes de enviar). Guardar onblur / tras 800ms debounce.
3. **Bloque Artículos producidos** — misma tabla, mismo patrón, contra `cod_articulo`.
4. **Bloque Tiempos** (UX del ASCII que mandaste):
   - 4 inputs estilo fila: Alistamiento / Producción / Empaque / Limpieza, sufijo "min".
   - Total calculado en vivo abajo (suma reactiva).
5. **Observaciones** — textarea (reusa el campo `notas` de la tarea — no duplicar por ahora).

### Estilo
Seguir patrón Quasar + manual de estilos (chips, `field-row`, `input-field`). Acordeón con `chevron_right`/`expand_more` como ya existe en [TareaPanel.vue:186](sistema_gestion/app/src/components/TareaPanel.vue#L186) para "Más campos".

### Normalización decimal (criterio Santi)
Helper util `parseDecimal(str)` en `src/services/numero.js`:
```js
export function parseDecimal(v) {
  if (v == null || v === '') return null
  const s = String(v).trim().replace(',', '.')
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}
```
Display: `Number(n).toLocaleString('es-CO', { maximumFractionDigits: 3 })` → muestra `1,2` en UI pero guarda `1.2`.

---

## Fases

### Fase 1 — Datos y API (backend)
- [ ] Migration: crear `g_tarea_produccion_lineas` + ALTER `g_tareas` para los 4 tiempos.
- [ ] Backup BD antes: `mysqldump g_tareas > backups/os_gestion/pre_produccion_{ts}.sql`.
- [ ] Implementar endpoint GET con lógica de siembra desde Effi (JOIN entre os_gestion y os_integracion vía conexiones separadas + lookup de unidad en os_inventario local).
- [ ] Implementar 2 endpoints PUT.

### Fase 2 — Frontend componente
- [ ] Crear `DetallesProduccion.vue` con los 3 bloques.
- [ ] Helper `parseDecimal` + formateo display.
- [ ] Integrar en TareaPanel, reemplazar bloque OP actual.
- [ ] Test Chrome DevTools MCP en web y móvil. Abrir una tarea real con OP (ej. la #455 que tiene OP hoy) y verificar que se carga la lista correcta.

### Fase 3 — Pulido
- [ ] Debounce de 800ms en inputs para no guardar en cada tecla.
- [ ] Indicador visual "modificado" (color de borde del input) cuando real ≠ teórico.
- [ ] Botón "Actualizar desde OP" (sincroniza si Effi cambió) — opcional, a validar con Santi.

---

## Decisiones abiertas (bloquean Fase 1)

- [ ] **¿Las 4 categorías de tiempo son fijas (Alistamiento, Producción, Empaque, Limpieza)?** ¿O necesitás una 5ª como "Transporte" o "Preparación"? Si son fijas, las dejo como columnas en `g_tareas`. Si cambia en el tiempo, mejor una tabla chica `g_tarea_tiempo_categoria`.
- [ ] **Snapshot vs live de unidades**: hoy propongo snapshot al sembrar. Si un artículo cambia de unidad en `inv_rangos` después, la tarea conserva la unidad original. ¿Está bien así?
- [ ] **¿Qué hacer si la tarea tiene `id_op` pero esa OP no tiene materiales ni productos en Effi?** Propongo: mostrar mensaje "Esta OP aún no tiene materiales/productos registrados en Effi" y dejar los bloques vacíos, sin romper.
- [ ] **¿El bloque de producción debe aparecer en tareas sin OP vinculada?** Hoy propongo: **no** — solo cuando hay `id_op` y categoría producción. Si querés que se puedan registrar consumos "a mano" sin OP, hay que cambiar el diseño.

---

## No incluido en este plan (a pedido de Santi)

- Ventas / CRM / Contacto / Etapas del embudo → cuando el CRM esté listo.
- Subcategorías dentro de Ventas → se crean en el CRM.
- Botón "+ agregar consumo" manual → no, por ahora solo lo que viene de Effi.

---

## Tareas para Antigravity (Google Labs)

- QA visual del componente una vez implementado: comparar contra el mockup a nivel de spacing, tipografía, alignment.
- Revisar que la UX de "Teórico / Real" sea clara para un usuario nuevo.

## Tareas para Subagentes (Claude)

- Implementación Fase 1 (backend): subagente `feature-dev:code-architect` diseña el endpoint GET con los 3 JOINs (os_gestion + os_integracion + os_inventario).
- Implementación Fase 2 (componente Vue): tras Fase 1 OK, subagente genera `DetallesProduccion.vue`.
