import { defineConfig } from '#q-app/wrappers'
import fs from 'node:fs'
import path from 'node:path'

// Lee APP_TIMEZONE/NAME del integracion_conexionesbd.env raíz del repo (fuente única).
function leerTimezoneCentral() {
  const envPath = path.resolve(import.meta.dirname, '../../integracion_conexionesbd.env')
  if (!fs.existsSync(envPath)) return { APP_TIMEZONE: '-05:00', APP_TIMEZONE_NAME: 'America/Bogota' }
  const out = { APP_TIMEZONE: '', APP_TIMEZONE_NAME: '' }
  for (const linea of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const l = linea.trim()
    if (!l || l.startsWith('#')) continue
    const i = l.indexOf('=')
    if (i < 0) continue
    const k = l.slice(0, i).trim()
    const v = l.slice(i + 1).trim()
    if (k === 'APP_TIMEZONE' || k === 'APP_TIMEZONE_NAME') out[k] = v
  }
  if (!out.APP_TIMEZONE) out.APP_TIMEZONE = '-05:00'
  if (!out.APP_TIMEZONE_NAME) out.APP_TIMEZONE_NAME = 'America/Bogota'
  return out
}
const TZ = leerTimezoneCentral()

export default defineConfig(() => {
  return {
    boot: ['pinia', 'googleAuth'],
    css: ['app.scss'],
    extras: ['material-icons'],
    build: {
      target: { browser: ['es2022'] },
      vueRouterMode: 'hash',
      env: {
        VITE_GOOGLE_CLIENT_ID: '290093919454-j2l1el0p624v65cada556pdc3r2gm6k7.apps.googleusercontent.com',
        VITE_API_BASE: '',
        VITE_APP_TIMEZONE: TZ.APP_TIMEZONE,
        VITE_APP_TIMEZONE_NAME: TZ.APP_TIMEZONE_NAME
      }
    },
    devServer: {
      open: false,
      port: 9301,
      host: '0.0.0.0',
      allowedHosts: 'all',
      proxy: { '/api': 'http://localhost:9300' }
    },
    framework: {
      config: {
        screen: { bodyClasses: true }
      },
      plugins: ['Notify', 'Dialog', 'Loading']
    },
    animations: [],
    pwa: {
      workboxMode: 'GenerateSW',
      workboxOptions: {
        skipWaiting: true,
        clientsClaim: true,
        cleanupOutdatedCaches: true
      }
    },
    capacitor: { hideSplashscreen: true }
  }
})
