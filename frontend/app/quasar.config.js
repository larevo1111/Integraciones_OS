import { defineConfig } from '#q-app/wrappers'

export default defineConfig((/* ctx */) => {
  return {
    boot: [],
    css: ['app.scss'],
    extras: [],
    build: {
      target: { browser: ['es2022'] },
      vueRouterMode: 'hash',
      vitePlugins: []
    },
    devServer: {
      open: false,
      port: 9100,
      host: '0.0.0.0'
    },
    framework: {
      config: {},
      plugins: ['Notify', 'Dialog', 'Loading']
    },
    animations: [],
    ssr: { pwa: false },
    pwa: {},
    capacitor: { hideSplashscreen: true },
    electron: { inspectPort: 5858 },
    bex: {}
  }
})
