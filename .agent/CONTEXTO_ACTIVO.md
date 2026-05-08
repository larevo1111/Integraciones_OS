# Contexto Activo — Integraciones OS
**Actualizado**: 2026-05-08

## Completado 2026-05-08 — Sistema Gestión: Sección Calidad por OP (v2.10.30)

Digitalizada la bitácora de calidad en papel como bloque dentro de cada OP en `OpPanel.vue`. Combina:
- **Inspección visual genérica** (4 booleanos: visual / tapado / etiqueta / sabor-olor) → para todos los productos
- **Mediciones de Puntos Críticos** (dinámicos por receta, leídos de `prod_recetas_puntos_criticos` BD `inventario_produccion_effi`) → según producto principal de la OP
- **Defectos** (críticos/mayores/menores con stepper +/-)
- **Resultado** (Aprobado / Rechazado / Liberado con observación) + auto-firma del usuario logueado

**BD nueva** (en `os_gestion` VPS):
- `g_op_inspeccion_calidad` — 1 row por inspección con snapshot completo de muestreo + booleanos + defectos + resultado + inspector
- `g_op_pc_registro` — 1 row por PC medido (FK a inspeccion). Snapshot de parametro/tipo/unidad/rango por si la receta cambia. Calcula `dentro_rango` server-side.

**Backend** (3 endpoints nuevos en `/api/gestion/op/:id/calidad/...`):
- `GET .../sugerencia` — devuelve PCs de la receta del producto principal + AQL sugerido (ANSI/ASQ Z1.4 simplificado: 2-15→2, 16-25→3, 26-50→5, 51-90→8, 91-150→13, 151-280→20, 281+→32)
- `GET ` — lista inspecciones con sus PCs
- `POST ` — crea inspección + PCs en transacción

**Frontend**:
- Nuevo `CalidadPanel.vue` — mobile-first, 5 sub-bloques (muestreo / visual / mediciones PCs / defectos / resultado). Indicador ✓/✗ por rango en cada PC numérico. Auto-rechazo + obs obligatoria si defectos críticos>0.
- `OpPanel.vue` — embebe CalidadPanel entre Tiempos y Tareas. Soft-block al validar: dialog warning si calidad rechazada o sin inspección (no bloquea, el director decide).

**Restricciones de alcance** (acordadas con Santi):
- Calidad vive 100% en `os_gestion`. NUNCA toca Effi (no estados nuevos, no workflows).
- Workflow de no conformidad / reproceso / descarte → fase ERP futura.

Plan: `.agent/planes/completados/calidad_inspeccion_op_2026-05-08.md`.

---

## Completado 2026-05-06 — Incidente login Google OAuth (root cause + fix definitivo) — v2.10.28

**Síntoma**: Deivy y Santi vieron error 400 "Missing required parameter: client_id" al hacer login con Google en `gestion.oscomunidad.com`. La app llevaba ~36h funcionando con bundle silencioso roto.

**Root cause** (combo de 3 cosas):
1. El 4-may a las 23:11, alguien hizo `npm run build` directo en VPS sin tener `sistema_gestion/app/.env` (gitignored). El bundle salió con `clientId: undefined` — sin error visible.
2. Service Worker de la PWA tenía cacheada la versión buena anterior → users seguían viendo la app funcionar mientras el bundle servidor estaba roto.
3. El 6-may en la mañana el SW detectó hash distinto en `sw.js`, invalidó cache, descargó bundle nuevo (roto) → todos los users empezaron a fallar **sin que nadie tocara nada hoy**.

**Investigación descartó hacker**: último login SSH externo fue 3-may, sin sesiones code-server hoy, cron `sync-repo.sh` solo hace `git pull` (sin build), sync.log muestra "Sin cambios" todas las ejecuciones del día.

**Fix definitivo** (v2.10.28):
- Eliminado `.env` (local + VPS).
- Nuevo archivo `sistema_gestion/app/src/config/oauth.js` con `export const GOOGLE_CLIENT_ID = '...'` committeado.
- `boot/googleAuth.js` y `LoginPage.vue` importan desde ahí (no `import.meta.env.VITE_*`).
- Quitado `VITE_GOOGLE_CLIENT_ID` de `quasar.config.js > build.env` (descubrimos que ese mecanismo deja `clientId: void 0` en el bundle — Quasar v2 + Vite v5 no inyecta `import.meta.env.VITE_*` desde `build.env` correctamente).
- Bundle deployado verificado: client_id presente en `oauth-*.js` chunk.

**Lección**: Secrets PÚBLICOS (Google client_id, Stripe pk_, Sentry DSN) NO van en `.env` — van committed. `.env` es solo para secrets verdaderos que NO deben quedar en repo. Memoria: `feedback_secrets_publicos_no_env.md`.

**Acción para users con caché vieja**: incógnito (Ctrl+Shift+N) o F12 → Application → Service Workers → Unregister + Clear site data.

---

## Completado 2026-05-05 — Scripts POST cotización/remisión + fix sesión producción

Sesión desde VPS. 4 frentes resueltos.

### A. Scripts POST directo nuevos (cotización venta + remisión compra)
- **`scripts/import_cotizacion_venta_post.py`** — POST a `/app/cotizacion/crear`, ~1s vs 60-90s Playwright.
  - Calcula `total_impuesto` sumando `base × TASAS_IMPUESTO[id]` por línea
  - Valida respuesta: `json.loads(body)` → `respuesta == 'OK'`
  - Detecta id de cotización creada via MAX(data-id) antes/después
- **`scripts/import_remision_compra_post.py`** — POST a `/app/remision_c/crear`, misma lógica.
  - Campos extra vs cotización: `t_egreso[]`, `medio_pago[]`, `caja_medio_pago[]` (sep `Ǆ`), `valor_medio_pago[]`, `action='1'`, `json_ref=''`
  - Sin `vendedor`, `propina`, `tercero`

### B. Cotización #1610 creada — La Viña
- 13 artículos "entregado" del xlsx `cruce_factura_inventario_TomaCafeLaVina.xlsx`
- Cliente La Viña: id Effi **793** (resuelto via paginación `llena_tercero_buscar`)
- Precios Tarifa A: de `zeffi_cotizaciones_ventas_detalle.precio_ta_a` / `zeffi_inventario.precio_ta_a`
- Vendedor: Jenifer CC `1128457413` → id Effi **165** (de `zeffi_facturas_venta_encabezados`)
- IVA por artículo: Propóleos=Exento(2), Mieles/Almendras/Bombones/Nibs=Excluido(7), Tabletas/Chocomiel/Cremas=19%(1)

### C. Skill `effi-tecnico` — Reglas comunes cotización + remisión
Bloque nuevo "Reglas comunes" añadido antes de `### POST /app/cotizacion/crear`:
1. **`impuestos[]` NUNCA vacío** — mapeo completo string→id (IVA 19%→1, Exento→2, 5%→3, 14%→4, INCBP→5, consumo 8%→6, Excluido→7). SQL de referencia incluido.
2. **`vendedor` desde última factura** — SQL sobre `zeffi_facturas_venta_encabezados`, NO desde `zeffi_clientes` (suele ser NULL).
3. **`t_forma_pago='1'`** (Contado a 1 día) — SIEMPRE, sin excepciones.

### D. Fix producción — renovación de sesión Effi antes de Playwright completo
**Problema**: cuando la sesión expira, el fallback usaba Playwright COMPLETO (login + crear OP = ~90s). Aunque el auto-login funcionaba, el usuario veía "programando" por ~90s.

**Solución**:
- Nuevo **`scripts/refresh_session.js`** — solo hace login Playwright, cierra el browser, actualiza `session.json`. (~25s)
- En `scripts/produccion/api.py` (`_ejecutar_op_background`): cuando POST directo falla por sesión expirada → llama `refresh_session.js` (~25s) → reintenta POST directo (~1s) → solo si falla cae al Playwright completo.
- Resultado: sesión expirada = ~27s vs ~90s antes.
- **Requiere reiniciar**: `sudo systemctl restart os-inventario-api.service`

### Pendientes inmediatos
- Inventario Jenifer (sigue vacío)
- Bug visual jornada (pausa 12:29-14:00 se pinta como 01:29-02:00 PM). BD y Excel correctos.

---

## En curso 2026-05-05 — Cierre inventario 30-abr + OP 2241 Arancel + sistema de notas por inventario

Continuación de la sesión anterior. 4 frentes resueltos:

### A. Remisión de compra #479 (UNICOR) sumada al inventario 30-abr
- Remisión #479 (04-may 17:12, $359.784,60) trae 4 envases UNICOR (cods 85, 86, 87, 88) — pagados abril, recibidos 04-may, entregados a Arancel para envasado.
- **Sync directo SQL** `effi_data` → `os_integracion` (4 tablas: zeffi_remisiones_compra_*, zeffi_ordenes_compra_*) tras correr `export_remisiones_compra.js` + `import_all.js`. El pipeline cron se evita para hacer un fix puntual.
- Sumadas las 4 cantidades al `inventario_fisico` de cada cod en bodega Principal (UPDATE en `inv_conteos`).

### B. OP 2241 — Arancel envasado miel (creada en Effi)
- **Producto**: Mieles SIN ETIQUETAR — Arancel vendió 97 kg miel a OS y la envasó en los envases UNICOR de la remisión #479.
- **Encargado**: Arancel Apicultor San Miguel (CC 3184970152)
- **Materiales** (5): cod 373 (97 kg miel × $21.000) + 4 envases UNICOR
- **Productos** (4): 36×550 + 48×547 + 72×546 + 72×548 (mieles SIN ETIQUETAR)
- **Otro costo**: id 8 ENVASADO MIEL APICA × 228 unds × $500 = $114.000
- Creada via Playwright (`import_orden_produccion.js` con `/tmp/op_arancel_2026-05-04.json`) — POST directo no aplica porque CC de Arancel no está en MAPEO_ENCARGADOS.
- Patrón clonado de OP 2040 (8-mar) — misma combinación de envases/cods/encargado.

### C. Sistema de notas por inventario — OBLIGATORIO
**Pattern**: `inventario/analisis_de_inventario/<YYYY-MM-DD>/notas.md` (uno por evento de inventario, versionado en repo).
- Sección agregada al skill `inventario-fisico/SKILL.md` con estructura mínima, cuándo escribir, por qué importa (5S Shitsuke).
- Creado `inventario/analisis_de_inventario/2026-04-30/notas.md` documentando:
  - Excepciones: precarga Cacao SL (cods 593/594), remisión 479 sumada
  - OP derivada: 2241 Arancel
  - Decisiones de criterio: OV #720, consignación, 14 cods T999/T05, 13 anulados con stock, 8 negativos
  - Pendientes: regularizar Cacao SL, sistemizar "compras pagadas en otro mes"
  - Backups asociados

### D. Skill `produccion-recetas` — sección "Línea ARANCEL"
Agregada nueva sección con:
- Tabla envase UNICOR → grs miel → producto SIN ETIQUETAR (cods 86→548, 87→546, 88→547, 85→550)
- Costos: miel $21.000/kg, envasado id 8 $500/und
- Encargado fijo: Arancel CC 3184970152
- Patrón observación + ratio total típico (228 envases = 97.32 kg miel)

### Estado inventario 30-abr
| | |
|---|---:|
| Total filas | 410 |
| Inventariables contadas | 301 |
| Excluidos | 109 |
| Pendientes | 0 |
| Diferencias post-ajustes | 188 (62%) |

Backups generados (3, post-cada cambio significativo):
- `inventario_2026-04-30_2026-05-04_234901.sql` — pre-restauración SL
- `inventario_2026-04-30_post_precargas_2026-05-04_235430.sql` — post-restauración SL
- `inventario_2026-04-30_post_op2241_2026-05-05_004907.sql` — post-remisión 479 + OP 2241

CSV versionado: `inventario/snapshots/inventario_2026-04-30_fisico_completo.csv` (refrescado).

### Pendientes inmediatos
- Inventario Jenifer (sigue vacío)
- Bug visual jornada (pausa 12:29-14:00 se pinta como 01:29-02:00 PM, -1h offset). Solo en detalle UI; BD y Excel correctos.

---

## En curso 2026-05-04 — Inventario 30-abr cargado + 29 OPs Procesadas + 4 fixes backend + módulo teórico Paso 1/2

Sesión grande directa desde VPS. 8 frentes resueltos:

### A. Inventario físico 30-abr — completo y respaldado
- **410 filas en `inv_conteos`** (fecha 2026-04-30): 301 inventariables (todas contadas, 188 con diferencia) + 109 excluidos (T999/T05/XMATERIAL/sin gestión)
- **Bodegas activas**: Principal (283), Productos No Conformes (18), Jenifer (0 — pestaña visible aunque vacía)
- Teórico cargado del xlsx `inventario/snapshots/inventario_2026-04-30_teorico.xlsx` (export crudo Effi del 1-may, 372 vigentes, 68 columnas)
- Validado contra Paso 1 (trazabilidad): coincide 372/372 si se excluye OV #720 (1-may 00:03 KAKAW) — prueba que el xlsx representa el cierre real al 30-abr 23:59
- Iteraciones de carga (en orden):
  1. Script ad-hoc `scripts/inventario/crear_inventario_30abr_desde_xlsx.py` cargó 174 filas iniciales (solo con stock)
  2. Insertados 13 anulados-con-stock del 29-abr (cods 199, 204, 351, 352, 353, 354, 402, 403, 404, 70, 82, 372, 274) — perdidos en el primer pase porque ya estaban anulados
  3. Insertados 109 excluidos (con bodega='—') + 93 inventariables sin stock (Principal teórico=0) → 390 filas
  4. Detectadas y arregladas 22 discrepancias vs xlsx: 14 con stock que estaban excluidos por reglas (Santi pidió volverlos a marcar excluidos manteniendo el dato del xlsx) + 8 stocks negativos descartados por bug `stock <= 0` → 400 filas
  5. **Precargas físicas SL** (cacao San Luis recién creado en Effi): cod 593 NIBS = 97.5 kg, cod 594 CASCARILLA = 16 kg en Principal con teórico=0 → diferencia +97.5 / +16 (esos cods aún no estaban en zeffi al cierre)
  6. Equipo recontó las precargas a 0 sin saberlo → restauradas con `contado_por='precarga_30abr_xlsx'` y nota explícita
- Pendiente: agregar inventario Jenifer + una compra que falta antes del cierre definitivo
- **Backups**:
  - `backups/inventario_produccion_effi/inventario_2026-04-30_2026-05-04_234901.sql` (estado 100% contado, antes de restauración SL)
  - `backups/inventario_produccion_effi/inventario_2026-04-30_post_precargas_2026-05-04_235430.sql` (estado actual, post-restauración SL)
  - `inventario/snapshots/inventario_2026-04-30_fisico_completo.csv` (versionable en repo, 410 líneas)

### B. Reporte de mercancía en consignación al 30-abr (aparte del inventario)
Generados en `inventario/analisis_de_inventario/2026-04-30/`:
- `consignacion_al_30abr.md` — resumen
- `consignacion_al_30abr_detallado.csv` — 200 líneas (cod × ov)
- `consignacion_al_30abr_por_ov.csv` — 10 OVs vigentes no facturadas
- `consignacion_al_30abr_por_articulo.csv` — 48 artículos únicos

**Total**: 312 unidades, $5.879.323. Toda esta mercancía YA está descontada del `stock_total_empresa` de Effi (Effi descuenta al crear OV); como ninguna OV vigente tiene mercancía aún en planta (Santi confirmó), el teórico del xlsx es correcto y NO hay que ajustar.

### C. 30 OPs Generadas Vigentes resueltas en Effi
- **OP 2230 anulada** (test ALIEXPRESS, $0.10) via `anular_orden_produccion.js`
- **29 OPs pasadas a Procesada** via `cambiar_estado_orden_produccion.js` en serie (Playwright). Tiempo total: 7.6 min (~16s por OP — sesión Effi reutilizada). 29/29 OK, cero fallos.
- OPs procesadas: 2163, 2164, 2165, 2191, 2194, 2195, 2198, 2199, 2202, 2203, 2204, 2205, 2207, 2208, 2210, 2214, 2215, 2217, 2221, 2223, 2224, 2228, 2229, 2234, 2235, 2236, 2237, 2238, 2239

### D. Módulo Inventario teórico — Paso 1/2 separados
**Antes**: `calcular_inventario_teorico.py` hacía todo monolítico:
```
stock_actual − trazabilidad_post_corte + materiales_OPs_Generadas − productos_OPs_Generadas
```
**Ahora**: 2 funciones independientes idempotentes:
- `aplicar_trazabilidad(fecha)` — Paso 1: solo el rebobinado (`stock − movimientos`)
- `aplicar_ops_generadas(fecha)` — Paso 2: solo las OPs (`+ materiales − productos`)
- `calcular(fecha)` (legacy) llama ambas en orden (retro-compat)

CLI: `--paso traza|ops|completo` (default completo). Cada paso conserva el otro campo en `inv_teorico` (`ajuste_trazabilidad` vs `ajuste_ops_*`). `actualizar_conteos` ahora **respeta `excluido=1`** (no sobrescribe los excluidos).

2 endpoints nuevos:
- `POST /api/inventario/aplicar-trazabilidad`
- `POST /api/inventario/aplicar-ops-generadas`

3 botones en header del inventario (frontend producción):
- 🕘 `history` — Paso 1 (rebobinar trazabilidad)
- 🏭 `factory` — Paso 2 (excluir OPs Generadas)
- 📊 `analytics` — Cálculo completo (los 2 pasos en orden)

### E. Sistema Gestión — tabla OPs filtros corregidos (v2.10.28)
Problema: filtro "Generada" mostraba 320 OPs (290 anuladas + 30 vigentes); "Anuladas" mostraba 0 (filtraba mal).

**Solución**: nueva columna calculada `estado_efectivo` en endpoint `/api/gestion/op`:
```sql
CASE WHEN vigencia='Anulado' THEN 'Anulada' ELSE estado END AS estado_efectivo
```
Frontend `OpTablePage.vue` ahora usa `estado_efectivo` con 4 opciones (Generada/Procesada/Validado/Anulada). Quitada columna Vigencia separada (era redundante).

### F. Bug fix timezone en edición de jornadas (v2.10.28)
**Síntoma**: Santi editaba jornada Deivy 21-abr inicio=7am, fin=5:12pm, al guardar quedaba 12am - 10:12am (offset 7h).
**Causa raíz**: 3 endpoints en `server.js` usaban `new Date(hora_inicio)` raw o pasaban string sin convertir. `new Date("2026-04-21T07:00")` en VPS Berlin (CEST) interpreta como local CEST → guarda 7h offset.
**Fix limpio**: 6 líneas en 3 endpoints reemplazando `new Date()`/raw → `parseBackendDate()` (helper `lib/timezone.js`, ya usado en otros 7 lugares):
- `PUT /jornadas/:id/editar`
- `PUT /jornadas/:id/editar-admin`
- `PUT /jornadas/:id/pausas/:pausaId`

### G. Bug fix backend inventario "no matriculado" (v0.4.11)
**Síntoma**: error 500 al crear artículo no matriculado en la app.
**Causa raíz**: regresión del fix SSH tunnel del 28-abr. `DB_INV` ahora es un **string tag**, pero 3 endpoints en `api.py` seguían usando `pymysql.connect(**DB_INV)` directo (rompe porque `**` espera dict, no string).
**Fix limpio**: 3 líneas reemplazando `**DB_INV` → `**_resolve_cfg(DB_INV)` — mismo patrón que ya usan los wrappers `db_query`/`db_execute`. Mantiene la atomicidad multi-query (que se perdería al partir en wrappers individuales).

Líneas tocadas: `agregar_no_matriculado` (449), `asignar_no_matriculado` (508), `cerrar_inventario_calcular_severidad` (956).

### H. UI inventario — refactor a OsDataTable + ajustes mobile (v0.4.11)
- `tabla-conteo.jsx` reescrita usando `OsDataTable` (igual que el resto del proyecto). Filtros/orden/agregados/exportar funcionan igual a las otras tablas.
- 3 props nuevas en `OsDataTable`: `rowClassName`, `hideOnMobile`, `labelMobile`.
- **Mobile**: 4 columnas (ID 11px, Artículo+TEO chip+grupo, Cat MP/PP/PT short, Cnt). Categoría se muestra siempre (corta), no se oculta — habilita filtro por tipo.
- Filtros pills: padding/gap aumentados — antes apretado.
- Bodegas: pestañas fijas (Principal / Productos No Conformes / Jenifer) aunque tengan 0 (lista hardcodeada en frontend `BODEGAS_FIJAS`).
- Columna ID con `text-[11px]` (2pt menos que el resto, mejor jerarquía visual).

### I. CLAUDE.md — regla de versionamiento formalizada
Punto 11 reforzado + nueva sección §Manejo de versiones:
- Bump de versión OBLIGATORIO en cada commit que toca frontend/backend
- Tabla de archivos por módulo (Gestión: `MainLayout.vue`; Producción: `package.json`)
- Esquema semver (PATCH/MINOR/MAJOR)
- Flujo obligatorio de 5 pasos por commit
- "Sin excepciones — facilita detectar qué versión está en producción sin abrir consola"

### Versiones desplegadas
- **Sistema Gestión v2.10.28** (bundle `index-6Z8F8iP-.js`) — fix timezone jornadas + tabla OPs estado_efectivo
- **Producción + Inventario v0.4.11** (bundle `index-v0_4_11-Cdn7GGp-.js`) — paso 1/2 teórico + fix NM 500 + UI compacta + bodegas fijas

### Servicios reiniciados (vía kill — systemd Restart=always)
- `os-gestion.service` PID 1736759 (22:59:22)
- `os-inventario-api.service` PID 1736766 (22:59:22)

### Pendientes inmediatos
- Agregar inventario Jenifer (todavía vacío)
- Incluir una compra al inventario 30-abr (Santi tiene la info)
- Decidir si la 3a fila "contada" accidental fue limpiada — sí, se limpió (cod 479 quedó pendiente)

### Bug visual conocido (no urgente)
- Detalle de pausa en jornada muestra hora 12h con bug: pausa 12:29-14:00 (91 min en BD = 1h 31m) se muestra como "01:29 PM - 02:00 PM" (= 31 min en pantalla). El Excel y la BD están bien; solo el popup pinta mal. Diagnóstico pendiente.

---

## En curso 2026-05-03 — Cacao San Luis (cadena Effi creada) + inventario 30-abr en preparación

Sesión corta directa desde el VPS (no desde local como suele ser). Sincronizado repo (`git pull`) sin pérdida — cambios locales del VPS eran byte-idénticos al remoto, fueron stash+pull+drop.

### A. Cadena cacao San Luis creada en Effi (4 cods nuevos)
Detalle completo en [contextos/inventario_fisico.md §Hitos 2026-05-03](contextos/inventario_fisico.md). Resumen:
- **Cod 585** (ALMENDRA DE CACAO SAN LUIS x KG, $11.000) ya existía — MP base
- **Cods 593, 594, 595, 596** creados via `import_articulo_crear_post.py` — NIBS SL ($19.000), CASCARILLA SL ($3.300), COBERTURA CPM 73% TEMPLADA SL ($43.432), COBERTURA 100% TEMPLADA SL ($43.432)
- Patrón paralelo a LT (La Tierrita): mismo `tipo=2`, `categoria=3`
- Convención de nombres: `xxxxx SL x KG` (origen + unidad al final)
- Costos NIBS y CASCARILLA escalados por proporción de almendra ($11k SL vs $15k SC LT). Coberturas iguales que LT (no escalan con almendra cruda — usan cod 319 + manteca templada cod 485)

### B. Inventario 30 abril 2026 — snapshot teórico guardado
- Export crudo de Effi del estado al 30-abr (sacado por Santi el 1-may): `inventario/snapshots/inventario_2026-04-30_teorico.xlsx` (renombrado del original `12355_17776671858111_756017.xlsx`)
- 372 artículos vigentes, 68 columnas (stocks por 15 bodegas + costos completos + tarifas)
- **Físico pendiente de capturar** — debe incluir adicionales fuera del export Effi:
  - 97.5 kg NIBS DE CACAO SL (cod 593) en bodega Principal
  - 16 kg CASCARILLA DE CACAO SL (cod 594) en bodega Principal
  - (estos cods son nuevos en Effi, sin stock — entran al inventario por conteo físico de lo que ya está en planta)

### C. Sync repo VPS ↔ remoto
- VPS estaba en `f43802a`, remoto tenía 4 commits adelante incluyendo el upload del xlsx (`82b9b2a`)
- Cambios locales sin commitear (`db.js`, `server.js`, scripts de artículos) eran **byte-idénticos** al remoto
- Resuelto con: backup `/tmp/public_bak_*` → `git stash -u` → `git pull` → `git stash drop`

---

## Completado 2026-04-29 / 30 — Producción: editor recetas evolución + módulo calidad/puntos críticos + scripts artículos Effi POST directo + depuración 94 artículos

Sesión grande del 29-30 abr en módulo Producción (`inv.oscomunidad.com`), 7 frentes resueltos:

### A. Editor de recetas — evolución (v0.4.4 → v0.4.10)
- **Campo `observaciones_op`** en `prod_recetas` (TEXT). Texto fijo que se inyecta en la observación de la OP al programar. Editable desde `/recetas/:cod` + precarga editable en el textarea del modal "Programar". `_construir_observacion()` ahora arma 2 partes: rigor (auto: productos+usr+sols) + extra (lo del textarea, viene precargado de la receta y editado por el usuario). Límite Effi subido de 250 → 1000 chars.
- **Sección "Puntos críticos"** en `/recetas/:cod` — tabla editable con columnas: Parámetro, Tipo (numerico/booleano/texto/seleccion), Unidad (Combobox sobre maestra), Instrumento (datalist), Mín, Máx, Opciones (CSV), Obligatorio. Inputs Mín/Máx/Unidad disabled si tipo≠numerico; Opciones disabled si tipo≠seleccion.
- **Tabla nueva `prod_recetas_puntos_criticos`** (FK receta_id, ON DELETE CASCADE).
- **Maestra `prod_unidades_medida`** — 35 unidades (22 espejo de Hostinger `costos_unidades` + 13 locales para puntos críticos: °C, °F, pH, °Brix, %, ppm, aw, UFC/g, UFC/ml, µm, bar, psi, rpm). Endpoint `GET /api/produccion/unidades`.
- Backend: `RecetaPatch.observaciones_op` opcional + `PUT /api/recetas/{cod}/full` reescribe puntos_criticos + `RecetaPuntoCriticoIn`.
- Combobox unidad: `min-w-[220px]` en popover (antes salía truncado por trigger estrecho de la celda).
- Reorden encargados en preview OP: Deivy/Laura primero, Santi/Jenifer al final. Default ya no es el usuario logueado.

### B. Módulo histórico inconsistencias — campos nuevos + estandarización (v0.4.5)
- ALTER masivo `inv_analisis_inconsistencias` y `inv_ajustes_historico`: rename `fecha`→`fecha_analisis`/`fecha_ajuste`, +`fecha_inventario`, `tipo_inconsistencia` (enum 5), `estado` (abierto/en_revision/resuelto/descartado vs pendiente/aplicado/fallido/revertido), `inventario_teorico`, `inventario_fisico`, `costo_unitario`, `costo_total_impacto`, `fecha_planificado`, `costo_total`, `error_msg`, `updated_at`.
- Backfill 22 análisis + 22 ajustes del 28-abr con valores nuevos.
- Páginas refactoreadas a **estándar OsDataTable** (igual a Solicitudes), reemplazando tablas HTML crudas: `/inconsistencias`, `/historico-ajustes`, `/inconsistencias/:id`.
- Detalle: 4 cards de snapshot (Stock antes / Teórico / Físico / Impacto $) + botones cambiar estado del análisis + tabla de ajustes con todos los campos nuevos.
- Backend: filtros nuevos `?estado=`, `?tipo=`; agrega `total_ajustado` al listar; PATCH `/api/inventario/inconsistencias/{id}/estado` y `.../historico-ajustes/{id}/estado`.

### C. Auditoría 297 candidatos a depurar + 94 anulados en Effi
- Query a `os_integracion`: artículos vigentes + sin uso como material/producto/compra desde 2025-04-29 (1 año). Detectó **297 candidatos** ($4.066.140 valor inventario; 216 nunca usados; 64 con stock).
- Generado `inventario/analisis_de_inventario/2026-04-29/depuracion_articulos_inactivos.md` y `.csv` (separador `;`, UTF-8 BOM, columna `accion_sugerida` con 5 valores).
- Santi marcó **94 con X** en el CSV → ejecutados via script anular masivo.
- 1ra ronda detectó bug crítico (URL-encoding del token cifrado), 2da ronda con fix completó **94/94 anulados**. Reversibles vía "Reactivar" en Effi.

### D. Scripts artículos Effi POST directo (3 nuevos)
Espionaje vía Chrome DevTools MCP descubrió 3 endpoints:
- **`POST /app/articulo/anular`** — 3 campos (`codigo` token cifrado, `session_empresa`, `session_usuario`). Reversible.
- **`POST /app/articulo/crear`** — form `form_CART` ~47 campos. Devuelve "OK" sin id (id se obtiene via scrape post-create).
- **`POST /app/articulo/modificar_articulo`** — 50 campos = data actual + cambios + id real + session_*.

Hallazgo crítico: `data-codigo` del HTML viene URL-encoded (`%3D%3D`) y Effi lo espera ASÍ, NO desencodeado. Validación de éxito por `body=="OK"` (no por HTTP 200, Effi siempre devuelve 200).

Scripts (en `scripts/`):
- `import_articulo_anular_post.py` — cods sueltos / `--csv` / `--dry-run` / `--delay`
- `import_articulo_crear_post.py` — `--nombre/--tipo/--categoria/--costo` o `--json`
- `import_articulo_modificar_post.py` — `--cod N --nombre/--costo/--tipo/--categoria` (cambio parcial) o `--json`

Documentado en `.claude/skills/effi-tecnico/SKILL.md` §3 (3 endpoints) + §13 (tokens cifrados).

### E. Bitácora calidad y puntos críticos (`.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md`)
Doc consolidado con:
- **Modelo conceptual 5S**: Inspección de calidad (booleanos genéricos, vive en módulo Gestión OS) vs Puntos críticos (configurables por producto, vive en ficha receta).
- Reglas para definir puntos críticos: solo medible, máximo 3-5 por producto, cada parámetro debe generar acción.
- **Instrumentos disponibles en planta OS**: termómetro, cronómetro, balanza, pH-metro (en agua + nevera), revisión organoléptica, test de PAPEL para templado (NO cuchillo).
- **10 procesos productivos identificados** (cocción mesa, refinado/conchado, templado chocolate, pasteurización miel, cristalización miel, infusionado miel, tostado cacao, tostado frutos secos, crema molienda, infusión cacao+menta+polen, chocomiel, chocobeetal granel).
- **13 productos PP CLAVE** identificados (las presentaciones envasadas heredan los puntos del proceso base, no se duplican).
- Plantillas concretas por proceso con parámetros sugeridos. **En proceso de validación con Santi lote por lote**.
- Vinculación futura HACCP/ISO 22000.

**📍 Punto exacto donde quedamos al cerrar la sesión (30-abr)**:
- **Lote 1 — Pasteurización miel** (cod 373, 586, 60 → afecta 27 SKUs derivados): se le propusieron a Santi 4 puntos (T° máx 60-65°C, tiempo 20-30min, pH 3.5-4.5, sabor/olor) y **están esperando confirmación de rangos REALES de su planta** (probablemente distintos: la operación puede ser HTST 50-58°C ó LTLT 5-45min según su práctica) antes de aplicar via PATCH a las recetas.
- **Lotes pendientes (en orden)**: Lote 2 = Templado chocolate (cod 583, 581, 485) → Lote 3 = Cocción mesa (73, 74) → Lote 4 = Chocobeetal granel (275) → Lote 5 = Chocomiel + Infusión + Marañón.
- **Cómo aplicar**: una vez validados los rangos por proceso, INSERT en `prod_recetas_puntos_criticos` con `receta_id` del cod base. Las presentaciones derivadas leerán los puntos del proceso base (no se duplican — eso lo decide el módulo Gestión OS al armar la sección de validación de OP).
- **Doc de referencia para retomar**: `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md` §4 (plantillas por proceso ya escritas, falta validar rangos).

### F. Bug fix crítico: SystemExit en POST OP (29-abr 17:51)
3 solicitudes (83/84/85) quedaron colgadas en estado "programando" por sesión Effi caducada. El script `import_orden_produccion_post.py` abortaba con `SystemExit` que no era capturado por el wrapper FastAPI (solo captura `Exception`). Fix: 3 `raise SystemExit` → `raise RuntimeError`. Sesión regenerada en VPS via `node -e require('./session.js').getPage()...`

### G. Pipeline cron + mail (29-abr 17:30)
- `effi-pipeline.timer`: 2h → 1h (a pedido de Santi)
- Gmail App Password renovado: viejo `jovc hbxy sjlz noob` (caducado) → nuevo `ucpl lyfh dujr fprd`. Mail a `larevo1111@gmail.com` funcionando.

### Tablas BD nuevas / modificadas (todas en VPS `inventario_produccion_effi`)
- **`prod_recetas_puntos_criticos`** (NUEVA): id, receta_id FK, orden, parametro, tipo enum(numerico/booleano/texto/seleccion), unidad, instrumento, valor_min/max, opciones_json, obligatorio, created_at, updated_at
- **`prod_unidades_medida`** (NUEVA): id, simbolo UNIQUE, nombre, categoria, factor, origen enum(hostinger/local), activo
- **`prod_recetas`** (ALTER): + `observaciones_op TEXT NULL`
- **`inv_analisis_inconsistencias`** (ALTER): rename fecha→fecha_analisis, +fecha_inventario, tipo_inconsistencia, estado, inventario_teorico/fisico, costo_unitario, costo_total_impacto, updated_at
- **`inv_ajustes_historico`** (ALTER): rename fecha→fecha_ajuste, +fecha_planificado, estado, costo_total, error_msg, updated_at

### Versiones desplegadas
Producción: v0.3.5 → v0.4.10. Bundle servido v0.4.10 desde VPS Contabo.

### Plan completado
- `.agent/planes/completados/auditoria_inventarios_negativos_2026-04-28.md` (cierre 28-abr)

---

## Completado 2026-04-29 — Sistema Gestión: bloque OPs + sidebar refactor + tiempos editables (v2.9.3 → v2.10.20)

Sesión intensiva en Sistema Gestión, foco principal en módulo de Órdenes de Producción y refactors UX/UI. Detalle completo en [contextos/sistema_gestion.md §Sesiones 2026-04-27 al 2026-04-29](contextos/sistema_gestion.md). Resumen ejecutivo:

### A. Módulo Órdenes de Producción (panel detalle)
- **`OpPanel.vue`** nuevo — abre desde `/ops-tabla`. Materiales/productos lectura, **Tiempos consolidados editables (nivel ≥5)**, tareas vinculadas con quickadd, observaciones lote, botones Procesar/Validar
- Tabla en `g_op_tiempos`: snapshot por `id_op × categoria_produccion_id`. Si vacío → modo "vivo" (suma `g_tareas.duracion_usuario_seg`). Si lleno → modo "snapshot"
- Endpoints nuevos: `POST /op/sync` (SSE), `PUT /op/:id/tiempos`, `PUT /op/:id/lineas`, `POST /op/:id/lineas`, `DELETE /op/:id/lineas/:lineaId`, `POST /op/:id/procesar`, `POST /op/:id/validar`
- **Botón "Sincronizar Effi"** en toolbar de tabla — llama al script Python `scripts/refresh_effi_produccion.py` con SSE (notify ongoing arriba con paso actual). Lock `/tmp/sync_ops_effi.lock` evita duplicados
- Tabla `/ops-tabla`: LIMIT 5000 + filtro últimos 6 meses por defecto

### B. Sidebar nivel 3 → popover flotante (estilo HubSpot)
- Componente nuevo **`SidebarSubSeccion.vue`** que decide popover (desktop+mobile) vs acordeón (mini-mode)
- En desktop: `q-menu` lateral a la derecha; en mobile: `q-menu` debajo del header (no se sale del drawer)
- Chevron `>` a la derecha del header. Click toggle abre/cierra. Hover muestra highlight (no abre)
- Aplicado a 6 sub-secciones × 2 contextos (Mis Tareas + Equipo)

### C. Tiempos consolidados editables (nivel ≥5)
- Sección "Tiempos consolidados" en OpPanel ahora tiene botón "Editar" (solo nivel ≥5)
- Modo edición: cada fila `[select] [_h_]h [_m_]m [×]` + botón `+ agregar tiempo` + Guardar/Cancelar
- Inputs `[h] [m]` separados (no `HH:MM:SS`) — mobile-friendly, teclado numérico directo
- Permite agregar tiempos a OPs viejas sin tareas vinculadas. NO toca tareas, solo `g_op_tiempos`

### D. Categorías actualizadas
- **Nueva**: `Desarrollo_de_producto` (id 17, orden 10, color `#00BFA5`, icono `science`)
- **Fusión**: Reuniones + Informes → `Reuniones_e_informes` (id 11, orden 13). Informes desactivada (registros migrados)
- **Sub-categorías producción nuevas**: `Produccion` (orden 1), `Desenmoldado` (orden 4)
- IA actualizada: pista del clasificador automático ahora reconoce las nuevas categorías

### E. Auto-update PWA (v2.9.8-9)
- **Banner verde** "Hay una nueva versión disponible — Actualizar" cuando el SW detecta versión nueva (chequeo cada 5 min)
- **Botón "Actualizar app"** en sidebar (debajo de Modo claro) — fuerza unregister SW + clear caches + reload
- `register-service-worker.js`: `updated` callback ahora dispara `CustomEvent('sw-updated')` en lugar de auto-reload silencioso

### F. Refactors / deuda técnica resuelta
- **MultiActionBar**: TareasPage tenía copia inline de 270 líneas. Reemplazada por componente compartido. –288 líneas en TareasPage
- **CatProduccionSelector**: chip Cat. producción inline duplicado en TareaForm + TareaPanel + OpPanel. Extraído a componente. –37 líneas netas
- **TareaForm + TareaPanel**: orden unificado (TareaMetaChips primero, luego OP, Cat. producción, DetallesProducción)
- Pendiente: unificar TareaForm y TareaPanel en un solo componente con prop `modo: crear|editar`

### G. Bugs UX/UI fijos (selección)
- v2.9.3: círculo check tareas invisible en modo claro (`rgba(255,255,255,0.50)` sobre blanco)
- v2.9.4 + v2.10.6: bottombar móvil tapaba botones/multibar (`bottom: calc(N + safe-area-inset-bottom)`)
- v2.10.8: papelera en TareaPanel embebido no eliminaba (faltaba `@eliminar` listener)
- v2.10.14: OpSelector mostraba `fecha_final` en lugar de `fecha_de_creacion`
- v2.10.15: TareaForm no mostraba Cat. producción + Detalles producción al seleccionar OP
- v2.10.17: tiempos consolidados sumaban `duracion_cronometro_seg` (raw) → ahora `duracion_usuario_seg`
- v2.10.18: banner "Sincronizando..." quedaba pegado tras terminar (notify dismiss faltante)

### Versión actual
**v2.10.20** desplegada en `gestion.oscomunidad.com` (VPS Contabo).

---

## Completado 2026-04-28 — Migración Producción+Inventario al VPS + Auditoría stocks negativos + Editor recetas + Histórico ajustes

Sesión grande con 9 frentes resueltos. Detalle por bloques:

### A. Migración apps al VPS Contabo
**Producción API (puerto 9600) e Inventario API (puerto 9401) ahora corren en VPS**, igual que Sistema Gestión. Cero cambios de código — solo configuración. La BD `inventario_produccion_effi` ya estaba en VPS, ahora se accede en modo `direct` (sin SSH tunnel).
- VPS: `pip install fastapi uvicorn pydantic pymysql sshtunnel httpx pyjwt python-dotenv python-multipart` + `cd produccion && npm install && npm run build` + `npm install` en `scripts/` (Playwright 1.49.1)
- VPS env: bloque `DB_INVENTARIO_*` con `SSH_HOST=direct` (también funciona INTEGRACION/GESTION en mismo modo si se quiere optimizar después)
- Service files versionados: `scripts/produccion/os-produccion-api.service`, `scripts/inventario/os-inventario-api.service`
- VPS cloudflared: `inv.oscomunidad.com` apunta a `localhost:9600` (era 9401)
- DNS Cloudflare: `cloudflared tunnel route dns --overwrite-dns fa4a4f3d-... inv.oscomunidad.com`
- Local: APIs `os-produccion-api`/`os-inventario-api` `systemctl stop` (no disable, respaldo); entry de `inv.oscomunidad.com` removida de `/etc/cloudflared/config.yml` (backup `.bak.20260428`)
- **Cron `effi-pipeline.timer` sigue en local** — corre cada **1 hora** (antes era 2h, lo bajé a pedido). El pipeline grande pasa por `effi_data` LOCAL como intermediaria → sync a `os_integracion` VPS. El botón "Sync Effi" del frontend (que vive en VPS) hace el mismo flujo pero usando la `effi_data` del VPS como intermediaria temporal — resultado final igual: `os_integracion` actualizado.
- Bug detectado y arreglado durante migración: `lib/db_conn.py::_cfg_remota_dict` modo `direct` leía `db['remote_port']` que no existe → ahora lee de `cfg_remota_ssh()`. Sin este fix el modo direct estaba roto.

### B. Regla nueva en código: paths/hosts SIEMPRE relativos
**MANIFESTO §8A** y **CLAUDE.md** documentan: prohibido hardcodear rutas absolutas, IPs o hostnames en código. Todo via `os.path.dirname(__file__)/...`, env vars, modo `direct`. Migración entre servidores = `git pull` + editar `.env` + reapuntar DNS, cero líneas de código tocadas. Ejemplificado por esta migración.

### C. Bug: SSH tunnel cacheado dejaba TODOS los endpoints caídos
APIs FastAPI cacheaban `cfg_inventario()` al startup. SSH tunnel se caía por timeout del server remoto (~10 min sin actividad) pero el dict cacheado seguía apuntando al puerto local del tunnel zombie → 100% de los endpoints daban HTTP 500 hasta restart manual del servicio.
**Fix triple capa**:
1. `lib/db_conn.py::abrir_tunel`: `set_keepalive=30s` + verificación `ssh_transport.is_active()` (no solo `forwarder.is_active`) + reabrir si está zombie.
2. `scripts/{produccion,inventario}/api.py`: `DB_INV/DB_EFFI` son tags string, no dicts cacheados. Wrappers `q()`/`exe()`/`db_query()` resuelven `cfg_inventario()` por request + reintento UNA vez en errores 2013/2006/"session not active"/"broken pipe".
3. `produccion/src/lib/api.js`: `request()` reintenta UNA vez con 800ms si recibe HTTP 5xx o NetworkError.
Memoria: [feedback_ssh_tunnel_cache.md](../../.claude/projects/-home-osserver-Proyectos-Antigravity-Integraciones-OS/memory/feedback_ssh_tunnel_cache.md). Tras la migración al VPS este bug ya no aplica (no hay tunnel SSH), pero el fix queda activo por si vuelve a usarse el modo SSH.

### D. Auditoría inventarios negativos 2026-04-28 (módulo nuevo)
**22 stocks negativos** detectados en bodegas de Effi (18 en Principal + 4 en Productos No Conformes Bod PPAL). Por cada caso:
- Análisis profundo trazabilidad + conteos previos + causa raíz → archivo `.md` en `inventario/analisis_de_inventario/2026-04-28/<cod>_<nombre>_<bodega>.md` (22 archivos + RESUMEN.md)
- Registro en BD VPS `inventario_produccion_effi`:
  - Tabla nueva **`inv_analisis_inconsistencias`**: `id, fecha, id_effi, nombre, bodega, stock_antes, problema, causa_raiz, evidencias_json, archivo_md, creado_por, created_at`
  - Tabla nueva **`inv_ajustes_historico`**: `id, analisis_id (FK), fecha, id_effi, bodega, tipo (ingreso/egreso), cantidad, stock_antes, stock_despues, op_ajuste_effi, motivo, ejecutado_por, created_at`
- Ajustes Effi via Playwright: **OP #369** (Principal, 18 items, 306 und) + **OP #370** (No Conformes, 4 items, 56 und). Todos los negativos a 0.
- Pendiente: cod 582 (-0.01 en Principal) detectado post-auditoría — fantasma de 10g por redondeo, no bloqueante.

### E. Frontend nuevo: páginas Inconsistencias e Histórico ajustes
- `/inconsistencias` — listado de análisis con búsqueda multi-palabra
- `/inconsistencias/:id` — detalle (problema, causa, ajustes asociados, contenido del .md renderizado)
- `/historico-ajustes` — tabla de todos los ajustes con link al análisis
- Backend: `GET /api/inventario/{historico-ajustes,inconsistencias,inconsistencias/{id}}` con filtros fecha/cod/bodega
- Sidebar: 2 entradas nuevas bajo Inventarios

### F. Editor de recetas (in-place, sheet right side)
Página `/recetas/:cod` ahora editable: tablas Materiales / Productos / Costos con Combobox cod (búsqueda multi-palabra), Input cantidad/costo, papelera por fila, "+Agregar" en header de cada sección. Toggle radio para producto principal. Totales recalculan en vivo. Botones "Descartar" / "Guardar cambios" aparecen solo cuando dirty.
- Backend: `PUT /api/recetas/{cod}/full` reescribe los 3 sub-arreglos (DELETE+INSERT)
- Modelos pydantic `RecetaMaterialIn`, `RecetaCostoIn`, `RecetaProductoIn`

### G. Bug crítico: número de OP creada quedaba siempre el mismo
`import_orden_produccion_post.py` consultaba `SELECT MAX(id_orden) FROM zeffi_produccion_encabezados` en BD local — que solo se actualiza con refresh manual de Effi. Resultado: todas las OPs creadas tras el último refresh recibían el mismo número (ej: 8 OPs distintas todas marcadas con #2223). El POST a Effi solo devuelve `"OK"` sin id.
**Fix**: ahora hace GET a `https://effi.com.co/app/orden_produccion`, parsea `data-id` del HTML ANTES y DESPUÉS del POST → id real = `MAX_DESPUES`. Independiente del refresh local.
Datos corregidos: solicitudes 73, 76-82 reasignadas a OPs 2223-2228 según orden de creación (en `prod_solicitudes` y `prod_ops_creadas`).

### H. Recetas corregidas (datos)
- **cod 387 Miel de Fuego 275g**: agregado ají (cod 379) con proporción 14.41% (0.0375 kg por unidad). Miel ajustada 0.275→0.260 kg. Costo: $8.325/und (era $6.488).
- **cod 238 Infusión 200g**: bolsa cambiada cod 100 (KRAFT 500g) → 143 (FLEX METAL 250g, $476.68).
- **cod 497 Infusión 400g**: agregadas etiquetas faltantes 490 (delantera, $1.125) + 523 (trasera, $1.125).

### I. Stock + unidades de Producto Terminado
- Backend `/api/articulos`: ahora usa `stock_total_empresa` (consolidado) en lugar de `stock_bodega_principal_sucursal_principal` aislada. Evita stocks fantasma cuando hay negativos en otra bodega que compensan.
- BD `inv_rangos`: PT con `unidad='GRS'` → `'UND'` (68 filas masivamente). Los productos terminados se cuentan por unidad — el "GRS" en el nombre es la presentación, no la unidad de conteo.
- Ajuste Effi cod 405 CHOCOBEETAL OS 130 GRS: Principal -63 / No Conformes +63 → quedó en 5 unidades reales (era 68 fantasma).

### J. Pipeline Effi: cron + mail
- Timer `effi-pipeline.timer`: `OnUnitActiveSec` 2h → **1h** (en `/etc/systemd/system/`, backup `.bak`)
- Mail `larevo1111@gmail.com` no llegaba: App Password de Google (`jovc hbxy sjlz noob`) caducado → renovado a `ucpl lyfh dujr fprd` en `scripts/.env` (gitignored)

### Tablas BD nuevas (VPS `inventario_produccion_effi`)
- `inv_analisis_inconsistencias` (22 filas iniciales)
- `inv_ajustes_historico` (22 filas iniciales con FK al análisis)

### Bumps de versión Producción
v0.3.2 → v0.3.3 → v0.3.4 → v0.3.5 → v0.4.0 → v0.4.1 (último deployado en VPS)

### Plan completado
[.agent/planes/completados/migracion_produccion_inventario_vps_2026-04-28.md](planes/completados/migracion_produccion_inventario_vps_2026-04-28.md)
[.agent/planes/activos/auditoria_inventarios_negativos_2026-04-28.md](planes/activos/auditoria_inventarios_negativos_2026-04-28.md) (mover a completados)

---

## Completado 2026-04-24 — Módulo "Órdenes de Producción" (Sistema Gestión v2.9.0)

Nuevo módulo que replica el patrón de Proyectos pero para OPs. La OP es un "mini proyecto" que agrupa N tareas; los tiempos y consumos reales se consolidan **a nivel OP** (no tarea).

**Schema BD `os_gestion` (VPS)**:
- **Nuevas**: `g_categorias_produccion` (12 seeds: Alistamiento, Templado, Enmoldado, Empaque, Etiquetado, Sellado, Esterilización, Pasteurización, Encordonado, Loteado, Limpieza, Otra), `g_op_lineas` (materiales+productos con cantidad_real por OP), `g_op_tiempos` (snapshot segundos_totales por categoría al validar), `g_op_detalle` (obs_lote, sellos procesar/validar, op_anterior).
- **g_tareas**: +`categoria_produccion_id INT NULL`, −5 columnas viejas (`tiempo_alistamiento_min`, `tiempo_produccion_min`, `tiempo_empaque_min`, `tiempo_limpieza_min`, `id_op_original`).
- **Drop**: tabla `g_tarea_produccion_lineas` (26 filas viejas descartadas por Q13).
- **Cédulas cargadas en sis_usuarios** (master VPS): Santi 3506889, Jenifer 1128457413, Deivy 74084937, Laura 1017206760, Ricardo 3502398759.

**Backend (server.js)**: 10 endpoints nuevos a nivel OP (`GET /categorias-produccion`, `GET /op`, `GET /op/:id/ficha`, `PUT /op/:id/detalle`, `PUT/POST/DELETE /op/:id/lineas/...`, `POST /op/:id/procesar` nivel≥3, `POST /op/:id/validar` nivel≥5). `GET /tareas` ahora acepta `?op_id=X` (match exacto) y devuelve `categoria_produccion_id/nombre`. Eliminados los 5 endpoints viejos `/tareas/:id/produccion/*`.

**Flujo `/validar` (15 pasos)**: calcular tiempos vivos → anular OP original (Playwright) → crear OP nueva con reales → Validado → `UPDATE g_tareas SET id_op=<nueva>` → copiar `g_op_lineas` a la nueva → INSERT `g_op_detalle` con `op_anterior` → snapshot en `g_op_tiempos` por categoría. Observación nueva: `LOTE X · Validó: · Reportó: · Creada/Procesada/Validada · Tiempos: Templado 4h · ... · Obs orig: ...`.

**Frontend**:
- **`DetallesProduccion.vue`** reducido a solo-lectura + link "Editar en la OP".
- **`OpPanel.vue` nuevo**: panel lateral 540px desktop / fullscreen mobile con 7 bloques (cabecera, materiales editables, productos editables, tiempos consolidados vivo/snapshot hh:mm:ss, tareas vinculadas click→abre TareaPanel, obs_lote, Procesar/Validar). Auto-sembra líneas desde Effi al abrir por primera vez.
- **`OpTablePage.vue` nuevo** (ruta `/ops-tabla`): tabla OsDataTable con Estado (ordena Generada→Procesada→Validado→Anulada) · OP · Responsable · Artículos (compuesto) · Fecha · Vigencia. Click fila → OpPanel.
- **Sidebar**: link "Órdenes de producción" en sección Tablas + sub-acordeón OP (50 items max) en Mis Tareas y Equipo que filtra tareas por `?op_id=X`.
- **TareaPanel**: selector `categoria_produccion_id` (12 chips pill) visible solo si la tarea tiene OP vinculada.
- **TareasPage**: soporta filtro `?op_id=X` en query.

**Versión**: v2.8.7 → **v2.9.0** (bump en MainLayout).

**Tests E2E con Chrome DevTools MCP**:
- Login JWT inyectado ✓
- /ops-tabla renderiza 500 OPs ✓
- Click fila abre OpPanel con cabecera + chip Generada + 5 secciones + botones Procesar/Validar visibles para nivel 9 ✓
- Input cantidad_real "7,45" (coma decimal) → BD guarda 7.450 ✓
- Textarea obs_lote guarda en `g_op_detalle.observaciones_lote` vía UPSERT ✓
- Sidebar acordeón "Órdenes de producción" → 50 items, click filtra tareas ✓
- PUT `categoria_produccion_id` por tarea + GET retorna `categoria_produccion_nombre` ✓
- Mobile 390x844 responsive ✓

**Archivos nuevos/modificados**:
- `sistema_gestion/api/migrations/2026-04-24_modulo_op.sql` (nuevo)
- `sistema_gestion/app/src/components/OpPanel.vue` (nuevo)
- `sistema_gestion/app/src/pages/OpTablePage.vue` (nuevo)
- `sistema_gestion/app/src/router/routes.js` (+ ruta `/ops-tabla`)
- `sistema_gestion/app/src/layouts/MainLayout.vue` (sub-acordeón OP + link Tablas + versión)
- `sistema_gestion/app/src/components/DetallesProduccion.vue` (reducido a solo-lectura)
- `sistema_gestion/app/src/components/TareaPanel.vue` (selector cat_producción)
- `sistema_gestion/app/src/pages/TareasPage.vue` (filtro op_id)
- `sistema_gestion/api/server.js` (+10 endpoints OP, -5 endpoints viejos, -SELECTs id_op_original)
- `sistema_gestion/api/db.js` (no tocado en esta fase)

**Plan completo**: [.agent/planes/completados/PLAN_MODULO_OP_GESTION_2026-04-24.md](planes/completados/PLAN_MODULO_OP_GESTION_2026-04-24.md).

---

## Completado 2026-04-24 — Aislamiento de Hostinger: usuarios desde sos_master_erp (VPS)

**Contexto**: Tras detectar y limpiar una intrusión (`maskedaltfivem@gmail.com`, ver `.agent/planes/activos/PLAN_MODULO_OP_GESTION_2026-04-24.md` §12), Santi decidió cortar la dependencia de Hostinger para validar usuarios. Hostinger queda aislado exclusivamente para el ERP Effi real (`u768061575_os_comunidad`).

**Cambios:**
- **Tabla master verificada**: `sos_master_erp.sis_usuarios` en VPS Contabo (creada 2026-04-20, 7 usuarios activos, sincronizada con Hostinger).
- **Helper nuevo `db.master()`**: en `lib/db_conn.js` + `scripts/lib/db_conn.py` + `scripts/lib/__init__.py` (+ `cfg_master()`).
- **Usuario MySQL `os_master` en VPS**: SELECT sobre `sos_master_erp.*` + INSERT sobre `audit_logins` y `audit_sos`.
- **Bloque `DB_MASTER_*` en `.env`**: local (SSH al VPS) + VPS (modo directo) + plantilla `.env.example`.
- **Sistema Gestión refactorizado**: `sistema_gestion/api/server.js` — 15+ queries que usaban `db.comunidad` + `sys_usuarios*` ahora usan `db.master` + `sis_usuarios*`. Mapping: `Email→email`, `Nombre_Usuario→nombre`, `Nivel_Acceso→nivel_global`, `estado 'Activo'→'activo'`, `sys_empresa.nombre_empresa→sis_empresas.nombre`, `ue.usuario→ue.usuario_email`, `ue.empresa→ue.empresa_uid`.
- **Producción refactorizado**: `scripts/produccion/api.py._buscar_usuario_os()` → master.
- **Scripts notificación refactorizados**: `notif_jornadas_abiertas.py`, `notif_jornada_no_iniciada.py` → master (eliminan SSH tunnel manual a Hostinger).
- **Cross-database JOIN eliminado**: en Gestión había JOIN entre `os_gestion.g_jornadas` y `u768061575_os_comunidad.sys_usuarios` (BDs en servers distintos → roto desde 2026-04-20). Reemplazado por 2 queries + merge en Node.
- **ERP Frontend + Inventario**: NO requieren cambios (ERP solo usa `db.integracion`; Inventario delega JWT a Gestión).

**Resultado**: si un atacante vuelve a entrar al ERP Hostinger (por WP PHP u otro vector), NO afecta a gestion/producción/inventario. Hostinger aislado funcionalmente.

**Pendientes:**
- Reiniciar `os-gestion.service` en VPS (requiere sudo Santi via code-server; archivos ya desplegados).
- Activar registro en `audit_logins` desde el flujo de login.
- Normalizar `g_jornadas.empresa` y `g_tareas.empresa` a lowercase (opcional, collation `_ci` ya matchea).

---

## Completado 2026-04-24 — Limpieza arquitectura BDs: effi_data ya no es fuente de verdad

**Problema detectado**: la app de Producción/Inventario aún consultaba `effi_data` LOCAL para tablas zeffi_* (OPs, materiales, artículos, recetas). Eso violaba la arquitectura: `effi_data` es **intermediaria del pipeline**, la fuente de verdad consolidada es `os_integracion` en VPS.

**Hecho:**
- ✅ Helper nuevo `cfg_integracion()` en `scripts/lib/db_conn.py` (análogo a `cfg_inventario()`, abre tunnel SSH al VPS automático)
- ✅ Reapuntados 12 archivos Python (5 producción + 7 inventario): `cfg_local()+'effi_data'` → `cfg_integracion()`
- ✅ Documentación: MANIFESTO §8 reescrito + memoria persistente `feedback_effi_data_intermediaria.md`
- ✅ Test exhaustivo 18/18 endpoints OK contra VPS (494 artículos, 60 solicitudes post-migración, 306 inventario, recetas)
- ✅ Backups de TODAS las BDs: `backups/{bd}/2026-04-24_131441.sql` (effi_data 58MB, ia_service_os 26MB, espocrm 1.6MB, os_whatsapp 52KB, os_inventario 1.2MB, os_produccion 16KB, comunidad 756KB)
- ✅ Migración legacy `os_produccion.solicitudes_produccion` (55 datos viejos) → VPS `prod_solicitudes` preservando IDs (1 grupo + 55 solicitudes con IDs 1-55)
- ✅ DROP de BDs locales duplicadas: `os_inventario` (1.7MB, 10 tablas inv_*) y `os_produccion` (3 tablas prod_*) — todo está en `inventario_produccion_effi` VPS
- ✅ Smoke test post-DROP: todos los endpoints siguen 200 OK

**Mapa final de BDs** (ver MANIFESTO §8):
- LOCAL: nextcloud, **effi_data** (intermediaria pipeline), ia_service_os, espocrm, nocodb_meta, sos_erp_local, ia_local, os_whatsapp
- VPS: **os_integracion** (fuente de verdad zeffi_* + resumen_* + crm_contactos + catalogo_articulos), os_gestion, **inventario_produccion_effi** (prod_* + inv_*)
- HOSTINGER: solo `u768061575_os_comunidad` (ERP real)

## Completado 2026-04-24 — Reversión arquitectura a VPS + auto-cierre jornadas + diagnóstico Playwright VPS

**Resumen**: Producción de `gestion.oscomunidad.com` vuelve a correr 100% en VPS Contabo (arquitectura correcta). El "bloqueante" que el 2026-04-23 motivó reapuntar DNS al local (supuesto filtro de Effi por IP) era falso — la sesión `session.json` stale copiada del local generaba cookies no reconocidas. Con login fresh generado en el VPS, Playwright ejecuta en VPS idéntico al local.

**Cambios aplicados:**
- **DNS `gestion.oscomunidad.com`** revertido al tunnel VPS (`fa4a4f3d`). Verificado con test destructivo: `systemctl stop os-gestion` local → `gestion.oscomunidad.com` HTTP 200 (tráfico 100% VPS).
- **Config `/etc/cloudflared/config.yml` del VPS** restaurado desde `.bak` (hostname `gestion.oscomunidad.com` → `localhost:9300` agregado de vuelta).
- **Config cloudflared LOCAL**: quitada la línea `gestion.oscomunidad.com` (ya no enruta esa URL).
- **Playwright + chromium** quedan instalados en VPS (operativos, usados por `/procesar` y `/validar`).
- **`session.json`**: generada fresh desde el VPS (no copiada del local). Cookies atadas al browser del VPS.
- **Auto-cierre de jornadas**: nuevo helper `cerrarJornadaAbandonada()` + endpoint `POST /api/internal/jornadas/auto-cierre` (interno, solo localhost) + cron horario `0 * * * *` **solo en VPS** (antes estaba también en local, ahora redundante porque prod es VPS).
- **Máxima absoluta** agregada a `CLAUDE.md`: "NUNCA cambios de infraestructura sin autorización explícita". Lista concreta de qué es "infraestructura" (DNS, /etc/, systemd, crontab, apt install, SSH tunnels, Playwright en servidores). Flujo: PARAR → explicar → esperar "sí hacelo" → reportar con sección "Cambios de infraestructura".
- **Merges desde GitHub** (trabajo de Santi en Claude web):
  - `claude/analyze-test-coverage-yL3oB`: fix ia-admin timezone (ContextosPage + DashboardPage), regla absoluta HELPERS en CLAUDE.md, fix `notif_jornadas_abiertas.py` a helpers, tests para `lib/timezone.js` / `lib/db_conn.js` / `scripts/lib/db_conn.py`.
  - `claude/check-repo-access-qHEpR`: pipeline frecuencia 2h→1h + docs `.agent/` actualizados.

**El jump tunnel a Hostinger** (`tunnel-hostinger.service` en local) se **mantiene activo** porque el servidor local (modo dev) sigue necesitándolo: Hostinger bloquea la IP del local para SSH directo. VPS en cambio llega directo a Hostinger sin jumphost (verificado `ssh u768061575@109.106.250.195:65002`). `.env` del VPS ya apunta directo.

**Verificación end-to-end** (Chrome DevTools via `gestion.oscomunidad.com`):
- Login con JWT inyectado en `localStorage.gestion_jwt` → app carga.
- API GET (tareas, usuarios, jornadas) → responde desde VPS.
- Crear tarea POST → OK en BD VPS.
- `/procesar` ciclo completo con OP test 2211 → OP en Effi pasa a Procesada.
- `/validar` ciclo completo con OP test 2212 → anula 2212, crea 2213 con reales (0.08 kg / 0.9 und), marca 2213 Validado. 1min 15s.
- OPs test (2211, 2212, 2213) anuladas al final. Tarea 557 limpia. Tarea 705 de test Chrome DevTools borrada.

**Plan completo**: [.agent/planes/completados/reversion_arquitectura_vps_2026-04-24.md](planes/completados/reversion_arquitectura_vps_2026-04-24.md).

### Extensión 2026-04-24 — Fix masivo de timezone en jornadas

**Contexto**: tras poner el cron auto-cierre en VPS, la jornada de Deivy (id 45) se cerró equivocadamente a las 14:00 Colombia cuando llevaba 6.5h abiertas (no 13h). El bug: el helper `cerrarJornadaAbandonada` calculaba tiempos en Node con `new Date()` / `new Date(str)`, que dependen del TZ del OS. VPS en `Europe/Berlin (CEST, +02:00)` → offset de 7h respecto a Colombia → falsos positivos.

**Fix arquitectónico:**
1. `lib/timezone.js`: nueva función `parseBackendDate(str)` — mirror exacto del helper homónimo en `sistema_gestion/app/src/services/fecha.js`. Es el único Date-factory válido para strings que vienen del pool mysql2 (con `dateStrings:true`).
2. `server.js cerrarJornadaAbandonada()`: reescrito. Todo el cálculo de tiempo pasa por SQL usando `NOW()`, `TIMESTAMPDIFF`, `DATE_FORMAT`, `DATE_ADD`. Cero `new Date()` para lógica temporal.
3. `server.js`: 7 usos de `new Date(row.fecha_X)` migrados a `parseBackendDate()` (indicadorConfianza, `/iniciar` gap 6h, `/reabrir` ventana 1h, filtros de semana, etc.).
4. Frontend `JornadaHeader.vue` + `JornadaDetallePopup.vue`: `import { parseBackendDate, TZ_NAME } from 'src/services/fecha'`. Todos los formateos usan `toLocaleString(..., { timeZone: TZ_NAME })` explícito. Edición de HH:MM se extrae por regex directa del string para ser inmune a TZ del browser.
5. Jornada 45 de Deivy **reabierta** manualmente (UPDATE directo).

**Verificación post-fix**: llamada manual al endpoint `/api/internal/jornadas/auto-cierre` desde VPS → `{ok:true, revisadas:2, cerradas:[]}` — cálculo correcto en TZ Colombia.

**Regla reforzada** (ya estaba en CLAUDE.md como REGLA ABSOLUTA TIMEZONE y vigilada por `.githooks/pre-commit`): cero hardcode de offset. Todo por `lib/timezone.js` (Node) o `services/fecha.js` (frontend). El git hook bloquea commits con `-05:00`, `America/Bogota`, `CURDATE()`, `toISOString().slice(0,10)`, `new Date(\`...T...\`)` fuera de la whitelist.

**Commits**: `abb2430` (fix auto-cierre), `35eb8d7` (migración masiva a parseBackendDate).

---

## Completado 2026-04-23 — Detalles de Producción + reporte de reales + validación (Sistema Gestión v2.8.5)

Módulo completo para que el operario reporte consumos reales en una OP vinculada a una tarea, y nivel ≥ 5 valide (anular + crear nueva con reales + marcar Validado en Effi).

**Entregado:**
- Panel de tarea con acordeón "Detalles de producción" (visible solo si categoría=Producción + `id_op` vinculado).
- Tabla materiales + productos con columnas Material/Estimado/Real (siembra automática desde Effi, unidades desde `os_integracion.unidades_articulos`).
- 4 inputs de tiempo (Alistamiento, Producción, Empaque, Limpieza) + total calculado en vivo.
- Chip de estado (Generada gris / Procesada naranja / Validado verde / Anulada gris oscuro).
- Botón "Procesar" (responsable o nivel ≥ responsable): cambia estado de OP a Procesada en Effi.
- Botón "Validar" (solo nivel ≥ 5): anula OP original + crea nueva con reales + marca Validado. `id_op_original` queda guardado, UI muestra "OP orig: xxxx".
- Decimal tolerante (coma y punto ambos válidos).
- Observación auto-generada: "Validación OS · Reportó: X · Validó: Y · Obs OP orig: ..."

**Versiones**: v2.8.0 → v2.8.5 (12 commits entre `58e54c8` y `021c421`).

**Plan completo** + lista de archivos + pendientes: [.agent/planes/completados/PLAN_DETALLES_PRODUCCION_2026-04-20.md](planes/completados/PLAN_DETALLES_PRODUCCION_2026-04-20.md).

### Infraestructura resuelta durante la ejecución
- ~~**DNS gestion.oscomunidad.com reapuntado al tunnel local**~~ — **revertido el 2026-04-24**: el diagnóstico era falso. Ver entrada del 2026-04-24.
- **SSH jump tunnel a Hostinger** (`tunnel-hostinger.service`): **se mantiene activo solo en local** (modo dev) porque la IP del local está bloqueada por Hostinger para SSH. VPS (prod) conecta directo sin jumphost.
- **`db.js` pool dinámico**: antes cacheaba el pool al arrancar; tras reconexión SSH quedaba obsoleto ("Pool is closed"). Ahora los getters leen el pool actual del helper central en cada acceso.
- **comunidad opcional al arranque**: si Hostinger tarda en responder, el server arranca igual y reintenta en background cada 15s. `/procesar` y `/validar` usan `req.usuario.nombre` del JWT (no dependen de comunidad).

## Módulos activos en paralelo

| Módulo | Archivo de contexto | Estado actual | Prioridad |
|---|---|---|---|
| Servicio IA + Bot Telegram | [contextos/ia_service.md](contextos/ia_service.md) | Super Agente activo, mejora continua cron | Alta |
| Pipeline Effi | [contextos/pipeline_effi.md](contextos/pipeline_effi.md) | Estable, 18 pasos activos | Normal |
| ERP Frontend | [contextos/erp_frontend.md](contextos/erp_frontend.md) | Módulo Ventas completo | Normal |
| Sistema Gestión OS | [contextos/sistema_gestion.md](contextos/sistema_gestion.md) | Jornadas ✅ + Tareas ✅ + Detalles de Producción ✅ (v2.8.5) | Alta |
| EspoCRM | [contextos/espocrm.md](contextos/espocrm.md) | Estable — sin trabajo activo | — |
| Inventario Físico | [contextos/inventario_fisico.md](contextos/inventario_fisico.md) | Operativo — inv.oscomunidad.com, inventarios completos + parciales | Alta |
| Producción | `produccion/` + `scripts/produccion/api.py:9600` | React + Shadcn/ui + Tailwind (style Linear). BD `inventario_produccion_effi` VPS (`prod_*`). Consulta zeffi de `os_integracion` VPS | Operativo — solicitudes → OPs Effi via Playwright |
| WA Bridge | `wa_bridge/` | ✅ Activo — puerto 3100, número 573214550933 vinculado | Normal |

## Trabajo activo (2026-04-23)

### Completado 2026-04-23 — Libro de Recetas de Producción

**Objetivo**: eliminar la deducción manual de recetas para cada OP. Catálogo maestro con receta por producto.

**Infraestructura**:
- BD VPS `inventario_produccion_effi`: 4 tablas nuevas (`prod_recetas`, `_materiales`, `_productos`, `_costos`)
- 8 scripts en `scripts/produccion/libro_recetas/`:
  - `listar_universo.py`, `dossier_producto.py`, `construir_receta.py`, `simular_op.py`, `persistir_receta.py`
  - `sugerir_atribuido.py` — motor propio que atribuye materiales en OPs multi-producto (afinidad semántica + match por cantidad + share)
  - `override_receta.py` — módulo para overrides manuales con razonamiento de Claude/Santi
  - `persistir_todas.py` — procesamiento masivo
- Endpoints API: `/api/recetas`, `/api/recetas/{cod}`, `/api/recetas/{cod}` PATCH, `/api/recetas/stats/resumen`
- UI: `/recetas` (lista con OsDataTable + resumen por familia) y `/recetas/:cod` (detalle con materiales/productos/costos + tarjetas económicas + textarea razonamiento + botones validar/devolver)

**Cobertura**: 108/108 productos con receta (productos producidos desde 2025-01-01). 72/108 validadas (67%). Los 36 en borrador son productos de 1-2 OPs que requieren razonamiento específico con Santi.

**Patrones documentados en skill `produccion-recetas` §12**: densidades (miel 1.28, polen 0.65, propóleo 1.30 g/ml), mapeo envase-peso, query SQL para identificar envase por match de cantidad.

### Completado 2026-04-20 — Inventario parcial abril + módulo Producción

**Inventario físico:**
- Inventario completo marzo 2026: cerrado, ajustes aplicados (361+362+363), informe PDF + análisis IA con Gemini
- Primer inventario parcial 20 abril: 28→33 artículos (con esterilizados), ajustes aplicados, cero artículos negativos en Effi
- Inventarios parciales operativos con preselección inteligente (`/api/inventario/sugerir-articulos`)
- Pestaña Costos con OsDataTable dark, informe PDF automático, análisis IA ejecutivo
- Observaciones en BD (`inv_observaciones`): automáticas + manuales (error_conteo, correccion_costo, hallazgo, manual)
- Soporte hora de corte intra-día (`--hora HH:MM:SS`)
- Envases normales vs esterilizados (mapeo)

**Timezone effi_data:**
- Toda `effi_data` uniformizada en UTC-5: `import_all.js` convierte `zeffi_cambios_estado.f_cambio_de_estado` de UTC a COT

**Costo:**
- Migrado de `costo_promedio` a `costo_manual` en todo el sistema (inventario, resúmenes, informes)

**Módulo Producción (2026-04-21):**
- Directorio: `produccion/` — stack React + Shadcn/ui + Tailwind v4 (style Linear.app)
- API: FastAPI `scripts/produccion/api.py` puerto 9600 (systemd `os-produccion-api`)
- BD: `os_produccion.solicitudes_produccion` (estados: solicitado/programado/en_produccion/producido/validado/cancelado)
- Estado: **operativo** — Jenifer programa solicitudes, Santi las convierte en OPs de Effi
- Tabla OsDataTable portada a React (filtros, subtotales, exportar, modo claro/oscuro)
- Panel detalle lateral al click en fila (sheet drawer)
- Scripts Playwright Effi (creados 2026-04-21):
  - `scripts/import_orden_produccion.js` — crea OPs en Effi desde JSON (probado con OP 2182)
  - `scripts/anular_orden_produccion.js` — anula OPs por ID
- **Logica recetas verificada**: productos se dividen en "lote fijo" (cobertura 73%, tabletas) vs "escalable por unidad" (nibs 100g, miel 640g). Doc en `MANUAL_EFFI_PRODUCCION_INVENTARIOS.md §3`.

### Completado 2026-04-20 — BDs Hostinger marcadas deprecated
- `u768061575_os_integracion` y `u768061575_os_gestion` en Hostinger: todas las tablas renombradas con prefijo `_deprecated_` + tabla `_DEPRECATED_README` con aviso y ruta al VPS.
- Motivo: prevenir que futuros agentes (Claude Code / Antigravity / scripts) consulten datos muertos. Si alguien hace `SELECT ... FROM zeffi_facturas_venta_encabezados` apuntando a Hostinger → error "table not found" (fail-fast).
- `u768061575_os_comunidad` intacta (ERP real Effi, prohibido tocar).
- PWA Service Worker: confirmado que `skipWaiting: true` + `clientsClaim: true` ya están en `quasar.config.js` y el `sw.js` compilado incluye `self.skipWaiting()` + `e.clientsClaim()` + `cleanupOutdatedCaches()`. Las PWAs se actualizan automáticamente al próximo abrir.

### Completado 2026-04-20 — Corte DNS gestion al VPS (migración completada)
- `gestion.oscomunidad.com` → VPS tunnel (antes: servidor local).
- Precondición verificada: `JWT_SECRET` y `GOOGLE_CLIENT_ID` idénticos local/VPS → usuarios NO perdieron sesión.
- Verificado con test destructivo: `systemctl stop os-gestion` en local → gestion.oscomunidad.com sigue HTTP 200.
- `gestion-vps.oscomunidad.com` se deja activo 7 días como red de seguridad. Programado eliminar 2026-04-27.
- Servidor local queda como **dev** (localhost:9300 para testing) y host de **servicios internos** que usan GPU/recursos locales (IA Service, Bot Telegram, Pipeline Effi, WA Bridge, EspoCRM Docker).

### Completado 2026-04-20 — Corte DNS menu + inv al VPS
- `menu.oscomunidad.com` → VPS tunnel (antes: servidor local)
- `inv.oscomunidad.com` → VPS tunnel (antes: servidor local)
- Verificado con test destructivo: `systemctl stop os-erp-frontend.service` en local → menu.oscomunidad.com sigue HTTP 200 (confirma ruta VPS).
- Testing local vía `http://localhost:9100`, `:9300`, `:9401` (mismas BDs del VPS vía SSH tunnel).

### Completado 2026-04-20 — VPS apps funcionando con `.env` propio
- Helper `lib/db_conn.js`/`scripts/lib/db_conn.py` extendido con **modo directo**: si `SSH_HOST=localhost`, salta tunnel SSH y conecta directo al MariaDB del mismo servidor.
- Creado `integracion_conexionesbd.env` en el VPS con modo directo para integracion+gestion, SSH a Hostinger para comunidad.
- Instaladas deps Python (`pymysql`, `sshtunnel`, `python-dotenv`) en el venv del VPS.
- `.gitignore` ajustado: `__pycache__/` y `*.pyc` removidos del tracking (59 archivos).
- Arreglado `sync-repo.sh` del VPS que fallaba silenciosamente por conflicto de pycache sin trackear.

### Completado 2026-04-20 — Migración Hostinger → VPS Contabo (BDs)
- **`os_integracion` y `os_gestion` migradas de Hostinger a VPS Contabo** (94.72.115.156).
- Servicios LOCALES intactos: `effi_data`, `ia_service_os`, `espocrm`, `os_inventario`, `os_whatsapp` siguen en servidor de casa.
- `os_comunidad` se queda en Hostinger (ERP real, prohibido tocar).
- Proceso del corte:
  1. Freeze 7 servicios systemd
  2. Dump delta Hostinger → re-import VPS (DROP+CREATE+restore, re-grant)
  3. `cp integracion_conexionesbd.vps.env integracion_conexionesbd.env` (switch)
  4. Restart servicios
  5. Golden path OK: Gestión login + tareas + ERP ventas + IA bot + Python helpers
- Backup Hostinger conservado: `/home/osserver/Proyectos_Antigravity/backups/u768061575_os_{integracion,gestion}/`
- Plan completo: `.agent/planes/completados/migracion_bd_hostinger_a_vps_contabo_2026-04-20.md`
- SSH key osserver@VPS autorizada desde servidor local (id_ed25519).
- MariaDB VPS: `default-time-zone=-05:00` nativo.

### Completado 2026-04-20 — Centralización de conexiones BD
- **Todas las credenciales de BD movidas a `integracion_conexionesbd.env`** (raíz del repo, gitignored).
- Plantilla versionada: `integracion_conexionesbd.env.example`.
- Helpers: `lib/db_conn.js` (Node) y `scripts/lib/db_conn.py` (Python). Cargan el `.env` automáticamente.
- 35 archivos refactorizados (5 servicios Node + 30 scripts Python): ningún host/user/pass/database hardcoded.
- API Node: `db.local('effi_data')`, `db.integracion()`, `db.gestion()`, `db.comunidad()`.
- API Python: `with local(db) as conn:`, `with integracion() as conn:`, `with gestion()`, `with comunidad()`, o `cfg_local()` / `cfg_remota_ssh(prefijo)` / `cfg_remota_db(prefijo)` para scripts legados.
- Validado: 7 servicios reiniciados y respondiendo. Smoke Python OK. Próximo paso: migrar `os_integracion` y `os_gestion` al VPS → solo editando el `.env`.

### Completado sesiones anteriores
- **Hostinger inalcanzable**: ISP bloqueaba la IP. Solución: Cloudflare WARP instalado (`warp-cli connect/disconnect`).
- **OpenCode modelo removido**: `mimo-v2-pro-free` ya no existe en OpenCode. Cambiado a `opencode/qwen3.6-plus-free` en `superagente_oc.py`.
- **Bot conflictos polling**: Múltiples restarts lo resolvieron. Causado por cambios de red (WARP).
- **ialocal sobreescribía modelo Ollama**: `ialocal/server.js` usaba `qwen2.5-coder:14b` como default, desplazaba a `qwen-coder-ctx` de VRAM. Corregido a `qwen-coder-ctx`.
- **Auto-corrección LIKE**: `_corregir_igualdad_nombres()` en servicio.py convierte `vendedor = 'X'` → `LIKE '%X%'` antes de ejecutar SQL.
- **Agregados pre-calculados**: `_calcular_agregados()` calcula SUM/MAX/MIN de columnas numéricas y los inyecta en el prompt de respuesta para que el LLM no sume mal.
- **Validación tablas inexistentes**: `obtener_columnas_reales()` ahora detecta tablas que no existen y sugiere alternativas.
- **Diagnóstico diario**: `scripts/diagnostico_diario.py` cron 6:30am. Revisa servicios, BDs, Hostinger, WARP, GPU, apps, pipeline, bot, disco. Envía reporte por bot principal con botón "Abrir con Claude Code" si hay fallos.

### ⚠️ PROBLEMA ABIERTO: Ollama lento (200s vs 14s en benchmark)

**Hechos comprobados:**
- Benchmark 29 marzo: modelo `qwen-coder-ctx` (qwen2.5-coder:14b + num_ctx=28672), 44K tokens input, latencia 12-17s, 15/15 SQL correctas
- Hoy 3 abril: mismo modelo `qwen-coder-ctx`, 25K tokens reales (medido con API nativa), latencia 180-200s, 10/15 SQL correctas
- Ollama versión 0.18.3, binario del 25 de marzo (no cambió)
- GPU: RTX 3060 12GB. Modelo ocupa 10.2GB VRAM.
- Ollama hace offloading parcial a RAM: 21 de 49 capas del modelo van a RAM, 284 graph splits por batch
- Consulta directa con prompt chico (32 tokens): 0.3s prompt eval + 22s load (primera vez) o 0.1s load (modelo ya cargado)
- Swap al 100% (8GB/8GB)

**Lo que NO se ha determinado:**
- Si el benchmark tenía el mismo offloading o si en ese momento cabía completo en VRAM
- Por qué la misma configuración da 14s entonces y 200s ahora
- Si hay una regresión de Ollama con offloading parcial (hay issues reportados en GitHub: #12037, #12504, #11060)
- Si el swap al 100% está causando que las capas en RAM se vayan a disco

**Configuración Ollama actual:**
- Agente BD: `ollama-qwen-coder` → `modelo_id=qwen-coder-ctx`
- Modelo: FROM qwen2.5-coder:14b, PARAMETER num_ctx 28672
- Endpoint: `http://localhost:11434/v1`
- Provider: `openai_compat.py`
- El endpoint /v1 reporta tokens INCORRECTOS (reporta 57K cuando son 25K reales)
- Ollama está activo pero el modelo no debe estar cargado en VRAM hasta que se necesite (warmup automático)

## Regla de actualización

Al empezar a trabajar en un módulo → leer su contexto.
Al terminar tarea significativa → actualizar el contexto del módulo.
MEMORY.md de Claude siempre refleja el módulo activo y su estado.

---

## Arquitectura general del sistema

### BDs

| BD | Ubicación | Rol |
|---|---|---|
| `effi_data` | MariaDB local | **INTERMEDIARIA del pipeline. SOLO el orquestador la usa.** Apps consultan os_integracion |
| `ia_service_os` | MariaDB local | Servicio IA (17 tablas + 1 vista) |
| `os_whatsapp` | MariaDB local | WA Bridge (wa_config, wa_contactos, wa_mensajes_entrantes, wa_mensajes_salientes) |
| `espocrm` | MariaDB local | CRM (488 contactos) |
| `nocodb_meta` | MariaDB local | Metadatos NocoDB |
| `os_integracion` | **VPS Contabo (94.72.115.156)** | **Fuente de verdad** — 56 tablas (41 zeffi + resumen_* + crm_contactos + catalogo_articulos + inv_catalogo_articulos). Migrada de Hostinger 2026-04-20. |
| `os_gestion` | **VPS Contabo** | Sistema Gestión OS. Migrada de Hostinger 2026-04-20. |
| `inventario_produccion_effi` | **VPS Contabo** | Solicitudes producción + grupos + recetas + logs + inventario físico (17 tablas: prod_* + inv_*). NO contiene zeffi_*. |
| `u768061575_os_comunidad` | **Hostinger** | **ERP REAL — PROHIBICIÓN ABSOLUTA, NO TOCAR**. Único uso restante de Hostinger. |

**Regla activa desde 2026-04-24** (ver MANIFESTO §8): `effi_data` es intermediaria del pipeline. Apps de inventario, producción, gestión, ERP consultan `os_integracion` en el VPS, no `effi_data` local.

MariaDB corre en el **host** (systemd), NO en Docker — puerto 3306.
Credenciales locales: `osadmin` / `Epist2487.`

### Servicios activos

| Servicio | Puerto | Systemd | URL |
|---|---|---|---|
| ERP Frontend API | 9100 | `os-erp-frontend` | menu.oscomunidad.com |
| IA Admin | 9200 | `os-ia-admin.service` | ia.oscomunidad.com |
| Sistema Gestión | 9300 | `os-gestion.service` | gestion.oscomunidad.com |
| IA Service Flask | 5100 | `ia-service.service` | interno |
| WA Bridge | 3100 | `wa-bridge.service` | interno — ver `.agent/CATALOGO_APIS.md` |
| Effi Webhook Flask | 5050 | `effi-webhook.service` | interno |
| Inventario API | 9401 | `os-inventario-api.service` | inv.oscomunidad.com |
| EspoCRM | 8083 | Docker | crm.oscomunidad.com |
| NocoDB | — | Docker | nocodb.oscomunidad.com |

### Archivos clave globales

| Archivo | Propósito |
|---|---|
| `scripts/orquestador.py` | Orquestador pipeline (cada 1h Lun-Sab 06:00-20:00) |
| `scripts/.env` | Credenciales (NO en git) |
| `logs/pipeline.log` | Log del pipeline |
| `/home/osserver/docker/docker-compose.yml` | Docker compose |
| `/etc/cloudflared/config.yml` | Cloudflare tunnel |
| `.agent/CATALOGO_SCRIPTS.md` | Catálogo completo de scripts |
| `.agent/CATALOGO_APIS.md` | Catálogo de todas las APIs HTTP internas (ia_service, wa_bridge) |
| `.agent/CATALOGO_TABLAS.md` | 47+ tablas con descripciones |
| `.agent/MANIFESTO.md` | Visión, arquitectura y reglas técnicas |
| `.agent/manuales/ia_service_manual.md` | Manual IA service v2.7 |
