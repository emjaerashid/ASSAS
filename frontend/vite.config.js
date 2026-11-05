import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Forward backend paths to Django so the dev app is same-origin, exactly
    // like production (where Django serves the built app itself).
    proxy: Object.fromEntries(
      ['/api', '/media', '/static', '/django-admin'].map((path) => [path, 'http://127.0.0.1:8000']),
    ),
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
  },
})
