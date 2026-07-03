import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The /api proxy is load-bearing: the browser only ever talks to one origin
// (5173 in dev, the FastAPI host in prod), so no CORS on the happy path and
// token handling behaves identically in both environments.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
