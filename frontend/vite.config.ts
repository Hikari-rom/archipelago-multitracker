/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/',
  plugins: [vue()],
  server: {
    proxy: { '/api': { target: 'http://127.0.0.1:42753', changeOrigin: false } },
  },
  test: { environment: 'happy-dom', include: ['tests/**/*.test.ts'] },
})
