/**
 * ArtifactWindow - Floating window wrapper for ArtifactPanel.
 * Provides draggable/resizable container for file viewing.
 *
 * @status active
 * @phase 104.9
 * @depends FloatingWindow, ArtifactPanel, useStore
 * @used_by ChatPanel
 *
 * MARKER_104_VISUAL - Added L2 approval level and content change props
 */

import { FloatingWindow } from './FloatingWindow';
import { ArtifactPanel } from './ArtifactPanel';
import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useStore } from '../../store/useStore';

// Phase 68.2: Support for direct file/content passing
interface FileInfo {
  path: string;
  name: string;
  extension?: string;
}

interface RawContent {
  content: string;
  title: string;
  type?: 'text' | 'markdown' | 'code' | 'web';
  sourceUrl?: string;
}

// MARKER_104_VISUAL - Approval levels for artifact editing
type ApprovalLevel = 'L1' | 'L2' | 'L3';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  isChatOpen?: boolean;
  /** Phase 68.2: Direct file info (overrides store selection) */
  file?: FileInfo | null;
  /** Phase 68.2: Raw content for preview */
  rawContent?: RawContent | null;
  /** Phase 104.9: Approval level for L2 editing */
  approvalLevel?: ApprovalLevel;
  /** Phase 104.9: Artifact ID for approval events */
  artifactId?: string;
  /** Phase 104.9: Callback for L2 content changes */
  onContentChange?: (content: string) => void;
  /** Phase 153: Initial media seek timestamp (seconds) for audio/video artifacts */
  initialSeekSec?: number;
}

export function ArtifactWindow({ isOpen, onClose, isChatOpen = false, file: propFile, rawContent, approvalLevel, artifactId, onContentChange, initialSeekSec }: Props) {
  const selectedId = useStore((state) => state.selectedId);
  const nodes = useStore((state) => state.nodes);
  const selectedNode = selectedId ? nodes[selectedId] : null;
  const [isIndexingToVetka, setIsIndexingToVetka] = useState(false);
  const [locallyIndexedPath, setLocallyIndexedPath] = useState<string | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);

  // Phase 68.2: Use prop file if provided, otherwise use store selection
  const storeFile = selectedNode && selectedNode.type === 'file' ? {
    path: selectedNode.path,
    name: selectedNode.name,
    extension: selectedNode.extension,
  } : null;

  const file = propFile || storeFile;
  const isFileMode = !rawContent && Boolean(file?.path);

  // Determine title based on what we're showing
  const title = rawContent?.title || file?.name || 'Artifact Viewer';

  const normalizePath = useCallback((p: string) => {
    const raw = String(p || '').trim();
    if (!raw) return '';
    const withoutScheme = raw.replace(/^file:\/\//, '');
    let decoded = withoutScheme;
    try {
      decoded = decodeURIComponent(withoutScheme);
    } catch {
      // keep as-is when not URI encoded
    }
    return decoded.replace(/\\/g, '/').replace(/\/+$/, '');
  }, []);

  const currentPath = useMemo(() => normalizePath(file?.path || ''), [file?.path, normalizePath]);
  const basename = useMemo(() => {
    const p = currentPath || '';
    const parts = p.split('/');
    return parts[parts.length - 1] || '';
  }, [currentPath]);

  useEffect(() => {
    if (!currentPath) return;
    if (locallyIndexedPath && locallyIndexedPath !== currentPath) {
      setLocallyIndexedPath(null);
    }
  }, [currentPath, locallyIndexedPath]);

  const isInVetka = useMemo(() => {
    if (locallyIndexedPath && locallyIndexedPath === currentPath) return true;
    if (!currentPath) return false;
    return Object.values(nodes).some((node: any) => {
      const nodePath = normalizePath(String(node?.path || ''));
      return nodePath === currentPath || nodePath.endsWith(`/${currentPath}`) || currentPath.endsWith(`/${nodePath}`);
    });
  }, [nodes, currentPath, normalizePath, locallyIndexedPath]);

  useEffect(() => {
    if (!isOpen) return;

    const loadFavoriteState = async () => {
      try {
        if (artifactId || (currentPath.includes('/data/artifacts/') || currentPath.includes('/src/vetka_out/'))) {
          const resp = await fetch('/api/artifacts');
          if (!resp.ok) return;
          const data = await resp.json();
          const list = data.artifacts || [];
          const match = list.find((a: any) => a.id === artifactId || a.file_path === currentPath || a.name === basename);
          setIsFavorite(Boolean(match?.is_favorite));
          return;
        }

        if (currentPath) {
          const resp = await fetch('/api/tree/favorites');
          if (!resp.ok) return;
          const data = await resp.json();
          const map = data.favorites || {};
          setIsFavorite(Boolean(map[currentPath]));
        }
      } catch {
        // no-op
      }
    };
    loadFavoriteState();
  }, [isOpen, artifactId, currentPath, basename]);

  const handleAddToVetka = useCallback(async () => {
    if (!currentPath || isIndexingToVetka || isInVetka) return;
    setIsIndexingToVetka(true);
    try {
      const response = await fetch('/api/watcher/index-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentPath }),
      });
      const data = await response.json();
      if (!response.ok || !data?.success) {
        throw new Error(data?.detail || data?.error || `HTTP ${response.status}`);
      }
      setLocallyIndexedPath(currentPath);
      window.dispatchEvent(new CustomEvent('vetka-tree-refresh-needed'));
    } catch (err) {
      console.error('[ArtifactWindow] Add to VETKA failed:', err);
    } finally {
      setIsIndexingToVetka(false);
    }
  }, [currentPath, isIndexingToVetka, isInVetka]);

  const handleToggleFavorite = useCallback(async () => {
    const next = !isFavorite;
    try {
      if (artifactId || (currentPath.includes('/data/artifacts/') || currentPath.includes('/src/vetka_out/'))) {
        const targetArtifactId = artifactId || basename || title;
        const response = await fetch(`/api/artifacts/${encodeURIComponent(targetArtifactId)}/favorite`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_favorite: next }),
        });
        if (!response.ok) return;
      } else if (currentPath) {
        const response = await fetch('/api/tree/favorite', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: currentPath, is_favorite: next }),
        });
        if (!response.ok) return;
      } else {
        return;
      }

      setIsFavorite(next);
      window.dispatchEvent(new CustomEvent('vetka-tree-refresh-needed'));
    } catch (err) {
      console.error('[ArtifactWindow] Favorite toggle failed:', err);
    }
  }, [artifactId, basename, currentPath, isFavorite, title]);

  const shouldShowFavoriteAction = !isFileMode || isInVetka;

  const headerFavoriteAction = shouldShowFavoriteAction ? (
    <button
      onClick={handleToggleFavorite}
      onMouseDown={(e) => e.stopPropagation()}
      title={isFavorite ? 'Remove favorite' : 'Add favorite'}
      style={{
        width: 24,
        height: 24,
        display: 'grid',
        placeItems: 'center',
        borderRadius: 6,
        border: '1px solid #3a3a3a',
        background: 'rgba(255,255,255,0.04)',
        color: '#f0f0f0',
        cursor: 'pointer',
        boxShadow: isFavorite ? '0 0 14px rgba(255,255,255,0.9)' : 'none',
      }}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
        <path d="M12 3.7l2.6 5.2 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z" fill={isFavorite ? 'currentColor' : 'none'} />
      </svg>
    </button>
  ) : null;

  const headerVetkaAction = isFileMode && !isInVetka ? (
    <button
      onClick={handleAddToVetka}
      onMouseDown={(e) => e.stopPropagation()}
      disabled={isIndexingToVetka}
      title={isIndexingToVetka ? 'Adding to VETKA...' : 'Add to VETKA'}
      style={{
        width: 24,
        height: 24,
        display: 'grid',
        placeItems: 'center',
        borderRadius: 6,
        border: '1px solid #3a3a3a',
        background: 'rgba(255,255,255,0.04)',
        color: '#f0f0f0',
        cursor: isIndexingToVetka ? 'wait' : 'pointer',
        boxShadow: isIndexingToVetka ? 'none' : '0 0 14px rgba(255,255,255,0.32)',
        opacity: isIndexingToVetka ? 0.45 : 1,
      }}
    >
      {isIndexingToVetka ? (
        <Loader2 size={13} className="animate-spin" />
      ) : (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="6" x2="12" y2="18" />
          <path d="M12 12 L8 7" />
          <path d="M12 12 L16 7" />
        </svg>
      )}
    </button>
  ) : null;

  return (
    <FloatingWindow
      title={title}
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={700}
      defaultHeight={500}
      headerActions={<>{headerFavoriteAction}{headerVetkaAction}</>}
    >
      {/* MARKER_104_VISUAL - Pass L2 approval props to ArtifactPanel */}
      <ArtifactPanel
        file={file}
        rawContent={rawContent}
        onClose={onClose}
        isChatOpen={isChatOpen}
        approvalLevel={approvalLevel}
        artifactId={artifactId}
        onContentChange={onContentChange}
        initialSeekSec={initialSeekSec}
      />
    </FloatingWindow>
  );
}
