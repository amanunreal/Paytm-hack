import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // 127.0.0.1, not localhost: uvicorn listens on IPv4 and Node may try ::1 first.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
