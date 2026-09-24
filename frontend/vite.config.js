import { defineConfig } from 'vite';
export default defineConfig({
  server: { host: '0.0.0.0', port: 8080, strictPort: true,
    proxy: { '/api/': { target: 'http://backend:8000', changeOrigin: false } } },
  build: { outDir: 'dist' },
});