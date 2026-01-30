/**
 * DropZoneRouter - Unified drop zone handler for main window.
 * Routes file drops to appropriate handlers based on drop location.
 * Supports both Tauri (native) and browser (HTML5) drag & drop.
 *
 * @status active
 * @phase 100.4
 * @depends react, ../config/tauri
 * @used_by App
 */

import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { isTauri, onFilesDropped, handleDropPaths, type FileInfo } from '../config/tauri';

// Drop zone types
export type DropZone = 'tree' | 'chat' | null;

// Event types for drop zone routing
export interface DropZoneEvent {
  zone: DropZone;
  files: FileInfo[];
  paths: string[];
}

// Browser file info (when Tauri is not available)
export interface BrowserFileInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: number | null;
  extension: string | null;
}

interface Props {
  children: ReactNode;
  isChatOpen: boolean;
  chatPanelWidth?: number;
  chatPosition?: 'left' | 'right';
  onDropToTree?: (event: DropZoneEvent) => void;
  onDropToChat?: (event: DropZoneEvent) => void;
}

/**
 * DropZoneRouter wraps the main window and routes file drops
 * to the appropriate zone (tree or chat panel).
 */
export function DropZoneRouter({
  children,
  isChatOpen,
  chatPanelWidth = 420,
  chatPosition = 'left',
  onDropToTree,
  onDropToChat,
}: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState<DropZone>(null);
  const dragCounterRef = useRef(0);
  const lastDragTimeRef = useRef(0);

  // Determine drop zone based on mouse position
  const getDropZone = useCallback((clientX: number): DropZone => {
    // If chat is closed, everything goes to tree
    if (!isChatOpen) {
      return 'tree';
    }

    if (chatPosition === 'left') {
      // Chat on left side
      if (clientX < chatPanelWidth) {
        return 'chat';
      }
      return 'tree';
    } else {
      // Chat on right side
      const windowWidth = window.innerWidth;
      if (clientX > windowWidth - chatPanelWidth) {
        return 'chat';
      }
      return 'tree';
    }
  }, [isChatOpen, chatPanelWidth, chatPosition]);

  // Convert browser File to FileInfo format
  const browserFileToInfo = useCallback((file: File, path?: string): BrowserFileInfo => {
    const ext = file.name.includes('.') ? file.name.split('.').pop() || null : null;
    return {
      name: file.name,
      path: path || `browser://${file.name}`,
      is_dir: false,
      size: file.size,
      modified: file.lastModified,
      extension: ext,
    };
  }, []);

  // Dispatch drop event to appropriate handler
  const dispatchDrop = useCallback((zone: DropZone, files: FileInfo[], paths: string[]) => {
    const event: DropZoneEvent = { zone, files, paths };

    // Dispatch custom event for global listeners
    window.dispatchEvent(new CustomEvent('vetka-file-drop', {
      detail: event,
    }));

    // Call specific handler
    if (zone === 'tree' && onDropToTree) {
      onDropToTree(event);
    } else if (zone === 'chat' && onDropToChat) {
      onDropToChat(event);
    }
  }, [onDropToTree, onDropToChat]);

  // ============================================
  // Tauri Native Drop Handler
  // ============================================
  useEffect(() => {
    if (!isTauri()) return;

    let unlistenFn: (() => void) | null = null;

    const setupListener = async () => {
      unlistenFn = await onFilesDropped(async (paths) => {
        // console.log('[DropZoneRouter] Tauri drop:', paths);

        // Get file info for dropped paths
        const fileInfos = await handleDropPaths(paths);
        if (!fileInfos || fileInfos.length === 0) return;

        // For Tauri, we need to get mouse position at drop time
        // Since Tauri doesn't provide it, default to tree zone
        // TODO: Implement Tauri drop position tracking
        const zone: DropZone = isChatOpen ? 'tree' : 'tree';

        dispatchDrop(zone, fileInfos, paths);

        // Reset drag state
        setIsDragging(false);
        setDragTarget(null);
      });
    };

    setupListener();

    return () => {
      unlistenFn?.();
    };
  }, [isChatOpen, dispatchDrop]);

  // ============================================
  // Browser HTML5 Drag & Drop Handler
  // ============================================
  useEffect(() => {
    // Skip browser handlers in Tauri mode (Tauri handles drops natively)
    if (isTauri()) return;

    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      dragCounterRef.current++;
      lastDragTimeRef.current = Date.now();
      if (dragCounterRef.current === 1) {
        setIsDragging(true);
      }
    };

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      lastDragTimeRef.current = Date.now();
      setDragTarget(getDropZone(e.clientX));
    };

    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      dragCounterRef.current--;

      // Only hide overlay when leaving the document entirely
      const relatedTarget = e.relatedTarget as Node | null;
      if (!relatedTarget || !document.contains(relatedTarget)) {
        dragCounterRef.current = 0;
        setIsDragging(false);
        setDragTarget(null);
      } else if (dragCounterRef.current <= 0) {
        dragCounterRef.current = 0;
        setIsDragging(false);
        setDragTarget(null);
      }
    };

    const handleDrop = async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const zone = getDropZone(e.clientX);
      dragCounterRef.current = 0;
      setIsDragging(false);
      setDragTarget(null);

      const items = e.dataTransfer?.items;
      if (!items) return;

      const files: BrowserFileInfo[] = [];
      const paths: string[] = [];

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind !== 'file') continue;

        // Try to get FileSystemHandle (modern API)
        // @ts-ignore - getAsFileSystemHandle is experimental
        if (item.getAsFileSystemHandle) {
          try {
            // @ts-ignore
            const handle = await item.getAsFileSystemHandle();

            if (handle.kind === 'directory') {
              // For directories, we can't get real paths in browser
              // Use virtual path
              const dirPath = `browser://${handle.name}`;
              paths.push(dirPath);
              files.push({
                name: handle.name,
                path: dirPath,
                is_dir: true,
                size: 0,
                modified: null,
                extension: null,
              });
            } else {
              const file = await (handle as FileSystemFileHandle).getFile();
              const filePath = `browser://${file.name}`;
              paths.push(filePath);
              files.push(browserFileToInfo(file, filePath));
            }
          } catch (err) {
            console.warn('[DropZoneRouter] FileSystemHandle error:', err);
          }
        } else {
          // Fallback: use getAsFile()
          const file = item.getAsFile();
          if (file) {
            const filePath = `browser://${file.name}`;
            paths.push(filePath);
            files.push(browserFileToInfo(file, filePath));
          }
        }
      }

      if (files.length > 0) {
        dispatchDrop(zone, files as FileInfo[], paths);
      }
    };

    const handleDragEnd = () => {
      dragCounterRef.current = 0;
      setIsDragging(false);
      setDragTarget(null);
    };

    // Stale drag detection - reset if no activity for 500ms
    const staleCheckInterval = setInterval(() => {
      if (isDragging && Date.now() - lastDragTimeRef.current > 500) {
        dragCounterRef.current = 0;
        setIsDragging(false);
        setDragTarget(null);
      }
    }, 200);

    document.addEventListener('dragenter', handleDragEnter);
    document.addEventListener('dragover', handleDragOver);
    document.addEventListener('dragleave', handleDragLeave);
    document.addEventListener('drop', handleDrop);
    document.addEventListener('dragend', handleDragEnd);

    return () => {
      clearInterval(staleCheckInterval);
      document.removeEventListener('dragenter', handleDragEnter);
      document.removeEventListener('dragover', handleDragOver);
      document.removeEventListener('dragleave', handleDragLeave);
      document.removeEventListener('drop', handleDrop);
      document.removeEventListener('dragend', handleDragEnd);
    };
  // Phase 100.5: Removed isDragging from deps - it caused handlers to re-register
  // on every state change, breaking the drag state machine mid-operation
  }, [getDropZone, browserFileToInfo, dispatchDrop]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {children}

      {/* Drop zone overlay */}
      {isDragging && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            pointerEvents: 'none',
            zIndex: 1000,
          }}
        >
          {/* Chat drop zone */}
          {isChatOpen && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                [chatPosition]: 0,
                width: chatPanelWidth,
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: dragTarget === 'chat'
                  ? 'rgba(74, 158, 255, 0.15)'
                  : 'rgba(255, 255, 255, 0.02)',
                border: dragTarget === 'chat'
                  ? '2px dashed rgba(74, 158, 255, 0.7)'
                  : '2px dashed rgba(255, 255, 255, 0.1)',
                transition: 'all 0.15s ease',
              }}
            >
              <span
                style={{
                  color: dragTarget === 'chat' ? '#4a9eff' : '#555',
                  fontSize: 14,
                  fontWeight: 500,
                  letterSpacing: '0.5px',
                  transition: 'color 0.15s',
                }}
              >
                Pin to Chat
              </span>
            </div>
          )}

          {/* Tree drop zone (main canvas area) */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              ...(isChatOpen
                ? chatPosition === 'left'
                  ? { left: chatPanelWidth, right: 0 }
                  : { left: 0, right: chatPanelWidth }
                : { left: 0, right: 0 }),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: dragTarget === 'tree'
                ? 'rgba(255, 255, 255, 0.06)'
                : 'transparent',
              border: dragTarget === 'tree'
                ? '2px dashed rgba(255, 255, 255, 0.4)'
                : '2px dashed transparent',
              transition: 'all 0.15s ease',
            }}
          >
            <span
              style={{
                color: dragTarget === 'tree' ? '#fff' : '#444',
                fontSize: 16,
                fontWeight: 500,
                letterSpacing: '0.5px',
                transition: 'color 0.15s',
              }}
            >
              Add to Tree
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DropZoneRouter;
