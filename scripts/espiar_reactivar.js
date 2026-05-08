const { getPage } = require('./session');
(async () => {
  const { browser, page } = await getPage();
  // Capturar requests POST
  page.on('request', req => {
    if (req.method() === 'POST' && req.url().includes('articulo')) {
      console.log(`\n📡 POST: ${req.url()}`);
      console.log(`   Data: ${req.postData()?.substring(0, 300)}`);
    }
  });
  await page.goto('https://effi.com.co/app/articulo', { waitUntil: 'networkidle' });
  console.log('🔄 Filtrando por anulados...');
  // Probar diferentes selectores de filtro
  const html = await page.content();
  // Buscar cómo se llama el campo vigencia
  const matches = html.match(/name=["']filtro_vigencia["']/g) || html.match(/id=["']filtro_vigencia[^"']*["']/g) || [];
  console.log('Selectores filtro_vigencia encontrados:', matches.slice(0, 5));
  // Buscar links Reactivar en cualquier parte
  const reactivarLinks = [...html.matchAll(/href="([^"]+reactivar[^"]*)"|data-action="([^"]*reactiv[^"]*)"|onclick="([^"]*reactiv[^"]*)"/gi)].slice(0, 5);
  console.log('Patrones reactivar en HTML:', reactivarLinks);
  await browser.close();
})();
