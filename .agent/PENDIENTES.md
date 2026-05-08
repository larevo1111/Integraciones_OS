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

### [P2] Validar y aplicar puntos críticos de calidad a las 13 recetas PP CLAVE
**Categoría**: estandarización (módulo calidad)
**Detectado**: 2026-04-30 por Claude
**Contexto**: Tabla `prod_recetas_puntos_criticos` ya creada y editor frontend funcionando. Doc `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md` tiene 10 procesos identificados con plantillas sugeridas (T°/tiempo/pH/sabor). **Estado al 30-abr: 0/99 recetas con puntos definidos**. Proceso de validación arrancado lote por lote con Santi pero sin terminar (esperando rangos REALES de planta para cada proceso).
**Riesgo si no se hace**: el módulo Gestión OS ya tiene listo el frontend para mostrar puntos críticos al validar OPs, pero sin datos quedaría vacío. Sin puntos críticos, el operario no sabe qué medir.
**Acción propuesta** — completar lote por lote con Santi, en este orden (cada lote = 1 sesión corta de validación + UPDATE):
1. **Lote 1: Pasteurización miel** (cod 373, 586, 60). 4 puntos sugeridos: T° máx 60-65°C, tiempo 20-30min, pH 3.5-4.5, sabor/olor. ESPERANDO rangos REALES de Santi (puede ser HTST 50-58°C ó LTLT distintos). → Aplica a 27 SKUs derivados.
2. **Lote 2: Templado chocolate** (cod 583, 581, 485). Sugerido: T° fusión 45-50°C, T° trabajo 31-32°C, test PAPEL (no cuchillo). → Aplica a 30+ SKUs (tabletas/bombones/granulados/coberturas).
3. **Lote 3: Cocción mesa** (cod 73, 74). Sugerido: T° 70-85°C, tiempo 30-45min, sabor.
4. **Lote 4: Chocobeetal granel** (cod 275). Sugerido: T° fusión chocolate, T° mezcla con polen, sabor.
5. **Lote 5: Resto** — Chocomiel (346), Infusión cacao+menta+polen (339), Marañón tostado (516), Cremas molienda (151/479/367/388), Tostado cacao (80/178/261), Tostado frutos secos.
**Cómo aplicar (post validación)**: INSERT en `prod_recetas_puntos_criticos` (FK `receta_id` del cod base). El módulo Gestión OS leerá esta tabla al armar sección de validación de OP. Los SKUs derivados heredan los puntos del proceso base.
**Doc referencia**: `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md` §4 (plantillas escritas, falta validar rangos).
**Archivos involucrados**: BD `prod_recetas_puntos_criticos` (no toca código).
**Estimado**: M (15 min × 5 lotes = ~75 min total, distribuido en sesiones cortas con Santi)

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

### [P2] Bug: PATCH `/api/ia/tipos-admin/:tipo` falla por columna inexistente
**Categoría**: limpieza
**Detectado**: 2026-05-08 por Claude (al configurar agente_preferido para demo)
**Contexto**: El endpoint usa `WHERE tipo=?` pero la columna real en `ia_tipos_consulta` se llama `slug`. La query falla con `Unknown column 'tipo' in 'WHERE'`. El PUT de la misma ruta sí usa `WHERE slug=?` y funciona — workaround actual es hacer PUT preservando todos los campos.
**Riesgo si no se hace**: cualquier cambio parcial de un tipo de consulta debe pasar por PUT (más verboso, más fácil de pifiar) en lugar de PATCH puntual. Sin impacto en producción mientras nadie use PATCH.
**Acción propuesta**:
- En `ia-admin/api/server.js:555`, reemplazar `WHERE tipo=?` por `WHERE slug=?`.
- Considerar agregar guardas: rechazar si `req.body` está vacío o tiene claves no whitelisted.
- Reiniciar `os-ia-admin.service` en server local.
**Archivos involucrados**: `ia-admin/api/server.js` (línea 555)
**Estimado**: S (5 min + restart)

---

### [P2] Bug: GET `/api/ia/superagente/sesiones` falla con `Unknown column 's.mensajes'`
**Categoría**: limpieza
**Detectado**: 2026-05-08 por Claude (smoke check super agentes)
**Contexto**: El endpoint hace `SELECT s.id, s.usuario_id, s.updated_at, s.mensajes ... FROM sa_sesiones s` pero esa tabla NO tiene columna `mensajes` (los mensajes de SA Claude viven en `~/.claude/projects/.../*.jsonl`, los de SA OpenCode en `~/.local/share/opencode/opencode.db`). Además solo lee `sa_sesiones` (Claude) y nunca `saoc_sesiones` (OpenCode).
**Riesgo si no se hace**: el panel admin web no puede listar sesiones de super agentes. Si Santi quiere ver historial de sesiones de SA antes/después de la demo, no puede sin hacer SSH al server local.
**Acción propuesta**:
- Refactorizar el endpoint para leer de ambas tablas (`sa_sesiones` y `saoc_sesiones`) y devolver una lista unificada con campo `tipo_agente: claude|opencode`.
- Eliminar referencia a `s.mensajes`. Si se quiere conteo de mensajes, leer del filesystem (Claude) o de `opencode.db` (OpenCode) en background — por ahora dejarlo en `null`.
- Mismo refactor para `GET /api/ia/superagente/sesiones/:id` (línea 1286).
- Reiniciar `os-ia-admin.service`.
**Archivos involucrados**: `ia-admin/api/server.js` (líneas 1257-1283 y 1286-1292)
**Estimado**: M (30-45 min)

---

## ✅ Resueltos
*(Items movidos aquí al cerrarse, con fecha y commit)*
