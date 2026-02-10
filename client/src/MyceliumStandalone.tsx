/**
 * MyceliumStandalone — Standalone wrapper for MCC window
 * MARKER_134.C34C: Separate Tauri window for autonomous monitoring
 * MARKER_135.1H: Added DAG/Tabs toggle (Phase 135)
 *
 * @status active
 * @phase 135
 */
import { useState } from 'react';
import { DevPanel } from './components/panels/DevPanel';
import { MyceliumCommandCenter } from './components/mcc/MyceliumCommandCenter';

type ViewMode = 'dag' | 'tabs';

export default function MyceliumStandalone() {
  const [viewMode, setViewMode] = useState<ViewMode>('dag');

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#0a0a0a',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* View mode toggle */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        padding: '4px 8px',
        borderBottom: '1px solid #222',
      }}>
        <button
          onClick={() => setViewMode(v => v === 'dag' ? 'tabs' : 'dag')}
          style={{
            background: 'transparent',
            border: '1px solid #333',
            borderRadius: 3,
            padding: '4px 10px',
            color: '#888',
            fontSize: 10,
            fontFamily: 'monospace',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span style={{ opacity: viewMode === 'dag' ? 1 : 0.5 }}>DAG</span>
          <span style={{ color: '#444' }}>|</span>
          <span style={{ opacity: viewMode === 'tabs' ? 1 : 0.5 }}>Tabs</span>
        </button>
      </div>

      {/* Content based on view mode */}
      <div style={{ flex: 1, minHeight: 0 }}>
        {viewMode === 'dag' ? (
          <MyceliumCommandCenter standalone={true} />
        ) : (
          <DevPanel standalone={true} />
        )}
      </div>
    </div>
  );
}
