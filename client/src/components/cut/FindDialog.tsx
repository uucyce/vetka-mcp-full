/**
 * MARKER_FCP7-FIND: Find dialog overlay — FCP7 Ch.10 Edit > Find (Cmd+F)
 *
 * Searches for clips on the timeline by name/filename.
 * Non-destructive: just highlights matching clips via store state.
 *
 * @status: IMPLEMENTED
 * @fcp7: Ch.10
 */
import { type ChangeEvent, type KeyboardEvent, useEffect, useRef } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

export default function FindDialog() {
  const showFindDialog = useCutEditorStore((s) => s.showFindDialog);
  const findQuery = useCutEditorStore((s) => s.findQuery);
  const setFindQuery = useCutEditorStore((s) => s.setFindQuery);
  const setShowFindDialog = useCutEditorStore((s) => s.setShowFindDialog);
  const lanes = useCutEditorStore((s) => s.lanes);
  const inputRef = useRef<HTMLInputElement>(null);

  // Count matching clips across all lanes
  const matchCount = findQuery.trim()
    ? lanes.reduce((total, lane) => {
        const q = findQuery.toLowerCase();
        return total + lane.clips.filter((clip) => {
          const name = clip.source_path.split('/').pop() ?? '';
          return name.toLowerCase().includes(q);
        }).length;
      }, 0)
    : 0;

  // Focus input when dialog opens
  useEffect(() => {
    if (showFindDialog) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [showFindDialog]);

  if (!showFindDialog) return null;

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setShowFindDialog(false);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFindQuery(e.target.value);
  };

  return (
    <div
      data-overlay="1"
      data-testid="find-dialog-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 8000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: 80,
        background: 'rgba(0,0,0,0.45)',
      }}
      onClick={() => setShowFindDialog(false)}
    >
      <div
        data-testid="find-dialog"
        style={{
          background: '#1a1a1a',
          border: '1px solid #444',
          borderRadius: 4,
          padding: '12px 16px',
          width: 360,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <span style={{ color: '#ccc', fontSize: 11, fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
            Find
          </span>
          {findQuery.trim() && (
            <span style={{ color: '#888', fontSize: 10 }}>
              {matchCount} clip{matchCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={findQuery}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Clip name or filename…"
          data-testid="find-dialog-input"
          style={{
            background: '#0d0d0d',
            border: '1px solid #444',
            borderRadius: 3,
            color: '#fff',
            fontSize: 12,
            padding: '6px 10px',
            outline: 'none',
            width: '100%',
            boxSizing: 'border-box',
          }}
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        />
        <div style={{ color: '#555', fontSize: 10, marginTop: 2 }}>
          Esc to close · matches highlighted on timeline
        </div>
      </div>
    </div>
  );
}
