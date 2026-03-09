const { getPage } = require('./session');

(async () => {
  const { browser, page } = await getPage();

  try {
    await page.goto('https://effi.com.co/app/mantenimiento_tablas/t_egreso_empresa');
    await page.waitForSelector('text=Exportar a excel');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel')
    ]);

    const filePath = `/exports/tipos_egresos/tipos_egresos_${new Date().toISOString().slice(0,10)}.xlsx`;
    await download.saveAs(filePath);
    console.log(`✅ Exportado: ${filePath}`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_tipos_egresos_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
