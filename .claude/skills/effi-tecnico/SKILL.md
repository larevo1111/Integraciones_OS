---
name: effi-tecnico
description: Skill TÉCNICO consolidado para integrar con Effi (https://effi.com.co) — autenticación, scraping con Playwright, POST directo a endpoints internos, formato de campos, exports/imports, manejo de sesión, debugging. Triggers: effi, orden de producción, OP, scraping effi, post effi, sesión effi, encargado effi, articulo_buscar, llena_, playwright_effi, import_orden_produccion, export_*.js Effi.
---

# effi-tecnico — Manual técnico de integración con Effi

Effi (https://effi.com.co) es el ERP propietario de Origen Silvestre. **No tiene API pública documentada**, pero sí endpoints internos HTTP que el form usa. Este skill consolida TODO lo necesario para integrarse con Effi: scraping, POST directo, sesión, formatos.

## 1. Arquitectura de integración con Effi

| Capa | Tecnología | Cuándo usar |
|---|---|---|
| **Sesión web (cookies)** | Playwright `storageState` en `scripts/session.json` | Todo: scraping, exports, POST directo |
| **Exports (datos)** | Scripts Playwright `scripts/export_*.js` | Bajar datos de Effi (inventario, OPs, ventas, etc.) |
| **POST directo (rápido)** | `requests.post()` Python con cookies de sesión | Crear OPs, ajustes, etc. (1s vs 60-90s) |
| **Scraping form (fallback)** | Playwright `import_orden_produccion.js` | Si POST directo falla o cambia el form |
| **BD intermedia** | `effi_data` MariaDB local (intermediaria) | Apps consultan `os_integracion` VPS, NO `effi_data` directo |

**Regla de oro**: `effi_data` local es STAGING del pipeline. Apps consultan **`os_integracion`** en VPS Contabo. Ver `feedback_effi_data_intermediaria.md`.

---

## 2. Sesión y autenticación

### Generación inicial
```bash
node scripts/session.js
```
- Abre Chromium, login manual con usuario/password en https://effi.com.co
- Guarda cookies + localStorage en `scripts/session.json`
- Sesión dura semanas/meses (Effi no expira agresivamente)

### Verificar sesión activa
```js
const { browser, page } = await getPage();  // helper existente
await page.goto('https://effi.com.co/app/orden_produccion');
if (page.url().includes('/ingreso')) { /* SESIÓN EXPIRADA — regenerar */ }
```

### Reusar cookies en Python (POST directo)
```python
import json, requests
state = json.loads(open('scripts/session.json').read())
cookies = {c['name']: c['value'] for c in state['cookies']}
s = requests.Session()
s.cookies.update(cookies)
s.headers.update({
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://effi.com.co/app/orden_produccion',
    'User-Agent': 'Mozilla/5.0 ...',
})
```

---

## 3. Endpoints HTTP internos descubiertos

### POST /app/orden_produccion/crear ⭐ (el más importante)
**Crea una OP completa**. Tiempo: ~0.2s. Form-urlencoded con arrays `[]`.

| Campo | Tipo | Notas |
|---|---|---|
| `sucursal` | int | Siempre `1` (Principal) |
| `bodega` | int | `1` = Principal |
| `fecha_inicio`, `fecha_fin` | string | Formato `DD/MM/YYYY` |
| `encargado` | int | **ID INTERNO**, NO el CC. Ver §4 |
| `observacion` | string | Texto libre |
| `tercero` | string | Vacío por defecto |
| `maquina` | string | `default` constante |
| `session_empresa`, `session_usuario` | hidden | Extraer del HTML (§7) |
| `articuloM[]` | array | Cod material |
| `cantidadM[]` | array | Cantidad |
| `costoM[]` | array | Formato `"17,000"` (coma como separador miles) |
| `loteM[]`, `serieM[]`, `descripcionM[]` | array | Vacíos OK |
| `articuloP[]`, `cantidadP[]`, `precioP[]`, `loteP[]`, `serieP[]`, `descripcionP[]` | arrays | Productos |
| `costo_produccion[]` | array | tipo_costo_id |
| `cantidad[]`, `costo[]` | arrays | Horas, $/hora otros costos |
| `costo_material`, `otros_costos`, `precio_venta`, `beneficio` | int | Totales calculados |

Implementación: [scripts/import_orden_produccion_post.py](scripts/import_orden_produccion_post.py).

### Reglas comunes — cotización venta + remisión compra

#### ⚠️ `impuestos[]` NUNCA va vacío
**Todos los artículos en Effi tienen un tipo de IVA**. Nunca enviar `impuestos[<id_concepto>][]` sin valor. El campo `zeffi_inventario.impuestos` contiene el string; mapearlo a su id numérico:

| String en `zeffi_inventario.impuestos` | id Effi |
|---|---|
| `'IVA 19%'` | `1` |
| `'IVA Exento'` | `2` |
| `'IVA 5%'` | `3` |
| `'IVA 14%'` | `4` |
| `'INCBP'` | `5` |
| `'Imp. consumo 8%'` | `6` |
| `'IVA Excluido'` | `7` |

```sql
SELECT cod_articulo, nombre, impuestos FROM zeffi_inventario WHERE cod_articulo IN (...);
```

#### ⚠️ `vendedor` NO sale de `zeffi_clientes`
`zeffi_clientes.vendedor` suele ser NULL. El vendedor real está en la última factura emitida al cliente:

```sql
SELECT id_vendedor, vendedor
FROM zeffi_facturas_venta_encabezados
WHERE cliente = '<id_cliente_effi>'
ORDER BY id_factura DESC
LIMIT 1;
```

El `id_vendedor` es el número de cédula (CC). Mapearlo al id interno Effi con `MAPEO_ENCARGADOS` en el script, o buscarlo en `zeffi_empleados` si aplica.

#### ⚠️ Forma de pago SIEMPRE Contado a 1 día
**Sin excepciones**: `t_forma_pago='1'` (Contado a 1 día). Nunca preguntar al usuario qué forma de pago usar.

---

### POST /app/cotizacion/crear ⭐ (cotización de venta)
Crea cotización completa. Form `form_CR`. ~43 fields para 1 línea + 1 forma de pago. Tiempo ~1s.

| Campo | Tipo | Notas |
|---|---|---|
| `sucursal`, `bodega`, `centro_costos` | int | `1` (Principal) |
| `fecha_entrega` | string | Formato `YYYY-MM-DD` (NO `DD/MM/YYYY` como OPs) |
| `divisa` | string | Código ISO: `'COP'` (158 opciones) |
| `trm` | int | `1` para COP |
| `cliente` | int | id Effi del cliente (resolver via búsqueda) |
| `direccion_cliente` | string | `'default'` o id de la dirección |
| `vendedor` | string | `'default'` o id del vendedor (376, 536...) |
| `tercero` | string | Vacío por defecto |
| `descuento_global`, `propina` | num | Defaults `0.00`, `0` |
| `articulo[]`, `cantidad[]`, `precio[]` | array | Líneas |
| `id_concepto[]` | string | **Random 21 dígitos** por línea, clave en `impuestos[<id>][]` |
| `bruto[]`, `descuento[]`, `total_concepto[]` | array | Calculados |
| `impuestos[<id_concepto>][]` | int | id del impuesto (1=IVA 19%, etc) |
| `t_forma_pago[]`, `valor_forma_pago[]` | array | Forma de pago. **NO requiere `medio_pago`/`caja_medio_pago`** (eso es de remisión compra) |
| `retencion[]`, `base_retencion[]`, `valor_retencion[]` | array | `'default'` + vacíos si no hay |
| `bruto_transaccion`, `subtotal_transaccion`, `total_descuento`, `total_impuesto`, `total_retencion`, `total_transaccion` | num | Totales (Effi recalcula impuesto al validar) |
| `garantia`, `observacion` | textarea | Vacíos OK |
| `prontopago`, `fecha_prontopago` | string | Vacíos OK |

Implementación: [scripts/import_cotizacion_venta_post.py](scripts/import_cotizacion_venta_post.py). URL listado: `/app/cotizacion?vigente=1`.

### POST /app/remision_c/crear ⭐ (remisión de compra)
Crea remisión de compra (entrada mercancía + pago). Form `form_CR`. ~50 fields. Tiempo ~1s.

Mismos campos base que cotización + diferencias clave:
| Campo | Notas |
|---|---|
| `fecha_compra` | NO `fecha_entrega` |
| `proveedor`, `direccion_proveedor` | NO `cliente`/`direccion_cliente` |
| `t_egreso[]` | tipo egreso por línea (`'1'` = compra normal, 126 opciones) |
| `remision_proveedor` | número de factura/remisión externa del proveedor |
| `medio_pago[]` | id medio de pago (1=Efectivo, 9 opciones) |
| `caja_medio_pago[]` | **`'1Ǆ2'`** con separador `Ǆ` (cuenta`Ǆ`caja) |
| `cuenta_medio_pago[]` | `'default'` o id |
| `valor_medio_pago[]` | mismo valor que `valor_forma_pago[]` |
| `observacion_medio_pago[]` | textarea |
| `sucursal_anticipo[]`, `id_anticipo[]` | anticipos (vacíos OK) |
| `action`, `json_ref` | hidden constantes (`'1'`, `''`) |
| Sin `vendedor`, `propina`, `tercero` | (lógico — es compra) |

Implementación: [scripts/import_remision_compra_post.py](scripts/import_remision_compra_post.py). Investigación previa: [.agent/docs/EFFI_POST_REMISION_COMPRA.md](.agent/docs/EFFI_POST_REMISION_COMPRA.md).

### POST /app/articulo/anular ⭐ (depuración masiva)
Anula (marca No Vigente) un artículo. Reversible vía "Reactivar" en UI.

**3 campos** form-urlencoded:
| Campo | Notas |
|---|---|
| `codigo` | **Token cifrado URL-encoded** del HTML (`%3D%3D` literal, NO desencodear). Ver §13 |
| `session_empresa` | `12355` |
| `session_usuario` | `origensilvestre.col@gmail.com` |

⚠️ **Importante**: Effi devuelve `HTTP 200` SIEMPRE. El éxito real es `body == "OK"`. Cualquier otra respuesta (típicamente "Error en los parámetros internos recibidos") indica fallo.

Script: `scripts/import_articulo_anular_post.py` — cods sueltos / `--csv` / `--dry-run` / `--delay`. Reusa session.json. Auto re-scrapea tokens (que se invalidan tras cada anulación de la misma página).

### POST /app/articulo/crear
Crea artículo nuevo. Form `form_CART`, ~47 campos efectivos.

**Campos mínimos**: `descripcion` (nombre), `t_articulo` (1=MP/2=PP/3=PT/4=Servicio/5=Activo), `categoria`, `sucursal=1`, `p_costo`. El resto son defaults (`marca=default`, cuentas contables=`default`, checkboxes=`on` si aplica). 4 tarifas estándar (`tarifa_precio[]`=13/15/16/19 con `p_venta[]` vacíos OK).

Response: HTTP 200 con body `"OK"` (no devuelve el id). Para obtener el id: scrape `/app/articulo` filtrando por `data-descripcion="<nombre>"` (los nuevos quedan al final).

Script: `scripts/import_articulo_crear_post.py` — CLI `--nombre/--tipo/--categoria/--costo` o `--json`.

### POST /app/articulo/modificar_articulo
Modifica artículo existente. Form similar a Crear + **3 campos extra**: `id` (real, no cifrado), `session_empresa`, `session_usuario`. Effi NO autorrellena el form al abrir el modal — JS lee los `data-*` del link `.modificar` y los inserta en el form.

**Estrategia POST directo**: scrape el `<a class="modificar">` del cod específico, extraer TODOS los `data-*` (38 campos: descripcion, referencia, t_articulo, categoria, sucursal, marca, p_costo, p_costo_promedio, p_min_venta, stock_minimo/optimo, compras/ventas/descuento/alquiler/mandato, cuentas contables, costo_inicial/valor_residual/valor_depreciado/vida_util_meses, fecha_*, observacion_activo_fijo, url_video, descripcion_detallada, valor/porcentaje/numero/texto_ref), mapear `data-X` → `name="X"` del form, aplicar cambios parciales del usuario, POST.

⚠️ Detalles importantes:
- **Checkboxes** (`gestion_stock`, `compras`, `ventas`, `descuento`, `alquiler`, `mandato`): el data viene como `"1"` o `"0"`. Effi quiere `"on"` si activo o **omitir el campo** si inactivo (no `"0"` ni `""`).
- **Selects vacíos**: usar `"default"` (no `""`) para `marca`, `cuenta_contable_*`.
- **HTML entities**: los `data-*` vienen HTML-encoded (`&quot;`, `&amp;`) — decodear antes de mandar.

Script: `scripts/import_articulo_modificar_post.py` — `--cod N --nombre X --costo Y` (cambio parcial) o `--json` (override).

### Otros endpoints internos
| Endpoint | Método | Uso |
|---|---|---|
| `/app/sucursal/llena_campos_vigentes_sucursal` | POST | Bodegas vigentes por sucursal |
| `/app/articulo/llena_articulo_buscar_stock` | POST | Buscar artículo en modal (con stock) |
| `/app/tercero/tercero/llena_tercero_buscar` | POST | Listar terceros (paginado, NO filtra por param `busqueda`) |
| `/app/orden_produccion/llena_costos_produccion` | POST | Catálogo de tipos de costo |

**Nota**: `llena_tercero_buscar` ignora el `busqueda` y devuelve los primeros 50 terceros. Para resolver CC → ID hay que paginar manualmente o cachear.

### §13 Tokens cifrados de artículo (campo `codigo`)
Los endpoints `/app/articulo/{anular,modificar_articulo,duplicar}` y `/app/articulo/adjuntar_manifiesto` esperan un **token cifrado** (no el id real). Effi lo cifra en backend con sal/clave que no tenemos — **no se puede generar localmente**.

**Cómo obtenerlo**: scrape de `/app/articulo` (paginado por `?page=N`, 50 artículos por página). Cada fila tiene:
```html
<a class="modificar" data-codigo="ITwenwlQRDqJVdis4gg3Pw==" data-id="4" ...>
<a class="anular"    data-codigo="ITwenwlQRDqJVdis4gg3Pw==" ...>
```

Regex Python: `re.findall(r'class="modificar"[^>]+data-codigo="([^"]+)"[^>]+data-id="(\d+)"', html)`

El token viene URL-encoded (`%3D%3D` = `==`). Antes de POSTear, des-encodear con `urllib.parse.unquote()`. Para 492 artículos requiere ~10 GETs (1 por página).

---

## 4. Mapeo CC/NIT → ID interno (encargados)

Effi maneja empleados como "terceros" con ID interno (ej: `536` para Deivy CC `74084937`). Mapeo conocido:

```python
MAPEO_ENCARGADOS = {
    '74084937':   '536',  # Deivy Andres Gonzalez Gutierrez
    # '1017206760': '???',  # Laura — agregar cuando se sepa
    # '1128457413': '???',  # Jenifer Alexandra Cano Garcia
}
```

**Cómo descubrir un nuevo ID**: usar el script con `SPY_REQUESTS=1` (ver §6) creando una OP con ese empleado, capturar el `encargado=NNN` del POST.

---

## 5. Formatos especiales

### Números con miles
Effi acepta `"17,000"` (coma). NO usar punto: `"17.000"` lo interpreta como `17.000` decimales.

```python
def _formato_coma(n):
    n = float(n)
    if n == int(n): return f'{int(n):,}'  # 17000 → "17,000"
    return f'{n:.2f}'.replace('.', ',')  # 0.5 → "0,50"
```

### Fechas
Formato `DD/MM/YYYY`. Convertir desde ISO:
```python
def _fmt_fecha(iso):
    y, m, d = iso.split('-')
    return f'{d}/{m}/{y}'
```

### Cantidades decimales
Effi acepta `0.05` o `0,05`. Probado con punto, funciona.

---

## 6. Espionaje (descubrir nuevos endpoints)

`scripts/import_orden_produccion.js` tiene un **hook opt-in** activable por env var:

```bash
SPY_REQUESTS=1 node scripts/import_orden_produccion.js /tmp/op.json
# Resultado: /tmp/espia_op_full.json con todas las requests POST a effi.com.co
```

**Qué captura**: URL, método, headers, post_data, response_status, response_body (200 chars).
**Filtra**: telemetría New Relic (`bam.nr-data.net`).

Este patrón sirve para descubrir endpoints internos de cualquier módulo Effi (ajustes, traslados, facturas, etc.).

---

## 7. Extraer hidden fields de la sesión

`session_empresa` y `session_usuario` vienen como hidden fields en el HTML. Extraer con regex:

```python
r = s.get('https://effi.com.co/app/orden_produccion')
emp = re.search(r'name=["\']session_empresa["\'][^>]*value=["\'](\d+)["\']', r.text)
usr = re.search(r'name=["\']session_usuario["\'][^>]*value=["\']([^"\']+)["\']', r.text)
```

**Valores conocidos OS**: `session_empresa=12355`, `session_usuario=origensilvestre.col@gmail.com`. Si Effi cambia, regex los detecta automáticamente.

---

## 8. Patrón híbrido: POST directo + Playwright fallback

**Política**: intentar POST primero (rápido), si falla por cualquier razón caer a Playwright (lento pero robusto). Patrón actual en `_ejecutar_op_background`:

```python
try:
    op_id = crear_op_post(json_path)  # 1s
except Exception:
    # Fallback Playwright (60-90s)
    proc = subprocess.run(['node', 'scripts/import_orden_produccion.js', json_path], ...)
    op_id = parse_OP_CREADA(proc.stdout)
```

**Por qué no eliminar Playwright**: si Effi cambia el form (campos hidden, validaciones, CSRF, etc.), POST puede romperse. Playwright es resiliente porque clickea visual.

---

## 9. Exports de Effi (Playwright)

Patrón: navegar al módulo → click "Exportar" → marcar campos → solicitar Excel → descargar. Scripts en `scripts/export_*.js`.

Exports clave:
- `export_inventario.js` → catálogo de artículos (zeffi_inventario)
- `export_produccion_encabezados.js` → OPs (zeffi_produccion_encabezados)
- `export_produccion_reportes.js` → 3 reportes en uno: materiales, articulos_producidos, otros_costos
- `export_facturas_venta.js`, `export_remisiones_venta.js`, etc.

**Limitación**: Effi devuelve algunos exports como **HTML disfrazado de .xlsx** (especialmente reportes complejos). El parser `import_all.js` detecta y maneja ambos casos (PK header vs `<html>`).

---

## 10. BDs y tablas Effi

Tablas que Effi exporta a `effi_data` (~41 tablas zeffi_*):

| Tabla | Contenido |
|---|---|
| `zeffi_inventario` | Catálogo artículos (cod, nombre, costo_manual, vigencia, etc.) |
| `zeffi_produccion_encabezados` | OPs (id_orden, fecha, encargado, observacion) |
| `zeffi_articulos_producidos` | Productos producidos por OP (con precio_minimo_ud) |
| `zeffi_materiales` | Materiales consumidos por OP |
| `zeffi_otros_costos` | M.O. y costos extra por OP |
| `zeffi_costos_produccion` | Catálogo tipos de costo (M.O. HORA, TOSTADO, TRANSPORTE, etc.) |
| `zeffi_facturas_venta`, `zeffi_remisiones_venta` | Ventas |

**Convención cantidades/costos en BD**: vienen como string con coma como decimal: `"18,78"` `"7000,0000"`. Para cálculos: `float(s.replace('.','').replace(',', '.'))`.

---

## 11. Auditoría OPs creadas desde la app

Tabla `prod_ops_creadas` en BD `inventario_produccion_effi` (VPS):

```sql
CREATE TABLE prod_ops_creadas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  op_effi VARCHAR(20),              -- ID OP en Effi
  fecha_creacion DATETIME,
  usuario VARCHAR(100),              -- Del JWT
  solicitudes_ids TEXT,              -- "68,69,70"
  payload_json LONGTEXT,             -- JSON completo enviado
  log_creacion LONGTEXT,             -- stdout+stderr
  duracion_seg INT,
  estado ENUM('ejecutando','ok','error'),
  error TEXT
)
```

Endpoints REST:
- `GET /api/produccion/ops-historico` — últimas 50
- `GET /api/produccion/ops-historico/{id}` — detalle con payload+log

---

## 12. Anti-patrones

❌ Hardcodear costos/precios en código (vienen de `zeffi_inventario.costo_manual` que MUTA al validar OPs).
❌ Usar `LIKE '%palabra1 palabra2%'` (no contiguo). Ver `CLAUDE.md §Quicksearch`.
❌ Enviar `encargado=74084937` (es CC, Effi quiere ID interno `536`).
❌ Enviar `costoM[]=17000.00` (Effi espera `"17,000"`).
❌ Olvidar `X-Requested-With: XMLHttpRequest` en POST (Effi puede rechazar).
❌ Saltarse `session.json` y hacer login programático (no funciona — Effi tiene 2FA en algunos flows).
❌ Modificar OP ya validada en Effi (rompe trazabilidad). Crear OP nueva con corrección.

---

## 13. Cómo anular una OP de test

**Effi NO tiene endpoint de anulación REST**. Toca:
1. Manual desde UI: click en la OP → menú → "Anular" → confirmar
2. Marcar la observación con "TEST — anular" para identificar fácil al revisar

Si crearon OPs de prueba, lista los ids y pídele a Santi/Deivy que las anulen manualmente.

---

## 14. Skills relacionadas
- `effi-database` — esquema de tablas zeffi_*
- `effi-negocio` — lógica de negocio (vigencia, canales, etc.)
- `playwright-effi` — patrones específicos de scraping Playwright
- `produccion-recetas` — recetas, materiales, formato de OPs

Este skill **NO reemplaza** los anteriores — los **complementa con la capa técnica HTTP**.

---

## 15. Archivos clave del repo

| Archivo | Propósito |
|---|---|
| `scripts/session.json` | Cookies de sesión Effi (gitignored, sensible) |
| `scripts/session.js` | Genera/refresca session.json |
| `scripts/import_orden_produccion.js` | Crea OP via Playwright (fallback) — con SPY hook |
| `scripts/import_orden_produccion_post.py` | Crea OP via POST directo (~1s) |
| `scripts/import_cotizacion_venta_post.py` | Crea cotización venta via POST directo (~1s) |
| `scripts/import_remision_compra_post.py` | Crea remisión de compra via POST directo (~1s) |
| `scripts/import_articulo_crear_post.py` | Crea artículo via POST directo |
| `scripts/import_articulo_modificar_post.py` | Modifica artículo via POST directo |
| `scripts/import_articulo_anular_post.py` | Anula artículo (con --csv batch) |
| `scripts/export_*.js` | Exports Playwright de cada módulo |
| `scripts/import_all.js` | Importa exports a `effi_data` (HTML/xlsx) |
| `scripts/refresh_effi_produccion.py` | Orquesta export+import+sync VPS |
| `scripts/produccion/api.py` | Backend que orquesta crear-op-effi |
| `.agent/docs/EFFI_POST_DIRECTO.md` | Doc original del descubrimiento (referencia) |

---

## 16. Tiempos típicos

| Operación | Tiempo |
|---|---|
| Login manual + generar sesión | 30s (única vez) |
| Crear OP via POST directo | ~1s ⭐ |
| Crear cotización venta via POST | ~1s ⭐ |
| Crear remisión compra via POST | ~1s ⭐ |
| Crear OP via Playwright (fallback) | 60-90s |
| Export inventario | ~30s |
| Export produccion_encabezados | ~60s |
| Export produccion_reportes (3 en 1) | ~120s |
| Refresh completo (5 tablas + sync VPS) | ~5 min |
