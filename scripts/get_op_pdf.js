/**
 * get_op_pdf.js — Descarga el PDF de una OP de Effi
 * Uso: node get_op_pdf.js <id_op> <ruta_salida>
 * Ejemplo: node get_op_pdf.js 2059 /tmp/op_2059.pdf
 */
const { getPage } = require('./session');

const idOp      = process.argv[2];
const rutaSalida = process.argv[3];

if (!idOp || !rutaSalida) {
  console.error('Uso: node get_op_pdf.js <id_op> <ruta_salida>');
  process.exit(1);
}

(async () => {
  const { browser, page } = await getPage();

  try {
    // Ir al módulo de órdenes de producción
    await page.goto('https://effi.com.co/app/orden_produccion');
    await page.waitForLoadState('networkidle');

    // Abrir filtros de búsqueda
    const btnFiltros = page.locator('text=Filtros de búsqueda');
    if (await btnFiltros.isVisible()) {
      await btnFiltros.click();
      await page.waitForTimeout(400);
    }

    // Llenar el campo ID de la OP
    const inputId = page.locator('input[placeholder="ID orden de producción"]');
    await inputId.fill(String(idOp));

    // Aplicar filtros
    await page.locator('text=Aplicar filtros').click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(600);

    // Hacer clic en el botón de opciones (▼) de la primera fila
    const btnOpciones = page.locator('button:has-text("Opciones"), .btn-opciones, [title="Opciones"]').first();
    if (!await btnOpciones.isVisible()) {
      // Intentar con el botón de flecha de la primera fila
      await page.locator('table tbody tr:first-child .btn-group button').first().click();
    } else {
      await btnOpciones.click();
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
    await page.screenshot({ path: `/tmp/error_op_pdf_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
