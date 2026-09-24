import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The dev server proxies /api to Flask so the session cookie is same-origin.
// Outside Docker the backend runs on localhost:5000; compose overrides the target.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:5000'
// When the dev server sits behind Nginx, the browser must open the HMR socket on Nginx's port.
const hmrClientPort = process.env.VITE_HMR_CLIENT_PORT
  ? Number(process.env.VITE_HMR_CLIENT_PORT)
  : undefined

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    hmr: hmrClientPort ? { clientPort: hmrClientPort } : undefined,
    // Bind-mounted sources on Docker Desktop (Windows/macOS) do not emit file events.
    watch:
      process.env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: false },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Whole-screen tests (render app, type into forms) need headroom on slower machines.
    testTimeout: 15_000,
    css: false,
  },
})
