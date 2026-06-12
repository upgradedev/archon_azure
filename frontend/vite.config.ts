import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_PROXY_TARGET — backend URL used by the Vite dev proxy (never sent to browser)
// VITE_API_BASE_URL — leave empty for local dev (uses proxy); set for direct prod builds
const proxyTarget = process.env.VITE_PROXY_TARGET
  || process.env.VITE_API_BASE_URL
  || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err) => console.error('[proxy error]', err.message))
        },
      },
    },
  },
})
