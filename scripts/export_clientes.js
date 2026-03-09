const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');

(async () => {
  const { browser, page } = await getPage();

  try {
    await page.goto('https://effi.com.co/app/tercero/cliente');
    await page.waitForSelector('text=Exportar a excel');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel')
    ]);

    const filePath = `/exports/clientes/clientes_${new Date().toISOString().slice(0,10)}.xlsx`;
    await download.saveAs(filePath);
    console.log(`✅ Exportado: ${filePath} (${contarFilas(filePath)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_clientes_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
