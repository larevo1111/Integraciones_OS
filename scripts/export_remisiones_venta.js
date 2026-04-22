const { localDate } = require('./lib/timezone')
const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path  = require('path');
const fs    = require('fs');
const https = require('https');
const http  = require('http');

const EXPORT_DIR = '/exports/remisiones_venta';
const EFFI_URL   = 'https://effi.com.co/app/remision_v?sucursal=1';
const fecha      = localDate();

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

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) fs.mkdirSync(EXPORT_DIR, { recursive: true });

  const { browser, context, page } = await getPage();

  try {
    console.log('🔄 Navegando a Remisiones de venta...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // --- 1. Encabezados ---
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });
    const fileEncabezados = path.join(EXPORT_DIR, `remisiones_venta_encabezados_${fecha}.xlsx`);
    const [dl1] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);
    await dl1.saveAs(fileEncabezados);
    console.log(`✅ Exportado: ${fileEncabezados} (${contarFilas(fileEncabezados)} filas)`);

    // --- 2. Detalle — Reporte de conceptos ---
    await page.click('text=Reportes y análisis de datos');
    await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });
    await page.click('text=Reporte de conceptos');

    console.log('⏳ Esperando modal...');
    await page.waitForSelector('#modalExcelConceptos', { timeout: 10000 });
    await page.waitForTimeout(500);

    // Marcar todos los checkboxes
    const total = await page.evaluate(() => {
      const checkboxes = document.querySelectorAll('#form_excel_conceptos input[type="checkbox"]');
      checkboxes.forEach(cb => { cb.checked = true; });
      return checkboxes.length;
    });
    console.log(`✅ Marcados ${total} campos (todos)`);

    // Interceptar window.open para capturar la URL del archivo
    await page.evaluate(() => {
      window._reportUrl = null;
      window.open = function(url) { window._reportUrl = url; return null; };
    });

    await page.locator('#btnValidarExcelConceptos').click();
    await page.waitForFunction(() => window._reportUrl !== null, { timeout: 15000 });

    const reportUrlRel = await page.evaluate(() => window._reportUrl);
    const reportUrl    = new URL(reportUrlRel, 'https://effi.com.co/app/').href;
    console.log('🔗 URL capturada:', reportUrl.split('/').pop());

    const cookies      = await context.cookies();
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    const fileDetalle = path.join(EXPORT_DIR, `remisiones_venta_detalle_${fecha}.xlsx`);
    await downloadFile(reportUrl, cookieHeader, fileDetalle);
    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_remisiones_venta_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
