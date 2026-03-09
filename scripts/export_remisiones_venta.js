const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path  = require('path');
const fs    = require('fs');
const https = require('https');
const http  = require('http');

const EXPORT_DIR = '/exports/remisiones_venta';
const EFFI_URL   = 'https://effi.com.co/app/remision_v?sucursal=1';
const fecha      = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

function httpGet(url, cookieHeader) {
  return new Promise((resolve, reject) => {
    const urlObj   = new URL(url);
    const protocol = urlObj.protocol === 'https:' ? https : http;
    protocol.get({ hostname: urlObj.hostname, path: urlObj.pathname + urlObj.search,
                   headers: { Cookie: cookieHeader } }, resolve).on('error', reject);
  });
}

function downloadFile(url, cookieHeader, destPath) {
  return new Promise((resolve, reject) => {
    const urlObj   = new URL(url);
    const protocol = urlObj.protocol === 'https:' ? https : http;
    const opts     = { hostname: urlObj.hostname, path: urlObj.pathname + urlObj.search,
                       headers: { Cookie: cookieHeader } };
    protocol.get(opts, (res) => {
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

    // Capturar enlace actual en notificaciones (para detectar el nuevo)
    const cookies      = await context.cookies();
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
    await page.waitForSelector('#notify-list', { timeout: 10000 });
    await page.waitForTimeout(300);
    const enlaceAnterior = await page.evaluate(() => {
      const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
      return links.length > 0 ? links[0].href : null;
    });
    console.log('🔗 Enlace anterior:', enlaceAnterior ? enlaceAnterior.split('/').pop() : '(ninguno)');

    // Cerrar dropdown y volver al modal (ya fue cerrado al hacer click fuera)
    // Reabrir reporte de conceptos si es necesario — pero el modal YA está abierto
    // Solo interceptamos window.open y presionamos exportar
    await page.evaluate(() => {
      window._reportUrl = null;
      window.open = function(url) { window._reportUrl = url; };
    });

    await page.locator('#btnValidarExcelConceptos').click();
    await page.waitForSelector('#modalExcelConceptos', { state: 'hidden', timeout: 15000 });

    const reportUrlRelativo = await page.evaluate(() => window._reportUrl);
    if (!reportUrlRelativo) throw new Error('No se capturó URL de reporte (window.open no fue llamado)');

    const reportUrlCompleto = new URL(reportUrlRelativo, 'https://effi.com.co/app/').href;
    console.log('🔗 URL del reporte:', reportUrlCompleto.substring(0, 200));

    // Disparar generación del reporte (GET autenticado)
    console.log('🚀 Disparando generación del reporte...');
    const respGen = await httpGet(reportUrlCompleto, cookieHeader);
    respGen.resume(); // consumir respuesta para liberar socket
    console.log(`   HTTP ${respGen.statusCode}`);

    // Esperar hasta que aparezca un nuevo enlace en notificaciones (máx 5 min)
    console.log('⏳ Esperando nuevo archivo en notificaciones (máx 5 min)...');
    let enlaceNuevo = null;
    const inicio    = Date.now();
    while (Date.now() - inicio < 300000) {
      await page.reload({ waitUntil: 'networkidle', timeout: 30000 });
      await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
      await page.waitForSelector('#notify-list', { timeout: 10000 });
      await page.waitForTimeout(300);

      const candidato = await page.evaluate(() => {
        const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
        return links.length > 0 ? links[0].href : null;
      });

      if (candidato && candidato !== enlaceAnterior) {
        enlaceNuevo = candidato;
        break;
      }
      console.log(`   ...sin cambio todavía (${Math.round((Date.now() - inicio) / 1000)}s)`);
      await page.waitForTimeout(5000);
    }

    if (!enlaceNuevo) throw new Error('Timeout: no apareció nuevo enlace en notificaciones tras 5 min');
    console.log('🔗 Nuevo enlace:', enlaceNuevo);

    const fileDetalle = path.join(EXPORT_DIR, `remisiones_venta_detalle_${fecha}.xlsx`);
    await downloadFile(enlaceNuevo, cookieHeader, fileDetalle);
    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_remisiones_venta_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
