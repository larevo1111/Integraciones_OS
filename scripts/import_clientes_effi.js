/**
 * import_clientes_effi.js — Paso 7b del pipeline
 *
 * Sube el XLSX generado por generar_plantilla_import_effi.py a Effi
 * via "Crear o modificar contactos masivamente".
 *
 * Uso:
 *   node scripts/import_clientes_effi.js                  # usa /tmp/import_clientes_effi_<hoy>.xlsx
 *   node scripts/import_clientes_effi.js /ruta/archivo.xlsx
 *
 * El archivo debe existir antes de llamar este script.
 */

const { getPage } = require('./session');
const path        = require('path');
const fs          = require('fs');

const HOY = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

// Ruta del XLSX: argumento o por defecto /tmp/import_clientes_effi_<hoy>.xlsx
const xlsxPath = process.argv[2]
  || `/tmp/import_clientes_effi_${HOY}.xlsx`;

(async () => {
  // Verificar que el archivo existe
  if (!fs.existsSync(xlsxPath)) {
    console.error(`❌ Archivo no encontrado: ${xlsxPath}`);
    console.error('   Ejecuta primero: python3 scripts/generar_plantilla_import_effi.py');
    process.exit(1);
  }

  console.log(`📄 Archivo a importar: ${xlsxPath}`);

  const { browser, page } = await getPage();

  try {
    // 1. Navegar a la sección de contactos
    await page.goto('https://effi.com.co/app/tercero/contacto', { waitUntil: 'networkidle' });
    await page.waitForSelector('text=Crear o modificar contactos masivamente', { timeout: 15000 });

    // 2. Abrir el modal de importación masiva
    await page.click('text=Crear o modificar contactos masivamente');
    // Esperar a que el modal esté visible (el input #id_ICM está en el DOM siempre, pero el modal se abre)
    await page.waitForTimeout(1000);

    // 3. Subir el archivo XLSX
    // Hay varios input[name="userfile"] — el primero es el del ICM (importar contactos masivamente)
    const fileInput = page.locator('input[name="userfile"]').first();
    await fileInput.setInputFiles(xlsxPath);
    console.log(`   ✅ Archivo seleccionado: ${path.basename(xlsxPath)}`);
    await page.waitForTimeout(1000);

    // 4. Click en "Crear o modificar" — botón #btn_submit dentro del modal ICM
    await page.click('#btn_submit');

    // 5. Esperar resultado — Effi procesa y muestra mensaje
    await page.waitForTimeout(5000);

    // Capturar el resultado buscando mensajes típicos de Effi
    const mensajeExito = await page.locator('text=/creado|modificado|importado|éxito|exitoso/i').count();
    const mensajeError = await page.locator('text=/error|falló|inválido/i').count();

    if (mensajeError > 0) {
      const textoError = await page.locator('text=/error|falló|inválido/i').first().textContent();
      console.error(`❌ import_clientes_effi — ERROR en Effi: ${textoError}`);
      await page.screenshot({ path: `/exports/error_import_effi_${Date.now()}.png` });
      process.exit(1);
    }

    // Screenshot para verificación
    const screenshotPath = `/exports/import_effi_resultado_${HOY}.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`✅ import_clientes_effi — importación completada (screenshot: ${screenshotPath})`);

  } catch (err) {
    console.error(`❌ import_clientes_effi — ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/error_import_effi_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
