/**
 * Reactiva artículos anulados en Effi vía Playwright.
 * Uso: node reactivar_articulos.js cod1 cod2 ...
 */
const { getPage } = require('./session');

const cods = process.argv.slice(2);
if (!cods.length) { console.error('Uso: node reactivar_articulos.js cod1 cod2 ...'); process.exit(1); }

(async () => {
  const { browser, page } = await getPage();

  for (const cod of cods) {
    console.log(`\n→ COD ${cod}`);
    try {
      await page.goto(`https://effi.com.co/app/articulo`, { waitUntil: 'networkidle', timeout: 30000 });

      // Filtros: ver artículos anulados
      await page.locator('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda")').first().click();
      await page.waitForTimeout(500);

      // Cambiar filtro vigencia a "Anulado"
      const ok = await page.evaluate(() => {
        const sel = document.querySelector('#filtro_vigencia_LIST, select[name="filtro_vigencia"]');
        if (sel) {
          sel.value = 'Anulado';
          if (window.$) $(sel).trigger('change').trigger('chosen:updated');
          return true;
        }
        return false;
      });

      // Filtrar por id
      await page.evaluate((id) => {
        const inp = document.querySelector('#filtro_id_articulo, input[name="filtro_id_articulo"]');
        if (inp) inp.value = id;
      }, cod);

      await page.locator('button:has-text("Buscar"), button:has-text("Aplicar"), button:has-text("Filtrar")').first().click();
      await page.waitForTimeout(2000);

      // Buscar fila por data-id
      const fila = page.locator(`tr[data-id="${cod}"]`).first();
      if (await fila.count() === 0) {
        console.log(`  ⚠ Cod ${cod} no encontrado en anulados`);
        continue;
      }

      // Click en menú acciones / botón "Reactivar"
      await fila.locator('a:has-text("Reactivar"), button:has-text("Reactivar"), .acciones a, .acciones button').first().click({ timeout: 5000 }).catch(async () => {
        // Si no hay botón directo, abrir menú de 3 puntos
        await fila.locator('.dropdown-toggle, [data-toggle="dropdown"]').first().click();
        await page.waitForTimeout(500);
        await page.locator('a:has-text("Reactivar")').first().click();
      });

      await page.waitForTimeout(800);

      // Confirmar diálogo si aparece
      const confirmar = page.locator('button:has-text("Aceptar"), button:has-text("Confirmar"), button:has-text("Sí")').first();
      if (await confirmar.count() > 0) await confirmar.click();
      await page.waitForTimeout(1500);
      console.log(`  ✅ ${cod} reactivado`);
    } catch (e) {
      console.log(`  ❌ ${cod} ERROR: ${e.message.split('\n')[0]}`);
    }
  }
  await browser.close();
})();
