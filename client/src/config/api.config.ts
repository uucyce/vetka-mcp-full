/**
 * VETKA API Configuration.
 * Unified API endpoints and WebSocket URL configuration.
 *
 * Supports:
 * - Browser mode: Vite proxy in dev, same origin in prod
 * - Tauri mode: Direct connection to FastAPI backend
 *
 * @status active
 * @phase 100.1 (Tauri migration)
 * @depends vite (import.meta.env), tauri (optional)
 * @used_by useTreeData.ts, ChatPanel.tsx, socket connections, API calls
 */

import { isTauri } from './tauri';

// Default backend URL for Tauri mode
const TAURI_BACKEND_URL = import.meta.env.VITE_TAURI_BACKEND_URL || 'http://127.0.0.1:5001';

/**
 * Check if running in Tauri desktop app
 */
export const IS_TAURI = isTauri();

/**
 * API Base URL
 * - Tauri: Direct to FastAPI (http://localhost:5001/api)
 * - Browser dev: Uses Vite proxy (/api)
 * - Browser prod: Same origin or configured
 */
export const API_BASE = (() => {
  // Tauri always uses direct connection
  if (IS_TAURI) {
    return `${TAURI_BACKEND_URL}/api`;
  }
  // Browser mode
  return import.meta.env.VITE_API_BASE || '/api';
})();

/**
 * Backend origin without /api suffix.
 * Useful for modules that need non-API routes or custom sub-path composition.
 */
export const BACKEND_ORIGIN = (() => {
  if (API_BASE.startsWith('http://') || API_BASE.startsWith('https://')) {
    return API_BASE.replace(/\/api\/?$/, '');
  }
  if (IS_TAURI) {
    return TAURI_BACKEND_URL;
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return 'http://127.0.0.1:5001';
})();

/**
 * WebSocket URL for Socket.IO
 * - Tauri: Direct WebSocket to backend
 * - Browser: Through proxy or same origin
 */
export const getSocketUrl = (): string => {
  // Explicit override
  if (import.meta.env.VITE_SOCKET_URL) {
    return import.meta.env.VITE_SOCKET_URL;
  }

  // Tauri mode - always direct connection
  if (IS_TAURI) {
    return TAURI_BACKEND_URL;
  }

  // Browser development - use backend port
  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:5001';
  }

  // Browser production - use current origin
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  return 'http://127.0.0.1:5001';
};

// Socket.IO path (relative, goes through proxy)
export const SOCKET_PATH = '/socket.io';

// Health check endpoint
export const HEALTH_ENDPOINT = `${API_BASE}/health`;

// Export environment info for debugging
export const ENV_INFO = {
  isTauri: IS_TAURI,
  isDev: import.meta.env.DEV,
  apiBase: API_BASE,
  backendOrigin: BACKEND_ORIGIN,
  socketUrl: getSocketUrl(),
};

// Log config on startup (dev only)
if (import.meta.env.DEV) {
  console.log('[VETKA Config]', ENV_INFO);
}

// Export for convenience
export default {
  API_BASE,
  BACKEND_ORIGIN,
  getSocketUrl,
  SOCKET_PATH,
  HEALTH_ENDPOINT,
  IS_TAURI,
  ENV_INFO,
};
