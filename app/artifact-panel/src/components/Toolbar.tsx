import { Edit3, Save, Copy, Download, RefreshCw, Maximize2, X, Loader2, Check } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

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
      className={`p-2 rounded transition-colors ${
        disabled ? 'opacity-35 cursor-not-allowed text-[#3f3f3f]' :
        active || firedAction === actionKey ? 'text-white bg-white/10' :
        'text-vetka-muted hover:text-white hover:bg-vetka-border'
      }`}
    >
      {firedAction === actionKey && successChildren ? successChildren : children}
    </button>
  );

  return (
    <div className="absolute bottom-0 left-0 right-0 p-2
                    bg-vetka-surface/95 border-t border-vetka-border
                    opacity-0 group-hover:opacity-100 transition-opacity duration-200
                    flex items-center gap-1 z-10">
      {onEdit && (
        <Btn onClick={onEdit} active={isEditing} title={isEditing ? 'Editing' : 'Edit'} actionKey="edit">
          <Edit3 size={18} />
        </Btn>
      )}
      {hasChanges && onSave && (
        <Btn
          onClick={onSave}
          title={isSaving ? 'Saving...' : 'Save'}
          disabled={isSaving}
          actionKey="save"
          successChildren={<Check size={18} />}
        >
          {isSaving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
        </Btn>
      )}
      {onCopy && (
        <Btn onClick={onCopy} title="Copy" actionKey="copy" successChildren={<Check size={18} />}>
          <Copy size={18} />
        </Btn>
      )}
      {onDownload && (
        <Btn onClick={onDownload} title="Download" actionKey="download" successChildren={<Check size={18} />}>
          <Download size={18} />
        </Btn>
      )}
      {onRefresh && (
        <Btn onClick={onRefresh} title="Refresh" actionKey="refresh" successChildren={<Check size={18} />}>
          <RefreshCw size={18} />
        </Btn>
      )}

      <div className="flex-1 text-center">
        <span className="text-xs text-vetka-muted truncate">{filename}</span>
        {fileSize !== undefined && (
          <span className="text-xs text-vetka-muted ml-2">({formatSize(fileSize)})</span>
        )}
      </div>

      {onFullscreen && (
        <Btn onClick={onFullscreen} title="Fullscreen" actionKey="fullscreen">
          <Maximize2 size={18} />
        </Btn>
      )}
      {onClose && (
        <Btn onClick={onClose} title="Close" actionKey="close">
          <X size={18} />
        </Btn>
      )}
    </div>
  );
}
