/**
 * MARKER_MULTICAM_VIEWER: Multicam angle grid viewer.
 *
 * FCP7 Ch.46-47: Multiclip viewer shows all camera angles in grid.
 * Click angle during playback = cut to that angle on timeline.
 *
 * Grid layouts: 2x2 (4 angles), 3x3 (9 angles), 1+3 (1 big + 3 small).
 * Active angle highlighted with border.
 *
 * MARKER_B94: Real video previews per angle via <video> elements synced to
 * store currentTime + angle.offset_sec. Replaces placeholder divs.
 */
import { useMemo, useRef, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

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

const VIDEO: CSSProperties = {
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  pointerEvents: 'none',
};

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

// ─── Angle video cell ───

interface AngleCellProps {
  sourcePath: string;
  offsetSec: number;
  label: string;
  index: number;
  isActive: boolean;
  onClick: () => void;
}

function AngleCell({ sourcePath, offsetSec, label, index, isActive, onClick }: AngleCellProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);

  const src = useMemo(
    () => `${API_BASE}/files/raw?path=${encodeURIComponent(sourcePath)}`,
    [sourcePath],
  );

  // Sync time: currentTime + offset
  useEffect(() => {
    const el = videoRef.current;
    if (!el || !el.readyState) return;
    const targetTime = Math.max(0, currentTime + offsetSec);
    if (Math.abs(el.currentTime - targetTime) > 0.15) {
      el.currentTime = targetTime;
    }
  }, [currentTime, offsetSec]);

  // Play/pause sync
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    if (isPlaying) {
      el.play().catch(() => {});
    } else {
      el.pause();
    }
  }, [isPlaying]);

  const handleLoadedMetadata = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = Math.max(0, currentTime + offsetSec);
    if (!isPlaying) el.pause();
  }, [currentTime, offsetSec, isPlaying]);

  return (
    <div
      style={isActive ? CELL_ACTIVE : CELL}
      data-testid={`multicam-angle-${index}`}
      onClick={onClick}
    >
      <video
        ref={videoRef}
        src={src}
        style={VIDEO}
        muted
        playsInline
        preload="metadata"
        onLoadedMetadata={handleLoadedMetadata}
      />
      <div style={ANGLE_NUM}>{index + 1}</div>
      <div style={LABEL}>{label}</div>
    </div>
  );
}

// ─── Main grid ───

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
        <AngleCell
          key={angle.source_path}
          sourcePath={angle.source_path}
          offsetSec={angle.offset_sec || 0}
          label={angle.label || basename(angle.source_path)}
          index={i}
          isActive={i === activeAngle}
          onClick={() => switchAngle(i)}
        />
      ))}
    </div>
  );
}
