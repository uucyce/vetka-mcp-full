/**
 * MARKER_W4.4: History Panel — visual undo/redo list (like Photoshop History).
 * Shows ordered list of edit operations from the undo stack.
 * Click entry → revert to that state. Entries above current = grayed (redo-able).
 * Mounted in Analysis tab group (left_bottom).
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

type HistoryEntry = {
  index: number;
  label: string;
  timestamp?: string;
};

type UndoStackResponse = {
  success: boolean;
  undo_depth: number;
  redo_depth: number;
  can_undo: boolean;
  can_redo: boolean;
  max_depth: number;
  labels: string[];
};

const CONTAINER: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  background: '#0a0a0a',
  color: '#999',
  fontSize: 11,
  fontFamily: 'system-ui',
  overflow: 'hidden',
};

const HEADER: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '6px 10px',
  borderBottom: '1px solid #1a1a1a',
  flexShrink: 0,
};

const LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '2px 0',
};

const ENTRY_BASE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '5px 10px',
  cursor: 'pointer',
  border: 'none',
  background: 'transparent',
  width: '100%',
  textAlign: 'left',
  fontFamily: 'system-ui',
  fontSize: 11,
};

export default function HistoryPanel() {
  const projectId = useCutEditorStore((s) => s.projectId);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const timelineId = useCutEditorStore((s) => s.timelineId);

  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [undoDepth, setUndoDepth] = useState(0);
  const [redoDepth, setRedoDepth] = useState(0);
  const [loading, setLoading] = useState(false);

  // Current position in history = total entries - redo_depth
  const totalEntries = entries.length;
  const currentIndex = totalEntries - redoDepth;

  const fetchStack = useCallback(async () => {
    if (!projectId || !sandboxRoot || !timelineId) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        sandbox_root: sandboxRoot,
        project_id: projectId,
        timeline_id: timelineId,
      });
      const res = await fetch(`${API_BASE}/cut/undo-stack?${params}`);
      if (!res.ok) return;
      const data: UndoStackResponse = await res.json();
      const items: HistoryEntry[] = data.labels.map((label, i) => ({
        index: i,
        label,
      }));
      // Always add "Open Project" as base entry
      if (items.length === 0) {
        items.push({ index: 0, label: 'Open Project' });
      }
      setEntries(items);
      setUndoDepth(data.undo_depth);
      setRedoDepth(data.redo_depth);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [projectId, sandboxRoot, timelineId]);

  // Poll undo stack periodically (every 3s when visible)
  useEffect(() => {
    fetchStack();
    const interval = setInterval(fetchStack, 3000);
    return () => clearInterval(interval);
  }, [fetchStack]);

  const handleUndoTo = useCallback(async (targetIndex: number) => {
    if (!projectId || !sandboxRoot || !timelineId) return;
    const stepsBack = currentIndex - targetIndex;
    if (stepsBack <= 0) return; // can't undo forward

    for (let i = 0; i < stepsBack; i++) {
      await fetch(`${API_BASE}/cut/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId,
        }),
      });
    }
    fetchStack();
  }, [projectId, sandboxRoot, timelineId, currentIndex, fetchStack]);

  const handleRedoTo = useCallback(async (targetIndex: number) => {
    if (!projectId || !sandboxRoot || !timelineId) return;
    const stepsForward = targetIndex - currentIndex;
    if (stepsForward <= 0) return;

    for (let i = 0; i < stepsForward; i++) {
      await fetch(`${API_BASE}/cut/redo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId,
        }),
      });
    }
    fetchStack();
  }, [projectId, sandboxRoot, timelineId, currentIndex, fetchStack]);

  const handleClick = useCallback((index: number) => {
    if (index < currentIndex) {
      handleUndoTo(index);
    } else if (index > currentIndex) {
      handleRedoTo(index);
    }
  }, [currentIndex, handleUndoTo, handleRedoTo]);

  if (!projectId) {
    return (
      <div style={{ ...CONTAINER, justifyContent: 'center', alignItems: 'center' }}>
        <span style={{ color: '#555' }}>No project loaded</span>
      </div>
    );
  }

  return (
    <div style={CONTAINER}>
      <div style={HEADER}>
        <span style={{ color: '#777', fontWeight: 500 }}>History</span>
        <span style={{ color: '#444', fontSize: 10 }}>
          {undoDepth > 0 ? `${undoDepth} undo` : ''}
          {redoDepth > 0 ? ` / ${redoDepth} redo` : ''}
        </span>
      </div>
      <div style={LIST}>
        {entries.length === 0 && !loading ? (
          <div style={{ padding: 12, color: '#444', textAlign: 'center' }}>
            No edit history yet
          </div>
        ) : (
          entries.map((entry, idx) => {
            const isCurrent = idx === currentIndex - 1;
            const isRedoable = idx >= currentIndex;
            return (
              <button
                key={idx}
                onClick={() => handleClick(idx)}
                style={{
                  ...ENTRY_BASE,
                  color: isRedoable ? '#3a3a3a' : isCurrent ? '#e0e0e0' : '#888',
                  background: isCurrent ? '#1a1a1a' : 'transparent',
                  borderLeft: isCurrent ? '2px solid #999' : '2px solid transparent',
                }}
              >
                <span style={{
                  width: 16,
                  flexShrink: 0,
                  color: '#444',
                  fontSize: 9,
                  textAlign: 'right',
                  marginRight: 8,
                }}>
                  {idx + 1}
                </span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {entry.label}
                </span>
                {isCurrent && (
                  <span style={{ color: '#999', fontSize: 9, marginLeft: 6, flexShrink: 0 }}>
                    current
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
