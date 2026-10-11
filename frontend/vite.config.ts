import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [react(), tailwindcss(), VitePWA({
    strategies: 'injectManifest',
    srcDir: 'src', filename: 'sw.js',
    manifest: false, injectRegister: null, registerType: 'prompt',
    injectManifest: {
      // Only public static resources: never HTML pages populated by an API,
      // financial responses, exports, session cookies or OAuth routes.
      globPatterns: ['assets/*.{js,css}', 'icons/*.png', 'icon.svg', 'offline.html'],
      maximumFileSizeToCacheInBytes: 2 * 1024 * 1024,
    },
    devOptions: { enabled: false },
  })],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': process.env.MONIQ_API_TARGET || 'http://127.0.0.1:8000' },
  },
  preview: { port: 4173, proxy: { '/api': process.env.MONIQ_API_TARGET || 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } } },
})
