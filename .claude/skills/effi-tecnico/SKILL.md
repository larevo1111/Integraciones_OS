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

### Otros endpoints internos
| Endpoint | Método | Uso |
|---|---|---|
| `/app/sucursal/llena_campos_vigentes_sucursal` | POST | Bodegas vigentes por sucursal |
| `/app/articulo/llena_articulo_buscar_stock` | POST | Buscar artículo en modal (con stock) |
| `/app/tercero/tercero/llena_tercero_buscar` | POST | Listar terceros (paginado, NO filtra por param `busqueda`) |
| `/app/orden_produccion/llena_costos_produccion` | POST | Catálogo de tipos de costo |

**Nota**: `llena_tercero_buscar` ignora el `busqueda` y devuelve los primeros 50 terceros. Para resolver CC → ID hay que paginar manualmente o cachear.

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
| Crear OP via Playwright (fallback) | 60-90s |
| Export inventario | ~30s |
| Export produccion_encabezados | ~60s |
| Export produccion_reportes (3 en 1) | ~120s |
| Refresh completo (5 tablas + sync VPS) | ~5 min |
