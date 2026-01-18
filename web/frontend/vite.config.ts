import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Define environment variables with defaults
  // VITE_DEMO_MODE_DEFAULT: 'true' for local dev, 'false' in production (set in Dockerfile)
  define: {
    'import.meta.env.VITE_DEMO_MODE_DEFAULT': JSON.stringify(
      process.env.VITE_DEMO_MODE_DEFAULT ?? 'true'
    ),
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
