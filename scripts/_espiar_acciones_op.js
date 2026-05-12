/**
 * _espiar_acciones_op.js — Captura los POST de "Cambiar estado" y "Anular" de OP en Effi.
 *
 * Estrategia: usa page.route() para INTERCEPTAR los POST a /app/orden_produccion/*
 * y ABORTARLOS antes de que lleguen al servidor. Captura URL + body + headers
 * sin modificar datos reales en Effi.
 *
 * Uso:
 *   node scripts/_espiar_acciones_op.js <id_orden> <accion>
 *
 * Acciones: "cambiar_estado_procesada" | "cambiar_estado_validado" | "anular"
 *
 * Output: /tmp/espia_<accion>_<id_orden>.json con la(s) request(s) capturada(s).
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SESION = path.join(__dirname, 'session.json');
const EFFI_URL = 'https://effi.com.co/app/orden_produccion';

const idOrden = process.argv[2];
const accion  = process.argv[3];

if (!idOrden || !accion) {
  console.error('Uso: node _espiar_acciones_op.js <id_orden> <accion>');
  console.error('Acciones: cambiar_estado_procesada | cambiar_estado_validado | anular');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ storageState: SESION });
  const page = await ctx.newPage();

  const capturadas = [];

  // Interceptar y ABORTAR cualquier POST a Effi orden_produccion
  await page.route('**/effi.com.co/app/orden_produccion/**', async route => {
    const req = route.request();
    if (req.method() === 'POST') {
      const data = {
        method: req.method(),
        url: req.url(),
        headers: req.headers(),
        post_data: req.postData(),
        post_data_decoded: null,
      };
      // Decode form-urlencoded para legibilidad
      try {
        if (data.post_data && data.headers['content-type']?.includes('urlencoded')) {
          const decoded = {};
          for (const pair of data.post_data.split('&')) {
            const [k, v] = pair.split('=');
            const key = decodeURIComponent(k);
            const val = decodeURIComponent((v || '').replace(/\+/g, ' '));
            if (key in decoded) {
              if (!Array.isArray(decoded[key])) decoded[key] = [decoded[key]];
              decoded[key].push(val);
            } else {
              decoded[key] = val;
            }
          }
          data.post_data_decoded = decoded;
        }
      } catch (e) { data.parse_error = e.message; }
      capturadas.push(data);
      console.log(`\n>>> POST INTERCEPTADO: ${req.url()}`);
      console.log(`    Bytes: ${data.post_data?.length || 0}`);
      // Devolver respuesta fake exitosa para que la UI no rompa
      await route.fulfill({ status: 200, body: JSON.stringify({ ok: true, intercepted: true }) });
    } else {
      await route.continue();
    }
  });

  console.log(`🔍 Navegando a Effi orden_produccion (acción: ${accion})...`);
  await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
  if (page.url().includes('/ingreso')) {
    console.error('❌ Sesión expirada. Regenerar con scripts/session.js');
    process.exit(1);
  }

  // Buscar OP
  console.log(`🔄 Buscando OP ${idOrden}...`);
  try {
    await page.locator('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda")').first().click({ timeout: 5000 });
    await page.waitForTimeout(700);
    const filtroId = page.locator('input[name="filtro_id_orden"], input[placeholder*="ID"]').first();
    if (await filtroId.count() > 0) {
      await filtroId.fill(String(idOrden));
      await page.locator('button:has-text("Buscar"), button:has-text("Aplicar"), button:has-text("Filtrar")').first().click();
      await page.waitForTimeout(2000);
    }
  } catch (e) { console.log('  (Sin filtros — busco en la página)'); }

  const fila = page.locator(`tr:has-text("ID: ${idOrden}"), tr:has-text("ID_EFFI: ${idOrden}")`).first();
  if ((await fila.count()) === 0) {
    console.error(`❌ OP ${idOrden} no encontrada`);
    process.exit(1);
  }

  // Dropdown fila
  await fila.locator('button.dropdown-toggle, button:has(.fa-ellipsis-v), button:has(.caret)').first().click();
  await page.waitForTimeout(500);

  if (accion === 'cambiar_estado_procesada' || accion === 'cambiar_estado_validado') {
    const estadoTarget = accion === 'cambiar_estado_procesada' ? 'Procesada' : 'Validado';
    console.log(`🔄 Abriendo modal "Cambiar estado" → ${estadoTarget}...`);
    await page.locator('.dropdown-menu a:has-text("Cambiar estado"), ul.dropdown-menu a:has-text("Cambiar estado")').first().click();
    await page.waitForTimeout(1200);

    const modal = page.locator('.modal.in, .modal.show').last();
    await modal.locator('.chosen-container, .chosen-single').first().click();
    await page.waitForTimeout(400);
    await page.locator(`.chosen-results li.active-result:has-text("${estadoTarget}")`).first().click();
    await page.waitForTimeout(300);
    const textarea = modal.locator('textarea').first();
    if (await textarea.count() > 0) await textarea.fill('ESPIA — interceptado, NO ejecutado');

    console.log(`🚀 Click final "Cambiar estado" (POST se aborta)...`);
    await modal.locator('button:has-text("Cambiar estado")').last().click();
    await page.waitForTimeout(3000);
  } else if (accion === 'anular') {
    console.log(`🔄 Click "Anular" del dropdown...`);
    await page.locator('.dropdown-menu a:has-text("Anular"), ul.dropdown-menu a:has-text("Anular")').first().click();
    await page.waitForTimeout(1200);
    const modal = page.locator('.modal.in, .modal.show').last();
    const textarea = modal.locator('textarea').first();
    if (await textarea.count() > 0) await textarea.fill('ESPIA — interceptado, NO ejecutado');
    console.log(`🚀 Click final "Anular" (POST se aborta)...`);
    await modal.locator('button:has-text("Anular"), button:has-text("Confirmar")').last().click();
    await page.waitForTimeout(3000);
  }

  const outFile = `/tmp/espia_${accion}_${idOrden}.json`;
  fs.writeFileSync(outFile, JSON.stringify(capturadas, null, 2));
  console.log(`\n📝 ${capturadas.length} request(s) capturada(s) en ${outFile}`);
  if (capturadas.length > 0) {
    console.log(`\n=== Primera request capturada ===`);
    console.log(`URL: ${capturadas[0].url}`);
    console.log(`Bytes: ${capturadas[0].post_data?.length || 0}`);
    if (capturadas[0].post_data_decoded) {
      console.log(`Fields (decoded):`);
      for (const [k, v] of Object.entries(capturadas[0].post_data_decoded)) {
        const vs = Array.isArray(v) ? `[${v.length} items]` : String(v).slice(0, 80);
        console.log(`  ${k} = ${vs}`);
      }
    }
  }

  await browser.close();
})();
