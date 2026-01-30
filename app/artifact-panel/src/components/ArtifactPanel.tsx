import { lazy, Suspense, useState, useEffect, useCallback } from 'react';
import { getViewerType } from '../utils/fileTypes';
import { RichTextEditor } from './viewers/RichTextEditor';
import { MarkdownViewer } from './viewers/MarkdownViewer';
import { ImageViewer } from './viewers/ImageViewer';
import { MediaViewer } from './viewers/MediaViewer';
import { Toolbar } from './Toolbar';
import { Loader2 } from 'lucide-react';
import { useIframeApi, postToParent } from '../hooks/useIframeApi';

// Lazy load heavy viewers
const CodeViewer = lazy(() => import('./viewers/CodeViewer').then(m => ({ default: m.CodeViewer })));
const AudioWaveform = lazy(() => import('./viewers/AudioWaveform').then(m => ({ default: m.AudioWaveform })));
const PDFViewer = lazy(() => import('./viewers/PDFViewer').then(m => ({ default: m.PDFViewer })));
const ThreeDViewer = lazy(() => import('./viewers/ThreeDViewer').then(m => ({ default: m.ThreeDViewer })));

function ViewerLoading() {
  return (
    <div className="h-full flex items-center justify-center bg-vetka-bg">
      <Loader2 className="w-8 h-8 animate-spin text-vetka-muted" />
    </div>
  );
}

interface FileData {
  path: string;
  content: string;
  mimeType: string;
  hasChanges: boolean;
  fileSize?: number;
}

interface Props {
  filePath?: string;
  onClose?: () => void;
}

export function ArtifactPanel({ filePath, onClose }: Props) {
  const [file, setFile] = useState<FileData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Open file - replaces current file (single file mode)
  const openFile = useCallback(async (path: string) => {
    console.log('[ArtifactPanel] openFile called with:', path);
    if (!path) return;

    // Same file? Just return
    if (file?.path === path) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });

      if (!response.ok) throw new Error('Failed to load');
      const data = await response.json();

      setFile({
        path,
        content: data.content,
        mimeType: data.mimeType,
        hasChanges: false,
        fileSize: data.size,
      });

      console.log('[ArtifactPanel] File loaded:', path, 'length:', data.content?.length);
      postToParent('FILE_OPENED', { path });
    } catch (err) {
      console.error('[ArtifactPanel] Load error:', err);
      postToParent('ERROR', { message: `Failed to load: ${err instanceof Error ? err.message : 'Unknown error'}` });
    } finally {
      setIsLoading(false);
    }
  }, [file?.path]);

  // Close file
  const closeFile = useCallback(() => {
    if (file?.hasChanges) {
      if (!confirm('Unsaved changes will be lost. Close anyway?')) return;
    }
    const oldPath = file?.path;
    setFile(null);
    setIsEditing(false);
    if (oldPath) postToParent('FILE_CLOSED', { path: oldPath });
  }, [file]);

  // Update content
  const updateContent = useCallback((content: string) => {
    setFile(prev => prev ? { ...prev, content, hasChanges: true } : null);
  }, []);

  // Save file
  const saveFile = useCallback(async () => {
    if (!file) return;
    setIsSaving(true);
    try {
      const response = await fetch('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: file.path, content: file.content }),
      });
      if (!response.ok) throw new Error('Save failed');
      setFile(prev => prev ? { ...prev, hasChanges: false } : null);
      postToParent('FILE_SAVED', { path: file.path });
    } catch (err) {
      console.error('[ArtifactPanel] Save error:', err);
    } finally {
      setIsSaving(false);
    }
  }, [file]);

  // Refresh file (reload from disk)
  const refreshFile = useCallback(async () => {
    if (!file) return;
    const currentPath = file.path;
    setFile(null); // Force re-fetch
    await openFile(currentPath);
  }, [file, openFile]);

  // iframe API
  useIframeApi({
    onOpenFile: openFile,
    onCloseFile: closeFile,
    onSetTheme: (theme) => console.log('[ArtifactPanel] Theme:', theme),
    onSetReadonly: (readonly) => console.log('[ArtifactPanel] Readonly:', readonly),
  });

  // Auto-open file from props
  useEffect(() => {
    if (filePath && !file) openFile(filePath);
  }, [filePath, file, openFile]);

  // Ready signal
  useEffect(() => {
    postToParent('READY');
  }, []);

  // Dirty signal
  useEffect(() => {
    if (file) postToParent('FILE_DIRTY', { path: file.path, isDirty: file.hasChanges });
  }, [file?.path, file?.hasChanges]);

  // Actions
  const handleCopy = () => navigator.clipboard.writeText(file?.content || '');
  const handleDownload = () => {
    if (!file) return;
    const filename = file.path.split('/').pop() || 'file';
    const blob = new Blob([file.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };
  const handleFullscreen = async () => {
    const panel = document.querySelector('.artifact-panel');
    if (!panel) return;
    try {
      if (!document.fullscreenElement) await panel.requestFullscreen();
      else await document.exitFullscreen();
    } catch (err) {
      console.error('[ArtifactPanel] Fullscreen error:', err);
    }
  };

  // Render viewer based on file type
  const renderViewer = () => {
    if (!file) return null;
    const { content, path } = file;
    const filename = path.split('/').pop() || '';
    const fileType = getViewerType(filename);
    const fileUrl = `/api/files/raw?path=${encodeURIComponent(path)}`;

    switch (fileType) {
      case 'code':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer content={content} filename={filename} readOnly={!isEditing} onChange={updateContent} />
          </Suspense>
        );
      case 'richtext':
        return <RichTextEditor content={content} readOnly={!isEditing} onChange={updateContent} />;
      case 'markdown':
        return isEditing
          ? <RichTextEditor content={content} onChange={updateContent} />
          : <MarkdownViewer content={content} />;
      case 'image':
        return <ImageViewer url={fileUrl} filename={filename} />;
      case 'media':
        return <MediaViewer url={fileUrl} />;
      case 'audio':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <AudioWaveform url={fileUrl} filename={filename} />
          </Suspense>
        );
      case 'pdf':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <PDFViewer url={fileUrl} />
          </Suspense>
        );
      case '3d':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <ThreeDViewer url={fileUrl} />
          </Suspense>
        );
      default:
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer content={content} filename={filename} readOnly={!isEditing} onChange={updateContent} />
          </Suspense>
        );
    }
  };

  return (
    <div className="artifact-panel group relative h-full flex flex-col bg-vetka-bg">
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-vetka-bg/80 z-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-vetka-accent" />
        </div>
      )}

      {/* Empty state */}
      {!file && !isLoading && (
        <div className="flex-1 flex items-center justify-center text-vetka-muted">
          <p>Click a file in the tree to view</p>
        </div>
      )}

      {/* Viewer */}
      {file && (
        <div className="flex-1 overflow-hidden">
          {renderViewer()}
        </div>
      )}

      {/* Floating Toolbar - appears on hover */}
      {file && (
        <Toolbar
          filename={file.path.split('/').pop() || ''}
          fileSize={file.fileSize}
          isEditing={isEditing}
          hasChanges={file.hasChanges}
          isSaving={isSaving}
          onEdit={() => setIsEditing(!isEditing)}
          onSave={saveFile}
          onCopy={handleCopy}
          onDownload={handleDownload}
          onRefresh={refreshFile}
          onFullscreen={handleFullscreen}
          onClose={closeFile}
        />
      )}
    </div>
  );
}
