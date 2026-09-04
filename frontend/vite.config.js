import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_PORT = process.env.VITE_API_PORT || '8021'
const DEV_PORT = Number(process.env.VITE_DEV_PORT || 5190)

export default defineConfig({
  plugins: [react()],
  server: {
    port: DEV_PORT,
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
})
