# Effi — POST directos para operaciones de OP

Investigación de los endpoints internos de Effi para **cambiar estado** y **anular** OPs, usados por Sistema Gestión al Procesar/Validar. Crear OP ya está documentado en `effi-tecnico/SKILL.md` (`/app/orden_produccion/crear`).

Captura realizada el 2026-05-12 con `scripts/_espiar_acciones_op.js` (intercepta con `page.route()` + `route.abort()` para no modificar datos reales en Effi).

---

## 1. POST `/app/orden_produccion/cambiar_estado`

Cambia estado de una OP (Generada → Procesada → Validado).

**Endpoint:** `POST https://effi.com.co/app/orden_produccion/cambiar_estado`

**Body (form-urlencoded):**

| Campo | Tipo | Ejemplo | Notas |
|---|---|---|---|
| `id` | token cifrado URL-encoded | `hQ2p1FzZBS7yIld27criHQ%3D%3D` | Igual que `articulo/anular` — hay que scrapearlo del HTML de `/app/orden_produccion` |
| `est_orden_produccion` | int | `2` = Procesada, `3` = Validado | (`1` = Generada, `4` = Anulada — probables) |
| `observacion` | string | `Reportó: Jennifer · Validó: Santiago` | Texto libre |

**Cómo obtener el `id` (token cifrado):**

GET `https://effi.com.co/app/orden_produccion` → parsear HTML → encontrar la fila de la OP por id_orden numérico → extraer `data-codigo` del `<a>` o `<button>` de cambiar estado (mismo patrón que el modal Anular Articulo).

Mismo gotcha que articulo_anular: viene URL-encoded, des-encodear con `urllib.parse.unquote()` antes de POSTear.

---

## 2. POST `/app/orden_produccion/anular`

Anula una OP (no se puede deshacer).

**Endpoint:** `POST https://effi.com.co/app/orden_produccion/anular`

**Body (form-urlencoded):**

| Campo | Tipo | Ejemplo | Notas |
|---|---|---|---|
| `id` | **id_orden numérico** | `2271` | NO requiere token cifrado — el id directo funciona |
| `sucursal` | int | `1` | Principal |
| `observacion_anular` | string | texto libre | Razón de la anulación |
| `session_empresa` | int | `12355` | (Constante de la cuenta — viene del HTML) |
| `session_usuario` | string | `origensilvestre.col@gmail.com` | Usuario que anula |

**Nota:** los campos `session_*` aparecen en el body pero Effi los puede inferir del cookie de sesión — probablemente sean opcionales. Verificar en implementación.

---

## 3. POST `/app/orden_produccion/crear` (referencia)

YA documentado en `.claude/skills/effi-tecnico/SKILL.md §POST /app/orden_produccion/crear`. Ya hay script `scripts/import_orden_produccion_post.py` (~3-5s vs 60-90s Playwright).

Response devuelve JSON con `OP_CREADA:<id_orden>` que se captura para los pasos siguientes.

---

## 4. Implementación de "Procesar" (POST)

1. **GET** `/app/orden_produccion` para scrapear el token del `id_orden` objetivo.
2. **POST** `/app/orden_produccion/cambiar_estado` con `est=2`, token, observación.

Tiempo estimado: **~2-3s** (vs 30-60s Playwright). **Mejora ~15x**.

---

## 5. Implementación de "Validar" (POST)

Tres pasos secuenciales:

1. **POST** `/crear` con materiales/productos reales → captura `id_nueva`.
2. **GET** `/app/orden_produccion` para scrapear el token de la `id_nueva`.
3. **POST** `/cambiar_estado` con `est=3`, token de id_nueva, observación.
4. **POST** `/anular` con `id=id_original` (numérico, sin token).

Tiempo estimado: **~5-8s** (vs 2-3 min Playwright). **Mejora ~18-30x**.

---

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Token cifrado expira / cambia entre páginas | Re-scrapear antes de cada POST cambiar_estado |
| Effi agrega CSRF token nuevo | Si POST devuelve 4xx, capturar via espía y agregar al payload |
| Effi cambia formato HTML del token | Fallback Playwright; mantener el script `cambiar_estado_orden_produccion.js` como respaldo |
| `session_*` resultan obligatorios | Ya los capturamos, agregar al body siempre |

**Patrón de fallback:** seguir el mismo enfoque que `import_orden_produccion_post.py` — try POST, except → Playwright. En Sistema Gestión `_jobValidar` puede tener un flag `usar_post=true` que invoca el camino rápido y cae al lento si algo falla.

---

## 7. Validación end-to-end (2026-05-12)

Probado en OPs reales de Effi (OP-2280 y OP-2281, ambas anuladas al final como cleanup).

| Operación | Script | Tiempo medido | Body Effi |
|---|---|---|---|
| **Crear OP** | `import_orden_produccion_post.py` | 0.12s | `OK` |
| **Cambiar estado → Procesada** | `cambiar_estado_orden_produccion_post.py 2280 Procesada` | 0.66s (0.58s GET token + 0.08s POST) | `OK` |
| **Cambiar estado → Validado** | `cambiar_estado_orden_produccion_post.py 2280 Validado` | 0.65s | `OK` |
| **Anular** (estado Generada) | `anular_orden_produccion_post.py 2281` | 0.32s (0.14s GET session + 0.18s POST) | `OK` |
| **Anular** (estado Validado) | `anular_orden_produccion_post.py 2280` | 0.21s | `OK` |

**Confirmado:**
- El endpoint `/anular` acepta OPs en cualquier estado (Generada, Procesada, Validada).
- El token cifrado de `/cambiar_estado` se scrapea bien con regex `class="cambiar_estado"\s+data-prefijo_id="<ID>"\s+data-id="([^"]+)"`.
- `urllib.parse.unquote()` del token es necesario antes de pasarlo a `requests.post(data=)` para evitar doble encoding.
- Después de anular, la fila en Effi tiene fondo rosado y desaparecen las acciones "Cambiar estado" / "Anular".

## 8. Próximos pasos (implementación en server.js)

- [ ] Modificar `server.js _jobProcesar` para invocar `cambiar_estado_orden_produccion_post.py` en lugar del Playwright
- [ ] Modificar `server.js _jobValidar` para usar los 3 POSTs en cascada (crear + cambiar_estado + anular)
- [ ] Mantener los `.js` Playwright como fallback (try POST → catch → Playwright)
- [ ] Probar en una OP real del flujo gestión completo

---

## Apéndice — capturas raw

- `/tmp/espia_cambiar_estado_procesada_2273.json` — Procesar OP-2273 (est=2)
- `/tmp/espia_cambiar_estado_validado_2272.json` — Validar OP-2272 (est=3)
- `/tmp/espia_anular_2271.json` — Anular OP-2271

Script de espionaje: `scripts/_espiar_acciones_op.js`. Reusable para otras acciones — solo necesita el flow Playwright correcto.
