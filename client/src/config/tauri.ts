// VETKA Tauri Detection & Bridge
// Phase 100.1: Runtime environment detection
// Phase 100.2: Dynamic imports to avoid browser errors

// NOTE: All Tauri packages are DYNAMICALLY imported inside functions
// This prevents "module not found" errors in browser mode
// TypeScript types are imported statically (stripped at compile time)

// ============================================
// Type Definitions (safe for browser - stripped at compile)
// ============================================

export interface BackendConfig {
  api_url: string;
  socket_url: string;
  is_local: boolean;
}

export interface SystemInfo {
  os: string;
  arch: string;
  tauri_version: string;
  app_version: string;
}

export interface HealthStatus {
  backend_alive: boolean;
  qdrant_alive: boolean;
  latency_ms: number;
}

export interface FileInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: number | null;
  extension: string | null;
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  encoding: string;
}

export interface HeartbeatPayload {
  timestamp: number;
  open_tasks: number;
  message: string | null;
  should_notify: boolean;
}

export interface FileChangeEvent {
  path: string;
  kind: string;
  paths: string[];
}

export interface OAuthDeepLinkEvent {
  urls: string[];
}

// ============================================
// Runtime Detection
// ============================================

/**
 * Check if running inside Tauri desktop app
 */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

// ============================================
// Dynamic Import Helpers (lazy-loaded with error handling)
// ============================================

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _invoke: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _listen: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _open: any = null;

async function getInvoke() {
  if (!isTauri()) return null;
  if (!_invoke) {
    try {
      const mod = await import('@tauri-apps/api/core');
      _invoke = mod.invoke;
    } catch (e) {
      console.warn('[Tauri] Failed to import @tauri-apps/api/core:', e);
      return null;
    }
  }
  return _invoke;
}

async function getListen() {
  if (!isTauri()) return null;
  if (!_listen) {
    try {
      const mod = await import('@tauri-apps/api/event');
      _listen = mod.listen;
    } catch (e) {
      console.warn('[Tauri] Failed to import @tauri-apps/api/event:', e);
      return null;
    }
  }
  return _listen;
}

async function getOpen() {
  if (!isTauri()) return null;
  if (!_open) {
    try {
      const mod = await import('@tauri-apps/plugin-dialog');
      _open = mod.open;
    } catch (e) {
      console.warn('[Tauri] Failed to import @tauri-apps/plugin-dialog:', e);
      return null;
    }
  }
  return _open;
}

// ============================================
// Backend Configuration
// ============================================

/**
 * Get backend configuration from Tauri
 * Falls back to defaults for browser mode
 */
export async function getBackendConfig(): Promise<BackendConfig> {
  const invoke = await getInvoke();
  if (invoke) {
    try {
      return await invoke<BackendConfig>('get_backend_url');
    } catch (e) {
      console.warn('Failed to get Tauri backend config:', e);
    }
  }

  // Browser fallback
  return {
    api_url: import.meta.env.VITE_API_BASE || '/api',
    socket_url: import.meta.env.DEV ? 'http://localhost:5001' : window.location.origin,
    is_local: true,
  };
}

/**
 * Check backend health (Tauri only - faster native check)
 */
export async function checkBackendHealth(): Promise<HealthStatus | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<HealthStatus>('check_backend_health');
  } catch (e) {
    console.warn('Backend health check failed:', e);
    return null;
  }
}

/**
 * Get system info (Tauri only)
 */
export async function getSystemInfo(): Promise<SystemInfo | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<SystemInfo>('get_system_info');
  } catch (e) {
    console.warn('Failed to get system info:', e);
    return null;
  }
}

// ============================================
// Native Dialog (Tauri only, Phase I3)
// ============================================

/**
 * Open native folder selection dialog (Tauri only)
 * Returns selected folder path or null if cancelled/browser mode
 * Phase I3: Native dialog integration
 */
export async function openFolderDialog(title: string = 'Select folder to scan'): Promise<string | null> {
  const open = await getOpen();
  if (!open) return null;

  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title
    });
    // open() returns string | string[] | null
    // With multiple: false, it returns string | null
    return selected as string | null;
  } catch (e) {
    console.warn('Native folder dialog failed:', e);
    return null;
  }
}

// MARKER_139.S1_4_WEB_LIVE_DEFAULT: Open full live web page in native Tauri WebView window
export async function openLiveWebWindow(url: string, title?: string, savePath?: string): Promise<boolean> {
  if (!url || !/^https?:\/\//i.test(url)) return false;
  const invoke = await getInvoke();
  if (!invoke) return false;

  try {
    let inferredSavePath = (savePath || '').trim();
    let savePaths: string[] = inferredSavePath ? [inferredSavePath] : [];

    // MARKER_147.WEB_SHELL_SAVE_PATHS: infer viewport node path candidates for save destination dropdown.
    try {
      const [{ useStore }, viewport] = await Promise.all([
        import('../store/useStore'),
        import('../utils/viewport'),
      ]);
      const state = useStore.getState();
      const pushPath = (p: string | undefined) => {
        const clean = String(p || '').trim();
        if (!clean || savePaths.includes(clean)) return;
        savePaths.push(clean);
      };

      // Always include obvious viewport anchors even when camera context is unavailable.
      if (state.selectedId && state.nodes[state.selectedId]) {
        pushPath(state.nodes[state.selectedId]?.path);
      }
      for (const pinnedId of state.pinnedFileIds || []) {
        pushPath(state.nodes[pinnedId]?.path);
        if (savePaths.length >= 24) break;
      }

      const camera = state.cameraRef;
      if (camera) {
        const vctx = viewport.buildViewportContext(state.nodes, state.pinnedFileIds, camera);
        const ranked = [...vctx.pinned_nodes, ...vctx.viewport_nodes]
          .filter((n: any) => n?.path && (n.type === 'file' || n.type === 'folder'))
          .sort((a: any, b: any) => {
            if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
            if (a.is_center !== b.is_center) return a.is_center ? -1 : 1;
            return (a.distance_to_camera || 0) - (b.distance_to_camera || 0);
          });
        const uniq = new Set<string>();
        for (const node of ranked) {
          const p = String(node.path || '').trim();
          if (!p || uniq.has(p)) continue;
          uniq.add(p);
          savePaths.push(p);
          if (savePaths.length >= 24) break;
        }
      }
      if (!inferredSavePath && savePaths.length > 0) {
        inferredSavePath = savePaths[0];
      }
      savePaths = savePaths.slice(0, 24);
    } catch {
      // non-fatal: keep opener-provided savePath only
    }

    // MARKER_128.9C_TAURI_INVOKE: Use Rust command for reliable native browser window creation
    const opened = await invoke('open_research_browser', {
      url,
      title: title || 'VETKA Live Web',
      save_path: inferredSavePath,
      save_paths: savePaths,
    });
    return opened === true;
  } catch (e) {
    console.warn('[Tauri] Failed to open live web window:', e);
    return false;
  }
}

// Open raw external webview (no shell) for sites that cannot render in embedded preview.
export async function openExternalWebWindow(url: string, title?: string): Promise<boolean> {
  if (!url || !/^https?:\/\//i.test(url)) return false;
  const invoke = await getInvoke();
  if (!invoke) return false;

  try {
    const opened = await invoke('open_external_webview', {
      url,
      title: title || 'VETKA External Web',
    });
    return opened === true;
  } catch (e) {
    console.warn('[Tauri] Failed to open external web window:', e);
    return false;
  }
}

// ============================================
// Native File System (Tauri only, Phase 100.2)
// ============================================

/**
 * Read file content directly via Tauri (no HTTP)
 * Falls back to null in browser mode
 */
export async function readFileNative(path: string): Promise<FileContent | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<FileContent>('read_file_native', { path });
  } catch (e) {
    console.warn('Native file read failed:', e);
    return null;
  }
}

/**
 * List directory contents (Tauri only)
 */
export async function listDirectoryNative(path: string): Promise<FileInfo[] | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<FileInfo[]>('list_directory', { path });
  } catch (e) {
    console.warn('Native directory listing failed:', e);
    return null;
  }
}

/**
 * Start watching a directory for changes (Tauri only)
 */
export async function watchDirectory(path: string): Promise<string | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<string>('watch_directory', { path });
  } catch (e) {
    console.warn('Failed to start file watcher:', e);
    return null;
  }
}

/**
 * Write file content directly via Tauri (no HTTP)
 * Phase 100.2: Native write support
 */
export async function writeFileNative(path: string, content: string): Promise<string | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<string>('write_file_native', { path, content });
  } catch (e) {
    console.warn('Native file write failed:', e);
    return null;
  }
}

/**
 * Remove file via Tauri (no HTTP)
 * Phase 100.2: Native remove support
 */
export async function removeFileNative(path: string): Promise<string | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<string>('remove_file_native', { path });
  } catch (e) {
    console.warn('Native file remove failed:', e);
    return null;
  }
}

/**
 * Handle dropped files/folders (Tauri only)
 * Phase 100.2: Native drag & drop
 */
export async function handleDropPaths(paths: string[]): Promise<FileInfo[] | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    return await invoke<FileInfo[]>('handle_drop_paths', { paths });
  } catch (e) {
    console.warn('Handle drop paths failed:', e);
    return null;
  }
}

// ============================================
// Event Listeners (Tauri only, Phase 100.2-100.3)
// ============================================

/**
 * Listen for heartbeat events from Tauri backend
 */
export async function onHeartbeat(callback: (payload: HeartbeatPayload) => void): Promise<(() => void) | null> {
  const listen = await getListen();
  if (!listen) return null;

  const unlisten = await listen<HeartbeatPayload>('heartbeat', (event) => {
    callback(event.payload);
  });
  return unlisten;
}

/**
 * Listen for file change events
 */
export async function onFileChange(callback: (event: FileChangeEvent) => void): Promise<(() => void) | null> {
  const listen = await getListen();
  if (!listen) return null;

  const unlisten = await listen<FileChangeEvent>('file-change', (event) => {
    callback(event.payload);
  });
  return unlisten;
}

/**
 * Listen for drag & drop events (files dropped on window)
 * Phase 100.2: Native drag & drop
 */
export async function onFilesDropped(callback: (paths: string[]) => void): Promise<(() => void) | null> {
  const listen = await getListen();
  if (!listen) return null;

  const unlisten = await listen<string[]>('files-dropped', (event) => {
    callback(event.payload);
  });
  return unlisten;
}

/**
 * Listen for OAuth deep-link URLs emitted by Tauri backend.
 * Event payload: { urls: string[] }
 */
export async function onOAuthDeepLink(callback: (payload: OAuthDeepLinkEvent) => void): Promise<(() => void) | null> {
  const listen = await getListen();
  if (!listen) return null;

  const unlisten = await listen('oauth-deep-link', (event: { payload?: OAuthDeepLinkEvent }) => {
    if (!event?.payload) return;
    callback(event.payload);
  });
  return unlisten;
}
