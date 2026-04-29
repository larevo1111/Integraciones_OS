/**
 * Espía POSTs de Effi al CREAR / MODIFICAR / ANULAR un artículo.
 * Crea "ESPIA-TEST-ZZZ" → modifica nombre → anula. Sin impacto en datos productivos.
 *
 * Uso: node scripts/_espiar_articulo.js
 * Salida: /tmp/espia_articulo_requests.json
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SESION = path.join(__dirname, 'session.json');
const NOMBRE_TEST = `ESPIA-TEST-ZZZ-${Date.now().toString().slice(-6)}`;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ storageState: SESION });
  const page = await ctx.newPage();

  const requests = [];
  page.on('request', req => {
    const url = req.url();
    if (url.includes('effi.com.co') && req.method() !== 'GET') {
      const data = {
        method: req.method(),
        url: url,
        post_data: req.postData(),
        ts: Date.now(),
      };
      requests.push(data);
      console.log(`>>> ${req.method()} ${url}`);
      if (data.post_data) {
        console.log(`    POST (${data.post_data.length}b): ${data.post_data.substring(0, 400)}`);
      }
    }
  });
  page.on('response', async resp => {
    const url = resp.url();
    if (url.includes('effi.com.co') && resp.request().method() !== 'GET' && resp.status() < 500) {
      try {
        const body = await resp.text();
        console.log(`<<< ${resp.status()} ${url} → ${body.substring(0, 200)}`);
      } catch {}
    }
  });

  // ─────────────────────────────────────────
  // FASE 1: CREAR
  // ─────────────────────────────────────────
  console.log('\n========== FASE 1: CREAR ==========');
  await page.goto('https://effi.com.co/app/articulo', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);

  // Click "Crear" (los pantallazos muestran botón verde "Crear" arriba)
  await page.click('a:has-text("Crear"), button:has-text("Crear")', { timeout: 10000 }).catch(e => {
    console.log('No encontré botón Crear directo, intentando .btn-success...');
    return page.click('.btn-success').catch(() => {});
  });
  await page.waitForTimeout(2000);

  // Llenar campos mínimos del modal Crear
  await page.fill('input[name="nombre"]', NOMBRE_TEST).catch(e => console.log('fill nombre fail:', e.message));
  // Tipo: Materia prima (id 1)
  await page.evaluate(() => {
    if (window.$ && $('#tipo_id').length) $('#tipo_id').val(1).trigger('change').trigger('chosen:updated');
    if (window.$ && $('#sucursal_id').length) $('#sucursal_id').val(1).trigger('change').trigger('chosen:updated');
    // Categoría: tomar la primera que aparezca
    if (window.$ && $('#categoria_id').length) {
      const opts = $('#categoria_id option').not(':first');
      if (opts.length) $('#categoria_id').val(opts.first().val()).trigger('change').trigger('chosen:updated');
    }
  });
  await page.fill('input[name="costo_manual"]', '1').catch(() => {});

  console.log('🚀 Submitting CREAR...');
  await page.click('button:has-text("Crear artículo"), button[type="submit"]').catch(() => {});
  await page.waitForTimeout(3000);

  // ─────────────────────────────────────────
  // FASE 2: MODIFICAR (buscar el artículo recién creado)
  // ─────────────────────────────────────────
  console.log('\n========== FASE 2: MODIFICAR ==========');
  await page.goto('https://effi.com.co/app/articulo', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // Buscar el artículo por nombre
  const filtroInput = page.locator('input[name="filtro"], input[placeholder*="Buscar"], #filtro').first();
  await filtroInput.fill(NOMBRE_TEST).catch(() => {});
  await page.waitForTimeout(2000);

  // Capturar el ID del artículo recién creado (data-id de la primera fila)
  const articuloIdCreado = await page.evaluate(() => {
    const row = document.querySelector('tr[data-id], [data-id]');
    return row ? row.getAttribute('data-id') : null;
  });
  console.log(`🆔 Artículo creado ID: ${articuloIdCreado}`);

  // Click en menú "Acciones" del primer artículo + "Modificar"
  await page.click('button.dropdown-toggle, .btn-default.dropdown-toggle, [data-toggle="dropdown"]').catch(() => {});
  await page.waitForTimeout(800);
  await page.click('a:has-text("Modificar")').catch(() => {});
  await page.waitForTimeout(2000);

  // Cambiar el nombre
  await page.fill('input[name="nombre"]', NOMBRE_TEST + '-MOD').catch(() => {});
  await page.fill('input[name="costo_manual"]', '2').catch(() => {});

  console.log('🚀 Submitting MODIFICAR...');
  await page.click('button:has-text("Modificar artículo"), button[type="submit"]').catch(() => {});
  await page.waitForTimeout(3000);

  // ─────────────────────────────────────────
  // FASE 3: ANULAR
  // ─────────────────────────────────────────
  console.log('\n========== FASE 3: ANULAR ==========');
  await page.goto('https://effi.com.co/app/articulo', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await filtroInput.fill(NOMBRE_TEST).catch(() => {});
  await page.waitForTimeout(2000);

  await page.click('button.dropdown-toggle, .btn-default.dropdown-toggle, [data-toggle="dropdown"]').catch(() => {});
  await page.waitForTimeout(800);
  await page.click('a:has-text("Anular")').catch(() => {});
  await page.waitForTimeout(1500);

  // Si hay confirmación
  await page.click('button:has-text("Sí"), button:has-text("Confirmar"), button.btn-danger').catch(() => {});
  await page.waitForTimeout(2500);

  // ─────────────────────────────────────────
  // Guardar
  // ─────────────────────────────────────────
  fs.writeFileSync('/tmp/espia_articulo_requests.json',
    JSON.stringify({ articulo_id_creado: articuloIdCreado, nombre_test: NOMBRE_TEST, requests }, null, 2));
  console.log(`\n📝 ${requests.length} requests → /tmp/espia_articulo_requests.json`);
  console.log(`   Artículo de prueba creado: ${NOMBRE_TEST} (id=${articuloIdCreado})`);

  await browser.close();
})();
