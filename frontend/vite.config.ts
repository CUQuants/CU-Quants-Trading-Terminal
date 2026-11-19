import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The backend is reached same-origin under /api, exactly as in production
// (where Caddy strips /api and forwards to the backend), so the session cookie
// works identically in dev. `changeOrigin` stays false: the backend's
// same-origin check compares the browser's Origin with the Host it receives.
const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: BACKEND,
        ws: true,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
