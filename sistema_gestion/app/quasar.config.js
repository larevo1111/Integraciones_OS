import { defineConfig } from '#q-app/wrappers'

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
        VITE_API_BASE: ''
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
      config: {},
      plugins: ['Notify', 'Dialog', 'Loading']
    },
    animations: [],
    capacitor: { hideSplashscreen: true }
  }
})
