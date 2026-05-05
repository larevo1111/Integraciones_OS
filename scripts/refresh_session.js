/**
 * refresh_session.js — Solo renueva la sesión Effi (no crea nada).
 * Usar cuando las cookies expiradas impiden que POST directo funcione.
 * Tiempo: ~20-30s (mucho más rápido que el Playwright completo de OP ~90s).
 *
 * Uso: node scripts/refresh_session.js
 * Salida: sale con 0 si ok, 1 si falla.
 */
const { getPage } = require('./session');

(async () => {
  let browser;
  try {
    const result = await getPage();
    browser = result.browser;
    console.log('✅ Sesión Effi renovada correctamente');
  } catch (e) {
    console.error('❌ Error renovando sesión:', e.message);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
})();
