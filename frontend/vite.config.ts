import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': process.env.MONIQ_API_TARGET || 'http://127.0.0.1:8000' },
  },
  preview: { port: 4173, proxy: { '/api': process.env.MONIQ_API_TARGET || 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } } },
})
