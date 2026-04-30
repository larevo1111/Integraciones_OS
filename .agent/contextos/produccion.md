# Producción OS — Contexto del Subproyecto

**Creado**: 2026-04-28
**Actualizado**: 2026-04-30
**Estado**: Operativo en VPS Contabo (`inv.oscomunidad.com`)
**Versión actual**: v0.4.10

---

## Qué es
App React + Vite + Shadcn/ui que centraliza la **programación de producción**: solicitudes, recetas, OPs y stock. Convive bajo el mismo dominio (`inv.oscomunidad.com`) con el módulo de Inventario Físico (que usa el mismo backend).

## Arquitectura
```
Frontend Producción (React/Vite, /produccion/dist/)
   ↓ servido por
API Producción (FastAPI, puerto 9600)  ← scripts/produccion/api.py
   ↓ proxy /api/inventario/* hacia
API Inventario (FastAPI, puerto 9401)  ← scripts/inventario/api.py
   ↓ ambas conectan a
BD inventario_produccion_effi (VPS, modo direct sin SSH tunnel)
   + BD os_integracion (VPS, lectura de catálogo Effi y OPs)
```

Ambas APIs y la BD corren en el **mismo VPS Contabo** desde 2026-04-28. Antes corrían en local con SSH tunnel — la migración eliminó esa categoría de problemas.

## Funcionalidades

### 1. Solicitudes (`/solicitudes`)
- Pedir producción de productos (cod_articulo + cantidad)
- 2 modos: "Por producto" (Combobox individual) y "Por grupo" (CHOCOLATE GRANULADO, MIELES, etc — todas las presentaciones de un grupo)
- Agrupar varias solicitudes en una sola OP (botón "Programar")
- Estados: solicitado / programando / programado
- Auto-refresh cada 5s mientras hay solicitudes en estado "programando" (creación OP en background)

### 2. Calendario (`/calendario`)
Placeholder — vista mensual de solicitudes programadas (próximamente).

### 3. Recetas (`/recetas`)
Libro maestro de recetas (110+ recetas validadas) por familia: mieles, chocolates, cremas_mani, infusiones, coberturas, tabletas, propóleo, polen, cacao_nibs, otros.

### 4. Receta detalle (`/recetas/:cod`) — **EDITABLE**
Tablas Materiales / Productos / Costos / **Puntos críticos** editables in-place:
- Combobox cod (búsqueda multi-palabra)
- Input cantidad y costo unitario
- Papelera por fila + "+Agregar" en header
- Toggle radio para producto principal
- Totales recalculan en vivo
- Botones "Descartar" / "Guardar cambios" aparecen solo cuando hay cambios

Sección **"Observaciones para Effi"** (textarea editable): texto fijo que se inyecta en la observación de cada OP de ese producto. Se precarga editable en el modal "Programar OP" (el usuario puede ajustarlo por OP). Backend: `PATCH /api/recetas/{cod}` con `observaciones_op`.

Sección **"Puntos críticos"** (tabla editable): parámetros medibles del proceso productivo con rango aceptable. Columnas: Parámetro, Tipo (numerico/booleano/texto/seleccion), Unidad (Combobox sobre maestra), Instrumento (datalist: Termómetro/Gramera/Cronómetro/Refractómetro/pH-metro/Higrómetro/Visual/Cuchillo), Mín, Máx, Opciones (CSV), Obligatorio. Inputs Mín/Máx/Unidad disabled si tipo≠numerico. Backend: `PUT /api/recetas/{cod}/full` reescribe puntos junto con materiales/costos/productos.

Backend: `PUT /api/recetas/{cod}/full` reescribe los 4 sub-arreglos (materiales, productos, costos, puntos_criticos).

### 5. Inventarios (`/inventarios`, `/inventarios/:fecha`, `/catalogo`)
Sub-app de inventarios físicos (módulo separado pero comparte backend). Ver [inventario_fisico.md](inventario_fisico.md).

### 6. Inconsistencias (`/inconsistencias`)
Listado de análisis de stocks negativos / descuadres. Click → detalle (`/inconsistencias/:id`) con problema, causa raíz, ajustes asociados, y contenido del `.md` renderizado.

### 7. Histórico ajustes (`/historico-ajustes`)
Tabla de TODOS los ajustes de inventario aplicados desde el sistema, con link al análisis que los generó.

### 8. Configuración (`/config`)
Placeholder — parámetros del módulo (próximamente).

## Sidebar global
- Sync Effi (botón footer): dispara `POST /api/refresh-effi` que ejecuta `refresh_effi_produccion.py`. Emite evento `effi-synced` cuando termina, y las páginas relevantes recargan datos automáticamente.

## Servicios systemd

### En VPS (producción)
- `os-produccion-api.service` (puerto 9600) — sirve frontend + API Producción + proxy a Inventario
- `os-inventario-api.service` (puerto 9401) — API Inventario

Service files versionados en `scripts/produccion/` y `scripts/inventario/`. Para reinstalar: copiar a `/etc/systemd/system/` + `daemon-reload + enable --now`.

### En LOCAL (servidor del taller)
- `effi-pipeline.timer` + `effi-pipeline.service` — orquestador grande Effi → effi_data LOCAL → sync a `os_integracion` VPS. **Frecuencia: cada 1 hora.** Ejecuta `scripts/orquestador.py`.
- APIs locales `os-produccion-api` y `os-inventario-api`: **detenidas** (`systemctl stop`), no `disable` — quedan como respaldo durante 1 semana post-migración.

## Tablas BD principales

### `inventario_produccion_effi` (VPS)
- `prod_recetas` (110+) — libro maestro. Campos clave: `cod_articulo`, `nombre`, `familia`, `patron`, `estado` (borrador/validada), `notas_analisis`, **`observaciones_op`** (texto fijo que va a Effi), confianza (alta/media/baja)
- `prod_recetas_materiales` — materiales por receta (cod_material, cantidad_por_lote, ratio_por_unidad, costo_unit_snapshot)
- `prod_recetas_productos` — productos coproducidos (cod_articulo, es_principal, cantidad_por_lote, precio_min_venta_snapshot)
- `prod_recetas_costos` — costos M.O. por receta (tipo_costo_id, cantidad_por_lote, costo_unit)
- **`prod_recetas_puntos_criticos`** (NUEVA 2026-04-29) — parámetros de calidad por receta. FK receta_id ON DELETE CASCADE. Campos: parametro, tipo (numerico/booleano/texto/seleccion), unidad, instrumento, valor_min, valor_max, opciones_json, obligatorio, orden. El módulo Gestión OS leerá esta tabla cuando muestre puntos críticos en validación de OPs.
- **`prod_unidades_medida`** (NUEVA 2026-04-29) — maestra de unidades. 35 entradas: 22 espejo de Hostinger `costos_unidades` + 13 locales para puntos críticos. Campos: simbolo UNIQUE, nombre, categoria, factor, origen (hostinger/local). Endpoint `GET /api/produccion/unidades`.
- `prod_solicitudes` — solicitudes de producción del frontend
- `prod_grupos` — agrupación de solicitudes en OP
- `prod_ops_creadas` — histórico de OPs creadas desde el sistema (con log_creacion + duracion + estado)
- `prod_logs` — log general
- `inv_conteos` — conteos físicos de inventario
- `inv_rangos` — unidades y grupos por cod_articulo
- `inv_auditorias` — log de cambios en conteos
- `inv_observaciones` — notas por conteo
- `inv_fechas` — meta de fechas de inventario (cierre, etc)
- `inv_analisis_inconsistencias` (NUEVA 2026-04-28, ALTER 2026-04-29: +fecha_inventario, tipo_inconsistencia, estado, inventario_teorico/fisico, costo_unitario, costo_total_impacto, updated_at)
- `inv_ajustes_historico` (NUEVA 2026-04-28, FK a análisis. ALTER 2026-04-29: +fecha_planificado, estado, costo_total, error_msg, updated_at)

### `os_integracion` (VPS) — espejo de Effi
- `zeffi_inventario` — catálogo + stocks por bodega
- `zeffi_produccion_encabezados` — OPs
- `zeffi_articulos_producidos` — productos resultantes de OPs
- `zeffi_materiales` — materiales consumidos
- `zeffi_otros_costos` — costos M.O. de OPs
- `zeffi_trazabilidad` — log de movimientos por artículo (clave para auditorías)
- `zeffi_ajustes_inventario` — ajustes aplicados en Effi

## Scripts clave

### Refresh Effi (en LOCAL)
- `scripts/orquestador.py` — pipeline grande Effi → effi_data → VPS (cada 1h via systemd timer)
- `scripts/refresh_effi_produccion.py` — refresh "rápido" de 5 tablas (inventario + 4 OPs), mismo flujo que el grande pero acotado

### Crear OP en Effi (background task)
- `scripts/import_orden_produccion_post.py` — POST directo (1s típico). **Captura el id real scrapeando `data-id` de `/app/orden_produccion` ANTES y DESPUÉS del POST** (el POST devuelve solo "OK"). Sin esto el id se cacheaba mal.
- `scripts/import_orden_produccion.js` — fallback Playwright (60-90s) si POST directo falla

### Ajustes de inventario en Effi (Playwright)
- `scripts/import_ajuste_inventario.js <bodega_id> <archivo.xlsx> [observacion]`
- Formato Excel en `plantilla_importacion_ajuste_inventario.xlsx`

### Artículos en Effi (POST directo, sin Playwright) — 2026-04-29
3 scripts Python con scraping de tokens cifrados:
- **`scripts/import_articulo_anular_post.py`** — anula 1+ artículos. `python3 ... 587,588 [--csv archivo.csv] [--dry-run] [--delay 0.5]`. Scrapea ~10 páginas para mapear `cod → codigo cifrado` (Effi requiere ese token URL-encoded TAL CUAL del HTML, no desencodear).
- **`scripts/import_articulo_crear_post.py`** — crea artículo. `python3 ... --nombre "X" --tipo 1 --categoria 47 --costo 1000`. Devuelve el id asignado scrapeando post-create.
- **`scripts/import_articulo_modificar_post.py`** — modifica artículo. `python3 ... --cod 587 --nombre "Nuevo" --costo 5000` (cambio parcial: lee data-* actual del link `.modificar`, mergea con cambios, POSTea). Soporta `--json` para override completo.

⚠️ Effi devuelve HTTP 200 SIEMPRE. El éxito real es `body=="OK"`. Cualquier otra respuesta (típicamente "Error en los parámetros internos recibidos") indica fallo. Validación documentada en `.claude/skills/effi-tecnico/SKILL.md` §3 y §13.

### Calidad / Puntos críticos — 2026-04-29
Doc completo en `.agent/docs/CALIDAD_Y_PUNTOS_CRITICOS.md`:
- Modelo 5S: Inspección genérica (vive en módulo Gestión OS) vs Puntos críticos (vive en ficha receta)
- Reglas para definir puntos críticos: solo medible, máximo 3-5 por producto
- Instrumentos disponibles en planta OS: termómetro, cronómetro, balanza, pH-metro (en agua + nevera), revisión organoléptica, test de PAPEL (NO cuchillo)
- 13 productos PP CLAVE identificados (procesos base, no presentaciones derivadas)
- Plantillas concretas por proceso (cocción mesa, templado, pasteurización miel, tostado cacao, tostado frutos secos, crema molienda, infusión, chocomiel, chocobeetal)
- Estado: en validación con Santi lote por lote (al 30-abr 0 de 99 PP con puntos definidos)

## Flujos críticos

### Crear OP desde frontend
1. Usuario selecciona solicitudes en `/solicitudes` y aprieta "Programar"
2. Modal `programar-grupo-dialog.jsx` muestra preview editable (productos, materiales, costos)
3. POST `/api/produccion/crear-op-effi` → encola BackgroundTask
4. BackgroundTask ejecuta `_ejecutar_op_background()`:
   - Intento 1: `import_orden_produccion_post.py` (POST directo, ~1s)
   - Fallback: `import_orden_produccion.js` (Playwright, ~60-90s)
5. Captura el id real de Effi y actualiza `prod_solicitudes.op_effi` + `prod_ops_creadas.op_effi`

### Refresh Effi manual
1. Usuario aprieta botón "Sync Effi" en sidebar
2. POST `/api/refresh-effi` (en VPS) → ejecuta `refresh_effi_produccion.py` localmente en VPS
3. Polling de `/api/refresh-effi/estado` cada 2.5s para mostrar progreso
4. Al terminar (`ok`/`error`), emite `effi-synced` → las páginas recargan
5. Observación: el cron grande sigue corriendo en LOCAL cada 1h (no se mezcla con esto)

### Auditoría de inconsistencias
1. Detección masiva de stocks negativos por bodega (query a `zeffi_inventario`)
2. Análisis trazabilidad por (cod, bodega) → causa raíz + recomendación
3. `.md` por caso en `analisis_de_inventario/<fecha>/` + INSERT en `inv_analisis_inconsistencias`
4. Ajustes Effi (Playwright) agrupados por bodega → INSERT en `inv_ajustes_historico` con FK
5. Refresh Effi para verificar que negativos quedaron en 0

## Reglas activas (del repo)

- **CLAUDE.md / MANIFESTO §8A**: paths/hosts SIEMPRE relativos. Migración entre servidores = git pull + .env + DNS, cero código.
- **MANIFESTO §8B**: credenciales centralizadas en `integracion_conexionesbd.env`. Modo `direct` cuando BD está en mismo servidor.
- **CLAUDE.md Quicksearch**: búsquedas LIKE multi-palabra siempre con AND, no string contiguo.
- **CLAUDE.md timezone**: hora Colombia (UTC-5) via `lib/timezone.js`. NUNCA `toISOString().slice(0,10)`.

## Próximos pasos pendientes
- Mover plan auditoría 28-abr a `completados/`
- Cod 582 MACADAMIA GRAGEADA: ajuste +0.01 en Principal (fantasma de 10g, no urgente)
- Anular OPs de test creadas durante desarrollo: 2214, 2215, 2216, 2218, 2219, 2220 (si siguen activas)
- Costos a arreglar en Effi: cod 334 ($3000), cod 139 ($61) — Effi tiene $0
