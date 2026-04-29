# PENDIENTES — Integraciones OS

Backlog vivo de **deuda técnica, seguridad y estandarización**. NO va aquí trabajo de feature ni bugs urgentes (esos van a `.agent/planes/activos/` o se resuelven en sesión).

## Cómo usar este archivo

### Cuándo agregar un item
- Detectaste algo que **NO es bloqueante ahora** pero hay que limpiar (creds en código, paths absolutos, código duplicado, falta de tests, dependencias viejas).
- Decidiste un atajo consciente que hay que volver a tocar después.
- Encontraste un anti-patrón que debería estandarizarse.

### Cuándo NO agregar
- Bug que rompe algo en producción → arreglar en la sesión.
- Feature pedido por Santi → plan en `.agent/planes/activos/`.
- Idea sin base concreta → no anotar.

### Formato de cada item

```markdown
### [P{1|2|3}] Título corto y accionable
**Categoría**: seguridad | limpieza | estandarización | dependencias | tests | docs
**Detectado**: YYYY-MM-DD por {quien}
**Contexto**: ¿qué pasa hoy? ¿por qué es deuda? (2-3 líneas)
**Riesgo si no se hace**: qué podría romper o qué fricción genera
**Acción propuesta**: pasos concretos (1-5 bullets)
**Archivos involucrados**: rutas relativas
**Estimado**: S (<30min) / M (30min-2h) / L (>2h)
```

### Prioridades
- **P1** — Riesgo activo (seguridad, datos, fragilidad operativa). Atender en la próxima sesión disponible.
- **P2** — Deuda significativa que enlentece el trabajo. Atender en 1-2 semanas.
- **P3** — Mejora deseable, sin urgencia. Atender cuando haya espacio.

### Cuándo cerrar un item
Al resolverlo: mover el bloque entero a `## ✅ Resueltos` con la fecha de cierre y commit relacionado. NO borrar — sirve de bitácora.

### Reglas
- Un item por bloque, sin mezclar problemas distintos.
- Mantener este archivo bajo 400 líneas. Si crece más, separar por dominio (`PENDIENTES_SEGURIDAD.md`, etc).
- Siempre revisar este archivo al inicio de sesión si Santi pide "tarea de limpieza" o "una tarde sin features".

---

## 🔴 Pendientes activos

### [P1] Credenciales Effi hardcodeadas en código fuente
**Categoría**: seguridad
**Detectado**: 2026-04-29 por Claude (al regenerar sesión Effi caída)
**Contexto**: `scripts/session.js` líneas 6-7 tienen `EFFI_USER` y `EFFI_PASS` como string literales en el código, versionado en git. Cualquiera con acceso al repo puede loguearse en Effi como Origen Silvestre.
**Riesgo si no se hace**: credenciales filtradas si el repo se vuelve público o se comparte por error; rotar el password en Effi exige nuevo commit + push.
**Acción propuesta**:
- Mover `EFFI_USER` y `EFFI_PASS` a `integracion_conexionesbd.env` (ya gitignored)
- Leer con `process.env.EFFI_USER` / `process.env.EFFI_PASS` en `session.js` (cargar dotenv si no está)
- Actualizar `integracion_conexionesbd.env.example` con los keys
- Documentar en MANIFESTO §8B
**Archivos involucrados**: `scripts/session.js`, `integracion_conexionesbd.env(.example)`
**Estimado**: S (15 min)

### [P2] `session.js` usa path absoluto `/scripts/session.json`
**Categoría**: estandarización (viola CLAUDE.md "paths relativos")
**Detectado**: 2026-04-29 por Claude
**Contexto**: `scripts/session.js` línea 4: `const SESSION_FILE = '/scripts/session.json'`. Funciona en local y VPS gracias a un symlink `/scripts → ~/Proyectos_Antigravity/Integraciones_OS/scripts`, pero rompe el principio "paths relativos" de MANIFESTO §8A. Si el repo se monta en otro path (CI, otro server, container), falla.
**Riesgo si no se hace**: imposibilita correr el repo desde otro directorio; nuevos colaboradores se chocan con el symlink mágico.
**Acción propuesta**:
- Cambiar a `path.join(__dirname, 'session.json')` (Node, relativo al script)
- Verificar que `import_orden_produccion.js`, `import_ajuste_inventario.js` y otros que también usan `/scripts/...` se actualicen
- Eliminar el symlink `/scripts` del VPS (y del local si existe) tras confirmar que nada lo usa
**Archivos involucrados**: `scripts/session.js`, `scripts/import_orden_produccion.js`, `scripts/import_ajuste_inventario.js`, otros `scripts/*.js`
**Estimado**: M (45 min) por la verificación cross-archivo

### [P2] `session.js` no se ejecuta solo (solo exporta `getPage`)
**Categoría**: limpieza
**Detectado**: 2026-04-29 por Claude (al intentar regenerar sesión)
**Contexto**: `scripts/session.js` exporta `getPage` pero no tiene bloque `if (require.main === module)`. Correr `node scripts/session.js` no hace nada — silencioso. Hay que invocar `require('./session.js').getPage()` desde otro script o `node -e`.
**Riesgo si no se hace**: confusión operativa cuando hay que regenerar sesión manualmente; documentación rota (los comentarios dicen "regenerar con scripts/session.js").
**Acción propuesta**:
- Agregar al final de `session.js`:
  ```js
  if (require.main === module) {
    getPage().then(({browser}) => browser.close()).catch(e => { console.error(e); process.exit(1) })
  }
  ```
- Probar: `node scripts/session.js` debe loguear y guardar
**Archivos involucrados**: `scripts/session.js`
**Estimado**: S (5 min)

---

### [P3] Sincronización maestra de unidades Hostinger → local
**Categoría**: estandarización
**Detectado**: 2026-04-29 por Claude
**Contexto**: Tabla `prod_unidades_medida` (en `inventario_produccion_effi` VPS) se pobló el 29-abr con 22 filas copiadas one-shot desde `u768061575_os_comunidad.costos_unidades` (Hostinger) + 13 filas locales (temperatura, pH, °Brix, ppm, UFC, etc. que Hostinger no tiene). Si Hostinger agrega/edita unidades, la tabla local queda desactualizada.
**Riesgo si no se hace**: divergencia de catálogos; un usuario puede agregar una unidad nueva en Hostinger ERP y no aparecer en producción/recetas (o viceversa).
**Acción propuesta**:
- Crear `scripts/sync_unidades_hostinger.py` que copie `costos_unidades` → `prod_unidades_medida` (UPSERT por `simbolo`, marcar `origen='hostinger'`, no tocar las `origen='local'`)
- Programar via cron 1x/día (alineado con pipeline Effi)
- Para cualquier unidad agregada localmente que después aparezca también en Hostinger: actualizar `origen='hostinger'` y mantener
**Archivos involucrados**: `scripts/sync_unidades_hostinger.py` (nuevo), tabla `prod_unidades_medida`
**Estimado**: M (45 min)

---

## ✅ Resueltos
*(Items movidos aquí al cerrarse, con fecha y commit)*
