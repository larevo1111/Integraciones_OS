const { chromium } = require('playwright');
const fs = require('fs');

const SESSION_FILE = '/scripts/session.json';
const EFFI_URL = 'https://effi.com.co';
const EFFI_USER = 'ORIGENSILVESTRE.COL@GMAIL.COM';
const EFFI_PASS = 'LAREVO1111';

async function getPage() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = fs.existsSync(SESSION_FILE)
    ? await browser.newContext({ storageState: SESSION_FILE })
    : await browser.newContext();

  const page = await context.newPage();

  // Verificar si la sesión sigue válida
  await page.goto(`${EFFI_URL}/app/tercero/cliente`);
  
  if (page.url().includes('/ingreso')) {
    console.log('� Sesión expirada, haciendo login...');
    await login(page, context);
  } else {
    console.log('✅ Sesión activa reutilizada');
  }

  return { browser, context, page };
}

async function login(page, context) {
  await page.goto(`${EFFI_URL}/ingreso`);
  await page.fill('#email', EFFI_USER);
  await page.fill('#password', EFFI_PASS);
  
  // Submit directo sin esperar reCAPTCHA (es invisible)
  await page.evaluate(() => {
    document.querySelector('form#login').submit();
  });

  await page.waitForURL(url => !url.toString().includes('/ingreso'), { timeout: 15000 });
  
  // Guardar sesión
  await context.storageState({ path: SESSION_FILE });
  console.log('✅ Login exitoso, sesión guardada');
}

module.exports = { getPage };
