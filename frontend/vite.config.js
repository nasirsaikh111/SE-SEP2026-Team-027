import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Forward API calls to the Django backend so the browser sees one origin (no CORS setup needed)
    proxy: {
      '/api': { target: process.env.SANGAM_API || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
