const { localDate } = require('./lib/timezone')
const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path  = require('path');
const fs    = require('fs');
const https = require('https');
const http  = require('http');

const EXPORT_DIR = '/exports/facturas_venta';
const EFFI_URL   = 'https://effi.com.co/app/factura_v?vigente=1';
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
    console.log('🔄 Navegando a Facturas de venta...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // --- 1. Encabezados ---
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });
    const fileEncabezados = path.join(EXPORT_DIR, `facturas_venta_encabezados_${fecha}.xlsx`);
    const [dl1] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);
    await dl1.saveAs(fileEncabezados);
    console.log(`✅ Exportado: ${fileEncabezados} (${contarFilas(fileEncabezados)} filas)`);

    // --- 2. Detalle — Reporte de conceptos ---
    // El botón navega directamente a la URL del reporte (no window.open ni download event).
    // Interceptamos la request para capturar la URL exacta y abortar la navegación,
    // luego descargamos directamente con cookies.
    await page.click('text=Reportes y análisis de datos');
    await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });

    await page.route('**/reporte_conceptos**', route => route.abort());
    const [req] = await Promise.all([
      page.waitForRequest(r => r.url().includes('reporte_conceptos'), { timeout: 15000 }),
      page.locator('text=Reporte de conceptos').click({ noWaitAfter: true }),
    ]);
    await page.unroute('**/reporte_conceptos**');

    const reportUrl = req.url();
    console.log('🔗 URL capturada:', reportUrl.split('/').slice(-2).join('/'));

    const cookies      = await context.cookies();
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    const fileDetalle = path.join(EXPORT_DIR, `facturas_venta_detalle_${fecha}.xlsx`);
    await downloadFile(reportUrl, cookieHeader, fileDetalle);
    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_facturas_venta_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
