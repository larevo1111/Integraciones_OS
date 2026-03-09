const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');
const fs   = require('fs');

const EXPORT_DIR = '/exports/produccion/encabezados_prod';
const EFFI_URL   = 'https://effi.com.co/app/orden_produccion';
const fecha      = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) fs.mkdirSync(EXPORT_DIR, { recursive: true });

  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Órdenes de producción (encabezados)...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });

    const filePath = path.join(EXPORT_DIR, `produccion_encabezados_${fecha}.xlsx`);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);

    await download.saveAs(filePath);
    console.log(`✅ Exportado: ${filePath} (${contarFilas(filePath)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/produccion/encabezados_prod/error_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
