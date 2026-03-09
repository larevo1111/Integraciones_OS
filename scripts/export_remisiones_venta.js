const { getPage }     = require('./session');
const { contarFilas, aplicarFiltroVigente } = require('./utils');
const path = require('path');
const fs = require('fs');
const https = require('https');
const http = require('http');

const EXPORT_DIR = '/exports/remisiones_venta';
const EFFI_URL   = 'https://effi.com.co/app/remision_v?vigente=1';
const fecha      = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  }

  const { browser, context, page } = await getPage();

  try {
    console.log('🔄 Navegando a Remisiones de venta...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // --- 0. Aplicar filtro Vigente via UI (para que Reporte de Conceptos lo herede) ---
    await aplicarFiltroVigente(page);

    // --- 1. Exportar a excel (encabezados) — descarga directa ---
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });
    const fileEncabezados = path.join(EXPORT_DIR, `remisiones_venta_encabezados_${fecha}.xlsx`);

    const [dl1] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);
    await dl1.saveAs(fileEncabezados);
    console.log(`✅ Exportado: ${fileEncabezados} (${contarFilas(fileEncabezados)} filas)`);

    // --- 2. Reporte de conceptos (detalle) — modal con checkboxes ---
    await page.click('text=Reportes y análisis de datos');
    await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });
    await page.click('text=Reporte de conceptos');

    console.log('⏳ Esperando modal...');
    await page.waitForSelector('#modalExcelConceptos', { timeout: 10000 });
    await page.waitForTimeout(500);

    const total = await page.evaluate(() => {
      const checkboxes = document.querySelectorAll('#form_excel_conceptos input[type="checkbox"]');
      checkboxes.forEach(cb => { cb.checked = true; });
      return checkboxes.length;
    });
    console.log(`✅ Marcados ${total} campos (todos)`);

    await page.locator('#btnValidarExcelConceptos').click();
    await page.waitForSelector('#modalExcelConceptos', { state: 'hidden', timeout: 15000 });

    console.log('⏳ Esperando generación del archivo (~12s)...');
    await page.waitForTimeout(12000);

    console.log('🔔 Abriendo notificaciones...');
    await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
    await page.waitForSelector('#notify-list', { timeout: 10000 });
    await page.waitForTimeout(500);

    const enlaceDescarga = await page.evaluate(() => {
      const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
      return links.length > 0 ? links[0].href : null;
    });

    if (!enlaceDescarga) {
      throw new Error('No se encontró enlace de descarga en notificaciones');
    }
    console.log('🔗 Enlace encontrado:', enlaceDescarga);

    const cookies = await context.cookies();
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
    const fileDetalle = path.join(EXPORT_DIR, `remisiones_venta_detalle_${fecha}.xlsx`);
    const urlObj = new URL(enlaceDescarga);
    const protocol = urlObj.protocol === 'https:' ? https : http;

    await new Promise((resolve, reject) => {
      const options = {
        hostname: urlObj.hostname,
        path: urlObj.pathname + urlObj.search,
        headers: { Cookie: cookieHeader },
      };
      protocol.get(options, (res) => {
        if (res.statusCode === 302 || res.statusCode === 301) {
          const redirectUrl = new URL(res.headers.location);
          protocol.get({
            hostname: redirectUrl.hostname,
            path: redirectUrl.pathname + redirectUrl.search,
            headers: { Cookie: cookieHeader },
          }, (res2) => {
            const file = fs.createWriteStream(fileDetalle);
            res2.pipe(file);
            file.on('finish', () => { file.close(); resolve(); });
          }).on('error', reject);
        } else {
          const file = fs.createWriteStream(fileDetalle);
          res.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }
      }).on('error', reject);
    });

    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_remisiones_venta_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
