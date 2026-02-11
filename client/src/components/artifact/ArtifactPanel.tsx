/**
 * ArtifactPanel - File and content viewer with editing support.
 * Displays files, raw content, and markdown with lazy-loaded viewers.
 *
 * @status active
 * @phase 104.9
 * @depends react, lucide-react, ./utils/fileTypes, ./viewers/*, ./Toolbar
 * @used_by ArtifactWindow, ChatPanel
 *
 * MARKER_104_VISUAL - L2 approval editing with subtle gray styling
 */

import { lazy, Suspense, useState, useEffect, useCallback, useRef } from 'react';
import { getViewerType } from './utils/fileTypes';
import { MarkdownViewer } from './viewers/MarkdownViewer';
import { Toolbar } from './Toolbar';
import { Loader2 } from 'lucide-react';
import { isTauri, openLiveWebWindow } from '../../config/tauri';

// Lazy load heavy viewers
const CodeViewer = lazy(() => import('./viewers/CodeViewer').then(m => ({ default: m.CodeViewer })));
const ImageViewer = lazy(() => import('./viewers/ImageViewer').then(m => ({ default: m.ImageViewer })));

function ViewerLoading() {
  return (
    <div style={{
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0a0a0a'
    }}>
      <Loader2 size={32} color="#666" style={{ animation: 'spin 1s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

interface FileInfo {
  path: string;
  name: string;
  extension?: string;
}

interface FileData {
  path: string;
  content: string;
  mimeType: string;
  hasChanges: boolean;
  fileSize?: number;
}

// Phase 48.5.1: Raw content for chat responses
interface RawContent {
  content: string;
  title: string;
  type?: 'text' | 'markdown' | 'code' | 'web';
  sourceUrl?: string;
}

// MARKER_104_VISUAL - Approval levels for artifact editing
type ApprovalLevel = 'L1' | 'L2' | 'L3';

interface Props {
  file?: FileInfo | null;
  rawContent?: RawContent | null;  // Phase 48.5.1: Direct content display
  onClose?: () => void;
  // Phase 60.4: Allow editing raw content
  onContentChange?: (content: string) => void;
  // Phase 104.9: Approval level for staged artifacts
  approvalLevel?: ApprovalLevel;
  // Phase 104.9: Artifact ID for approval events
  artifactId?: string;
}

export function ArtifactPanel({ file, rawContent, onClose, onContentChange, approvalLevel, artifactId }: Props) {
  const [fileData, setFileData] = useState<FileData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [webMode, setWebMode] = useState<'live' | 'md'>('live');
  const [openingNativeWeb, setOpeningNativeWeb] = useState(false);

  // Phase 60.4: Editable raw content state
  const [editableContent, setEditableContent] = useState<string>('');
  const [rawHasChanges, setRawHasChanges] = useState(false);

  // MARKER_104_VISUAL - L2 approval state
  const [currentApprovalLevel, setCurrentApprovalLevel] = useState<ApprovalLevel | undefined>(approvalLevel);

  // MARKER_104_VISUAL - Sync approvalLevel from props
  useEffect(() => {
    setCurrentApprovalLevel(approvalLevel);
  }, [approvalLevel]);

  // MARKER_104_VISUAL - Listen for artifact-approval CustomEvent from useSocket.ts
  useEffect(() => {
    const handleApprovalEvent = (event: CustomEvent<{
      artifactId?: string;
      approvalLevel?: ApprovalLevel;
      action?: 'approve' | 'reject' | 'edit';
    }>) => {
      const { artifactId: eventArtifactId, approvalLevel: eventLevel, action } = event.detail;

      // Only respond if this event is for our artifact
      if (artifactId && eventArtifactId && eventArtifactId !== artifactId) {
        return;
      }

      if (eventLevel) {
        setCurrentApprovalLevel(eventLevel);
      }

      // L2 level enables editing mode automatically
      if (eventLevel === 'L2' || action === 'edit') {
        setIsEditing(true);
      }
    };

    window.addEventListener('artifact-approval', handleApprovalEvent as EventListener);
    return () => {
      window.removeEventListener('artifact-approval', handleApprovalEvent as EventListener);
    };
  }, [artifactId]);

  // Phase 60.4: Undo history (max 10 states)
  const MAX_UNDO_HISTORY = 10;
  const undoHistoryRef = useRef<string[]>([]);
  const [canUndo, setCanUndo] = useState(false);

  // Phase 48.5.1: Handle raw content mode
  const isRawContentMode = !!rawContent;

  // Phase 60.4: Sync editable content when rawContent changes
  useEffect(() => {
    if (rawContent?.content) {
      setEditableContent(rawContent.content);
      setRawHasChanges(false);
      // Reset undo history
      undoHistoryRef.current = [rawContent.content];
      setCanUndo(false);
    }
  }, [rawContent?.content]);

  // MARKER_139.S1_4_WEB_LIVE_DEFAULT: Live mode must be default for web artifacts
  useEffect(() => {
    if (rawContent?.type === 'web') {
      setWebMode('live');
    }
  }, [rawContent?.type, rawContent?.sourceUrl]);

  // Phase 60.4: Push to undo history
  const pushToUndoHistory = useCallback((content: string) => {
    const history = undoHistoryRef.current;
    // Don't push if same as last
    if (history[history.length - 1] === content) return;

    history.push(content);
    // Keep max 10 states
    if (history.length > MAX_UNDO_HISTORY) {
      history.shift();
    }
    setCanUndo(history.length > 1);
  }, []);

  // Phase 60.4: Undo action
  const handleUndo = useCallback(() => {
    const history = undoHistoryRef.current;
    if (history.length <= 1) return;

    // Remove current state
    history.pop();
    // Get previous state
    const previousState = history[history.length - 1];
    if (previousState !== undefined) {
      setEditableContent(previousState);
      setRawHasChanges(previousState !== rawContent?.content);
    }
    setCanUndo(history.length > 1);
  }, [rawContent?.content]);

  // Load file content
  const loadFile = useCallback(async (path: string) => {
    if (!path) return;

    // MARKER_139.S1_3_WEB_FALLBACK: Never treat http(s) URL as local file path
    if (/^https?:\/\//i.test(path)) {
      setFileData({
        path,
        content: `# External Web URL\n\nSource: ${path}\n\nUse web preview mode to render full page.`,
        mimeType: 'text/markdown',
        hasChanges: false,
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });

      if (!response.ok) throw new Error('Failed to load');
      const data = await response.json();

      setFileData({
        path,
        content: data.content,
        mimeType: data.mimeType || 'text/plain',
        hasChanges: false,
        fileSize: data.size,
      });
    } catch (err) {
      console.error('[ArtifactPanel] Load error:', err);
      // Fallback for demo mode
      setFileData({
        path,
        content: `// Could not load file: ${path}\n// Backend not available`,
        mimeType: 'text/plain',
        hasChanges: false,
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load file when selection changes
  useEffect(() => {
    if (file?.path) {
      loadFile(file.path);
    } else {
      setFileData(null);
    }
  }, [file?.path, loadFile]);

  // Update content
  const updateContent = useCallback((content: string) => {
    setFileData(prev => prev ? { ...prev, content, hasChanges: true } : null);
  }, []);

  // Save file
  const saveFile = useCallback(async () => {
    if (!fileData) return;
    setIsSaving(true);
    try {
      const response = await fetch('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fileData.path, content: fileData.content }),
      });
      if (!response.ok) throw new Error('Save failed');
      setFileData(prev => prev ? { ...prev, hasChanges: false } : null);
    } catch (err) {
      console.error('[ArtifactPanel] Save error:', err);
    } finally {
      setIsSaving(false);
    }
  }, [fileData]);

  // MARKER_136.W3C: Global keyboard shortcut listeners (Ctrl+S, Ctrl+Z)
  useEffect(() => {
    const handleGlobalSave = () => {
      // If editing raw content, save via onContentChange callback
      if (isEditing && rawHasChanges && onContentChange) {
        onContentChange(editableContent);
        setRawHasChanges(false);
      }
      // If editing file, save via saveFile
      else if (fileData?.hasChanges) {
        saveFile();
      }
    };

    const handleGlobalUndo = () => {
      if (isEditing) {
        handleUndo();
      }
    };

    window.addEventListener('vetka-save-file', handleGlobalSave);
    window.addEventListener('vetka-undo', handleGlobalUndo);

    return () => {
      window.removeEventListener('vetka-save-file', handleGlobalSave);
      window.removeEventListener('vetka-undo', handleGlobalUndo);
    };
  }, [isEditing, rawHasChanges, editableContent, onContentChange, fileData, saveFile, handleUndo]);

  // Actions
  const handleCopy = () => navigator.clipboard.writeText(fileData?.content || '');
  const handleDownload = () => {
    if (!fileData) return;
    const filename = fileData.path.split('/').pop() || 'file';
    const blob = new Blob([fileData.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Phase 48.5.1: Render raw content
  // Phase 60.4: Added editing support
  // MARKER_104_VISUAL - L2 approval editing with subtle gray styling
  const renderRawContent = () => {
    if (!rawContent) return null;

    const contentToShow = isEditing ? editableContent : rawContent.content;

    // MARKER_104_VISUAL - L2 subtle gray styling for approval editing
    const isL2Editing = currentApprovalLevel === 'L2' && isEditing;

    // Phase 60.4: Editing mode - textarea for all types
    // MARKER_104_VISUAL - Enhanced with L2 subtle styling
    if (isEditing) {
      return (
        <div style={{
          height: '100%',
          overflow: 'auto',
          padding: 12,
          // MARKER_104_VISUAL - Subtle background for L2 editing
          background: isL2Editing ? '#1a1a1a' : '#0a0a0a',
          opacity: isL2Editing ? 0.9 : 1,
        }}>
          <textarea
            value={editableContent}
            onChange={(e) => {
              setEditableContent(e.target.value);
              setRawHasChanges(true);
              // MARKER_104_VISUAL - Notify parent of L2 content change
              if (currentApprovalLevel === 'L2' && onContentChange) {
                onContentChange(e.target.value);
              }
            }}
            onBlur={() => {
              // Phase 60.4: Save state to undo history on blur (not every keystroke)
              pushToUndoHistory(editableContent);
            }}
            onKeyDown={(e) => {
              // Phase 60.4: Ctrl+Z / Cmd+Z for undo
              if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                e.preventDefault();
                handleUndo();
              }
            }}
            style={{
              width: '100%',
              height: '100%',
              minHeight: 300,
              padding: 16,
              // MARKER_104_VISUAL - L2 subtle gray styling (NO bright colors)
              background: isL2Editing ? '#1a1a1a' : '#111',
              border: '1px solid #333',
              borderRadius: isL2Editing ? 4 : 8,
              color: '#e0e0e0',
              fontSize: 14,
              lineHeight: 1.6,
              fontFamily: 'monospace',
              resize: 'none',
              outline: 'none',
              // MARKER_104_VISUAL - Subtle opacity for L2
              opacity: isL2Editing ? 0.9 : 1,
            }}
            placeholder={isL2Editing ? "L2 Edit: Modify staged artifact..." : "Edit content here..."}
          />
          {/* MARKER_104_VISUAL - L2 approval indicator */}
          {isL2Editing && (
            <div style={{
              position: 'absolute',
              top: 4,
              right: 8,
              fontSize: 10,
              color: '#666',
              fontFamily: 'monospace',
            }}>
              L2 EDIT
            </div>
          )}
        </div>
      );
    }

    // View mode
    switch (rawContent.type) {
      case 'web': {
        const markdownFallback = [
          `# ${rawContent.title || 'Web result'}`,
          '',
          rawContent.sourceUrl ? `Source: ${rawContent.sourceUrl}` : '',
          '',
          rawContent.content || '',
        ].join('\n');

        return (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
            <div style={{
              padding: '8px 12px',
              borderBottom: '1px solid #222',
              fontSize: 11,
              color: '#999',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ color: '#666', textTransform: 'uppercase', letterSpacing: 1 }}>web preview</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <button
                  onClick={() => setWebMode('live')}
                  style={{
                    border: '1px solid #333',
                    background: webMode === 'live' ? '#1f2937' : '#111',
                    color: webMode === 'live' ? '#d1e3ff' : '#999',
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Live web page mode"
                >
                  LIVE
                </button>
                <button
                  onClick={() => setWebMode('md')}
                  style={{
                    border: '1px solid #333',
                    background: webMode === 'md' ? '#1f2937' : '#111',
                    color: webMode === 'md' ? '#d1e3ff' : '#999',
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Markdown fallback mode"
                >
                  MD
                </button>
              </div>
              {rawContent.sourceUrl && (
                <a
                  href={rawContent.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#8ab4f8', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={rawContent.sourceUrl}
                >
                  {rawContent.sourceUrl}
                </a>
              )}
              {isTauri() && rawContent.sourceUrl && (
                <button
                  onClick={async () => {
                    if (!rawContent.sourceUrl || openingNativeWeb) return;
                    setOpeningNativeWeb(true);
                    try {
                      await openLiveWebWindow(rawContent.sourceUrl, rawContent.title || 'VETKA Live Web');
                    } finally {
                      setOpeningNativeWeb(false);
                    }
                  }}
                  style={{
                    marginLeft: 'auto',
                    border: '1px solid #2f3f57',
                    background: '#111827',
                    color: '#a6c8ff',
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 4,
                    cursor: openingNativeWeb ? 'wait' : 'pointer',
                    opacity: openingNativeWeb ? 0.7 : 1,
                  }}
                  title="Open in native Tauri live window"
                >
                  {openingNativeWeb ? 'OPENING...' : 'NATIVE WINDOW'}
                </button>
              )}
            </div>
            <div style={{ flex: 1, minHeight: 0 }}>
              {webMode === 'live' && rawContent.sourceUrl ? (
                <iframe
                  title={rawContent.title || 'Web preview'}
                  src={rawContent.sourceUrl}
                  // MARKER_139.S1_4_WEB_LIVE_DEFAULT: Relaxed sandbox for auth/session-heavy websites
                  sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-downloads"
                  referrerPolicy="strict-origin-when-cross-origin"
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    background: '#fff',
                  }}
                />
              ) : webMode === 'md' ? (
                <MarkdownViewer content={markdownFallback} />
              ) : (
                <div style={{ padding: 16, color: '#777', fontSize: 12 }}>
                  Web URL is missing.
                </div>
              )}
            </div>
            {!!contentToShow && (
              <div style={{ borderTop: '1px solid #222', padding: '8px 12px', fontSize: 11, color: '#888' }}>
                {contentToShow}
              </div>
            )}
          </div>
        );
      }
      case 'markdown':
        return <MarkdownViewer content={contentToShow} />;
      case 'code':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={contentToShow}
              filename="response.txt"
              readOnly={true}
              onChange={() => {}}
            />
          </Suspense>
        );
      default:
        // Plain text - use pre with styling
        return (
          <div style={{
            height: '100%',
            overflow: 'auto',
            padding: 20,
            background: '#0a0a0a'
          }}>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: '#e0e0e0',
              fontSize: 14,
              lineHeight: 1.6,
              margin: 0,
              fontFamily: 'inherit'
            }}>
              {contentToShow}
            </pre>
          </div>
        );
    }
  };

  // Render viewer based on file type
  const renderViewer = () => {
    if (!fileData || !file) return null;
    const { content, path } = fileData;
    const filename = file.name;
    const fileType = getViewerType(filename);
    const fileUrl = `/api/files/raw?path=${encodeURIComponent(path)}`;

    if (/^https?:\/\//i.test(path)) {
      return <MarkdownViewer content={content} />;
    }

    switch (fileType) {
      case 'code':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={content}
              filename={filename}
              readOnly={!isEditing}
              onChange={updateContent}
            />
          </Suspense>
        );
      case 'markdown':
        // Phase 60.4: Support editing for markdown files
        if (isEditing) {
          return (
            <div style={{
              height: '100%',
              overflow: 'auto',
              padding: 12,
              background: '#0a0a0a'
            }}>
              <textarea
                value={content}
                onChange={(e) => updateContent(e.target.value)}
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: 400,
                  padding: 16,
                  background: '#111',
                  border: '1px solid #333',
                  borderRadius: 8,
                  color: '#e0e0e0',
                  fontSize: 14,
                  lineHeight: 1.6,
                  fontFamily: 'monospace',
                  resize: 'none',
                  outline: 'none',
                }}
                placeholder="Edit markdown here..."
              />
            </div>
          );
        }
        return <MarkdownViewer content={content} />;
      case 'image':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <ImageViewer url={fileUrl} filename={filename} />
          </Suspense>
        );
      default:
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={content}
              filename={filename}
              readOnly={!isEditing}
              onChange={updateContent}
            />
          </Suspense>
        );
    }
  };

  // Phase 48.5.1: Copy raw content
  // Phase 60.4: Copy current content (edited or original)
  const handleCopyRaw = () => navigator.clipboard.writeText(isEditing ? editableContent : (rawContent?.content || ''));

  // Phase 60.4: Save edited raw content
  const handleSaveRaw = () => {
    if (onContentChange && rawHasChanges) {
      onContentChange(editableContent);
      setRawHasChanges(false);
      setIsEditing(false);
    }
  };

  // Phase 60.4: Open file in Finder (macOS)
  const handleOpenInFinder = async () => {
    if (!fileData?.path) return;
    try {
      await fetch('/api/files/open-in-finder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fileData.path }),
      });
    } catch (err) {
      console.error('[ArtifactPanel] Open in Finder error:', err);
    }
  };

  // Phase 60.4: Save As / Duplicate - download with custom name
  const handleSaveAs = () => {
    const content = isRawContentMode
      ? (isEditing ? editableContent : rawContent?.content || '')
      : (fileData?.content || '');
    const defaultName = isRawContentMode
      ? 'artifact.md'
      : (fileData?.path.split('/').pop() || 'file.txt');

    const newName = prompt('Save as:', defaultName);
    if (!newName) return;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = newName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0a',
      position: 'relative',
    }}>
      {/* Loading overlay */}
      {isLoading && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(10, 10, 10, 0.8)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Loader2 size={32} color="#666" style={{ animation: 'spin 1s linear infinite' }} />
        </div>
      )}

      {/* Phase 48.5.1: Raw content mode */}
      {/* Phase 60.4: Added editing support */}
      {isRawContentMode && rawContent && (
        <>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {renderRawContent()}
          </div>
          <Toolbar
            filename={rawContent.title}
            fileSize={isEditing ? editableContent.length : rawContent.content.length}
            isEditing={isEditing && rawContent.type !== 'web'}
            hasChanges={rawHasChanges}
            isSaving={false}
            canUndo={canUndo}
            onEdit={rawContent.type === 'web' ? undefined : () => setIsEditing(!isEditing)}
            onUndo={rawContent.type === 'web' ? undefined : handleUndo}
            onSave={rawContent.type === 'web' ? undefined : handleSaveRaw}
            onSaveAs={handleSaveAs}
            onCopy={handleCopyRaw}
            onDownload={() => {
              const content = isEditing ? editableContent : rawContent.content;
              const blob = new Blob([content], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'response.txt';
              a.click();
              URL.revokeObjectURL(url);
            }}
            onRefresh={() => {}}
            onClose={onClose}
          />
        </>
      )}

      {/* File mode - Empty state */}
      {!isRawContentMode && !file && !isLoading && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
        }}>
          <p>Select a file to view</p>
        </div>
      )}

      {/* File mode - Viewer */}
      {!isRawContentMode && fileData && (
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {renderViewer()}
        </div>
      )}

      {/* File mode - Toolbar */}
      {!isRawContentMode && fileData && (
        <Toolbar
          filename={file?.name || ''}
          filePath={fileData.path}
          fileSize={fileData.fileSize}
          isEditing={isEditing}
          hasChanges={fileData.hasChanges}
          isSaving={isSaving}
          onEdit={() => setIsEditing(!isEditing)}
          onSave={saveFile}
          onSaveAs={handleSaveAs}
          onCopy={handleCopy}
          onDownload={handleDownload}
          onOpenInFinder={handleOpenInFinder}
          onRefresh={() => file && loadFile(file.path)}
          onClose={onClose}
        />
      )}
    </div>
  );
}
