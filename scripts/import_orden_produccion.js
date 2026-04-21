/**
 * import_orden_produccion.js
 *
 * Crea una Orden de Producción en Effi a partir de un archivo JSON.
 *
 * Uso:
 *   node scripts/import_orden_produccion.js <archivo.json>
 *
 * Formato del JSON:
 * {
 *   "sucursal_id": 1,                    // Siempre 1 - Principal
 *   "bodega_id": 1,                      // 1 = Principal (ver import_ajuste_inventario.js)
 *   "fecha_inicio": "2026-04-21",        // YYYY-MM-DD
 *   "fecha_fin": "2026-04-21",
 *   "encargado": "74084937",             // CC del empleado (Deivy = 74084937, Jenifer = ...)
 *   "tercero": "",                       // CC del tercero (opcional)
 *   "activo_productivo_id": null,        // ID de máquina (opcional)
 *   "observacion": "LOTE xxx",
 *   "materiales": [
 *     { "cod_articulo": "178", "cantidad": 8, "costo": 24000, "lote": "", "serie": "" }
 *   ],
 *   "articulos_producidos": [
 *     { "cod_articulo": "317", "cantidad": 12, "precio": 5605, "lote": "", "serie": "" }
 *   ],
 *   "otros_costos": [
 *     { "tipo_costo_id": 1, "cantidad": 1, "costo": 5000 }
 *   ]
 * }
 *
 * IDs de bodegas: ver import_ajuste_inventario.js
 */

const { getPage } = require('./session');
const path = require('path');
const fs   = require('fs');

const EFFI_URL = 'https://effi.com.co/app/orden_produccion';

// ── Parámetros ──────────────────────────────────────────────────────────────

const jsonPath = process.argv[2];

if (!jsonPath) {
  console.error('Uso: node import_orden_produccion.js <archivo.json>');
  process.exit(1);
}
if (!fs.existsSync(jsonPath)) {
  console.error(`❌ Archivo no encontrado: ${jsonPath}`);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));

// Validación básica
const required = ['sucursal_id', 'bodega_id', 'fecha_inicio', 'fecha_fin', 'encargado'];
for (const k of required) {
  if (!data[k]) {
    console.error(`❌ Campo obligatorio faltante: ${k}`);
    process.exit(1);
  }
}
data.materiales = data.materiales || [];
data.articulos_producidos = data.articulos_producidos || [];
data.otros_costos = data.otros_costos || [];
data.observacion = data.observacion || '';

if (data.materiales.length === 0 && data.articulos_producidos.length === 0) {
  console.error('❌ Se requiere al menos un material o artículo producido');
  process.exit(1);
}

console.log(`📄 Archivo: ${jsonPath}`);
console.log(`🏭 Sucursal: ${data.sucursal_id} | Bodega: ${data.bodega_id}`);
console.log(`📅 ${data.fecha_inicio} → ${data.fecha_fin}`);
console.log(`👤 Encargado: ${data.encargado}`);
console.log(`📦 Materiales: ${data.materiales.length}, Producidos: ${data.articulos_producidos.length}, Otros costos: ${data.otros_costos.length}`);

// Helper: buscar artículo en el autocomplete y seleccionarlo
async function seleccionarArticulo(page, inputSelector, codArticulo) {
  await page.locator(inputSelector).click();
  await page.locator(inputSelector).fill(String(codArticulo));
  await page.waitForTimeout(800);
  // Esperar a que aparezca el dropdown de autocomplete y click en el primer resultado
  // Effi usa jQuery UI autocomplete: los resultados van en .ui-autocomplete
  const resultados = page.locator('.ui-autocomplete:visible li.ui-menu-item');
  await resultados.first().waitFor({ state: 'visible', timeout: 5000 });
  await resultados.first().click();
  await page.waitForTimeout(500);
}

// Helper: buscar encargado/tercero (usa el icono de lupa)
async function buscarEncargado(page, inputNombreId, inputHiddenId, idBusqueda) {
  // Escribir en el input visible
  await page.locator(`#${inputNombreId}`).click();
  await page.locator(`#${inputNombreId}`).fill(String(idBusqueda));
  await page.waitForTimeout(800);
  const resultados = page.locator('.ui-autocomplete:visible li.ui-menu-item');
  await resultados.first().waitFor({ state: 'visible', timeout: 5000 });
  await resultados.first().click();
  await page.waitForTimeout(500);
}

(async () => {
  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Órdenes de producción...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    if (page.url().includes('/ingreso')) {
      console.error('❌ Sesión expirada. Regenerar con session.js');
      process.exit(1);
    }
    console.log('✅ Página cargada');

    // 1. Click en Crear
    console.log('🔄 Abriendo formulario...');
    await page.locator('a:has-text("Crear"), button:has-text("Crear")').first().click();
    await page.waitForTimeout(1500);

    // 2. Sucursal
    console.log(`🔄 Sucursal: ${data.sucursal_id}`);
    await page.evaluate((id) => {
      const sel = document.querySelector('#sucursal_CR');
      sel.value = String(id);
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    }, data.sucursal_id);
    await page.waitForTimeout(1500);

    // 3. Bodega
    console.log(`🔄 Bodega: ${data.bodega_id}`);
    await page.evaluate((id) => {
      const sel = document.querySelector('#bodega_CR');
      sel.disabled = false;
      sel.value = String(id);
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    }, data.bodega_id);
    await page.waitForTimeout(1500);

    // 4. Fechas (Effi usa datepicker, pero con fill directo también funciona si es DD/MM/YYYY)
    const fmtFecha = (iso) => {
      const [y, m, d] = iso.split('-');
      return `${d}/${m}/${y}`;
    };
    console.log(`🔄 Fechas: ${fmtFecha(data.fecha_inicio)} → ${fmtFecha(data.fecha_fin)}`);
    await page.locator('#fecha_inicio_CR').fill(fmtFecha(data.fecha_inicio));
    await page.locator('#fecha_fin_CR').fill(fmtFecha(data.fecha_fin));
    // Cerrar datepicker si queda abierto
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 5. Encargado (buscar por CC)
    console.log(`🔄 Encargado: ${data.encargado}`);
    await buscarEncargado(page, 'nombre_encargado_CR', 'encargado_CR', data.encargado);

    // 6. Tercero (opcional)
    if (data.tercero) {
      console.log(`🔄 Tercero: ${data.tercero}`);
      await buscarEncargado(page, 'nombre_tercero_CR', 'tercero_CR', data.tercero);
    }

    // 7. Activo productivo (opcional)
    if (data.activo_productivo_id) {
      await page.evaluate((id) => {
        const sel = document.querySelector('#maquina_CR');
        sel.value = String(id);
        $(sel).trigger('change');
        $(sel).trigger('chosen:updated');
      }, data.activo_productivo_id);
      await page.waitForTimeout(500);
    }

    // 8. Materiales
    for (let i = 0; i < data.materiales.length; i++) {
      const m = data.materiales[i];
      console.log(`  📥 Material ${i+1}: ${m.cod_articulo} x${m.cantidad}`);
      await seleccionarArticulo(page, '#articulo_CRM', m.cod_articulo);
      await page.locator('#lote_CRM').fill(String(m.lote || ''));
      await page.locator('#serie_CRM').fill(String(m.serie || ''));
      await page.locator('#cantidad_CRM').fill(String(m.cantidad));
      await page.locator('#costo_CRM').fill(String(m.costo || 0));
      // Click Agregar material
      await page.locator('#btnAgregarMaterial').click();
      await page.waitForTimeout(500);
    }

    // 9. Artículos producidos
    for (let i = 0; i < data.articulos_producidos.length; i++) {
      const p = data.articulos_producidos[i];
      console.log(`  📤 Producido ${i+1}: ${p.cod_articulo} x${p.cantidad}`);
      await seleccionarArticulo(page, '#articulo_CRP', p.cod_articulo);
      await page.locator('#lote_CRP').fill(String(p.lote || ''));
      await page.locator('#serie_CRP').fill(String(p.serie || ''));
      await page.locator('#cantidad_CRP').fill(String(p.cantidad));
      await page.locator('#precio_CRP').fill(String(p.precio || 0));
      await page.locator('#btnAgregarProducido').click();
      await page.waitForTimeout(500);
    }

    // 10. Otros costos
    for (let i = 0; i < data.otros_costos.length; i++) {
      const c = data.otros_costos[i];
      console.log(`  💰 Otro costo ${i+1}: tipo ${c.tipo_costo_id} x${c.cantidad}`);
      await page.evaluate((id) => {
        const sel = document.querySelector('#costo_produccion_CR');
        sel.value = String(id);
        $(sel).trigger('change');
        $(sel).trigger('chosen:updated');
      }, c.tipo_costo_id);
      await page.waitForTimeout(300);
      await page.locator('#cantidad_CR').fill(String(c.cantidad));
      await page.locator('input[name="costo[]"]').first().fill(String(c.costo));
      // Click Agregar costo — buscar el botón por texto
      await page.locator('button:has-text("Agregar costo")').click();
      await page.waitForTimeout(500);
    }

    // 11. Observación
    if (data.observacion) {
      console.log(`🔄 Observación: "${data.observacion.substring(0, 50)}..."`);
      const textarea = page.locator('#form_CR textarea[name="observacion"], textarea[placeholder="Observación"]').first();
      await textarea.fill(data.observacion);
      await page.waitForTimeout(300);
    }

    // Screenshot pre-crear
    await page.screenshot({ path: `/exports/op_pre_crear_${Date.now()}.png` });

    // 12. Crear OP
    console.log('🔄 Creando orden de producción...');
    await page.locator('button:has-text("Crear orden de producción")').click();
    await page.waitForTimeout(5000);

    // Verificar errores
    const erroresValidacion = await page.locator('.modal.in .text-danger, .modal.in .alert-danger, .modal.show .text-danger, .modal.show .alert-danger').count();
    if (erroresValidacion > 0) {
      const textoError = await page.locator('.modal.in .text-danger, .modal.in .alert-danger, .modal.show .text-danger, .modal.show .alert-danger').first().textContent().catch(() => 'Error desconocido');
      await page.screenshot({ path: `/exports/op_error_${Date.now()}.png` });
      console.error(`❌ Error de validación: ${textoError.trim()}`);
      process.exit(1);
    }

    const screenshotPath = `/exports/op_resultado_${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath });
    console.log(`✅ Orden de producción creada exitosamente (screenshot: ${screenshotPath})`);

  } catch (err) {
    console.error(`❌ ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/op_error_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
