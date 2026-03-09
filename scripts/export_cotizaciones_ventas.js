const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');
const fs = require('fs');

const EXPORT_DIR = '/exports/cotizaciones_ventas';
const EFFI_URL   = 'https://effi.com.co/app/cotizacion?vigente=1';
const fecha      = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  }

  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Cotizaciones...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // --- 1. Exportar a excel (encabezados) ---
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });
    const fileEncabezados = path.join(EXPORT_DIR, `cotizaciones_ventas_encabezados_${fecha}.xlsx`);

    const [dl1] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);
    await dl1.saveAs(fileEncabezados);
    console.log(`✅ Exportado: ${fileEncabezados} (${contarFilas(fileEncabezados)} filas)`);

    // --- 2. Reporte de conceptos (detalle) ---
    await page.click('text=Reportes y análisis de datos');
    await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });

    const fileDetalle = path.join(EXPORT_DIR, `cotizaciones_ventas_detalle_${fecha}.xlsx`);

    const [dl2] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Reporte de conceptos'),
    ]);
    await dl2.saveAs(fileDetalle);
    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_cotizaciones_ventas_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
