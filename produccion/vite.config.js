import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { readFileSync } from 'fs'

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'))
const VERSION = pkg.version.replace(/\./g, '_')

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  build: {
    rollupOptions: {
      output: {
        // Incluir versión en el nombre para garantizar invalidación de cache
        entryFileNames:  `assets/[name]-v${VERSION}-[hash].js`,
        chunkFileNames:  `assets/[name]-v${VERSION}-[hash].js`,
        assetFileNames:  `assets/[name]-v${VERSION}-[hash][extname]`,
      },
    },
  },
})
