/**
 * Unified Scan Panel Component - Phase 92.4
 * Combines ScannerPanel + ScanProgressPanel into ONE unified panel
 *
 * @file ScanPanel.tsx
 * @status ACTIVE
 * @phase Phase 92.4 - Unified scan panel with inline path input
 * @lastUpdate 2026-01-25
 *
 * Features:
 * - Carousel source selector (Local, Cloud, Browser, Social)
 * - INLINE path input (no popup dialog!)
 * - 10px progress bar (VETKA blue)
 * - File counter: 45/156 files
 * - Scanned files list with 300ms hover preview
 * - Click file → camera navigation (fly-to)
 * - Collapsible/expandable
 * - Resizable height via drag
 * - Small trash icon for Clear All
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import './ScanPanel.css';
import { API_BASE } from '../../config/api.config';
import { isTauri, onFilesDropped, onOAuthDeepLink, handleDropPaths, openFolderDialog, openExternalWebWindow, type FileInfo as TauriFileInfo } from '../../config/tauri';

// Interfaces
interface WatchedDirectory {
  path: string;
  status: 'watching' | 'scanning' | 'error';
  filesCount?: number;
}

interface ScannedFile {
  path: string;
  timestamp: number;
  type?: 'file' | 'directory';
  size?: number;
  modified?: string;
}

interface ConnectorProvider {
  id: string;
  source: 'cloud' | 'social';
  display_name: string;
  connected: boolean;
  status?: 'connected' | 'expired' | 'error' | 'pending';
  auth_method?: 'oauth' | 'api_key' | 'basic' | 'custom';
  provider_class?: string;
  auth_flow?: string;
  capabilities?: {
    read: boolean;
    write: boolean;
    offline_access: boolean;
    webhooks: boolean;
  };
  requires_verification?: boolean;
  rate_limit_model?: string;
  rate_limit_policy?: string;
  compliance_notes?: string;
  token_policy?: string;
  token_present?: boolean;
  last_refresh_at?: string | null;
  expires_in?: number;
  account_label?: string | null;
  last_sync_at?: string | null;
  last_scan_at?: string | null;
  last_scan_count?: number;
}

interface ConnectorTreeNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  mime_type?: string;
  size?: number;
  modified?: string | null;
  children?: ConnectorTreeNode[];
}

type ConnectorAuthMethod = 'oauth' | 'api_key' | 'link';
const resolveAuthMethods = (provider: ConnectorProvider | null): ConnectorAuthMethod[] => {
  if (!provider) return ['oauth'];
  const declared = String(provider.auth_method || '').toLowerCase();
  if (declared === 'oauth' || declared === 'oauth2') return ['oauth'];
  if (declared === 'api_key') return ['api_key', 'link'];
  if (declared === 'basic') return ['link'];
  return ['oauth', 'api_key', 'link'];
};

interface ScanPanelProps {
  onFileClick: (path: string) => void;
  onFilePin?: (path: string) => void;  // Phase 92.5: Pin file to chat context
  pinnedPaths?: string[];  // Phase 92.5: Currently pinned file paths
  isVisible?: boolean;
  onEvent?: (event: ScannerEvent) => void;
}

export interface ScannerEvent {
  type: 'tab_opened' | 'directory_added' | 'directory_removed' | 'scan_complete' | 'scan_error' | 'files_dropped' | 'connector_connected' | 'connector_disconnected' | 'connector_scanned';
  path?: string;
  filesCount?: number;
  error?: string;
  fileTypes?: Record<string, number>;
}

// Source definitions for carousel
const sources = [
  { id: 'local', name: 'Local Files', available: true },
  { id: 'cloud', name: 'Cloud Storage', available: false },
  { id: 'browser', name: 'Browser History', available: false },
  { id: 'social', name: 'Social Networks', available: false },
];

// ============== SVG ICONS ==============

const FolderIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
);

const CloudIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
  </svg>
);

const GlobeIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);

const ShareIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="18" cy="5" r="3"/>
    <circle cx="6" cy="12" r="3"/>
    <circle cx="18" cy="19" r="3"/>
    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
  </svg>
);

const ChevronLeft = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);

const ChevronRight = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const FlyToIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3"/>
    <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
  </svg>
);

const FileIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
  </svg>
);

const TrashIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    <line x1="10" y1="11" x2="10" y2="17"/>
    <line x1="14" y1="11" x2="14" y2="17"/>
  </svg>
);

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);

const LoadingIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="32">
      <animate attributeName="stroke-dashoffset" values="32;0" dur="1s" repeatCount="indefinite"/>
    </circle>
  </svg>
);

// Phase I3: Browse folder icon
const BrowseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M5 19a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h9a2 2 0 0 1 2 2v1"/>
    <circle cx="17" cy="17" r="3"/>
    <path d="M21 21l-1.5-1.5"/>
  </svg>
);

// Phase 92.5: Pin icon for file context
const PinIcon = ({ filled = false }: { filled?: boolean }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
    <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
  </svg>
);

// ============== HELPERS ==============

const getSourceIcon = (id: string) => {
  switch (id) {
    case 'local': return <FolderIcon />;
    case 'cloud': return <CloudIcon />;
    case 'browser': return <GlobeIcon />;
    case 'social': return <ShareIcon />;
    default: return <FolderIcon />;
  }
};

const formatSize = (bytes?: number): string => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (date?: string): string => {
  if (!date) return '—';
  try {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  } catch {
    return '—';
  }
};

// Format scan timestamp (compact, relative)
const formatScanTime = (timestamp: number): string => {
  const now = Date.now();
  const diff = now - timestamp;

  if (diff < 5000) return 'just now';
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
};

// ============== COMPONENT ==============

export const ScanPanel: React.FC<ScanPanelProps> = ({
  onFileClick,
  onFilePin,
  pinnedPaths = [],
  isVisible = true,
  onEvent
}) => {
  // Source carousel state
  const [currentSourceIndex, setCurrentSourceIndex] = useState(0);
  const currentSource = sources[currentSourceIndex];

  // Watched directories state (kept for API status tracking)
  const [, setWatchedDirs] = useState<WatchedDirectory[]>([]);

  // Scanning state
  const [isScanning, setIsScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentFiles, setCurrentFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [scannedFiles, setScannedFiles] = useState<ScannedFile[]>([]);

  // UI state
  const [panelHeight, setPanelHeight] = useState(350);
  const [isDragging, setIsDragging] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [connectorProviders, setConnectorProviders] = useState<ConnectorProvider[]>([]);
  const [connectorsLoading, setConnectorsLoading] = useState(false);
  const [connectorBusy, setConnectorBusy] = useState<Record<string, 'connect' | 'scan' | 'disconnect' | null>>({});
  const [connectorTreeLoading, setConnectorTreeLoading] = useState<Record<string, boolean>>({});
  const [connectorTrees, setConnectorTrees] = useState<Record<string, ConnectorTreeNode[]>>({});
  const [connectorTreeModalProvider, setConnectorTreeModalProvider] = useState<ConnectorProvider | null>(null);
  const [selectedTreeIdsByProvider, setSelectedTreeIdsByProvider] = useState<Record<string, string[]>>({});
  const [secureStorageEnabled, setSecureStorageEnabled] = useState(false);
  const [connectModalProvider, setConnectModalProvider] = useState<ConnectorProvider | null>(null);
  const [connectAuthMethod, setConnectAuthMethod] = useState<ConnectorAuthMethod>('oauth');
  const [connectValue, setConnectValue] = useState('');
  const [oauthClientId, setOauthClientId] = useState('');
  const [oauthClientSecret, setOauthClientSecret] = useState('');
  const [connectSubmitting, setConnectSubmitting] = useState(false);

  // Phase 92.4: Inline path input state (no popup!)
  const [pathInput, setPathInput] = useState('');
  const [isAddingPath, setIsAddingPath] = useState(false);
  const pathInputRef = useRef<HTMLInputElement>(null);

  // Hover preview state (300ms delay like search panel)
  const [hoveredFile, setHoveredFile] = useState<ScannedFile | null>(null);
  const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 });
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Phase 100.2: Native drag & drop state
  const [isDragOver, setIsDragOver] = useState(false);

  // MARKER_136.W3A: Detected project type
  const [projectType, setProjectType] = useState<{
    type: string;
    framework: string | null;
    languages: string[];
    confidence: number;
  } | null>(null);

  // Refs for drag resize
  const panelRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef<number>(0);
  const dragStartHeight = useRef<number>(350);

  // ============== FETCH INITIAL STATUS ==============

  useEffect(() => {
    fetch(`${API_BASE}/watcher/status`)
      .then(res => res.json())
      .then(data => {
        if (data.watching) {
          setWatchedDirs(data.watching.map((path: string) => ({
            path,
            status: 'watching'
          })));
        }
      })
      .catch(() => {});
  }, []);

  // ============== PHASE 147.2: CONNECTORS (CLOUD/SOCIAL) ==============

  const loadConnectors = useCallback(async (source: 'cloud' | 'social') => {
    setConnectorsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/connectors/status?source=${encodeURIComponent(source)}`);
      const result = await response.json();
      if (response.ok && result?.success && Array.isArray(result.providers)) {
        setConnectorProviders(result.providers as ConnectorProvider[]);
        setSecureStorageEnabled(Boolean(result?.secure_storage_enabled));
      } else {
        setConnectorProviders([]);
        setSecureStorageEnabled(false);
      }
    } catch (err) {
      console.error('[ScanPanel] Failed to load connectors:', err);
      setConnectorProviders([]);
      setSecureStorageEnabled(false);
    } finally {
      setConnectorsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentSource.id === 'cloud' || currentSource.id === 'social') {
      void loadConnectors(currentSource.id as 'cloud' | 'social');
    }
  }, [currentSource.id, loadConnectors]);

  useEffect(() => {
    if (!isTauri()) return;

    let unlistenFn: (() => void) | null = null;
    const setup = async () => {
      unlistenFn = await onOAuthDeepLink(async (payload) => {
        const urls = Array.isArray(payload?.urls) ? payload.urls : [];
        const oauthUrl = urls.find((u) => String(u).startsWith('vetka://oauth/callback'));
        if (!oauthUrl) return;

        try {
          const parsed = new URL(oauthUrl);
          const authCode = parsed.searchParams.get('code') || '';
          const oauthState = parsed.searchParams.get('state') || '';
          if (!authCode || !oauthState) return;

          const response = await fetch(`${API_BASE}/connectors/oauth/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              oauth_state: oauthState,
              auth_code: authCode,
            }),
          });
          const result = await response.json();
          if (!response.ok || !result?.success) {
            throw new Error(result?.detail || result?.error || `HTTP ${response.status}`);
          }

          if (currentSource.id === 'cloud' || currentSource.id === 'social') {
            await loadConnectors(currentSource.id as 'cloud' | 'social');
          }
          onEvent?.({ type: 'connector_connected' });
        } catch (err) {
          console.error('[ScanPanel] OAuth deep-link completion failed:', err);
        }
      });
    };

    setup();
    return () => {
      unlistenFn?.();
    };
  }, [currentSource.id, loadConnectors, onEvent]);

  const runConnectorAction = useCallback(async (
    providerId: string,
    action: 'scan' | 'disconnect',
    payload?: Record<string, unknown>
  ) => {
    setConnectorBusy((prev) => ({ ...prev, [providerId]: action }));
    try {
      const endpoint = `${API_BASE}/connectors/${encodeURIComponent(providerId)}/${action}`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload ? JSON.stringify(payload) : undefined,
      });
      const result = await response.json();
      if (!response.ok || !result?.success) {
        throw new Error(result?.detail || result?.error || `HTTP ${response.status}`);
      }

      if (currentSource.id === 'cloud' || currentSource.id === 'social') {
        await loadConnectors(currentSource.id as 'cloud' | 'social');
      }
      if (action === 'scan') {
        onEvent?.({ type: 'connector_scanned', filesCount: result?.scanned_count || 0 });
      } else {
        onEvent?.({ type: 'connector_disconnected' });
      }
    } catch (err) {
      console.error(`[ScanPanel] Connector ${action} failed:`, err);
      const msg = err instanceof Error ? err.message : `${action} failed`;
      alert(`Connector ${action} failed: ${msg}`);
    } finally {
      setConnectorBusy((prev) => ({ ...prev, [providerId]: null }));
    }
  }, [currentSource.id, loadConnectors, onEvent]);

  const openConnectorTree = useCallback(async (provider: ConnectorProvider) => {
    const providerId = provider.id;
    setConnectorTreeLoading((prev) => ({ ...prev, [providerId]: true }));
    try {
      const response = await fetch(`${API_BASE}/connectors/${encodeURIComponent(providerId)}/tree`);
      const result = await response.json();
      if (!response.ok || !result?.success || !Array.isArray(result?.tree)) {
        throw new Error(result?.detail || result?.error || `HTTP ${response.status}`);
      }
      setConnectorTrees((prev) => ({ ...prev, [providerId]: result.tree as ConnectorTreeNode[] }));
      setConnectorTreeModalProvider(provider);
      setSelectedTreeIdsByProvider((prev) => ({ ...prev, [providerId]: prev[providerId] || [] }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load tree';
      alert(`Tree load failed: ${msg}`);
    } finally {
      setConnectorTreeLoading((prev) => ({ ...prev, [providerId]: false }));
    }
  }, []);

  const toggleTreeSelection = useCallback((providerId: string, nodeId: string) => {
    setSelectedTreeIdsByProvider((prev) => {
      const current = prev[providerId] || [];
      const has = current.includes(nodeId);
      const next = has ? current.filter((id) => id !== nodeId) : [...current, nodeId];
      return { ...prev, [providerId]: next };
    });
  }, []);

  const openConnectModal = useCallback((provider: ConnectorProvider) => {
    const methods = resolveAuthMethods(provider);
    setConnectModalProvider(provider);
    setConnectAuthMethod(methods[0]);
    setConnectValue('');
    setOauthClientId('');
    setOauthClientSecret('');
  }, []);

  const submitConnectModal = useCallback(async () => {
    if (!connectModalProvider || connectSubmitting) return;
    setConnectSubmitting(true);
    try {
      const providerId = connectModalProvider.id;
      if (connectAuthMethod === 'oauth') {
        const hasInlineOauthCreds = oauthClientId.trim().length > 0 || oauthClientSecret.trim().length > 0;
        if (hasInlineOauthCreds) {
          if (!oauthClientId.trim() || !oauthClientSecret.trim()) {
            throw new Error('Both Client ID and Client Secret are required');
          }
          const credsResp = await fetch(`${API_BASE}/connectors/${encodeURIComponent(providerId)}/oauth/credentials`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              client_id: oauthClientId.trim(),
              client_secret: oauthClientSecret.trim(),
            }),
          });
          const credsData = await credsResp.json();
          if (!credsResp.ok || !credsData?.success) {
            throw new Error(credsData?.detail || credsData?.error || `HTTP ${credsResp.status}`);
          }
        }

        // MARKER_147_5_SCANPANEL_OAUTH_HANDOFF: start OAuth and open real provider URL, no local auto-complete.
        const startResp = await fetch(`${API_BASE}/connectors/${encodeURIComponent(providerId)}/oauth/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isTauri() && connectModalProvider.provider_class !== 'google'
              ? { redirect_uri: 'vetka://oauth/callback' }
              : {}
          ),
        });
        const startData = await startResp.json();
        if (!startResp.ok || !startData?.success || !startData?.auth_url) {
          throw new Error(startData?.detail || startData?.error || `HTTP ${startResp.status}`);
        }

        const authUrl = String(startData.auth_url);
        if (isTauri()) {
          await openExternalWebWindow(authUrl, `Connect ${connectModalProvider.display_name}`);
        } else {
          window.open(authUrl, '_blank', 'noopener,noreferrer');
        }

        // MARKER_147_5_SCANPANEL_OAUTH_POLL: background status poll after browser callback.
        // Close modal immediately and poll backend status while user completes OAuth in browser.
        setConnectModalProvider(null);
        setConnectValue('');
        setOauthClientId('');
        setOauthClientSecret('');

        const pollUntil = Date.now() + 180000;
        const poll = async () => {
          if (Date.now() > pollUntil) return;
          try {
            const response = await fetch(`${API_BASE}/connectors/status?source=${encodeURIComponent(currentSource.id)}`);
            const result = await response.json();
            const provider = Array.isArray(result?.providers)
              ? (result.providers as ConnectorProvider[]).find((p) => p.id === providerId)
              : null;
            if (provider?.connected && provider?.token_present) {
              await loadConnectors(currentSource.id as 'cloud' | 'social');
              onEvent?.({ type: 'connector_connected' });
              return;
            }
          } catch {
            // keep polling
          }
          setTimeout(() => {
            void poll();
          }, 2000);
        };
        setTimeout(() => {
          void poll();
        }, 1500);
        return;
      } else {
        const manualResp = await fetch(`${API_BASE}/connectors/${encodeURIComponent(providerId)}/auth/manual`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            auth_type: connectAuthMethod,
            value: connectValue.trim(),
            account_label: providerId,
          }),
        });
        const manualData = await manualResp.json();
        if (!manualResp.ok || !manualData?.success) {
          throw new Error(manualData?.detail || manualData?.error || `HTTP ${manualResp.status}`);
        }
      }

      if (currentSource.id === 'cloud' || currentSource.id === 'social') {
        await loadConnectors(currentSource.id as 'cloud' | 'social');
      }
      onEvent?.({ type: 'connector_connected' });
      setConnectModalProvider(null);
      setConnectValue('');
    } catch (err) {
      console.error('[ScanPanel] Connector auth failed:', err);
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Connector auth failed: ${msg}`);
    } finally {
      setConnectSubmitting(false);
    }
  }, [
    connectModalProvider,
    connectSubmitting,
    connectAuthMethod,
    connectValue,
    oauthClientId,
    oauthClientSecret,
    currentSource.id,
    loadConnectors,
    onEvent
  ]);

  // ============== PHASE 100.2: NATIVE DRAG & DROP ==============

  useEffect(() => {
    if (!isTauri()) return;

    let unlistenFn: (() => void) | null = null;

    // Subscribe to Tauri's native file drop events (async setup)
    const setupListener = async () => {
      unlistenFn = await onFilesDropped(async (paths: string[]) => {
      console.log('[ScanPanel] Phase 100.2: Native files dropped:', paths);

      // Process dropped paths via Tauri
      const fileInfos = await handleDropPaths(paths);

      if (fileInfos && fileInfos.length > 0) {
        // Find directories among dropped items
        const directories = fileInfos.filter((f: TauriFileInfo) => f.is_dir);
        const files = fileInfos.filter((f: TauriFileInfo) => !f.is_dir);

        // Add directories to watcher
        for (const dir of directories) {
          try {
            const response = await fetch(`${API_BASE}/watcher/add`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ path: dir.path, recursive: true })
            });

            if (response.ok) {
              const result = await response.json();
              console.log('[ScanPanel] Added dropped directory:', dir.path, result);
              onEvent?.({
                type: 'directory_added',
                path: dir.path,
                filesCount: result.indexed_count || result.files_count || 0
              });
            }
          } catch (err) {
            console.error('[ScanPanel] Error adding dropped directory:', err);
          }
        }

        // Add individual files to scanned list
        const newFiles: ScannedFile[] = files.map((f: TauriFileInfo) => ({
          path: f.path,
          timestamp: Date.now(),
          type: 'file' as const,
          size: f.size,
          modified: f.modified ? new Date(f.modified * 1000).toISOString() : undefined
        }));

        if (newFiles.length > 0) {
          setScannedFiles(prev => [...newFiles, ...prev].slice(0, 20));
        }

        onEvent?.({
          type: 'files_dropped',
          filesCount: fileInfos.length
        });

        // Refresh watcher status
        fetch(`${API_BASE}/watcher/status`)
          .then(res => res.json())
          .then(data => {
            if (data.watching) {
              setWatchedDirs(data.watching.map((path: string) => ({
                path,
                status: 'watching'
              })));
            }
          })
          .catch(() => {});
      }

      setIsDragOver(false);
    });
    };

    setupListener();

    return () => {
      unlistenFn?.();
    };
  }, [onEvent]);

  // ============== SOCKET EVENT LISTENERS ==============

  useEffect(() => {
    const handleScanProgress = (event: CustomEvent<{
      progress: number;
      status?: string;
      file_path?: string;
      current?: number;
      total?: number;
      file_size?: number;
      file_mtime?: number;
    }>) => {
      const detail = event.detail;
      setProgress(detail.progress || 0);
      setIsScanning(true);

      if (detail.current !== undefined) setCurrentFiles(detail.current);
      if (detail.total !== undefined) setTotalFiles(detail.total);

      if (detail.file_path) {
        setScannedFiles(prev => {
          const newFile: ScannedFile = {
            path: detail.file_path!,
            timestamp: Date.now(),
            type: 'file',
            size: detail.file_size,
            modified: detail.file_mtime ? new Date(detail.file_mtime * 1000).toISOString() : undefined
          };
          const filtered = prev.filter(f => f.path !== detail.file_path);
          return [newFile, ...filtered].slice(0, 20);
        });
      }
    };

    const handleScanComplete = (event: CustomEvent<{ filesCount?: number; nodes_count?: number }>) => {
      setIsScanning(false);
      setProgress(100);
      const count = event.detail?.filesCount || event.detail?.nodes_count || 0;
      setTotalFiles(count);
      setCurrentFiles(count);
      onEvent?.({ type: 'scan_complete', filesCount: count });

      // Refresh watched dirs
      fetch(`${API_BASE}/watcher/status`)
        .then(res => res.json())
        .then(data => {
          if (data.watching) {
            setWatchedDirs(data.watching.map((path: string) => ({
              path,
              status: 'watching'
            })));
          }
        })
        .catch(() => {});

      // Phase 92.5: Only reset progress bar after 5 seconds
      // Keep scanned files visible so user can click to fly-to!
      setTimeout(() => {
        setProgress(0);
        // DON'T clear scannedFiles - user needs them for camera navigation!
        // setScannedFiles([]);
        // DON'T reset totalFiles - shows "44 files" as summary
        // setTotalFiles(0);
        // setCurrentFiles(0);
      }, 5000);
    };

    const handleDirectoryScanned = (event: CustomEvent<{ path: string; files_count?: number }>) => {
      if (event.detail.path) {
        setScannedFiles(prev => {
          const newFile: ScannedFile = {
            path: event.detail.path,
            timestamp: Date.now(),
            type: 'directory'
          };
          const filtered = prev.filter(f => f.path !== event.detail.path);
          return [newFile, ...filtered].slice(0, 20);
        });
      }
    };

    window.addEventListener('scan_progress', handleScanProgress as EventListener);
    window.addEventListener('scan_complete', handleScanComplete as EventListener);
    window.addEventListener('directory_scanned', handleDirectoryScanned as EventListener);

    return () => {
      window.removeEventListener('scan_progress', handleScanProgress as EventListener);
      window.removeEventListener('scan_complete', handleScanComplete as EventListener);
      window.removeEventListener('directory_scanned', handleDirectoryScanned as EventListener);
    };
  }, [onEvent]);

  // ============== CAROUSEL NAVIGATION ==============

  const prevSource = () => setCurrentSourceIndex(i => (i - 1 + sources.length) % sources.length);
  const nextSource = () => setCurrentSourceIndex(i => (i + 1) % sources.length);

  // ============== ADD FOLDER (INLINE INPUT) ==============

  const handleAddFolder = useCallback(async () => {
    const fullPath = pathInput.trim();
    if (!fullPath) {
      pathInputRef.current?.focus();
      return;
    }

    setIsAddingPath(true);

    try {
      const response = await fetch(`${API_BASE}/watcher/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fullPath, recursive: true })
      });

      if (response.ok) {
        const result = await response.json();

        // MARKER_136.W3A: Store detected project type
        if (result.project_type) {
          setProjectType(result.project_type);
        }

        // Refresh watched dirs
        const statusResponse = await fetch(`${API_BASE}/watcher/status`);
        const data = await statusResponse.json();
        if (data.watching) {
          setWatchedDirs(data.watching.map((path: string) => ({
            path,
            status: 'watching'
          })));
        }

        onEvent?.({
          type: 'directory_added',
          path: fullPath,
          filesCount: result.indexed_count || result.files_count || 0
        });

        // Clear input on success
        setPathInput('');
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to add folder'}`);
      }
    } catch (err) {
      console.error('[ScanPanel] Error adding folder:', err);
      alert('Failed to add folder. Check console for details.');
    } finally {
      setIsAddingPath(false);
    }
  }, [pathInput, onEvent]);

  const handlePathKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddFolder();
    }
  }, [handleAddFolder]);

  // ============== PHASE I3: NATIVE BROWSE DIALOG ==============

  const handleBrowseFolder = useCallback(async () => {
    // Only works in Tauri mode
    const selectedPath = await openFolderDialog('Select folder to scan');

    if (selectedPath) {
      // Set path in input and trigger scan
      setPathInput(selectedPath);

      // Auto-trigger scan after selection
      setIsAddingPath(true);

      try {
        const response = await fetch(`${API_BASE}/watcher/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: selectedPath, recursive: true })
        });

        if (response.ok) {
          const result = await response.json();

          // MARKER_136.W3A: Store detected project type
          if (result.project_type) {
            setProjectType(result.project_type);
          }

          // Refresh watched dirs
          const statusResponse = await fetch(`${API_BASE}/watcher/status`);
          const data = await statusResponse.json();
          if (data.watching) {
            setWatchedDirs(data.watching.map((path: string) => ({
              path,
              status: 'watching'
            })));
          }

          onEvent?.({
            type: 'directory_added',
            path: selectedPath,
            filesCount: result.indexed_count || result.files_count || 0
          });

          // Clear input on success
          setPathInput('');
        } else {
          const error = await response.json();
          alert(`Error: ${error.detail || 'Failed to add folder'}`);
        }
      } catch (err) {
        console.error('[ScanPanel] Error adding folder from browse:', err);
        alert('Failed to add folder. Check console for details.');
      } finally {
        setIsAddingPath(false);
      }
    }
  }, [onEvent]);

  // ============== CLEAR ALL SCANS ==============

  // FIX_96.4: Updated to show both Qdrant and Weaviate clearing
  const handleClearAll = useCallback(async () => {
    const confirmed = window.confirm(
      'Are you sure you want to clear ALL indexed files?\n\n' +
      'This will delete scan data from:\n' +
      '• Qdrant (vector embeddings)\n' +
      '• Weaviate (keyword search)\n\n' +
      'Chat history will be preserved.\n' +
      'You will need to re-scan folders to rebuild the index.'
    );

    if (!confirmed) return;

    setIsClearing(true);

    try {
      const response = await fetch(`${API_BASE}/scanner/clear-all`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setWatchedDirs([]);
        setScannedFiles([]);
        setProgress(0);
        setTotalFiles(0);
        setCurrentFiles(0);
        // FIX_96.4: Show detailed clear result
        const qdrantMsg = result.qdrant_cleared ? `✅ Qdrant: ${result.qdrant_count || 0}` : '❌ Qdrant: failed';
        const weaviateMsg = result.weaviate_cleared ? `✅ Weaviate: ${result.weaviate_count || 0}` : '❌ Weaviate: failed';
        alert(`Cleared indexed files:\n${qdrantMsg}\n${weaviateMsg}`);
        onEvent?.({ type: 'scan_complete', filesCount: 0 });
      } else {
        alert(`Error: ${result.detail || 'Failed to clear scans'}`);
      }
    } catch (err) {
      console.error('[ScanPanel] Error clearing scans:', err);
      alert('Failed to clear scans. Check console for details.');
    } finally {
      setIsClearing(false);
    }
  }, [onEvent]);

  // ============== RESIZE HANDLERS ==============

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartY.current = e.clientY;
    dragStartHeight.current = panelHeight;
  }, [panelHeight]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaY = e.clientY - dragStartY.current;
      const newHeight = Math.min(
        Math.max(dragStartHeight.current + deltaY, 150),
        window.innerHeight * 0.7
      );
      setPanelHeight(newHeight);
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  // ============== HOVER PREVIEW (300ms) ==============

  const handleFileMouseEnter = useCallback((file: ScannedFile, e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);

    hoverTimerRef.current = setTimeout(() => {
      setHoveredFile(file);
      setPreviewPosition({
        x: Math.min(rect.right + 8, window.innerWidth - 360),
        y: Math.min(rect.top, window.innerHeight - 200)
      });
    }, 300);
  }, []);

  const handleFileMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    setHoveredFile(null);
  }, []);

  const handleFileClick = useCallback((path: string) => {
    console.log('[ScanPanel] Phase 92.5: File clicked for fly-to:', path);
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    setHoveredFile(null);
    onFileClick(path);
  }, [onFileClick]);

  // Phase 92.5: Handle file pin
  const handleFilePin = useCallback((e: React.MouseEvent, path: string) => {
    e.stopPropagation();  // Don't trigger fly-to
    console.log('[ScanPanel] Phase 92.5: File pinned to context:', path);
    onFilePin?.(path);
  }, [onFilePin]);

  // Phase 92.5: Check if file is pinned
  const isFilePinned = useCallback((path: string): boolean => {
    return pinnedPaths.includes(path);
  }, [pinnedPaths]);

  // ============== PHASE 100.2: BROWSER DRAG & DROP FALLBACK ==============

  const handleBrowserDragOver = useCallback((e: React.DragEvent) => {
    if (isTauri()) return; // Native Tauri handles this
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleBrowserDragLeave = useCallback((e: React.DragEvent) => {
    if (isTauri()) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleBrowserDrop = useCallback(async (e: React.DragEvent) => {
    if (isTauri()) return; // Native Tauri handles this
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const items = e.dataTransfer.items;
    if (!items) return;

    // Browser File System Access API fallback
    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry?.();
        if (entry?.isDirectory) {
          // Can't get real path in browser, show hint
          alert('Browser mode: Use the path input to add folders.\nFor native drag & drop, run VETKA as desktop app.');
        }
      }
    }
  }, []);

  // ============== UI HELPERS ==============

  const getFileName = (path: string): string => {
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
  };

  const renderConnectorTree = (providerId: string, nodes: ConnectorTreeNode[], depth = 0): React.ReactNode => {
    const selectedIds = selectedTreeIdsByProvider[providerId] || [];
    return nodes.map((node) => {
      const checked = selectedIds.includes(node.id);
      return (
        <div key={`${providerId}-${node.id}`} className="connector-tree-row" style={{ paddingLeft: `${12 + depth * 16}px` }}>
          <label className="connector-tree-label">
            <input
              type="checkbox"
              checked={checked}
              onChange={() => toggleTreeSelection(providerId, node.id)}
            />
            <span className={`connector-tree-type ${node.type}`}>{node.type === 'folder' ? 'DIR' : 'FILE'}</span>
            <span className="connector-tree-name" title={node.path}>{node.name}</span>
          </label>
          {Array.isArray(node.children) && node.children.length > 0 ? (
            <div className="connector-tree-children">
              {renderConnectorTree(providerId, node.children, depth + 1)}
            </div>
          ) : null}
        </div>
      );
    });
  };

  // ============== RENDER ==============

  if (!isVisible) return null;

  return (
    <div
      ref={panelRef}
      className={`scan-panel ${isScanning ? 'scanning' : ''} ${isDragOver ? 'drag-over' : ''}`}
      style={{ height: `${panelHeight}px` }}
      onDragOver={handleBrowserDragOver}
      onDragLeave={handleBrowserDragLeave}
      onDrop={handleBrowserDrop}
    >
      {/* ===== HEADER: Source Carousel + Stats + Collapse ===== */}
      <div className="scan-panel-header">
        {/* Source carousel */}
        <div className="source-carousel-mini">
          <button className="carousel-btn-mini" onClick={prevSource}>
            <ChevronLeft />
          </button>
          <div className="source-display-mini">
            <span className="source-icon-mini">{getSourceIcon(currentSource.id)}</span>
            <span className="source-name-mini">{currentSource.name}</span>
          </div>
          <button className="carousel-btn-mini" onClick={nextSource}>
            <ChevronRight />
          </button>
        </div>

        {/* Stats & controls */}
        <div className="scan-panel-controls">
          {/* Phase 92.9: Show progress during scan, show total after */}
          {isScanning && (
            <span className="scan-stats">
              {currentFiles}/{totalFiles}
            </span>
          )}
          {!isScanning && totalFiles > 0 && (
            <span className="scan-stats complete">
              {totalFiles} files
            </span>
          )}

          {/* Clear All button (small trash icon) */}
          <button
            className={`clear-btn ${isClearing ? 'clearing' : ''}`}
            onClick={handleClearAll}
            disabled={isClearing}
            title={isClearing ? 'Clearing...' : 'Clear All Scans'}
          >
            {isClearing ? <LoadingIcon /> : <TrashIcon />}
          </button>
          {/* Phase 92.9: Removed collapse button - panel always expanded */}
        </div>
      </div>

      {/* ===== PROGRESS BAR (10px) ===== */}
      {(isScanning || progress > 0) && (
        <div className="scan-progress-bar">
          <div
            className={`scan-progress-fill ${isScanning && progress === 0 ? 'indeterminate' : ''}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* MARKER_136.W3A: Project Type Badge */}
      {projectType && projectType.type !== 'unknown' && (
        <div className="project-type-badge" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 12px',
          background: 'rgba(255, 255, 255, 0.03)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: 11,
          fontFamily: 'monospace',
        }}>
          <span style={{ color: '#888', fontSize: 9, textTransform: 'uppercase', letterSpacing: 1 }}>
            detected:
          </span>
          <span style={{
            color: '#fff',
            fontWeight: 500,
            padding: '2px 8px',
            background: 'rgba(255, 255, 255, 0.08)',
            borderRadius: 3,
          }}>
            {projectType.framework || projectType.type}
          </span>
          {projectType.languages.length > 0 && (
            <span style={{ color: '#666', fontSize: 10 }}>
              {projectType.languages.slice(0, 3).join(' · ')}
            </span>
          )}
          {projectType.confidence > 0.7 && (
            <span style={{
              color: '#555',
              fontSize: 9,
              marginLeft: 'auto',
            }}>
              {Math.round(projectType.confidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* ===== CONTENT ===== */}
      <div className="scan-panel-content">
          {/* Local Files source content */}
          {currentSource.id === 'local' ? (
            <>
              {/* Phase 100.2: Tauri = Browse button only, Browser = path input */}
              <div className="path-input-row">
                {isTauri() ? (
                  /* Phase I6: Tauri mode - single Browse button, no path input */
                  <button
                    className="browse-folder-btn-full"
                    onClick={handleBrowseFolder}
                    disabled={isAddingPath}
                    title="Select folder to scan"
                  >
                    {isAddingPath ? <LoadingIcon /> : <BrowseIcon />}
                    <span className="browse-label">Select Folder</span>
                  </button>
                ) : (
                  /* Browser fallback - path input + add button */
                  <>
                    <input
                      ref={pathInputRef}
                      type="text"
                      className="path-input"
                      placeholder="/path/to/folder"
                      value={pathInput}
                      onChange={(e) => setPathInput(e.target.value)}
                      onKeyDown={handlePathKeyDown}
                      disabled={isAddingPath}
                    />
                    <button
                      className={`add-folder-btn ${isAddingPath ? 'adding' : ''}`}
                      onClick={handleAddFolder}
                      disabled={isAddingPath || !pathInput.trim()}
                      title="Add folder to scan"
                    >
                      {isAddingPath ? <LoadingIcon /> : <PlusIcon />}
                    </button>
                  </>
                )}
              </div>

              {/* Scanned files list */}
              {scannedFiles.length > 0 ? (
                <div className="scanned-files-section">
                  <div className="scanned-files-label">
                    Recently scanned — Click to fly, Pin to context
                  </div>
                  <ul className="scanned-files-list">
                    {scannedFiles.map((file) => {
                      const pinned = isFilePinned(file.path);
                      return (
                        <li
                          key={`${file.path}-${file.timestamp}`}
                          className={`scanned-file-item ${pinned ? 'pinned' : ''}`}
                          onClick={() => handleFileClick(file.path)}
                          onMouseEnter={(e) => handleFileMouseEnter(file, e)}
                          onMouseLeave={handleFileMouseLeave}
                          title={file.path}
                        >
                          <span className="check-icon">
                            <CheckIcon />
                          </span>
                          <span className="file-name">{getFileName(file.path)}</span>
                          <span className="file-meta">
                            {file.size ? formatSize(file.size) : ''}
                            {file.size ? ' · ' : ''}
                            {formatScanTime(file.timestamp)}
                          </span>
                          {/* Phase 92.5: Pin button */}
                          {onFilePin && (
                            <button
                              className={`pin-btn ${pinned ? 'pinned' : ''}`}
                              onClick={(e) => handleFilePin(e, file.path)}
                              title={pinned ? 'Unpin from context' : 'Pin to context'}
                            >
                              <PinIcon filled={pinned} />
                            </button>
                          )}
                          <span className="fly-indicator">
                            <FlyToIcon />
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : (
                /* Empty state - no scanned files yet */
                <div className="empty-scan-state">
                  <div className="empty-scan-text">No recently scanned files</div>
                  <div className="empty-scan-hint">Files will appear here during scanning</div>
                </div>
              )}
            </>
          ) : (currentSource.id === 'cloud' || currentSource.id === 'social') ? (
            <div className="connectors-panel">
              <div className="connectors-header">
                Connect accounts and run scan into VETKA
                <span className={`connectors-secure ${secureStorageEnabled ? 'on' : 'off'}`}>
                  {secureStorageEnabled ? 'secure store: on' : 'secure store: fallback'}
                </span>
              </div>
              {connectorsLoading ? (
                <div className="connectors-loading">
                  <LoadingIcon />
                  <span>Loading connectors...</span>
                </div>
              ) : connectorProviders.length === 0 ? (
                <div className="coming-soon-panel">
                  <div className="coming-soon-text">No providers configured</div>
                  <div className="coming-soon-hint">Check backend connector defaults</div>
                </div>
              ) : (
                <div className="connectors-list">
                  {connectorProviders.map((provider) => {
                    const busyAction = connectorBusy[provider.id];
                    const isBusy = Boolean(busyAction);
                    const isConnected = provider.connected && (provider.status || 'pending') === 'connected';
                    const needsAuth = !isConnected || !provider.token_present;
                    const isGoogleDrive = provider.id === 'google_drive' || provider.provider_class === 'google';
                    const selectedIds = selectedTreeIdsByProvider[provider.id] || [];
                    return (
                      <div key={provider.id} className="connector-card">
                        <div className="connector-meta">
                          <div className="connector-name">{provider.display_name}</div>
                          <div className="connector-sub">
                            <span className={`connector-status ${isConnected ? 'connected' : 'disconnected'}`}>
                              {(provider.status || (provider.connected ? 'connected' : 'pending')).toUpperCase()}
                            </span>
                            {provider.connected ? (
                              <span className="connector-token">
                                {provider.token_present ? 'token: saved' : 'token: missing'}
                              </span>
                            ) : null}
                            {provider.last_scan_count ? (
                              <span className="connector-last">
                                {provider.last_scan_count} items
                              </span>
                            ) : null}
                            {provider.last_refresh_at ? (
                              <span className="connector-refresh">
                                refreshed {new Date(provider.last_refresh_at).toLocaleDateString()}
                              </span>
                            ) : null}
                            {provider.requires_verification ? (
                              <span className="connector-policy">review required</span>
                            ) : null}
                          </div>
                        </div>
                        <div className="connector-actions">
                          {needsAuth ? (
                            <button
                              className="connector-btn"
                              disabled={isBusy}
                              onClick={() => openConnectModal(provider)}
                              title={`Authorize ${provider.display_name}`}
                            >
                              Auth
                            </button>
                          ) : (
                            <>
                              {isGoogleDrive && (
                                <button
                                  className="connector-btn ghost"
                                  disabled={isBusy || Boolean(connectorTreeLoading[provider.id])}
                                  onClick={() => void openConnectorTree(provider)}
                                  title="Browse Google Drive tree"
                                >
                                  {connectorTreeLoading[provider.id] ? 'Loading...' : 'Browse'}
                                </button>
                              )}
                              <button
                                className="connector-btn"
                                disabled={isBusy}
                                onClick={() =>
                                  void runConnectorAction(
                                    provider.id,
                                    'scan',
                                    isGoogleDrive
                                      ? { selected_ids: selectedIds }
                                      : undefined
                                  )
                                }
                                title={`Scan ${provider.display_name}`}
                              >
                                {busyAction === 'scan' ? 'Scanning...' : 'Scan'}
                              </button>
                              <button
                                className="connector-btn ghost"
                                disabled={isBusy}
                                onClick={() => void runConnectorAction(provider.id, 'disconnect')}
                                title={`Disconnect ${provider.display_name}`}
                              >
                                {busyAction === 'disconnect' ? 'Disconnecting...' : 'Disconnect'}
                              </button>
                            </>
                          )}
                        </div>
                        {provider.capabilities ? (
                          <div className="connector-capabilities">
                            {provider.capabilities.offline_access && <span>Offline</span>}
                            {provider.capabilities.webhooks && <span>Webhooks</span>}
                            {isGoogleDrive && selectedIds.length > 0 && <span>{selectedIds.length} selected</span>}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Coming soon panel for other sources */
            <div className="coming-soon-panel">
              <div className="coming-soon-text">Coming soon</div>
              <div className="coming-soon-hint">
                {currentSource.id === 'cloud' && 'Connect Google Drive, Dropbox, iCloud...'}
                {currentSource.id === 'browser' && 'Import bookmarks and history'}
                {currentSource.id === 'social' && 'Link Twitter, LinkedIn, GitHub...'}
              </div>
            </div>
          )}
        </div>

      {connectModalProvider && (
        <div className="connector-modal-overlay" onClick={() => !connectSubmitting && setConnectModalProvider(null)}>
          <div className="connector-modal" onClick={(e) => e.stopPropagation()}>
            <div className="connector-modal-title">
              Connect {connectModalProvider.display_name}
            </div>
            {(() => {
              const allowedMethods = resolveAuthMethods(connectModalProvider);
              return (
                <>
            <div className="connector-methods">
              {allowedMethods.includes('oauth') && (
                <button
                  className={`connector-method-btn ${connectAuthMethod === 'oauth' ? 'active' : ''}`}
                  onClick={() => setConnectAuthMethod('oauth')}
                  disabled={connectSubmitting}
                >
                  OAuth
                </button>
              )}
              {allowedMethods.includes('api_key') && (
                <button
                  className={`connector-method-btn ${connectAuthMethod === 'api_key' ? 'active' : ''}`}
                  onClick={() => setConnectAuthMethod('api_key')}
                  disabled={connectSubmitting}
                >
                  API key
                </button>
              )}
              {allowedMethods.includes('link') && (
                <button
                  className={`connector-method-btn ${connectAuthMethod === 'link' ? 'active' : ''}`}
                  onClick={() => setConnectAuthMethod('link')}
                  disabled={connectSubmitting}
                >
                  Link
                </button>
              )}
            </div>
            {allowedMethods.length === 1 && allowedMethods[0] === 'oauth' && (
              <div className="connector-sub" style={{ marginTop: 10 }}>
                Paste Client ID / Client Secret once (optional). They are stored securely for OAuth start.
              </div>
            )}
            {connectAuthMethod === 'oauth' && (
              <>
                <input
                  className="connector-auth-input"
                  style={{ marginTop: 10 }}
                  value={oauthClientId}
                  onChange={(e) => setOauthClientId(e.target.value)}
                  placeholder="Client ID (optional)"
                  disabled={connectSubmitting}
                />
                <input
                  className="connector-auth-input"
                  value={oauthClientSecret}
                  onChange={(e) => setOauthClientSecret(e.target.value)}
                  placeholder="Client secret (optional)"
                  disabled={connectSubmitting}
                />
              </>
            )}
            {connectAuthMethod !== 'oauth' && (
              <input
                className="connector-auth-input"
                value={connectValue}
                onChange={(e) => setConnectValue(e.target.value)}
                placeholder={connectAuthMethod === 'api_key' ? 'Paste API key' : 'Paste auth link/token'}
                disabled={connectSubmitting}
              />
            )}
            <div className="connector-modal-actions">
              <button
                className="connector-btn ghost"
                onClick={() => setConnectModalProvider(null)}
                disabled={connectSubmitting}
              >
                Cancel
              </button>
              <button
                className="connector-btn"
                onClick={() => void submitConnectModal()}
                disabled={connectSubmitting || (connectAuthMethod !== 'oauth' && !connectValue.trim())}
              >
                {connectSubmitting ? 'Authorizing...' : 'Continue'}
              </button>
            </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

      {connectorTreeModalProvider && (
        <div className="connector-modal-overlay" onClick={() => setConnectorTreeModalProvider(null)}>
          <div className="connector-modal connector-tree-modal" onClick={(e) => e.stopPropagation()}>
            <div className="connector-modal-title">
              {connectorTreeModalProvider.display_name} — Select folders/files to scan
            </div>
            <div className="connector-tree-list">
              {connectorTrees[connectorTreeModalProvider.id]?.length
                ? renderConnectorTree(connectorTreeModalProvider.id, connectorTrees[connectorTreeModalProvider.id])
                : <div className="connector-sub">No files found or access is limited.</div>}
            </div>
            <div className="connector-modal-actions">
              <button
                className="connector-btn ghost"
                onClick={() => setConnectorTreeModalProvider(null)}
              >
                Close
              </button>
              <button
                className="connector-btn"
                onClick={() => {
                  setConnectorTreeModalProvider(null);
                }}
              >
                Use Selection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== RESIZE HANDLE (at bottom) ===== */}
      <div
        className={`scan-resize-handle ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleDragStart}
      />

      {/* ===== HOVER PREVIEW POPUP ===== */}
      {hoveredFile && (
        <div
          className="file-preview-popup"
          style={{
            left: previewPosition.x,
            top: previewPosition.y
          }}
        >
          <div className="preview-header">
            <span className="preview-icon"><FileIcon /></span>
            <span className="preview-name">{getFileName(hoveredFile.path)}</span>
          </div>
          <div className="preview-meta">
            <span>{hoveredFile.type === 'directory' ? 'Directory' : 'File'}</span>
            <span>{formatSize(hoveredFile.size)}</span>
            <span>{formatDate(hoveredFile.modified)}</span>
          </div>
          <div className="preview-path">{hoveredFile.path}</div>
        </div>
      )}
    </div>
  );
};

export default ScanPanel;
