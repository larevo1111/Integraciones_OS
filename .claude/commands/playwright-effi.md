# Skill: Playwright para exports de Effi

Guía de patrones, errores conocidos y lecciones aprendidas para escribir o modificar scripts de exportación de Effi con Playwright.

---

## REGLA FUNDAMENTAL — No asumir, preguntar

> **Antes de escribir cualquier lógica de descarga, verificar cómo se comporta la página.**
>
> Effi tiene al menos 4 mecanismos distintos para generar archivos. Asumir el mecanismo
> equivocado genera scripts que nunca funcionan o que esperan indefinidamente.
>
> Antes de codificar, preguntar: *"¿el archivo sale de inmediato al hacer click, o hay
> un paso intermedio (modal, ventana emergente, notificación asíncrona)?"*
>
> Para diagnosticar un botón desconocido, agregar listeners temporales ANTES del click:
> ```js
> page.on('download', d => console.log('DOWNLOAD:', d.url()));
> page.on('request',  r => console.log('REQUEST:', r.url()));
> page.on('popup',    p => console.log('POPUP:', p.url()));
> await page.evaluate(() => {
>   window.open = (url) => { console.log('window.open:', url); return null; };
> });
> ```

---

## Arquitectura base de todos los scripts

```
/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/
├── session.js        → getPage() — reutiliza sesión autenticada
├── utils.js          → contarFilas()
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

| Parámetro | Efecto | Usar para |
|---|---|---|
| `?sucursal=1` | Todos los registros históricos de todas las sucursales | **Preferir siempre** |
| `?vigente=1` | Solo registros actualmente activos/abiertos | Solo si el módulo lo requiere (ej. facturas_venta) |

**Si un export trae menos registros de lo esperado:** cambiar a `?sucursal=1` como primer diagnóstico.

---

## Tipos de export y su patrón

### Tipo 1 — Descarga directa con evento download

Click en botón → Playwright intercepta el evento `download` directamente.

```js
const [dl] = await Promise.all([
  page.waitForEvent('download'),
  page.click('text=Exportar a excel'),
]);
await dl.saveAs(rutaDestino);
```

**Scripts:** `clientes`, `proveedores`, `bodegas`, `trazabilidad`, `ajustes_inventario`,
`traslados_inventario`, `categorias_articulos`, `ordenes_compra`, `facturas_compra`,
`remisiones_compra`, `cotizaciones_ventas`, `cuentas_por_pagar`, `cuentas_por_cobrar`,
`comprobantes_ingreso`, `guias_transporte`, `tipos_egresos`, `tipos_marketing`,
`produccion_encabezados`, `produccion_reportes`, `costos_produccion`, `devoluciones_venta`,
`ordenes_venta` (ambos), `notas_credito_venta` (ambos)

---

### Tipo 2 — Navegación directa a URL de archivo (page.route)

El botón navega la página actual a la URL del reporte. Playwright queda esperando que esa
"navegación" termine, pero nunca termina porque es una descarga. **Síntoma:**

```
- click action done
- waiting for scheduled navigations to finish   ← se cuelga aquí, timeout 30s
```

**Solución:** usar `page.route()` para abortar la navegación, capturar la URL con
`page.waitForRequest()`, y descargar directamente con `http.get` autenticado.

```js
await page.route('**/reporte_conceptos**', route => route.abort());
const [req] = await Promise.all([
  page.waitForRequest(r => r.url().includes('reporte_conceptos'), { timeout: 15000 }),
  page.locator('text=Reporte de conceptos').click({ noWaitAfter: true }),
]);
await page.unroute('**/reporte_conceptos**');

const reportUrl    = req.url();
const cookies      = await context.cookies();
const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
await downloadFile(reportUrl, cookieHeader, fileDetalle);
```

**Scripts:** `facturas_venta` (detalle)

> **Nota:** `noWaitAfter: true` es necesario para que el click no quede esperando
> la navegación que acabamos de abortar con `page.route()`.

---

### Tipo 3 — Modal con checkboxes + window.open

El "Reporte de conceptos" abre un **modal con checklist** de campos. Al hacer submit,
Effi llama `window.open(url)` internamente. La URL capturada ES el archivo — descarga
inmediata, no asíncrona.

**Síntoma si se usa `waitForEvent('download')`:** timeout 30s — el evento download nunca llega.

```js
// Abrir modal
await page.click('text=Reportes y análisis de datos');
await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });
await page.click('text=Reporte de conceptos');
await page.waitForSelector('#modalExcelConceptos', { timeout: 10000 });
await page.waitForTimeout(500);

// Marcar todos los checkboxes
const total = await page.evaluate(() => {
  const checkboxes = document.querySelectorAll('#form_excel_conceptos input[type="checkbox"]');
  checkboxes.forEach(cb => { cb.checked = true; });
  return checkboxes.length;
});

// Interceptar window.open y descargar
await page.evaluate(() => {
  window._reportUrl = null;
  window.open = function(url) { window._reportUrl = url; return null; };
});
await page.locator('#btnValidarExcelConceptos').click();
await page.waitForFunction(() => window._reportUrl !== null, { timeout: 15000 });

const reportUrlRel = await page.evaluate(() => window._reportUrl);
const reportUrl    = new URL(reportUrlRel, 'https://effi.com.co/app/').href;
const cookies      = await context.cookies();
const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
await downloadFile(reportUrl, cookieHeader, fileDetalle);
```

**Scripts:** `remisiones_venta` (detalle)

> La URL generada incluye todos los parámetros de columnas (`c1=1&c2=1...c75=1&sucursal=1`),
> resultado directo de haber marcado los checkboxes en el modal.

---

### Tipo 4 — Modal con checkboxes + notificación asíncrona

**Solo `export_inventario.js`.** El archivo se genera en background y aparece en el panel
de notificaciones (`#notify-list`). No hay download event ni window.open.

```js
await page.locator('#btnValidarExcel').click();
await page.waitForSelector('#form_excel', { state: 'hidden', timeout: 15000 });
await page.waitForTimeout(12000); // esperar generación
await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
await page.waitForSelector('#notify-list', { timeout: 10000 });
const enlaceDescarga = await page.evaluate(() => {
  const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
  return links.length > 0 ? links[0].href : null;
});
```

> **CRÍTICO:** Este patrón es EXCLUSIVO de `inventario`. NO aplicar a otros módulos
> aunque tengan modal de checkboxes.

---

## Error clásico — Confundir tipos

**Bug de remisiones_venta (resuelto):** script basado en `inventario.js` esperaba
notificación asíncrona. El archivo ya estaba generado por `window.open` desde el primer
instante, pero el script esperaba 5 minutos en un polling inútil.

**Bug de facturas_venta (resuelto):** se usaba `waitForEvent('download')` pero el botón
navega directamente a la URL del archivo. Playwright esperaba que la navegación terminara
(nunca ocurre porque es una descarga), timeout a los 30 segundos.

**Diagnóstico rápido:** agregar listeners antes del click (ver sección REGLA FUNDAMENTAL)
y observar qué evento dispara el botón antes de decidir el mecanismo.

---

## Función downloadFile

Necesaria para Tipos 2 y 3. Requiere `https`/`http` y que `context` esté disponible
(desestructurar `{ browser, context, page }` desde `getPage()`).

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
const cookies      = await context.cookies();
const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
```

> `downloadFile` no tiene timeout — streams directamente al disco sin límite de tiempo.
> Ideal para archivos pesados (ej. facturas_venta detalle ~24 MB).

---

## Marcar checkboxes en modales

```js
const total = await page.evaluate(() => {
  const checkboxes = document.querySelectorAll('#id_form input[type="checkbox"]');
  checkboxes.forEach(cb => { cb.checked = true; });
  return checkboxes.length;
});
// IDs conocidos en Effi:
// inventario        → #form_excel           / botón: #btnValidarExcel
// remisiones_venta  → #form_excel_conceptos / botón: #btnValidarExcelConceptos
```

---

## Checklist al crear un script nuevo

- [ ] ¿La URL usa `?sucursal=1`? (preferir sobre `?vigente=1`)
- [ ] ¿Qué mecanismo usa el botón? (diagnosticar antes de codificar)
- [ ] ¿Se necesita `context` además de `page`? (necesario para Tipos 2 y 3)
- [ ] ¿El directorio de export existe? (`fs.mkdirSync(..., { recursive: true })`)
- [ ] ¿El script imprime `✅ Exportado: ruta (N filas)` al finalizar?
- [ ] ¿Hay `process.exit(1)` + screenshot en el catch?
- [ ] ¿Está en `export_all.sh` y en `.agent/CATALOGO_SCRIPTS.md`?
