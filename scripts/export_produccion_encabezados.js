const { getPage }     = require('./session');
const { contarFilas } = require('./utils');

(async () => {
  const { browser, page } = await getPage();

  try {
    await page.goto('https://effi.com.co/app/orden_produccion');
    await page.waitForSelector('text=Exportar a excel');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel')
    ]);

    const filePath = `/exports/produccion/encabezados_prod/encabezados_${new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' })}.xlsx`;
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
