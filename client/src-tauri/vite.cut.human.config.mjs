import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  root: __dirname,
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 3011,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://127.0.0.1:5001',
        ws: true
      }
    }
  },
  build: {
    outDir: resolve(__dirname, '../dist-cut-human'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        cut: resolve(__dirname, 'cut.human.html')
      }
    }
  },
  optimizeDeps: {
    exclude: [
      '@tauri-apps/api',
      '@tauri-apps/api/core',
      '@tauri-apps/api/event',
      '@tauri-apps/plugin-dialog'
    ]
  }
});
