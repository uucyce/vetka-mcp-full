/**
 * MARKER_GAMMA-MON1: FCP7 Source Monitor action buttons.
 *
 * Standalone row of buttons rendered below MonitorTransport in Source panel.
 * FCP7 convention: Source viewer has dedicated Insert/Overwrite/Mark Clip buttons.
 *
 * Integration: SourceMonitorPanel.tsx adds <SourceMonitorButtons /> below MonitorTransport.
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const ROW_STYLE: CSSProperties = {
  display: 'flex',
  gap: 2,
  padding: '2px 4px',
  background: '#0d0d0d',
  borderTop: '1px solid #1a1a1a',
  justifyContent: 'center',
  flexShrink: 0,
};

const BTN_STYLE: CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 3,
  color: '#aaa',
  fontSize: 10,
  fontFamily: 'system-ui, -apple-system, sans-serif',
  padding: '3px 8px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  minWidth: 24,
  minHeight: 24,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  userSelect: 'none',
  transition: 'background 0.1s, color 0.1s',
};

const BTN_HOVER: CSSProperties = {
  background: '#333',
  color: '#ddd',
};

interface ButtonDef {
  label: string;
  title: string;
  action: () => void;
}

export default function SourceMonitorButtons() {
  const store = useCutEditorStore;

  const handleMarkClip = useCallback(() => {
    store.getState().markClip?.();
  }, []);

  const handleMatchFrame = useCallback(() => {
    store.getState().matchFrame?.();
  }, []);

  const handleInsert = useCallback(() => {
    store.getState().insertEdit?.();
  }, []);

  const handleOverwrite = useCallback(() => {
    store.getState().overwriteEdit?.();
  }, []);

  const buttons: ButtonDef[] = [
    { label: 'X', title: 'Mark Clip (X)', action: handleMarkClip },
    { label: 'F', title: 'Match Frame (F)', action: handleMatchFrame },
    { label: ',', title: 'Insert Edit (,)', action: handleInsert },
    { label: '.', title: 'Overwrite Edit (.)', action: handleOverwrite },
  ];

  return (
    <div style={ROW_STYLE} data-testid="source-monitor-buttons">
      {buttons.map((btn) => (
        <button
          key={btn.label}
          style={BTN_STYLE}
          title={btn.title}
          onClick={btn.action}
          onMouseEnter={(e) => Object.assign(e.currentTarget.style, BTN_HOVER)}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#1a1a1a';
            e.currentTarget.style.color = '#aaa';
          }}
        >
          {btn.label}
        </button>
      ))}
    </div>
  );
}
