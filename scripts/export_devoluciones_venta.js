const { getPage }     = require('./session');
const { contarFilas } = require('./utils');
const path = require('path');
const fs = require('fs');

const EXPORT_DIR = '/exports/devoluciones_venta';
const EFFI_URL   = 'https://effi.com.co/app/devolucion_v';
const fecha      = new Date().toISOString().slice(0, 10);

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  }

  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Devoluciones de venta...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // --- 1. Exportar a excel (encabezados) ---
    await page.waitForSelector('text=Exportar a excel', { timeout: 15000 });
    const fileEncabezados = path.join(EXPORT_DIR, `devoluciones_venta_encabezados_${fecha}.xlsx`);

    const [dl1] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Exportar a excel'),
    ]);
    await dl1.saveAs(fileEncabezados);
    console.log(`✅ Exportado: ${fileEncabezados} (${contarFilas(fileEncabezados)} filas)`);

    // --- 2. Reporte de conceptos (detalle) ---
    await page.click('text=Reportes y análisis de datos');
    await page.waitForSelector('text=Reporte de conceptos', { timeout: 15000 });

    const fileDetalle = path.join(EXPORT_DIR, `devoluciones_venta_detalle_${fecha}.xlsx`);

    const [dl2] = await Promise.all([
      page.waitForEvent('download'),
      page.click('text=Reporte de conceptos'),
    ]);
    await dl2.saveAs(fileDetalle);
    console.log(`✅ Exportado: ${fileDetalle} (${contarFilas(fileDetalle)} filas)`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `/exports/error_devoluciones_venta_${Date.now()}.png` });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
