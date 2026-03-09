/**
 * export_inventario.js
 * Exporta inventario COMPLETO de Effi a Excel
 * Marca todos los checkboxes disponibles dinámicamente (precios y bodegas incluidos)
 * Ruta de salida: /exports/inventario/inventario_YYYY-MM-DD.xlsx
 */

const { chromium }    = require('playwright');
const { contarFilas } = require('./utils');
const path = require('path');
const fs   = require('fs');

const SESSION_FILE = '/scripts/session.json';
const EXPORT_DIR   = '/exports/inventario';
const EFFI_URL     = 'https://effi.com.co/app/articulo';

(async () => {
  if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  if (!fs.existsSync(SESSION_FILE)) {
    console.error('❌ No se encontró session.json en', SESSION_FILE);
    await browser.close();
    process.exit(1);
  }

  console.log('� Cargando sesión guardada...');
  const sessionData = JSON.parse(fs.readFileSync(SESSION_FILE, 'utf8'));
  const context = await browser.newContext({ storageState: sessionData });
  const page = await context.newPage();

  const fecha = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });
  const rutaDestino = path.join(EXPORT_DIR, `inventario_${fecha}.xlsx`);

  console.log('� Navegando a Inventario...');
  await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });

  if (page.url().includes('login') || page.url().includes('signin')) {
    console.error('❌ Sesión expirada. Regenerar session.json con session.js');
    await browser.close();
    process.exit(1);
  }

  console.log('✅ Cargado:', page.url());

  console.log('� Buscando botón exportar...');
  const btnExportar = page.locator('text=Exportar a excel').first();
  await btnExportar.waitFor({ timeout: 15000 });
  await btnExportar.click();

  console.log('⏳ Esperando modal...');
  await page.waitForSelector('#form_excel', { timeout: 10000 });
  await page.waitForTimeout(500);

  const total = await page.evaluate(() => {
    const checkboxes = document.querySelectorAll('#form_excel input[type="checkbox"]');
    checkboxes.forEach(cb => { cb.checked = true; });
    return checkboxes.length;
  });
  console.log(`✅ Marcados ${total} campos (todos)`);

  console.log('� Solicitando exportación...');
  await page.locator('#btnValidarExcel').click();

  await page.waitForSelector('#form_excel', { state: 'hidden', timeout: 15000 });

  console.log('⏳ Esperando generación del archivo (~10s)...');
  await page.waitForTimeout(12000);

  console.log('� Abriendo notificaciones...');
  await page.locator('li.dropdown.notifications-menu a.dropdown-toggle').click();
  await page.waitForSelector('#notify-list', { timeout: 10000 });
  await page.waitForTimeout(500);

  const enlaceDescarga = await page.evaluate(() => {
    const links = document.querySelectorAll('#notify-list a[href*="reportes_excel"][href$=".xlsx"]');
    return links.length > 0 ? links[0].href : null;
  });

  if (!enlaceDescarga) {
    console.error('❌ No se encontró enlace de descarga en notificaciones');
    await browser.close();
    process.exit(1);
  }

  console.log('� Enlace encontrado:', enlaceDescarga);

  const cookies = await context.cookies();
  const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');

  const https = require('https');
  const http = require('http');
  const urlObj = new URL(enlaceDescarga);
  const protocol = urlObj.protocol === 'https:' ? https : http;

  await new Promise((resolve, reject) => {
    const options = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      headers: { Cookie: cookieHeader },
    };
    protocol.get(options, (res) => {
      if (res.statusCode === 302 || res.statusCode === 301) {
        const redirectUrl = new URL(res.headers.location);
        protocol.get({
          hostname: redirectUrl.hostname,
          path: redirectUrl.pathname + redirectUrl.search,
          headers: { Cookie: cookieHeader },
        }, (res2) => {
          const file = fs.createWriteStream(rutaDestino);
          res2.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }).on('error', reject);
      } else {
        const file = fs.createWriteStream(rutaDestino);
        res.pipe(file);
        file.on('finish', () => { file.close(); resolve(); });
      }
    }).on('error', reject);
  });

  console.log(`✅ Exportado: ${rutaDestino} (${contarFilas(rutaDestino)} filas)`);

  await browser.close();
  process.exit(0);
})();
