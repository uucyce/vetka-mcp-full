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

export interface WebArtifactSavedEvent {
  success: boolean;
  file_path?: string;
  target_node_path?: string;
  error?: string;
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
    socket_url: import.meta.env.DEV ? 'http://127.0.0.1:5001' : window.location.origin,
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
    let savePaths: string[] = [];
    let internalFallbackPaths: string[] = [];

    // MARKER_147.WEB_SHELL_SAVE_PATHS: infer viewport node path candidates for save destination dropdown.
    try {
      const [{ useStore }, viewport] = await Promise.all([
        import('../store/useStore'),
        import('../utils/viewport'),
      ]);
      const state = useStore.getState();
      const rootPath = String((state as any).rootPath || '').trim().replace(/\\/g, '/');
      const normalizePathForSave = (pathValue: string, nodeType?: string): string => {
        const clean = String(pathValue || '').trim().replace(/\\/g, '/');
        if (!clean) return '';
        const hintedType = String(nodeType || '').toLowerCase();
        const looksLikeFileByType = hintedType === 'file';
        const looksLikeFileByExt = /\.[a-z0-9]{1,8}$/i.test(clean.split('/').pop() || '');
        if (looksLikeFileByType || looksLikeFileByExt) {
          const idx = clean.lastIndexOf('/');
          return idx > 0 ? clean.slice(0, idx) : clean;
        }
        return clean;
      };
      const isInternalWorktreePath = (pathValue: string): boolean => {
        return /\/\.claude\/worktrees\//.test(pathValue) || /\/\.playgrounds\//.test(pathValue);
      };
      const isLikelyVirtualChatPath = (pathValue: string): boolean => {
        const v = String(pathValue || '').trim();
        if (!v) return true;
        if (v.startsWith('chat_') || /^chat[_-]/i.test(v)) return true;
        if (v.startsWith('/chat_') || v.includes('/chat_')) return true;
        // UUID-like chat ids without directory separators are not filesystem paths.
        if (!v.includes('/') && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)) return true;
        return false;
      };
      const isPathEligibleForWebSave = (pathValue: string): boolean => {
        const v = String(pathValue || '').trim();
        if (!v) return false;
        if (/[\r\n\t]/.test(v)) return false;
        if (v === 'main_tree_root') return false;
        if (isLikelyVirtualChatPath(v)) return false;
        const vn = v.replace(/\\/g, '/');
        if (!vn.includes('/')) return false;
        // MARKER_148.WEB_SAVE_PATH_ROOT_GUARD: keep suggestions inside project tree when rootPath is known.
        if (rootPath && vn.startsWith('/') && !vn.startsWith(rootPath)) return false;
        if (vn === '/Users' || /^\/Users\/[^/]+$/.test(vn) || /^\/Users\/[^/]+\/Documents$/.test(vn)) return false;
        return true;
      };
      const isNodeTypeEligibleForWebSave = (nodeType: string | undefined): boolean => {
        const t = String(nodeType || '').toLowerCase();
        if (!t) return true;
        return t === 'file' || t === 'folder' || t === 'artifact';
      };
      const pushPath = (p: string | undefined, nodeType?: string) => {
        const clean = normalizePathForSave(String(p || '').trim(), nodeType);
        if (!clean) return;
        if (!isPathEligibleForWebSave(clean)) return;
        if (savePaths.includes(clean) || internalFallbackPaths.includes(clean)) return;
        // MARKER_148.WEB_SAVE_PATH_INTERNAL_FILTER: avoid defaulting to agent worktrees unless nothing else exists.
        if (isInternalWorktreePath(clean)) {
          internalFallbackPaths.push(clean);
          return;
        }
        savePaths.push(clean);
      };

      // MARKER_148.WEB_VIEWPORT_SAVE_ANCHORS: include viewport anchors even without camera context.
      if (state.selectedId && state.nodes[state.selectedId]) {
        const selectedNode = state.nodes[state.selectedId];
        if (isNodeTypeEligibleForWebSave((selectedNode as any)?.type)) {
          pushPath(selectedNode?.path, (selectedNode as any)?.type);
        }
      }
      const pinnedCandidates: string[] = [];
      for (const pinnedId of state.pinnedFileIds || []) {
        const pinnedNode = state.nodes[pinnedId];
        if (isNodeTypeEligibleForWebSave((pinnedNode as any)?.type)) {
          const normalizedPinned = normalizePathForSave(String(pinnedNode?.path || ''), (pinnedNode as any)?.type);
          if (normalizedPinned) pinnedCandidates.push(normalizedPinned);
          pushPath(pinnedNode?.path, (pinnedNode as any)?.type);
        }
        if (savePaths.length >= 24) break;
      }

      const camera = state.cameraRef;
      const viewportCandidates: string[] = [];
      if (camera) {
        try {
          camera.updateMatrixWorld?.(true);
          camera.updateProjectionMatrix?.();
        } catch {
          // non-fatal: continue with best effort context
        }
        const vctx = viewport.buildViewportContext(state.nodes, state.pinnedFileIds, camera);
        const ranked = [...vctx.pinned_nodes, ...vctx.viewport_nodes]
          // MARKER_149.WEB_VIEWPORT_PATHS_STRICT: use only concrete in-viewport file/folder/artifact nodes.
          .filter((n: any) => n?.path && isNodeTypeEligibleForWebSave(n?.type))
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
          const normalizedViewport = normalizePathForSave(p, node?.type);
          if (normalizedViewport) viewportCandidates.push(normalizedViewport);
          pushPath(p, node?.type);
          if (savePaths.length >= 24) break;
        }
      }
      // MARKER_149.WEB_SAVE_PATH_PRIORITY_IF:
      // if pinned candidates exist -> pinned first, then nearest viewport candidates.
      // else -> nearest viewport candidates only.
      const dedupeKeepOrder = (arr: string[]) => Array.from(new Set(arr.map((s) => String(s || '').trim()).filter(Boolean)));
      const prioritized = pinnedCandidates.length > 0
        ? dedupeKeepOrder([...pinnedCandidates, ...viewportCandidates])
        : dedupeKeepOrder(viewportCandidates);
      if (prioritized.length > 0) {
        const merged = dedupeKeepOrder([...prioritized, ...savePaths]);
        savePaths = merged.slice(0, 24);
      }
      if (!inferredSavePath && savePaths.length > 0) {
        inferredSavePath = savePaths[0];
      }
      if ((!inferredSavePath || isInternalWorktreePath(inferredSavePath)) && savePaths.length > 0) {
        inferredSavePath = savePaths[0];
      }
      if (!inferredSavePath) {
        if (rootPath && !isInternalWorktreePath(rootPath)) {
          inferredSavePath = rootPath;
          if (!savePaths.includes(rootPath)) savePaths.unshift(rootPath);
        }
      }
      if (savePaths.length === 0 && internalFallbackPaths.length > 0) {
        // MARKER_149.WEB_VIEWPORT_PATHS_INTERNAL_LAST: only if viewport yielded nothing.
        savePaths = internalFallbackPaths.slice(0, 12);
        inferredSavePath = inferredSavePath || savePaths[0] || '';
      }
      savePaths = savePaths.slice(0, 24);
    } catch {
      // non-fatal: keep opener-provided savePath only
    }

    // MARKER_148.WEB_DIRECT_OPEN: /web opens dedicated direct webview with save-path context.
    const opened = await invoke('open_direct_web_window', {
      url,
      title: title || 'VETKA Web',
      savePath: inferredSavePath,
      savePaths: savePaths,
    });
    if (savePaths.length === 0) {
      console.warn('[WEB] save path inference returned empty set');
    } else {
      console.log('[WEB] save path inference', {
        inferredSavePath,
        savePathsCount: savePaths.length,
        sample: savePaths.slice(0, 5),
      });
    }
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

/**
 * Listen for web artifact save completion emitted by Tauri backend.
 */
export async function onWebArtifactSaved(
  callback: (payload: WebArtifactSavedEvent) => void
): Promise<(() => void) | null> {
  const listen = await getListen();
  if (!listen) return null;

  const unlisten = await listen('vetka:web-artifact-saved', (event: { payload?: WebArtifactSavedEvent }) => {
    if (!event?.payload) return;
    callback(event.payload);
  });
  return unlisten;
}
