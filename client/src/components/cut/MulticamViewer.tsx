/**
 * MARKER_MULTICAM_VIEWER: Multicam angle grid viewer.
 *
 * FCP7 Ch.46-47: Multiclip viewer shows all camera angles in grid.
 * Click angle during playback = cut to that angle on timeline.
 *
 * Grid layouts: 2x2 (4 angles), 3x3 (9 angles), 1+3 (1 big + 3 small).
 * Active angle highlighted with border.
 */
import { useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const GRID: CSSProperties = {
  display: 'grid',
  gap: 1,
  width: '100%',
  height: '100%',
  background: '#000',
};

const CELL: CSSProperties = {
  position: 'relative',
  background: '#0a0a0a',
  overflow: 'hidden',
  cursor: 'pointer',
  border: '1px solid transparent',
};

const CELL_ACTIVE: CSSProperties = {
  ...CELL,
  border: '1px solid #999',
};

const LABEL: CSSProperties = {
  position: 'absolute',
  bottom: 2,
  left: 4,
  fontSize: 9,
  fontFamily: 'monospace',
  color: '#aaa',
  textShadow: '0 1px 2px rgba(0,0,0,0.9)',
  pointerEvents: 'none',
  userSelect: 'none',
};

const ANGLE_NUM: CSSProperties = {
  position: 'absolute',
  top: 2,
  right: 4,
  fontSize: 11,
  fontWeight: 700,
  fontFamily: 'monospace',
  color: '#666',
  pointerEvents: 'none',
  userSelect: 'none',
};

const EMPTY: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#333',
  fontSize: 11,
  userSelect: 'none',
};

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

export default function MulticamViewer() {
  const multicamMode = useCutEditorStore((s) => s.multicamMode);
  const angles = useCutEditorStore((s) => s.multicamAngles);
  const activeAngle = useCutEditorStore((s) => s.multicamActiveAngle);
  const switchAngle = useCutEditorStore((s) => s.multicamSwitchAngle);

  const gridCols = useMemo(() => {
    if (angles.length <= 1) return 1;
    if (angles.length <= 4) return 2;
    return 3;
  }, [angles.length]);

  if (!multicamMode || angles.length === 0) {
    return <div style={EMPTY}>No multicam clip loaded</div>;
  }

  return (
    <div
      style={{ ...GRID, gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
      data-testid="multicam-viewer-grid"
    >
      {angles.map((angle, i) => (
        <div
          key={angle.source_path}
          style={i === activeAngle ? CELL_ACTIVE : CELL}
          data-testid={`multicam-angle-${i}`}
          onClick={() => switchAngle(i)}
        >
          {/* Angle preview placeholder — VideoPreview integration needed */}
          <div style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: i === activeAngle ? '#1a1a1a' : '#0d0d0d',
          }}>
            <span style={{ color: '#333', fontSize: 20, fontWeight: 700 }}>
              {i + 1}
            </span>
          </div>
          <div style={ANGLE_NUM}>{i + 1}</div>
          <div style={LABEL}>{angle.label || basename(angle.source_path)}</div>
        </div>
      ))}
    </div>
  );
}
