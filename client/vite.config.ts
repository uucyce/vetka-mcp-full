import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// MARKER_175.2: Multi-target build — VETKA (full 3D) vs MCC (standalone)
const isMCC = process.env.VITE_MODE === 'mcc';

// MARKER_175.3: Dev server redirect — serve mycelium.html as default in MCC mode
// rollupOptions.input only affects build, this plugin handles dev server
function mccDevRedirect(): Plugin {
  return {
    name: 'mcc-dev-redirect',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.url === '/' || req.url === '/index.html') {
          req.url = '/mycelium.html';
        }
        next();
      });
    }
  };
}

export default defineConfig({
  plugins: [
    react(),
    ...(isMCC ? [mccDevRedirect()] : []),
  ],
  server: {
    port: isMCC ? 3002 : 3001,
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
    outDir: isMCC ? '../dist-mcc' : '../dist',
    emptyOutDir: true,
    // Phase 100.2 + MARKER_175.2: Rollup options for build splitting
    rollupOptions: {
      // MARKER_175.2: MCC build uses mycelium.html entry, VETKA uses index.html
      input: isMCC
        ? { mycelium: resolve(__dirname, 'mycelium.html') }
        : { vetka: resolve(__dirname, 'index.html') },
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
