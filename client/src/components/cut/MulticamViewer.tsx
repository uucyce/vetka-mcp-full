/**
 * MARKER_MULTICAM_VIEWER: Multicam angle grid viewer.
 *
 * FCP7 Ch.46-47: Multiclip viewer shows all camera angles in grid.
 * Click angle during playback = cut to that angle on timeline.
 *
 * Grid layouts: 2x2 (4 angles), 3x3 (9 angles), 1+3 (1 big + 3 small).
 * Active angle highlighted with border.
 */
import { useMemo, useState, useEffect, useRef, type CSSProperties } from 'react';
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

const THUMB_IMG: CSSProperties = {
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  display: 'block',
};

const THUMB_FALLBACK: CSSProperties = {
  width: '100%',
  height: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: '#0d0d0d',
};

// Debounced thumbnail that updates on playhead scrub
const thumbCache = new Map<string, string>();

function AngleThumbnail({ sourcePath, timeSec, isActive }: {
  sourcePath: string;
  timeSec: number;
  isActive: boolean;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFetchedRef = useRef<string>('');

  useEffect(() => {
    // Debounce thumbnail fetches during scrub (300ms)
    if (timerRef.current) clearTimeout(timerRef.current);

    const fetchKey = `${sourcePath}@${timeSec.toFixed(1)}`;
    if (fetchKey === lastFetchedRef.current) return;

    timerRef.current = setTimeout(() => {
      const url = `${API_BASE}/cut/thumbnail?source_path=${encodeURIComponent(sourcePath)}&time_sec=${timeSec.toFixed(2)}&width=240&height=135`;

      const cached = thumbCache.get(url);
      if (cached) {
        setSrc(cached);
        lastFetchedRef.current = fetchKey;
        return;
      }

      let cancelled = false;
      fetch(url)
        .then((r) => r.ok ? r.blob() : null)
        .then((blob) => {
          if (cancelled || !blob) return;
          const objectUrl = URL.createObjectURL(blob);
          thumbCache.set(url, objectUrl);
          setSrc(objectUrl);
          lastFetchedRef.current = fetchKey;
          setError(false);
        })
        .catch(() => {
          if (!cancelled) setError(true);
        });

      return () => { cancelled = true; };
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [sourcePath, timeSec]);

  if (error || !src) {
    return (
      <div style={{ ...THUMB_FALLBACK, background: isActive ? '#1a1a1a' : '#0d0d0d' }}>
        <span style={{ color: '#333', fontSize: 10 }}>No preview</span>
      </div>
    );
  }

  return <img src={src} alt="angle" style={THUMB_IMG} />;
}

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

export default function MulticamViewer() {
  const multicamMode = useCutEditorStore((s) => s.multicamMode);
  const angles = useCutEditorStore((s) => s.multicamAngles);
  const activeAngle = useCutEditorStore((s) => s.multicamActiveAngle);
  const switchAngle = useCutEditorStore((s) => s.multicamSwitchAngle);
  const currentTime = useCutEditorStore((s) => s.currentTime);

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
          <AngleThumbnail
            sourcePath={angle.source_path}
            timeSec={currentTime}
            isActive={i === activeAngle}
          />
          <div style={ANGLE_NUM}>{i + 1}</div>
          <div style={LABEL}>{angle.label || basename(angle.source_path)}</div>
        </div>
      ))}
    </div>
  );
}
