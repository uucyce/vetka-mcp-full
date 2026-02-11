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
import { isTauri, onFilesDropped, handleDropPaths, openFolderDialog, type FileInfo as TauriFileInfo } from '../../config/tauri';

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

interface ScanPanelProps {
  onFileClick: (path: string) => void;
  onFilePin?: (path: string) => void;  // Phase 92.5: Pin file to chat context
  pinnedPaths?: string[];  // Phase 92.5: Currently pinned file paths
  isVisible?: boolean;
  onEvent?: (event: ScannerEvent) => void;
}

export interface ScannerEvent {
  type: 'tab_opened' | 'directory_added' | 'directory_removed' | 'scan_complete' | 'scan_error' | 'files_dropped';
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

const ChevronDown = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);

const ChevronUp = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="18 15 12 9 6 15"/>
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
  const [isExpanded, setIsExpanded] = useState(true);
  const [panelHeight, setPanelHeight] = useState(350);
  const [isDragging, setIsDragging] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

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

  const toggleExpanded = useCallback(() => setIsExpanded(prev => !prev), []);

  const getFileName = (path: string): string => {
    const parts = path.split('/');
    return parts[parts.length - 1] || path;
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
          {currentSource.available ? (
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
