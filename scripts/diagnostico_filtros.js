/**
 * diagnostico_filtros.js
 * Inspecciona el panel de filtros de fecha en un módulo de Effi.
 * Toma screenshots y extrae el HTML del panel para identificar selectores.
 * Uso: node scripts/diagnostico_filtros.js
 */

const { getPage } = require('./session');
const fs = require('fs');

const URL_MODULO = 'https://effi.com.co/app/factura_v';
const OUT_DIR    = '/exports/diagnostico';

(async () => {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Facturas de venta...');
    await page.goto(URL_MODULO, { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: `${OUT_DIR}/1_pagina_inicial.png`, fullPage: true });
    console.log('📸 Screenshot 1: página inicial guardado');

    // Extraer texto del aviso de filtro de fecha si existe
    const avisoFiltro = await page.evaluate(() => {
      const el = document.querySelector('.alert, .notice, [class*="filter"], [class*="aviso"]');
      return el ? el.innerText : null;
    });
    if (avisoFiltro) console.log('⚠️  Aviso encontrado:', avisoFiltro);

    // Buscar y hacer click en "Filtros de búsqueda"
    console.log('\n🔍 Buscando botón de filtros...');
    const btnFiltros = await page.locator('text=Filtros de búsqueda').first();
    const visible = await btnFiltros.isVisible().catch(() => false);

    if (visible) {
      await btnFiltros.click();
      console.log('✅ Click en "Filtros de búsqueda"');
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${OUT_DIR}/2_panel_filtros_abierto.png`, fullPage: true });
      console.log('📸 Screenshot 2: panel de filtros abierto');

      // Extraer HTML del panel de filtros
      const htmlFiltros = await page.evaluate(() => {
        // Buscar el formulario o panel de filtros
        const candidatos = [
          document.querySelector('form[id*="filter"]'),
          document.querySelector('form[id*="filtro"]'),
          document.querySelector('form[id*="busqueda"]'),
          document.querySelector('[id*="filter"]'),
          document.querySelector('[id*="filtro"]'),
          document.querySelector('[class*="filter-panel"]'),
          document.querySelector('[class*="panel-filter"]'),
        ].filter(Boolean);

        if (candidatos.length > 0) return candidatos[0].outerHTML;

        // Fallback: buscar inputs de fecha visibles
        const inputs = Array.from(document.querySelectorAll('input[type="date"], input[name*="fecha"], input[id*="fecha"], input[placeholder*="fecha"], input[placeholder*="Fecha"]'));
        return inputs.map(i => `${i.outerHTML} (name=${i.name}, id=${i.id}, placeholder=${i.placeholder})`).join('\n');
      });

      console.log('\n📋 HTML del panel de filtros:');
      console.log(htmlFiltros || '(no encontrado)');
      fs.writeFileSync(`${OUT_DIR}/panel_filtros.html`, htmlFiltros || '(vacío)');

      // Buscar específicamente inputs de fecha
      const inputsFecha = await page.evaluate(() => {
        const inputs = Array.from(document.querySelectorAll('input'));
        return inputs
          .filter(i => i.type === 'date' || i.type === 'text' && (
            i.name?.toLowerCase().includes('fecha') ||
            i.id?.toLowerCase().includes('fecha') ||
            i.placeholder?.toLowerCase().includes('fecha') ||
            i.placeholder?.toLowerCase().includes('date')
          ))
          .map(i => ({
            tag:         i.tagName,
            type:        i.type,
            name:        i.name,
            id:          i.id,
            placeholder: i.placeholder,
            value:       i.value,
            visible:     i.offsetParent !== null,
            selector:    i.id ? `#${i.id}` : i.name ? `[name="${i.name}"]` : '(sin id/name)',
          }));
      });

      console.log('\n📅 Inputs de fecha encontrados:');
      console.log(JSON.stringify(inputsFecha, null, 2));

      // Buscar botón de limpiar filtros
      const btnLimpiar = await page.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="reset"]'));
        return btns
          .filter(b => b.innerText?.toLowerCase().includes('limpiar') ||
                       b.innerText?.toLowerCase().includes('borrar') ||
                       b.innerText?.toLowerCase().includes('reset') ||
                       b.innerText?.toLowerCase().includes('todos') ||
                       b.value?.toLowerCase().includes('limpiar'))
          .map(b => ({ texto: b.innerText || b.value, id: b.id, class: b.className }));
      });

      console.log('\n🧹 Botones limpiar/reset encontrados:');
      console.log(JSON.stringify(btnLimpiar, null, 2));

    } else {
      console.log('⚠️  Botón "Filtros de búsqueda" no encontrado');

      // Buscar inputs de fecha directamente en la página
      const inputsFecha = await page.evaluate(() => {
        const inputs = Array.from(document.querySelectorAll('input'));
        return inputs
          .filter(i => i.type === 'date' || (
            i.name?.toLowerCase().includes('fecha') ||
            i.id?.toLowerCase().includes('fecha')
          ))
          .map(i => ({ type: i.type, name: i.name, id: i.id, value: i.value }));
      });
      console.log('Inputs de fecha en página:', JSON.stringify(inputsFecha, null, 2));
    }

    console.log(`\n✅ Diagnóstico completo. Revisa screenshots en ${OUT_DIR}/`);

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: `${OUT_DIR}/error_diagnostico.png`, fullPage: true });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
