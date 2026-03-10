const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const fs = require('fs');

(async () => {
  const { browser, page } = await getPage();

  try {
    const dir = '/exports/empleados';
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    await page.goto('https://effi.com.co/app/tercero/empleado');
    await page.waitForSelector('text=Exportar a excel');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel')
    ]);

    const filePath = `${dir}/empleados_${new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' })}.xlsx`;
    await download.saveAs(filePath);
    console.log(`✅ Exportado: ${filePath} (${contarFilas(filePath)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_empleados_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
