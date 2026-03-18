/**
 * QA Screenshots — OS Gestión
 * Captura 11 screenshots (desktop + mobile)
 */
const { chromium } = require('/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const TOKEN = fs.readFileSync('/tmp/qa_token.txt', 'utf8').trim();
const PADRE_IDS = JSON.parse(fs.readFileSync('/tmp/qa_padre_ids.json', 'utf8'));
const BASE_URL = 'https://gestion.oscomunidad.com';
const OUT_DIR = '/home/osserver/playwright/exports/qa_gestion';

// Asegurar que el directorio existe
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const USUARIO = { email: 'larevo1111@gmail.com', nombre: 'SYSOP', nivel: 9 };
const EMPRESA = { uid: 'Ori_Sil_2', nombre: 'Origen Silvestre', siglas: 'OS' };

async function injectAuth(page) {
  await page.addInitScript(({ token, usuario, empresa }) => {
    localStorage.setItem('gestion_jwt', token);
    localStorage.setItem('gestion_usuario', JSON.stringify(usuario));
    localStorage.setItem('gestion_empresa', JSON.stringify(empresa));
  }, { token: TOKEN, usuario: USUARIO, empresa: EMPRESA });
}

async function waitForTareas(page) {
  // Esperar a que carguen las tareas (spinner desaparece o aparece contenido)
  await page.waitForTimeout(2000);
  try {
    await page.waitForSelector('.tarea-item, .empty-state, [class*="tarea"]', { timeout: 8000 });
  } catch (e) {
    // continuar de todas formas
  }
  await page.waitForTimeout(1000);
}

async function screenshot(page, filename, description) {
  const filepath = path.join(OUT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: false });
  console.log(`  ✓ ${filename} — ${description}`);
  return filepath;
}

async function runDesktop(browser) {
  console.log('\n=== SCREENSHOTS DESKTOP (1400x850) ===');
  const context = await browser.newContext({
    viewport: { width: 1400, height: 850 }
  });
  const page = await context.newPage();
  await injectAuth(page);

  // 1. Lista principal — filtro "Hoy"
  await page.goto(`${BASE_URL}/tareas`, { waitUntil: 'networkidle', timeout: 30000 });
  await waitForTareas(page);
  // Buscar chip "Hoy" y hacer click
  const chipHoy = page.locator('text=Hoy').first();
  if (await chipHoy.count() > 0) await chipHoy.click();
  await page.waitForTimeout(1500);
  await screenshot(page, '01_desktop_filtro_hoy.png', 'Lista filtro Hoy');

  // 2. Hover sobre tarea con subtareas (padre id=35)
  // Vamos a filtro "Todas" para ver todas las tareas
  const chipTodas = page.locator('text=Todas').first();
  if (await chipTodas.count() > 0) await chipTodas.click();
  await page.waitForTimeout(1500);
  // Hacer hover en la tarea padre (buscar por texto)
  const tareaPadre = page.locator('.tarea-item, [class*="tarea-row"]').filter({ hasText: 'Proyecto expansión punto venta Cali' }).first();
  if (await tareaPadre.count() > 0) {
    await tareaPadre.hover();
    await page.waitForTimeout(500);
  } else {
    // Hover en cualquier tarea
    const cualquierTarea = page.locator('.tarea-item, [class*="tarea"]').first();
    if (await cualquierTarea.count() > 0) await cualquierTarea.hover();
  }
  await screenshot(page, '02_desktop_hover_tarea_con_subtareas.png', 'Hover tarea con subtareas');

  // 3. Filtro "Mañana"
  const chipManana = page.locator('text=Mañana').first();
  if (await chipManana.count() > 0) {
    await chipManana.click();
    await page.waitForTimeout(1500);
  }
  await screenshot(page, '03_desktop_filtro_manana.png', 'Lista filtro Mañana');

  // 4. Filtro "Esta semana"
  const chipSemana = page.locator('text=Esta semana, text=Semana').first();
  if (await chipSemana.count() > 0) {
    await chipSemana.click();
    await page.waitForTimeout(1500);
  } else {
    // Intentar buscar por texto parcial
    const chips = page.locator('[class*="chip"], [class*="filter"], button').filter({ hasText: /semana/i }).first();
    if (await chips.count() > 0) await chips.click();
    await page.waitForTimeout(1500);
  }
  await screenshot(page, '04_desktop_filtro_semana.png', 'Lista filtro Esta semana');

  // 5. Filtro "Todas"
  const chipTodasB = page.locator('text=Todas').first();
  if (await chipTodasB.count() > 0) await chipTodasB.click();
  await page.waitForTimeout(1500);
  await screenshot(page, '05_desktop_filtro_todas.png', 'Lista todas las tareas');

  // 6. Click chip "Personalizado" — ver popup filtro
  const chipPersonalizado = page.locator('text=Personalizado').first();
  if (await chipPersonalizado.count() > 0) {
    await chipPersonalizado.click();
    await page.waitForTimeout(1000);
  }
  await screenshot(page, '06_desktop_chip_personalizado.png', 'Chip Personalizado abierto');

  // 7. Panel de tarea abierto — click en primera tarea
  // Primero cerramos cualquier popup/overlay
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  // Si hay overlay, hacer click fuera de él
  const overlay = page.locator('.fpop-overlay, [class*="overlay"], [class*="modal-backdrop"]').first();
  if (await overlay.count() > 0) {
    await page.mouse.click(50, 50); // click fuera del popup
    await page.waitForTimeout(800);
  }

  // Volver a "Todas"
  const chipTodasC = page.locator('text=Todas').first();
  if (await chipTodasC.count() > 0) await chipTodasC.click();
  await page.waitForTimeout(1500);

  // Click en el título de la primera tarea
  const primeraTarea = page.locator('.tarea-item, [class*="tarea-row"]').first();
  if (await primeraTarea.count() > 0) {
    // Intentar click en el título dentro de la tarea
    const titulo = primeraTarea.locator('[class*="titulo"], [class*="title"], span, p').first();
    if (await titulo.count() > 0) {
      await titulo.click();
    } else {
      await primeraTarea.click();
    }
    await page.waitForTimeout(2000);
  }
  await screenshot(page, '07_desktop_panel_tarea_abierto.png', 'Panel detalle tarea (cronómetro)');

  // 8. Tarea con subtareas expandida
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  // Buscar botón de expandir subtareas (↳ o badge)
  const btnExpand = page.locator('[class*="subtarea"], [class*="expand"], button').filter({ hasText: /↳|subtarea/i }).first();
  if (await btnExpand.count() > 0) {
    await btnExpand.click();
    await page.waitForTimeout(1000);
  } else {
    // Buscar la tarea padre y click en su ↳
    const tareasAll = page.locator('.tarea-item, [class*="tarea-row"]');
    const count = await tareasAll.count();
    for (let i = 0; i < count; i++) {
      const t = tareasAll.nth(i);
      const text = await t.textContent();
      if (text && text.includes('expansión punto venta')) {
        const expandBtn = t.locator('button, [class*="subtarea"]').first();
        if (await expandBtn.count() > 0) await expandBtn.click();
        break;
      }
    }
    await page.waitForTimeout(1000);
  }
  await screenshot(page, '08_desktop_tarea_subtareas_expandida.png', 'Subtareas expandidas');

  // 9. Quick insert subtarea — click en ↳ de una tarea padre
  const botonSubtarea = page.locator('button[title*="subtarea"], [class*="add-subtask"], button').filter({ hasText: /↳/ }).first();
  if (await botonSubtarea.count() > 0) {
    await botonSubtarea.click();
    await page.waitForTimeout(1000);
  }
  await screenshot(page, '09_desktop_quick_insert_subtarea.png', 'Quick insert subtarea activo');

  await context.close();
}

async function runMobile(browser) {
  console.log('\n=== SCREENSHOTS MOBILE (390x844 — iPhone 14) ===');
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
  });
  const page = await context.newPage();
  await injectAuth(page);

  // 10. Lista mobile — filtro chips scrollables
  await page.goto(`${BASE_URL}/tareas`, { waitUntil: 'networkidle', timeout: 30000 });
  await waitForTareas(page);
  await screenshot(page, '10_mobile_lista_chips.png', 'Lista mobile con chips filtro');

  // 11. Bottom sheet tarea abierta
  const primeraTarea = page.locator('.tarea-item, [class*="tarea-row"]').first();
  if (await primeraTarea.count() > 0) {
    await primeraTarea.click();
    await page.waitForTimeout(2000);
  }
  await screenshot(page, '11_mobile_bottom_sheet_tarea.png', 'Bottom sheet tarea abierta');

  await context.close();
}

async function main() {
  console.log('Iniciando Playwright QA...');
  console.log('Token:', TOKEN.substring(0, 30) + '...');
  console.log('Out dir:', OUT_DIR);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    await runDesktop(browser);
    await runMobile(browser);
  } finally {
    await browser.close();
  }

  // Listar archivos generados
  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.png')).sort();
  console.log('\n=== Archivos generados ===');
  files.forEach(f => console.log('  ' + path.join(OUT_DIR, f)));
  console.log(`\nTotal: ${files.length} screenshots`);
}

main().catch(e => {
  console.error('ERROR:', e);
  process.exit(1);
});
