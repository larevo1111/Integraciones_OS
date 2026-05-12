const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SESSION_FILE = path.join(__dirname, 'session.json');

// Credenciales Effi — cargadas de Infisical (con fallback a env vars)
// Antes de 2026-05-11 estaban hardcoded en este archivo (leak fix).
let EFFI_URL = process.env.EFFI_URL || 'https://effi.com.co';
let EFFI_USER = process.env.EFFI_USER;
let EFFI_PASS = process.env.EFFI_PASS;

async function _cargarCredsInfisical() {
  if (EFFI_USER && EFFI_PASS) return;  // ya cargadas
  try {
    const infisical = require('../lib/infisical');
    const effi = await infisical.getMany('/effi');
    if (effi.EFFI_URL) EFFI_URL = effi.EFFI_URL;
    if (effi.EFFI_USER) EFFI_USER = effi.EFFI_USER;
    if (effi.EFFI_PASS) EFFI_PASS = effi.EFFI_PASS;
  } catch (e) {
    console.warn(`[session] Infisical /effi no disponible: ${e.message}`);
  }
}

async function getPage() {
  await _cargarCredsInfisical();
  if (!EFFI_USER || !EFFI_PASS) {
    throw new Error('EFFI_USER/EFFI_PASS no disponibles (Infisical ni env vars)');
  }
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
