/**
 * anular_orden_produccion.js
 *
 * Anula una Orden de Producción en Effi por su ID.
 *
 * Uso:
 *   node scripts/anular_orden_produccion.js <id_orden> [observacion]
 *
 * Ejemplo:
 *   node scripts/anular_orden_produccion.js 2143 "OP creada con cantidad errónea"
 */

const { getPage } = require('./session');

const EFFI_URL = 'https://effi.com.co/app/orden_produccion';

const idOrden = process.argv[2];
const observacion = process.argv[3] || `SYS GENERATED - Anulación OP ${idOrden}`;

if (!idOrden) {
  console.error('Uso: node anular_orden_produccion.js <id_orden> [observacion]');
  process.exit(1);
}

console.log(`🗑️  Anulando OP ${idOrden}`);
console.log(`📝 Observación: ${observacion}`);

(async () => {
  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Órdenes de producción...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    if (page.url().includes('/ingreso')) {
      console.error('❌ Sesión expirada. Regenerar con session.js');
      process.exit(1);
    }

    // Buscar la OP por ID. Effi tiene un filtro de búsqueda — usar el filtro de código.
    console.log('🔄 Abriendo filtros...');
    await page.locator('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda")').first().click();
    await page.waitForTimeout(1000);

    // Llenar filtro ID_orden o código
    const filtroId = page.locator('input[name="filtro_id_orden"], input[placeholder*="ID"]').first();
    if (await filtroId.count() > 0) {
      await filtroId.fill(String(idOrden));
      await page.locator('button:has-text("Buscar"), button:has-text("Aplicar"), button:has-text("Filtrar")').first().click();
      await page.waitForTimeout(2000);
    } else {
      // Fallback: recargar con filtro en URL
      await page.goto(`${EFFI_URL}?id_orden=${idOrden}`, { waitUntil: 'networkidle' });
    }

    // Encontrar la fila de la OP y hacer click en el menú de acciones
    console.log(`🔄 Buscando fila de OP ${idOrden}...`);
    const fila = page.locator(`tr:has-text("ID: ${idOrden}"), tr:has-text("ID_EFFI: ${idOrden}")`).first();
    const filaCount = await fila.count();
    if (filaCount === 0) {
      console.error(`❌ OP ${idOrden} no encontrada en la lista`);
      await page.screenshot({ path: `/exports/anular_op_nofound_${Date.now()}.png` });
      process.exit(1);
    }

    // Click en el botón de acciones de esa fila (dropdown con 3 puntos o flecha)
    await fila.locator('button.dropdown-toggle, button:has(.fa-ellipsis-v), button:has(.caret)').first().click();
    await page.waitForTimeout(500);

    // Click en "Anular"
    await page.locator('a:has-text("Anular"), button:has-text("Anular")').first().click();
    await page.waitForTimeout(1500);

    // Confirmar con observación
    console.log('🔄 Llenando observación de anulación...');
    const textarea = page.locator('.modal.in textarea, .modal.show textarea').first();
    if (await textarea.count() > 0) {
      await textarea.fill(observacion);
      await page.waitForTimeout(300);
    }

    // Click botón confirmar anulación
    await page.locator('.modal.in button:has-text("Anular"), .modal.show button:has-text("Anular"), .modal.in button:has-text("Confirmar"), .modal.show button:has-text("Confirmar")').last().click();
    await page.waitForTimeout(4000);

    const screenshotPath = `/exports/op_anulada_${idOrden}_${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`✅ OP ${idOrden} anulada (screenshot: ${screenshotPath})`);

  } catch (err) {
    console.error(`❌ ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/anular_op_error_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
