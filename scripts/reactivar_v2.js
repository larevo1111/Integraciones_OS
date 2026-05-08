/**
 * Reactiva artículos anulados navegando a la URL del modal directo.
 */
const { getPage } = require('./session');
const cods = process.argv.slice(2);

(async () => {
  const { browser, page } = await getPage();
  page.setDefaultTimeout(60000);

  // Aumentar timeout
  for (const cod of cods) {
    console.log(`\n→ COD ${cod}`);
    try {
      // Navegar a /app/articulo y configurar filtro vigencia=Anulado via JS
      await page.goto('https://effi.com.co/app/articulo', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(2000);

      // Abrir filtros
      const filtroBtn = page.locator('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda"), .filtros-btn');
      if (await filtroBtn.count()) await filtroBtn.first().click();
      await page.waitForTimeout(1000);

      // Inspeccionar selectores disponibles
      const inspect = await page.evaluate(() => {
        const allSelects = [...document.querySelectorAll('select')].map(s => ({
          id: s.id, name: s.name, options: [...s.options].map(o => o.value).slice(0, 5)
        }));
        const allInputs = [...document.querySelectorAll('input[type=text], input[type=number]')].map(i => ({
          id: i.id, name: i.name, placeholder: i.placeholder
        })).slice(0, 10);
        return { selects: allSelects.slice(0, 10), inputs: allInputs };
      });
      if (cod === cods[0]) {
        console.log('SELECTS:', JSON.stringify(inspect.selects, null, 2));
        console.log('INPUTS:', JSON.stringify(inspect.inputs, null, 2));
      }

      // Configurar filtros: id_articulo + vigencia=Anulado
      await page.evaluate((codArt) => {
        // Vigencia
        const selVig = document.querySelector('select[name="filtro_vigencia"], #filtro_vigencia, #filtro_vigencia_LIST');
        if (selVig) {
          selVig.value = 'Anulado';
          if (window.$) $(selVig).trigger('change').trigger('chosen:updated');
        }
        // ID artículo
        const inpId = document.querySelector('input[name="filtro_id_articulo"], input[name="filtro_id"], input[name="filtro_codigo"]');
        if (inpId) inpId.value = codArt;
      }, cod);

      // Buscar
      await page.locator('button:has-text("Buscar"), button:has-text("Aplicar"), button:has-text("Filtrar"), #btn_filtrar').first().click().catch(()=>{});
      await page.waitForTimeout(3000);

      // Buscar botón reactivar
      const reactivar = page.locator(`tr[data-id="${cod}"] a:has-text("Reactivar"), tr[data-id="${cod}"] button:has-text("Reactivar"), a.reactivar[data-id="${cod}"]`);
      const cnt = await reactivar.count();
      console.log(`  Reactivar buttons encontrados: ${cnt}`);
      if (cnt > 0) {
        await reactivar.first().click();
        await page.waitForTimeout(1500);
        // Confirmar
        const confirmar = page.locator('button:has-text("Aceptar"), button:has-text("Sí"), button:has-text("Confirmar")');
        if (await confirmar.count()) await confirmar.first().click();
        await page.waitForTimeout(2000);
        console.log(`  ✅ ${cod} reactivado`);
      } else {
        // Intento via menu dropdown
        const menu = page.locator(`tr[data-id="${cod}"] .dropdown-toggle, tr[data-id="${cod}"] [data-toggle="dropdown"]`);
        if (await menu.count()) {
          await menu.first().click();
          await page.waitForTimeout(500);
          await page.locator('a:has-text("Reactivar")').first().click({ timeout: 5000 });
          await page.waitForTimeout(1500);
          console.log(`  ✅ ${cod} reactivado (via dropdown)`);
        } else {
          console.log(`  ⚠ No se encontró botón Reactivar para ${cod}`);
        }
      }
    } catch (e) {
      console.log(`  ❌ ${cod} ERROR: ${e.message.split('\n')[0].substring(0, 100)}`);
    }
  }
  await browser.close();
})();
