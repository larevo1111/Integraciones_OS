/**
 * import_ajuste_inventario.js
 *
 * Crea un ajuste de inventario en Effi importando conceptos desde un Excel.
 *
 * Flujo:
 *   1. Navegar a Ajustes de inventario
 *   2. Click "Crear"
 *   3. Seleccionar Sucursal (siempre Principal) y Bodega (parámetro)
 *   4. Click "Importar conceptos"
 *   5. Subir archivo Excel
 *   6. Click "Importar conceptos" en el modal de upload
 *   7. Esperar que se carguen los conceptos
 *   8. Llenar campo Observación
 *   9. Click "Crear ajuste de inventario"
 *
 * Uso:
 *   node scripts/import_ajuste_inventario.js <bodega_id> <archivo.xlsx> [observacion]
 *
 * Ejemplo:
 *   node scripts/import_ajuste_inventario.js 1 /tmp/ajuste_principal.xlsx "Ajuste inventario marzo 2026"
 *
 * Bodegas (ID - Nombre):
 *   1  - Principal
 *   2  - Villa de aburra
 *   3  - Apica
 *   4  - El Salvador
 *   5  - Feria Santa Elena
 *   6  - DON LUIS SAN MIGUEL
 *   7  - LA TIERRITA
 *   8  - Jenifer
 *   10 - REGINALDO
 *   13 - Desarrollo de Producto
 *   14 - Ricardo
 *   15 - Mercado Libre
 *   16 - Santiago
 *   17 - Productos No Conformes Bod PPAL
 *   18 - FERIA CAMPESINA SAN CARLOS
 */

const { getPage } = require('./session');
const path = require('path');
const fs   = require('fs');

const EFFI_URL = 'https://effi.com.co/app/ajuste_inventario';
const HOY = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });
const AHORA = new Date().toLocaleString('es-CO', { timeZone: 'America/Bogota' });

// ── Parámetros ──────────────────────────────────────────────────────────────

const bodegaId    = process.argv[2];
const xlsxPath    = process.argv[3];
const observacion = process.argv[4] || `SYS GENERATED - Ajuste inventario, ${AHORA}`;

if (!bodegaId || !xlsxPath) {
  console.error('Uso: node import_ajuste_inventario.js <bodega_id> <archivo.xlsx> [observacion]');
  console.error('Ejemplo: node import_ajuste_inventario.js 1 /tmp/ajuste.xlsx "Ajuste marzo"');
  process.exit(1);
}

if (!fs.existsSync(xlsxPath)) {
  console.error(`❌ Archivo no encontrado: ${xlsxPath}`);
  process.exit(1);
}

console.log(`📄 Archivo: ${xlsxPath}`);
console.log(`🏭 Bodega ID: ${bodegaId}`);
console.log(`📝 Observación: ${observacion}`);

(async () => {
  const { browser, page } = await getPage();

  try {
    // 1. Navegar a Ajustes de inventario
    console.log('🔄 Navegando a Ajustes de inventario...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

    if (page.url().includes('/ingreso')) {
      console.error('❌ Sesión expirada. Regenerar con session.js');
      process.exit(1);
    }
    console.log('✅ Página cargada');

    // 2. Click en botón "Crear" (botón + Crear en la barra de acciones)
    console.log('🔄 Abriendo formulario de creación...');
    await page.locator('a:has-text("Crear"), button:has-text("Crear")').first().click();
    await page.waitForTimeout(1500);

    // 3. Seleccionar Sucursal: "1 - Principal" via jQuery Chosen API
    console.log('🔄 Seleccionando Sucursal: Principal...');
    await page.evaluate(() => {
      const sel = document.querySelector('#sucursal_CR');
      sel.value = '1';
      // Disparar change para que Effi cargue bodegas y Chosen se actualice
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    });
    await page.waitForTimeout(2000);

    // 4. Seleccionar Bodega por ID via jQuery Chosen API
    console.log(`🔄 Seleccionando Bodega ID ${bodegaId}...`);
    await page.evaluate((id) => {
      const sel = document.querySelector('#bodega_CR');
      sel.disabled = false;
      sel.value = id;
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    }, bodegaId);
    await page.waitForTimeout(2000);

    // Esperar que se cargue el formulario completo (divFase2 visible)
    await page.waitForSelector('#divFase2:not([style*="display: none"])', { timeout: 10000 });
    console.log('✅ Formulario cargado');

    // 5. Click en "Importar conceptos" (botón verde en el formulario principal)
    console.log('🔄 Abriendo modal de importación...');
    await page.locator('#importarConceptos_CR').click();
    await page.waitForTimeout(1500);

    // 6. Subir archivo Excel — buscar el file input dentro del modal de importación
    console.log('🔄 Subiendo archivo Excel...');
    // El modal de importación tiene un form con input[type=file]
    // Necesitamos el que está visible ahora (en el modal de importar conceptos)
    const modalImport = page.locator('.modal.in .modal-body input[type="file"], .modal.show .modal-body input[type="file"]');
    const inputCount = await modalImport.count();
    console.log(`   File inputs en modal: ${inputCount}`);
    if (inputCount > 0) {
      await modalImport.first().setInputFiles(xlsxPath);
    } else {
      // Fallback: buscar cualquier file input visible
      await page.locator('input[type="file"]').last().setInputFiles(xlsxPath);
    }
    console.log(`✅ Archivo seleccionado: ${path.basename(xlsxPath)}`);
    await page.waitForTimeout(1000);

    // Screenshot post-upload
    await page.screenshot({ path: `/exports/ajuste_post_upload_${Date.now()}.png` });

    // 7. Click "Importar conceptos" en el modal de upload (botón #btn_submit del formulario #formulario_IC)
    console.log('🔄 Importando conceptos...');
    await page.locator('#formulario_IC #btn_submit').click();
    await page.waitForTimeout(5000);

    // Esperar que el modal de importación se cierre
    // El formulario principal debe volver a ser visible con los conceptos cargados
    await page.screenshot({ path: `/exports/ajuste_pre_crear_${Date.now()}.png` });

    // 8. Llenar campo Observación
    console.log('🔄 Llenando observación...');
    await page.evaluate((obs) => {
      const ta = document.querySelector('#form_CR textarea');
      if (ta) ta.value = obs;
    }, observacion);
    await page.waitForTimeout(500);

    // 9. Click "Crear ajuste de inventario"
    console.log('🔄 Creando ajuste de inventario...');
    await page.evaluate(() => {
      const btns = document.querySelectorAll('#form_CR button, #form_CR input[type="submit"]');
      for (const btn of btns) {
        if (btn.textContent.includes('Crear ajuste')) { btn.click(); return; }
      }
      // Fallback: submit del form
      document.querySelector('#form_CR').submit();
    });

    // 10. Esperar resultado
    await page.waitForTimeout(5000);

    // Screenshot del resultado
    const screenshotPath = `/exports/ajuste_resultado_${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath });

    // Verificar si hubo error
    const hayError = await page.locator('text=/error|falló|inválido/i').count();
    if (hayError > 0) {
      const textoError = await page.locator('text=/error|falló|inválido/i').first().textContent();
      console.error(`❌ import_ajuste_inventario — ERROR en Effi: ${textoError}`);
      process.exit(1);
    }

    console.log(`✅ import_ajuste_inventario — Ajuste creado exitosamente (screenshot: ${screenshotPath})`);

  } catch (err) {
    console.error(`❌ import_ajuste_inventario — ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/error_ajuste_inventario_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
