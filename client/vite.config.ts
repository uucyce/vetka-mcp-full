import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
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
    outDir: '../dist',
    emptyOutDir: true,
    // Phase 100.2: Rollup options for Tauri compatibility
    rollupOptions: {
      // External Tauri packages - resolved at runtime, not bundled
      external: process.env.TAURI_PLATFORM ? [] : [
        '@tauri-apps/api',
        '@tauri-apps/api/core',
        '@tauri-apps/api/event',
        '@tauri-apps/plugin-dialog'
      ]
    }
  },
  // Phase 100.2: Resolve Tauri packages only when available
  resolve: {
    alias: process.env.TAURI_PLATFORM ? {} : {
      // In browser mode, these imports will be handled by dynamic import guards
    }
  },
  // Phase 100.2: Optimize deps - exclude Tauri packages from pre-bundling in dev
  optimizeDeps: {
    exclude: [
      '@tauri-apps/api',
      '@tauri-apps/api/core',
      '@tauri-apps/api/event',
      '@tauri-apps/plugin-dialog'
    ]
  }
});
