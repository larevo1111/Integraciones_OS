/**
 * get_remision_pdf.js — Descarga el PDF de una Remisión de venta de Effi
 * Uso: node get_remision_pdf.js <id_remision> <ruta_salida>
 */
const { getPage } = require('./session');

const idRem      = process.argv[2];
const rutaSalida = process.argv[3];

if (!idRem || !rutaSalida) {
  console.error('Uso: node get_remision_pdf.js <id_remision> <ruta_salida>');
  process.exit(1);
}

(async () => {
  const { browser, page } = await getPage();

  try {
    await page.goto('https://effi.com.co/app/remision_v');
    await page.waitForLoadState('networkidle');

    // Abrir filtros de búsqueda
    const btnFiltros = page.locator('text=Filtros de búsqueda');
    if (await btnFiltros.isVisible()) {
      await btnFiltros.click();
      await page.waitForTimeout(400);
    }

    // Llenar el campo ID remisión
    const inputId = page.locator('input[placeholder="ID remisión"]');
    await inputId.fill(String(idRem));

    // Aplicar filtros
    await page.locator('text=Aplicar filtros').click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(600);

    // Abrir menú opciones de la primera fila
    await page.locator('table tbody tr:first-child .btn-group button').first().click();
    await page.waitForTimeout(300);

    // Hacer clic en "Ver PDF"
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('text=Ver PDF').first().click()
    ]);

    await download.saveAs(rutaSalida);
    console.log(`OK:${rutaSalida}`);

  } catch (err) {
    console.error('ERROR:' + err.message);
    await page.screenshot({ path: `/tmp/error_remision_pdf_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
