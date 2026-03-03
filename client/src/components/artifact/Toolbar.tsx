/**
 * Toolbar - Action toolbar for artifact viewer with file operations.
 * Provides edit, save, copy, download, and undo functionality.
 *
 * @status active
 * @phase 96
 * @depends lucide-react
 * @used_by ArtifactPanel
 */

import { Edit3, Save, Copy, Download, RefreshCw, X, Loader2, FolderOpen, Undo2, FilePlus2, Pin, Check } from 'lucide-react';
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
  onPin?: () => void;
  isPinned?: boolean;
  pinVisible?: boolean;
  pinDisabled?: boolean;
  pinTitle?: string;
  onClose?: () => void;
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
  onPin,
  isPinned,
  pinVisible,
  pinDisabled,
  pinTitle,
  onClose
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
    padding: 8,
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
      padding: 8,
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

      {onClose && (
        <Btn onClick={onClose} title="Close" actionKey="close">
          <X size={16} />
        </Btn>
      )}
    </div>
  );
}
