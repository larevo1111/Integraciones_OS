/** Espía requests POST de Effi al crear OP. Usa selectores correctos del script real. */
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ storageState: 'scripts/session.json' });
  const page = await ctx.newPage();

  const reqs = [];
  page.on('request', req => {
    const u = req.url();
    if (u.includes('effi.com.co') && req.method() !== 'GET' && !u.includes('bam.nr-data')) {
      const d = { method: req.method(), url: u, headers: req.headers(), post_data: req.postData() };
      reqs.push(d);
      console.log(`>>> ${req.method()} ${u}`);
      if (d.post_data) console.log(`    DATA(${d.post_data.length}b): ${d.post_data.substring(0,400)}`);
    }
  });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('effi.com.co') && r.request().method() !== 'GET' && !u.includes('bam.nr')) {
      try {
        const b = await r.text();
        console.log(`<<< ${r.status()} ${u} → ${b.substring(0,200)}`);
      } catch {}
    }
  });

  // Usar JSON simple
  const data = JSON.parse(fs.readFileSync('/tmp/op_test_espia.json'));

  const _impl = require('./import_orden_produccion.js');
  // Mejor: ejecutar el script y suplantar la creación
  await page.goto('https://effi.com.co/app/orden_produccion', { waitUntil: 'networkidle' });
  console.log('🔍 Página cargada');

  // Click "Crear" (lupa o botón +)
  await page.click('a[href*="orden_produccion/create"], a[title*="Crear"], i.fa-plus').catch(() => {});
  await page.waitForTimeout(2000);

  console.log('📝 Form abierto. Revisar selectores reales:');
  const inputs = await page.$$eval('input[name], select[name]', els => els.map(e => ({ name: e.name, id: e.id, type: e.type })));
  console.log('Form fields:', JSON.stringify(inputs.slice(0, 30), null, 2));

  fs.writeFileSync('/tmp/espia_form_fields.json', JSON.stringify(inputs, null, 2));
  fs.writeFileSync('/tmp/espia_op_requests.json', JSON.stringify(reqs, null, 2));
  console.log(`\n📦 Captura inicial guardada. Próximo paso: identificar el POST de submit.`);

  await browser.close();
})();
