/**
 * QA Script — ia.oscomunidad.com
 * Toma screenshots de todas las páginas con sesión autenticada.
 */
const { chromium } = require('/home/osserver/Proyectos_Antigravity/Integraciones_OS/scripts/node_modules/playwright')

const JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImxhcmV2bzExMTFAZ21haWwuY29tIiwibm9tYnJlIjoiU2FudGlhZ28iLCJyb2wiOiJhZG1pbiIsImZvdG8iOiIiLCJpYXQiOjE3NzMzNjY5ODYsImV4cCI6MTc3Mzk3MTc4Nn0.BUJevo5ntnvNkMuj7GK8FZt-ORR18ekED_6LEr3kygc'
const USUARIO = JSON.stringify({ email: 'larevo1111@gmail.com', nombre: 'Santiago', rol: 'admin', foto: '' })

const BASE = 'https://ia.oscomunidad.com'
const SCREENSHOTS = '/home/osserver/playwright/exports'

const paginas = [
  { ruta: '/#/dashboard',  nombre: 'dashboard' },
  { ruta: '/#/agentes',    nombre: 'agentes' },
  { ruta: '/#/tipos',      nombre: 'tipos' },
  { ruta: '/#/logs',       nombre: 'logs' },
  { ruta: '/#/playground', nombre: 'playground' },
  { ruta: '/#/usuarios',   nombre: 'usuarios' },
]

;(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
  const erroresConsola = {}

  for (const p of paginas) {
    erroresConsola[p.nombre] = []

    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 }
    })

    // Inyectar JWT en localStorage antes de navegar
    await ctx.addInitScript(({ jwt, usuario }) => {
      localStorage.setItem('ia_jwt', jwt)
      localStorage.setItem('ia_usuario', usuario)
    }, { jwt: JWT, usuario: USUARIO })

    const page = await ctx.newPage()

    // Capturar errores de consola
    page.on('console', msg => {
      if (msg.type() === 'error') {
        erroresConsola[p.nombre].push(`[console.error] ${msg.text()}`)
      }
    })
    page.on('pageerror', err => {
      erroresConsola[p.nombre].push(`[pageerror] ${err.message}`)
    })

    try {
      await page.goto(BASE + p.ruta, { waitUntil: 'networkidle', timeout: 15000 })
      await page.waitForTimeout(2500)

      const path = `${SCREENSHOTS}/ia_admin_${p.nombre}.png`
      await page.screenshot({ path, fullPage: true })
      console.log(`OK: ${p.nombre} → ${path}`)

      // Si hay errores de consola, logearlos
      if (erroresConsola[p.nombre].length > 0) {
        console.log(`  ERRORES en ${p.nombre}: ${erroresConsola[p.nombre].join(' | ')}`)
      }
    } catch (e) {
      console.error(`ERROR en ${p.nombre}: ${e.message}`)
      erroresConsola[p.nombre].push(`[navigation] ${e.message}`)
    }

    await ctx.close()
  }

  // Screenshot de login page
  const ctxLogin = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const pageLogin = await ctxLogin.newPage()
  try {
    await pageLogin.goto(BASE + '/#/login', { waitUntil: 'networkidle', timeout: 10000 })
    await pageLogin.waitForTimeout(1500)
    await pageLogin.screenshot({ path: `${SCREENSHOTS}/ia_admin_login.png`, fullPage: true })
    console.log('OK: login screenshot')
  } catch (e) { console.error('ERROR login:', e.message) }
  await ctxLogin.close()

  await browser.close()

  // Escribir errores de consola
  console.log('\n=== Errores de consola por página ===')
  for (const [pag, errs] of Object.entries(erroresConsola)) {
    if (errs.length > 0) {
      console.log(`\n${pag}:`)
      errs.forEach(e => console.log('  ' + e))
    } else {
      console.log(`${pag}: sin errores`)
    }
  }
})()
