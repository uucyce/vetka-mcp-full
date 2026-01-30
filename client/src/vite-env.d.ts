/**
 * Vite environment type declarations.
 * Provides TypeScript types for Vite client features.
 *
 * @status active
 * @phase 100.1 (Tauri migration)
 * @depends vite/client
 * @used_by TypeScript compiler
 */

/// <reference types="vite/client" />

// Tauri global type declaration
declare global {
  interface Window {
    __TAURI__?: {
      invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
      event: {
        listen: <T>(event: string, handler: (event: { payload: T }) => void) => Promise<() => void>;
        emit: (event: string, payload?: unknown) => Promise<void>;
      };
    };
  }
}

// Environment variables
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_SOCKET_URL?: string;
  readonly VITE_TAURI_BACKEND_URL?: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

export {};
