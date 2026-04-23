/**
 * cambiar_estado_orden_produccion.js
 *
 * Cambia el estado de una Orden de Producción en Effi.
 *
 * Uso:
 *   node scripts/cambiar_estado_orden_produccion.js <id_orden> <estado> [observacion]
 *
 * Estados válidos: "Generada" | "Procesada" | "Validado"
 *
 * Ejemplo:
 *   node scripts/cambiar_estado_orden_produccion.js 2182 "Procesada" "Reportó: Jennifer Cano"
 */

const { getPage } = require('./session');

const EFFI_URL = 'https://effi.com.co/app/orden_produccion';
const ESTADOS_VALIDOS = ['Generada', 'Procesada', 'Validado'];

const idOrden    = process.argv[2];
const estado     = process.argv[3];
const observacion = process.argv[4] || `SYS - Cambio estado a ${estado}`;

if (!idOrden || !estado) {
  console.error('Uso: node cambiar_estado_orden_produccion.js <id_orden> <estado> [observacion]');
  console.error(`Estados válidos: ${ESTADOS_VALIDOS.join(', ')}`);
  process.exit(1);
}

if (!ESTADOS_VALIDOS.includes(estado)) {
  console.error(`❌ Estado inválido: "${estado}". Usar: ${ESTADOS_VALIDOS.join(', ')}`);
  process.exit(1);
}

console.log(`🔄 Cambiando estado de OP ${idOrden} → "${estado}"`);
console.log(`📝 Observación: ${observacion}`);

(async () => {
  const { browser, page } = await getPage();

  try {
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    if (page.url().includes('/ingreso')) {
      console.error('❌ Sesión expirada. Regenerar con session.js');
      process.exit(1);
    }

    // Buscar la OP por ID (filtros de búsqueda)
    console.log('🔄 Abriendo filtros...');
    await page.locator('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda")').first().click();
    await page.waitForTimeout(800);

    const filtroId = page.locator('input[name="filtro_id_orden"], input[placeholder*="ID"]').first();
    if (await filtroId.count() > 0) {
      await filtroId.fill(String(idOrden));
      await page.locator('button:has-text("Buscar"), button:has-text("Aplicar"), button:has-text("Filtrar")').first().click();
      await page.waitForTimeout(2000);
    } else {
      await page.goto(`${EFFI_URL}?id_orden=${idOrden}`, { waitUntil: 'networkidle' });
    }

    // Fila de la OP
    console.log(`🔄 Buscando fila de OP ${idOrden}...`);
    const fila = page.locator(`tr:has-text("ID: ${idOrden}"), tr:has-text("ID_EFFI: ${idOrden}")`).first();
    if ((await fila.count()) === 0) {
      console.error(`❌ OP ${idOrden} no encontrada en la lista`);
      await page.screenshot({ path: `/exports/cambiar_estado_nofound_${Date.now()}.png` });
      process.exit(1);
    }

    // Menú de acciones (dropdown de la fila)
    await fila.locator('button.dropdown-toggle, button:has(.fa-ellipsis-v), button:has(.caret)').first().click();
    await page.waitForTimeout(500);

    // Click "Cambiar estado" del dropdown (es <a>, no el <button> del modal)
    await page.locator('.dropdown-menu a:has-text("Cambiar estado"), ul.dropdown-menu a:has-text("Cambiar estado"), li > a:has-text("Cambiar estado")').first().click();
    await page.waitForTimeout(1500);

    // Modal: seleccionar nuevo estado (dropdown Chosen)
    console.log(`🔄 Seleccionando estado "${estado}" en modal...`);
    const modal = page.locator('.modal.in, .modal.show').last();

    // Chosen envuelve el select nativo (oculto). Interactuar con la UI Chosen.
    await modal.locator('.chosen-container, .chosen-single').first().click();
    await page.waitForTimeout(500);
    // Buscar la opción exacta (li con texto igual)
    const opcion = page.locator(`.chosen-results li.active-result:text-is("${estado}")`).first();
    if (await opcion.count() === 0) {
      // Fallback con :has-text si el selector :text-is no matchea
      await page.locator(`.chosen-results li.active-result:has-text("${estado}")`).first().click();
    } else {
      await opcion.click();
    }
    await page.waitForTimeout(400);

    // Observación
    const textarea = modal.locator('textarea').first();
    if (await textarea.count() > 0) {
      await textarea.fill(observacion);
      await page.waitForTimeout(300);
    }

    // Click "Cambiar estado"
    await modal.locator('button:has-text("Cambiar estado")').last().click();
    await page.waitForTimeout(4000);

    const screenshotPath = `/exports/op_estado_${idOrden}_${estado}_${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`✅ OP ${idOrden} → estado "${estado}" (screenshot: ${screenshotPath})`);

  } catch (err) {
    console.error(`❌ ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/cambiar_estado_error_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
