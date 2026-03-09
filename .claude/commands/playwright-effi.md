# Skill: Playwright para exports de Effi

Guía de patrones, errores conocidos y lecciones aprendidas para escribir o modificar scripts de exportación de Effi con Playwright.

---

## REGLA FUNDAMENTAL — No asumir, preguntar

> **Antes de escribir cualquier lógica de descarga, preguntar cómo se comporta la página.**
>
> Effi tiene al menos 4 mecanismos distintos para generar archivos. Asumir el mecanismo
> equivocado genera scripts que nunca funcionan o que esperan indefinidamente.
>
> Preguntar siempre: *"¿el archivo sale de inmediato al hacer click, o hay un paso intermedio
> (modal, ventana emergente, notificación asíncrona)?"*

---

## Arquitectura base de todos los scripts

```
/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/
├── session.js        → getPage() — reutiliza sesión autenticada
├── utils.js          → contarFilas(), aplicarFiltroVigente()
├── export_*.js       → 26 scripts de exportación
└── session.json      → estado de sesión Playwright (cookies + localStorage)
```

**Plantilla mínima:**
```js
const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');
const fs   = require('fs');

const EXPORT_DIR = '/exports/nombre_modulo';
const EFFI_URL   = 'https://effi.com.co/app/ruta_modulo?sucursal=1';
const fecha      = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) fs.mkdirSync(EXPORT_DIR, { recursive: true });
  const { browser, page } = await getPage();
  try {
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // ... lógica específica
  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_nombre_modulo_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
```

---

## Parámetro de URL — sucursal vs vigente

**Crítico:** el parámetro en la URL de Effi determina cuántos registros trae.

| Parámetro | Efecto | Usar para |
|---|---|---|
| `?sucursal=1` | Todos los registros históricos de todas las sucursales | **Siempre preferir este** |
| `?vigente=1` | Solo registros actualmente activos/abiertos | No usar para histórico |
| *(sin parámetro)* | Varía por módulo, puede filtrar por fecha | Evitar |

**Lección aprendida:** `export_ordenes_venta.js` usaba `?vigente=1` y traía muy pocos registros.
Al cambiar a `?sucursal=1` pasó de ~100 a 695 encabezados + 7166 detalle.

**Sugerencia:** si un export trae menos registros de los esperados, probar agregar `?sucursal=1`
a la URL como primer paso de diagnóstico.

---

## Tipos de export y su patrón

### Tipo 1 — Descarga directa (mayoría de scripts)

Click en botón → Playwright intercepta el evento `download` directamente.

```js
const [dl] = await Promise.all([
  page.waitForEvent('download'),
  page.click('text=Exportar a excel'),
]);
await dl.saveAs(rutaDestino);
```

**Scripts que usan este patrón:**
`clientes`, `proveedores`, `bodegas`, `trazabilidad`, `ajustes_inventario`,
`traslados_inventario`, `categorias_articulos`, `ordenes_compra`, `facturas_compra`,
`remisiones_compra`, `cotizaciones_ventas`, `cuentas_por_pagar`, `cuentas_por_cobrar`,
`comprobantes_ingreso`, `guias_transporte`, `tipos_egresos`, `tipos_marketing`,
`produccion_encabezados`, `produccion_reportes`, `costos_produccion`, `devoluciones_venta`

---

### Tipo 2 — Encabezados + Detalle (descarga directa ambos)

El módulo tiene dos exports: "Exportar a excel" (encabezados) y "Reporte de conceptos" (detalle).
Ambos generan descarga directa con `waitForEvent('download')`.

```js
// Encabezados
const [dl1] = await Promise.all([
  page.waitForEvent('download'),
  page.click('text=Exportar a excel'),
]);
await dl1.saveAs(fileEncabezados);

// Detalle
await page.click('text=Reportes y análisis de datos');
await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });
const [dl2] = await Promise.all([
  page.waitForEvent('download'),
  page.click('text=Reporte de conceptos'),
]);
await dl2.saveAs(fileDetalle);
```

**Scripts:** `facturas_venta`, `notas_credito_venta`, `ordenes_venta`

---

### Tipo 3 — Modal con checkboxes + window.open (remisiones_venta detalle)

El "Reporte de conceptos" abre un **modal con checklist** de campos antes de exportar.
Al hacer submit, Effi llama `window.open(url)` en lugar de generar un download event.
La URL capturada ES el archivo — descarga inmediata, no asíncrona.

**Flujo:**
1. Click "Reportes y análisis de datos" → "Reporte de conceptos" → modal aparece
2. Marcar todos los checkboxes del modal
3. Interceptar `window.open` antes de hacer submit
4. Click submit → capturar URL → descargar con `http.get` autenticado

```js
// Paso 1: abrir modal
await page.click('text=Reportes y análisis de datos');
await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });
await page.click('text=Reporte de conceptos');
await page.waitForSelector('#modalExcelConceptos', { timeout: 10000 });
await page.waitForTimeout(500);

// Paso 2: marcar todos los checkboxes
const total = await page.evaluate(() => {
  const checkboxes = document.querySelectorAll('#form_excel_conceptos input[type="checkbox"]');
  checkboxes.forEach(cb => { cb.checked = true; });
  return checkboxes.length;
});
console.log(`✅ Marcados ${total} campos (todos)`);

// Paso 3: interceptar window.open
await page.evaluate(() => {
  window._reportUrl = null;
  window.open = function(url) { window._reportUrl = url; return null; };
});

// Paso 4: submit + capturar URL + descargar
await page.locator('#btnValidarExcelConceptos').click();
await page.waitForFunction(() => window._reportUrl !== null, { timeout: 15000 });

const reportUrlRel = await page.evaluate(() => window._reportUrl);
const reportUrl    = new URL(reportUrlRel, 'https://effi.com.co/app/').href;

const cookies      = await context.cookies();
const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
await downloadFile(reportUrl, cookieHeader, fileDetalle);
```

**Scripts:** `remisiones_venta` (detalle)

> **Nota:** La URL generada por `window.open` ya incluye los parámetros de los checkboxes
> (`c1=1&c2=1...c75=1&sucursal=1`), así que marcarlos en el modal es lo que los incluye.

---

### Tipo 4 — Modal con checkboxes + notificación asíncrona (inventario)

**Solo `export_inventario.js`.** Al hacer submit, Effi genera el archivo en background
y lo notifica mediante el panel de notificaciones (`#notify-list`). No hay download event
ni `window.open` — hay que esperar a que aparezca el enlace en notificaciones.

```js
// Submit
await page.locator('#btnValidarExcel').click();
await page.waitForSelector('#form_excel', { state: 'hidden', timeout: 15000 });

// Esperar generación (~12s hardcodeado para inventario)
await page.waitForTimeout(12000);

// Leer enlace de notificaciones
await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
await page.waitForSelector('#notify-list', { timeout: 10000 });
const enlaceDescarga = await page.evaluate(() => {
  const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
  return links.length > 0 ? links[0].href : null;
});
```

> **IMPORTANTE:** Este patrón (notificaciones) es EXCLUSIVO de `inventario`.
> NO aplicar a otros módulos aunque tengan modal de checkboxes.

---

## Error clásico — Confundir Tipo 3 con Tipo 4

**El bug de `remisiones_venta`:** el script fue escrito basándose en `inventario.js`
y por eso esperaba la notificación asíncrona. Resultado: el script quedaba esperando
5 minutos en un polling que nunca terminaba, porque el archivo YA había sido generado
por `window.open` desde el primer momento.

**Síntoma:** script cuelga en `"⏳ Esperando nuevo archivo en notificaciones (máx 5 min)..."` o
en `page.waitForEvent: Timeout 30000ms exceeded while waiting for event "download"`.

**Diagnóstico:** si `waitForEvent('download')` falla con timeout pero el modal sí se cerró,
es probable que el mecanismo sea `window.open`. Agregar un interceptor temporal para confirmar:

```js
await page.evaluate(() => {
  const orig = window.open;
  window.open = function(url, ...args) {
    console.log('window.open llamado con:', url);
    return orig.call(this, url, ...args);
  };
});
```

---

## Marcar checkboxes en modales

Siempre usar `page.evaluate()` para manipular checkboxes directamente en el DOM
en lugar de hacer clicks individuales (más rápido y confiable):

```js
// Marcar todos
const total = await page.evaluate(() => {
  const checkboxes = document.querySelectorAll('#id_form input[type="checkbox"]');
  checkboxes.forEach(cb => { cb.checked = true; });
  return checkboxes.length;
});

// IDs de formularios conocidos en Effi:
// inventario        → #form_excel          / botón: #btnValidarExcel
// remisiones_venta  → #form_excel_conceptos / botón: #btnValidarExcelConceptos
```

---

## Función downloadFile (para window.open / http directo)

```js
const https = require('https');
const http  = require('http');

function downloadFile(url, cookieHeader, destPath) {
  return new Promise((resolve, reject) => {
    const urlObj   = new URL(url);
    const protocol = urlObj.protocol === 'https:' ? https : http;
    protocol.get({ hostname: urlObj.hostname, path: urlObj.pathname + urlObj.search,
                   headers: { Cookie: cookieHeader } }, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        const redir = new URL(res.headers.location);
        protocol.get({ hostname: redir.hostname, path: redir.pathname + redir.search,
                       headers: { Cookie: cookieHeader } }, (res2) => {
          const file = fs.createWriteStream(destPath);
          res2.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }).on('error', reject);
      } else {
        const file = fs.createWriteStream(destPath);
        res.pipe(file);
        file.on('finish', () => { file.close(); resolve(); });
      }
    }).on('error', reject);
  });
}

// Obtener cookieHeader:
const cookies      = await context.cookies();  // requiere context, no solo page
const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
```

> **Nota:** `getPage()` retorna `{ browser, context, page }`. Si se necesita `context`
> (para cookies o para `window.open`), desestructurar los tres.

---

## Formato de archivos exportados

La mayoría de exports de Effi son **HTML ISO-8859 disfrazados de `.xlsx`**, no Excel real.
`import_all.js` detecta esto automáticamente con `isHtmlFile()`. No impacta en los scripts
de export — solo relevante en el import.

| Tipo | Scripts |
|---|---|
| HTML disfrazado de xlsx (ISO-8859) | Mayoría (clientes, proveedores, inventario, etc.) |
| Excel real | `facturas_venta` encabezados, algunos otros |

---

## Checklist al crear un script nuevo

- [ ] ¿La URL usa `?sucursal=1`? (preferir sobre `?vigente=1`)
- [ ] ¿El export es directo (Tipo 1) o tiene pasos intermedios?
- [ ] ¿Hay modal de checkboxes? → preguntar si el submit genera download directo o `window.open`
- [ ] ¿Se necesita `context` además de `page`? (necesario para cookies con window.open)
- [ ] ¿El directorio de export existe? (`fs.mkdirSync(..., { recursive: true })`)
- [ ] ¿El script imprime `✅ Exportado: ruta (N filas)` al finalizar?
- [ ] ¿Hay `process.exit(1)` + screenshot en el catch?
- [ ] ¿Está agregado en `export_all.sh` y en `.agent/CATALOGO_SCRIPTS.md`?
