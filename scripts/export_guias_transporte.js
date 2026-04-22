const { localDate } = require('./lib/timezone')
const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');
const fs   = require('fs');
const https = require('https');
const http  = require('http');

const EXPORT_DIR = '/exports/guias_transporte';
const EFFI_URL   = 'https://effi.com.co/app/guia_transporte?sucursal=1';
const fecha      = localDate();

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  }

  const { browser, context, page } = await getPage();

  try {
    console.log('🔄 Navegando a Guías de transporte...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });

    // Verificar si hay registros antes de intentar exportar
    const sinRegistros = await page.evaluate(() => {
      const texto = document.body.innerText;
      return texto.includes('0 guías de transporte encontradas') ||
             texto.includes('No hay registros para exportar');
    });

    if (sinRegistros) {
      console.log('⚠️  Sin registros en Guías de transporte — omitido (0 filas)');
      await browser.close();
      process.exit(0);
    }

    await page.click('text=Exportar a excel');

    console.log('⏳ Esperando modal...');
    await page.waitForSelector('#modalExcel', { timeout: 10000 });
    await page.waitForTimeout(500);

    const total = await page.evaluate(() => {
      const checkboxes = document.querySelectorAll('#form_excel input[type="checkbox"]');
      checkboxes.forEach(cb => { cb.checked = true; });
      return checkboxes.length;
    });
    console.log(`✅ Marcados ${total} campos (todos)`);

    await page.locator('#btnValidarExcel').click();
    await page.waitForSelector('#modalExcel', { state: 'hidden', timeout: 15000 });

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
    const filePath = path.join(EXPORT_DIR, `guias_transporte_${fecha}.xlsx`);
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
            const file = fs.createWriteStream(filePath);
            res2.pipe(file);
            file.on('finish', () => { file.close(); resolve(); });
          }).on('error', reject);
        } else {
          const file = fs.createWriteStream(filePath);
          res.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }
      }).on('error', reject);
    });

    console.log(`✅ Exportado: ${filePath} (${contarFilas(filePath)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_guias_transporte_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
