/**
 * MARKER_SCOPES: Video Scopes panel — Waveform, Vectorscope, Histogram.
 *
 * FCP7 Reference: Ch.78 "Measuring and Setting Video Levels"
 * Renders scope data from backend GET /cut/scopes/analyze onto canvas.
 *
 * Three modes (tabs):
 *   - Waveform: Y = luma (0-100 IRE), X = pixel column
 *   - Vectorscope: circular CbCr plot with skin tone line
 *   - Histogram: stacked R/G/B curves
 *
 * Updates on playhead change (debounced 200ms to avoid hammering backend).
 *
 * @phase SCOPES
 * @task tb_1773997178_1
 */
import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

type ScopeMode = 'waveform' | 'vectorscope' | 'histogram';

const PANEL_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#0a0a0a',
  color: '#ccc',
  fontSize: 11,
  fontFamily: 'system-ui',
  overflow: 'hidden',
};

const TAB_BAR: CSSProperties = {
  display: 'flex',
  gap: 0,
  background: '#111',
  borderBottom: '1px solid #222',
  flexShrink: 0,
};

const TAB_BTN: CSSProperties = {
  padding: '4px 12px',
  background: 'none',
  border: 'none',
  borderBottom: '2px solid transparent',
  color: '#888',
  fontSize: 10,
  cursor: 'pointer',
  fontWeight: 500,
};

const TAB_BTN_ACTIVE: CSSProperties = {
  ...TAB_BTN,
  color: '#ccc',
  borderBottomColor: '#4a9eff',
};

const CANVAS_WRAP: CSSProperties = {
  flex: 1,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 8,
  minHeight: 0,
};

const STATUS_BAR: CSSProperties = {
  padding: '2px 8px',
  fontSize: 9,
  color: '#555',
  borderTop: '1px solid #1a1a1a',
  flexShrink: 0,
};

type ScopeData = {
  histogram?: { r: number[]; g: number[]; b: number[] };
  waveform?: number[][];
  vectorscope?: number[][];
  frame_w?: number;
  frame_h?: number;
};

function drawWaveform(ctx: CanvasRenderingContext2D, data: number[][], w: number, h: number) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);

  if (!data.length) return;

  const scopeH = data.length;
  const scopeW = data[0].length;
  const scaleX = w / scopeW;
  const scaleY = h / scopeH;

  // Draw IRE reference lines
  ctx.strokeStyle = '#222';
  ctx.lineWidth = 1;
  for (const ire of [0, 25, 50, 75, 100]) {
    const y = h - (ire / 100) * h;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw waveform data — green phosphor look
  for (let sy = 0; sy < scopeH; sy++) {
    for (let sx = 0; sx < scopeW; sx++) {
      const val = data[sy][sx];
      if (val <= 0) continue;
      const alpha = Math.min(1, val / 180);
      ctx.fillStyle = `rgba(0, 200, 80, ${alpha})`;
      ctx.fillRect(sx * scaleX, sy * scaleY, Math.max(1, scaleX), Math.max(1, scaleY));
    }
  }

  // IRE labels
  ctx.fillStyle = '#555';
  ctx.font = '9px system-ui';
  for (const ire of [0, 50, 100]) {
    const y = h - (ire / 100) * h;
    ctx.fillText(`${ire}`, 2, y - 2);
  }
}

function drawVectorscope(ctx: CanvasRenderingContext2D, data: number[][], w: number, h: number) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);

  if (!data.length) return;

  const scopeSize = data.length;
  const scale = Math.min(w, h) / scopeSize;
  const offsetX = (w - scopeSize * scale) / 2;
  const offsetY = (h - scopeSize * scale) / 2;

  // Draw graticule circle
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) / 2 - 4;

  ctx.strokeStyle = '#222';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();

  // Crosshair
  ctx.beginPath();
  ctx.moveTo(cx, cy - radius);
  ctx.lineTo(cx, cy + radius);
  ctx.moveTo(cx - radius, cy);
  ctx.lineTo(cx + radius, cy);
  ctx.stroke();

  // Skin tone line (~123 degrees from Cb axis)
  ctx.strokeStyle = '#553300';
  ctx.lineWidth = 1;
  const skinAngle = (123 * Math.PI) / 180;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(skinAngle) * radius, cy - Math.sin(skinAngle) * radius);
  ctx.stroke();

  // Draw vectorscope data
  for (let sy = 0; sy < scopeSize; sy++) {
    for (let sx = 0; sx < scopeSize; sx++) {
      const val = data[sy][sx];
      if (val <= 0) continue;
      const alpha = Math.min(1, val / 200);
      ctx.fillStyle = `rgba(80, 180, 255, ${alpha})`;
      ctx.fillRect(
        offsetX + sx * scale,
        offsetY + sy * scale,
        Math.max(1, scale),
        Math.max(1, scale),
      );
    }
  }
}

function drawHistogram(
  ctx: CanvasRenderingContext2D,
  data: { r: number[]; g: number[]; b: number[] },
  w: number,
  h: number,
) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);

  const maxVal = Math.max(
    ...data.r.slice(1, 254),
    ...data.g.slice(1, 254),
    ...data.b.slice(1, 254),
    1,
  );

  const barW = w / 256;

  // Draw each channel with alpha blending
  const channels: { bins: number[]; color: string }[] = [
    { bins: data.r, color: 'rgba(255, 60, 60, 0.5)' },
    { bins: data.g, color: 'rgba(60, 255, 60, 0.5)' },
    { bins: data.b, color: 'rgba(60, 100, 255, 0.5)' },
  ];

  for (const ch of channels) {
    ctx.fillStyle = ch.color;
    for (let i = 0; i < 256; i++) {
      const barH = (ch.bins[i] / maxVal) * h;
      ctx.fillRect(i * barW, h - barH, Math.max(1, barW), barH);
    }
  }

  // Axis labels
  ctx.fillStyle = '#555';
  ctx.font = '9px system-ui';
  ctx.fillText('0', 2, h - 2);
  ctx.fillText('255', w - 22, h - 2);
}

export default function VideoScopes() {
  const [mode, setMode] = useState<ScopeMode>('waveform');
  const [scopeData, setScopeData] = useState<ScopeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fetchTimerRef = useRef<number | null>(null);

  const currentTime = useCutEditorStore((s) => s.currentTime);
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);

  // Use program media if available, fall back to source
  const mediaPath = programMediaPath || sourceMediaPath;

  // Debounced fetch — 200ms after playhead stops
  const fetchScopes = useCallback(
    (path: string, time: number) => {
      if (fetchTimerRef.current) {
        clearTimeout(fetchTimerRef.current);
      }
      fetchTimerRef.current = window.setTimeout(async () => {
        setLoading(true);
        setError(null);
        try {
          const url = `${API_BASE}/cut/scopes/analyze?source_path=${encodeURIComponent(path)}&time=${time}&scopes=${mode}&size=256`;
          const res = await fetch(url);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          if (data.success) {
            setScopeData(data);
          } else {
            setError(data.error || 'analysis_failed');
          }
        } catch (e: any) {
          setError(e.message || 'fetch_failed');
        } finally {
          setLoading(false);
        }
      }, 200);
    },
    [mode],
  );

  // Trigger fetch on media/time/mode change
  useEffect(() => {
    if (!mediaPath) {
      setScopeData(null);
      return;
    }
    fetchScopes(mediaPath, currentTime);
    return () => {
      if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current);
    };
  }, [mediaPath, currentTime, mode, fetchScopes]);

  // Draw on canvas when data arrives
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !scopeData) return;

    const rect = canvas.parentElement?.getBoundingClientRect();
    const w = rect ? Math.floor(rect.width - 16) : 256;
    const h = rect ? Math.floor(rect.height - 16) : 256;
    const size = Math.min(w, h, 512);

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    if (mode === 'waveform' && scopeData.waveform) {
      drawWaveform(ctx, scopeData.waveform, size, size);
    } else if (mode === 'vectorscope' && scopeData.vectorscope) {
      drawVectorscope(ctx, scopeData.vectorscope, size, size);
    } else if (mode === 'histogram' && scopeData.histogram) {
      drawHistogram(ctx, scopeData.histogram, size, size);
    }
  }, [scopeData, mode]);

  return (
    <div style={PANEL_STYLE} data-testid="cut-video-scopes">
      <div style={TAB_BAR}>
        {(['waveform', 'vectorscope', 'histogram'] as const).map((m) => (
          <button
            key={m}
            style={mode === m ? TAB_BTN_ACTIVE : TAB_BTN}
            onClick={() => setMode(m)}
            data-testid={`scope-tab-${m}`}
          >
            {m === 'waveform' ? 'Waveform' : m === 'vectorscope' ? 'Vectorscope' : 'Histogram'}
          </button>
        ))}
      </div>

      <div style={CANVAS_WRAP}>
        {!mediaPath ? (
          <span style={{ color: '#555', fontSize: 10 }}>No media selected</span>
        ) : error ? (
          <span style={{ color: '#ef4444', fontSize: 10 }}>{error}</span>
        ) : (
          <canvas ref={canvasRef} data-testid="scope-canvas" />
        )}
      </div>

      <div style={STATUS_BAR}>
        {loading ? 'Analyzing...' : scopeData ? `${scopeData.frame_w}x${scopeData.frame_h} @ ${currentTime.toFixed(2)}s` : ''}
      </div>
    </div>
  );
}
