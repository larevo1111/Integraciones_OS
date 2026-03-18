const { chromium } = require('playwright');

(async () => {
  const TOKEN = process.argv[2];
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Log de consola para debug
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  // Inyectar JWT en localStorage
  await page.addInitScript((token) => {
    localStorage.setItem('gestion_jwt', token);
    localStorage.setItem('gestion_usuario', JSON.stringify({ email: 'santiago@origensilvestre.com', nombre: 'Santiago' }));
    localStorage.setItem('gestion_empresa', JSON.stringify('Ori_Sil_2'));
  }, TOKEN);

  console.log('Navegando a tareas...');
  await page.goto('https://gestion.oscomunidad.com/#/tareas');

  // Esperar más tiempo a que cargue la SPA
  await page.waitForTimeout(6000);

  // Ver qué hay en la página
  const title = await page.title();
  const url = await page.url();
  console.log('Title:', title, '| URL:', url);

  // Verificar si hay contenido visible
  const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
  console.log('Body text:', bodyText);

  // Screenshot estado inicial
  await page.screenshot({ path: '/tmp/qa_meta_todas.png', fullPage: false });
  console.log('Screenshot 1 guardado');

  // Contar chips disponibles
  const chips = page.locator('.chip');
  const chipCount = await chips.count();
  console.log('Chips encontrados:', chipCount);

  // Click en filtro "Todas"
  let clickedTodas = false;
  for (let i = 0; i < chipCount; i++) {
    const txt = await chips.nth(i).textContent();
    console.log(`Chip ${i}: "${txt}"`);
    if (txt && txt.trim() === 'Todas') {
      await chips.nth(i).click();
      clickedTodas = true;
      console.log('Clicked Todas');
      break;
    }
  }

  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/qa_meta_fila.png', fullPage: false });
  console.log('Screenshot 2 guardado');

  // Hover sobre primera tarea
  const tareas = page.locator('.tarea-item');
  const tareaCount = await tareas.count();
  console.log('Tareas encontradas:', tareaCount);

  if (tareaCount > 0) {
    await tareas.first().hover();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/qa_meta_hover.png', fullPage: false });
    console.log('Screenshot 3 (hover) guardado');
  } else {
    // Screenshot de todas formas
    await page.screenshot({ path: '/tmp/qa_meta_hover.png', fullPage: false });
    console.log('Screenshot 3 guardado (sin hover, no hay tareas)');
  }

  // Dump del DOM de la primera tarea si existe
  if (tareaCount > 0) {
    const html = await tareas.first().innerHTML();
    console.log('HTML primera tarea:', html.substring(0, 1000));
  }

  await browser.close();
  console.log('Listo.');
})();
