/**
 * MARKER_180.7: BPMTrack — Canvas-based BPM visualization track.
 * Renders 4 dot rows below the timeline ruler:
 *   🟢 Audio beats   (green  #5DCAA5)
 *   🔵 Visual cuts   (blue   #85B7EB)
 *   ⚪ Script events  (white  #E0E0E0)
 *   🟠 Sync points   (orange #FF9F43) — where 2-3 sources coincide
 *
 * Architecture doc §5.1:
 * "BPM display: three colored dots on timeline ruler (audio/visual/script).
 *  Orange dot = all-sync point (±2 frames tolerance)."
 *
 * §5.2: "Canvas rendering for dense beat grids (120+ BPM = 240+ dots per minute)."
 *
 * Props mirror TimelineTrackView scroll/zoom so dots align with clips.
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';

// ─── Types ───

interface BPMBeat {
  sec: number;
  bpm?: number;
  source: 'audio';
}

interface VisualCut {
  sec: number;
  source: 'visual';
}

interface ScriptEvent {
  sec: number;
  type?: string;
  energy?: number;
  scene_id?: string;
  source: 'script';
}

interface SyncPoint {
  sec: number;
  strength: number;       // 1.0 = triple sync, 0.67 = double
  sources: string[];
}

interface BPMMarkersData {
  audio_beats: BPMBeat[];
  visual_cuts: VisualCut[];
  script_events: ScriptEvent[];
  sync_points: SyncPoint[];
}

// ─── Config ───

const TRACK_HEIGHT = 36;              // total height for 4 rows
const ROW_HEIGHT = 8;                 // each dot row
const ROW_GAP = 1;                    // between rows
const DOT_RADIUS = 2;
const DOT_RADIUS_SYNC = 3;           // sync dots are larger
const MIN_DOT_SPACING_PX = 3;        // skip dots closer than this

// MARKER_GAMMA-P4.2: Monochrome palette — brightness differentiation only
const COLORS = {
  audio:   '#ccc',      // bright — audio beats
  visual:  '#888',      // medium — visual beats
  script:  '#E0E0E0',   // near-white — script beats
  sync:    '#fff',      // white — all-sync emphasis
  syncDim: '#777',      // dimmed — partial sync (0.67)
  bg:      '#111111',
  border:  '#333',
};

// ─── Styles ───

const CONTAINER: CSSProperties = {
  width: '100%',
  height: TRACK_HEIGHT,
  background: COLORS.bg,
  borderTop: `0.5px solid ${COLORS.border}`,
  position: 'relative',
  flexShrink: 0,
  overflow: 'hidden',
};

// ─── Props ───

interface BPMTrackProps {
  /** Timeline ID for fetching BPM markers */
  timelineId?: string;
  /** Script text for narrative BPM computation */
  scriptText?: string;
  /** Pixels per second — must match TimelineTrackView zoom */
  pxPerSec: number;
  /** Horizontal scroll offset in pixels — must match timeline scroll */
  scrollLeft: number;
  /** Total timeline duration in seconds (for canvas width) */
  durationSec: number;
  /** Left margin to align with lane headers */
  laneHeaderWidth?: number;
  /** Whether to show row labels */
  showLabels?: boolean;
}

export default function BPMTrack({
  timelineId = 'main',
  scriptText = '',
  pxPerSec,
  scrollLeft,
  durationSec,
  laneHeaderWidth = 76,
  showLabels = true,
}: BPMTrackProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<BPMMarkersData | null>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  // Sync store for BPM display values
  const setBPM = usePanelSyncStore((s) => s.setBPM);

  // ─── Fetch BPM markers from backend ───
  useEffect(() => {
    let cancelled = false;

    async function fetchMarkers() {
      try {
        const res = await fetch(`${API_BASE}/cut/pulse/bpm-markers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timeline_id: timelineId,
            script_text: scriptText,
          }),
        });
        if (!res.ok) return;
        const json = await res.json();
        if (!cancelled && json.success) {
          setData({
            audio_beats: json.audio_beats || [],
            visual_cuts: json.visual_cuts || [],
            script_events: json.script_events || [],
            sync_points: json.sync_points || [],
          });

          // Compute BPM display values and push to sync store
          const audioBPM = json.audio_beats?.length
            ? json.audio_beats[0]?.bpm ?? null
            : null;
          // Visual BPM = cuts per minute
          const totalDur = durationSec || 1;
          const visualBPM = json.visual_cuts?.length
            ? Math.round((json.visual_cuts.length / totalDur) * 60)
            : null;
          // Script BPM = events per minute
          const scriptBPM = json.script_events?.length
            ? Math.round((json.script_events.length / totalDur) * 60)
            : null;
          setBPM(audioBPM, visualBPM, scriptBPM);
        }
      } catch {
        // silently fail — BPM track is non-critical
      }
    }

    fetchMarkers();
    return () => { cancelled = true; };
  }, [timelineId, scriptText, durationSec, setBPM]);

  // ─── Track container width via ResizeObserver ───
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // ─── Canvas rendering ───
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;

    const dpr = window.devicePixelRatio || 1;
    const visibleWidth = containerWidth - laneHeaderWidth;
    canvas.width = visibleWidth * dpr;
    canvas.height = TRACK_HEIGHT * dpr;
    canvas.style.width = `${visibleWidth}px`;
    canvas.style.height = `${TRACK_HEIGHT}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, visibleWidth, TRACK_HEIGHT);

    // Row Y positions (top to bottom): audio, visual, script, sync
    const rows = [
      { y: ROW_GAP + ROW_HEIGHT / 2,                                  color: COLORS.audio,  items: data.audio_beats.map(b => b.sec) },
      { y: ROW_GAP + ROW_HEIGHT + ROW_GAP + ROW_HEIGHT / 2,           color: COLORS.visual, items: data.visual_cuts.map(v => v.sec) },
      { y: ROW_GAP + (ROW_HEIGHT + ROW_GAP) * 2 + ROW_HEIGHT / 2,     color: COLORS.script, items: data.script_events.map(s => s.sec) },
    ];

    // Draw dot rows
    for (const row of rows) {
      ctx.fillStyle = row.color;
      let lastPx = -Infinity;
      for (const sec of row.items) {
        const px = sec * pxPerSec - scrollLeft;
        // Skip off-screen or too close to previous dot
        if (px < -DOT_RADIUS || px > visibleWidth + DOT_RADIUS) continue;
        if (px - lastPx < MIN_DOT_SPACING_PX) continue;
        lastPx = px;

        ctx.beginPath();
        ctx.arc(px, row.y, DOT_RADIUS, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Draw sync points (bottom row, larger dots)
    const syncY = ROW_GAP + (ROW_HEIGHT + ROW_GAP) * 3 + ROW_HEIGHT / 2;
    let lastSyncPx = -Infinity;
    for (const sp of data.sync_points) {
      const px = sp.sec * pxPerSec - scrollLeft;
      if (px < -DOT_RADIUS_SYNC || px > visibleWidth + DOT_RADIUS_SYNC) continue;
      if (px - lastSyncPx < MIN_DOT_SPACING_PX) continue;
      lastSyncPx = px;

      // Full sync (3 sources) = bright orange, partial = dimmed
      ctx.fillStyle = sp.strength >= 1.0 ? COLORS.sync : COLORS.syncDim;
      ctx.beginPath();
      ctx.arc(px, syncY, DOT_RADIUS_SYNC, 0, Math.PI * 2);
      ctx.fill();

      // Full sync gets a subtle glow ring (exception to no-glow rule: functional indicator)
      if (sp.strength >= 1.0) {
        ctx.strokeStyle = COLORS.sync;
        ctx.globalAlpha = 0.3;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(px, syncY, DOT_RADIUS_SYNC + 2, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1.0;
      }
    }
  }, [data, pxPerSec, scrollLeft, containerWidth, laneHeaderWidth]);

  // Re-draw on any change
  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  return (
    <div ref={containerRef} style={CONTAINER}>
      {/* Row labels */}
      {showLabels && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: laneHeaderWidth,
            height: TRACK_HEIGHT,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-around',
            padding: '2px 4px',
            fontSize: 8,
            fontFamily: '"JetBrains Mono", monospace',
            color: '#555',
            userSelect: 'none',
            zIndex: 1,
          }}
        >
          <span style={{ color: COLORS.audio }}>♩ AUD</span>
          <span style={{ color: COLORS.visual }}>◆ VIS</span>
          <span style={{ color: COLORS.script }}>¶ SCR</span>
          <span style={{ color: COLORS.sync }}>● SYN</span>
        </div>
      )}

      {/* Canvas for dots */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          left: laneHeaderWidth,
          top: 0,
        }}
      />

      {/* Empty state */}
      {data && data.audio_beats.length === 0 && data.visual_cuts.length === 0 && data.script_events.length === 0 && (
        <div
          style={{
            position: 'absolute',
            left: laneHeaderWidth,
            top: 0,
            right: 0,
            height: TRACK_HEIGHT,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 9,
            color: '#444',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          No BPM data — import media to analyze rhythm
        </div>
      )}
    </div>
  );
}
