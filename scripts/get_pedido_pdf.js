/**
 * get_pedido_pdf.js — Descarga el PDF de una Cotización (Pedido) de Effi
 * Uso: node get_pedido_pdf.js <id_cotizacion> <ruta_salida>
 */
const { getPage } = require('./session');

const idPed      = process.argv[2];
const rutaSalida = process.argv[3];

if (!idPed || !rutaSalida) {
  console.error('Uso: node get_pedido_pdf.js <id_cotizacion> <ruta_salida>');
  process.exit(1);
}

(async () => {
  const { browser, page } = await getPage();

  try {
    // Navegar directamente con el ID como filtro (igual que la URL del screenshot)
    await page.goto(`https://effi.com.co/app/cotizacion?id=${idPed}&id=${idPed}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);

    // Hacer clic en el botón de opciones (▼) de la primera fila
    const btnOpciones = page.locator('button:has-text("Opciones"), .btn-opciones, [title="Opciones"]').first();
    if (await btnOpciones.isVisible()) {
      await btnOpciones.click();
    } else {
      await page.locator('table tbody tr:first-child .btn-group button').first().click();
    }
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
    await page.screenshot({ path: `/tmp/error_pedido_pdf_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
