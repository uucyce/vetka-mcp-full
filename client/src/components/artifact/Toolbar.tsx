/**
 * Toolbar - Action toolbar for artifact viewer with file operations.
 * Provides edit, save, copy, download, and undo functionality.
 *
 * @status active
 * @phase 96
 * @depends lucide-react
 * @used_by ArtifactPanel
 */

import { Edit3, Save, Copy, Download, RefreshCw, X, Loader2, FolderOpen, Undo2, FilePlus2 } from 'lucide-react';

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
  onClose
}: Props) {
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

  const Btn = ({ onClick, active, disabled, children, title, accent }: {
    onClick?: () => void;
    active?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    title: string;
    accent?: boolean;
  }) => (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      style={{
        ...btnBase,
        color: disabled ? '#333' : accent ? '#60a5fa' : active ? '#fff' : '#666',
        background: active ? '#3b82f6' : 'transparent',
        opacity: disabled ? 0.3 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {children}
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
        <Btn onClick={onEdit} active={isEditing} title={isEditing ? 'Editing' : 'Edit'}>
          <Edit3 size={16} />
        </Btn>
      )}
      {/* Phase 60.4: Undo button (when editing and can undo) */}
      {isEditing && onUndo && (
        <Btn onClick={onUndo} title="Undo (Ctrl+Z)" disabled={!canUndo}>
          <Undo2 size={16} />
        </Btn>
      )}
      {/* Phase 60.4: Save button - always visible when onSave provided, accent when hasChanges */}
      {onSave && (
        <Btn onClick={onSave} accent={hasChanges} title={isSaving ? 'Saving...' : hasChanges ? 'Save changes' : 'No changes'} disabled={isSaving || !hasChanges}>
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
        </Btn>
      )}
      {/* Phase 60.4: Save As / Duplicate */}
      {onSaveAs && (
        <Btn onClick={onSaveAs} title="Save As / Duplicate">
          <FilePlus2 size={16} />
        </Btn>
      )}
      {onCopy && <Btn onClick={onCopy} title="Copy to clipboard"><Copy size={16} /></Btn>}
      {onDownload && <Btn onClick={onDownload} title="Download"><Download size={16} /></Btn>}
      {/* Phase 60.4: Open in Finder button */}
      {onOpenInFinder && <Btn onClick={onOpenInFinder} title="Open in Finder"><FolderOpen size={16} /></Btn>}
      {onRefresh && <Btn onClick={onRefresh} title="Refresh"><RefreshCw size={16} /></Btn>}

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

      {onClose && <Btn onClick={onClose} title="Close"><X size={16} /></Btn>}
    </div>
  );
}
