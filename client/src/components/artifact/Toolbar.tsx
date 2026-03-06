/**
 * Toolbar - Action toolbar for artifact viewer with file operations.
 * Provides edit, save, copy, download, and undo functionality.
 *
 * @status active
 * @phase 96
 * @depends lucide-react
 * @used_by ArtifactPanel
 */

import { Edit3, Save, Copy, Download, RefreshCw, X, Loader2, FolderOpen, Undo2, FilePlus2, Pin, Check, Info, ExternalLink } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface Props {
  filename: string;
  filePath?: string;  // Phase 60.4: For "Open in Finder"
  fileSize?: number;
  createdAt?: number;
  modifiedAt?: number;
  isEditing?: boolean;
  hasChanges?: boolean;
  isSaving?: boolean;
  canUndo?: boolean;  // Phase 60.4: Undo support
  onEdit?: () => void;
  onSave?: () => void;
  onSaveAs?: () => void;  // Phase 60.4: Save As / Duplicate
  onUndo?: () => void;  // Phase 60.4: Undo
  onCopy?: () => void;
  onDownload?: () => void;
  onRefresh?: () => void;
  onOpenInFinder?: () => void;  // Phase 60.4: Open file in Finder
  onInfo?: () => void;
  infoActive?: boolean;
  onDetach?: () => void;
  onPin?: () => void;
  isPinned?: boolean;
  pinVisible?: boolean;
  pinDisabled?: boolean;
  pinTitle?: string;
  detachedShowFavorite?: boolean;
  detachedFavoriteActive?: boolean;
  detachedFavoriteBusy?: boolean;
  onDetachedFavoriteToggle?: () => void;
  detachedShowVetka?: boolean;
  detachedVetkaBusy?: boolean;
  onDetachedVetkaAdd?: () => void;
  onClose?: () => void;
  compact?: boolean;
}

export function Toolbar({
  filename,
  filePath,
  fileSize,
  createdAt,
  modifiedAt,
  isEditing,
  hasChanges,
  isSaving,
  canUndo,
  onEdit,
  onSave,
  onSaveAs,
  onUndo,
  onCopy,
  onDownload,
  onRefresh,
  onOpenInFinder,
  onInfo,
  infoActive,
  onDetach,
  onPin,
  isPinned,
  pinVisible,
  pinDisabled,
  pinTitle,
  detachedShowFavorite,
  detachedFavoriteActive,
  detachedFavoriteBusy,
  onDetachedFavoriteToggle,
  detachedShowVetka,
  detachedVetkaBusy,
  onDetachedVetkaAdd,
  onClose,
  compact = false,
}: Props) {
  const [firedAction, setFiredAction] = useState<string | null>(null);
  const actionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (actionTimerRef.current) clearTimeout(actionTimerRef.current);
  }, []);

  const flashAction = (actionKey: string) => {
    if (actionTimerRef.current) clearTimeout(actionTimerRef.current);
    setFiredAction(actionKey);
    actionTimerRef.current = setTimeout(() => setFiredAction(null), 1100);
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'n/a';
    try {
      const d = new Date(timestamp * 1000);
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch {
      return 'n/a';
    }
  };

  const btnBase = {
    padding: compact ? 6 : 8,
    borderRadius: 4,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    transition: 'all 0.15s',
  };

  const Btn = ({ onClick, active, disabled, children, successChildren, title, actionKey }: {
    onClick?: () => void;
    active?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    successChildren?: React.ReactNode;
    title: string;
    actionKey: string;
  }) => (
    <button
      onClick={() => {
        if (disabled || !onClick) return;
        onClick();
        flashAction(actionKey);
      }}
      title={title}
      disabled={disabled}
      style={{
        ...btnBase,
        color: disabled ? '#3f3f3f' : active || firedAction === actionKey ? '#ffffff' : '#808080',
        background: active || firedAction === actionKey ? 'rgba(255,255,255,0.10)' : 'transparent',
        opacity: disabled ? 0.35 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {firedAction === actionKey && successChildren ? successChildren : children}
    </button>
  );

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      padding: compact ? 6 : 8,
      background: 'rgba(15, 15, 15, 0.95)',
      borderTop: '1px solid #222',
    }}>
      {onEdit && (
        <Btn onClick={onEdit} active={isEditing} title={isEditing ? 'Editing' : 'Edit'} actionKey="edit">
          <Edit3 size={16} />
        </Btn>
      )}
      {/* Phase 60.4: Undo button (when editing and can undo) */}
      {isEditing && onUndo && (
        <Btn onClick={onUndo} title="Undo (Ctrl+Z)" disabled={!canUndo} actionKey="undo">
          <Undo2 size={16} />
        </Btn>
      )}
      {/* Phase 60.4: Save button - always visible when onSave provided, accent when hasChanges */}
      {onSave && (
        <Btn
          onClick={onSave}
          title={isSaving ? 'Saving...' : hasChanges ? 'Save changes' : 'No changes'}
          disabled={isSaving || !hasChanges}
          actionKey="save"
          successChildren={<Check size={16} />}
        >
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
        </Btn>
      )}
      {/* Phase 60.4: Save As / Duplicate */}
      {onSaveAs && (
        <Btn onClick={onSaveAs} title="Save As / Duplicate" actionKey="save_as" successChildren={<Check size={16} />}>
          <FilePlus2 size={16} />
        </Btn>
      )}
      {onCopy && (
        <Btn onClick={onCopy} title="Copy to clipboard" actionKey="copy" successChildren={<Check size={16} />}>
          <Copy size={16} />
        </Btn>
      )}
      {onDownload && (
        <Btn onClick={onDownload} title="Download" actionKey="download" successChildren={<Check size={16} />}>
          <Download size={16} />
        </Btn>
      )}
      {/* Phase 60.4: Open in Finder button */}
      {onOpenInFinder && (
        <Btn onClick={onOpenInFinder} title="Open in Finder" actionKey="finder" successChildren={<Check size={16} />}>
          <FolderOpen size={16} />
        </Btn>
      )}
      {onRefresh && (
        <Btn onClick={onRefresh} title="Refresh" actionKey="refresh" successChildren={<Check size={16} />}>
          <RefreshCw size={16} />
        </Btn>
      )}
      {onInfo && (
        <Btn onClick={onInfo} active={Boolean(infoActive)} title="Media info" actionKey="info">
          <Info size={16} />
        </Btn>
      )}
      {onDetach && (
        <Btn onClick={onDetach} title="Open detached media window" actionKey="detach" successChildren={<Check size={16} />}>
          <ExternalLink size={16} />
        </Btn>
      )}
      {pinVisible && (
        <Btn
          onClick={onPin}
          active={Boolean(isPinned)}
          title={pinTitle || (isPinned ? 'Unpin from chat context' : 'Pin to chat context')}
          actionKey="pin"
          disabled={pinDisabled || !onPin}
          successChildren={<Check size={16} />}
        >
          <Pin size={16} />
        </Btn>
      )}

      {!compact && (
        <div style={{ flex: 1, textAlign: 'center' }}>
          <span style={{ fontSize: 11, color: '#666' }}>{filename}</span>
          {fileSize !== undefined && (
            <span style={{ fontSize: 11, color: '#444', marginLeft: 8 }}>({formatSize(fileSize)})</span>
          )}
          {(createdAt || modifiedAt) && (
            <div style={{ fontSize: 10, color: '#4f4f4f', marginTop: 2 }}>
              <span>Created: {formatDate(createdAt)}</span>
              <span style={{ marginLeft: 8 }}>Modified: {formatDate(modifiedAt)}</span>
            </div>
          )}
        </div>
      )}
      {compact && <div style={{ flex: 1 }} />}

      {detachedShowFavorite && (
        <Btn
          onClick={onDetachedFavoriteToggle}
          active={Boolean(detachedFavoriteActive)}
          disabled={Boolean(detachedFavoriteBusy)}
          title={detachedFavoriteActive ? 'Remove favorite' : 'Add favorite'}
          actionKey="detached-favorite"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
            <path d="M12 3.7l2.6 5.2 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z" fill={detachedFavoriteActive ? 'currentColor' : 'none'} />
          </svg>
        </Btn>
      )}

      {detachedShowVetka && (
        <Btn
          onClick={onDetachedVetkaAdd}
          disabled={Boolean(detachedVetkaBusy)}
          title={detachedVetkaBusy ? 'Adding to VETKA...' : 'Add to VETKA'}
          actionKey="detached-vetka"
        >
          {detachedVetkaBusy ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
              <circle cx="12" cy="12" r="9" />
              <line x1="12" y1="6" x2="12" y2="18" />
              <path d="M12 12 L8 7" />
              <path d="M12 12 L16 7" />
            </svg>
          )}
        </Btn>
      )}

      {onClose && (
        <Btn onClick={onClose} title="Close" actionKey="close">
          <X size={16} />
        </Btn>
      )}
    </div>
  );
}
