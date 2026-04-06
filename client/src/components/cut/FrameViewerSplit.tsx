/**
 * MARKER_FRAME_SPLIT: Frame Viewer Split — compare original vs color-graded.
 *
 * FCP7 Frame Viewer: split screen with adjustable split position.
 * Left = original frame, Right = color-corrected (CSS filter applied).
 * Drag the split line to adjust. Toggle via store.showFrameViewerSplit.
 *
 * Renders as overlay inside VideoPreview container.
 * Uses clip-path CSS to mask the two halves of the same video.
 *
 * Monochrome — split line is #888, labels are #666.
 *
 * @phase FRAME_VIEWER
 * @task tb_1774312382_55
 */
import { useState, useCallback, useRef, useEffect, type CSSProperties, type MouseEvent } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Styles ───

const OVERLAY: CSSProperties = {
  position: 'absolute',
  inset: 0,
  zIndex: 10,
  overflow: 'hidden',
  cursor: 'default',
};

const VIDEO_BASE: CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  objectFit: 'contain',
  pointerEvents: 'none',
};

const SPLIT_LINE: CSSProperties = {
  position: 'absolute',
  top: 0,
  width: 2,
  height: '100%',
  background: '#888',
  cursor: 'ew-resize',
  zIndex: 12,
  boxShadow: '0 0 6px rgba(0,0,0,0.8)',
};

const SPLIT_HANDLE: CSSProperties = {
  position: 'absolute',
  top: '50%',
  left: -6,
  width: 14,
  height: 28,
  marginTop: -14,
  background: '#333',
  border: '1px solid #666',
  borderRadius: 3,
  cursor: 'ew-resize',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const LABEL: CSSProperties = {
  position: 'absolute',
  bottom: 28,
  fontSize: 9,
  fontFamily: 'system-ui',
  color: '#666',
  background: 'rgba(0,0,0,0.6)',
  padding: '1px 6px',
  borderRadius: 2,
  textTransform: 'uppercase',
  letterSpacing: 0.5,
  userSelect: 'none',
  pointerEvents: 'none',
  zIndex: 13,
};

// ─── Component ───

interface FrameViewerSplitProps {
  /** Video source URL */
  videoSrc: string;
  /** CSS filter string for the graded side (right) */
  gradedFilter?: string;
  /** Poster image URL */
  poster?: string;
}

export default function FrameViewerSplit({ videoSrc, gradedFilter, poster }: FrameViewerSplitProps) {
  const [splitRatio, setSplitRatio] = useState(0.5);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const originalVideoRef = useRef<HTMLVideoElement>(null);
  const gradedVideoRef = useRef<HTMLVideoElement>(null);

  // Sync both videos to store's currentTime
  const currentTime = useCutEditorStore((s) => s.currentTime);

  useEffect(() => {
    const syncVideo = (video: HTMLVideoElement | null) => {
      if (!video || !video.src) return;
      if (Math.abs(video.currentTime - currentTime) > 0.15) {
        video.currentTime = currentTime;
      }
    };
    syncVideo(originalVideoRef.current);
    syncVideo(gradedVideoRef.current);
  }, [currentTime]);

  // Drag handler
  const handleMouseDown = useCallback((e: MouseEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (e: globalThis.MouseEvent) => {
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const ratio = Math.max(0.05, Math.min(0.95, (e.clientX - rect.left) / rect.width));
      setSplitRatio(ratio);
    };

    const handleUp = () => setDragging(false);

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
  }, [dragging]);

  const splitPct = `${(splitRatio * 100).toFixed(1)}%`;

  return (
    <div ref={containerRef} style={OVERLAY} data-testid="frame-viewer-split">
      {/* Original (left side) — no filter */}
      <video
        ref={originalVideoRef}
        src={videoSrc}
        poster={poster}
        style={{
          ...VIDEO_BASE,
          clipPath: `inset(0 ${100 - splitRatio * 100}% 0 0)`,
        }}
        preload="metadata"
        playsInline
        muted
      />

      {/* Graded (right side) — with CSS filter */}
      <video
        ref={gradedVideoRef}
        src={videoSrc}
        poster={poster}
        style={{
          ...VIDEO_BASE,
          clipPath: `inset(0 0 0 ${splitRatio * 100}%)`,
          filter: gradedFilter || 'none',
        }}
        preload="metadata"
        playsInline
        muted
      />

      {/* Split line + handle */}
      <div
        style={{ ...SPLIT_LINE, left: splitPct, transform: 'translateX(-1px)' }}
        onMouseDown={handleMouseDown}
      >
        <div style={SPLIT_HANDLE}>
          {/* Grip dots */}
          <svg width="6" height="16" viewBox="0 0 6 16">
            {[2, 6, 10, 14].map((y) => (
              <circle key={y} cx="3" cy={y} r="1" fill="#888" />
            ))}
          </svg>
        </div>
      </div>

      {/* Labels */}
      <div style={{ ...LABEL, left: 8 }}>Original</div>
      <div style={{ ...LABEL, right: 8 }}>Graded</div>
    </div>
  );
}
