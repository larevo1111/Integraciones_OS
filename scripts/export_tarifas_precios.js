const { localDate } = require('./lib/timezone')
const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const fs = require('fs');

(async () => {
  const { browser, page } = await getPage();

  try {
    const dir = '/exports/tarifas_precios';
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    await page.goto('https://effi.com.co/app/mantenimiento_tablas/tarifa_precio_empresa');
    await page.waitForSelector('text=Exportar a excel');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel')
    ]);

    const filePath = `${dir}/tarifas_precios_${localDate()}.xlsx`;
    await download.saveAs(filePath);
    console.log(`✅ Exportado: ${filePath} (${contarFilas(filePath)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_tarifas_precios_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
