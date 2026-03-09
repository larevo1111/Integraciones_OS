const { getPage }     = require('./session');
const { contarFilas } = require('./utils');

const reportes = [
  { texto: 'Reporte de materiales',               carpeta: 'materiales' },
  { texto: 'Reporte de artículos producidos',      carpeta: 'articulos_producidos' },
  { texto: 'Reporte de otros costos de producción', carpeta: 'otros_costos' },
  { texto: 'Reporte de cambios de estado',          carpeta: 'cambios_estado' },
];

(async () => {
  const fecha = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

  for (const reporte of reportes) {
    const { browser, page } = await getPage();
    try {
      await page.goto('https://effi.com.co/app/orden_produccion');
      await page.click('text=Reportes y análisis de datos');
      await page.waitForSelector(`text=${reporte.texto}`);

      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.click(`text=${reporte.texto}`)
      ]);

      const filePath = `/exports/produccion/${reporte.carpeta}/${reporte.carpeta}_${fecha}.xlsx`;
      await download.saveAs(filePath);
      console.log(`✅ ${reporte.texto}: ${filePath} (${contarFilas(filePath)} filas)`);

    } catch (err) {
      console.error(`❌ Error en ${reporte.texto}:`, err.message);
      await page.screenshot({ path: `/exports/produccion/${reporte.carpeta}/error_${Date.now()}.png` });
    } finally {
      await browser.close();
    }
  }
})();
