import { Edit3, Save, Copy, Download, RefreshCw, Maximize2, X, Loader2 } from 'lucide-react';

interface Props {
  filename: string;
  fileSize?: number;
  isEditing?: boolean;
  hasChanges?: boolean;
  isSaving?: boolean;
  onEdit?: () => void;
  onSave?: () => void;
  onCopy?: () => void;
  onDownload?: () => void;
  onRefresh?: () => void;
  onFullscreen?: () => void;
  onClose?: () => void;
}

export function Toolbar({
  filename,
  fileSize,
  isEditing,
  hasChanges,
  isSaving,
  onEdit,
  onSave,
  onCopy,
  onDownload,
  onRefresh,
  onFullscreen,
  onClose
}: Props) {
  const formatSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
      className={`p-2 rounded transition-colors ${
        disabled ? 'opacity-30 cursor-not-allowed' :
        accent ? 'text-vetka-accent hover:bg-vetka-border' :
        active ? 'bg-vetka-accent text-white' :
        'text-vetka-muted hover:text-white hover:bg-vetka-border'
      }`}
    >
      {children}
    </button>
  );

  return (
    <div className="absolute bottom-0 left-0 right-0 p-2
                    bg-vetka-surface/95 border-t border-vetka-border
                    opacity-0 group-hover:opacity-100 transition-opacity duration-200
                    flex items-center gap-1 z-10">
      {onEdit && (
        <Btn onClick={onEdit} active={isEditing} title={isEditing ? 'Editing' : 'Edit'}>
          <Edit3 size={18} />
        </Btn>
      )}
      {hasChanges && onSave && (
        <Btn
          onClick={onSave}
          accent
          title={isSaving ? 'Saving...' : 'Save'}
          disabled={isSaving}
        >
          {isSaving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
        </Btn>
      )}
      {onCopy && <Btn onClick={onCopy} title="Copy"><Copy size={18} /></Btn>}
      {onDownload && <Btn onClick={onDownload} title="Download"><Download size={18} /></Btn>}
      {onRefresh && <Btn onClick={onRefresh} title="Refresh"><RefreshCw size={18} /></Btn>}

      <div className="flex-1 text-center">
        <span className="text-xs text-vetka-muted truncate">{filename}</span>
        {fileSize !== undefined && (
          <span className="text-xs text-vetka-muted ml-2">({formatSize(fileSize)})</span>
        )}
      </div>

      {onFullscreen && <Btn onClick={onFullscreen} title="Fullscreen"><Maximize2 size={18} /></Btn>}
      {onClose && <Btn onClick={onClose} title="Close"><X size={18} /></Btn>}
    </div>
  );
}
